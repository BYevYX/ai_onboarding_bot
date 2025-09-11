"""
Application configuration using Pydantic Settings.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppBaseSettings(BaseSettings):
    """Base application settings."""

    environment: str = Field("development", env="ENVIRONMENT", frozen=True)

    # базовый конфиг (общий для всех наследников)
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        # чтобы Field(frozen=True) действительно блокировал присвоение
        validate_assignment=True,
    )

    @classmethod
    def _build_settings_config_for_subclass(cls) -> SettingsConfigDict:
        """Формирует итоговый SettingsConfigDict с учётом env_prefix наследника (если есть)."""
        base_dict = dict(cls.model_config or {})
        env_prefix = getattr(cls, "env_prefix", None)
        if env_prefix:
            base_dict["env_prefix"] = env_prefix
        return SettingsConfigDict(**base_dict)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        При создании подкласса подставляем на класс корректный __pydantic_settings_config__.
        Это официальный и надёжный хук для pydantic v2.
        """
        super().__init_subclass__(**kwargs)
        cls.__pydantic_settings_config__ = cls._build_settings_config_for_subclass()


class DatabaseSettings(AppBaseSettings):
    """Database configuration settings."""

    env_prefix = "DATABASE_"

    url: str = Field(..., frozen=True)
    echo: bool = Field(False, frozen=True)
    pool_size: int = Field(10, frozen=True)
    max_overflow: int = Field(20, frozen=True)


class RedisSettings(AppBaseSettings):
    """Redis configuration settings."""

    env_prefix = "REDIS_"

    url: str = Field("redis://localhost:6379/0", frozen=True)
    max_connections: int = Field(10, frozen=True)


class QdrantSettings(AppBaseSettings):
    """Qdrant vector database configuration."""

    env_prefix = "QDRANT_"

    url: str = Field("http://localhost:6333", frozen=True)
    api_key: Optional[str] = Field(None, frozen=True)
    collection_name: str = Field("onboarding_documents", frozen=True)
    vector_size: int = Field(1536, frozen=True)  # OpenAI embedding size


class OpenAISettings(AppBaseSettings):
    """OpenAI API configuration."""

    env_prefix = "OPENAI_"

    api_key: str = Field("placeholder", frozen=True)
    model: str = Field("gpt-4-turbo-preview", frozen=True)
    embedding_model: str = Field("text-embedding-3-small", frozen=True)
    max_tokens: int = Field(4000, frozen=True)
    temperature: float = Field(0.7, frozen=True)


class LangChainSettings(AppBaseSettings):
    """LangChain and LangSmith configuration."""

    env_prefix = "LANGCHAIN_"

    tracing_v2: bool = Field(False, frozen=True)
    api_key: Optional[str] = Field(None, frozen=True)
    project: str = Field("telegram-onboarding-bot", frozen=True)


class TelegramSettings(AppBaseSettings):
    """Telegram Bot configuration."""

    env_prefix = "TELEGRAM_"

    bot_token: str = Field("placeholder", frozen=True)


class APISettings(AppBaseSettings):
    """FastAPI configuration."""

    env_prefix = "API_"

    host: str = Field("0.0.0.0", frozen=True)
    port: int = Field(8000, frozen=True)
    reload: bool = Field(False, frozen=True)
    debug: bool = Field(False, frozen=True)


class SecuritySettings(AppBaseSettings):
    """Security configuration."""

    # оставил env= как было у тебя (не добавлял новых)
    secret_key: str = Field("placeholder-secret-key-change-in-production", env="SECRET_KEY", frozen=True)
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES", frozen=True)


class LoggingSettings(AppBaseSettings):
    """Logging configuration."""

    level: str = Field("INFO", env="LOG_LEVEL")
    format: str = Field("json", env="LOG_FORMAT")

    @field_validator("level")
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class FileUploadSettings(AppBaseSettings):
    """File upload configuration."""

    max_file_size: int = Field(10_485_760, env="MAX_FILE_SIZE")  # 10MB
    allowed_file_types: List[str] = Field(
        ["pdf", "docx", "txt", "md"],
        env="ALLOWED_FILE_TYPES",
    )
    upload_dir: str = Field("uploads", env="UPLOAD_DIR")

    @field_validator("allowed_file_types", mode="before")
    def parse_file_types(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",") if ext.strip()]
        return v


class MultilingualSettings(AppBaseSettings):
    """Multilingual support configuration."""

    env_prefix = "I18N_"

    default_language: str = Field("ru", env="DEFAULT_LANGUAGE")
    supported_languages: List[str] = Field(
        ["ru", "en", "ar"],
        env="SUPPORTED_LANGUAGES",
    )

    @field_validator("supported_languages", mode="before")
    def parse_languages(cls, v):
        if isinstance(v, str):
            return [lang.strip() for lang in v.split(",") if lang.strip()]
        return v


class CacheSettings(AppBaseSettings):
    """Cache configuration."""

    env_prefix = "CACHE_"

    ttl: int = Field(3600)  # 1 hour
    max_size: int = Field(1000)


class Settings(AppBaseSettings):
    """Main application settings."""

    # environment унаследован из AppBaseSettings, не дублируем

    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    langchain: LangChainSettings = Field(default_factory=LangChainSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    file_upload: FileUploadSettings = Field(default_factory=FileUploadSettings)
    multilingual: MultilingualSettings = Field(default_factory=MultilingualSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)

    @field_validator("environment")
    def validate_environment(cls, v: str) -> str:
        valid_envs = ["development", "testing", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v


# Ленивое получение настроек (рекомендуется для тестов / FastAPI)
# Первый вызов создаст Settings(), дальше кешируется.
@lru_cache()
def get_settings() -> Settings:
    return Settings()
