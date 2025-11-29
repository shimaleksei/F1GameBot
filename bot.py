"""Main bot file for F1 Game Bot."""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, DATABASE_PATH, validate_config
from database import init_db
from handlers import user_handlers, admin_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to start the bot."""
    # Validate configuration
    try:
        validate_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    # Initialize database
    logger.info("Initializing database...")
    logger.info(f"Database path: {DATABASE_PATH}")
    await init_db()
    logger.info("Database initialized successfully")
    
    # Initialize bot and dispatcher with FSM storage
    storage = MemoryStorage()
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)
    
    # Register routers
    # IMPORTANT: admin_handlers must be registered BEFORE user_handlers
    # to ensure admin commands are processed before the catch-all handler
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)
    
    # Start polling
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)

