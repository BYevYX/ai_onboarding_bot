"""
Vector store implementation using Qdrant and LangChain.
"""

from typing import Any, Dict, List, Optional, Tuple
import uuid
from datetime import datetime

from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, MatchValue

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.exceptions import VectorStoreError, VectorSearchError, VectorIndexError
from app.ai.langchain.llm_manager import llm_manager

logger = get_logger("ai.vector_store")


class OnboardingVectorStore:
    """Vector store for onboarding documents using Qdrant."""
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[QdrantClient] = None
        self._vector_store: Optional[QdrantVectorStore] = None
        self.collection_name = self.settings.qdrant.collection_name
    
    def get_client(self) -> QdrantClient:
        """Get Qdrant client."""
        if self._client is None:
            self._client = QdrantClient(
                url=self.settings.qdrant.url,
                api_key=self.settings.qdrant.api_key,
            )
        return self._client
    
    async def get_vector_store(self) -> QdrantVectorStore:
        """Get LangChain Qdrant vector store."""
        if self._vector_store is None:
            embeddings = llm_manager.get_embeddings()
            
            self._vector_store = QdrantVectorStore(
                client=self.get_client(),
                collection_name=self.collection_name,
                embeddings=embeddings,
            )
        return self._vector_store
    
    async def initialize_collection(self) -> bool:
        """Initialize Qdrant collection if it doesn't exist."""
        try:
            client = self.get_client()
            
            # Check if collection exists
            collections = client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create collection
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.settings.qdrant.vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(
                    "Qdrant collection created",
                    collection_name=self.collection_name
                )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to initialize Qdrant collection",
                error=str(e),
                collection_name=self.collection_name
            )
            raise VectorStoreError(
                message=f"Failed to initialize collection: {str(e)}",
                error_code="COLLECTION_INIT_FAILED"
            )
    
    async def add_documents(
        self,
        documents: List[Document],
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Add documents to vector store."""
        try:
            await self.initialize_collection()
            vector_store = await self.get_vector_store()
            
            # Add metadata to documents
            for doc in documents:
                doc.metadata.update({
                    "document_id": document_id or str(uuid.uuid4()),
                    "indexed_at": datetime.utcnow().isoformat(),
                    **(metadata or {})
                })
            
            # Add documents to vector store
            ids = await vector_store.aadd_documents(documents)
            
            logger.info(
                "Documents added to vector store",
                document_count=len(documents),
                document_id=document_id,
                vector_ids=len(ids)
            )
            
            return ids
            
        except Exception as e:
            logger.error(
                "Failed to add documents to vector store",
                error=str(e),
                document_count=len(documents),
                document_id=document_id
            )
            raise VectorIndexError(
                document_id=document_id or "unknown",
                reason=str(e)
            )
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_conditions: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0
    ) -> List[Tuple[Document, float]]:
        """Perform similarity search."""
        try:
            vector_store = await self.get_vector_store()
            
            # Build filter if provided
            search_kwargs = {"k": k}
            if filter_conditions:
                search_kwargs["filter"] = self._build_filter(filter_conditions)
            
            # Perform search
            results = await vector_store.asimilarity_search_with_score(
                query=query,
                **search_kwargs
            )
            
            # Filter by score threshold
            filtered_results = [
                (doc, score) for doc, score in results
                if score >= score_threshold
            ]
            
            logger.info(
                "Vector similarity search completed",
                query_length=len(query),
                results_count=len(filtered_results),
                k=k,
                score_threshold=score_threshold
            )
            
            return filtered_results
            
        except Exception as e:
            logger.error(
                "Vector similarity search failed",
                error=str(e),
                query=query[:100],  # Log first 100 chars
                k=k
            )
            raise VectorSearchError(
                query=query,
                reason=str(e)
            )
    
    async def search_by_metadata(
        self,
        metadata_filter: Dict[str, Any],
        limit: int = 10
    ) -> List[Document]:
        """Search documents by metadata."""
        try:
            client = self.get_client()
            
            # Build filter
            filter_conditions = self._build_filter(metadata_filter)
            
            # Search points
            search_result = client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_conditions,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # Convert to documents
            documents = []
            for point in search_result[0]:
                doc = Document(
                    page_content=point.payload.get("page_content", ""),
                    metadata=point.payload.get("metadata", {})
                )
                documents.append(doc)
            
            logger.info(
                "Metadata search completed",
                filter_conditions=metadata_filter,
                results_count=len(documents)
            )
            
            return documents
            
        except Exception as e:
            logger.error(
                "Metadata search failed",
                error=str(e),
                metadata_filter=metadata_filter
            )
            raise VectorSearchError(
                query=str(metadata_filter),
                reason=str(e)
            )
    
    async def delete_documents(
        self,
        document_id: str
    ) -> bool:
        """Delete documents by document_id."""
        try:
            client = self.get_client()
            
            # Delete points with matching document_id
            client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="metadata.document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            )
            
            logger.info(
                "Documents deleted from vector store",
                document_id=document_id
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to delete documents from vector store",
                error=str(e),
                document_id=document_id
            )
            return False
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information."""
        try:
            client = self.get_client()
            info = client.get_collection(self.collection_name)
            
            return {
                "name": info.config.params.vectors.size,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance,
                "points_count": info.points_count,
                "status": info.status
            }
            
        except Exception as e:
            logger.error(
                "Failed to get collection info",
                error=str(e),
                collection_name=self.collection_name
            )
            return {}
    
    def _build_filter(self, conditions: Dict[str, Any]) -> Filter:
        """Build Qdrant filter from conditions."""
        must_conditions = []
        
        for key, value in conditions.items():
            if isinstance(value, list):
                # Multiple values - use should condition
                should_conditions = [
                    FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=v)
                    ) for v in value
                ]
                must_conditions.append(Filter(should=should_conditions))
            else:
                # Single value
                must_conditions.append(
                    FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=value)
                    )
                )
        
        return Filter(must=must_conditions)


# Global vector store instance
vector_store = OnboardingVectorStore()