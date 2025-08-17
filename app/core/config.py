"""
Application configuration using Pydantic Settings.
"""

import os
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(..., env="DATABASE_URL")
    echo: bool = Field(False, env="DATABASE_ECHO")
    pool_size: int = Field(10, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(20, env="DATABASE_MAX_OVERFLOW")
    
    class Config:
        env_prefix = "DATABASE_"


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    max_connections: int = Field(10, env="REDIS_MAX_CONNECTIONS")
    
    class Config:
        env_prefix = "REDIS_"


class QdrantSettings(BaseSettings):
    """Qdrant vector database configuration."""
    
    url: str = Field("http://localhost:6333", env="QDRANT_URL")
    api_key: Optional[str] = Field(None, env="QDRANT_API_KEY")
    collection_name: str = Field("onboarding_documents", env="QDRANT_COLLECTION_NAME")
    vector_size: int = Field(1536, env="QDRANT_VECTOR_SIZE")  # OpenAI embedding size
    
    class Config:
        env_prefix = "QDRANT_"


class OpenAISettings(BaseSettings):
    """OpenAI API configuration."""
    
    api_key: str = Field(..., env="OPENAI_API_KEY")
    model: str = Field("gpt-4-turbo-preview", env="OPENAI_MODEL")
    embedding_model: str = Field("text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")
    max_tokens: int = Field(4000, env="OPENAI_MAX_TOKENS")
    temperature: float = Field(0.7, env="OPENAI_TEMPERATURE")
    
    class Config:
        env_prefix = "OPENAI_"


class LangChainSettings(BaseSettings):
    """LangChain and LangSmith configuration."""
    
    tracing_v2: bool = Field(False, env="LANGCHAIN_TRACING_V2")
    api_key: Optional[str] = Field(None, env="LANGCHAIN_API_KEY")
    project: str = Field("telegram-onboarding-bot", env="LANGCHAIN_PROJECT")
    
    class Config:
        env_prefix = "LANGCHAIN_"


class TelegramSettings(BaseSettings):
    """Telegram Bot configuration."""
    
    bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    webhook_url: Optional[str] = Field(None, env="TELEGRAM_WEBHOOK_URL")
    webhook_secret: Optional[str] = Field(None, env="TELEGRAM_WEBHOOK_SECRET")
    
    class Config:
        env_prefix = "TELEGRAM_"


class APISettings(BaseSettings):
    """FastAPI configuration."""
    
    host: str = Field("0.0.0.0", env="API_HOST")
    port: int = Field(8000, env="API_PORT")
    reload: bool = Field(False, env="API_RELOAD")
    debug: bool = Field(False, env="API_DEBUG")
    
    class Config:
        env_prefix = "API_"


class SecuritySettings(BaseSettings):
    """Security configuration."""
    
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    class Config:
        env_prefix = "SECURITY_"


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    
    level: str = Field("INFO", env="LOG_LEVEL")
    format: str = Field("json", env="LOG_FORMAT")
    
    @validator("level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    class Config:
        env_prefix = "LOG_"


class FileUploadSettings(BaseSettings):
    """File upload configuration."""
    
    max_file_size: int = Field(10485760, env="MAX_FILE_SIZE")  # 10MB
    allowed_file_types: List[str] = Field(
        ["pdf", "docx", "txt", "md"], 
        env="ALLOWED_FILE_TYPES"
    )
    upload_dir: str = Field("uploads", env="UPLOAD_DIR")
    
    @validator("allowed_file_types", pre=True)
    def parse_file_types(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v
    
    class Config:
        env_prefix = "FILE_"


class MultilingualSettings(BaseSettings):
    """Multilingual support configuration."""
    
    default_language: str = Field("ru", env="DEFAULT_LANGUAGE")
    supported_languages: List[str] = Field(
        ["ru", "en", "ar"], 
        env="SUPPORTED_LANGUAGES"
    )
    
    @validator("supported_languages", pre=True)
    def parse_languages(cls, v):
        if isinstance(v, str):
            return [lang.strip() for lang in v.split(",")]
        return v
    
    class Config:
        env_prefix = "LANG_"


class CacheSettings(BaseSettings):
    """Cache configuration."""
    
    ttl: int = Field(3600, env="CACHE_TTL")  # 1 hour
    max_size: int = Field(1000, env="CACHE_MAX_SIZE")
    
    class Config:
        env_prefix = "CACHE_"


class MonitoringSettings(BaseSettings):
    """Monitoring configuration."""
    
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    prometheus_port: int = Field(9090, env="PROMETHEUS_PORT")
    
    class Config:
        env_prefix = "MONITORING_"


class Settings(BaseSettings):
    """Main application settings."""
    
    environment: str = Field("development", env="ENVIRONMENT")
    
    # Sub-settings
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    qdrant: QdrantSettings = QdrantSettings()
    openai: OpenAISettings = OpenAISettings()
    langchain: LangChainSettings = LangChainSettings()
    telegram: TelegramSettings = TelegramSettings()
    api: APISettings = APISettings()
    security: SecuritySettings = SecuritySettings()
    logging: LoggingSettings = LoggingSettings()
    file_upload: FileUploadSettings = FileUploadSettings()
    multilingual: MultilingualSettings = MultilingualSettings()
    cache: CacheSettings = CacheSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    
    @validator("environment")
    def validate_environment(cls, v):
        valid_envs = ["development", "testing", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings