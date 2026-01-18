"""
LLM Manager for handling OpenAI models through LangChain with RAG support.
"""

from typing import Any, Dict, List, Optional, Union
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.callbacks import AsyncCallbackHandler
from langchain.schema import LLMResult

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.cache import cached
from app.core.exceptions import LLMResponseError, EmbeddingGenerationError

logger = get_logger("ai.llm")


class RAGCallbackHandler(AsyncCallbackHandler):
    """Custom callback handler for RAG operations monitoring."""
    
    def __init__(self, user_id: Optional[int] = None):
        self.user_id = user_id
        self.start_time = None
        self.tokens_used = 0
    
    async def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Called when LLM starts running."""
        import time
        self.start_time = time.time()
        logger.debug(
            "LLM chain started",
            user_id=self.user_id,
            prompt_count=len(prompts),
            model=serialized.get("name", "unknown")
        )
    
    async def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Called when LLM ends running."""
        import time
        if self.start_time:
            duration = time.time() - self.start_time
            
            # Extract token usage if available
            if response.llm_output and "token_usage" in response.llm_output:
                self.tokens_used = response.llm_output["token_usage"].get("total_tokens", 0)
            
            logger.info(
                "LLM chain completed",
                user_id=self.user_id,
                duration=duration,
                tokens_used=self.tokens_used,
                generations_count=len(response.generations)
            )
    
    async def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs) -> None:
        """Called when LLM errors."""
        logger.error(
            "LLM chain error",
            user_id=self.user_id,
            error=str(error),
            error_type=type(error).__name__
        )


