"""
Main entry point for the Telegram onboarding bot application.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.logging import configure_logging, get_logger
from app.core.config import get_settings


async def run_bot():
    """Run the Telegram bot in polling mode."""
    configure_logging()
    logger = get_logger("main")
    
    try:
        logger.info("Starting Telegram onboarding bot")
        
        from app.bot.bot import run_bot_polling
        await run_bot_polling()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Bot crashed", error=str(e))
        raise


async def run_api():
    """Run the FastAPI application."""
    configure_logging()
    logger = get_logger("main")
    
    try:
        logger.info("Starting FastAPI application")
        
        import uvicorn
        from app.api.main import app
        
        settings = get_settings()
        
        config = uvicorn.Config(
            app,
            host=settings.api.host,
            port=settings.api.port,
            reload=settings.api.reload,
            log_level=settings.logging.level.lower()
        )
        
        server = uvicorn.Server(config)
        await server.serve()
        
    except KeyboardInterrupt:
        logger.info("API server stopped by user")
    except Exception as e:
        logger.error("API server crashed", error=str(e))
        raise


async def run_combined():
    """Run both bot and API server together."""
    configure_logging()
    logger = get_logger("main")
    
    logger.info("Starting combined bot and API server")
    
    # Create tasks for both services
    bot_task = asyncio.create_task(run_bot())
    api_task = asyncio.create_task(run_api())
    
    try:
        # Wait for either task to complete (or fail)
        done, pending = await asyncio.wait(
            [bot_task, api_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Check if any task failed
        for task in done:
            if task.exception():
                raise task.exception()
                
    except KeyboardInterrupt:
        logger.info("Services stopped by user")
        
        # Cancel all tasks
        bot_task.cancel()
        api_task.cancel()
        
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
            
        try:
            await api_task
        except asyncio.CancelledError:
            pass


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python main.py [bot|api|combined]")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    if mode == "bot":
        asyncio.run(run_bot())
    elif mode == "api":
        asyncio.run(run_api())
    elif mode == "combined":
        asyncio.run(run_combined())
    else:
        print("Invalid mode. Use 'bot', 'api', or 'combined'")
        sys.exit(1)


if __name__ == "__main__":
    main()