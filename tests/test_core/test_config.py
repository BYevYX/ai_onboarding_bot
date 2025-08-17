"""
Tests for core configuration.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.core.config import Settings, get_settings


class TestSettings:
    """Test settings configuration."""
    
    def test_settings_creation(self):
        """Test settings can be created with defaults."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql+asyncpg://test:test@localhost:5432/test',
            'OPENAI_API_KEY': 'test-key',
            'TELEGRAM_BOT_TOKEN': 'test-token',
            'SECRET_KEY': 'test-secret'
        }):
            settings = Settings()
            
            assert settings.environment == "development"
            assert settings.database.url == 'postgresql+asyncpg://test:test@localhost:5432/test'
            assert settings.openai.api_key == 'test-key'
            assert settings.telegram.bot_token == 'test-token'
            assert settings.security.secret_key == 'test-secret'
    
    def test_database_settings(self):
        """Test database settings."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql+asyncpg://test:test@localhost:5432/test',
            'DATABASE_ECHO': 'true',
            'DATABASE_POOL_SIZE': '20',
            'OPENAI_API_KEY': 'test-key',
            'TELEGRAM_BOT_TOKEN': 'test-token',
            'SECRET_KEY': 'test-secret'
        }):
            settings = Settings()
            
            assert settings.database.url == 'postgresql+asyncpg://test:test@localhost:5432/test'
            assert settings.database.echo == True
            assert settings.database.pool_size == 20
    
    def test_openai_settings(self):
        """Test OpenAI settings."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql+asyncpg://test:test@localhost:5432/test',
            'OPENAI_API_KEY': 'test-key',
            'OPENAI_MODEL': 'gpt-4',
            'OPENAI_TEMPERATURE': '0.5',
            'TELEGRAM_BOT_TOKEN': 'test-token',
            'SECRET_KEY': 'test-secret'
        }):
            settings = Settings()
            
            assert settings.openai.api_key == 'test-key'
            assert settings.openai.model == 'gpt-4'
            assert settings.openai.temperature == 0.5
    
    def test_multilingual_settings(self):
        """Test multilingual settings."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql+asyncpg://test:test@localhost:5432/test',
            'OPENAI_API_KEY': 'test-key',
            'TELEGRAM_BOT_TOKEN': 'test-token',
            'SECRET_KEY': 'test-secret',
            'DEFAULT_LANGUAGE': 'en',
            'SUPPORTED_LANGUAGES': 'en,ru,ar'
        }):
            settings = Settings()
            
            assert settings.multilingual.default_language == 'en'
            assert settings.multilingual.supported_languages == ['en', 'ru', 'ar']
    
    def test_environment_validation(self):
        """Test environment validation."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql+asyncpg://test:test@localhost:5432/test',
            'OPENAI_API_KEY': 'test-key',
            'TELEGRAM_BOT_TOKEN': 'test-token',
            'SECRET_KEY': 'test-secret',
            'ENVIRONMENT': 'invalid'
        }):
            with pytest.raises(ValueError):
                Settings()
    
    def test_get_settings(self):
        """Test get_settings function."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql+asyncpg://test:test@localhost:5432/test',
            'OPENAI_API_KEY': 'test-key',
            'TELEGRAM_BOT_TOKEN': 'test-token',
            'SECRET_KEY': 'test-secret'
        }):
            settings = get_settings()
            assert isinstance(settings, Settings)
            assert settings.environment == "development"