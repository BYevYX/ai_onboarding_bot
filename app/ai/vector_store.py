"""
Simplified vector store using Qdrant.
"""

from typing import List, Optional, Tuple, Dict, Any

from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ai.llm import get_embeddings

logger = get_logger("ai.vector_store")

_client: Optional[QdrantClient] = None
_vector_store: Optional[QdrantVectorStore] = None


def get_client() -> QdrantClient:
    """Get Qdrant client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
    return _client


async def get_vector_store() -> QdrantVectorStore:
    """Get LangChain Qdrant vector store."""
    global _vector_store
    if _vector_store is None:
        settings = get_settings()
        embeddings = get_embeddings()
        
        _vector_store = QdrantVectorStore(
            client=get_client(),
            collection_name=settings.qdrant_collection_name,
            embeddings=embeddings,
        )
    return _vector_store


async def initialize_collection() -> bool:
    """Initialize Qdrant collection if it doesn't exist."""
    try:
        settings = get_settings()
        client = get_client()
        
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if settings.qdrant_collection_name not in collection_names:
            client.create_collection(
                collection_name=settings.qdrant_collection_name,
                vectors_config=VectorParams(
                    size=1536,  # OpenAI embedding size
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {settings.qdrant_collection_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize collection: {e}")
        return False


async def add_documents(
    documents: List[Document],
    metadata: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Add documents to vector store."""
    try:
        await initialize_collection()
        store = await get_vector_store()
        
        # Add metadata to documents
        if metadata:
            for doc in documents:
                doc.metadata.update(metadata)
        
        ids = await store.aadd_documents(documents)
        logger.info(f"Added {len(documents)} documents to vector store")
        
        return ids
        
    except Exception as e:
        logger.error(f"Failed to add documents: {e}")
        raise


async def search(
    query: str,
    k: int = 5,
    score_threshold: float = 0.7
) -> List[Tuple[Document, float]]:
    """Search for similar documents."""
    try:
        store = await get_vector_store()
        
        results = await store.asimilarity_search_with_score(
            query=query,
            k=k
        )
        
        # Filter by score threshold
        filtered = [(doc, score) for doc, score in results if score >= score_threshold]
        
        logger.info(f"Search returned {len(filtered)} results for query: {query[:50]}...")
        
        return filtered
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


async def delete_by_source(source: str) -> bool:
    """Delete documents by source filename."""
    try:
        settings = get_settings()
        client = get_client()
        
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        client.delete(
            collection_name=settings.qdrant_collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="metadata.source",
                        match=MatchValue(value=source)
                    )
                ]
            )
        )
        
        logger.info(f"Deleted documents with source: {source}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete documents: {e}")
        return False


async def get_collection_stats() -> Dict[str, Any]:
    """Get collection statistics."""
    try:
        settings = get_settings()
        client = get_client()
        
        info = client.get_collection(settings.qdrant_collection_name)
        
        return {
            "collection_name": settings.qdrant_collection_name,
            "points_count": info.points_count,
            "status": str(info.status)
        }
        
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        return {"error": str(e)}