class LLMManager:
    """Manager for LLM operations using LangChain with RAG support."""
    
    def __init__(self):
        self.settings = get_settings()
        self._chat_model: Optional[ChatOpenAI] = None
        self._embeddings: Optional[OpenAIEmbeddings] = None
        self._rag_chains: Dict[str, LLMChain] = {}
    
    def get_chat_model(self, **kwargs) -> ChatOpenAI:
        """Get ChatOpenAI model instance."""
        if self._chat_model is None:
            self._chat_model = ChatOpenAI(
                model=self.settings.openai.model,
                openai_api_key=self.settings.openai.api_key,
                temperature=self.settings.openai.temperature,
                max_tokens=self.settings.openai.max_tokens,
                **kwargs
            )
        return self._chat_model
    
    def get_embeddings(self) -> OpenAIEmbeddings:
        """Get OpenAI embeddings instance."""
        if self._embeddings is None:
            self._embeddings = OpenAIEmbeddings(
                model=self.settings.openai.embedding_model,
                openai_api_key=self.settings.openai.api_key,
            )
        return self._embeddings
    
    def get_rag_chain(
        self,
        chain_type: str = "default",
        user_id: Optional[int] = None
    ) -> LLMChain:
        """Get or create RAG chain for specific use case."""
        if chain_type not in self._rag_chains:
            self._rag_chains[chain_type] = self._create_rag_chain(chain_type, user_id)
        return self._rag_chains[chain_type]
    
    def _create_rag_chain(self, chain_type: str, user_id: Optional[int] = None) -> LLMChain:
        """Create RAG chain based on type."""
        llm = self.get_chat_model()
        callback_handler = RAGCallbackHandler(user_id=user_id)
        
        if chain_type == "simple_qa":
            prompt = PromptTemplate(
                input_variables=["context", "question"],
                template="""Используй следующий контекст для ответа на вопрос.
                Если информации недостаточно, честно скажи об этом.
                
                Контекст:
                {context}
                
                Вопрос: {question}
                
                Ответ:"""
            )
        elif chain_type == "conversational":
            prompt = PromptTemplate(
                input_variables=["context", "chat_history", "question"],
                template="""Ты - корпоративный помощник. Используй контекст и историю диалога для ответа.
                
                Контекст:
                {context}
                
                История диалога:
                {chat_history}
                
                Текущий вопрос: {question}
                
                Ответ:"""
            )
        elif chain_type == "multilingual":
            prompt = PromptTemplate(
                input_variables=["context", "question", "language"],
                template="""Answer the question using the provided context in the specified language.
                
                Context:
                {context}
                
                Question: {question}
                Language: {language}
                
                Answer:"""
            )
        else:  # default
            prompt = PromptTemplate(
                input_variables=["context", "question"],
                template="""Ты - корпоративный помощник для адаптации сотрудников.
                Используй предоставленный контекст для ответа на вопрос.
                
                Контекст:
                {context}
                
                Вопрос: {question}
                
                Ответ:"""
            )
        
        return LLMChain(
            llm=llm,
            prompt=prompt,
            callbacks=[callback_handler],
            verbose=False
        )
    
    async def generate_response(
        self,
        messages: List[BaseMessage],
        user_id: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate response from chat model."""
        try:
            chat_model = self.get_chat_model(**kwargs)
            
            # Add callback handler if user_id provided
            if user_id:
                callback_handler = RAGCallbackHandler(user_id=user_id)
                kwargs.setdefault('callbacks', []).append(callback_handler)
            
            response = await chat_model.ainvoke(messages, **kwargs)
            
            logger.info(
                "LLM response generated",
                model=self.settings.openai.model,
                message_count=len(messages),
                response_length=len(response.content),
                user_id=user_id
            )
            
            return response.content
            
        except Exception as e:
            logger.error(
                "LLM response generation failed",
                error=str(e),
                model=self.settings.openai.model,
                user_id=user_id
            )
            raise LLMResponseError(
                model=self.settings.openai.model,
                reason=str(e)
            )
    
    @cached(ttl=1800, key_prefix="llm_rag_response")  # Cache for 30 minutes
    async def generate_rag_response(
        self,
        context: str,
        question: str,
        chain_type: str = "default",
        user_id: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate RAG response with caching."""
        try:
            chain = self.get_rag_chain(chain_type, user_id)
            
            chain_input = {
                "context": context,
                "question": question,
                **kwargs
            }
            
            response = await chain.arun(**chain_input)
            
            logger.info(
                "RAG response generated",
                chain_type=chain_type,
                context_length=len(context),
                question_length=len(question),
                response_length=len(response),
                user_id=user_id
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "RAG response generation failed",
                error=str(e),
                chain_type=chain_type,
                user_id=user_id
            )
            raise LLMResponseError(
                model=f"rag_chain_{chain_type}",
                reason=str(e)
            )
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        try:
            embeddings = self.get_embeddings()
            vectors = await embeddings.aembed_documents(texts)
            
            logger.info(
                "Embeddings generated",
                text_count=len(texts),
                vector_dimension=len(vectors[0]) if vectors else 0
            )
            
            return vectors
            
        except Exception as e:
            logger.error(
                "Embedding generation failed",
                error=str(e),
                text_count=len(texts)
            )
            raise EmbeddingGenerationError(
                text_length=sum(len(text) for text in texts),
                reason=str(e)
            )
    
    async def generate_single_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        try:
            embeddings = self.get_embeddings()
            vector = await embeddings.aembed_query(text)
            
            logger.debug(
                "Single embedding generated",
                text_length=len(text),
                vector_dimension=len(vector)
            )
            
            return vector
            
        except Exception as e:
            logger.error(
                "Single embedding generation failed",
                error=str(e),
                text_length=len(text)
            )
            raise EmbeddingGenerationError(
                text_length=len(text),
                reason=str(e)
            )


class OnboardingLLM:
    """Specialized LLM for onboarding conversations."""
    
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager
        self.system_prompts = {
            "ru": """Ты - AI-ассистент для адаптации новых сотрудников. 
            Твоя задача - помочь новым сотрудникам освоиться в компании, 
            ответить на их вопросы и предоставить необходимую информацию.
            
            Принципы работы:
            - Будь дружелюбным и профессиональным
            - Предоставляй точную и актуальную информацию
            - Если не знаешь ответа, честно об этом скажи
            - Помогай сотрудникам чувствовать себя комфортно
            - Используй корпоративную документацию для ответов""",
            
            "en": """You are an AI assistant for employee onboarding.
            Your task is to help new employees get familiar with the company,
            answer their questions and provide necessary information.
            
            Working principles:
            - Be friendly and professional
            - Provide accurate and up-to-date information
            - If you don't know the answer, be honest about it
            - Help employees feel comfortable
            - Use corporate documentation for answers""",
            
            "ar": """أنت مساعد ذكي لتأهيل الموظفين الجدد.
            مهمتك هي مساعدة الموظفين الجدد على التعرف على الشركة،
            والإجابة على أسئلتهم وتقديم المعلومات اللازمة.
            
            مبادئ العمل:
            - كن ودودًا ومهنيًا
            - قدم معلومات دقيقة ومحدثة
            - إذا كنت لا تعرف الإجابة، كن صادقًا حول ذلك
            - ساعد الموظفين على الشعور بالراحة
            - استخدم وثائق الشركة للإجابات"""
        }
    
    async def generate_onboarding_response(
        self,
        user_message: str,
        context: Optional[str] = None,
        language: str = "ru",
        user_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate onboarding-specific response."""
        
        # Build system message
        system_prompt = self.system_prompts.get(language, self.system_prompts["ru"])
        
        if user_info:
            system_prompt += f"\n\nИнформация о пользователе:\n"
            system_prompt += f"- Имя: {user_info.get('name', 'Не указано')}\n"
            system_prompt += f"- Должность: {user_info.get('position', 'Не указана')}\n"
            system_prompt += f"- Отдел: {user_info.get('department', 'Не указан')}\n"
        
        if context:
            system_prompt += f"\n\nКонтекст из документации:\n{context}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        return await self.llm_manager.generate_response(messages)
    
    async def generate_welcome_message(
        self,
        user_name: str,
        position: str,
        department: str,
        language: str = "ru"
    ) -> str:
        """Generate personalized welcome message."""
        
        welcome_prompts = {
            "ru": f"""Создай персональное приветственное сообщение для нового сотрудника:
            - Имя: {user_name}
            - Должность: {position}
            - Отдел: {department}
            
            Сообщение должно быть теплым, профессиональным и мотивирующим.""",
            
            "en": f"""Create a personalized welcome message for a new employee:
            - Name: {user_name}
            - Position: {position}
            - Department: {department}
            
            The message should be warm, professional and motivating.""",
            
            "ar": f"""أنشئ رسالة ترحيب شخصية لموظف جديد:
            - الاسم: {user_name}
            - المنصب: {position}
            - القسم: {department}
            
            يجب أن تكون الرسالة دافئة ومهنية ومحفزة."""
        }
        
        prompt = welcome_prompts.get(language, welcome_prompts["ru"])
        messages = [HumanMessage(content=prompt)]
        
        return await self.llm_manager.generate_response(messages)


# Global LLM manager instance
llm_manager = LLMManager()
onboarding_llm = OnboardingLLM(llm_manager)