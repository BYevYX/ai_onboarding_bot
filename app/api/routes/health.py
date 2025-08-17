"""
Health check endpoints.
"""

from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("api.health")
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    settings = get_settings()
    
    # Check service statuses
    services = {}
    
    # Check Redis
    try:
        from app.core.cache import cache_manager
        redis_client = await cache_manager.get_redis()
        await redis_client.ping()
        services["redis"] = "healthy"
    except Exception as e:
        logger.warning("Redis health check failed", error=str(e))
        services["redis"] = "unhealthy"
    
    # Check Qdrant
    try:
        from app.ai.langchain.vector_store import vector_store
        client = vector_store.get_client()
        collections = client.get_collections()
        services["qdrant"] = "healthy"
    except Exception as e:
        logger.warning("Qdrant health check failed", error=str(e))
        services["qdrant"] = "unhealthy"
    
    # Check OpenAI (basic connectivity)
    try:
        from app.ai.langchain.llm_manager import llm_manager
        # Just check if we can create the client
        llm_manager.get_chat_model()
        services["openai"] = "healthy"
    except Exception as e:
        logger.warning("OpenAI health check failed", error=str(e))
        services["openai"] = "unhealthy"
    
    # Overall status
    overall_status = "healthy" if all(
        status == "healthy" for status in services.values()
    ) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="0.1.0",
        services=services
    )


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check for Kubernetes."""
    try:
        # Check critical dependencies
        from app.ai.langchain.vector_store import vector_store
        await vector_store.initialize_collection()
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return {
            "status": "not_ready",
            "timestamp": datetime.utcnow(),
            "error": str(e)
        }


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """Liveness check for Kubernetes."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }