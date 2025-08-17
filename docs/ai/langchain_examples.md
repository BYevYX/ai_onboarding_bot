# Примеры использования LangChain и LangGraph

## Обзор

Этот документ содержит практические примеры использования LangChain и LangGraph в Telegram-боте для онбординга сотрудников.

## 1. Базовая настройка LangChain

### Конфигурация LLM и Embeddings
```python
# app/ai/langchain/config.py
import os
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.callbacks import get_openai_callback

class LangChainConfig:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Настройка LLM
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.7,
            openai_api_key=self.openai_api_key,
            max_tokens=1000
        )
        
        # Настройка Embeddings
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002",
            openai_api_key=self.openai_api_key
        )
    
    def get_llm(self):
        return self.llm
    
    def get_embeddings(self):
        return self.embeddings
    
    def track_usage(self, callback_func):
        """Отслеживание использования токенов"""
        with get_openai_callback() as cb:
            result = callback_func()
            return result, {
                "total_tokens": cb.total_tokens,
                "prompt_tokens": cb.prompt_tokens,
                "completion_tokens": cb.completion_tokens,
                "total_cost": cb.total_cost
            }
```

## 2. LangGraph Workflow для RAG

### Полный RAG Workflow
```python
# app/ai/langgraph/rag_workflow.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
from langchain.schema import Document
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import StrOutputParser

class RAGState(TypedDict):
    """Состояние RAG workflow"""
    original_query: str
    user_id: int
    language: str
    enhanced_query: str
    retrieved_documents: List[Document]
    context: str
    final_response: str
    metadata: Dict[str, Any]

class RAGWorkflow:
    def __init__(self, llm, embeddings, vector_store):
        self.llm = llm
        self.embeddings = embeddings
        self.vector_store = vector_store
        
        # Создание workflow
        workflow = StateGraph(RAGState)
        
        # Добавление узлов
        workflow.add_node("detect_language", self.detect_language)
        workflow.add_node("enhance_query", self.enhance_query)
        workflow.add_node("retrieve_documents", self.retrieve_documents)
        workflow.add_node("generate_response", self.generate_response)
        
        # Определение маршрутов
        workflow.set_entry_point("detect_language")
        workflow.add_edge("detect_language", "enhance_query")
        workflow.add_edge("enhance_query", "retrieve_documents")
        workflow.add_edge("retrieve_documents", "generate_response")
        workflow.add_edge("generate_response", END)
        
        # Компиляция
        self.app = workflow.compile()
    
    async def detect_language(self, state: RAGState) -> RAGState:
        """Определение языка запроса"""
        from langdetect import detect
        
        try:
            detected_lang = detect(state["original_query"])
            state["language"] = detected_lang
        except:
            state["language"] = "ru"
        
        state["metadata"]["detected_language"] = state["language"]
        return state
    
    async def enhance_query(self, state: RAGState) -> RAGState:
        """Улучшение поискового запроса"""
        enhancement_prompt = ChatPromptTemplate.from_template("""
        Улучши следующий поисковый запрос для лучшего поиска в корпоративной базе знаний.
        Добавь синонимы и связанные термины, сохраняя исходный смысл.
        
        Исходный запрос: {query}
        Язык: {language}
        
        Улучшенный запрос:
        """)
        
        chain = enhancement_prompt | self.llm | StrOutputParser()
        
        enhanced = await chain.ainvoke({
            "query": state["original_query"],
            "language": state["language"]
        })
        
        state["enhanced_query"] = enhanced.strip()
        return state
    
    async def retrieve_documents(self, state: RAGState) -> RAGState:
        """Поиск релевантных документов"""
        retriever = self.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": 10,
                "score_threshold": 0.7
            }
        )
        
        docs = await retriever.aget_relevant_documents(state["enhanced_query"])
        state["retrieved_documents"] = docs
        state["metadata"]["retrieved_count"] = len(docs)
        
        # Построение контекста
        context_parts = []
        for i, doc in enumerate(docs):
            context_parts.append(f"Документ {i+1}: {doc.page_content}")
        
        state["context"] = "\n\n".join(context_parts)
        return state
    
    async def generate_response(self, state: RAGState) -> RAGState:
        """Генерация финального ответа"""
        response_prompt = ChatPromptTemplate.from_template("""
        Ты - корпоративный помощник для онбординга сотрудников.
        Используй предоставленный контекст для ответа на вопрос пользователя.
        
        Контекст:
        {context}
        
        Вопрос: {query}
        Язык ответа: {language}
        
        Требования:
        - Отвечай на языке пользователя
        - Будь конкретным и полезным
        - Если информации недостаточно, скажи об этом
        - Ссылайся на источники
        
        Ответ:
        """)
        
        chain = response_prompt | self.llm | StrOutputParser()
        
        response = await chain.ainvoke({
            "context": state["context"],
            "query": state["original_query"],
            "language": state["language"]
        })
        
        state["final_response"] = response.strip()
        return state
    
    async def process_query(self, query: str, user_id: int) -> Dict[str, Any]:
        """Основной метод обработки запроса"""
        initial_state = RAGState(
            original_query=query,
            user_id=user_id,
            language="",
            enhanced_query="",
            retrieved_documents=[],
            context="",
            final_response="",
            metadata={}
        )
        
        final_state = await self.app.ainvoke(initial_state)
        
        return {
            "response": final_state["final_response"],
            "language": final_state["language"],
            "retrieved_count": final_state["metadata"]["retrieved_count"],
            "enhanced_query": final_state["enhanced_query"]
        }
```

