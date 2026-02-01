"""
Simplified Telegram bot setup.
"""

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import get_settings
from app.core.logging import get_logger
from app.bot.handlers import router
from app.ai import vector_store

logger = get_logger("bot")


async def create_bot() -> Bot:
    """Create bot instance."""
    settings = get_settings()
    return Bot(token=settings.telegram_bot_token)


async def create_dispatcher() -> Dispatcher:
    """Create dispatcher with storage."""
    settings = get_settings()
    
    # Try to use Redis storage, fall back to memory storage
    storage = None
    
    try:
        import redis.asyncio as redis
        from aiogram.fsm.storage.redis import RedisStorage
        
        # Test connection
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        storage = RedisStorage(redis_client)
        logger.info("Using Redis storage for FSM")
    except Exception as e:
        logger.warning(f"Redis not available, using memory storage: {e}")
        storage = MemoryStorage()
    
    # Create dispatcher
    dp = Dispatcher(storage=storage)
    
    # Include handlers
    dp.include_router(router)
    
    return dp


async def set_bot_commands(bot: Bot) -> None:
    """Set bot menu commands."""
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="help", description="📚 Справка"),
        BotCommand(command="status", description="📊 Статус системы"),
        BotCommand(command="ask", description="❓ Задать вопрос"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Bot commands set")


async def on_startup(bot: Bot) -> None:
    """Startup handler."""
    logger.info("Bot starting up...")
    
    # Set bot commands menu
    await set_bot_commands(bot)
    
    # Initialize vector store (non-blocking)
    try:
        success = await vector_store.initialize_collection()
        if success:
            logger.info("Vector store initialized")
        else:
            logger.warning("Vector store not available - document features disabled")
    except Exception as e:
        logger.warning(f"Vector store initialization failed: {e}")


async def on_shutdown() -> None:
    """Shutdown handler."""
    logger.info("Bot shutting down...")


async def run_bot() -> None:
    """Run the bot in polling mode."""
    bot = await create_bot()
    dp = await create_dispatcher()
    
    # Register startup/shutdown handlers
    dp.startup.register(lambda: on_startup(bot))
    dp.shutdown.register(on_shutdown)
    
    logger.info("Starting bot in polling mode")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
