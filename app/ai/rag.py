"""
Simplified RAG service for Q&A.
"""

from typing import Dict, Any, List, Optional

from app.core.logging import get_logger
from app.ai import vector_store, llm

logger = get_logger("ai.rag")


async def process_query(
    query: str,
    user_id: int,
    language: str = "ru"
) -> Dict[str, Any]:
    """Process a user query using RAG."""
    try:
        context = ""
        source_docs = []
        
        # Try to search for relevant documents if vector store is available
        if await vector_store.is_available():
            search_results = await vector_store.search(
                query=query,
                k=5,
                score_threshold=0.5
            )
            
            # Build context from search results
            if search_results:
                context_parts = []
                for doc, score in search_results:
                    context_parts.append(doc.page_content)
                    source_docs.append({
                        "content": doc.page_content[:200] + "...",
                        "source": doc.metadata.get("source", "unknown"),
                        "score": score
                    })
                context = "\n\n".join(context_parts)
        
        # Generate response
        response = await llm.generate_response(
            query=query,
            context=context,
            language=language
        )
        
        logger.info(
            f"RAG query processed for user {user_id}, "
            f"found {len(source_docs)} relevant documents"
        )
        
        return {
            "answer": response,
            "source_documents": source_docs,
            "has_context": bool(context)
        }
        
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        
        # Return fallback response
        fallback_messages = {
            "ru": "Извините, произошла ошибка при обработке вашего вопроса. Попробуйте позже.",
            "en": "Sorry, an error occurred while processing your question. Please try again later."
        }
        
        return {
            "answer": fallback_messages.get(language, fallback_messages["ru"]),
            "source_documents": [],
            "has_context": False,
            "error": str(e)
        }


async def health_check() -> Dict[str, Any]:
    """Check RAG system health."""
    try:
        stats = await vector_store.get_collection_stats()
        
        return {
            "status": "healthy" if stats.get('status') != 'unavailable' else "degraded",
            "vector_store": stats
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
