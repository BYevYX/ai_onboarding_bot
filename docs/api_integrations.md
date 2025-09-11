# API и интеграции Telegram-бота для онбординга

## Внешние API интеграции

### 1. Telegram Bot API

#### Основные методы Telegram API
```python
# Отправка сообщений
async def send_message(
    chat_id: int,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML"
) -> Message

# Отправка документов
async def send_document(
    chat_id: int,
    document: InputFile,
    caption: Optional[str] = None
) -> Message

# Редактирование сообщений
async def edit_message_text(
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None
) -> Message
```

### 2. OpenAI ChatGPT API

#### Конфигурация клиента
```python
from openai import AsyncOpenAI

class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = 4000
        self.temperature = 0.7
```

#### Методы интеграции
```python
# Генерация ответов
async def generate_response(
    self,
    messages: List[Dict[str, str]],
    context: Optional[str] = None,
    language: str = "ru"
) -> str:
    """
    Генерация ответа на основе контекста и истории диалога
    """
    
# Создание embeddings
async def create_embeddings(
    self,
    texts: List[str],
    model: str = "text-embedding-ada-002"
) -> List[List[float]]:
    """
    Создание векторных представлений для текстов
    """

# Анализ намерений
async def analyze_intent(
    self,
    message: str,
    language: str = "ru"
) -> Dict[str, Any]:
    """
    Анализ намерений пользователя
    """
```

### 3. Translation API (Google Translate)

#### Конфигурация
```python
from googletrans import Translator
from langdetect import detect

class TranslationService:
    def __init__(self):
        self.translator = Translator()
        self.supported_languages = ["ru", "en", "ar"]
        self.default_language = "ru"
```

#### Методы перевода
```python
# Определение языка
async def detect_language(self, text: str) -> str:
    """
    Автоматическое определение языка текста
    """

# Перевод текста
async def translate_text(
    self,
    text: str,
    target_language: str,
    source_language: Optional[str] = None
) -> Dict[str, str]:
    """
    Перевод текста на целевой язык
    """

# Массовый перевод
async def translate_batch(
    self,
    texts: List[str],
    target_language: str
) -> List[Dict[str, str]]:
    """
    Перевод множества текстов
    """
```

### 4. Qdrant Vector Database API

#### Конфигурация клиента
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

class QdrantService:
    def __init__(self, host: str, port: int, api_key: Optional[str] = None):
        self.client = QdrantClient(host=host, port=port, api_key=api_key)
        self.collection_name = "documents"
        self.vector_size = 1536  # OpenAI embedding size
```

#### Методы работы с векторами
```python
# Создание коллекции
async def create_collection(self) -> bool:
    """
    Создание коллекции для хранения векторов
    """

# Добавление векторов
async def add_vectors(
    self,
    points: List[Dict[str, Any]]
) -> bool:
    """
    Добавление векторных представлений документов
    """

