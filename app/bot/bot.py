"""
Simplified Telegram bot setup.
"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import get_logger
from app.bot.handlers import router
from app.ai import vector_store

logger = get_logger("bot")


async def create_bot() -> Bot:
    """Create bot instance."""
    settings = get_settings()
    return Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )


async def create_dispatcher() -> Dispatcher:
    """Create dispatcher with Redis storage."""
    settings = get_settings()
    
    # Create Redis storage for FSM
    redis_client = redis.from_url(settings.redis_url)
    storage = RedisStorage(redis_client)
    
    # Create dispatcher
    dp = Dispatcher(storage=storage)
    
    # Include handlers
    dp.include_router(router)
    
    return dp


async def on_startup() -> None:
    """Startup handler."""
    logger.info("Bot starting up...")
    
    # Initialize vector store
    try:
        await vector_store.initialize_collection()
        logger.info("Vector store initialized")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")


async def on_shutdown() -> None:
    """Shutdown handler."""
    logger.info("Bot shutting down...")


async def run_bot() -> None:
    """Run the bot in polling mode."""
    bot = await create_bot()
    dp = await create_dispatcher()
    
    # Register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    logger.info("Starting bot in polling mode")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
