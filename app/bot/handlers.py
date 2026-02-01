"""
Simplified Telegram bot handlers - document upload and Q&A only.
"""

import os
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ai import rag, document_processor

logger = get_logger("bot.handlers")
router = Router()


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    """Handle /start command."""
    welcome_text = """
👋 Добро пожаловать в корпоративного AI-помощника!

📚 Я могу отвечать на вопросы по документам компании.

🔧 Доступные команды:
/help - Показать справку
/ask <вопрос> - Задать вопрос
/status - Статус системы

📎 Для загрузки документов просто отправьте файл (PDF, DOCX, TXT).

💡 Примеры вопросов:
• "Какие документы нужны для отпуска?"
• "Где находится офис?"
• "Как оформить больничный?"
    """
    await message.answer(welcome_text)


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    """Handle /help command."""
    help_text = """
🤖 Корпоративный AI-помощник

📋 Команды:
/start - Начать работу
/help - Эта справка
/ask <вопрос> - Задать вопрос AI
/status - Проверить статус системы

📎 Загрузка документов:
Отправьте файл в формате PDF, DOCX или TXT.
Документ будет обработан и добавлен в базу знаний.

❓ Как задавать вопросы:
Используйте команду /ask или просто напишите вопрос.
AI найдет релевантную информацию в документах и ответит.

🔍 Примеры:
/ask Какой график работы офиса?
/ask Как оформить командировку?
    """
    await message.answer(help_text)


@router.message(Command("status"))
async def status_handler(message: Message) -> None:
    """Handle /status command."""
    try:
        health = await rag.health_check()
        
        status_text = f"""
📊 Статус системы:

🔧 RAG: {health.get('status', 'unknown')}
📚 Документов в базе: {health.get('vector_store', {}).get('points_count', 'N/A')}
        """
        await message.answer(status_text)
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        await message.answer("❌ Ошибка при проверке статуса")


@router.message(Command("ask"))
async def ask_handler(message: Message) -> None:
    """Handle /ask command - process question through RAG."""
    try:
        # Extract question from command
        query = message.text.replace("/ask", "").strip()
        
        if not query:
            await message.answer(
                "❓ Пожалуйста, укажите вопрос.\n"
                "Пример: /ask Какой график работы?"
            )
            return
        
        # Send "typing" indicator
        await message.answer("🔍 Ищу ответ...")
        
        # Process through RAG
        result = await rag.process_query(
            query=query,
            user_id=message.from_user.id,
            language="ru"
        )
        
        response = result["answer"]
        
        # Add source info if available
        if result.get("source_documents"):
            sources = set(doc["source"] for doc in result["source_documents"])
            response += f"\n\n📚 Источники: {', '.join(sources)}"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ask handler error: {e}")
        await message.answer("❌ Произошла ошибка при обработке вопроса.")


@router.message(F.document)
async def document_handler(message: Message) -> None:
    """Handle document upload."""
    try:
        document = message.document
        settings = get_settings()
        
        # Check file size
        if document.file_size > settings.max_file_size:
            await message.answer(
                f"❌ Файл слишком большой.\n"
                f"Максимальный размер: {settings.max_file_size // 1024 // 1024} MB"
            )
            return
        
        # Check file extension
        filename = document.file_name or "document"
        ext = Path(filename).suffix.lower()
        allowed = document_processor.get_allowed_extensions()
        
        if ext not in allowed:
            await message.answer(
                f"❌ Неподдерживаемый формат файла.\n"
                f"Поддерживаемые форматы: {', '.join(allowed)}"
            )
            return
        
        await message.answer("📥 Загружаю документ...")
        
        # Download file
        file = await message.bot.get_file(document.file_id)
        file_content = await message.bot.download_file(file.file_path)
        
        # Save file
        file_path = document_processor.save_uploaded_file(
            file_content.read(),
            filename
        )
        
        await message.answer("⚙️ Обрабатываю документ...")
        
        # Process document
        result = await document_processor.process_document(
            file_path=file_path,
            source_name=filename
        )
        
        if result["success"]:
            await message.answer(
                f"✅ Документ обработан!\n\n"
                f"📄 Файл: {result['source']}\n"
                f"📊 Частей: {result['chunks_count']}\n\n"
                f"Теперь вы можете задавать вопросы по этому документу."
            )
        else:
            await message.answer(
                f"❌ Ошибка при обработке документа:\n{result.get('error', 'Неизвестная ошибка')}"
            )
        
        # Clean up file
        try:
            os.remove(file_path)
        except:
            pass
        
    except Exception as e:
        logger.error(f"Document handler error: {e}")
        await message.answer("❌ Произошла ошибка при обработке документа.")


@router.message()
async def default_handler(message: Message) -> None:
    """Handle all other text messages as questions."""
    if not message.text:
        return
    
    text = message.text.strip()
    
    if len(text) < 3:
        await message.answer("❓ Пожалуйста, задайте более развернутый вопрос.")
        return
    
    try:
        # Send "typing" indicator
        await message.answer("🔍 Ищу ответ...")
        
        # Process through RAG
        result = await rag.process_query(
            query=text,
            user_id=message.from_user.id,
            language="ru"
        )
        
        response = result["answer"]
        
        # Add source info if available
        if result.get("source_documents"):
            sources = set(doc["source"] for doc in result["source_documents"])
            response += f"\n\n📚 Источники: {', '.join(sources)}"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Default handler error: {e}")
        await message.answer("❌ Произошла ошибка при обработке вопроса.")
