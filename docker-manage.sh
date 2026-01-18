#!/bin/bash

# Docker Management Script for AI Bot Application
# This script provides easy commands to manage the Docker environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Docker Compose command (will be set by check_docker_compose)
DOCKER_COMPOSE=""

# Function to check if Docker Compose is available
check_docker_compose() {
    # Check for new docker compose (plugin) first
    if docker compose version > /dev/null 2>&1; then
        DOCKER_COMPOSE="docker compose"
        return 0
    fi
    
    # Check for old docker-compose (standalone)
    if command -v docker-compose > /dev/null 2>&1; then
        DOCKER_COMPOSE="docker-compose"
        return 0
    fi
    
    print_error "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
}

# Development environment functions
dev_build() {
    print_header "Building Development Environment"
    $DOCKER_COMPOSE build --no-cache
}

dev_up() {
    print_header "Starting Development Environment"
    $DOCKER_COMPOSE up -d
    print_status "Development environment started successfully!"
    print_status "API available at: http://localhost:8000"
    print_status "API docs available at: http://localhost:8000/docs"
}

dev_down() {
    print_header "Stopping Development Environment"
    $DOCKER_COMPOSE down
    print_status "Development environment stopped successfully!"
}

dev_logs() {
    print_header "Showing Development Logs"
    $DOCKER_COMPOSE logs -f "${2:-}"
}

dev_shell() {
    print_header "Opening Shell in Development Container"
    $DOCKER_COMPOSE exec app bash
}

# Production environment functions
prod_build() {
    print_header "Building Production Environment"
    if [ ! -f .env.prod ]; then
        print_error "Production environment file (.env.prod) not found!"
        print_warning "Please create .env.prod file with production configuration."
        print_warning "Example: cp .env.prod.example .env.prod"
        exit 1
    fi
    $DOCKER_COMPOSE -f docker-compose.prod.yml --env-file .env.prod build --no-cache
}

prod_up() {
    print_header "Starting Production Environment"
    if [ ! -f .env.prod ]; then
        print_error "Production environment file (.env.prod) not found!"
        print_warning "Please create .env.prod file with production configuration."
        exit 1
    fi
    $DOCKER_COMPOSE -f docker-compose.prod.yml --env-file .env.prod up -d
    print_status "Production environment started successfully!"
    print_status "API available at: http://localhost:8000"
}

prod_down() {
    print_header "Stopping Production Environment"
    $DOCKER_COMPOSE -f docker-compose.prod.yml --env-file .env.prod down
    print_status "Production environment stopped successfully!"
}

prod_logs() {
    print_header "Showing Production Logs"
    $DOCKER_COMPOSE -f docker-compose.prod.yml --env-file .env.prod logs -f "${2:-}"
}

prod_shell() {
    print_header "Opening Shell in Production Container"
    $DOCKER_COMPOSE -f docker-compose.prod.yml --env-file .env.prod exec app bash
}

# Database management functions
db_migrate() {
    print_header "Running Database Migrations"
    if [ "$1" = "prod" ]; then
        $DOCKER_COMPOSE -f docker-compose.prod.yml --env-file .env.prod exec app alembic upgrade head
    else
        $DOCKER_COMPOSE exec app alembic upgrade head
    fi
    print_status "Database migrations completed successfully!"
}

db_shell() {
    print_header "Opening Database Shell"
    if [ "$1" = "prod" ]; then
        $DOCKER_COMPOSE -f docker-compose.prod.yml --env-file .env.prod exec postgres psql -U ${POSTGRES_USER:-user} -d ${POSTGRES_DB:-onboarding_bot}
    else
        $DOCKER_COMPOSE exec postgres psql -U ${POSTGRES_USER:-user} -d ${POSTGRES_DB:-onboarding_bot}
    fi
}

db_backup() {
    print_header "Creating Database Backup"
    local backup_file="backup_$(date +%Y%m%d_%H%M%S).sql"
    if [ "$1" = "prod" ]; then
        $DOCKER_COMPOSE -f docker-compose.prod.yml --env-file .env.prod exec -T postgres pg_dump -U ${POSTGRES_USER:-user} -d ${POSTGRES_DB:-onboarding_bot} > "$backup_file"
    else
        $DOCKER_COMPOSE exec -T postgres pg_dump -U ${POSTGRES_USER:-user} -d ${POSTGRES_DB:-onboarding_bot} > "$backup_file"
    fi
    print_status "Database backup created: $backup_file"
}


