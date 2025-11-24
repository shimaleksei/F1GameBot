"""Keyboards for F1 Game Bot."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_races_menu() -> InlineKeyboardMarkup:
    """Get admin races management menu keyboard (C-006)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📋 Просмотр гонок", callback_data="admin_races_view"))
    builder.add(InlineKeyboardButton(text="➕ Добавить гонку", callback_data="admin_races_add"))
    builder.add(InlineKeyboardButton(text="✏️ Редактировать гонку", callback_data="admin_races_edit"))
    builder.add(InlineKeyboardButton(text="🗑️ Удалить гонку", callback_data="admin_races_delete"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_races_cancel"))
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_race_list_keyboard(races: list, prefix: str = "race") -> InlineKeyboardMarkup:
    """Get keyboard with list of races."""
    builder = InlineKeyboardBuilder()
    for race in races:
        status_emoji = "✅" if race.status == "finished" else "🏁"
        builder.add(InlineKeyboardButton(
            text=f"{status_emoji} {race.name}",
            callback_data=f"{prefix}_{race.id}"
        ))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    builder.adjust(1)
    return builder.as_markup()


def get_confirm_keyboard(confirm_data: str, cancel_data: str = "cancel") -> InlineKeyboardMarkup:
    """Get confirmation keyboard."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_data))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_data))
    builder.adjust(2)
    return builder.as_markup()


def get_cancel_keyboard(cancel_data: str = "cancel") -> InlineKeyboardMarkup:
    """Get cancel keyboard."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_data))
    return builder.as_markup()

