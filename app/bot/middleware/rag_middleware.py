"""
Middleware for RAG operations rate limiting and monitoring.
"""

import asyncio
from typing import Any, Awaitable, Callable, Dict, Optional
from datetime import datetime, timedelta

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.cache import cache_manager
from app.ai.rag.vector_cache_service import vector_cache_service

logger = get_logger("bot.rag_middleware")


class RAGRateLimitMiddleware(BaseMiddleware):
    """Middleware for rate limiting RAG operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.rate_limits = {
            "queries_per_minute": 10,
            "queries_per_hour": 100,
            "complex_queries_per_hour": 20
        }
        
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process middleware."""
        
        # Only apply to messages and callback queries
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)
        
        user_id = event.from_user.id if event.from_user else None
        if not user_id:
            return await handler(event, data)
        
        # Check rate limits
        if not await self._check_rate_limits(user_id):
            await self._send_rate_limit_message(event)
            return
        
        # Add RAG context to data
        data["rag_context"] = await self._get_rag_context(user_id)
        
        # Execute handler with timing
        start_time = datetime.utcnow()
        try:
            result = await handler(event, data)
            
            # Log successful processing
            duration = (datetime.utcnow() - start_time).total_seconds()
            await self._log_rag_usage(user_id, duration, success=True)
            
            return result
            
        except Exception as e:
            # Log failed processing
            duration = (datetime.utcnow() - start_time).total_seconds()
            await self._log_rag_usage(user_id, duration, success=False, error=str(e))
            raise
    
    async def _check_rate_limits(self, user_id: int) -> bool:
        """Check if user is within rate limits."""
        try:
            now = datetime.utcnow()
            
            # Check minute limit
            minute_key = f"rag_rate_limit:minute:{user_id}:{now.strftime('%Y%m%d%H%M')}"
            minute_count = await cache_manager.get(minute_key) or 0
            
            if minute_count >= self.rate_limits["queries_per_minute"]:
                logger.warning(
                    "RAG rate limit exceeded (minute)",
                    user_id=user_id,
                    count=minute_count,
                    limit=self.rate_limits["queries_per_minute"]
                )
                return False
            
            # Check hour limit
            hour_key = f"rag_rate_limit:hour:{user_id}:{now.strftime('%Y%m%d%H')}"
            hour_count = await cache_manager.get(hour_key) or 0
            
            if hour_count >= self.rate_limits["queries_per_hour"]:
                logger.warning(
                    "RAG rate limit exceeded (hour)",
                    user_id=user_id,
                    count=hour_count,
                    limit=self.rate_limits["queries_per_hour"]
                )
                return False
            
            # Update counters
            await cache_manager.set(minute_key, minute_count + 1, ttl=60)
            await cache_manager.set(hour_key, hour_count + 1, ttl=3600)
            
            return True
            
        except Exception as e:
            logger.error("Rate limit check failed", error=str(e), user_id=user_id)
            # Allow request on error to avoid blocking users
            return True
    
    async def _get_rag_context(self, user_id: int) -> Dict[str, Any]:
        """Get RAG context for user."""
        try:
            context = await vector_cache_service.get_cached_user_context(user_id)
            return context or {}
        except Exception as e:
            logger.error("Failed to get RAG context", error=str(e), user_id=user_id)
            return {}
    
    async def _log_rag_usage(
        self,
        user_id: int,
        duration: float,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Log RAG usage statistics."""
        try:
            usage_data = {
                "user_id": user_id,
                "duration": duration,
                "success": success,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if error:
                usage_data["error"] = error
            
            # Store usage data for analytics
            usage_key = f"rag_usage:{user_id}:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            await cache_manager.set(usage_key, usage_data, ttl=86400)  # Keep for 24 hours
            
            logger.info(
                "RAG usage logged",
                user_id=user_id,
                duration=duration,
                success=success
            )
            
        except Exception as e:
            logger.error("Failed to log RAG usage", error=str(e))
    
    async def _send_rate_limit_message(self, event: TelegramObject) -> None:
        """Send rate limit exceeded message."""
        try:
            if isinstance(event, Message):
                await event.answer(
                    "⚠️ Превышен лимит запросов. Пожалуйста, подождите немного перед следующим вопросом.\n\n"
                    "⚠️ Rate limit exceeded. Please wait a moment before asking another question.\n\n"
                    "⚠️ تم تجاوز حد المعدل. يرجى الانتظار قليلاً قبل طرح سؤال آخر."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "Rate limit exceeded. Please wait.",
                    show_alert=True
                )
        except Exception as e:
            logger.error("Failed to send rate limit message", error=str(e))


class RAGMonitoringMiddleware(BaseMiddleware):
    """Middleware for monitoring RAG operations."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process middleware."""
        
        # Only monitor messages
        if not isinstance(event, Message):
            return await handler(event, data)
        
        user_id = event.from_user.id if event.from_user else None
        if not user_id:
            return await handler(event, data)
        
        # Add monitoring context
        data["monitoring"] = {
            "start_time": datetime.utcnow(),
            "user_id": user_id,
            "message_length": len(event.text or ""),
            "message_type": "text" if event.text else "other"
        }
        
        try:
            result = await handler(event, data)
            
            # Log successful interaction
            await self._log_interaction(data["monitoring"], success=True)
            
            return result
            
        except Exception as e:
            # Log failed interaction
            await self._log_interaction(data["monitoring"], success=False, error=str(e))
            raise
    
    async def _log_interaction(
        self,
        monitoring_data: Dict[str, Any],
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Log interaction for monitoring."""
        try:
            end_time = datetime.utcnow()
            duration = (end_time - monitoring_data["start_time"]).total_seconds()
            
            log_data = {
                **monitoring_data,
                "end_time": end_time.isoformat(),
                "duration": duration,
                "success": success
            }
            
            if error:
                log_data["error"] = error
            
            # Store for analytics
            log_key = f"rag_interaction:{monitoring_data['user_id']}:{end_time.strftime('%Y%m%d%H%M%S')}"
            await cache_manager.set(log_key, log_data, ttl=86400)
            
            logger.info(
                "RAG interaction monitored",
                user_id=monitoring_data["user_id"],
                duration=duration,
                success=success,
                message_length=monitoring_data["message_length"]
            )
            
        except Exception as e:
            logger.error("Failed to log interaction", error=str(e))


class RAGCacheWarmupMiddleware(BaseMiddleware):
    """Middleware for warming up RAG cache based on user patterns."""
    
    def __init__(self):
        self.settings = get_settings()
        self.warmup_patterns = {
            "common_queries": [
                "что такое компания",
                "где находится офис",
                "как получить пропуск",
                "рабочее время",
                "отпуск",
                "what is the company",
                "office location",
                "working hours",
                "vacation policy"
            ]
        }
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process middleware."""
        
        # Only process messages
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)
        
        user_id = event.from_user.id if event.from_user else None
        if not user_id:
            return await handler(event, data)
        
        # Check if this is a new user and warm up cache
        await self._maybe_warmup_cache(user_id, event.text)
        
        return await handler(event, data)
    
    async def _maybe_warmup_cache(self, user_id: int, query: str) -> None:
        """Maybe warm up cache for new users."""
        try:
            # Check if user is new (no cached context)
            cached_context = await vector_cache_service.get_cached_user_context(user_id)
            
            if not cached_context:
                # New user - warm up cache with common queries
                logger.info("Warming up cache for new user", user_id=user_id)
                
                # This would be done asynchronously to not block the user
                asyncio.create_task(
                    vector_cache_service.warm_up_cache(
                        common_queries=self.warmup_patterns["common_queries"],
                        user_contexts=[{"user_id": user_id, "first_query": query}]
                    )
                )
                
        except Exception as e:
            logger.error("Cache warmup failed", error=str(e), user_id=user_id)