## 3. LangChain Agents для корпоративных функций

### Корпоративный агент с инструментами
```python
# app/ai/langchain/agents.py
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import BaseTool
from langchain.prompts import ChatPromptTemplate
from typing import Type, Optional
from pydantic import BaseModel, Field

class UserSearchInput(BaseModel):
    name: str = Field(description="Имя или фамилия сотрудника для поиска")
    department: Optional[str] = Field(description="Департамент для фильтрации")

class UserSearchTool(BaseTool):
    name = "search_employee"
    description = "Поиск информации о сотрудниках компании по имени или департаменту"
    args_schema: Type[BaseModel] = UserSearchInput
    
    def __init__(self, user_service):
        super().__init__()
        self.user_service = user_service
    
    async def _arun(self, name: str, department: Optional[str] = None) -> str:
        users = await self.user_service.search_users(
            query=name,
            department=department
        )
        
        if not users:
            return f"Сотрудники с именем '{name}' не найдены"
        
        result = f"Найдено сотрудников: {len(users)}\n"
        for user in users[:5]:
            result += f"• {user.first_name} {user.last_name} - {user.department} ({user.position})\n"
        
        return result

class PolicySearchInput(BaseModel):
    topic: str = Field(description="Тема или ключевые слова для поиска в политиках компании")

class PolicySearchTool(BaseTool):
    name = "search_policy"
    description = "Поиск корпоративных политик и процедур по теме"
    args_schema: Type[BaseModel] = PolicySearchInput
    
    def __init__(self, document_service):
        super().__init__()
        self.document_service = document_service
    
    async def _arun(self, topic: str) -> str:
        documents = await self.document_service.search_documents(
            query=topic,
            category="policy"
        )
        
        if not documents:
            return f"Политики по теме '{topic}' не найдены"
        
        result = f"Найдено политик: {len(documents)}\n"
        for doc in documents[:3]:
            result += f"• {doc.title}\n"
        
        return result

class CorporateAgent:
    def __init__(self, llm, user_service, document_service):
        self.llm = llm
        
        # Создание инструментов
        self.tools = [
            UserSearchTool(user_service),
            PolicySearchTool(document_service)
        ]
        
        # Системный промпт
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
            Ты - корпоративный помощник для новых сотрудников.
            У тебя есть доступ к следующим инструментам:
            - search_employee: поиск информации о коллегах
            - search_policy: поиск корпоративных политик
            
            Используй эти инструменты когда пользователь:
            - Спрашивает о коллегах или контактах
            - Интересуется политиками компании
            - Нужна информация о процедурах
            
            Всегда будь вежливым и профессиональным.
            """),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Создание агента
        self.agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Создание executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=3
        )
    
    async def process_query(self, query: str) -> str:
        result = await self.agent_executor.ainvoke({"input": query})
        return result["output"]
```

## 4. Conversational RAG с памятью

