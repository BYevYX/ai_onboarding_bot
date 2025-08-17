# Стратегия тестирования и CI/CD

## Обзор стратегии тестирования

Комплексная стратегия тестирования включает unit-тесты, интеграционные тесты, end-to-end тесты и автоматизированный CI/CD пайплайн с использованием GitHub Actions.

## Пирамида тестирования

```mermaid
graph TB
    subgraph "Test Pyramid"
        E2E[End-to-End Tests<br/>~10%]
        INT[Integration Tests<br/>~30%]
        UNIT[Unit Tests<br/>~60%]
    end
    
    subgraph "Test Types"
        UT[Unit Tests]
        IT[Integration Tests]
        CT[Contract Tests]
        PT[Performance Tests]
        ST[Security Tests]
        E2ET[E2E Tests]
    end
    
    subgraph "CI/CD Pipeline"
        BUILD[Build & Lint]
        TEST[Run Tests]
        SEC[Security Scan]
        DEPLOY[Deploy]
        MONITOR[Monitor]
    end
    
    UNIT --> UT
    INT --> IT
    INT --> CT
    E2E --> E2ET
    
    BUILD --> TEST
    TEST --> SEC
    SEC --> DEPLOY
    DEPLOY --> MONITOR
```

## Структура тестов

### 1. Unit Tests

#### Конфигурация pytest
```python
# tests/conftest.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config.database import Base
from app.models import User, Document, Role
from app.services.cache_service import CacheService
from app.services.translation_service import TranslationService

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine):
    """Create test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
def mock_cache_service():
    """Mock cache service."""
    cache_service = MagicMock(spec=CacheService)
    cache_service.get = AsyncMock(return_value=None)
    cache_service.set = AsyncMock(return_value=True)
    cache_service.delete = AsyncMock(return_value=True)
    return cache_service

@pytest.fixture
def mock_translation_service():
    """Mock translation service."""
    translation_service = MagicMock(spec=TranslationService)
    translation_service.translate_text = AsyncMock(return_value={
        "translated_text": "Hello",
        "source_language": "ru",
        "target_language": "en",
        "provider": "mock"
    })
    translation_service.detect_language = AsyncMock(return_value={
        "language": "ru",
        "confidence": 0.9
    })
    return translation_service

@pytest.fixture
async def test_user(db_session):
    """Create test user."""
    user = User(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        email="test@example.com",
        language_code="ru",
        department="IT",
        position="Developer"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def test_document(db_session, test_user):
    """Create test document."""
    document = Document(
        title="Test Document",
        description="Test document description",
        file_name="test.pdf",
        file_path="/test/path/test.pdf",
        file_size=1024,
        file_type="pdf",
        mime_type="application/pdf",
        content_hash="test_hash",
        language="ru",
        category="test",
        uploaded_by=test_user.id
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document
```

#### Unit тесты для сервисов
```python
# tests/unit/test_services/test_user_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.auth_service import AuthService
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

class TestAuthService:
    
    @pytest.fixture
    def auth_service(self, db_session, mock_cache_service):
        return AuthService(db_session, mock_cache_service)
    
    async def test_create_user_success(self, auth_service, db_session):
        """Test successful user creation."""
        user_data = UserCreate(
            telegram_id=987654321,
            username="newuser",
            first_name="New",
            last_name="User",
            email="new@example.com"
        )
        
        user = await auth_service.create_user(user_data)
        
        assert user.telegram_id == 987654321
        assert user.username == "newuser"
        assert user.is_active is True
        assert user.onboarding_completed is False
    
    async def test_create_user_duplicate_telegram_id(self, auth_service, test_user):
        """Test user creation with duplicate telegram_id."""
        user_data = UserCreate(
            telegram_id=test_user.telegram_id,
            username="duplicate",
            first_name="Duplicate",
            last_name="User"
        )
        
        with pytest.raises(ValueError, match="User with this telegram_id already exists"):
            await auth_service.create_user(user_data)
    
    async def test_get_user_by_telegram_id(self, auth_service, test_user):
        """Test getting user by telegram_id."""
        user = await auth_service.get_user_by_telegram_id(test_user.telegram_id)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.telegram_id == test_user.telegram_id
    
    async def test_update_user(self, auth_service, test_user):
        """Test user update."""
        update_data = UserUpdate(
            first_name="Updated",
            department="HR"
        )
        
        updated_user = await auth_service.update_user(test_user.id, update_data)
        
        assert updated_user.first_name == "Updated"
        assert updated_user.department == "HR"
        assert updated_user.last_name == test_user.last_name  # Unchanged
    
    async def test_user_permissions_caching(self, auth_service, test_user, mock_cache_service):
        """Test user permissions caching."""
        # Mock cache miss, then hit
        mock_cache_service.get.side_effect = [None, ["documents.read"]]
        
        # First call - cache miss
        permissions = await auth_service.get_user_permissions(test_user.id)
        assert mock_cache_service.set.called
        
        # Second call - cache hit
        permissions = await auth_service.get_user_permissions(test_user.id)
        assert permissions == ["documents.read"]
```

#### Unit тесты для RAG системы
```python
# tests/unit/test_services/test_rag_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.rag_service import RAGService
from app.ai.embeddings.generator import EmbeddingService
from app.ai.rag.retriever import VectorSearchService

class TestRAGService:
    
    @pytest.fixture
    def mock_embedding_service(self):
        service = MagicMock(spec=EmbeddingService)
        service.generate_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
        return service
    
    @pytest.fixture
    def mock_vector_search(self):
        service = MagicMock(spec=VectorSearchService)
        service.search_similar_chunks = AsyncMock(return_value=[
            {
                "id": "doc_1_chunk_1",
                "score": 0.9,
                "content": "Test content",
                "document_id": 1,
                "metadata": {"category": "test"}
            }
        ])
        return service
    
    @pytest.fixture
    def rag_service(self, mock_embedding_service, mock_vector_search, mock_cache_service):
        return RAGService(
            embedding_service=mock_embedding_service,
            vector_search_service=mock_vector_search,
            cache_service=mock_cache_service
        )
    
    async def test_process_query_success(self, rag_service, test_user):
        """Test successful query processing."""
        query = "What is the company policy?"
        
        with patch('app.services.rag_service.QueryProcessor') as mock_processor:
            mock_processor.return_value.process_query = AsyncMock(return_value={
                "original_query": query,
                "language": "en",
                "expanded_query": "company policy guidelines",
                "keywords": ["company", "policy"]
            })
            
            with patch('app.services.rag_service.RAGResponseGenerator') as mock_generator:
                mock_generator.return_value.generate_response = AsyncMock(return_value={
                    "response": "The company policy states...",
                    "confidence": 0.85,
                    "sources": ["Document 1"]
                })
                
                result = await rag_service.process_query(query, test_user)
                
                assert "response" in result
                assert result["response"] == "The company policy states..."
                assert result["confidence"] == 0.85
                assert "processing_time_ms" in result
    
    async def test_process_query_with_cache(self, rag_service, test_user, mock_cache_service):
        """Test query processing with cache hit."""
        query = "Cached query"
        cached_result = {
            "response": "Cached response",
            "confidence": 0.9,
            "sources": ["Cached source"]
        }
        
        mock_cache_service.get.return_value = cached_result
        
        result = await rag_service.process_query(query, test_user)
        
        assert result == cached_result
        mock_cache_service.get.assert_called_once()
    
    async def test_process_query_error_handling(self, rag_service, test_user):
        """Test error handling in query processing."""
        query = "Error query"
        
        with patch('app.services.rag_service.QueryProcessor') as mock_processor:
            mock_processor.return_value.process_query = AsyncMock(
                side_effect=Exception("Processing error")
            )
            
            result = await rag_service.process_query(query, test_user)
            
            assert "error" in result
            assert "processing_time_ms" in result
            assert "Извините, произошла ошибка" in result["response"]
```

### 2. Integration Tests

#### Тесты API эндпоинтов
```python
# tests/integration/test_api/test_user_endpoints.py
import pytest
from httpx import AsyncClient
from app.main import app
from app.core.security import create_access_token

class TestUserEndpoints:
    
    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.fixture
    def auth_headers(self, test_user):
        token = create_access_token(data={"sub": str(test_user.id)})
        return {"Authorization": f"Bearer {token}"}
    
    async def test_get_users_unauthorized(self, client):
        """Test getting users without authentication."""
        response = await client.get("/api/v1/users")
        assert response.status_code == 401
    
    async def test_get_users_authorized(self, client, auth_headers):
        """Test getting users with authentication."""
        response = await client.get("/api/v1/users", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    async def test_get_user_by_id(self, client, auth_headers, test_user):
        """Test getting specific user."""
        response = await client.get(f"/api/v1/users/{test_user.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_user.id
        assert data["telegram_id"] == test_user.telegram_id
    
    async def test_create_user(self, client, auth_headers):
        """Test user creation."""
        user_data = {
            "telegram_id": 111222333,
            "username": "apiuser",
            "first_name": "API",
            "last_name": "User",
            "email": "api@example.com"
        }
        
        response = await client.post("/api/v1/users", json=user_data, headers=auth_headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["telegram_id"] == 111222333
        assert data["username"] == "apiuser"
    
    async def test_update_user(self, client, auth_headers, test_user):
        """Test user update."""
        update_data = {
            "first_name": "Updated API",
            "department": "Marketing"
        }
        
        response = await client.put(
            f"/api/v1/users/{test_user.id}", 
            json=update_data, 
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["first_name"] == "Updated API"
        assert data["department"] == "Marketing"
```

#### Тесты базы данных
```python
# tests/integration/test_database/test_repositories.py
import pytest
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.document_repository import DocumentRepository

class TestUserRepository:
    
    @pytest.fixture
    def user_repo(self, db_session):
        return UserRepository(db_session)
    
    async def test_create_and_get_user(self, user_repo):
        """Test user creation and retrieval."""
        user_data = {
            "telegram_id": 555666777,
            "username": "repouser",
            "first_name": "Repo",
            "last_name": "User"
        }
        
        # Create user
        user = await user_repo.create(user_data)
        assert user.id is not None
        assert user.telegram_id == 555666777
        
        # Get user by ID
        retrieved_user = await user_repo.get_by_id(user.id)
        assert retrieved_user is not None
        assert retrieved_user.telegram_id == 555666777
        
        # Get user by telegram_id
        telegram_user = await user_repo.get_by_telegram_id(555666777)
        assert telegram_user is not None
        assert telegram_user.id == user.id
    
    async def test_update_user(self, user_repo, test_user):
        """Test user update."""
        update_data = {"department": "Updated Department"}
        
        updated_user = await user_repo.update(test_user.id, update_data)
        assert updated_user.department == "Updated Department"
        
        # Verify in database
        db_user = await user_repo.get_by_id(test_user.id)
        assert db_user.department == "Updated Department"
    
    async def test_get_users_with_filters(self, user_repo, test_user):
        """Test getting users with filters."""
        # Create additional test user
        await user_repo.create({
            "telegram_id": 888999000,
            "username": "filteruser",
            "first_name": "Filter",
            "department": "HR"
        })
        
        # Filter by department
        hr_users = await user_repo.get_by_filters({"department": "HR"})
        assert len(hr_users) == 1
        assert hr_users[0].department == "HR"
        
        # Filter by active status
        active_users = await user_repo.get_by_filters({"is_active": True})
        assert len(active_users) >= 2  # At least our test users

class TestDocumentRepository:
    
    @pytest.fixture
    def doc_repo(self, db_session):
        return DocumentRepository(db_session)
    
    async def test_create_and_search_documents(self, doc_repo, test_user):
        """Test document creation and search."""
        doc_data = {
            "title": "Integration Test Document",
            "description": "Test document for integration testing",
            "file_name": "integration_test.pdf",
            "file_path": "/test/integration_test.pdf",
            "file_size": 2048,
            "file_type": "pdf",
            "content_hash": "integration_hash",
            "category": "testing",
            "uploaded_by": test_user.id
        }
        
        # Create document
        document = await doc_repo.create(doc_data)
        assert document.id is not None
        assert document.title == "Integration Test Document"
        
        # Search by category
        test_docs = await doc_repo.search({"category": "testing"})
        assert len(test_docs) >= 1
        assert any(doc.id == document.id for doc in test_docs)
        
        # Search by title
        title_docs = await doc_repo.search({"title": "Integration"})
        assert len(title_docs) >= 1
```

