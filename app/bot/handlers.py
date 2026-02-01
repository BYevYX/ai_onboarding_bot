"""
Telegram bot handlers with inline keyboards.
"""

import os
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ai import rag, document_processor, vector_store

logger = get_logger("bot.handlers")
router = Router()


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Get main menu keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❓ Задать вопрос", callback_data="ask_question"),
            InlineKeyboardButton(text="📊 Статус", callback_data="status")
        ],
        [
            InlineKeyboardButton(text="📚 Справка", callback_data="help"),
            InlineKeyboardButton(text="📄 Загрузить документ", callback_data="upload_doc")
        ]
    ])


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Get back to menu keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")]
    ])


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    """Handle /start command."""
    welcome_text = """
🤖 Корпоративный AI-помощник

Я помогу найти информацию в документах компании и ответить на ваши вопросы.

📌 Что я умею:
• Отвечать на вопросы по документам
• Искать информацию в базе знаний
• Обрабатывать загруженные файлы

Выберите действие:
    """
    await message.answer(welcome_text, reply_markup=get_main_keyboard())


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery) -> None:
    """Handle main menu callback."""
    text = """
🤖 Корпоративный AI-помощник

Выберите действие:
    """
    await callback.message.edit_text(text, reply_markup=get_main_keyboard())
    await callback.answer()


@router.message(Command("help"))
@router.callback_query(F.data == "help")
async def help_handler(event: Message | CallbackQuery) -> None:
    """Handle /help command and callback."""
    help_text = """
📚 Справка

🔹 Как задать вопрос:
Просто напишите ваш вопрос в чат или нажмите "Задать вопрос"

🔹 Загрузка документов:
Отправьте файл (PDF, DOCX, TXT) в чат

🔹 Примеры вопросов:
• Какой график работы офиса?
• Как оформить отпуск?
• Где найти шаблон заявления?

💡 Чем больше документов загружено, тем точнее ответы!
    """
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(help_text, reply_markup=get_back_keyboard())
        await event.answer()
    else:
        await event.answer(help_text, reply_markup=get_back_keyboard())


@router.message(Command("status"))
@router.callback_query(F.data == "status")
async def status_handler(event: Message | CallbackQuery) -> None:
    """Handle /status command and callback."""
    try:
        health = await rag.health_check()
        
        vs_status = health.get('vector_store', {})
        qdrant_ok = vs_status.get('status') != 'unavailable'
        points = vs_status.get('points_count', 0)
        
        qdrant_emoji = "✅" if qdrant_ok else "❌"
        
        status_text = f"""
📊 Статус системы

{qdrant_emoji} База знаний: {"Подключена" if qdrant_ok else "Недоступна"}
📄 Документов в базе: {points if points else 0}
🤖 AI-модель: Готова

{"💡 Загрузите документы для работы с RAG" if points == 0 else "✨ Система готова к работе!"}
        """
        
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(status_text, reply_markup=get_back_keyboard())
            await event.answer()
        else:
            await event.answer(status_text, reply_markup=get_back_keyboard())
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        error_text = "❌ Ошибка при проверке статуса"
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(error_text, reply_markup=get_back_keyboard())
            await event.answer()
        else:
            await event.answer(error_text, reply_markup=get_back_keyboard())


@router.callback_query(F.data == "ask_question")
async def ask_question_callback(callback: CallbackQuery) -> None:
    """Handle ask question callback."""
    text = """
❓ Задайте ваш вопрос

Просто напишите вопрос в чат, и я найду ответ в документах компании.

💡 Примеры:
• Какой график работы?
• Как оформить командировку?
• Где взять справку?
    """
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "upload_doc")
async def upload_doc_callback(callback: CallbackQuery) -> None:
    """Handle upload document callback."""
    if not await vector_store.is_available():
        text = """
❌ База знаний недоступна

Для загрузки документов необходимо подключение к Qdrant.
Обратитесь к администратору.
        """
    else:
        text = """
📄 Загрузка документа

Отправьте файл в чат, и я добавлю его в базу знаний.

📌 Поддерживаемые форматы:
• PDF
• DOCX
• TXT

⚡ Максимальный размер: 10 MB
        """
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()


