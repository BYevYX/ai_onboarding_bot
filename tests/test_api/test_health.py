"""
Tests for health check endpoints.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.api.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check_healthy(self, client):
        """Test health check when all services are healthy."""
        with patch('app.api.routes.health.cache_manager') as mock_cache, \
             patch('app.api.routes.health.vector_store') as mock_vector, \
             patch('app.api.routes.health.llm_manager') as mock_llm:
            
            # Mock healthy services
            mock_cache.get_redis.return_value.ping = AsyncMock()
            mock_vector.get_client.return_value.get_collections.return_value = []
            mock_llm.get_chat_model.return_value = True
            
            response = client.get("/health/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "degraded"]
            assert "timestamp" in data
            assert "version" in data
            assert "services" in data
    
    def test_readiness_check(self, client):
        """Test readiness check."""
        with patch('app.api.routes.health.vector_store') as mock_vector:
            mock_vector.initialize_collection = AsyncMock(return_value=True)
            
            response = client.get("/health/ready")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "timestamp" in data
    
    def test_liveness_check(self, client):
        """Test liveness check."""
        response = client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data
    
    def test_health_check_degraded(self, client):
        """Test health check when some services are unhealthy."""
        with patch('app.api.routes.health.cache_manager') as mock_cache, \
             patch('app.api.routes.health.vector_store') as mock_vector, \
             patch('app.api.routes.health.llm_manager') as mock_llm:
            
            # Mock unhealthy Redis
            mock_cache.get_redis.return_value.ping = AsyncMock(side_effect=Exception("Connection failed"))
            mock_vector.get_client.return_value.get_collections.return_value = []
            mock_llm.get_chat_model.return_value = True
            
            response = client.get("/health/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["services"]["redis"] == "unhealthy"