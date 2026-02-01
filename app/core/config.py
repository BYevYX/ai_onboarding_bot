"""
Simplified application configuration.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Environment
    environment: str = Field("development", alias="ENVIRONMENT")
    debug: bool = Field(False, alias="DEBUG")
    
    # Telegram
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    
    # OpenAI
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4-turbo-preview", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field("text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")
    
    # Qdrant
    qdrant_url: str = Field("http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(None, alias="QDRANT_API_KEY")
    qdrant_collection_name: str = Field("documents", alias="QDRANT_COLLECTION_NAME")
    
    # Redis (for FSM storage)
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    
    # File upload
    max_file_size: int = Field(10_485_760, alias="MAX_FILE_SIZE")  # 10MB
    upload_dir: str = Field("uploads", alias="UPLOAD_DIR")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
