"""
API routes for RAG system monitoring and management.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.ai.rag.hybrid_rag_service import hybrid_rag_service
from app.ai.rag.vector_cache_service import vector_cache_service
from app.ai.langchain.vector_store import vector_store

logger = get_logger("api.rag")

router = APIRouter(prefix="/rag", tags=["RAG System"])


class RAGQueryRequest(BaseModel):
    """Request model for RAG query."""
    query: str = Field(..., description="User query")
    user_id: int = Field(..., description="User ID")
    language: str = Field("ru", description="Response language")
    use_conversation_memory: bool = Field(True, description="Use conversation memory")
    user_info: Optional[Dict[str, Any]] = Field(None, description="User context information")


class RAGQueryResponse(BaseModel):
    """Response model for RAG query."""
    answer: str = Field(..., description="Generated answer")
    query_complexity: str = Field(..., description="Query complexity level")
    processing_method: str = Field(..., description="Processing method used")
    source_documents: List[Dict[str, Any]] = Field(..., description="Source documents")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: str = Field(..., description="Response timestamp")


class RAGHealthResponse(BaseModel):
    """Response model for RAG health check."""
    status: str = Field(..., description="Overall health status")
    vector_store: Dict[str, Any] = Field(..., description="Vector store status")
    llm: Dict[str, Any] = Field(..., description="LLM status")
    active_conversations: int = Field(..., description="Number of active conversations")
    timestamp: str = Field(..., description="Health check timestamp")


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""
    redis_info: Dict[str, Any] = Field(..., description="Redis information")
    key_counts: Dict[str, int] = Field(..., description="Cache key counts by type")
    cache_ttl: Dict[str, int] = Field(..., description="Cache TTL settings")
    timestamp: str = Field(..., description="Statistics timestamp")


@router.post("/query", response_model=RAGQueryResponse)
async def process_rag_query(request: RAGQueryRequest) -> RAGQueryResponse:
    """Process a RAG query through the hybrid service."""
    try:
        start_time = datetime.utcnow()
        
        result = await hybrid_rag_service.process_query(
            query=request.query,
            user_id=request.user_id,
            user_info=request.user_info,
            language=request.language,
            use_conversation_memory=request.use_conversation_memory
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return RAGQueryResponse(
            answer=result["answer"],
            query_complexity=result.get("query_complexity", "unknown"),
            processing_method=result.get("processing_method", "unknown"),
            source_documents=result.get("source_documents", []),
            processing_time=processing_time,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error("RAG query processing failed", error=str(e), user_id=request.user_id)
        raise HTTPException(
            status_code=500,
            detail=f"RAG query processing failed: {str(e)}"
        )


@router.get("/health", response_model=RAGHealthResponse)
async def get_rag_health() -> RAGHealthResponse:
    """Get RAG system health status."""
    try:
        health = await hybrid_rag_service.health_check()
        
        return RAGHealthResponse(
            status=health.get("status", "unknown"),
            vector_store=health.get("vector_store", {}),
            llm=health.get("llm", {}),
            active_conversations=health.get("active_conversations", 0),
            timestamp=health.get("timestamp", datetime.utcnow().isoformat())
        )
        
    except Exception as e:
        logger.error("RAG health check failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"RAG health check failed: {str(e)}"
        )


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats() -> CacheStatsResponse:
    """Get cache statistics."""
    try:
        stats = await vector_cache_service.get_cache_stats()
        
        return CacheStatsResponse(
            redis_info=stats.get("redis_info", {}),
            key_counts=stats.get("key_counts", {}),
            cache_ttl=stats.get("cache_ttl", {}),
            timestamp=stats.get("timestamp", datetime.utcnow().isoformat())
        )
        
    except Exception as e:
        logger.error("Cache stats retrieval failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Cache stats retrieval failed: {str(e)}"
        )


@router.delete("/cache/user/{user_id}")
async def clear_user_cache(user_id: int) -> Dict[str, Any]:
    """Clear cache for specific user."""
    try:
        # Clear RAG memory
        memory_cleared = await hybrid_rag_service.clear_user_memory(user_id)
        
        # Clear vector cache
        cache_cleared = await vector_cache_service.invalidate_user_cache(user_id)
        
        return {
            "user_id": user_id,
            "memory_cleared": memory_cleared,
            "cache_entries_cleared": cache_cleared,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("User cache clearing failed", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=500,
            detail=f"User cache clearing failed: {str(e)}"
        )


@router.delete("/cache/search")
async def clear_search_cache(
    pattern: str = Query("*search*", description="Cache key pattern to clear")
) -> Dict[str, Any]:
    """Clear search cache entries."""
    try:
        cleared_count = await vector_cache_service.invalidate_search_cache(pattern)
        
        return {
            "pattern": pattern,
            "cleared_count": cleared_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Search cache clearing failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Search cache clearing failed: {str(e)}"
        )


@router.get("/conversations/{user_id}")
async def get_user_conversation_history(user_id: int) -> Dict[str, Any]:
    """Get conversation history for user."""
    try:
        history = await hybrid_rag_service.get_user_conversation_history(user_id)
        
        return {
            "user_id": user_id,
            "conversation_history": history,
            "message_count": len(history),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Conversation history retrieval failed", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=500,
            detail=f"Conversation history retrieval failed: {str(e)}"
        )


@router.get("/vector-store/info")
async def get_vector_store_info() -> Dict[str, Any]:
    """Get vector store information."""
    try:
        info = await vector_store.get_collection_info()
        
        return {
            "collection_info": info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Vector store info retrieval failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Vector store info retrieval failed: {str(e)}"
        )


@router.post("/cache/warmup")
async def warmup_cache(
    common_queries: List[str] = Query(..., description="Common queries to cache"),
    user_contexts: List[Dict[str, Any]] = Query([], description="User contexts to cache")
) -> Dict[str, Any]:
    """Warm up cache with common queries and contexts."""
    try:
        result = await vector_cache_service.warm_up_cache(
            common_queries=common_queries,
            user_contexts=user_contexts
        )
        
        return {
            "warmup_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Cache warmup failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Cache warmup failed: {str(e)}"
        )


@router.get("/metrics")
async def get_rag_metrics() -> Dict[str, Any]:
    """Get comprehensive RAG system metrics."""
    try:
        # Get health status
        health = await hybrid_rag_service.health_check()
        
        # Get cache stats
        cache_stats = await vector_cache_service.get_cache_stats()
        
        # Get vector store info
        vector_info = await vector_store.get_collection_info()
        
        return {
            "health": health,
            "cache": cache_stats,
            "vector_store": vector_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("RAG metrics retrieval failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"RAG metrics retrieval failed: {str(e)}"
        )