### 3. End-to-End Tests

#### Telegram Bot E2E тесты
```python
# tests/e2e/test_bot_flow.py
import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import Update, Message, User as TelegramUser, Chat
from app.bot.main import bot, dp

class TestBotE2E:
    
    @pytest.fixture
    def telegram_user(self):
        return TelegramUser(
            id=123456789,
            is_bot=False,
            first_name="Test",
            last_name="User",
            username="testuser"
        )
    
    @pytest.fixture
    def chat(self):
        return Chat(id=123456789, type="private")
    
    async def test_start_command_new_user(self, telegram_user, chat):
        """Test /start command for new user."""
        message = Message(
            message_id=1,
            date=1234567890,
            chat=chat,
            from_user=telegram_user,
            text="/start"
        )
        
        update = Update(update_id=1, message=message)
        
        with patch('app.services.auth_service.AuthService.get_user_by_telegram_id') as mock_get_user:
            mock_get_user.return_value = None
            
            with patch('app.services.auth_service.AuthService.create_user') as mock_create_user:
                mock_create_user.return_value = AsyncMock()
                
                with patch.object(bot, 'send_message') as mock_send:
                    await dp.feed_update(bot, update)
                    
                    mock_create_user.assert_called_once()
                    mock_send.assert_called_once()
                    
                    # Check welcome message
                    call_args = mock_send.call_args
                    assert "Добро пожаловать" in call_args[1]['text']
    
    async def test_search_flow(self, telegram_user, chat, test_user):
        """Test search functionality flow."""
        # Search command
        search_message = Message(
            message_id=2,
            date=1234567890,
            chat=chat,
            from_user=telegram_user,
            text="Как подключиться к VPN?"
        )
        
        update = Update(update_id=2, message=search_message)
        
        with patch('app.services.auth_service.AuthService.get_user_by_telegram_id') as mock_get_user:
            mock_get_user.return_value = test_user
            
            with patch('app.services.rag_service.RAGService.process_query') as mock_rag:
                mock_rag.return_value = {
                    "response": "Для подключения к VPN...",
                    "confidence": 0.9,
                    "sources": ["VPN Guide"]
                }
                
                with patch.object(bot, 'send_message') as mock_send:
                    await dp.feed_update(bot, update)
                    
                    mock_rag.assert_called_once()
                    mock_send.assert_called_once()
                    
                    # Check response
                    call_args = mock_send.call_args
                    assert "Для подключения к VPN" in call_args[1]['text']
    
    async def test_document_upload_flow(self, telegram_user, chat, test_user):
        """Test document upload flow."""
        # Mock document message
        document_message = Message(
            message_id=3,
            date=1234567890,
            chat=chat,
            from_user=telegram_user,
            document=AsyncMock()
        )
        
        update = Update(update_id=3, message=document_message)
        
        with patch('app.services.auth_service.AuthService.get_user_by_telegram_id') as mock_get_user:
            mock_get_user.return_value = test_user
            
            with patch('app.services.document_service.DocumentService.upload_document') as mock_upload:
                mock_upload.return_value = {"status": "success", "document_id": 1}
                
                with patch.object(bot, 'send_message') as mock_send:
                    await dp.feed_update(bot, update)
                    
                    mock_upload.assert_called_once()
                    mock_send.assert_called_once()
```

