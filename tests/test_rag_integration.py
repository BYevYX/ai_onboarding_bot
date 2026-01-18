"""
Integration tests for hybrid RAG system.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.rag.hybrid_rag_service import hybrid_rag_service, QueryComplexityAnalyzer
from app.ai.rag.vector_cache_service import vector_cache_service
from app.ai.langchain.llm_manager import llm_manager
from app.ai.langchain.vector_store import vector_store


class TestQueryComplexityAnalyzer:
    """Test query complexity analysis."""
    
    def test_simple_query_detection(self):
        """Test detection of simple queries."""
        simple_queries = [
            "что такое компания",
            "where is the office",
            "ما هو الراتب",
            "когда обед"
        ]
        
        for query in simple_queries:
            complexity = QueryComplexityAnalyzer.analyze_complexity(query)
            assert complexity == "simple", f"Query '{query}' should be simple"
    
    def test_complex_query_detection(self):
        """Test detection of complex queries."""
        complex_queries = [
            "объясни процедуру оформления отпуска и какие документы нужны",
            "explain the company policy on remote work and benefits",
            "اشرح سياسة الشركة حول العمل عن بُعد والمزايا",
            "расскажи подробно о карьерных возможностях"
        ]
        
        for query in complex_queries:
            complexity = QueryComplexityAnalyzer.analyze_complexity(query)
            assert complexity == "complex", f"Query '{query}' should be complex"


class TestVectorCacheService:
    """Test vector cache service functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test cache key generation."""
        key1 = vector_cache_service._generate_cache_key(
            "test", "query", user_id=123, param="value"
        )
        key2 = vector_cache_service._generate_cache_key(
            "test", "query", user_id=123, param="value"
        )
        
        assert key1 == key2, "Same parameters should generate same key"
        
        key3 = vector_cache_service._generate_cache_key(
            "test", "query", user_id=456, param="value"
        )
        
        assert key1 != key3, "Different parameters should generate different keys"
    
    @pytest.mark.asyncio
    async def test_embedding_cache(self):
        """Test embedding caching functionality."""
        with patch('app.core.cache.cache_manager') as mock_cache:
            mock_cache.set.return_value = True
            mock_cache.get.return_value = {
                "embedding": [0.1, 0.2, 0.3],
                "text": "test text",
                "model": "test-model"
            }
            
            # Test caching
            success = await vector_cache_service.cache_embeddings(
                "test text", [0.1, 0.2, 0.3], "test-model"
            )
            assert success
            
            # Test retrieval
            cached_embedding = await vector_cache_service.get_cached_embedding(
                "test text", "test-model"
            )
            assert cached_embedding == [0.1, 0.2, 0.3]


class TestHybridRAGService:
    """Test hybrid RAG service functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        user_id = 12345
        
        # Clear any existing rate limit data
        hybrid_rag_service._user_request_counts = {}
        
        # Test within limits
        for i in range(5):
            allowed = hybrid_rag_service._check_rate_limit(user_id)
            assert allowed, f"Request {i+1} should be allowed"
        
        # Test exceeding limits
        hybrid_rag_service._user_request_counts[user_id] = [
            hybrid_rag_service._user_request_counts[user_id][0]
        ] * 15  # Simulate 15 requests
        
        allowed = hybrid_rag_service._check_rate_limit(user_id)
        assert not allowed, "Request should be rate limited"
    
    @pytest.mark.asyncio
    async def test_user_memory_management(self):
        """Test user memory management."""
        user_id = 12345
        
        # Clear memory should work even if no memory exists
        success = await hybrid_rag_service.clear_user_memory(user_id)
        assert success is False  # No memory to clear
        
        # Get empty history
        history = await hybrid_rag_service.get_user_conversation_history(user_id)
        assert history == []
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality."""
        with patch('app.ai.langchain.vector_store.vector_store') as mock_vector_store, \
             patch('app.ai.langchain.llm_manager.llm_manager') as mock_llm:
            
            mock_vector_store.get_collection_info.return_value = {"points_count": 100}
            mock_llm.generate_response.return_value = "Test response"
            
            health = await hybrid_rag_service.health_check()
            
            assert health["status"] == "healthy"
            assert "vector_store" in health
            assert "llm" in health


class TestRAGIntegration:
    """Test full RAG integration."""
    
    @pytest.mark.asyncio
    async def test_query_processing_flow(self):
        """Test complete query processing flow."""
        with patch('app.ai.rag.hybrid_rag_service.vector_store') as mock_vector_store, \
             patch('app.ai.langchain.llm_manager.llm_manager') as mock_llm, \
             patch('app.ai.rag.vector_cache_service.vector_cache_service') as mock_cache:
            
            # Mock vector search results
            from langchain_core.documents import Document
            mock_docs = [
                (Document(page_content="Test content", metadata={"title": "Test"}), 0.9)
            ]
            mock_vector_store.similarity_search.return_value = mock_docs
            
            # Mock LLM response
            mock_llm.generate_response.return_value = "Test answer"
            
            # Mock cache operations
            mock_cache.cache_user_context.return_value = True
            mock_cache.get_cached_search_results.return_value = None
            mock_cache.cache_search_results.return_value = True
            
            # Test query processing
            result = await hybrid_rag_service.process_query(
                query="Test query",
                user_id=12345,
                language="ru"
            )
            
            assert "answer" in result
            assert "query_complexity" in result
            assert "processing_method" in result
    
    @pytest.mark.asyncio
    async def test_fallback_mechanism(self):
        """Test fallback mechanism when main processing fails."""
        with patch('app.ai.rag.hybrid_rag_service.vector_store') as mock_vector_store:
            
            # Mock vector store to raise exception
            mock_vector_store.similarity_search.side_effect = Exception("Vector search failed")
            
            # Mock fallback search to return results
            from langchain_core.documents import Document
            mock_docs = [Document(page_content="Fallback content", metadata={"title": "Fallback"})]
            mock_vector_store.search_by_metadata.return_value = mock_docs
            
            # This should not raise an exception due to fallback
            try:
                result = await hybrid_rag_service._fallback_search(
                    "test query",
                    {"department": "IT"}
                )
                assert len(result) > 0
            except Exception as e:
                pytest.fail(f"Fallback should handle exceptions: {e}")


class TestMiddlewareIntegration:
    """Test middleware integration."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_middleware(self):
        """Test rate limiting middleware."""
        from app.bot.middleware.rag_middleware import RAGRateLimitMiddleware
        
        middleware = RAGRateLimitMiddleware()
        
        # Test rate limit checking
        allowed = await middleware._check_rate_limits(12345)
        assert allowed, "First request should be allowed"
    
    @pytest.mark.asyncio
    async def test_monitoring_middleware(self):
        """Test monitoring middleware."""
        from app.bot.middleware.rag_middleware import RAGMonitoringMiddleware
        
        middleware = RAGMonitoringMiddleware()
        
        # Test monitoring data structure
        monitoring_data = {
            "start_time": asyncio.get_event_loop().time(),
            "user_id": 12345,
            "message_length": 50,
            "message_type": "text"
        }
        
        # This should not raise an exception
        await middleware._log_interaction(monitoring_data, success=True)


@pytest.mark.asyncio
async def test_full_system_integration():
    """Test full system integration with mocked dependencies."""
    
    with patch('app.ai.langchain.vector_store.vector_store') as mock_vector_store, \
         patch('app.ai.langchain.llm_manager.llm_manager') as mock_llm, \
         patch('app.core.cache.cache_manager') as mock_cache:
        
        # Setup mocks
        mock_vector_store.initialize_collection.return_value = True
        mock_vector_store.get_collection_info.return_value = {"points_count": 100}
        mock_llm.generate_response.return_value = "Test response"
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        
        # Test health check
        health = await hybrid_rag_service.health_check()
        assert health["status"] == "healthy"
        
        # Test cache stats
        mock_cache.info.return_value = {"used_memory": "1MB"}
        mock_cache.keys.return_value = ["key1", "key2"]
        
        stats = await vector_cache_service.get_cache_stats()
        assert "timestamp" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])