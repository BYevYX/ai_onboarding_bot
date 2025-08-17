# Telegram Onboarding Bot with LangChain/LangGraph

AI-powered Telegram bot for employee onboarding using LangChain and LangGraph frameworks.

## 🚀 Features

### Core Functionality
- **AI-Powered Conversations**: Uses LangChain and LangGraph for sophisticated AI workflows
- **RAG Architecture**: Retrieval-Augmented Generation with Qdrant vector database
- **Multi-language Support**: Russian, English, and Arabic languages
- **Role-Based Access Control**: Admin, HR, Manager, and Employee roles
- **Document Processing**: Automated indexing of PDF, DOCX, TXT, and Markdown files

### LangChain/LangGraph Integration
- **LangGraph Workflows**: State machine-based onboarding processes
- **LangChain Components**: Vector stores, embeddings, and document processing
- **OpenAI Integration**: GPT-4 and text-embedding-3-small models
- **Custom Tools**: Corporate-specific tools and workflows

### Technical Features
- **FastAPI REST API**: Comprehensive API for system management
- **PostgreSQL Database**: Async SQLAlchemy with Alembic migrations
- **Redis Caching**: Performance optimization and session storage
- **Docker Support**: Full containerization with docker-compose
- **Comprehensive Testing**: Unit and integration tests with pytest

## 📋 Requirements

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Qdrant vector database
- OpenAI API key

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd telegram-onboarding-bot
```

### 2. Install Dependencies
```bash
# For development
pip install -r requirements/dev.txt

# For production
pip install -r requirements/prod.txt
```

### 3. Environment Configuration
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Database Setup
```bash
# Run migrations
alembic upgrade head
```

### 5. Initialize Vector Store
```bash
# The vector store will be initialized automatically on first run
```

## 🚀 Usage

### Running the Bot
```bash
# Bot only (polling mode)
python main.py bot

# API server only
python main.py api

# Both bot and API
python main.py combined
```

### Using Docker
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📚 API Documentation

Once the API server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Health Checks
- `GET /health/` - System health status
- `GET /health/ready` - Readiness check
- `GET /health/live` - Liveness check

#### User Management
- `POST /api/v1/users/` - Create user
- `GET /api/v1/users/{user_id}` - Get user
- `PUT /api/v1/users/{user_id}` - Update user
- `GET /api/v1/users/` - List users

#### Document Management
- `POST /api/v1/documents/upload` - Upload document
- `POST /api/v1/documents/search` - Search documents
- `DELETE /api/v1/documents/{document_id}` - Delete document

#### Onboarding Workflow
- `POST /api/v1/onboarding/start` - Start onboarding
- `POST /api/v1/onboarding/message` - Process message
- `GET /api/v1/onboarding/{user_id}/status` - Get status
- `POST /api/v1/onboarding/{user_id}/complete` - Complete onboarding

## 🤖 Bot Commands

- `/start` - Begin onboarding process
- `/help` - Show help information
- `/status` - Check onboarding progress

## 🏗️ Architecture

### LangChain/LangGraph Components

#### Workflows
- **OnboardingWorkflow**: State machine for employee onboarding
- **DocumentReviewNode**: Process document interactions
- **QuestionsAnswersNode**: Handle Q&A sessions
- **CompletionNode**: Finalize onboarding process

#### Vector Store
- **QdrantVectorStore**: Document embeddings and similarity search
- **DocumentProcessor**: Automated document indexing
- **RAG Pipeline**: Context-aware response generation

#### LLM Integration
- **ChatOpenAI**: GPT-4 for conversations
- **OpenAIEmbeddings**: Text embeddings for RAG
- **Custom Prompts**: Multilingual system prompts

### Database Schema

#### Core Tables
- `users` - User information and profiles
- `onboarding_sessions` - Workflow state and progress
- `documents` - Document metadata and indexing
- `chat_messages` - Conversation history
- `audit_logs` - System event tracking

### Services Architecture
- **UserService**: User management operations
- **OnboardingService**: Workflow orchestration
- **DocumentProcessor**: File processing and indexing
- **VectorStore**: Semantic search and retrieval

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
```

## 📊 Monitoring

### Health Checks
- System health monitoring
- Service dependency checks
- Performance metrics

### Logging
- Structured JSON logging
- Correlation ID tracking
- Error tracking with Sentry

### Metrics
- Prometheus metrics export
- Custom business metrics
- Performance monitoring

## 🔧 Configuration

### Environment Variables

#### Required
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
OPENAI_API_KEY=your_openai_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
SECRET_KEY=your_secret_key
```

#### Optional
```bash
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379/0
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
```

### LangChain Configuration
- Model selection and parameters
- Embedding model configuration
- Vector store settings
- Workflow customization

## 🚀 Deployment

### Docker Deployment
```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes
```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/
```

### Environment-Specific Configs
- Development: Local services
- Staging: Shared resources
- Production: High availability setup

## 📈 Scaling

### Horizontal Scaling
- Multiple bot instances
- Load-balanced API servers
- Distributed vector store

### Performance Optimization
- Redis caching layer
- Database connection pooling
- Async processing queues

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements/dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests before committing
pytest
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` directory
- **Issues**: Create GitHub issues for bugs
- **Discussions**: Use GitHub discussions for questions

## 🔄 Changelog

### v0.1.0 (Current)
- Initial release with LangChain/LangGraph integration
- Complete onboarding workflow implementation
- Multi-language support (Russian, English, Arabic)
- RAG architecture with Qdrant vector store
- Comprehensive API and bot functionality
- Docker containerization and deployment configs

## 🎯 Roadmap

- [ ] Advanced analytics dashboard
- [ ] Integration with HR systems
- [ ] Voice message support
- [ ] Mobile app companion
- [ ] Advanced workflow customization
- [ ] Multi-tenant support

---

Built with ❤️ using LangChain, LangGraph, FastAPI, and aiogram.