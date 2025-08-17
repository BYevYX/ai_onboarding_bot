"""
LLM Manager for handling OpenAI models through LangChain.
"""

from typing import Any, Dict, List, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.exceptions import LLMResponseError, EmbeddingGenerationError

logger = get_logger("ai.llm")


class LLMManager:
    """Manager for LLM operations using LangChain."""
    
    def __init__(self):
        self.settings = get_settings()
        self._chat_model: Optional[ChatOpenAI] = None
        self._embeddings: Optional[OpenAIEmbeddings] = None
    
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
    
    async def generate_response(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> str:
        """Generate response from chat model."""
        try:
            chat_model = self.get_chat_model(**kwargs)
            response = await chat_model.ainvoke(messages)
            
            logger.info(
                "LLM response generated",
                model=self.settings.openai.model,
                message_count=len(messages),
                response_length=len(response.content)
            )
            
            return response.content
            
        except Exception as e:
            logger.error(
                "LLM response generation failed",
                error=str(e),
                model=self.settings.openai.model
            )
            raise LLMResponseError(
                model=self.settings.openai.model,
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