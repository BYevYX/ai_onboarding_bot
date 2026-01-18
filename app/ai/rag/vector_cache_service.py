"""
Advanced caching service for vector operations with Redis backend.
"""

import asyncio
import hashlib
import json
import pickle
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

from langchain_core.documents import Document

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.cache import cache_manager
from app.core.exceptions import VectorSearchError

logger = get_logger("ai.vector_cache")


class VectorCacheService:
    """Advanced caching service for vector operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.cache_ttl = {
            "embeddings": 86400,  # 24 hours
            "search_results": 3600,  # 1 hour
            "user_context": 1800,  # 30 minutes
            "document_metadata": 7200,  # 2 hours
        }
    
    def _generate_cache_key(
        self,
        prefix: str,
        *args,
        user_id: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate cache key from arguments."""
        key_parts = [prefix]
        
        # Add user_id if provided
        if user_id:
            key_parts.append(f"user:{user_id}")
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                # Hash complex objects
                arg_str = json.dumps(arg, sort_keys=True, default=str)
                key_parts.append(hashlib.md5(arg_str.encode()).hexdigest()[:8])
        
        # Add keyword arguments
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (str, int, float, bool)):
                key_parts.append(f"{k}:{v}")
            else:
                v_str = json.dumps(v, sort_keys=True, default=str)
                key_parts.append(f"{k}:{hashlib.md5(v_str.encode()).hexdigest()[:8]}")
        
        return ":".join(key_parts)
    
    async def cache_embeddings(
        self,
        text: str,
        embedding: List[float],
        model: str = "default"
    ) -> bool:
        """Cache embedding for text."""
        try:
            cache_key = self._generate_cache_key("embedding", text, model=model)
            
            # Store embedding with metadata
            cache_data = {
                "embedding": embedding,
                "text": text,
                "model": model,
                "cached_at": datetime.utcnow().isoformat(),
                "dimension": len(embedding)
            }
            
            success = await cache_manager.set(
                cache_key,
                cache_data,
                ttl=self.cache_ttl["embeddings"]
            )
            
            if success:
                logger.debug(
                    "Embedding cached",
                    text_length=len(text),
                    model=model,
                    dimension=len(embedding)
                )
            
            return success
            
        except Exception as e:
            logger.error("Failed to cache embedding", error=str(e))
            return False
    
    async def get_cached_embedding(
        self,
        text: str,
        model: str = "default"
    ) -> Optional[List[float]]:
        """Get cached embedding for text."""
        try:
            cache_key = self._generate_cache_key("embedding", text, model=model)
            cache_data = await cache_manager.get(cache_key)
            
            if cache_data and isinstance(cache_data, dict):
                embedding = cache_data.get("embedding")
                if embedding:
                    logger.debug(
                        "Embedding cache hit",
                        text_length=len(text),
                        model=model
                    )
                    return embedding
            
            return None
            
        except Exception as e:
            logger.error("Failed to get cached embedding", error=str(e))
            return None
    
    async def cache_search_results(
        self,
        query: str,
        results: List[Tuple[Document, float]],
        search_params: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> bool:
        """Cache search results."""
        try:
            cache_key = self._generate_cache_key(
                "search",
                query,
                user_id=user_id,
                **search_params
            )
            
            # Serialize documents for caching
            serialized_results = []
            for doc, score in results:
                serialized_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                })
            
            cache_data = {
                "query": query,
                "results": serialized_results,
                "search_params": search_params,
                "user_id": user_id,
                "cached_at": datetime.utcnow().isoformat(),
                "result_count": len(results)
            }
            
            success = await cache_manager.set(
                cache_key,
                cache_data,
                ttl=self.cache_ttl["search_results"]
            )
            
            if success:
                logger.debug(
                    "Search results cached",
                    query_length=len(query),
                    result_count=len(results),
                    user_id=user_id
                )
            
            return success
            
        except Exception as e:
            logger.error("Failed to cache search results", error=str(e))
            return False
    
    async def get_cached_search_results(
        self,
        query: str,
        search_params: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> Optional[List[Tuple[Document, float]]]:
        """Get cached search results."""
        try:
            cache_key = self._generate_cache_key(
                "search",
                query,
                user_id=user_id,
                **search_params
            )
            
            cache_data = await cache_manager.get(cache_key)
            
            if cache_data and isinstance(cache_data, dict):
                serialized_results = cache_data.get("results", [])
                
                # Deserialize documents
                results = []
                for item in serialized_results:
                    doc = Document(
                        page_content=item["content"],
                        metadata=item["metadata"]
                    )
                    results.append((doc, item["score"]))
                
                if results:
                    logger.debug(
                        "Search results cache hit",
                        query_length=len(query),
                        result_count=len(results),
                        user_id=user_id
                    )
                    return results
            
            return None
            
        except Exception as e:
            logger.error("Failed to get cached search results", error=str(e))
            return None
    
    async def cache_user_context(
        self,
        user_id: int,
        context_data: Dict[str, Any]
    ) -> bool:
        """Cache user context data."""
        try:
            cache_key = self._generate_cache_key("user_context", user_id=user_id)
            
            cache_data = {
                **context_data,
                "cached_at": datetime.utcnow().isoformat(),
                "user_id": user_id
            }
            
            success = await cache_manager.set(
                cache_key,
                cache_data,
                ttl=self.cache_ttl["user_context"]
            )
            
            if success:
                logger.debug("User context cached", user_id=user_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to cache user context", error=str(e), user_id=user_id)
            return False
    
    async def get_cached_user_context(
        self,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get cached user context."""
        try:
            cache_key = self._generate_cache_key("user_context", user_id=user_id)
            cache_data = await cache_manager.get(cache_key)
            
            if cache_data and isinstance(cache_data, dict):
                logger.debug("User context cache hit", user_id=user_id)
                return cache_data
            
            return None
            
        except Exception as e:
            logger.error("Failed to get cached user context", error=str(e), user_id=user_id)
            return None
    
    async def cache_document_metadata(
        self,
        document_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Cache document metadata."""
        try:
            cache_key = self._generate_cache_key("doc_metadata", document_id)
            
            cache_data = {
                "document_id": document_id,
                "metadata": metadata,
                "cached_at": datetime.utcnow().isoformat()
            }
            
            success = await cache_manager.set(
                cache_key,
                cache_data,
                ttl=self.cache_ttl["document_metadata"]
            )
            
            if success:
                logger.debug("Document metadata cached", document_id=document_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to cache document metadata", error=str(e))
            return False
    
    async def get_cached_document_metadata(
        self,
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached document metadata."""
        try:
            cache_key = self._generate_cache_key("doc_metadata", document_id)
            cache_data = await cache_manager.get(cache_key)
            
            if cache_data and isinstance(cache_data, dict):
                logger.debug("Document metadata cache hit", document_id=document_id)
                return cache_data.get("metadata")
            
            return None
            
        except Exception as e:
            logger.error("Failed to get cached document metadata", error=str(e))
            return None
    
    async def invalidate_user_cache(self, user_id: int) -> int:
        """Invalidate all cache entries for a user."""
        try:
            pattern = f"*:user:{user_id}:*"
            count = await cache_manager.clear_pattern(pattern)
            
            logger.info("User cache invalidated", user_id=user_id, cleared_count=count)
            return count
            
        except Exception as e:
            logger.error("Failed to invalidate user cache", error=str(e), user_id=user_id)
            return 0
    
    async def invalidate_search_cache(self, pattern: str = "*search*") -> int:
        """Invalidate search cache entries."""
        try:
            count = await cache_manager.clear_pattern(pattern)
            
            logger.info("Search cache invalidated", pattern=pattern, cleared_count=count)
            return count
            
        except Exception as e:
            logger.error("Failed to invalidate search cache", error=str(e))
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            redis_client = await cache_manager.get_redis()
            
            # Get basic Redis info
            info = await redis_client.info()
            
            # Count keys by type
            key_counts = {}
            for cache_type in ["embedding", "search", "user_context", "doc_metadata"]:
                pattern = f"*{cache_type}*"
                keys = await redis_client.keys(pattern)
                key_counts[cache_type] = len(keys)
            
            return {
                "redis_info": {
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0)
                },
                "key_counts": key_counts,
                "cache_ttl": self.cache_ttl,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def warm_up_cache(
        self,
        common_queries: List[str],
        user_contexts: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Warm up cache with common data."""
        try:
            warmed_up = {
                "queries": 0,
                "contexts": 0,
                "errors": 0
            }
            
            # Pre-cache common queries (this would need integration with search service)
            for query in common_queries:
                try:
                    # This is a placeholder - in real implementation,
                    # you'd perform actual searches and cache results
                    cache_key = self._generate_cache_key("warmup_query", query)
                    await cache_manager.set(cache_key, {"query": query}, ttl=3600)
                    warmed_up["queries"] += 1
                except Exception:
                    warmed_up["errors"] += 1
            
            # Pre-cache user contexts
            for context in user_contexts:
                try:
                    user_id = context.get("user_id")
                    if user_id:
                        await self.cache_user_context(user_id, context)
                        warmed_up["contexts"] += 1
                except Exception:
                    warmed_up["errors"] += 1
            
            logger.info("Cache warm-up completed", stats=warmed_up)
            return warmed_up
            
        except Exception as e:
            logger.error("Cache warm-up failed", error=str(e))
            return {"error": str(e)}


# Global vector cache service instance
vector_cache_service = VectorCacheService()