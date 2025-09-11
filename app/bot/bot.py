"""
Main Telegram bot setup and configuration.
"""

import asyncio
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import get_logger, configure_logging
from app.bot.handlers import router
from app.core.exceptions import TelegramBotError

logger = get_logger("bot")


class TelegramBot:
    """Telegram bot manager."""
    
    def __init__(self):
        self.settings = get_settings()
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.redis_storage: Optional[RedisStorage] = None
    
    async def create_bot(self) -> Bot:
        """Create bot instance."""
        if self.bot is None:
            self.bot = Bot(
                token=self.settings.telegram.bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
        return self.bot
    
    async def create_dispatcher(self) -> Dispatcher:
        """Create dispatcher with Redis storage."""
        if self.dp is None:
            # Create Redis storage for FSM
            redis_client = redis.from_url(self.settings.redis.url)
            self.redis_storage = RedisStorage(redis_client)
            
            # Create dispatcher
            self.dp = Dispatcher(storage=self.redis_storage)
            
            # Include routers
            self.dp.include_router(router)
            
            # Add startup and shutdown handlers
            self.dp.startup.register(self._on_startup)
            self.dp.shutdown.register(self._on_shutdown)
        
        return self.dp
    
    async def _on_startup(self) -> None:
        """Bot startup handler."""
        logger.info("Bot starting up")
        
        # Initialize AI components
        try:
            from app.ai.langchain.vector_store import vector_store
            await vector_store.initialize_collection()
            logger.info("Vector store initialized")
        except Exception as e:
            logger.error("Failed to initialize vector store", error=str(e))
        
        # Set bot commands
        bot = await self.create_bot()
        await self._set_bot_commands(bot)
        
        logger.info("Bot startup completed")
    
    async def _on_shutdown(self) -> None:
        """Bot shutdown handler."""
        logger.info("Bot shutting down")
        
        # Close Redis storage
        if self.redis_storage:
            await self.redis_storage.close()
        
        # Close bot session
        if self.bot:
            await self.bot.session.close()
        
        logger.info("Bot shutdown completed")
    
    async def _set_bot_commands(self, bot: Bot) -> None:
        """Set bot commands menu."""
        from aiogram.types import BotCommand
        
        commands = [
            BotCommand(command="start", description="Начать процесс адаптации"),
            BotCommand(command="help", description="Показать справку"),
            BotCommand(command="status", description="Показать статус адаптации"),
        ]
        
        await bot.set_my_commands(commands)
        logger.info("Bot commands set", commands_count=len(commands))
    
    async def start_polling(self) -> None:
        """Start bot in polling mode."""
        try:
            bot = await self.create_bot()
            dp = await self.create_dispatcher()
            
            logger.info("Starting bot in polling mode")
            await dp.start_polling(bot)
            
        except Exception as e:
            logger.error("Polling mode failed", error=str(e))
            raise TelegramBotError(
                message=f"Failed to start polling: {str(e)}",
                error_code="POLLING_FAILED"
            )


# Global bot instance
telegram_bot = TelegramBot()


async def run_bot_polling():
    """Run bot in polling mode."""
    configure_logging()
    
    try:
        await telegram_bot.start_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Bot crashed", error=str(e))
        raise

