"""
Simplified vector store using Qdrant.
"""

from typing import List, Optional, Tuple, Dict, Any
import warnings

from langchain_core.documents import Document

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("ai.vector_store")

_client = None
_vector_store = None
_available = False


def get_client():
    """Get Qdrant client."""
    global _client
    if _client is None:
        try:
            from qdrant_client import QdrantClient
            
            settings = get_settings()
            
            # Log connection details (without exposing full API key)
            api_key = settings.qdrant_api_key
            logger.info(f"Connecting to Qdrant at: {settings.qdrant_url}")
            logger.info(f"API key provided: {bool(api_key)}")
            if api_key:
                logger.info(f"API key length: {len(api_key)}, starts with: {api_key[:20]}...")
            
            # For Qdrant Cloud, we need to pass the URL and API key
            # The URL should be HTTPS for cloud instances
            if api_key:
                _client = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=api_key,
                    timeout=30,  # Increase timeout for cloud
                )
            else:
                # Local Qdrant without auth
                _client = QdrantClient(
                    url=settings.qdrant_url,
                    timeout=10,
                )
            
            logger.info("Qdrant client created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create Qdrant client: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    return _client


async def get_vector_store():
    """Get LangChain Qdrant vector store."""
    global _vector_store, _available
    
    if not _available:
        return None
        
    if _vector_store is None:
        try:
            from langchain_qdrant import QdrantVectorStore
            from app.ai.llm import get_embeddings
            
            settings = get_settings()
            client = get_client()
            
            if client is None:
                return None
            
            embeddings = get_embeddings()
            
            # Note: parameter is 'embedding' (singular) in langchain-qdrant
            _vector_store = QdrantVectorStore(
                client=client,
                collection_name=settings.qdrant_collection_name,
                embedding=embeddings,
            )
            logger.info("Vector store created successfully")
        except Exception as e:
            logger.error(f"Failed to create vector store: {e}")
            return None
            
    return _vector_store


async def initialize_collection() -> bool:
    """Initialize Qdrant collection if it doesn't exist."""
    global _available
    
    try:
        from qdrant_client.models import Distance, VectorParams
        
        settings = get_settings()
        logger.info(f"Initializing collection: {settings.qdrant_collection_name}")
        
        client = get_client()
        
        if client is None:
            logger.error("Client is None - could not create Qdrant client")
            _available = False
            return False
        
        # Test connection by getting collections list
        logger.info("Testing Qdrant connection...")
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        logger.info(f"Found existing collections: {collection_names}")
        
        if settings.qdrant_collection_name not in collection_names:
            logger.info(f"Creating new collection: {settings.qdrant_collection_name}")
            client.create_collection(
                collection_name=settings.qdrant_collection_name,
                vectors_config=VectorParams(
                    size=1536,  # OpenAI embedding size
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {settings.qdrant_collection_name}")
        else:
            logger.info(f"Collection '{settings.qdrant_collection_name}' already exists")
        
        _available = True
        logger.info("Qdrant initialization successful!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize collection: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        _available = False
        return False


async def is_available() -> bool:
    """Check if vector store is available."""
    return _available


async def add_documents(
    documents: List[Document],
    metadata: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Add documents to vector store."""
    if not _available:
        raise RuntimeError("Vector store is not available. Please start Qdrant.")
    
    try:
        store = await get_vector_store()
        
        if store is None:
            raise RuntimeError("Vector store is not available")
        
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
    if not _available:
        logger.warning("Vector store is not available - returning empty results")
        return []
    
    try:
        store = await get_vector_store()
        
        if store is None:
            return []
        
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
    if not _available:
        return False
    
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        settings = get_settings()
        client = get_client()
        
        if client is None:
            return False
        
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
    if not _available:
        return {"status": "unavailable", "error": "Qdrant not connected"}
    
    try:
        settings = get_settings()
        client = get_client()
        
        if client is None:
            return {"status": "unavailable", "error": "Client not initialized"}
        
        info = client.get_collection(settings.qdrant_collection_name)
        
        return {
            "collection_name": settings.qdrant_collection_name,
            "points_count": info.points_count,
            "status": str(info.status)
        }
        
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        return {"status": "error", "error": str(e)}
