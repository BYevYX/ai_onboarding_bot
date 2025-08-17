# LangChain и LangGraph зависимости

## Основные зависимости

### LangChain Core
```txt
# Основные компоненты LangChain
langchain==0.1.0
langchain-core==0.1.0
langchain-community==0.0.10

# LangGraph для создания workflows
langgraph==0.0.20

# LangChain интеграции
langchain-openai==0.0.5
langchain-qdrant==0.0.1
```

### AI/ML зависимости
```txt
# OpenAI
openai==1.6.1

# Embeddings и векторные операции
sentence-transformers==2.2.2
numpy==1.24.3
scipy==1.11.4

# Векторная база данных
qdrant-client==1.7.0

# Обработка текста
tiktoken==0.5.2
```

### Дополнительные LangChain компоненты
```txt
# Парсеры и форматтеры
langchain-experimental==0.0.50

# Кэширование для LangChain
langchain-cache==0.0.1

# Мониторинг и отладка
langsmith==0.0.70
```

## Полный requirements/langchain.txt

```txt
# LangChain Framework
langchain==0.1.0
langchain-core==0.1.0
langchain-community==0.0.10
langchain-experimental==0.0.50
langchain-openai==0.0.5
langchain-qdrant==0.0.1

# LangGraph для workflows
langgraph==0.0.20

# OpenAI интеграция
openai==1.6.1
tiktoken==0.5.2

# Векторные операции
sentence-transformers==2.2.2
numpy==1.24.3
scipy==1.11.4

# Векторная база данных
qdrant-client==1.7.0

# Мониторинг и отладка
langsmith==0.0.70

# Дополнительные утилиты
pydantic==2.5.0
typing-extensions==4.8.0
```

## Обновленный requirements/base.txt

```txt
# Основные зависимости приложения
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Telegram Bot
aiogram==3.2.0

# База данных
sqlalchemy[asyncio]==2.0.23
alembic==1.13.1
asyncpg==0.29.0

# Redis
redis[hiredis]==5.0.1

# LangChain и AI
langchain==0.1.0
langchain-core==0.1.0
langchain-community==0.0.10
langchain-openai==0.0.5
langchain-qdrant==0.0.1
langgraph==0.0.20
openai==1.6.1
sentence-transformers==2.2.2
qdrant-client==1.7.0

# Обработка документов
PyPDF2==3.0.1
pdfplumber==0.10.3
python-docx==1.1.0
python-magic==0.4.27

# Многоязычность
langdetect==1.0.9
googletrans==4.0.0rc1

# HTTP клиент
httpx==0.25.2
aiohttp==3.9.1

# Утилиты
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0

# Логирование
structlog==23.2.0
python-json-logger==2.0.7

# Мониторинг
prometheus-client==0.19.0
sentry-sdk[fastapi]==1.38.0

# Валидация и сериализация
marshmallow==3.20.1
```

## Обновленный requirements/dev.txt

```txt
# Включаем базовые зависимости
-r base.txt

# Разработка и тестирование
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0

# Линтеры и форматтеры
black==23.11.0
isort==5.12.0
flake8==6.1.0
mypy==1.7.1

# Pre-commit hooks
pre-commit==3.6.0

# Отладка LangChain
langsmith==0.0.70
langchain-experimental==0.0.50

# Jupyter для экспериментов
jupyter==1.0.0
ipykernel==6.26.0

# Профилирование
py-spy==0.3.14
memory-profiler==0.61.0
```

## Docker requirements

### requirements/prod.txt
```txt
# Продакшн зависимости
-r base.txt

# Дополнительные продакшн зависимости
gunicorn==21.2.0
```

### requirements/test.txt
```txt
# Тестовые зависимости
-r base.txt

pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
factory-boy==3.3.0
faker==20.1.0

# Тестирование LangChain
langchain-experimental==0.0.50
```

## Установка зависимостей

### Для разработки
```bash
pip install -r requirements/dev.txt
```

### Для продакшена
```bash
pip install -r requirements/prod.txt
```

### Только LangChain компоненты
```bash
pip install -r requirements/langchain.txt
```

## Версионирование

Все версии зафиксированы для обеспечения воспроизводимости сборок. При обновлении LangChain компонентов рекомендуется:

1. Обновлять все LangChain пакеты одновременно
2. Тестировать совместимость с существующим кодом
3. Проверять breaking changes в changelog
4. Обновлять примеры кода при необходимости

## Конфликты зависимостей

### Известные проблемы
- `pydantic` версии должны быть совместимы между LangChain и FastAPI
- `numpy` версии могут конфликтовать между sentence-transformers и другими ML библиотеками
- `openai` клиент должен быть совместим с langchain-openai

### Решения
```txt
# Фиксация совместимых версий
pydantic>=2.0.0,<3.0.0
numpy>=1.24.0,<2.0.0
openai>=1.0.0,<2.0.0