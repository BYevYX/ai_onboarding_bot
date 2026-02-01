"""
Simplified LLM and embeddings manager.
"""

from typing import List, Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("ai.llm")

_chat_model: Optional[ChatOpenAI] = None
_embeddings: Optional[OpenAIEmbeddings] = None


def get_chat_model() -> ChatOpenAI:
    """Get ChatOpenAI model instance."""
    global _chat_model
    if _chat_model is None:
        settings = get_settings()
        # Note: 'api_key' is the current parameter name in langchain-openai 0.3+
        _chat_model = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.7
        )
    return _chat_model


def get_embeddings() -> OpenAIEmbeddings:
    """Get OpenAI embeddings instance."""
    global _embeddings
    if _embeddings is None:
        settings = get_settings()
        # Note: 'api_key' is the current parameter name in langchain-openai 0.3+
        _embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )
    return _embeddings


async def generate_response(
    query: str,
    context: str,
    language: str = "ru"
) -> str:
    """Generate response using RAG context."""
    
    system_prompts = {
        "ru": """Ты - корпоративный AI-помощник. Отвечай на вопросы сотрудников, используя предоставленный контекст из документов компании.

Правила:
- Отвечай точно и по существу
- Если информации в контексте недостаточно, честно скажи об этом
- Будь дружелюбным и профессиональным""",
        
        "en": """You are a corporate AI assistant. Answer employee questions using the provided context from company documents.

Rules:
- Answer accurately and to the point
- If the context doesn't have enough information, say so honestly
- Be friendly and professional"""
    }
    
    system_prompt = system_prompts.get(language, system_prompts["ru"])
    
    if context:
        system_prompt += f"\n\nКонтекст из документов:\n{context}"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=query)
    ]
    
    chat_model = get_chat_model()
    response = await chat_model.ainvoke(messages)
    
    return response.content