### Диалоговый RAG с историей
```python
# app/ai/langchain/conversational_rag.py
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage

class ConversationalRAG:
    def __init__(self, llm, vector_store, memory_size: int = 10):
        self.llm = llm
        self.vector_store = vector_store
        
        # Память для диалога
        self.memory = ConversationBufferWindowMemory(
            k=memory_size,
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        # Создание conversational chain
        self.chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vector_store.as_retriever(),
            memory=self.memory,
            return_source_documents=True,
            verbose=True,
            combine_docs_chain_kwargs={
                "prompt": self._get_qa_prompt()
            }
        )
    
    def _get_qa_prompt(self):
        from langchain.prompts import PromptTemplate
        
        return PromptTemplate(
            template="""
            Используй следующий контекст для ответа на вопрос.
            Если ты не знаешь ответа, скажи что не знаешь.
            
            Контекст: {context}
            
            Вопрос: {question}
            
            Полезный ответ:
            """,
            input_variables=["context", "question"]
        )
    
    async def chat(self, message: str, user_id: int) -> Dict[str, Any]:
        """Диалоговый интерфейс"""
        result = await self.chain.acall({
            "question": message,
            "chat_history": self.memory.chat_memory.messages
        })
        
        return {
            "answer": result["answer"],
            "source_documents": [
                {
                    "content": doc.page_content[:200] + "...",
                    "source": doc.metadata.get("title", "Unknown")
                }
                for doc in result["source_documents"]
            ],
            "chat_history_length": len(self.memory.chat_memory.messages)
        }
    
    def get_chat_history(self) -> List[Dict[str, str]]:
        """Получение истории диалога"""
        history = []
        for message in self.memory.chat_memory.messages:
            history.append({
                "type": "human" if isinstance(message, HumanMessage) else "ai",
                "content": message.content
            })
        return history
    
    def clear_history(self):
        """Очистка истории диалога"""
        self.memory.clear()
```

## 5. Интеграция с Telegram Bot

### Bot handlers с LangChain
```python
# app/bot/handlers/langchain_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

class ConversationStates(StatesGroup):
    chatting = State()
    agent_mode = State()

class LangChainBotHandlers:
    def __init__(
        self,
        rag_workflow,
        conversational_rag,
        corporate_agent
    ):
        self.rag_workflow = rag_workflow
        self.conversational_rag = conversational_rag
        self.corporate_agent = corporate_agent
        self.router = Router()
        
        # Регистрация handlers
        self._register_handlers()
    
    def _register_handlers(self):
        self.router.message(Command("rag"))(self.rag_search)
        self.router.message(Command("chat"))(self.start_conversation)
        self.router.message(Command("agent"))(self.agent_mode)
        self.router.message(ConversationStates.chatting)(self.continue_conversation)
        self.router.message(ConversationStates.agent_mode)(self.agent_query)
    
    async def rag_search(self, message: Message, user: User):
        """Одиночный RAG поиск"""
        query = message.text.replace("/rag", "").strip()
        
        if not query:
            await message.answer(
                "Пожалуйста, укажите запрос после команды /rag\n"
                "Например: /rag как подключиться к VPN"
            )
            return
        
        # Показываем индикатор печати
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        try:
            result = await self.rag_workflow.process_query(query, user.id)
            
            response_text = result["response"]
            
            # Добавляем метаинформацию
            if result["retrieved_count"] > 0:
                response_text += f"\n\n📚 Найдено документов: {result['retrieved_count']}"
                response_text += f"\n🔍 Улучшенный запрос: {result['enhanced_query']}"
            
            await message.answer(response_text)
            
        except Exception as e:
            await message.answer(
                "Извините, произошла ошибка при обработке запроса. "
                "Попробуйте переформулировать вопрос."
            )
    
    async def start_conversation(self, message: Message, state: FSMContext, user: User):
        """Начало диалогового режима"""
        await state.set_state(ConversationStates.chatting)
        
        query = message.text.replace("/chat", "").strip()
        
        if query:
            # Если есть запрос, сразу обрабатываем
            await self.continue_conversation(message, state, user)
        else:
            await message.answer(
                "🗣 Диалоговый режим активирован!\n"
                "Теперь я буду помнить контекст нашего разговора.\n"
                "Задайте ваш вопрос или используйте /stop для выхода."
            )
    
    async def continue_conversation(self, message: Message, state: FSMContext, user: User):
        """Продолжение диалога"""
        if message.text == "/stop":
            await state.clear()
            self.conversational_rag.clear_history()
            await message.answer("Диалоговый режим завершен.")
            return
        
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        try:
            result = await self.conversational_rag.chat(message.text, user.id)
            
            response_text = result["answer"]
            
            # Добавляем информацию об источниках
            if result["source_documents"]:
                response_text += "\n\n📖 Источники:"
                for doc in result["source_documents"][:2]:
                    response_text += f"\n• {doc['source']}"
            
            await message.answer(response_text)
            
        except Exception as e:
            await message.answer(
                "Произошла ошибка в диалоге. Попробуйте еще раз или используйте /stop для выхода."
            )
    
    async def agent_mode(self, message: Message, state: FSMContext, user: User):
        """Режим агента с инструментами"""
        await state.set_state(ConversationStates.agent_mode)
        
        query = message.text.replace("/agent", "").strip()
        
        if query:
            await self.agent_query(message, state, user)
        else:
            await message.answer(
                "🤖 Режим агента активирован!\n"
                "Я могу помочь найти коллег и корпоративные политики.\n"
                "Задайте вопрос или используйте /stop для выхода."
            )
    
    async def agent_query(self, message: Message, state: FSMContext, user: User):
        """Обработка запроса через агента"""
        if message.text == "/stop":
            await state.clear()
            await message.answer("Режим агента завершен.")
            return
        
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        try:
            response = await self.corporate_agent.process_query(message.text)
            await message.answer(response)
            
        except Exception as e:
            await message.answer(
                "Произошла ошибка при обработке запроса агентом. "
                "Попробуйте переформулировать вопрос."
            )
```

