"""
Main FastAPI application setup.
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
from app.api.routes import documents, users, onboarding, health
from app.bot.bot import telegram_bot

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting FastAPI application")
    
    # Initialize AI components
    try:
        from app.ai.langchain.vector_store import vector_store
        await vector_store.initialize_collection()
        logger.info("Vector store initialized")
    except Exception as e:
        logger.error("Failed to initialize vector store", error=str(e))
    
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
    """Create FastAPI application."""
    configure_logging()
    settings = get_settings()
    
    app = FastAPI(
        title="Telegram Onboarding Bot API",
        description="AI-powered employee onboarding system with LangChain/LangGraph",
        version="0.1.0",
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