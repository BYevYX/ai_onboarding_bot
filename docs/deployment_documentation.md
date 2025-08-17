# Документация по развертыванию Telegram-бота для онбординга

## Обзор развертывания

Данная документация описывает процесс развертывания Telegram-бота для онбординга сотрудников в различных окружениях: development, staging и production.

## Системные требования

### Минимальные требования

#### Development окружение
- **CPU**: 2 ядра
- **RAM**: 4 GB
- **Диск**: 20 GB SSD
- **ОС**: Ubuntu 20.04+ / macOS 10.15+ / Windows 10+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

#### Production окружение
- **CPU**: 4 ядра (8 рекомендуется)
- **RAM**: 8 GB (16 GB рекомендуется)
- **Диск**: 100 GB SSD (с возможностью расширения)
- **ОС**: Ubuntu 22.04 LTS
- **Docker**: 24.0+
- **Docker Compose**: 2.20+

### Рекомендуемые требования для Production

#### Сервер приложений
- **CPU**: 8 ядер Intel Xeon или AMD EPYC
- **RAM**: 16-32 GB
- **Диск**: 200 GB NVMe SSD
- **Сеть**: 1 Gbps

#### База данных (PostgreSQL)
- **CPU**: 4-8 ядер
- **RAM**: 8-16 GB
- **Диск**: 500 GB SSD с высоким IOPS
- **Backup**: Автоматическое резервное копирование

#### Векторная БД (Qdrant)
- **CPU**: 4-6 ядер
- **RAM**: 8-16 GB
- **Диск**: 100-500 GB SSD (зависит от объема документов)

## Предварительная настройка

### 1. Установка Docker и Docker Compose

#### Ubuntu/Debian
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Добавление GPG ключа Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавление репозитория Docker
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Перезагрузка для применения изменений
sudo reboot
```

#### CentOS/RHEL
```bash
# Установка Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Запуск Docker
sudo systemctl start docker
sudo systemctl enable docker

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
```

### 2. Настройка файрвола

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 8000/tcp    # API (только для staging/dev)
sudo ufw enable

# Firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

### 3. Создание пользователя для приложения

```bash
# Создание пользователя
sudo useradd -m -s /bin/bash telegram-bot
sudo usermod -aG docker telegram-bot

# Создание директорий
sudo mkdir -p /opt/telegram-bot
sudo chown telegram-bot:telegram-bot /opt/telegram-bot

# Переключение на пользователя приложения
sudo su - telegram-bot
```

## Настройка окружений

### Development окружение

#### 1. Клонирование репозитория
```bash
cd /opt/telegram-bot
git clone https://github.com/your-org/telegram-onboarding-bot.git
cd telegram-onboarding-bot
```

#### 2. Настройка переменных окружения
```bash
# Копирование примера конфигурации
cp .env.example .env.dev

# Редактирование конфигурации
nano .env.dev
```

Пример `.env.dev`:
```bash
# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production

# Telegram
TELEGRAM_BOT_TOKEN=your-dev-bot-token
TELEGRAM_WEBHOOK_URL=https://your-dev-domain.com/webhook/telegram

# Database
POSTGRES_DB=telegram_bot_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=dev_password
DATABASE_URL=postgresql://postgres:dev_password@postgres-dev:5432/telegram_bot_dev

# Redis
REDIS_URL=redis://redis-dev:6379/0

# Qdrant
QDRANT_URL=http://qdrant-dev:6333

# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo

# Logging
LOG_LEVEL=DEBUG
```

#### 3. Запуск development окружения
```bash
# Сборка и запуск
make dev

# Или напрямую через Docker Compose
docker-compose -f docker-compose.dev.yml up -d

# Проверка статуса
docker-compose -f docker-compose.dev.yml ps

# Просмотр логов
docker-compose -f docker-compose.dev.yml logs -f
```

#### 4. Инициализация базы данных
```bash
# Выполнение миграций
docker-compose -f docker-compose.dev.yml exec telegram-bot-dev alembic upgrade head

# Создание тестовых данных (опционально)
docker-compose -f docker-compose.dev.yml exec telegram-bot-dev python -m scripts.seed_data
```

### Production окружение

#### 1. Подготовка сервера

```bash
# Создание директорий
sudo mkdir -p /opt/telegram-bot/{storage,logs,backups,config}
sudo chown -R telegram-bot:telegram-bot /opt/telegram-bot

# Настройка логротации
sudo tee /etc/logrotate.d/telegram-bot << EOF
/opt/telegram-bot/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 telegram-bot telegram-bot
    postrotate
        docker-compose -f /opt/telegram-bot/docker-compose.yml restart telegram-bot
    endscript
}
EOF
```

#### 2. Настройка SSL сертификатов

```bash
# Установка Certbot
sudo apt install -y certbot

# Получение SSL сертификата
sudo certbot certonly --standalone -d your-domain.com

