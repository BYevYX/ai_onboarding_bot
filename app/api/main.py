"""
Main FastAPI application setup with RAG integration.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.exceptions import BaseAppException
from app.api.routes import documents, users, onboarding, health, rag
from app.bot.bot import telegram_bot

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager with RAG initialization."""
    # Startup
    logger.info("Starting FastAPI application with RAG integration")
    
    # Initialize AI components
    try:
        from app.ai.langchain.vector_store import vector_store
        from app.ai.rag.hybrid_rag_service import hybrid_rag_service
        from app.ai.rag.vector_cache_service import vector_cache_service
        
        # Initialize vector store
        await vector_store.initialize_collection()
        logger.info("Vector store initialized")
        
        # Health check for RAG service
        health = await hybrid_rag_service.health_check()
        if health.get("status") == "healthy":
            logger.info("Hybrid RAG service is healthy")
        else:
            logger.warning("Hybrid RAG service health check failed", health=health)
        
        # Warm up cache with common queries
        common_queries = [
            "что такое компания",
            "рабочее время",
            "отпуск",
            "пропуск",
            "столовая",
            "working hours",
            "vacation policy",
            "office location"
        ]
        
        await vector_cache_service.warm_up_cache(
            common_queries=common_queries,
            user_contexts=[]
        )
        logger.info("RAG cache warmed up")
        
    except Exception as e:
        logger.error("Failed to initialize AI components", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application")
    
    # Close connections
    try:
        from app.core.cache import cache_manager
        await cache_manager.close()
        logger.info("Cache connections closed")
    except Exception as e:
        logger.error("Error closing cache connections", error=str(e))


def create_app() -> FastAPI:
    """Create FastAPI application with RAG integration."""
    configure_logging()
    settings = get_settings()
    
    app = FastAPI(
        title="Telegram Onboarding Bot API with Hybrid RAG",
        description="""
        AI-powered employee onboarding system with advanced RAG capabilities:
        
        🤖 **Hybrid RAG System**
        - LangChain integration for document processing
        - Qdrant vector database for semantic search
        - OpenAI embeddings and LLM models
        - Intelligent query complexity analysis
        - Conversation memory management
        
        🚀 **Features**
        - Multi-language support (Russian, English, Arabic)
        - Real-time document search and Q&A
        - Rate limiting and caching
        - Comprehensive monitoring and analytics
        - Telegram bot integration
        
        📊 **Monitoring**
        - RAG system health checks
        - Cache statistics and management
        - User conversation tracking
        - Performance metrics
        """,
        version="1.0.0",
        docs_url="/docs" if settings.api.debug else None,
        redoc_url="/redoc" if settings.api.debug else None,
        lifespan=lifespan
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure properly for production
    )
    
    # Add exception handlers
    @app.exception_handler(BaseAppException)
    async def app_exception_handler(request: Request, exc: BaseAppException):
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.error_code or "APP_ERROR",
                "message": exc.message,
                "details": exc.details
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception",
            error=str(exc),
            path=request.url.path,
            method=request.method
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred"
            }
        )
    
    # Include routers
    app.include_router(health.router, prefix="/health", tags=["Health"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
    app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["Onboarding"])
    app.include_router(rag.router, prefix="/api/v1/rag", tags=["RAG System"])
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        log_level=settings.logging.level.lower()
    )