## 6. Мониторинг и отладка LangChain

### Callbacks для мониторинга
```python
# app/ai/langchain/monitoring.py
from langchain.callbacks.base import BaseCallbackHandler
from typing import Dict, Any, List
import time
import logging

class TelegramBotCallbackHandler(BaseCallbackHandler):
    """Callback для мониторинга LangChain операций"""
    
    def __init__(self):
        self.start_time = None
        self.tokens_used = 0
        self.cost = 0.0
        self.logger = logging.getLogger(__name__)
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Начало LLM запроса"""
        self.start_time = time.time()
        self.logger.info(f"LLM запрос начат. Промптов: {len(prompts)}")
    
    def on_llm_end(self, response, **kwargs) -> None:
        """Завершение LLM запроса"""
        duration = time.time() - self.start_time if self.start_time else 0
        
        # Извлечение информации о токенах
        if hasattr(response, 'llm_output') and response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
            self.tokens_used = token_usage.get('total_tokens', 0)
        
        self.logger.info(
            f"LLM запрос завершен. Время: {duration:.2f}с, Токены: {self.tokens_used}"
        )
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Ошибка LLM"""
        self.logger.error(f"Ошибка LLM: {error}")
    
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs) -> None:
        """Начало цепочки"""
        chain_name = serialized.get('name', 'Unknown')
        self.logger.info(f"Цепочка '{chain_name}' начата")
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        """Завершение цепочки"""
        self.logger.info("Цепочка завершена успешно")
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Начало использования инструмента"""
        tool_name = serialized.get('name', 'Unknown')
        self.logger.info(f"Инструмент '{tool_name}' запущен с входом: {input_str[:100]}...")
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        """Завершение использования инструмента"""
        self.logger.info(f"Инструмент завершен. Выход: {output[:100]}...")

# Использование callback
def create_monitored_llm():
    from langchain.chat_models import ChatOpenAI
    
    callback_handler = TelegramBotCallbackHandler()
    
    llm = ChatOpenAI(
        model="gpt-4",
        callbacks=[callback_handler],
        verbose=True
    )
    
    return llm, callback_handler
```

Эти примеры показывают, как интегрировать LangChain и LangGraph в Telegram-бот для создания мощной системы онбординга с поддержкой сложных AI workflows, агентов с инструментами и диалоговых интерфейсов.