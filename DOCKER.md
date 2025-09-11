# Docker Configuration for AI Bot Application

This document provides comprehensive information about the Docker setup for the AI Bot application, including all services, configuration options, and deployment strategies.

## 🏗️ Architecture Overview

The application uses a microservices architecture with the following components:

- **FastAPI Application**: Main web API server
- **Telegram Bot**: Separate bot service for handling Telegram interactions
- **PostgreSQL**: Primary database for application data
- **Redis**: Caching and session storage
- **Qdrant**: Vector database for AI embeddings
- **Nginx**: Reverse proxy and load balancer (production only)
- **Prometheus**: Metrics collection and monitoring
- **Grafana**: Metrics visualization and dashboards

## 📁 File Structure

```
├── Dockerfile                          # Multi-stage Docker build
├── docker-compose.yml                  # Development environment
├── docker-compose.prod.yml             # Production environment
├── docker-entrypoint.sh               # Application entrypoint script
├── docker-manage.sh                   # Management script
├── .env                               # Development environment variables
├── .env.prod                          # Production environment variables
└── docker/                           # Docker configuration files
    ├── postgres/
    │   └── init/
    │       └── 01-init.sql           # Database initialization
    ├── redis/
    │   └── redis.conf                # Redis configuration
    ├── qdrant/
    │   └── config/
    │       └── config.yaml           # Qdrant configuration
    ├── nginx/
    │   ├── nginx.conf                # Main Nginx configuration
    │   └── conf.d/
    │       └── default.conf          # Server configuration
    ├── prometheus/
    │   └── prometheus.yml            # Prometheus configuration
    └── grafana/
        ├── datasources/
        │   └── prometheus.yml        # Grafana datasource
        └── dashboards/
            └── dashboard.yml         # Dashboard provisioning
```

## 🚀 Quick Start

### Development Environment

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd ai_bot
   cp .env.example .env
   # Edit .env with your configuration (passwords, API keys, etc.)
   ```

2. **Start services**:
   ```bash
   ./docker-manage.sh dev:up
   ```

3. **Access services**:
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379
   - Qdrant: http://localhost:6333

### Production Environment

1. **Setup environment**:
   ```bash
   cp .env.example .env.prod
   # Edit .env.prod with production values (secure passwords, real API keys, etc.)
   ```

2. **Deploy**:
   ```bash
   ./docker-manage.sh prod:up
   ```

3. **Access services**:
   - API: http://localhost:8000
   - Grafana: http://localhost:3000
   - Prometheus: http://localhost:9090

## 🐳 Docker Images

### Application Image (Multi-stage)

The main Dockerfile uses multi-stage builds:

- **Base Stage**: Common dependencies and system packages
- **Development Stage**: Includes dev dependencies and debugging tools
- **Production Stage**: Optimized for production with minimal dependencies

### External Images

- `postgres:15-alpine`: Lightweight PostgreSQL database
- `redis:7-alpine`: Redis cache server
- `qdrant/qdrant:latest`: Vector database for AI embeddings
- `nginx:alpine`: Reverse proxy (production only)
- `prom/prometheus:latest`: Metrics collection
- `grafana/grafana:latest`: Metrics visualization

## 🔧 Configuration

### Environment Variables

#### Database Configuration
```bash
POSTGRES_DB=onboarding_bot
POSTGRES_USER=user
POSTGRES_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
DATABASE_ECHO=false
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

#### Redis Configuration
```bash
REDIS_PASSWORD=your_redis_password_here
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
REDIS_MAX_CONNECTIONS=10
```

#### Qdrant Configuration
```bash
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=your_api_key
QDRANT_COLLECTION_NAME=onboarding_documents
```

#### AI Services
```bash
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4-turbo-preview
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langchain_key
```

#### Telegram Bot
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
```

### Service Coordination

The entrypoint script handles:
- **Service Dependencies**: Waits for required services to be ready
- **Database Migrations**: Runs Alembic migrations automatically
- **Vector Store Initialization**: Sets up Qdrant collections
- **Health Checks**: Validates service connectivity
- **Environment Variables**: All sensitive data loaded from .env files

## 📊 Monitoring

### Health Checks

All services include comprehensive health checks:

- **Application**: HTTP endpoint `/health`
- **PostgreSQL**: `pg_isready` command
- **Redis**: `redis-cli ping`
- **Qdrant**: HTTP health endpoint

### Metrics Collection

- **Prometheus**: Collects metrics from all services
- **Grafana**: Provides visualization dashboards
- **Application Metrics**: Custom metrics via `/metrics` endpoint

## 🔒 Security

### Production Security Features

- **Non-root User**: Application runs as dedicated user
- **Secret Management**: All passwords and API keys from .env files
- **Network Isolation**: Services communicate via internal network
- **SSL/TLS**: Nginx handles SSL termination
- **Rate Limiting**: API rate limiting via Nginx
- **Security Headers**: Comprehensive HTTP security headers
- **Environment Separation**: Different .env files for dev/prod

### Development Security

- **Local Only**: Services bound to localhost
- **Debug Mode**: Enhanced logging and debugging
- **Hot Reload**: Code changes reflected immediately

## 📈 Scaling

### Horizontal Scaling

The architecture supports horizontal scaling:

- **Application Replicas**: Multiple app containers behind load balancer
- **Database Connection Pooling**: Efficient database connections
- **Redis Clustering**: Redis can be clustered for high availability
- **Stateless Design**: Application containers are stateless

### Resource Management

Production deployment includes resource limits:

```yaml
deploy:
  resources:
    limits:
      memory: 2G
    reservations:
      memory: 1G
