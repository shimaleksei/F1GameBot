"""Custom filters for F1 Game Bot."""
from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from config import is_admin
from services.user_service import get_user_by_telegram_id


class AdminFilter(BaseFilter):
    """Filter to check if user is admin."""
    
    async def __call__(self, obj: Union[Message, CallbackQuery], *args, **kwargs) -> bool:
        """Check if user is admin."""
        if hasattr(obj, 'from_user') and obj.from_user:
            return is_admin(obj.from_user.id)
        return False


class AllowedUserFilter(BaseFilter):
    """Filter to check if user is allowed to use the bot (whitelist)."""
    
    async def __call__(self, obj: Union[Message, CallbackQuery], *args, **kwargs) -> bool:
        """Check if user is allowed to use the bot."""
        if hasattr(obj, 'from_user') and obj.from_user:
            user_id = obj.from_user.id
            # Admins are always allowed
            if is_admin(user_id):
                return True
            # Check if user is in whitelist
            user = await get_user_by_telegram_id(user_id)
            return user is not None and user.is_allowed
        return False