# Поиск похожих векторов
async def search_similar(
    self,
    query_vector: List[float],
    limit: int = 10,
    score_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Поиск похожих документов по векторному представлению
    """
```

## Внутренние API эндпоинты

### 1. User Management API

```python
# GET /api/v1/users
async def get_users(
    skip: int = 0,
    limit: int = 100,
    department: Optional[str] = None,
    role: Optional[str] = None
) -> List[UserResponse]

# GET /api/v1/users/{user_id}
async def get_user(user_id: int) -> UserResponse

# POST /api/v1/users
async def create_user(user: UserCreate) -> UserResponse

# PUT /api/v1/users/{user_id}
async def update_user(user_id: int, user: UserUpdate) -> UserResponse

# DELETE /api/v1/users/{user_id}
async def delete_user(user_id: int) -> Dict[str, str]

# POST /api/v1/users/{user_id}/roles
async def assign_role(user_id: int, role_assignment: RoleAssignment) -> UserResponse
```

### 2. Document Management API

```python
# GET /api/v1/documents
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    language: Optional[str] = None,
    search: Optional[str] = None
) -> List[DocumentResponse]

# GET /api/v1/documents/{document_id}
async def get_document(document_id: int) -> DocumentResponse

# POST /api/v1/documents
async def upload_document(
    file: UploadFile,
    metadata: DocumentMetadata
) -> DocumentResponse

# PUT /api/v1/documents/{document_id}
async def update_document(
    document_id: int,
    document: DocumentUpdate
) -> DocumentResponse

# DELETE /api/v1/documents/{document_id}
async def delete_document(document_id: int) -> Dict[str, str]

# POST /api/v1/documents/{document_id}/reindex
async def reindex_document(document_id: int) -> Dict[str, str]
```

### 3. Search API

```python
# POST /api/v1/search
async def search_documents(
    query: SearchQuery
) -> SearchResponse

# POST /api/v1/search/semantic
async def semantic_search(
    query: SemanticSearchQuery
) -> SearchResponse

# GET /api/v1/search/suggestions
async def get_search_suggestions(
    q: str,
    language: str = "ru"
) -> List[str]
```

### 4. Analytics API

```python
# GET /api/v1/analytics/usage
async def get_usage_analytics(
    start_date: datetime,
    end_date: datetime,
    granularity: str = "day"
) -> AnalyticsResponse

# GET /api/v1/analytics/users
async def get_user_analytics(
    user_id: Optional[int] = None,
    department: Optional[str] = None
) -> UserAnalyticsResponse

# GET /api/v1/analytics/documents
async def get_document_analytics(
    document_id: Optional[int] = None,
    category: Optional[str] = None
) -> DocumentAnalyticsResponse

# POST /api/v1/analytics/events
async def track_event(event: AnalyticsEvent) -> Dict[str, str]
```

## Pydantic схемы для API

### User Schemas
```python
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    language_code: str = "ru"
    department: Optional[str] = None
    position: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    language_code: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    onboarding_completed: bool
    roles: List[str]
    created_at: datetime
    last_activity: datetime

    class Config:
        from_attributes = True
```

### Document Schemas
```python
class DocumentBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    language: str = "ru"
    is_public: bool = False
    access_level: str = "employee"

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None
    access_level: Optional[str] = None

class DocumentResponse(DocumentBase):
    id: int
    file_name: str
    file_size: int
    file_type: str
    version: int
    is_active: bool
    uploaded_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### Search Schemas
```python
class SearchQuery(BaseModel):
    query: str
    language: Optional[str] = "ru"
    category: Optional[str] = None
    limit: int = 10
    offset: int = 0

class SemanticSearchQuery(BaseModel):
    query: str
    language: Optional[str] = "ru"
    similarity_threshold: float = 0.7
    limit: int = 10

class SearchResult(BaseModel):
    document_id: int
    title: str
    content_snippet: str
    score: float
    category: Optional[str] = None
    language: str

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_count: int
    processing_time_ms: int
```

## Middleware и безопасность

### Authentication Middleware
```python
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Проверка JWT токена
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )
```

### Rate Limiting Middleware
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Применение rate limiting
@limiter.limit("100/minute")
async def search_documents(
    request: Request,
    query: SearchQuery
) -> SearchResponse:
    pass
```

### CORS Configuration
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-admin-panel.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## WebSocket для real-time обновлений

### WebSocket Manager
```python
from fastapi import WebSocket
from typing import List, Dict

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.user_connections[user_id] = websocket

    def disconnect(self, websocket: WebSocket, user_id: int):
        self.active_connections.remove(websocket)
        if user_id in self.user_connections:
            del self.user_connections[user_id]

    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.user_connections:
            await self.user_connections[user_id].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
```

### WebSocket Endpoints
```python
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Обработка входящих сообщений
            await process_websocket_message(data, user_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
```

## Мониторинг API

### Health Check Endpoints
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

@app.get("/health/detailed")
async def detailed_health_check():
    return {
        "status": "healthy",
        "services": {
            "database": await check_database_health(),
            "redis": await check_redis_health(),
            "qdrant": await check_qdrant_health(),
            "openai": await check_openai_health()
        },
        "timestamp": datetime.utcnow()
    }
```

### Metrics Endpoint
```python
# Внутренние метрики (без prometheus)
class MetricsCollector:
    def __init__(self):
        self.request_count = {}
        self.request_durations = []
    
    def increment_request_count(self, method: str, endpoint: str):
        key = f"{method}:{endpoint}"
        self.request_count[key] = self.request_count.get(key, 0) + 1
    
    def record_request_duration(self, duration: float):
        self.request_durations.append(duration)

metrics_collector = MetricsCollector()

@app.get("/metrics")
async def get_metrics():
    return {
        "request_counts": metrics_collector.request_count,
        "avg_request_duration": sum(metrics_collector.request_durations) / len(metrics_collector.request_durations) if metrics_collector.request_durations else 0,
        "total_requests": sum(metrics_collector.request_count.values())
    }
```

## Error Handling

### Custom Exception Handlers
```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

class CustomException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )
```

## API Documentation

### OpenAPI Configuration
```python
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Telegram Onboarding Bot API",
        version="1.0.0",
        description="API для управления Telegram-ботом онбординга сотрудников",
        routes=app.routes,
    )
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi