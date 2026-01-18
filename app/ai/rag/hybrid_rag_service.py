"""
Hybrid RAG Service integrating LangChain components with existing architecture.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
import hashlib

from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langchain_core.documents import Document
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.cache import cache_manager, cached
from app.core.exceptions import VectorSearchError, LLMResponseError
from app.ai.langchain.llm_manager import llm_manager, onboarding_llm
from app.ai.langchain.vector_store import vector_store

logger = get_logger("ai.hybrid_rag")


class QueryComplexityAnalyzer:
    """Analyzes query complexity to determine processing strategy."""
    
    SIMPLE_PATTERNS = [
        "что такое", "кто такой", "где находится", "когда", "сколько",
        "what is", "who is", "where is", "when", "how much",
        "ما هو", "من هو", "أين", "متى", "كم"
    ]
    
    COMPLEX_PATTERNS = [
        "объясни", "расскажи", "сравни", "проанализируй", "как работает",
        "explain", "tell me", "compare", "analyze", "how does",
        "اشرح", "أخبرني", "قارن", "حلل", "كيف يعمل"
    ]
    
    @classmethod
    def analyze_complexity(cls, query: str) -> str:
        """Analyze query complexity."""
        query_lower = query.lower()
        
        # Check for simple patterns
        if any(pattern in query_lower for pattern in cls.SIMPLE_PATTERNS):
            return "simple"
        
        # Check for complex patterns
        if any(pattern in query_lower for pattern in cls.COMPLEX_PATTERNS):
            return "complex"
        
        # Default based on length and question marks
        if len(query.split()) <= 5 and query.count('?') <= 1:
            return "simple"
        
        return "complex"


class HybridRAGService:
    """Hybrid RAG service combining custom logic with LangChain components."""
    
    def __init__(self):
        self.settings = get_settings()
        self.complexity_analyzer = QueryComplexityAnalyzer()
        
        # Initialize LangChain components
        self._simple_qa_chain: Optional[RetrievalQA] = None
        self._conversational_chain: Optional[ConversationalRetrievalChain] = None
        self._compression_retriever: Optional[ContextualCompressionRetriever] = None
        
        # Memory for conversations (per user)
        self._user_memories: Dict[int, ConversationBufferWindowMemory] = {}
        
        # Rate limiting
        self._user_request_counts: Dict[int, List[datetime]] = {}
        self.max_requests_per_minute = 10
        
    async def _get_simple_qa_chain(self) -> RetrievalQA:
        """Get or create simple QA chain."""
        if self._simple_qa_chain is None:
            llm = llm_manager.get_chat_model()
            retriever = await self._get_compression_retriever()
            
            prompt_template = PromptTemplate(
                input_variables=["context", "question"],
                template="""Используй следующий контекст для ответа на вопрос. 
                Если информации недостаточно, честно скажи об этом.
                
                Контекст:
                {context}
                
                Вопрос: {question}
                
                Ответ:"""
            )
            
            self._simple_qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt_template}
            )
            
        return self._simple_qa_chain
    
    async def _get_conversational_chain(self, user_id: int) -> ConversationalRetrievalChain:
        """Get or create conversational chain for user."""
        if self._conversational_chain is None:
            llm = llm_manager.get_chat_model()
            retriever = await self._get_compression_retriever()
            
            # Create memory for user if not exists
            if user_id not in self._user_memories:
                self._user_memories[user_id] = ConversationBufferWindowMemory(
                    k=5,  # Keep last 5 exchanges
                    memory_key="chat_history",
                    return_messages=True,
                    output_key="answer"
                )
            
            self._conversational_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=self._user_memories[user_id],
                return_source_documents=True,
                verbose=False
            )
            
        return self._conversational_chain
    
    async def _get_compression_retriever(self) -> ContextualCompressionRetriever:
        """Get or create compression retriever."""
        if self._compression_retriever is None:
            base_retriever = (await vector_store.get_vector_store()).as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={
                    "k": 10,
                    "score_threshold": 0.7
                }
            )
            
            # Add compression to reduce irrelevant content
            compressor = LLMChainExtractor.from_llm(llm_manager.get_chat_model())
            self._compression_retriever = ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=base_retriever
            )
            
        return self._compression_retriever
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limits."""
        now = datetime.utcnow()
        minute_ago = datetime.utcnow().replace(second=0, microsecond=0)
        
        if user_id not in self._user_request_counts:
            self._user_request_counts[user_id] = []
        
        # Clean old requests
        self._user_request_counts[user_id] = [
            req_time for req_time in self._user_request_counts[user_id]
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self._user_request_counts[user_id]) >= self.max_requests_per_minute:
            return False
        
        # Add current request
        self._user_request_counts[user_id].append(now)
        return True
    
    @cached(ttl=300, key_prefix="rag_search")  # Cache for 5 minutes
    async def _cached_vector_search(
        self,
        query: str,
        k: int = 5,
        filter_conditions: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.7
    ) -> List[Tuple[Document, float]]:
        """Cached vector search."""
        return await vector_store.similarity_search(
            query=query,
            k=k,
            filter_conditions=filter_conditions,
            score_threshold=score_threshold
        )
    
    async def _fallback_search(
        self,
        query: str,
        user_info: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Fallback search when vector search fails."""
        try:
            # Try metadata search
            if user_info and user_info.get("department"):
                metadata_filter = {
                    "department": [user_info["department"], "general"]
                }
                results = await vector_store.search_by_metadata(
                    metadata_filter=metadata_filter,
                    limit=5
                )
                if results:
                    return results
            
            # Try broader search with lower threshold
            results = await vector_store.similarity_search(
                query=query,
                k=3,
                score_threshold=0.5
            )
            return [doc for doc, score in results]
            
        except Exception as e:
            logger.error("Fallback search failed", error=str(e))
            return []
    
    async def process_query(
        self,
        query: str,
        user_id: int,
        user_info: Optional[Dict[str, Any]] = None,
        language: str = "ru",
        use_conversation_memory: bool = True
    ) -> Dict[str, Any]:
        """Process query using hybrid RAG approach."""
        
        # Check rate limits
        if not self._check_rate_limit(user_id):
            raise VectorSearchError(
                query=query,
                reason="Rate limit exceeded. Please wait before making another request."
            )
        
        try:
            # Analyze query complexity
            complexity = self.complexity_analyzer.analyze_complexity(query)
            
            logger.info(
                "Processing RAG query",
                user_id=user_id,
                query_length=len(query),
                complexity=complexity,
                language=language
            )
            
            if complexity == "simple" and not use_conversation_memory:
                # Use simple QA chain for straightforward questions
                result = await self._process_simple_query(query, user_info)
            else:
                # Use conversational chain for complex queries or when memory is needed
                result = await self._process_conversational_query(
                    query, user_id, user_info, language
                )
            
            # Add metadata
            result.update({
                "query_complexity": complexity,
                "processing_method": "simple" if complexity == "simple" and not use_conversation_memory else "conversational",
                "user_id": user_id,
                "language": language,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return result
            
        except Exception as e:
            logger.error(
                "RAG query processing failed",
                error=str(e),
                user_id=user_id,
                query=query[:100]
            )
            
            # Try fallback
            fallback_docs = await self._fallback_search(query, user_info)
            if fallback_docs:
                # Generate response using custom LLM with fallback context
                context = "\n".join([doc.page_content for doc in fallback_docs])
                response = await onboarding_llm.generate_onboarding_response(
                    user_message=query,
                    context=context,
                    language=language,
                    user_info=user_info
                )
                
                return {
                    "answer": response,
                    "source_documents": [
                        {
                            "content": doc.page_content,
                            "metadata": doc.metadata
                        }
                        for doc in fallback_docs
                    ],
                    "query_complexity": "fallback",
                    "processing_method": "fallback",
                    "user_id": user_id,
                    "language": language
                }
            
            raise LLMResponseError(
                model="hybrid_rag",
                reason=f"Failed to process query: {str(e)}"
            )
    
    async def _process_simple_query(
        self,
        query: str,
        user_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process simple query using RetrievalQA chain."""
        qa_chain = await self._get_simple_qa_chain()
        
        # Add user context to query if available
        enhanced_query = query
        if user_info:
            context_parts = []
            if user_info.get("department"):
                context_parts.append(f"Отдел: {user_info['department']}")
            if user_info.get("position"):
                context_parts.append(f"Должность: {user_info['position']}")
            
            if context_parts:
                enhanced_query = f"{query}\n\nКонтекст пользователя: {', '.join(context_parts)}"
        
        result = await qa_chain.acall({"query": enhanced_query})
        
        return {
            "answer": result["result"],
            "source_documents": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in result["source_documents"]
            ]
        }
    
    async def _process_conversational_query(
        self,
        query: str,
        user_id: int,
        user_info: Optional[Dict[str, Any]] = None,
        language: str = "ru"
    ) -> Dict[str, Any]:
        """Process conversational query with memory."""
        conv_chain = await self._get_conversational_chain(user_id)
        
        # Update memory with user context if first interaction
        memory = self._user_memories[user_id]
        if not memory.chat_memory.messages and user_info:
            context_message = self._build_user_context_message(user_info, language)
            memory.chat_memory.add_message(SystemMessage(content=context_message))
        
        result = await conv_chain.acall({"question": query})
        
        return {
            "answer": result["answer"],
            "source_documents": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in result["source_documents"]
            ],
            "chat_history": [
                {
                    "type": msg.type if hasattr(msg, 'type') else msg.__class__.__name__,
                    "content": msg.content
                }
                for msg in memory.chat_memory.messages[-10:]  # Last 10 messages
            ]
        }
    
    def _build_user_context_message(
        self,
        user_info: Dict[str, Any],
        language: str
    ) -> str:
        """Build user context message for conversation memory."""
        templates = {
            "ru": "Информация о пользователе: {name}, должность: {position}, отдел: {department}",
            "en": "User information: {name}, position: {position}, department: {department}",
            "ar": "معلومات المستخدم: {name}، المنصب: {position}، القسم: {department}"
        }
        
        template = templates.get(language, templates["ru"])
        return template.format(
            name=user_info.get("name", "Не указано"),
            position=user_info.get("position", "Не указана"),
            department=user_info.get("department", "Не указан")
        )
    
    async def clear_user_memory(self, user_id: int) -> bool:
        """Clear conversation memory for user."""
        try:
            if user_id in self._user_memories:
                self._user_memories[user_id].clear()
                logger.info("User memory cleared", user_id=user_id)
                return True
            return False
        except Exception as e:
            logger.error("Failed to clear user memory", user_id=user_id, error=str(e))
            return False
    
    async def get_user_conversation_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Get conversation history for user."""
        if user_id not in self._user_memories:
            return []
        
        memory = self._user_memories[user_id]
        return [
            {
                "type": msg.type if hasattr(msg, 'type') else msg.__class__.__name__,
                "content": msg.content,
                "timestamp": getattr(msg, 'timestamp', None)
            }
            for msg in memory.chat_memory.messages
        ]
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for RAG service."""
        try:
            # Test vector store connection
            collection_info = await vector_store.get_collection_info()
            
            # Test LLM connection
            test_response = await llm_manager.generate_response([
                HumanMessage(content="Test message")
            ])
            
            return {
                "status": "healthy",
                "vector_store": {
                    "connected": bool(collection_info),
                    "points_count": collection_info.get("points_count", 0)
                },
                "llm": {
                    "connected": bool(test_response),
                    "model": self.settings.openai.model
                },
                "active_conversations": len(self._user_memories),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global hybrid RAG service instance
hybrid_rag_service = HybridRAGService()