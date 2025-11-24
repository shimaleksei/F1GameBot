"""Custom filters for F1 Game Bot."""
from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from config import is_admin


class AdminFilter(BaseFilter):
    """Filter to check if user is admin."""
    
    async def __call__(self, obj: Union[Message, CallbackQuery], *args, **kwargs) -> bool:
        """Check if user is admin."""
        if hasattr(obj, 'from_user') and obj.from_user:
            return is_admin(obj.from_user.id)
        return False

