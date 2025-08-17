"""
Caching utilities using Redis and in-memory cache.
"""

import json
import pickle
from typing import Any, Optional, Union
from functools import wraps
import asyncio

import redis.asyncio as redis
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("cache")


class CacheManager:
    """Redis-based cache manager."""
    
    def __init__(self):
        self.settings = get_settings()
        self._redis: Optional[redis.Redis] = None
    
    async def get_redis(self) -> redis.Redis:
        """Get Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.settings.redis.url,
                max_connections=self.settings.redis.max_connections,
                decode_responses=False  # We'll handle encoding ourselves
            )
        return self._redis
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            redis_client = await self.get_redis()
            value = await redis_client.get(key)
            if value is None:
                return None
            
            # Try to deserialize as JSON first, then pickle
            try:
                return json.loads(value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return pickle.loads(value)
                
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        try:
            redis_client = await self.get_redis()
            ttl = ttl or self.settings.cache.ttl
            
            # Try to serialize as JSON first, then pickle
            try:
                serialized_value = json.dumps(value).encode('utf-8')
            except (TypeError, ValueError):
                serialized_value = pickle.dumps(value)
            
            await redis_client.setex(key, ttl, serialized_value)
            return True
            
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            redis_client = await self.get_redis()
            result = await redis_client.delete(key)
            return result > 0
            
        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            redis_client = await self.get_redis()
            result = await redis_client.exists(key)
            return result > 0
            
        except Exception as e:
            logger.error("Cache exists error", key=key, error=str(e))
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        try:
            redis_client = await self.get_redis()
            keys = await redis_client.keys(pattern)
            if keys:
                return await redis_client.delete(*keys)
            return 0
            
        except Exception as e:
            logger.error("Cache clear pattern error", pattern=pattern, error=str(e))
            return 0
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


# Global cache manager instance
cache_manager = CacheManager()


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments."""
    key_parts = []
    
    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(str(hash(str(arg))))
    
    # Add keyword arguments
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}:{v}")
        else:
            key_parts.append(f"{k}:{hash(str(v))}")
    
    return ":".join(key_parts)


def cached(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    key_func: Optional[callable] = None
):
    """Decorator for caching function results."""
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key_str = key_func(*args, **kwargs)
            else:
                cache_key_str = cache_key(func.__name__, *args, **kwargs)
            
            if key_prefix:
                cache_key_str = f"{key_prefix}:{cache_key_str}"
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key_str)
            if cached_result is not None:
                logger.debug("Cache hit", key=cache_key_str, function=func.__name__)
                return cached_result
            
            # Execute function
            logger.debug("Cache miss", key=cache_key_str, function=func.__name__)
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache_manager.set(cache_key_str, result, ttl)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class InMemoryCache:
    """Simple in-memory cache for frequently accessed data."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache = {}
        self._access_order = []
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        if key in self._cache:
            # Move to end (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set value in memory cache."""
        if key in self._cache:
            # Update existing
            self._cache[key] = value
            self._access_order.remove(key)
            self._access_order.append(key)
        else:
            # Add new
            if len(self._cache) >= self.max_size:
                # Remove least recently used
                lru_key = self._access_order.pop(0)
                del self._cache[lru_key]
            
            self._cache[key] = value
            self._access_order.append(key)
    
    def delete(self, key: str) -> bool:
        """Delete value from memory cache."""
        if key in self._cache:
            del self._cache[key]
            self._access_order.remove(key)
            return True
        return False
    
    def clear(self):
        """Clear all cached values."""
        self._cache.clear()
        self._access_order.clear()


# Global in-memory cache instance
memory_cache = InMemoryCache(max_size=get_settings().cache.max_size)