# Cleanup functions
cleanup() {
    print_header "Cleaning Up Docker Resources"
    print_warning "This will remove all stopped containers, unused networks, and dangling images."
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker system prune -f
        print_status "Cleanup completed!"
    else
        print_status "Cleanup cancelled."
    fi
}

cleanup_all() {
    print_header "Cleaning Up All Docker Resources"
    print_error "WARNING: This will remove ALL Docker containers, images, volumes, and networks!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker system prune -a -f --volumes
        print_status "Complete cleanup finished!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Health check function
health_check() {
    print_header "Checking Service Health"
    local env_flag=""
    if [ "$1" = "prod" ]; then
        env_flag="-f docker-compose.prod.yml --env-file .env.prod"
    fi
    
    echo "Service Status:"
    $DOCKER_COMPOSE $env_flag ps
    
    echo -e "\nHealth Checks:"
    curl -f http://localhost:8000/health 2>/dev/null && echo -e "\n✅ API Health: OK" || echo -e "\n❌ API Health: FAILED"
    
    # Check database connection
    if $DOCKER_COMPOSE $env_flag exec -T postgres pg_isready -U ${POSTGRES_USER:-user} -d ${POSTGRES_DB:-onboarding_bot} > /dev/null 2>&1; then
        echo "✅ Database: OK"
    else
        echo "❌ Database: FAILED"
    fi
    
    # Check Redis connection
    if $DOCKER_COMPOSE $env_flag exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis: OK"
    else
        echo "❌ Redis: FAILED"
    fi
    
    # Check Qdrant connection
    if curl -f http://localhost:6333/health > /dev/null 2>&1; then
        echo "✅ Qdrant: OK"
    else
        echo "❌ Qdrant: FAILED"
    fi
}

# Help function
show_help() {
    echo "AI Bot Docker Management Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Development Commands:"
    echo "  dev:build         Build development environment"
    echo "  dev:up            Start development environment"
    echo "  dev:down          Stop development environment"
    echo "  dev:logs [service] Show development logs"
    echo "  dev:shell         Open shell in development container"
    echo ""
    echo "Production Commands:"
    echo "  prod:build        Build production environment"
    echo "  prod:up           Start production environment"
    echo "  prod:down         Stop production environment"
    echo "  prod:logs [service] Show production logs"
    echo "  prod:shell        Open shell in production container"
    echo ""
    echo "Database Commands:"
    echo "  db:migrate [prod] Run database migrations"
    echo "  db:shell [prod]   Open database shell"
    echo "  db:backup [prod]  Create database backup"
    echo ""
    echo "Utility Commands:"
    echo "  health [prod]     Check service health"
    echo "  cleanup           Clean up Docker resources"
    echo "  cleanup:all       Clean up ALL Docker resources (DANGEROUS)"
    echo "  help              Show this help message"
    echo ""
}

# Main script logic
main() {
    check_docker
    check_docker_compose
    
    case "${1:-help}" in
        "dev:build")
            dev_build
            ;;
        "dev:up")
            dev_up
            ;;
        "dev:down")
            dev_down
            ;;
        "dev:logs")
            dev_logs "$@"
            ;;
        "dev:shell")
            dev_shell
            ;;
        "prod:build")
            prod_build
            ;;
        "prod:up")
            prod_up
            ;;
        "prod:down")
            prod_down
            ;;
        "prod:logs")
            prod_logs "$@"
            ;;
        "prod:shell")
            prod_shell
            ;;
        "db:migrate")
            db_migrate "$2"
            ;;
        "db:shell")
            db_shell "$2"
            ;;
        "db:backup")
            db_backup "$2"
            ;;
        "health")
            health_check "$2"
            ;;
        "cleanup")
            cleanup
            ;;
        "cleanup:all")
            cleanup_all
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Run main function with all arguments
main "$@"