### 4. Performance Tests

#### Load Testing с Locust
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import random

class TelegramBotUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login and get auth token."""
        response = self.client.post("/api/v1/auth/login", json={
            "telegram_id": random.randint(100000, 999999),
            "username": f"testuser_{random.randint(1, 1000)}"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}
    
    @task(3)
    def search_documents(self):
        """Test search functionality."""
        queries = [
            "company policy",
            "vacation request",
            "IT support",
            "HR procedures",
            "security guidelines"
        ]
        
        query = random.choice(queries)
        self.client.post(
            "/api/v1/search",
            json={"query": query, "limit": 10},
            headers=self.headers
        )
    
    @task(2)
    def get_documents(self):
        """Test document listing."""
        self.client.get(
            "/api/v1/documents",
            params={"limit": 20, "offset": 0},
            headers=self.headers
        )
    
    @task(1)
    def get_user_profile(self):
        """Test user profile retrieval."""
        self.client.get("/api/v1/users/me", headers=self.headers)
    
    @task(1)
    def health_check(self):
        """Test health endpoint."""
        self.client.get("/health")

class AdminUser(HttpUser):
    wait_time = between(2, 5)
    weight = 1  # Lower weight for admin users
    
    def on_start(self):
        """Admin login."""
        response = self.client.post("/api/v1/auth/login", json={
            "telegram_id": 999999999,
            "username": "admin_user"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(2)
    def get_analytics(self):
        """Test analytics endpoints."""
        self.client.get("/api/v1/analytics/usage", headers=self.headers)
    
    @task(1)
    def manage_users(self):
        """Test user management."""
        self.client.get("/api/v1/users", headers=self.headers)
```

## CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '18'

jobs:
  lint-and-format:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements/dev.txt
    
    - name: Run black
      run: black --check app/ tests/
    
    - name: Run isort
      run: isort --check-only app/ tests/
    
    - name: Run flake8
      run: flake8 app/ tests/
    
    - name: Run mypy
      run: mypy app/

  test:
    runs-on: ubuntu-latest
    needs: lint-and-format
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements/test.txt
    
    - name: Run unit tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/0
      run: |
        pytest tests/unit/ -v --cov=app --cov-report=xml
    
    - name: Run integration tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/0
      run: |
        pytest tests/integration/ -v
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests

  security-scan:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements/prod.txt
        pip install safety bandit
    
    - name: Run safety check
      run: safety check
    
    - name: Run bandit security scan
      run: bandit -r app/ -f json -o bandit-report.json
    
    - name: Upload security scan results
      uses: actions/upload-artifact@v3
      with:
        name: security-scan-results
        path: bandit-report.json

  build-and-push:
    runs-on: ubuntu-latest
    needs: [test, security-scan]
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./docker/Dockerfile
        target: production
        push: true
        tags: |
          ${{ secrets.DOCKER_USERNAME }}/telegram-onboarding-bot:latest
          ${{ secrets.DOCKER_USERNAME }}/telegram-onboarding-bot:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy-staging:
    runs-on: ubuntu-latest
    needs: build-and-push
    if: github.ref == 'refs/heads/develop'
    environment: staging
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to staging
      run: |
        echo "Deploying to staging environment"
        # Add deployment script here
    
    - name: Run E2E tests
      run: |
        echo "Running E2E tests against staging"
        # Add E2E test execution

  deploy-production:
    runs-on: ubuntu-latest
    needs: build-and-push
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    -