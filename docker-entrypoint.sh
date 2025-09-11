#!/bin/bash
set -e

# Function to wait for a service to be ready
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    
    echo "Waiting for $service_name to be ready at $host:$port..."
    while ! nc -z "$host" "$port"; do
        sleep 1
    done
    echo "$service_name is ready!"
}

# Function to run database migrations
run_migrations() {
    echo "Running database migrations..."
    alembic upgrade head
    echo "Database migrations completed!"
}

# Function to initialize vector store
init_vector_store() {
    echo "Initializing vector store..."
    python -c "
import asyncio
from app.ai.langchain.vector_store import vector_store

async def init():
    try:
        await vector_store.initialize_collection()
        print('Vector store initialized successfully!')
    except Exception as e:
        print(f'Vector store initialization failed: {e}')
        # Don't fail the startup if vector store init fails
        pass

asyncio.run(init())
"
}

# Wait for required services
if [ "$WAIT_FOR_DB" = "true" ]; then
    wait_for_service "${DATABASE_HOST:-postgres}" "${DATABASE_PORT:-5432}" "PostgreSQL"
fi

if [ "$WAIT_FOR_REDIS" = "true" ]; then
    wait_for_service "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" "Redis"
fi

if [ "$WAIT_FOR_QDRANT" = "true" ]; then
    wait_for_service "${QDRANT_HOST:-qdrant}" "${QDRANT_PORT:-6333}" "Qdrant"
fi

# Run migrations if requested
if [ "$RUN_MIGRATIONS" = "true" ]; then
    run_migrations
fi

# Initialize vector store if requested
if [ "$INIT_VECTOR_STORE" = "true" ]; then
    init_vector_store
fi

# Execute the main command
exec "$@"