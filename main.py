"""
Main entry point for the RAG Telegram bot.
"""

import asyncio
import sys

from app.core.logging import configure_logging, get_logger
from app.bot.bot import run_bot


async def main():
    """Main entry point."""
    configure_logging()
    logger = get_logger("main")
    
    logger.info("Starting RAG Telegram bot")
    
    try:
        await run_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
