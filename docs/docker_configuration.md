# Docker-контейнеризация и конфигурационные файлы

## Обзор контейнеризации

Полная Docker-контейнеризация системы с использованием Docker Compose для оркестрации всех сервисов, включая приложение, базы данных, кэш и мониторинг.

## Docker Architecture

```mermaid
graph TB
    subgraph "Load Balancer"
        NGINX[Nginx]
    end
    
    subgraph "Application Services"
        APP1[Bot App 1]
        APP2[Bot App 2]
        API[API Service]
        WORKER[Background Worker]
    end
    
    subgraph "Databases"
        PG[PostgreSQL]
        REDIS[Redis]
        QDRANT[Qdrant]
    end
    
    subgraph "Monitoring"
        PROM[Prometheus]
        GRAF[Grafana]
        ALERT[AlertManager]
    end
    
    subgraph "Storage"
        FILES[File Storage]
        LOGS[Log Storage]
    end
    
    NGINX --> APP1
    NGINX --> APP2
    NGINX --> API
    
    APP1 --> PG
    APP1 --> REDIS
    APP1 --> QDRANT
    
    APP2 --> PG
    APP2 --> REDIS
    APP2 --> QDRANT
    
    API --> PG
    API --> REDIS
    
    WORKER --> PG
    WORKER --> REDIS
    WORKER --> QDRANT
    
    PROM --> APP1
    PROM --> APP2
    PROM --> API
    
    GRAF --> PROM
    ALERT --> PROM
    
    APP1 --> FILES
    APP2 --> FILES
    WORKER --> FILES
    
    APP1 --> LOGS
    APP2 --> LOGS
    API --> LOGS
```

## Docker Compose Configuration

### Main docker-compose.yml
```yaml
version: '3.8'

services:
  # Application Services
  telegram-bot:
    build:
      context: .
      dockerfile: docker/Dockerfile
      target: production
    container_name: telegram-bot
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
    env_file:
      - .env
    volumes:
      - ./storage:/app/storage
      - ./logs:/app/logs
      - ./config:/app/config
    depends_on:
      - postgres
      - redis
      - qdrant
    networks:
      - app-network
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'

  api-service:
    build:
      context: .
      dockerfile: docker/Dockerfile
      target: production
    container_name: api-service
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    volumes:
      - ./storage:/app/storage
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    networks:
      - app-network
    command: ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

  background-worker:
    build:
      context: .
      dockerfile: docker/Dockerfile
      target: production
    container_name: background-worker
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
    env_file:
      - .env
    volumes:
      - ./storage:/app/storage
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
      - qdrant
    networks:
      - app-network
    command: ["python", "-m", "app.workers.main"]

  # Database Services
  postgres:
    image: postgres:15-alpine
    container_name: postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - app-network
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
      - ./docker/redis/redis.conf:/usr/local/etc/redis/redis.conf
    ports:
      - "6379:6379"
    networks:
      - app-network
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.25'

  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
    volumes:
      - qdrant_data:/qdrant/storage
      - ./docker/qdrant/config.yaml:/qdrant/config/production.yaml
    ports:
      - "6333:6333"
      - "6334:6334"
    networks:
      - app-network
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  # Load Balancer
  nginx:
    image: nginx:alpine
    container_name: nginx
    restart: unless-stopped
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf
      - ./storage:/var/www/storage
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - telegram-bot
      - api-service
    networks:
      - app-network

  # Monitoring Services
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus/alert_rules.yml:/etc/prometheus/alert_rules.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    networks:
      - app-network

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    networks:
      - app-network

  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    restart: unless-stopped
    volumes:
      - ./monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager_data:/alertmanager
    ports:
      - "9093:9093"
    networks:
      - app-network

  # Log Management
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
    container_name: elasticsearch
    restart: unless-stopped
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    networks:
      - app-network
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'

  logstash:
    image: docker.elastic.co/logstash/logstash:8.8.0
    container_name: logstash
    restart: unless-stopped
    volumes:
      - ./docker/logstash/pipeline:/usr/share/logstash/pipeline
      - ./logs:/usr/share/logstash/logs
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch
    networks:
      - app-network

  kibana:
    image: docker.elastic.co/kibana/kibana:8.8.0
    container_name: kibana
    restart: unless-stopped
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
    networks:
      - app-network

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  prometheus_data:
  grafana_data:
  alertmanager_data:
  elasticsearch_data:

networks:
  app-network:
    driver: bridge
```

