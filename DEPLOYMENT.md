# 🚀 Инструкция по развертыванию AI Bot на сервере

Эта инструкция содержит пошаговое руководство по первоначальной настройке сервера и запуску приложения через Docker.

---

## 📋 Содержание

1. [Требования к серверу](#требования-к-серверу)
2. [Первоначальная настройка сервера](#первоначальная-настройка-сервера)
3. [Настройка переменных окружения](#настройка-переменных-окружения)
4. [Запуск приложения](#запуск-приложения)
5. [Настройка SSL (HTTPS)](#настройка-ssl-https)
6. [Мониторинг и логирование](#мониторинг-и-логирование)
7. [Обновление приложения](#обновление-приложения)
8. [Резервное копирование](#резервное-копирование)
9. [Устранение неполадок](#устранение-неполадок)

---

## 📦 Требования к серверу

### Минимальные требования:
- **CPU**: 2 vCPU
- **RAM**: 4 GB
- **Диск**: 20 GB SSD
- **ОС**: Ubuntu 22.04 LTS / Debian 11+ / CentOS 8+

### Рекомендуемые требования (для production):
- **CPU**: 4 vCPU
- **RAM**: 8 GB
- **Диск**: 50 GB SSD
- **ОС**: Ubuntu 22.04 LTS

### Открытые порты:
- `22` - SSH
- `80` - HTTP
- `443` - HTTPS

---

## 🔧 Первоначальная настройка сервера

### Шаг 1: Подключение к серверу

```bash
ssh root@YOUR_SERVER_IP
```

### Шаг 2: Обновление системы

```bash
# Ubuntu/Debian
apt update && apt upgrade -y

# CentOS/RHEL
dnf update -y
```

### Шаг 3: Установка Docker

```bash
# Удаляем старые версии (если есть)
apt remove docker docker-engine docker.io containerd runc

# Устанавливаем необходимые пакеты
apt install -y ca-certificates curl gnupg lsb-release

# Добавляем официальный GPG ключ Docker
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Добавляем репозиторий Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Устанавливаем Docker Engine
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Шаг 4: Проверка установки Docker

```bash
docker --version
docker compose version
```

### Шаг 5: Настройка Docker для запуска без sudo (опционально)

```bash
# Создаем группу docker (если не существует)
groupadd docker

# Добавляем текущего пользователя в группу
usermod -aG docker $USER

# Применяем изменения
newgrp docker
```

### Шаг 6: Установка дополнительных утилит

```bash
apt install -y git curl wget htop nano
```

### Шаг 7: Настройка firewall (UFW)

```bash
# Включаем UFW
ufw enable

# Разрешаем SSH
ufw allow 22

# Разрешаем HTTP и HTTPS
ufw allow 80
ufw allow 443

# Проверяем статус
ufw status
```

### Шаг 8: Клонирование репозитория

```bash
# Создаем директорию для приложения
mkdir -p /opt/apps
cd /opt/apps

# Клонируем репозиторий
git clone YOUR_REPOSITORY_URL ai_bot
cd ai_bot

# Даем права на выполнение скриптам
chmod +x docker-manage.sh docker-entrypoint.sh
```

---

## ⚙️ Настройка переменных окружения

### Шаг 1: Создание файла .env.prod

```bash
# Копируем шаблон
cp .env.prod.example .env.prod

# Открываем для редактирования
nano .env.prod
```

### Шаг 2: Заполнение переменных

Откройте файл `.env.prod` и заполните следующие **ОБЯЗАТЕЛЬНЫЕ** параметры:

#### 🔐 Безопасность (Security)

| Параметр | Описание | Как получить |
|----------|----------|--------------|
| `SECRET_KEY` | Секретный ключ приложения | Сгенерируйте: `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL | Сгенерируйте: `openssl rand -base64 24` |
| `REDIS_PASSWORD` | Пароль Redis | Сгенерируйте: `openssl rand -base64 24` |

#### 🤖 Telegram Bot

| Параметр | Описание | Как получить |
|----------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота | 1. Откройте Telegram<br>2. Найдите @BotFather<br>3. Отправьте `/newbot`<br>4. Следуйте инструкциям<br>5. Скопируйте токен |

#### 🧠 OpenAI API

| Параметр | Описание | Как получить |
|----------|----------|--------------|
| `OPENAI_API_KEY` | API ключ OpenAI | 1. Зарегистрируйтесь на [platform.openai.com](https://platform.openai.com)<br>2. Перейдите в [API Keys](https://platform.openai.com/api-keys)<br>3. Нажмите "Create new secret key"<br>4. Скопируйте ключ |

#### 📊 Мониторинг (Опционально, но рекомендуется)

| Параметр | Описание | Как получить |
|----------|----------|--------------|
| `SENTRY_DSN` | DSN для Sentry | 1. Зарегистрируйтесь на [sentry.io](https://sentry.io)<br>2. Создайте проект (Python)<br>3. Скопируйте DSN |
| `LANGCHAIN_API_KEY` | API ключ LangSmith | 1. Зарегистрируйтесь на [smith.langchain.com](https://smith.langchain.com)<br>2. Перейдите в Settings → API Keys<br>3. Создайте новый ключ |

### Шаг 3: Пример заполненного файла

```bash
# Пример .env.prod (НЕ ИСПОЛЬЗУЙТЕ эти значения!)

ENVIRONMENT=production

# Database
POSTGRES_DB=onboarding_bot
POSTGRES_USER=user
POSTGRES_PASSWORD=Xk9mNp2qRs5tVw8yAb3cDf6gHj
DATABASE_URL=postgresql+asyncpg://user:Xk9mNp2qRs5tVw8yAb3cDf6gHj@postgres:5432/onboarding_bot

# Redis
REDIS_PASSWORD=Lm4nOp7qRs0tUv3wXy6zA
REDIS_URL=redis://:Lm4nOp7qRs0tUv3wXy6zA@redis:6379/0

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Telegram
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Security
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

### Шаг 4: Проверка синхронизации паролей

**ВАЖНО**: Убедитесь, что пароли в URL совпадают с отдельными переменными:

```bash
# Пароль в POSTGRES_PASSWORD должен совпадать с паролем в DATABASE_URL
POSTGRES_PASSWORD=MyPassword123
DATABASE_URL=postgresql+asyncpg://user:MyPassword123@postgres:5432/onboarding_bot
#                                    ^^^^^^^^^^^^^^^ <- тот же пароль

# Пароль в REDIS_PASSWORD должен совпадать с паролем в REDIS_URL
REDIS_PASSWORD=MyRedisPassword456
REDIS_URL=redis://:MyRedisPassword456@redis:6379/0
#                 ^^^^^^^^^^^^^^^^^^ <- тот же пароль
```

---

## 🚀 Запуск приложения

### Вариант 1: Использование docker-manage.sh (рекомендуется)

```bash
# Сборка образов
./docker-manage.sh prod:build

# Запуск всех сервисов
./docker-manage.sh prod:up

# Проверка статуса
./docker-manage.sh health prod
```

### Вариант 2: Использование Docker Compose напрямую

```bash
# Сборка образов
docker compose -f docker-compose.prod.yml --env-file .env.prod build

# Запуск в фоновом режиме
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Проверка статуса контейнеров
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
```

### Проверка запуска

```bash
# Проверка логов
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f

# Проверка здоровья API
curl http://localhost:8000/health

# Ожидаемый ответ:
# {"status":"healthy","database":"connected","redis":"connected","qdrant":"connected"}
```

### Остановка приложения

```bash
# Через скрипт
./docker-manage.sh prod:down

# Или напрямую
docker compose -f docker-compose.prod.yml --env-file .env.prod down
```

---

## 🔒 Настройка SSL (HTTPS)

### Вариант 1: Let's Encrypt (рекомендуется)

```bash
# Установка certbot
apt install -y certbot

# Остановка nginx временно
docker compose -f docker-compose.prod.yml --env-file .env.prod stop nginx

# Получение сертификата
certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Копирование сертификатов
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/nginx/ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/nginx/ssl/key.pem
```

### Шаг 2: Настройка Nginx для HTTPS

Отредактируйте файл `docker/nginx/conf.d/default.conf`:

```bash
nano docker/nginx/conf.d/default.conf
```

Раскомментируйте секцию HTTPS в конце файла и замените `your-domain.com` на ваш домен.

### Шаг 3: Перезапуск Nginx

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod restart nginx
```

### Автоматическое обновление сертификатов

```bash
# Создаем cron задачу
crontab -e

# Добавляем строку (обновление каждый месяц):
0 0 1 * * certbot renew --quiet && cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /opt/apps/ai_bot/docker/nginx/ssl/cert.pem && cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /opt/apps/ai_bot/docker/nginx/ssl/key.pem && docker compose -f /opt/apps/ai_bot/docker-compose.prod.yml restart nginx
```

---

## 📊 Мониторинг и логирование

### Просмотр логов

```bash
# Все сервисы
./docker-manage.sh prod:logs

# Конкретный сервис
./docker-manage.sh prod:logs app
./docker-manage.sh prod:logs bot
./docker-manage.sh prod:logs postgres
./docker-manage.sh prod:logs redis
./docker-manage.sh prod:logs qdrant
```

### Мониторинг ресурсов

```bash
# Использование ресурсов контейнерами
docker stats

# Использование диска
docker system df
```

### Доступ к Sentry

Если вы настроили `SENTRY_DSN`, все ошибки будут автоматически отправляться в Sentry.
Перейдите на [sentry.io](https://sentry.io) для просмотра ошибок.

---

## 🔄 Обновление приложения

### Стандартное обновление

```bash
cd /opt/apps/ai_bot

# Получаем последние изменения
git pull origin main

# Пересобираем образы
./docker-manage.sh prod:build

# Перезапускаем с минимальным простоем
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --no-deps --build app bot
```

### Обновление с миграциями БД

```bash
cd /opt/apps/ai_bot

# Получаем последние изменения
git pull origin main

# Пересобираем образы
./docker-manage.sh prod:build

# Останавливаем приложение
./docker-manage.sh prod:down

# Запускаем (миграции выполнятся автоматически)
./docker-manage.sh prod:up
```

---

## 💾 Резервное копирование

### Резервная копия базы данных

```bash
# Создание бэкапа
./docker-manage.sh db:backup prod

# Файл будет создан: backup_YYYYMMDD_HHMMSS.sql
```

### Автоматическое резервное копирование

```bash
# Создаем скрипт бэкапа
cat > /opt/apps/ai_bot/backup.sh << 'EOF'
#!/bin/bash
cd /opt/apps/ai_bot
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Бэкап БД
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T postgres pg_dump -U user onboarding_bot > $BACKUP_DIR/db_$DATE.sql

# Бэкап uploads
docker cp ai_bot_app_prod:/app/uploads $BACKUP_DIR/uploads_$DATE

# Удаляем старые бэкапы (старше 7 дней)
find $BACKUP_DIR -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /opt/apps/ai_bot/backup.sh

# Добавляем в cron (ежедневно в 3:00)
crontab -e
# Добавить: 0 3 * * * /opt/apps/ai_bot/backup.sh >> /var/log/backup.log 2>&1
```

### Восстановление из бэкапа

```bash
# Восстановление БД
cat backup_file.sql | docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T postgres psql -U user onboarding_bot
```

---

## 🔍 Устранение неполадок

### Проблема: Контейнеры не запускаются

```bash
# Проверьте логи
docker compose -f docker-compose.prod.yml --env-file .env.prod logs

# Проверьте переменные окружения
docker compose -f docker-compose.prod.yml --env-file .env.prod config
```

### Проблема: Ошибка подключения к БД

```bash
# Проверьте, что PostgreSQL запущен
docker compose -f docker-compose.prod.yml --env-file .env.prod ps postgres

# Проверьте логи PostgreSQL
docker compose -f docker-compose.prod.yml --env-file .env.prod logs postgres

# Проверьте правильность пароля в .env.prod
# POSTGRES_PASSWORD должен совпадать с паролем в DATABASE_URL
```

### Проблема: Telegram бот не отвечает

```bash
# Проверьте логи бота
docker compose -f docker-compose.prod.yml --env-file .env.prod logs bot

# Проверьте токен
# Убедитесь, что TELEGRAM_BOT_TOKEN правильный

# Проверьте, что бот не запущен где-то еще
# (один токен = один экземпляр бота)
```

### Проблема: OpenAI API ошибки

```bash
# Проверьте логи приложения
docker compose -f docker-compose.prod.yml --env-file .env.prod logs app

# Частые причины:
# - Неверный API ключ
# - Закончился баланс на аккаунте OpenAI
# - Превышен лимит запросов
```

### Проблема: Недостаточно памяти

```bash
# Проверьте использование памяти
docker stats

# Увеличьте лимиты в docker-compose.prod.yml
# или добавьте swap на сервере:
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Очистка ресурсов Docker

```bash
# Удаление неиспользуемых образов и контейнеров
./docker-manage.sh cleanup

# ВНИМАНИЕ: Полная очистка (удалит все данные!)
./docker-manage.sh cleanup:all
```

---

## 📞 Полезные команды

```bash
# Вход в контейнер приложения
./docker-manage.sh prod:shell

# Вход в базу данных
./docker-manage.sh db:shell prod

# Выполнение миграций вручную
docker compose -f docker-compose.prod.yml --env-file .env.prod exec app alembic upgrade head

# Создание новой миграции
docker compose -f docker-compose.prod.yml --env-file .env.prod exec app alembic revision --autogenerate -m "description"

# Перезапуск конкретного сервиса
docker compose -f docker-compose.prod.yml --env-file .env.prod restart app

# Просмотр использования ресурсов
docker stats
```

---

## ✅ Чеклист развертывания

- [ ] Сервер настроен и Docker установлен
- [ ] Репозиторий склонирован в `/opt/apps/ai_bot`
- [ ] Создан файл `.env.prod` из `.env.prod.example`
- [ ] Заполнены все обязательные переменные:
  - [ ] `SECRET_KEY`
  - [ ] `POSTGRES_PASSWORD` и синхронизирован с `DATABASE_URL`
  - [ ] `REDIS_PASSWORD` и синхронизирован с `REDIS_URL`
  - [ ] `TELEGRAM_BOT_TOKEN`
  - [ ] `OPENAI_API_KEY`
- [ ] Образы собраны: `./docker-manage.sh prod:build`
- [ ] Приложение запущено: `./docker-manage.sh prod:up`
- [ ] Health check проходит: `curl http://localhost:8000/health`
- [ ] Telegram бот отвечает на сообщения
- [ ] (Опционально) SSL сертификаты настроены
- [ ] (Опционально) Автоматическое резервное копирование настроено

---

**Дата создания**: Январь 2026  
**Версия документа**: 1.0