# Копирование сертификатов
sudo mkdir -p /opt/telegram-bot/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/telegram-bot/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/telegram-bot/ssl/
sudo chown -R telegram-bot:telegram-bot /opt/telegram-bot/ssl
```

#### 3. Конфигурация production

Создание `.env`:
```bash
# Application
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-production-key

# Telegram
TELEGRAM_BOT_TOKEN=your-production-bot-token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook/telegram
TELEGRAM_WEBHOOK_SECRET=your-webhook-secret

# Database
POSTGRES_DB=telegram_bot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-strong-postgres-password
DATABASE_URL=postgresql://postgres:your-strong-postgres-password@postgres:5432/telegram_bot

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=your-redis-password

# Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=your-qdrant-api-key

# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4

# Translation
GOOGLE_TRANSLATE_API_KEY=your-google-translate-key

# Monitoring
SENTRY_DSN=your-sentry-dsn
GRAFANA_PASSWORD=your-grafana-password

# Alerting
SLACK_WEBHOOK_URL=your-slack-webhook
TELEGRAM_ALERT_BOT_TOKEN=your-alert-bot-token
TELEGRAM_ALERT_CHAT_ID=your-alert-chat-id

# Security
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
CORS_ORIGINS=https://your-domain.com

# Performance
MAX_WORKERS=4
WORKER_CONNECTIONS=1000
```

#### 4. Настройка Nginx с SSL

```nginx
# /opt/telegram-bot/docker/nginx/production.conf
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/private/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=webhook:10m rate=100r/s;
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    # Telegram Webhook
    location /webhook/ {
        limit_req zone=webhook burst=50 nodelay;
        
        proxy_pass http://telegram_bot;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Security
        proxy_hide_header X-Powered-By;
        proxy_set_header X-Forwarded-Host $host;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # API Endpoints
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://api_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health Check
    location /health {
        proxy_pass http://api_service/health;
        access_log off;
    }

    # Block access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
```

#### 5. Запуск production окружения

```bash
# Переход в директорию проекта
cd /opt/telegram-bot

# Сборка production образов
make build

# Запуск production окружения
make prod

# Проверка статуса всех сервисов
docker-compose ps

# Выполнение миграций
make migrate

# Проверка health check
curl -f http://localhost/health
```

## Мониторинг и обслуживание

### 1. Настройка мониторинга

#### Prometheus конфигурация
```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'telegram-bot'
    static_configs:
      - targets: ['telegram-bot:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

#### Grafana Dashboard
```bash
# Импорт готовых дашбордов
curl -X POST \
  http://admin:your-grafana-password@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @monitoring/grafana/dashboards/telegram-bot-dashboard.json
```

### 2. Настройка алертов

#### AlertManager конфигурация
```yaml
# monitoring/alertmanager/alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@your-domain.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    channel: '#alerts'
    title: 'Telegram Bot Alert'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

  telegram_configs:
  - bot_token: 'YOUR_ALERT_BOT_TOKEN'
    chat_id: YOUR_ALERT_CHAT_ID
    message: |
      🚨 *Alert*: {{ .GroupLabels.alertname }}
      
      {{ range .Alerts }}
      *Summary*: {{ .Annotations.summary }}
      *Description*: {{ .Annotations.description }}
      {{ end }}
```

### 3. Резервное копирование

#### Автоматический backup скрипт
```bash
#!/bin/bash
# scripts/backup.sh

set -e

BACKUP_DIR="/opt/telegram-bot/backups/$(date +%Y%m%d_%H%M%S)"
RETENTION_DAYS=30

echo "Starting backup process..."

# Создание директории backup
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
echo "Backing up PostgreSQL..."
docker-compose exec -T postgres pg_dump -U postgres telegram_bot | gzip > $BACKUP_DIR/postgres.sql.gz

# Backup Redis
echo "Backing up Redis..."
docker-compose exec -T redis redis-cli --rdb - > $BACKUP_DIR/redis.rdb

# Backup Qdrant
echo "Backing up Qdrant..."
curl -X POST "http://localhost:6333/collections/documents/snapshots" > $BACKUP_DIR/qdrant_snapshot.json

# Backup file storage
echo "Backing up file storage..."
tar -czf $BACKUP_DIR/storage.tar.gz -C /opt/telegram-bot storage/

# Backup configuration
echo "Backing up configuration..."
tar -czf $BACKUP_DIR/config.tar.gz -C /opt/telegram-bot config/ .env

# Cleanup old backups
echo "Cleaning up old backups..."
find /opt/telegram-bot/backups -type d -mtime +$RETENTION_DAYS -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR"

# Upload to cloud storage (optional)
if [ -n "$AWS_S3_BUCKET" ]; then
    echo "Uploading to S3..."
    aws s3 sync $BACKUP_DIR s3://$AWS_S3_BUCKET/backups/$(basename $BACKUP_DIR)/
fi
```

#### Настройка cron для автоматических backup'ов
```bash
# Добавление в crontab
crontab -e

# Ежедневный backup в 2:00 AM
0 2 * * * /opt/telegram-bot/scripts/backup.sh >> /opt/telegram-bot/logs/backup.log 2>&1

# Еженедельная очистка логов
0 3 * * 0 find /opt/telegram-bot/logs -name "*.log" -mtime +7 -delete
```

## Обновление и развертывание

### 1. Blue-Green Deployment

#### Скрипт обновления
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

ENVIRONMENT=${1:-production}
VERSION=${2:-latest}

echo "Deploying version $VERSION to $ENVIRONMENT..."

# Backup before deployment
./scripts/backup.sh

# Pull new images
docker-compose pull

# Run database migrations
docker-compose run --rm telegram-bot alembic upgrade head

# Rolling update
docker-compose up -d --no-deps telegram-bot

# Health check
echo "Waiting for service to be ready..."
for i in {1..30}; do
    if curl -f http://localhost/health > /dev/null 2>&1; then
        echo "Service is healthy!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 10
done

# Cleanup old images
docker image prune -f

echo "Deployment completed successfully!"
```

### 2. Rollback процедура

```bash
#!/bin/bash
# scripts/rollback.sh

set -e

BACKUP_DIR=${1}

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

echo "Rolling back to backup: $BACKUP_DIR"

# Stop services
docker-compose down

# Restore database
echo "Restoring database..."
gunzip -c $BACKUP_DIR/postgres.sql.gz | docker-compose exec -T postgres psql -U postgres -d telegram_bot

# Restore Redis
echo "Restoring Redis..."
docker-compose exec -T redis redis-cli --pipe < $BACKUP_DIR/redis.rdb

# Restore file storage
echo "Restoring file storage..."
tar -xzf $BACKUP_DIR/storage.tar.gz -C /opt/telegram-bot/

# Start services
docker-compose up -d

echo "Rollback completed!"
```

## Troubleshooting

### Общие проблемы и решения

#### 1. Проблемы с подключением к базе данных

```bash
# Проверка статуса PostgreSQL
docker-compose exec postgres pg_isready -U postgres

# Проверка логов PostgreSQL
docker-compose logs postgres

# Подключение к базе данных
docker-compose exec postgres psql -U postgres -d telegram_bot

# Проверка соединений
docker-compose exec postgres psql -U postgres -c "SELECT * FROM pg_stat_activity;"
```

#### 2. Проблемы с Redis

```bash
# Проверка статуса Redis
docker-compose exec redis redis-cli ping

# Проверка использования памяти
docker-compose exec redis redis-cli info memory

# Очистка кэша (осторожно!)
docker-compose exec redis redis-cli flushall
```

#### 3. Проблемы с Qdrant

```bash
# Проверка статуса Qdrant
curl http://localhost:6333/

# Проверка коллекций
curl http://localhost:6333/collections

# Проверка логов
docker-compose logs qdrant
```

#### 4. Проблемы с производительностью

```bash
# Мониторинг ресурсов
docker stats

# Проверка использования диска
df -h
du -sh /opt/telegram-bot/*

# Анализ медленных запросов PostgreSQL
docker-compose exec postgres psql -U postgres -d telegram_bot -c "
SELECT query, mean_time, calls, total_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;"
```

### Логи и диагностика

#### Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f telegram-bot

# Последние 100 строк
docker-compose logs --tail=100 telegram-bot

# Логи с временными метками
docker-compose logs -t telegram-bot
```

#### Мониторинг метрик
```bash
# Prometheus метрики
curl http://localhost:9090/metrics

# Метрики приложения
curl http://localhost:8000/metrics

# Health check
curl http://localhost/health
```

## Безопасность

### 1. Настройка файрвола

```bash
# Закрытие ненужных портов
sudo ufw deny 5432  # PostgreSQL
sudo ufw deny 6379  # Redis
sudo ufw deny 6333  # Qdrant
sudo ufw deny 9090  # Prometheus
sudo ufw deny 3000  # Grafana

# Разрешение только для локальной сети
sudo ufw allow from 10.0.0.0/8 to any port 5432
sudo ufw allow from 172.16.0.0/12 to any port 6379
```

### 2. Обновление системы

```bash
# Регулярные обновления
sudo apt update && sudo apt upgrade -y

# Автоматические обновления безопасности
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 3. Мониторинг безопасности

```bash
# Установка fail2ban
sudo apt install -y fail2ban

# Конфигурация fail2ban
sudo tee /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
port = http,https
logpath = /opt/telegram-bot/logs/nginx/error.log
EOF

sudo systemctl restart fail2ban
```

## Заключение

Данная документация покрывает основные аспекты развертывания Telegram-бота для онбординга сотрудников. Для успешного развертывания рекомендуется:

1. **Тестирование**: Всегда тестируйте развертывание в staging окружении
2. **Мониторинг**: Настройте полноценный мониторинг и алерты
3. **Резервное копирование**: Регулярно создавайте backup'ы
4. **Безопасность**: Следуйте best practices по безопасности
5. **Документация**: Ведите актуальную документацию изменений

При возникновении проблем обращайтесь к разделу Troubleshooting или создавайте issue в репозитории проекта.