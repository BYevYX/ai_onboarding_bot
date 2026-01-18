"""
Telegram bot message handlers for employee onboarding with hybrid RAG integration.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from langchain_core.messages import HumanMessage

from app.core.logging import get_logger
from app.ai.langchain.workflows import onboarding_workflow, OnboardingState
from app.ai.rag.hybrid_rag_service import hybrid_rag_service
from app.ai.rag.vector_cache_service import vector_cache_service

logger = get_logger("bot.handlers")

# Create router for handlers
router = Router()


class OnboardingStates(StatesGroup):
    """FSM states for onboarding process."""
    WAITING_FOR_START = State()
    PROFILE_SETUP = State()
    DOCUMENT_REVIEW = State()
    QUESTIONS_ANSWERS = State()
    COMPLETED = State()


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext) -> None:
    """Handle /start command."""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        
        logger.info(
            "User started onboarding",
            user_id=user_id,
            username=username
        )
        
        # Create welcome keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_en")],
            [InlineKeyboardButton(text="🇸🇦 العربية", callback_data="lang_ar")]
        ])
        
        welcome_text = """
👋 Добро пожаловать в систему адаптации сотрудников!

🇺🇸 Welcome to the employee onboarding system!

🇸🇦 مرحباً بك في نظام تأهيل الموظفين!

Пожалуйста, выберите язык / Please select language / يرجى اختيار اللغة:
        """
        
        await message.answer(welcome_text, reply_markup=keyboard)
        await state.set_state(OnboardingStates.WAITING_FOR_START)
        
    except Exception as e:
        logger.error("Start handler error", error=str(e), user_id=message.from_user.id)
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data.startswith("lang_"))
async def language_selection_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle language selection."""
    try:
        language = callback.data.split("_")[1]
        user_id = callback.from_user.id
        
        # Store language in state
        await state.update_data(language=language)
        
        logger.info("Language selected", user_id=user_id, language=language)
        
        # Language-specific messages
        messages = {
            "ru": "🎉 Отлично! Начинаем процесс адаптации на русском языке.\n\nДля начала мне нужна информация о вас. Как вас зовут?",
            "en": "🎉 Great! Starting the onboarding process in English.\n\nFirst, I need some information about you. What's your name?",
            "ar": "🎉 ممتاز! بدء عملية التأهيل باللغة العربية.\n\nأولاً، أحتاج بعض المعلومات عنك. ما اسمك؟"
        }
        
        await callback.message.edit_text(messages.get(language, messages["ru"]))
        await state.set_state(OnboardingStates.PROFILE_SETUP)
        await callback.answer()
        
    except Exception as e:
        logger.error("Language selection error", error=str(e), user_id=callback.from_user.id)
        await callback.answer("Ошибка при выборе языка")


@router.message(StateFilter(OnboardingStates.PROFILE_SETUP))
async def profile_setup_handler(message: Message, state: FSMContext) -> None:
    """Handle profile setup messages."""
    try:
        user_data = await state.get_data()
        language = user_data.get("language", "ru")
        user_info = user_data.get("user_info", {})
        
        # Parse user input based on current profile completion
        text = message.text.strip()
        
        if not user_info.get("name"):
            user_info["name"] = text
            
            prompts = {
                "ru": f"Приятно познакомиться, {text}! Какая у вас должность?",
                "en": f"Nice to meet you, {text}! What's your position?",
                "ar": f"سعيد بلقائك، {text}! ما هو منصبك؟"
            }
            
        elif not user_info.get("position"):
            user_info["position"] = text
            
            prompts = {
                "ru": f"Отлично! В каком отделе вы работаете?",
                "en": f"Great! Which department do you work in?",
                "ar": f"ممتاز! في أي قسم تعمل؟"
            }
            
        elif not user_info.get("department"):
            user_info["department"] = text
            
            prompts = {
                "ru": f"Спасибо! Когда ваш первый рабочий день? (например: 2024-01-15)",
                "en": f"Thank you! When is your first working day? (e.g., 2024-01-15)",
                "ar": f"شكراً! متى يوم عملك الأول؟ (مثال: 2024-01-15)"
            }
            
        elif not user_info.get("start_date"):
            user_info["start_date"] = text
            
            # Profile complete, start workflow
            await state.update_data(user_info=user_info)
            
            # Initialize onboarding workflow
            initial_state: OnboardingState = {
                "user_id": message.from_user.id,
                "telegram_id": message.from_user.id,
                "stage": "welcome",
                "user_info": user_info,
                "messages": [],
                "documents_reviewed": [],
                "questions_asked": [],
                "completion_score": 0.0,
                "language": language,
                "context": None,
                "next_action": None
            }
            
            # Run workflow welcome node
            result = await onboarding_workflow.run_workflow(initial_state)
            
            # Send welcome message from workflow
            if result["messages"]:
                last_message = result["messages"][-1]
                await message.answer(last_message.content)
            
            await state.set_state(OnboardingStates.DOCUMENT_REVIEW)
            await state.update_data(workflow_state=result)
            return
        
        # Update state and send next prompt
        await state.update_data(user_info=user_info)
        await message.answer(prompts.get(language, prompts["ru"]))
        
    except Exception as e:
        logger.error("Profile setup error", error=str(e), user_id=message.from_user.id)
        await message.answer("Произошла ошибка при настройке профиля.")


@router.message(StateFilter(OnboardingStates.DOCUMENT_REVIEW))
async def document_review_handler(message: Message, state: FSMContext) -> None:
    """Handle document review phase."""
    try:
        user_data = await state.get_data()
        language = user_data.get("language", "ru")
        workflow_state = user_data.get("workflow_state", {})
        
        # Add user message to workflow state
        workflow_state["messages"].append(HumanMessage(content=message.text))
        
        # Continue workflow from document review
        workflow_state["stage"] = "document_review"
        result = await onboarding_workflow._document_review_node(workflow_state)
        
        # Send response
        if result["messages"]:
            last_message = result["messages"][-1]
            await message.answer(last_message.content)
        
        # Update state
        await state.update_data(workflow_state=result)
        
        # Check if ready to move to Q&A
        if result.get("next_action") == "questions_answers":
            await state.set_state(OnboardingStates.QUESTIONS_ANSWERS)
            
            # Create Q&A keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❓ Задать вопрос", callback_data="ask_question")],
                [InlineKeyboardButton(text="📋 Завершить адаптацию", callback_data="complete_onboarding")]
            ])
            
            qa_prompts = {
                "ru": "Теперь вы можете задать любые вопросы о компании, своей роли или процедурах:",
                "en": "Now you can ask any questions about the company, your role, or procedures:",
                "ar": "الآن يمكنك طرح أي أسئلة حول الشركة أو دورك أو الإجراءات:"
            }
            
            await message.answer(
                qa_prompts.get(language, qa_prompts["ru"]),
                reply_markup=keyboard
            )
        
    except Exception as e:
        logger.error("Document review error", error=str(e), user_id=message.from_user.id)
        await message.answer("Произошла ошибка при обработке документов.")


@router.message(StateFilter(OnboardingStates.QUESTIONS_ANSWERS))
async def questions_answers_handler(message: Message, state: FSMContext) -> None:
    """Handle Q&A phase."""
    try:
        user_data = await state.get_data()
        language = user_data.get("language", "ru")
        workflow_state = user_data.get("workflow_state", {})
        
        # Add user message to workflow state
        workflow_state["messages"].append(HumanMessage(content=message.text))
        
        # Process Q&A through workflow
        workflow_state["stage"] = "questions_answers"
        result = await onboarding_workflow._questions_answers_node(workflow_state)
        
        # Send AI response
        if result["messages"]:
            last_message = result["messages"][-1]
            await message.answer(last_message.content)
        
        # Update state
        await state.update_data(workflow_state=result)
        
        # Check if ready for completion
        if result.get("next_action") == "completion":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Завершить адаптацию", callback_data="complete_onboarding")]
            ])
            
            completion_prompts = {
                "ru": "Отличная работа! Готовы завершить процесс адаптации?",
                "en": "Great work! Ready to complete the onboarding process?",
                "ar": "عمل رائع! هل أنت مستعد لإكمال عملية التأهيل؟"
            }
            
            await message.answer(
                completion_prompts.get(language, completion_prompts["ru"]),
                reply_markup=keyboard
            )
        
    except Exception as e:
        logger.error("Q&A handler error", error=str(e), user_id=message.from_user.id)
        await message.answer("Произошла ошибка при обработке вопроса.")


@router.callback_query(F.data == "complete_onboarding")
async def complete_onboarding_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle onboarding completion."""
    try:
        user_data = await state.get_data()
        workflow_state = user_data.get("workflow_state", {})
        
        # Run completion workflow
        workflow_state["stage"] = "completion"
        result = await onboarding_workflow._completion_node(workflow_state)
        
        # Send completion message
        if result["messages"]:
            last_message = result["messages"][-1]
            await callback.message.edit_text(last_message.content)
        
        # Set completed state
        await state.set_state(OnboardingStates.COMPLETED)
        await state.update_data(workflow_state=result)
        
        logger.info(
            "Onboarding completed",
            user_id=callback.from_user.id,
            completion_score=result.get("completion_score", 0)
        )
        
        await callback.answer("Адаптация завершена!")
        
    except Exception as e:
        logger.error("Completion handler error", error=str(e), user_id=callback.from_user.id)
        await callback.answer("Ошибка при завершении адаптации")


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    """Handle /help command."""
    help_text = """
🤖 Бот для адаптации сотрудников с AI-поддержкой

📋 Основные команды:
/start - Начать процесс адаптации
/help - Показать эту справку
/status - Показать текущий статус адаптации

🤖 AI-помощник:
/ask <вопрос> - Задать прямой вопрос AI-помощнику
/clear_memory - Очистить историю диалога с AI
/rag_stats - Показать статистику AI-системы

🔧 Возможности бота:
• Интеллектуальные ответы на вопросы о компании
• Семантический поиск по документам
• Персонализированная адаптация
• Многоязычная поддержка
• Кэширование для быстрых ответов

💡 Примеры вопросов:
• "Какие документы нужны для отпуска?"
• "Где находится столовая?"
• "Как работает система пропусков?"
• "What are the working hours?"

🌍 Поддерживаемые языки: Русский, English, العربية

ℹ️ Просто напишите свой вопрос, и AI-помощник найдет ответ в корпоративных документах!
    """
    
    await message.answer(help_text)


@router.message(Command("status"))
async def status_handler(message: Message, state: FSMContext) -> None:
    """Handle /status command."""
    try:
        user_data = await state.get_data()
        current_state = await state.get_state()
        workflow_state = user_data.get("workflow_state", {})
        
        if not workflow_state:
            await message.answer("Адаптация не начата. Используйте /start для начала.")
            return
        
        stage = workflow_state.get("stage", "unknown")
        completion_score = workflow_state.get("completion_score", 0)
        documents_count = len(workflow_state.get("documents_reviewed", []))
        questions_count = len(workflow_state.get("questions_asked", []))
        
        status_text = f"""
📊 Статус адаптации:

🎯 Текущий этап: {stage}
📈 Прогресс: {completion_score:.1f}%
📚 Изучено документов: {documents_count}
❓ Задано вопросов: {questions_count}

Продолжайте процесс адаптации!
        """
        
        await message.answer(status_text)
        
    except Exception as e:
        logger.error("Status handler error", error=str(e), user_id=message.from_user.id)
        await message.answer("Ошибка при получении статуса.")


@router.message(Command("ask"))
async def ask_handler(message: Message, state: FSMContext) -> None:
    """Handle direct RAG questions outside of onboarding flow."""
    try:
        user_id = message.from_user.id
        query = message.text.replace("/ask", "").strip()
        
        if not query:
            await message.answer(
                "Пожалуйста, задайте вопрос после команды /ask\n"
                "Например: /ask Какие документы нужны для отпуска?"
            )
            return
        
        # Get user data for context
        user_data = await state.get_data()
        user_info = user_data.get("user_info", {})
        language = user_data.get("language", "ru")
        
        # Process query through hybrid RAG
        rag_result = await hybrid_rag_service.process_query(
            query=query,
            user_id=user_id,
            user_info=user_info,
            language=language,
            use_conversation_memory=False  # Use simple mode for direct questions
        )
        
        response = rag_result["answer"]
        source_docs = rag_result.get("source_documents", [])
        
        # Add source information if available
        if source_docs:
            response += f"\n\n📚 Источники: {len(source_docs)} документ(ов)"
        
        await message.answer(response)
        
        logger.info(
            "Direct RAG query processed",
            user_id=user_id,
            query_length=len(query),
            complexity=rag_result.get("query_complexity"),
            source_count=len(source_docs)
        )
        
    except Exception as e:
        logger.error("Ask handler error", error=str(e), user_id=message.from_user.id)
        await message.answer(
            "Произошла ошибка при обработке вопроса. Попробуйте позже или обратитесь к HR."
        )


@router.message(Command("clear_memory"))
async def clear_memory_handler(message: Message) -> None:
    """Clear user's conversation memory."""
    try:
        user_id = message.from_user.id
        
        # Clear hybrid RAG memory
        success = await hybrid_rag_service.clear_user_memory(user_id)
        
        # Clear cache
        await vector_cache_service.invalidate_user_cache(user_id)
        
        if success:
            await message.answer(
                "✅ История диалога очищена.\n"
                "✅ Conversation history cleared.\n"
                "✅ تم مسح تاريخ المحادثة."
            )
        else:
            await message.answer(
                "ℹ️ История диалога уже пуста.\n"
                "ℹ️ Conversation history is already empty.\n"
                "ℹ️ تاريخ المحادثة فارغ بالفعل."
            )
        
        logger.info("User memory cleared", user_id=user_id)
        
    except Exception as e:
        logger.error("Clear memory error", error=str(e), user_id=message.from_user.id)
        await message.answer("Произошла ошибка при очистке памяти.")