@router.message(Command("ask"))
async def ask_handler(message: Message) -> None:
    """Handle /ask command."""
    query = message.text.replace("/ask", "").strip()
    
    if not query:
        text = """
❓ Укажите вопрос после команды

Пример: /ask Какой график работы?

Или просто напишите вопрос в чат.
        """
        await message.answer(text, reply_markup=get_back_keyboard())
        return
    
    await process_question(message, query)


@router.message(F.document)
async def document_handler(message: Message) -> None:
    """Handle document upload."""
    try:
        if not await vector_store.is_available():
            await message.answer(
                "❌ База знаний недоступна\n\n"
                "Загрузка документов временно невозможна.",
                reply_markup=get_back_keyboard()
            )
            return
        
        document = message.document
        settings = get_settings()
        
        # Check file size
        if document.file_size > settings.max_file_size:
            await message.answer(
                f"❌ Файл слишком большой\n\n"
                f"Максимальный размер: {settings.max_file_size // 1024 // 1024} MB",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Check file extension
        filename = document.file_name or "document"
        ext = Path(filename).suffix.lower()
        allowed = document_processor.get_allowed_extensions()
        
        if ext not in allowed:
            await message.answer(
                f"❌ Неподдерживаемый формат\n\n"
                f"Поддерживаемые форматы: {', '.join(allowed)}",
                reply_markup=get_back_keyboard()
            )
            return
        
        status_msg = await message.answer("📥 Загружаю документ...")
        
        # Download file
        file = await message.bot.get_file(document.file_id)
        file_content = await message.bot.download_file(file.file_path)
        
        # Save file
        file_path = document_processor.save_uploaded_file(
            file_content.read(),
            filename
        )
        
        await status_msg.edit_text("⚙️ Обрабатываю документ...")
        
        # Process document
        result = await document_processor.process_document(
            file_path=file_path,
            source_name=filename
        )
        
        if result["success"]:
            success_text = f"""
✅ Документ загружен!

📄 Файл: {result['source']}
📊 Обработано частей: {result['chunks_count']}

Теперь вы можете задавать вопросы по этому документу.
            """
            await status_msg.edit_text(success_text, reply_markup=get_main_keyboard())
        else:
            await status_msg.edit_text(
                f"❌ Ошибка обработки\n\n{result.get('error', 'Неизвестная ошибка')}",
                reply_markup=get_back_keyboard()
            )
        
        # Clean up file
        try:
            os.remove(file_path)
        except:
            pass
        
    except Exception as e:
        logger.error(f"Document handler error: {e}")
        await message.answer(
            "❌ Ошибка при обработке документа",
            reply_markup=get_back_keyboard()
        )


@router.message()
async def default_handler(message: Message) -> None:
    """Handle all other text messages as questions."""
    if not message.text:
        return
    
    text = message.text.strip()
    
    if len(text) < 3:
        await message.answer(
            "❓ Слишком короткий вопрос\n\n"
            "Пожалуйста, задайте более развернутый вопрос.",
            reply_markup=get_main_keyboard()
        )
        return
    
    await process_question(message, text)


async def process_question(message: Message, query: str) -> None:
    """Process a question through RAG."""
    try:
        status_msg = await message.answer("🔍 Ищу ответ...")
        
        result = await rag.process_query(
            query=query,
            user_id=message.from_user.id,
            language="ru"
        )
        
        response = result["answer"]
        
        # Add source info
        if result.get("source_documents"):
            sources = set(doc["source"] for doc in result["source_documents"])
            response += f"\n\n📚 Источники: {', '.join(sources)}"
        elif not result.get("has_context"):
            response += "\n\n⚠️ Ответ без контекста из документов"
        
        await status_msg.edit_text(response, reply_markup=get_main_keyboard())
        
    except Exception as e:
        logger.error(f"Question processing error: {e}")
        await message.answer(
            "❌ Ошибка при обработке вопроса",
            reply_markup=get_back_keyboard()
        )