### Development docker-compose.dev.yml
```yaml
version: '3.8'

services:
  telegram-bot-dev:
    build:
      context: .
      dockerfile: docker/Dockerfile.dev
    container_name: telegram-bot-dev
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://postgres:postgres@postgres-dev:5432/telegram_bot_dev
      - REDIS_URL=redis://redis-dev:6379/0
      - QDRANT_URL=http://qdrant-dev:6333
    env_file:
      - .env.dev
    volumes:
      - .:/app
      - ./storage:/app/storage
      - ./logs:/app/logs
    ports:
      - "8001:8000"
    depends_on:
      - postgres-dev
      - redis-dev
      - qdrant-dev
    networks:
      - dev-network
    command: ["python", "-m", "app.main"]

  postgres-dev:
    image: postgres:15-alpine
    container_name: postgres-dev
    environment:
      - POSTGRES_DB=telegram_bot_dev
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
    ports:
      - "5433:5432"
    networks:
      - dev-network

  redis-dev:
    image: redis:7-alpine
    container_name: redis-dev
    ports:
      - "6380:6379"
    networks:
      - dev-network

  qdrant-dev:
    image: qdrant/qdrant:latest
    container_name: qdrant-dev
    volumes:
      - qdrant_dev_data:/qdrant/storage
    ports:
      - "6335:6333"
    networks:
      - dev-network

volumes:
  postgres_dev_data:
  qdrant_dev_data:

networks:
  dev-network:
    driver: bridge
```

## Dockerfiles

### Production Dockerfile
```dockerfile
# docker/Dockerfile
FROM python:3.11-slim as base

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя приложения
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Установка рабочей директории
WORKDIR /app

# Копирование requirements
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

# Development stage
FROM base as development

RUN pip install --no-cache-dir -r requirements/dev.txt

COPY . .
RUN chown -R appuser:appuser /app

USER appuser

CMD ["python", "-m", "app.main"]

# Production stage
FROM base as production

# Копирование приложения
COPY app/ app/
COPY config/ config/
COPY scripts/ scripts/
COPY alembic.ini .
COPY pyproject.toml .

# Создание необходимых директорий
RUN mkdir -p /app/logs /app/storage /app/storage/documents /app/storage/embeddings

# Установка прав доступа
RUN chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запуск приложения
CMD ["python", "-m", "app.main"]
```

### Development Dockerfile
```dockerfile
# docker/Dockerfile.dev
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libmagic1 \
    curl \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Установка Python зависимостей
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/dev.txt

# Установка pre-commit hooks
RUN pip install pre-commit

# Создание пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app

USER appuser

# Запуск в режиме разработки с hot reload
CMD ["python", "-m", "app.main", "--reload"]
```

## Configuration Files

