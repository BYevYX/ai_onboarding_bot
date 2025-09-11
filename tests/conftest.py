"""
Pytest configuration and fixtures.
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base
from app.core.config import get_settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_factory() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = MagicMock()
    settings.openai.api_key = "test-api-key"
    settings.openai.model = "gpt-4-turbo-preview"
    settings.openai.embedding_model = "text-embedding-3-small"
    settings.openai.temperature = 0.7
    settings.openai.max_tokens = 4000
    
    settings.qdrant.url = "http://localhost:6333"
    settings.qdrant.api_key = None
    settings.qdrant.collection_name = "test_collection"
    settings.qdrant.vector_size = 1536
    
    settings.redis.url = "redis://localhost:6379/0"
    settings.redis.max_connections = 10
    
    settings.telegram.bot_token = "test-bot-token"
    
    settings.cache.ttl = 3600
    settings.cache.max_size = 1000
    
    settings.multilingual.default_language = "ru"
    settings.multilingual.supported_languages = ["ru", "en", "ar"]
    
    return settings


@pytest.fixture
def mock_llm_manager():
    """Mock LLM manager."""
    manager = AsyncMock()
    manager.generate_response.return_value = "Test AI response"
    manager.generate_embeddings.return_value = [[0.1] * 1536]
    manager.generate_single_embedding.return_value = [0.1] * 1536
    return manager


@pytest.fixture
def mock_vector_store():
    """Mock vector store."""
    store = AsyncMock()
    store.initialize_collection.return_value = True
    store.add_documents.return_value = ["doc-id-1", "doc-id-2"]
    store.similarity_search.return_value = []
    store.delete_documents.return_value = True
    return store


@pytest.fixture
def mock_onboarding_workflow():
    """Mock onboarding workflow."""
    workflow = AsyncMock()
    workflow.run_workflow.return_value = {
        "user_id": 1,
        "telegram_id": 123456789,
        "stage": "completed",
        "completion_score": 100.0,
        "messages": [],
        "documents_reviewed": ["doc1", "doc2"],
        "questions_asked": ["q1", "q2"],
        "language": "ru"
    }
    return workflow


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "telegram_id": 123456789,
        "username": "test_user",
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "phone": "+1234567890",
        "position": "Developer",
        "department": "IT",
        "language": "ru"
    }


@pytest.fixture
def sample_document_data():
    """Sample document data for testing."""
    return {
        "title": "Test Document",
        "filename": "test.pdf",
        "document_type": "handbook",
        "department": "IT",
        "language": "ru",
        "content": "This is a test document content."
    }


@pytest.fixture
def sample_onboarding_data():
    """Sample onboarding data for testing."""
    return {
        "user_id": 1,
        "telegram_id": 123456789,
        "language": "ru",
        "user_info": {
            "name": "Test User",
            "position": "Developer",
            "department": "IT",
            "start_date": "2024-01-15"
        }
    }


@pytest.fixture
def mock_telegram_message():
    """Mock Telegram message."""
    message = MagicMock()
    message.from_user.id = 123456789
    message.from_user.username = "test_user"
    message.from_user.first_name = "Test"
    message.from_user.last_name = "User"
    message.text = "Test message"
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_telegram_callback():
    """Mock Telegram callback query."""
    callback = MagicMock()
    callback.from_user.id = 123456789
    callback.from_user.username = "test_user"
    callback.data = "test_callback_data"
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback