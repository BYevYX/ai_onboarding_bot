# Структура проекта Telegram-бота для онбординга

## Общая структура папок

```
telegram-onboarding-bot/
├── app/                              # Основное приложение
│   ├── __init__.py
│   ├── main.py                       # Точка входа приложения
│   ├── config/                       # Конфигурация
│   │   ├── __init__.py
│   │   ├── settings.py               # Основные настройки
│   │   ├── database.py               # Настройки БД
│   │   ├── redis.py                  # Настройки Redis
│   │   └── logging.py                # Настройки логирования
│   ├── core/                         # Ядро системы
│   │   ├── __init__.py
│   │   ├── exceptions.py             # Кастомные исключения
│   │   ├── security.py               # Безопасность и аутентификация
│   │   ├── middleware.py             # Middleware для обработки запросов
│   │   └── dependencies.py           # Dependency injection
│   ├── models/                       # Модели данных
│   │   ├── __init__.py
│   │   ├── base.py                   # Базовая модель
│   │   ├── user.py                   # Модель пользователя
│   │   ├── document.py               # Модель документа
│   │   ├── conversation.py           # Модель диалога
│   │   ├── role.py                   # Модель роли
│   │   └── analytics.py              # Модель аналитики
│   ├── schemas/                      # Pydantic схемы
│   │   ├── __init__.py
│   │   ├── user.py                   # Схемы пользователя
│   │   ├── document.py               # Схемы документа
│   │   ├── conversation.py           # Схемы диалога
│   │   └── common.py                 # Общие схемы
│   ├── services/                     # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── auth_service.py           # Сервис аутентификации
│   │   ├── document_service.py       # Сервис работы с документами
│   │   ├── rag_service.py            # RAG сервис
│   │   ├── language_service.py       # Сервис языков
│   │   ├── cache_service.py          # Сервис кэширования
│   │   ├── analytics_service.py      # Сервис аналитики
│   │   └── notification_service.py   # Сервис уведомлений
│   ├── bot/                          # Telegram Bot
│   │   ├── __init__.py
│   │   ├── handlers/                 # Обработчики команд
│   │   │   ├── __init__.py
│   │   │   ├── start.py              # Команда /start
│   │   │   ├── help.py               # Команда /help
│   │   │   ├── admin.py              # Админские команды
│   │   │   ├── documents.py          # Работа с документами
│   │   │   ├── search.py             # Поиск по документам
│   │   │   └── settings.py           # Настройки пользователя
│   │   ├── keyboards/                # Клавиатуры
│   │   │   ├── __init__.py
│   │   │   ├── inline.py             # Inline клавиатуры
│   │   │   ├── reply.py              # Reply клавиатуры
│   │   │   └── dynamic.py            # Динамические клавиатуры
│   │   ├── middlewares/              # Middleware для бота
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # Аутентификация
│   │   │   ├── language.py           # Определение языка
│   │   │   ├── logging.py            # Логирование
│   │   │   └── throttling.py         # Ограничение запросов
│   │   ├── filters/                  # Фильтры сообщений
│   │   │   ├── __init__.py
│   │   │   ├── role.py               # Фильтр по ролям
│   │   │   ├── language.py           # Фильтр по языку
│   │   │   └── content.py            # Фильтр контента
│   │   └── utils/                    # Утилиты бота
│   │       ├── __init__.py
│   │       ├── formatters.py         # Форматирование сообщений
│   │       ├── validators.py         # Валидация данных
│   │       └── helpers.py            # Вспомогательные функции
│   ├── ai/                           # AI/ML компоненты с LangChain
│   │   ├── __init__.py
│   │   ├── langchain/                # LangChain интеграция
│   │   │   ├── __init__.py
│   │   │   ├── embeddings.py         # LangChain Embeddings
│   │   │   ├── vectorstores.py       # LangChain VectorStores
│   │   │   ├── chains.py             # LangChain Chains
│   │   │   ├── agents.py             # LangChain Agents
│   │   │   └── tools.py              # Custom LangChain Tools
│   │   ├── langgraph/                # LangGraph workflows
│   │   │   ├── __init__.py
│   │   │   ├── rag_workflow.py       # RAG workflow граф
│   │   │   ├── conversation_graph.py # Диалоговый граф
│   │   │   ├── document_processing_graph.py # Граф обработки документов
│   │   │   └── states.py             # Состояния для графов
│   │   ├── prompts/                  # Промпт-шаблоны
│   │   │   ├── __init__.py
│   │   │   ├── rag_prompts.py        # Промпты для RAG
│   │   │   ├── conversation_prompts.py # Промпты для диалогов
│   │   │   └── system_prompts.py     # Системные промпты
│   │   └── tools/                    # Кастомные инструменты
│   │       ├── __init__.py
│   │       ├── user_search_tool.py   # Поиск пользователей
│   │       ├── document_tool.py      # Работа с документами
│   │       └── analytics_tool.py     # Аналитические инструменты
│   ├── document_processing/          # Обработка документов
│   │   ├── __init__.py
│   │   ├── parsers/                  # Парсеры файлов
│   │   │   ├── __init__.py
│   │   │   ├── pdf_parser.py         # Парсер PDF
│   │   │   ├── docx_parser.py        # Парсер DOCX
│   │   │   ├── txt_parser.py         # Парсер TXT
│   │   │   └── base_parser.py        # Базовый парсер
│   │   ├── processors/               # Обработчики контента
│   │   │   ├── __init__.py
│   │   │   ├── text_cleaner.py       # Очистка текста
│   │   │   ├── chunker.py            # Разбиение на чанки
│   │   │   ├── metadata_extractor.py # Извлечение метаданных
│   │   │   └── indexer.py            # Индексация
│   │   └── storage/                  # Хранение файлов
│   │       ├── __init__.py
│   │       ├── file_manager.py       # Менеджер файлов
│   │       ├── version_control.py    # Контроль версий
│   │       └── backup.py             # Резервное копирование
│   ├── database/                     # База данных
│   │   ├── __init__.py
│   │   ├── connection.py             # Подключение к БД
│   │   ├── migrations/               # Миграции Alembic
│   │   │   ├── env.py
│   │   │   ├── script.py.mako
│   │   │   └── versions/
│   │   └── repositories/             # Репозитории
│   │       ├── __init__.py
│   │       ├── base.py               # Базовый репозиторий
│   │       ├── user_repository.py    # Репозиторий пользователей
│   │       ├── document_repository.py # Репозиторий документов
│   │       └── conversation_repository.py # Репозиторий диалогов
│   ├── api/                          # REST API (опционально)
│   │   ├── __init__.py
│   │   ├── v1/                       # API версии 1
│   │   │   ├── __init__.py
│   │   │   ├── endpoints/            # Эндпоинты
│   │   │   │   ├── __init__.py
│   │   │   │   ├── users.py          # Пользователи
│   │   │   │   ├── documents.py      # Документы
│   │   │   │   └── analytics.py      # Аналитика
│   │   │   └── dependencies.py       # Зависимости API
│   │   └── middleware.py             # API middleware
│   └── utils/                        # Общие утилиты
│       ├── __init__.py
│       ├── logger.py                 # Логгер
│       ├── cache.py                  # Кэш утилиты
│       ├── validators.py             # Валидаторы
│       ├── decorators.py             # Декораторы
│       └── constants.py              # Константы
├── tests/                            # Тесты
│   ├── __init__.py
│   ├── conftest.py                   # Конфигурация pytest
│   ├── unit/                         # Unit тесты
│   │   ├── __init__.py
│   │   ├── test_services/            # Тесты сервисов
│   │   ├── test_models/              # Тесты моделей
│   │   └── test_utils/               # Тесты утилит
│   ├── integration/                  # Интеграционные тесты
│   │   ├── __init__.py
│   │   ├── test_bot/                 # Тесты бота
│   │   ├── test_api/                 # Тесты API
│   │   └── test_database/            # Тесты БД
│   └── fixtures/                     # Тестовые данные
│       ├── documents/                # Тестовые документы
│       └── data/                     # Тестовые данные
├── scripts/                          # Скрипты
│   ├── __init__.py
│   ├── init_db.py                    # Инициализация БД
│   ├── migrate.py                    # Миграции
│   ├── seed_data.py                  # Заполнение тестовыми данными
│   ├── backup.py                     # Резервное копирование
│   └── deploy.py                     # Деплой
├── docs/                             # Документация
│   ├── api/                          # API документация
│   ├── deployment/                   # Документация по деплою
│   ├── user_guide/                   # Руководство пользователя
│   └── development/                  # Документация для разработчиков
├── docker/                           # Docker конфигурация
│   ├── Dockerfile                    # Основной Dockerfile
│   ├── Dockerfile.dev                # Dockerfile для разработки
│   ├── docker-compose.yml            # Docker Compose
│   ├── docker-compose.dev.yml        # Docker Compose для разработки
│   └── nginx/                        # Конфигурация Nginx
│       └── nginx.conf
├── config/                           # Конфигурационные файлы
│   ├── .env.example                  # Пример переменных окружения
│   ├── logging.yaml                  # Конфигурация логирования
│   ├── prometheus.yml                # Конфигурация Prometheus
│   └── locales/                      # Локализация
│       ├── ru/                       # Русский язык
│       ├── en/                       # Английский язык
│       └── ar/                       # Арабский язык
├── storage/                          # Хранилище файлов
│   ├── documents/                    # Загруженные документы
│   ├── embeddings/                   # Векторные представления
│   ├── cache/                        # Кэш файлы
│   └── backups/                      # Резервные копии
├── monitoring/                       # Мониторинг
│   ├── grafana/                      # Конфигурация Grafana
│   ├── prometheus/                   # Конфигурация Prometheus
│   └── alerts/                       # Настройки алертов
├── requirements/                     # Зависимости
│   ├── base.txt                      # Базовые зависимости
│   ├── dev.txt                       # Зависимости для разработки
│   ├── test.txt                      # Зависимости для тестов
│   └── prod.txt                      # Зависимости для продакшена
├── .github/                          # GitHub Actions
│   └── workflows/                    # CI/CD пайплайны
│       ├── test.yml                  # Тестирование
│       ├── build.yml                 # Сборка
│       └── deploy.yml                # Деплой
├── .gitignore                        # Git ignore
├── .dockerignore                     # Docker ignore
├── README.md                         # Основная документация
├── CHANGELOG.md                      # История изменений
├── LICENSE                           # Лицензия
├── pyproject.toml                    # Конфигурация проекта
├── alembic.ini                       # Конфигурация Alembic
└── Makefile                          # Команды для разработки
```

## Описание основных модулей

### 1. Core Modules (`app/core/`)
- **exceptions.py**: Кастомные исключения для различных типов ошибок
- **security.py**: JWT токены, хеширование паролей, RBAC
- **middleware.py**: Middleware для логирования, аутентификации, rate limiting
- **dependencies.py**: Dependency injection для FastAPI и aiogram

### 2. Models (`app/models/`)
- **user.py**: Пользователи, роли, права доступа
- **document.py**: Документы, метаданные, версии
- **conversation.py**: История диалогов, контекст
- **analytics.py**: Метрики использования, статистика

### 3. Services (`app/services/`)
- **auth_service.py**: Аутентификация, авторизация, управление сессиями
- **document_service.py**: CRUD операции с документами, индексация
- **rag_service.py**: RAG пайплайн, поиск, генерация ответов
- **language_service.py**: Определение языка, перевод, локализация

### 4. Bot Handlers (`app/bot/handlers/`)
- **start.py**: Регистрация новых пользователей, приветствие
- **admin.py**: Административные функции, управление документами
- **search.py**: Поиск по документам, RAG запросы
- **documents.py**: Загрузка, просмотр, управление документами

### 5. AI Components (`app/ai/`)
- **embeddings/**: Генерация и поиск по векторным представлениям
- **llm/**: Интеграция с OpenAI, управление промптами
- **rag/**: RAG пайплайн, retrieval и generation
- **translation/**: Многоязычная поддержка

### 6. Document Processing (`app/document_processing/`)
- **parsers/**: Парсеры для различных форматов файлов
- **processors/**: Обработка текста, извлечение метаданных
- **storage/**: Управление файлами, версионирование

## Принципы организации кода

### 1. Separation of Concerns
- Четкое разделение между слоями (handlers, services, repositories)
- Изоляция бизнес-логики от инфраструктурного кода
- Отдельные модули для различных типов функциональности

### 2. Dependency Injection
- Использование FastAPI Depends для внедрения зависимостей
- Легкое тестирование через mock объекты
- Гибкая конфигурация сервисов

### 3. Configuration Management
- Централизованная конфигурация через Pydantic Settings
- Переменные окружения для различных сред
- Валидация конфигурации при запуске

### 4. Error Handling
- Централизованная обработка ошибок
- Кастомные исключения для различных типов ошибок
- Graceful degradation при недоступности внешних сервисов

### 5. Testing Strategy
- Unit тесты для бизнес-логики
- Integration тесты для API и БД
- Fixtures для тестовых данных
- Mocking внешних сервисов