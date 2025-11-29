"""Notification service for sending notifications to users."""
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from services.user_service import get_all_users

logger = logging.getLogger(__name__)


async def notify_all_users_about_bet(
    bot: Bot,
    user_name: str,
    user_telegram_id: int,
    race_name: str,
    race_date: str,
    race_time: str,
    driver_1st: str,
    driver_2nd: str,
    driver_3rd: str,
    driver_1st_full: str = "",
    driver_2nd_full: str = "",
    driver_3rd_full: str = "",
    is_update: bool = False
) -> int:
    """
    Send notification to all allowed users about a new/updated bet.
    
    Args:
        bot: Bot instance for sending messages
        user_name: Name of the user who made the bet
        user_telegram_id: Telegram ID of the user who made the bet (to exclude from notifications)
        race_name: Name of the race
        race_date: Date of the race
        race_time: Time of the race
        driver_1st: Driver code for 1st place
        driver_2nd: Driver code for 2nd place
        driver_3rd: Driver code for 3rd place
        driver_1st_full: Full name of driver for 1st place (optional)
        driver_2nd_full: Full name of driver for 2nd place (optional)
        driver_3rd_full: Full name of driver for 3rd place (optional)
        is_update: Whether this is an update to existing bet
    
    Returns:
        Number of successfully sent notifications
    """
    # Get all allowed users (except the user who made the bet)
    all_users = await get_all_users()
    allowed_users = [u for u in all_users if u.is_allowed and u.telegram_id != user_telegram_id]
    
    if not allowed_users:
        logger.info("No other allowed users found for bet notification")
        return 0
    
    # Format driver names
    def format_driver(code: str, full_name: str) -> str:
        if full_name:
            return f"{code} - {full_name}"
        return code
    
    # Create notification message
    action_text = "обновил ставку" if is_update else "сделал ставку"
    message_text = (
        f"🎯 <b>{user_name}</b> {action_text}!\n\n"
        f"🏁 Гонка: <b>{race_name}</b>\n"
        f"📅 Дата: {race_date} в {race_time}\n\n"
        f"Ставка:\n"
        f"🥇 1-е: {format_driver(driver_1st, driver_1st_full)}\n"
        f"🥈 2-е: {format_driver(driver_2nd, driver_2nd_full)}\n"
        f"🥉 3-е: {format_driver(driver_3rd, driver_3rd_full)}"
    )
    
    # Send notification to all allowed users
    success_count = 0
    for user in allowed_users:
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message_text
            )
            success_count += 1
        except TelegramBadRequest as e:
            # User might have blocked the bot or deleted account
            if "chat not found" in str(e).lower() or "blocked" in str(e).lower():
                logger.warning(f"Could not send notification to user {user.telegram_id}: {e}")
            else:
                logger.error(f"Error sending notification to user {user.telegram_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending notification to user {user.telegram_id}: {e}")
    
    logger.info(f"Bet notification sent to {success_count}/{len(allowed_users)} users")
    return success_count