@router.message(Command("rag_stats"))
async def rag_stats_handler(message: Message) -> None:
    """Show RAG system statistics."""
    try:
        user_id = message.from_user.id
        
        # Get user conversation history
        history = await hybrid_rag_service.get_user_conversation_history(user_id)
        
        # Get cache stats
        cache_stats = await vector_cache_service.get_cache_stats()
        
        # Get RAG health
        health = await hybrid_rag_service.health_check()
        
        stats_text = f"""📊 RAG System Statistics

👤 Your Stats:
• Conversation messages: {len(history)}
• Active conversations: {cache_stats.get('key_counts', {}).get('user_context', 0)}

🔧 System Health:
• Status: {health.get('status', 'unknown')}
• Vector DB points: {health.get('vector_store', {}).get('points_count', 0)}
• LLM Model: {health.get('llm', {}).get('model', 'unknown')}

💾 Cache Stats:
• Search cache: {cache_stats.get('key_counts', {}).get('search', 0)} entries
• Embedding cache: {cache_stats.get('key_counts', {}).get('embedding', 0)} entries
• Memory usage: {cache_stats.get('redis_info', {}).get('used_memory', 'unknown')}
"""
        
        await message.answer(stats_text)
        
    except Exception as e:
        logger.error("RAG stats error", error=str(e), user_id=message.from_user.id)
        await message.answer("Произошла ошибка при получении статистики.")


@router.message()
async def default_handler(message: Message, state: FSMContext) -> None:
    """Handle all other messages with enhanced RAG support."""
    try:
        current_state = await state.get_state()
        user_id = message.from_user.id
        
        if current_state == OnboardingStates.COMPLETED:
            # For completed users, provide direct RAG assistance
            if message.text and len(message.text.strip()) > 3:
                user_data = await state.get_data()
                user_info = user_data.get("user_info", {})
                language = user_data.get("language", "ru")
                
                try:
                    rag_result = await hybrid_rag_service.process_query(
                        query=message.text,
                        user_id=user_id,
                        user_info=user_info,
                        language=language,
                        use_conversation_memory=True
                    )
                    
                    response = rag_result["answer"]
                    await message.answer(response)
                    return
                    
                except Exception as rag_error:
                    logger.error("RAG processing failed in default handler", error=str(rag_error))
            
            await message.answer(
                "Ваша адаптация завершена! Если у вас есть дополнительные вопросы, "
                "используйте команду /ask или обратитесь к HR."
            )
            
        elif current_state is None:
            await message.answer(
                "Добро пожаловать! Используйте /start для начала процесса адаптации "
                "или /ask для прямых вопросов."
            )
        else:
            # Forward to appropriate handler based on state
            if current_state == OnboardingStates.PROFILE_SETUP:
                await profile_setup_handler(message, state)
            elif current_state == OnboardingStates.DOCUMENT_REVIEW:
                await document_review_handler(message, state)
            elif current_state == OnboardingStates.QUESTIONS_ANSWERS:
                await questions_answers_handler(message, state)
            else:
                await message.answer("Не понимаю. Используйте /help для справки.")
                
    except Exception as e:
        logger.error("Default handler error", error=str(e), user_id=message.from_user.id)
        await message.answer("Произошла ошибка. Попробуйте позже.")