### Environment Variables (.env.example)
```bash
# Application Settings
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-secret-key-here
API_VERSION=v1

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook/telegram
TELEGRAM_WEBHOOK_SECRET=your-webhook-secret

# Database
POSTGRES_DB=telegram_bot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-postgres-password
DATABASE_URL=postgresql://postgres:your-postgres-password@postgres:5432/telegram_bot

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=your-redis-password

# Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=your-qdrant-api-key

# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002

# Translation
GOOGLE_TRANSLATE_API_KEY=your-google-translate-key

# Monitoring
SENTRY_DSN=your-sentry-dsn
GRAFANA_PASSWORD=your-grafana-password

# Alerting
SLACK_WEBHOOK_URL=your-slack-webhook-url
TELEGRAM_ALERT_BOT_TOKEN=your-alert-bot-token
TELEGRAM_ALERT_CHAT_ID=your-alert-chat-id

# File Storage
MAX_FILE_SIZE_MB=50
ALLOWED_FILE_TYPES=pdf,docx,txt

# Cache Settings
CACHE_TTL_SECONDS=3600
MEMORY_CACHE_SIZE=1000

# Rate Limiting
DEFAULT_RATE_LIMIT=100
SEARCH_RATE_LIMIT=20
UPLOAD_RATE_LIMIT=5

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Nginx Configuration
```nginx
# docker/nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 10240;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/x-javascript
        application/xml+rss
        application/json;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=webhook:10m rate=100r/s;

    # Upstream servers
    upstream telegram_bot {
        least_conn;
        server telegram-bot:8000 max_fails=3 fail_timeout=30s;
    }

    upstream api_service {
        least_conn;
        server api-service:8000 max_fails=3 fail_timeout=30s;
    }

    include /etc/nginx/conf.d/*.conf;
}
```

```nginx
# docker/nginx/default.conf
server {
    listen 80;
    server_name localhost;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # API endpoints
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://api_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Telegram webhook
    location /webhook/ {
        limit_req zone=webhook burst=50 nodelay;
        
        proxy_pass http://telegram_bot;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        proxy_pass http://api_service/health;
        access_log off;
    }

    # Metrics (internal only)
    location /metrics {
        allow 172.16.0.0/12;  # Docker networks
        deny all;
        proxy_pass http://api_service/metrics;
    }

    # Static files
    location /storage/ {
        alias /var/www/storage/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # Default location
    location / {
        return 404;
    }
}
```

### Redis Configuration
```conf
# docker/redis/redis.conf
# Network
bind 0.0.0.0
port 6379
timeout 300
tcp-keepalive 60

# General
daemonize no
supervised no
pidfile /var/run/redis_6379.pid
loglevel notice
logfile ""

# Snapshotting
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir ./

# Replication
replica-serve-stale-data yes
replica-read-only yes

# Security
requirepass your-redis-password

# Memory management
maxmemory 512mb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Append only file
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Slow log
slowlog-log-slower-than 10000
slowlog-max-len 128
```

### Qdrant Configuration
```yaml
# docker/qdrant/config.yaml
log_level: INFO

storage:
  storage_path: /qdrant/storage

service:
  host: 0.0.0.0
  http_port: 6333
  grpc_port: 6334
  enable_cors: true

cluster:
  enabled: false

telemetry_disabled: true

# Performance settings
hnsw_config:
  m: 16
  ef_construct: 100
  full_scan_threshold: 10000

# Memory settings
optimizer:
  deleted_threshold: 0.2
  vacuum_min_vector_number: 1000
  default_segment_number: 0
  max_segment_size_kb: 5000000
  memmap_threshold_kb: 200000
  indexing_threshold_kb: 20000
  flush_interval_sec: 5
  max_optimization_threads: 1
```

## Build and Deployment Scripts

### Build Script
```bash
#!/bin/bash
# scripts/build.sh

set -e

echo "Building Telegram Onboarding Bot..."

# Build production image
docker build -f docker/Dockerfile --target production -t telegram-onboarding-bot:latest .

# Build development image
docker build -f docker/Dockerfile.dev -t telegram-onboarding-bot:dev .

echo "Build completed successfully!"
```

### Deployment Script
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

ENVIRONMENT=${1:-production}

echo "Deploying to $ENVIRONMENT environment..."

if [ "$ENVIRONMENT" = "production" ]; then
    # Production deployment
    docker-compose -f docker-compose.yml down
    docker-compose -f docker-compose.yml pull
    docker-compose -f docker-compose.yml up -d
    
    # Wait for services to be ready
    echo "Waiting for services to start..."
    sleep 30
    
    # Run database migrations
    docker-compose exec telegram-bot alembic upgrade head
    
    # Health check
    docker-compose exec telegram-bot python -m scripts.health_check
    
elif [ "$ENVIRONMENT" = "development" ]; then
    # Development deployment
    docker-compose -f docker-compose.dev.yml down
    docker-compose -f docker-compose.dev.yml up -d
    
    # Wait for services
    sleep 15
    
    # Run migrations
    docker-compose -f docker-compose.dev.yml exec telegram-bot-dev alembic upgrade head
fi

echo "Deployment completed successfully!"
```

### Backup Script
```bash
#!/bin/bash
# scripts/backup.sh

set -e

BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "Creating backup in $BACKUP_DIR..."

# Database backup
docker-compose exec postgres pg_dump -U postgres telegram_bot > $BACKUP_DIR/database.sql

# Redis backup
docker-compose exec redis redis-cli --rdb $BACKUP_DIR/redis.rdb

# Qdrant backup
curl -X POST "http://localhost:6333/collections/documents/snapshots" > $BACKUP_DIR/qdrant_snapshot.json

# File storage backup
tar -czf $BACKUP_DIR/storage.tar.gz ./storage

# Configuration backup
tar -czf $BACKUP_DIR/config.tar.gz ./config

echo "Backup completed: $BACKUP_DIR"
```

### Makefile
```makefile
# Makefile
.PHONY: help build dev prod test clean backup

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	@./scripts/build.sh

dev: ## Start development environment
	@docker-compose -f docker-compose.dev.yml up -d
	@echo "Development environment started at http://localhost:8001"

prod: ## Start production environment
	@docker-compose up -d
	@echo "Production environment started"

test: ## Run tests
	@docker-compose -f docker-compose.dev.yml exec telegram-bot-dev python -m pytest

clean: ## Clean up containers and volumes
	@docker-compose down -v
	@docker-compose -f docker-compose.dev.yml down -v
	@docker system prune -f

backup: ## Create backup
	@./scripts/backup.sh

logs: ## Show logs
	@docker-compose logs -f

migrate: ## Run database migrations
	@docker-compose exec telegram-bot alembic upgrade head

shell: ## Open shell in container
	@docker-compose exec telegram-bot bash

psql: ## Connect to PostgreSQL
	@docker-compose exec postgres psql -U postgres -d telegram_bot

redis-cli: ## Connect to Redis
	@docker-compose exec redis redis-cli
```

Эта конфигурация Docker обеспечивает:
- Полную контейнеризацию всех сервисов
- Разделение на production и development окружения
- Масштабируемость через Docker Swarm или Kubernetes
- Мониторинг и логирование
- Автоматические backup'ы
- Health checks и graceful shutdown
- Безопасность через изоляцию сетей
- Оптимизацию ресурсов