```

## 🛠️ Management Commands

Use the `docker-manage.sh` script for common operations:

### Development
```bash
./docker-manage.sh dev:build      # Build development images
./docker-manage.sh dev:up         # Start development environment
./docker-manage.sh dev:down       # Stop development environment
./docker-manage.sh dev:logs       # View logs
./docker-manage.sh dev:shell      # Open shell in container
```

### Production
```bash
./docker-manage.sh prod:build     # Build production images
./docker-manage.sh prod:up        # Start production environment
./docker-manage.sh prod:down      # Stop production environment
./docker-manage.sh prod:logs      # View logs
./docker-manage.sh prod:shell     # Open shell in container
```

### Database
```bash
./docker-manage.sh db:migrate     # Run migrations
./docker-manage.sh db:shell       # Open database shell
./docker-manage.sh db:backup      # Create backup
```

### Monitoring
```bash
./docker-manage.sh monitoring:up  # Start monitoring services
./docker-manage.sh health         # Check service health
```

### Maintenance
```bash
./docker-manage.sh cleanup        # Clean unused resources
./docker-manage.sh cleanup:all    # Clean all resources (DANGEROUS)
```

## 🔍 Troubleshooting

### Common Issues

1. **Port Conflicts**:
   ```bash
   # Check what's using the port
   lsof -i :8000
   # Kill the process or change port in docker-compose.yml
   ```

2. **Permission Issues**:
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   chmod +x docker-manage.sh
   ```

3. **Database Connection Issues**:
   ```bash
   # Check database logs
   ./docker-manage.sh dev:logs postgres
   # Verify database is ready
   ./docker-manage.sh health
   ```

4. **Memory Issues**:
   ```bash
   # Check container resource usage
   docker stats
   # Increase Docker memory limit in Docker Desktop
   ```

### Debugging

1. **Application Logs**:
   ```bash
   ./docker-manage.sh dev:logs app
   ```

2. **Service Status**:
   ```bash
   docker-compose ps
   ./docker-manage.sh health
   ```

3. **Container Shell Access**:
   ```bash
   ./docker-manage.sh dev:shell
   ```

4. **Database Inspection**:
   ```bash
   ./docker-manage.sh db:shell
   ```

## 🚀 Deployment

### Development Deployment

1. Ensure Docker and Docker Compose are installed
2. Clone repository and configure `.env`
3. Run `./docker-manage.sh dev:up`
4. Access application at http://localhost:8000

### Production Deployment

1. **Server Setup**:
   - Install Docker and Docker Compose
   - Configure firewall (ports 80, 443)
   - Set up SSL certificates

2. **Application Deployment**:
   ```bash
   # Clone repository
   git clone <repository>
   cd ai_bot
   
   # Configure production environment
   cp .env.prod.example .env.prod
   # Edit .env.prod with production values
   
   # Deploy
   ./docker-manage.sh prod:build
   ./docker-manage.sh prod:up
   ```

3. **SSL Configuration**:
   - Place SSL certificates in `docker/nginx/ssl/`
   - Uncomment HTTPS server block in `docker/nginx/conf.d/default.conf`
   - Restart Nginx: `docker-compose -f docker-compose.prod.yml restart nginx`

### CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to server
        run: |
          ssh user@server 'cd /app && git pull && ./docker-manage.sh prod:build && ./docker-manage.sh prod:up'
```

## 📝 Best Practices

1. **Environment Separation**: Use different compose files for dev/prod
2. **Secret Management**: Never commit secrets to version control
3. **Resource Limits**: Set appropriate memory and CPU limits
4. **Health Checks**: Implement comprehensive health checks
5. **Logging**: Use structured logging with appropriate levels
6. **Monitoring**: Set up alerts for critical metrics
7. **Backups**: Regular database and volume backups
8. **Updates**: Keep base images and dependencies updated

## 🆘 Support

For issues and questions:

1. Check this documentation
2. Review application logs
3. Check service health status
4. Consult Docker Compose documentation
5. Open an issue in the repository

---

**Note**: This Docker configuration is designed for both development and production use. Always review and customize the configuration for your specific deployment requirements.