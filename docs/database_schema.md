# Схема базы данных Telegram-бота для онбординга

## Обзор базы данных

Система использует PostgreSQL как основную реляционную базу данных, Redis для кэширования и Qdrant для векторного поиска.

## PostgreSQL Schema

### 1. Таблица пользователей (users)

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    language_code VARCHAR(10) DEFAULT 'ru',
    preferred_language VARCHAR(10) DEFAULT 'ru',
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    department VARCHAR(255),
    position VARCHAR(255),
    hire_date DATE,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    onboarding_progress JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_department ON users(department);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_last_activity ON users(last_activity);
```

### 2. Таблица ролей (roles)

```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Предустановленные роли
INSERT INTO roles (name, display_name, description, permissions) VALUES
('super_admin', 'Супер Администратор', 'Полный доступ к системе', '["*"]'),
('admin', 'Администратор', 'Управление пользователями и документами', '["users.*", "documents.*", "analytics.read"]'),
('hr_manager', 'HR Менеджер', 'Управление онбордингом сотрудников', '["users.read", "users.update", "documents.read", "onboarding.*"]'),
('employee', 'Сотрудник', 'Базовый доступ к боту', '["documents.read", "search.*", "profile.*"]');
```

### 3. Таблица связи пользователей и ролей (user_roles)

```sql
CREATE TABLE user_roles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_by BIGINT REFERENCES users(id),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    
    UNIQUE(user_id, role_id)
);

-- Индексы
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles(role_id);
```

### 4. Таблица документов (documents)

```sql
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    file_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    mime_type VARCHAR(100),
    language VARCHAR(10) DEFAULT 'ru',
    category VARCHAR(100),
    tags TEXT[],
    content_hash VARCHAR(64) UNIQUE,
    processed_content TEXT,
    metadata JSONB DEFAULT '{}',
    version INTEGER DEFAULT 1,
    parent_document_id BIGINT REFERENCES documents(id),
    is_active BOOLEAN DEFAULT TRUE,
    is_public BOOLEAN DEFAULT FALSE,
    access_level VARCHAR(50) DEFAULT 'employee',
    uploaded_by BIGINT NOT NULL REFERENCES users(id),
    approved_by BIGINT REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    indexed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_language ON documents(language);
CREATE INDEX idx_documents_is_active ON documents(is_active);
CREATE INDEX idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX idx_documents_content_hash ON documents(content_hash);
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);
```

### 5. Таблица чанков документов (document_chunks)

```sql
CREATE TABLE document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_length INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding_id VARCHAR(255), -- ID в векторной БД
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(document_id, chunk_index)
);

-- Индексы
CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_document_chunks_embedding_id ON document_chunks(embedding_id);
```

### 6. Таблица диалогов (conversations)

```sql
CREATE TABLE conversations (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,
    context JSONB DEFAULT '{}',
    language VARCHAR(10) DEFAULT 'ru',
    is_active BOOLEAN DEFAULT TRUE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE
);

-- Индексы
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_conversations_is_active ON conversations(is_active);
```

### 7. Таблица сообщений (messages)

```sql
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL, -- 'user', 'bot', 'system'
    content TEXT NOT NULL,
    original_content TEXT, -- Оригинальный текст до перевода
    language VARCHAR(10),
    metadata JSONB DEFAULT '{}',
    telegram_message_id INTEGER,
    is_translated BOOLEAN DEFAULT FALSE,
    processing_time_ms INTEGER,
    tokens_used INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_message_type ON messages(message_type);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

### 8. Таблица поисковых запросов (search_queries)

```sql
CREATE TABLE search_queries (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    original_query TEXT, -- Оригинальный запрос до перевода
    language VARCHAR(10),
    results_count INTEGER DEFAULT 0,
    response_time_ms INTEGER,
    found_documents BIGINT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_search_queries_user_id ON search_queries(user_id);
CREATE INDEX idx_search_queries_created_at ON search_queries(created_at);
CREATE INDEX idx_search_queries_found_documents ON search_queries USING GIN(found_documents);
```

### 9. Таблица доступа к документам (document_access)

```sql
CREATE TABLE document_access (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    department VARCHAR(255),
    access_type VARCHAR(50) NOT NULL, -- 'read', 'write', 'admin'
    granted_by BIGINT REFERENCES users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    
    CHECK (user_id IS NOT NULL OR role_id IS NOT NULL OR department IS NOT NULL)
);

-- Индексы
CREATE INDEX idx_document_access_document_id ON document_access(document_id);
CREATE INDEX idx_document_access_user_id ON document_access(user_id);
CREATE INDEX idx_document_access_role_id ON document_access(role_id);
CREATE INDEX idx_document_access_department ON document_access(department);
```

### 10. Таблица аналитики (analytics_events)

```sql
CREATE TABLE analytics_events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB DEFAULT '{}',
    session_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_analytics_events_user_id ON analytics_events(user_id);
CREATE INDEX idx_analytics_events_event_type ON analytics_events(event_type);
CREATE INDEX idx_analytics_events_created_at ON analytics_events(created_at);
CREATE INDEX idx_analytics_events_session_id ON analytics_events(session_id);
```

### 11. Таблица кэша (cache_entries)

```sql
CREATE TABLE cache_entries (
    id BIGSERIAL PRIMARY KEY,
    cache_key VARCHAR(500) UNIQUE NOT NULL,
    cache_value JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    access_count INTEGER DEFAULT 1
);

-- Индексы
CREATE INDEX idx_cache_entries_cache_key ON cache_entries(cache_key);
CREATE INDEX idx_cache_entries_expires_at ON cache_entries(expires_at);
```

### 12. Таблица системных настроек (system_settings)

```sql
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    updated_by BIGINT REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Предустановленные настройки
INSERT INTO system_settings (key, value, description, is_public) VALUES
('bot_welcome_message', '{"ru": "Добро пожаловать!", "en": "Welcome!", "ar": "أهلا وسهلا!"}', 'Приветственное сообщение бота', true),
('max_file_size_mb', '50', 'Максимальный размер загружаемого файла в МБ', false),
('supported_file_types', '["pdf", "docx", "txt"]', 'Поддерживаемые типы файлов', true),
('rag_chunk_size', '1000', 'Размер чанка для RAG', false),
('rag_chunk_overlap', '200', 'Перекрытие чанков для RAG', false);
```

## Redis Schema

### Структура кэша в Redis

```
# Пользовательские сессии
user_session:{telegram_id} -> {
    "user_id": 123,
    "language": "ru",
    "context": {...},
    "last_activity": "2024-01-01T12:00:00Z"
}

# Кэш переводов
translation:{hash} -> {
    "original": "Hello",
    "translated": "Привет",
    "from_lang": "en",
    "to_lang": "ru",
    "cached_at": "2024-01-01T12:00:00Z"
}

# Кэш поисковых запросов
search_cache:{query_hash} -> {
    "query": "как подключиться к VPN",
    "results": [...],
    "language": "ru",
    "cached_at": "2024-01-01T12:00:00Z"
}

# Кэш документов
document_cache:{document_id} -> {
    "content": "...",
    "metadata": {...},
    "cached_at": "2024-01-01T12:00:00Z"
}

# Rate limiting
rate_limit:{user_id}:{action} -> {
    "count": 5,
    "reset_at": "2024-01-01T12:01:00Z"
}

# Активные диалоги
active_conversation:{user_id} -> {
    "conversation_id": 123,
    "context": {...},
    "started_at": "2024-01-01T12:00:00Z"
}
```

## Qdrant Vector Database Schema

### Коллекции в Qdrant

```python
# Коллекция для embeddings документов
collection_name = "documents"
vector_config = {
    "size": 1536,  # Размер embedding от OpenAI
    "distance": "Cosine"
}

# Структура точки в Qdrant
point = {
    "id": "doc_123_chunk_1",
    "vector": [0.1, 0.2, ...],  # 1536 размерность
    "payload": {
        "document_id": 123,
        "chunk_index": 1,
        "content": "Текст чанка...",
        "language": "ru",
        "category": "hr",
        "metadata": {...}
    }
}
```

## Миграции и версионирование

### Alembic конфигурация

```python
# alembic/env.py
from app.models import Base
from app.config.database import DATABASE_URL

config.set_main_option("sqlalchemy.url", DATABASE_URL)
target_metadata = Base.metadata
```

### Пример миграции

```python
# alembic/versions/001_initial_schema.py
"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Создание всех таблиц
    op.create_table('users', ...)
    op.create_table('roles', ...)
    # ... остальные таблицы

def downgrade():
    # Удаление таблиц в обратном порядке
    op.drop_table('analytics_events')
    # ... остальные таблицы
```

## Индексы и оптимизация

### Составные индексы

```sql
-- Для быстрого поиска активных пользователей по департаменту
CREATE INDEX idx_users_department_active ON users(department, is_active) 
WHERE is_active = true;

-- Для поиска документов по категории и языку
CREATE INDEX idx_documents_category_language_active ON documents(category, language, is_active) 
WHERE is_active = true;

-- Для аналитики по времени и типу события
CREATE INDEX idx_analytics_events_type_time ON analytics_events(event_type, created_at DESC);
```

### Партиционирование

```sql
-- Партиционирование таблицы сообщений по времени
CREATE TABLE messages_y2024m01 PARTITION OF messages
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE messages_y2024m02 PARTITION OF messages
FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
```

## Backup и восстановление

### Стратегия резервного копирования

```bash
# Ежедневный backup PostgreSQL
pg_dump -h localhost -U postgres -d onboarding_bot > backup_$(date +%Y%m%d).sql

# Backup Redis
redis-cli --rdb backup_redis_$(date +%Y%m%d).rdb

# Backup Qdrant
curl -X POST "http://localhost:6333/collections/documents/snapshots"
```

## Мониторинг производительности

### Ключевые метрики

```sql
-- Медленные запросы
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Размер таблиц
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Использование индексов
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;