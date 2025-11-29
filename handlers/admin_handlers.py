"""Admin handlers for F1 Game Bot."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.filters import AdminFilter
from utils.keyboards import (
    get_admin_races_menu,
    get_race_list_keyboard,
    get_confirm_keyboard,
    get_cancel_keyboard
)
from services.race_service import (
    get_all_races,
    get_race_by_id,
    create_race,
    update_race,
    delete_race
)
from services.result_service import (
    get_races_without_results,
    get_result_by_race_id,
    create_or_update_result,
    calculate_and_save_points
)
from services.driver_service import get_all_drivers, get_driver_by_code
from services.user_service import get_all_users, get_user_by_telegram_id, set_user_allowed
from utils.keyboards import get_race_list_keyboard, get_confirm_keyboard, get_cancel_keyboard
from config import DEFAULT_TIMEZONE

router = Router()


# FSM States for race management
class AddRaceStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_time = State()


class EditRaceStates(StatesGroup):
    waiting_for_race = State()
    waiting_for_field = State()
    waiting_for_value = State()


class DeleteRaceStates(StatesGroup):
    waiting_for_race = State()
    waiting_for_confirm = State()


class EnterResultsStates(StatesGroup):
    waiting_for_race = State()
    waiting_for_1st = State()
    waiting_for_2nd = State()
    waiting_for_3rd = State()
    waiting_for_confirm = State()


@router.message(Command("admin_races"), AdminFilter())
async def cmd_admin_races(message: Message):
    """Handle /admin_races command (F-003, C-006)."""
    await message.answer(
        "🏁 <b>Управление гонками</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_races_menu()
    )


@router.message(Command("admin_races"), ~AdminFilter())
async def cmd_admin_races_not_admin(message: Message):
    """Handle /admin_races command for non-admins."""
    await message.answer("Вам не разрешено использовать эту команду.")


# View races
@router.callback_query(F.data == "admin_races_view", AdminFilter())
async def callback_view_races(callback: CallbackQuery):
    """View all races."""
    races = await get_all_races()
    
    if not races:
        await callback.message.edit_text(
            "📋 <b>Все гонки</b>\n\n"
            "Гонки не найдены. Добавьте первую гонку!",
            reply_markup=get_admin_races_menu()
        )
        await callback.answer()
        return
    
    text = "📋 <b>Все гонки</b>\n\n"
    for race in races:
        status_emoji = "✅" if race.status == "finished" else "🏁"
        status_text = "Завершена" if race.status == "finished" else "Предстоящая"
        text += f"{status_emoji} <b>{race.name}</b>\n"
        text += f"   📅 {race.date} в {race.start_time} ({race.timezone})\n"
        text += f"   Статус: {status_text}\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_admin_races_menu())
    await callback.answer()


# Add race flow
@router.callback_query(F.data == "admin_races_add", AdminFilter())
async def callback_add_race_start(callback: CallbackQuery, state: FSMContext):
    """Start add race flow."""
    await state.set_state(AddRaceStates.waiting_for_name)
    await callback.message.edit_text(
        "➕ <b>Добавить новую гонку</b>\n\n"
        "Отправьте название гонки (например, 'Гран-при Бахрейна'):",
        reply_markup=get_cancel_keyboard("admin_races_cancel")
    )
    await callback.answer()


@router.message(AddRaceStates.waiting_for_name, AdminFilter())
async def process_race_name(message: Message, state: FSMContext):
    """Process race name."""
    race_name = message.text.strip()
    if not race_name:
        await message.answer("Пожалуйста, отправьте корректное название гонки:")
        return
    
    await state.update_data(race_name=race_name)
    await state.set_state(AddRaceStates.waiting_for_date)
    await message.answer(
        f"Название гонки: <b>{race_name}</b>\n\n"
        "Теперь отправьте дату гонки в формате <b>YYYY-MM-DD</b>\n"
        "Пример: 2025-03-02",
        reply_markup=get_cancel_keyboard("admin_races_cancel")
    )


@router.message(AddRaceStates.waiting_for_date, AdminFilter())
async def process_race_date(message: Message, state: FSMContext):
    """Process race date."""
    date_str = message.text.strip()
    
    # Validate date format YYYY-MM-DD
    try:
        from datetime import datetime
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer(
            "Я не понимаю эту дату. Пожалуйста, используйте формат <b>YYYY-MM-DD</b>\n"
            "Пример: 2025-03-02",
            reply_markup=get_cancel_keyboard("admin_races_cancel")
        )
        return
    
    await state.update_data(race_date=date_str)
    await state.set_state(AddRaceStates.waiting_for_time)
    await message.answer(
        f"Дата: <b>{date_str}</b>\n\n"
        "Теперь отправьте время старта гонки в формате <b>HH:MM</b> (24-часовой формат)\n"
        "Пример: 16:00",
        reply_markup=get_cancel_keyboard("admin_races_cancel")
    )


@router.message(AddRaceStates.waiting_for_time, AdminFilter())
async def process_race_time(message: Message, state: FSMContext):
    """Process race time."""
    time_str = message.text.strip()
    
    # Validate time format HH:MM
    try:
        from datetime import datetime
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await message.answer(
            "Я не понимаю это время. Пожалуйста, используйте формат <b>HH:MM</b> (24-часовой формат)\n"
            "Пример: 16:00",
            reply_markup=get_cancel_keyboard("admin_races_cancel")
        )
        return
    
    data = await state.get_data()
    race_name = data.get("race_name")
    race_date = data.get("race_date")
    
    # Create race
    try:
        race = await create_race(race_name, race_date, time_str, DEFAULT_TIMEZONE)
        status_text = "Завершена" if race.status == "finished" else "Предстоящая"
        await message.answer(
            f"✅ <b>Гонка успешно добавлена!</b>\n\n"
            f"Название: <b>{race.name}</b>\n"
            f"Дата: {race.date}\n"
            f"Время: {race.start_time} ({race.timezone})\n"
            f"Статус: {status_text}",
            reply_markup=get_admin_races_menu()
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при создании гонки: {str(e)}\n\n"
            "Попробуйте снова.",
            reply_markup=get_admin_races_menu()
        )
    
    await state.clear()


# Edit race flow
@router.callback_query(F.data == "admin_races_edit", AdminFilter())
async def callback_edit_race_start(callback: CallbackQuery, state: FSMContext):
    """Start edit race flow."""
    races = await get_all_races()
    
    if not races:
        await callback.message.edit_text(
            "Гонки не найдены. Добавьте первую гонку!",
            reply_markup=get_admin_races_menu()
        )
        await callback.answer()
        return
    
    await state.set_state(EditRaceStates.waiting_for_race)
    await callback.message.edit_text(
        "✏️ <b>Редактировать гонку</b>\n\n"
        "Выберите гонку для редактирования:",
        reply_markup=get_race_list_keyboard(races, "edit_race")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_race_"), AdminFilter())
async def callback_edit_race_select(callback: CallbackQuery, state: FSMContext):
    """Select race to edit."""
    race_id = int(callback.data.split("_")[-1])
    race = await get_race_by_id(race_id)
    
    if not race:
        await callback.answer("Я не могу найти эту гонку. Проверьте ID.", show_alert=True)
        await callback.message.edit_text(
            "Гонка не найдена.",
            reply_markup=get_admin_races_menu()
        )
        await state.clear()
        return
    
    await state.update_data(race_id=race_id)
    await state.set_state(EditRaceStates.waiting_for_field)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📝 Название", callback_data="edit_field_name"))
    builder.add(InlineKeyboardButton(text="📅 Дата", callback_data="edit_field_date"))
    builder.add(InlineKeyboardButton(text="⏰ Время", callback_data="edit_field_time"))
    builder.add(InlineKeyboardButton(text="🌍 Часовой пояс", callback_data="edit_field_timezone"))
    builder.add(InlineKeyboardButton(text="📊 Статус", callback_data="edit_field_status"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_races_cancel"))
    builder.adjust(2, 2, 1, 1)
    
    status_text = "Завершена" if race.status == "finished" else "Предстоящая"
    await callback.message.edit_text(
        f"✏️ <b>Редактировать гонку</b>\n\n"
        f"Гонка: <b>{race.name}</b>\n"
        f"Дата: {race.date}\n"
        f"Время: {race.start_time} ({race.timezone})\n"
        f"Статус: {status_text}\n\n"
        "Что вы хотите изменить?",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_field_"), AdminFilter())
async def callback_edit_field_select(callback: CallbackQuery, state: FSMContext):
    """Select field to edit."""
    field = callback.data.split("_")[-1]
    await state.update_data(edit_field=field)
    await state.set_state(EditRaceStates.waiting_for_value)
    
    field_prompts = {
        "name": "Отправьте новое название гонки:",
        "date": "Отправьте новую дату в формате <b>YYYY-MM-DD</b>:",
        "time": "Отправьте новое время в формате <b>HH:MM</b>:",
        "timezone": "Отправьте новый часовой пояс (например, UTC, Europe/Moscow):",
        "status": "Отправьте новый статус (<b>upcoming</b> или <b>finished</b>):"
    }
    
    field_names = {
        "name": "Название",
        "date": "Дата",
        "time": "Время",
        "timezone": "Часовой пояс",
        "status": "Статус"
    }
    
    await callback.message.edit_text(
        f"✏️ <b>Редактировать {field_names.get(field, field.capitalize())}</b>\n\n"
        f"{field_prompts.get(field, 'Отправьте новое значение:')}",
        reply_markup=get_cancel_keyboard("admin_races_cancel")
    )
    await callback.answer()


@router.message(EditRaceStates.waiting_for_value, AdminFilter())
async def process_edit_value(message: Message, state: FSMContext):
    """Process edit value."""
    data = await state.get_data()
    race_id = data.get("race_id")
    field = data.get("edit_field")
    value = message.text.strip()
    
    race = await get_race_by_id(race_id)
    if not race:
        await message.answer("Гонка не найдена.", reply_markup=get_admin_races_menu())
        await state.clear()
        return
    
    # Validate based on field
    if field == "date":
        try:
            from datetime import datetime
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            await message.answer(
                "Я не понимаю эту дату. Пожалуйста, используйте формат <b>YYYY-MM-DD</b>",
                reply_markup=get_cancel_keyboard("admin_races_cancel")
            )
            return
    elif field == "time":
        try:
            from datetime import datetime
            datetime.strptime(value, "%H:%M")
        except ValueError:
            await message.answer(
                "Я не понимаю это время. Пожалуйста, используйте формат <b>HH:MM</b>",
                reply_markup=get_cancel_keyboard("admin_races_cancel")
            )
            return
    elif field == "status":
        if value.lower() not in ["upcoming", "finished"]:
            await message.answer(
                "Статус должен быть либо <b>upcoming</b>, либо <b>finished</b>",
                reply_markup=get_cancel_keyboard("admin_races_cancel")
            )
            return
        value = value.lower()
    
    # Update race
    update_data = {field: value}
    updated_race = await update_race(race_id, **update_data)
    
    if updated_race:
        status_text = "Завершена" if updated_race.status == "finished" else "Предстоящая"
        await message.answer(
            f"✅ <b>Гонка успешно обновлена!</b>\n\n"
            f"Название: <b>{updated_race.name}</b>\n"
            f"Дата: {updated_race.date}\n"
            f"Время: {updated_race.start_time} ({updated_race.timezone})\n"
            f"Статус: {status_text}",
            reply_markup=get_admin_races_menu()
        )
    else:
        await message.answer(
            "❌ Ошибка при обновлении гонки. Попробуйте снова.",
            reply_markup=get_admin_races_menu()
        )
    
    await state.clear()


# Delete race flow
@router.callback_query(F.data == "admin_races_delete", AdminFilter())
async def callback_delete_race_start(callback: CallbackQuery, state: FSMContext):
    """Start delete race flow."""
    races = await get_all_races()
    
    if not races:
        await callback.message.edit_text(
            "Гонки не найдены. Добавьте первую гонку!",
            reply_markup=get_admin_races_menu()
        )
        await callback.answer()
        return
    
    await state.set_state(DeleteRaceStates.waiting_for_race)
    await callback.message.edit_text(
        "🗑️ <b>Удалить гонку</b>\n\n"
        "⚠️ <b>Внимание:</b> Это удалит гонку и все связанные ставки!\n\n"
        "Выберите гонку для удаления:",
        reply_markup=get_race_list_keyboard(races, "delete_race")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_race_"), AdminFilter())
async def callback_delete_race_select(callback: CallbackQuery, state: FSMContext):
    """Select race to delete."""
    race_id = int(callback.data.split("_")[-1])
    race = await get_race_by_id(race_id)
    
    if not race:
        await callback.answer("Я не могу найти эту гонку. Проверьте ID.", show_alert=True)
        await callback.message.edit_text(
            "Гонка не найдена.",
            reply_markup=get_admin_races_menu()
        )
        await state.clear()
        return
    
    await state.update_data(race_id=race_id)
    await state.set_state(DeleteRaceStates.waiting_for_confirm)
    
    await callback.message.edit_text(
        f"🗑️ <b>Удалить гонку</b>\n\n"
        f"⚠️ <b>Внимание:</b> Это навсегда удалит:\n"
        f"• Гонку: <b>{race.name}</b>\n"
        f"• Дата: {race.date} в {race.start_time}\n"
        f"• Все ставки на эту гонку\n\n"
        f"Вы уверены?",
        reply_markup=get_confirm_keyboard(f"confirm_delete_{race_id}", "admin_races_cancel")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"), AdminFilter())
async def callback_delete_race_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirm race deletion."""
    race_id = int(callback.data.split("_")[-1])
    race = await get_race_by_id(race_id)
    
    if not race:
        await callback.answer("Гонка не найдена.", show_alert=True)
        await callback.message.edit_text(
            "Гонка не найдена.",
            reply_markup=get_admin_races_menu()
        )
        await state.clear()
        return
    
    success = await delete_race(race_id)
    
    if success:
        await callback.message.edit_text(
            f"✅ <b>Гонка успешно удалена!</b>\n\n"
            f"Удалена: <b>{race.name}</b>",
            reply_markup=get_admin_races_menu()
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при удалении гонки. Попробуйте снова.",
            reply_markup=get_admin_races_menu()
        )
    
    await state.clear()
    await callback.answer()


# Cancel handlers
@router.callback_query(F.data == "admin_races_cancel")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel current operation."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Операция отменена.",
        reply_markup=get_admin_races_menu()
    )
    await callback.answer()


# Enter results flow
@router.message(Command("results"), AdminFilter())
async def cmd_results(message: Message, state: FSMContext):
    """Handle /results command (F-007, C-008)."""
    races = await get_races_without_results()
    
    if not races:
        await message.answer(
            "🏁 <b>Ввести результаты гонки</b>\n\n"
            "Для всех гонок уже введены результаты. Добавьте новую гонку, чтобы ввести результаты."
        )
        return
    
    await state.set_state(EnterResultsStates.waiting_for_race)
    await message.answer(
        "🏁 <b>Ввести результаты гонки</b>\n\n"
        "Выберите гонку для ввода результатов:",
        reply_markup=get_race_list_keyboard(races, "result_race")
    )


@router.message(Command("results"), ~AdminFilter())
async def cmd_results_not_admin(message: Message):
    """Handle /results command for non-admins."""
    await message.answer("Вам не разрешено вводить результаты.")


@router.callback_query(F.data.startswith("result_race_"), AdminFilter())
async def callback_result_race_select(callback: CallbackQuery, state: FSMContext):
    """Select race for entering results."""
    race_id = int(callback.data.split("_")[-1])
    race = await get_race_by_id(race_id)
    
    if not race:
        await callback.answer("Гонка не найдена.", show_alert=True)
        await callback.message.edit_text("Гонка не найдена.")
        await state.clear()
        return
    
    # Check if result already exists
    existing_result = await get_result_by_race_id(race_id)
    if existing_result:
        await callback.message.edit_text(
            f"⚠️ <b>Результаты уже введены</b>\n\n"
            f"Гонка: <b>{race.name}</b>\n"
            f"Текущие результаты:\n"
            f"1️⃣ {existing_result.driver_1st}\n"
            f"2️⃣ {existing_result.driver_2nd}\n"
            f"3️⃣ {existing_result.driver_3rd}\n\n"
            "Хотите перезаписать?",
            reply_markup=get_confirm_keyboard(f"overwrite_result_{race_id}", "cancel_results")
        )
        await callback.answer()
        return
    
    await state.update_data(race_id=race_id)
    await state.set_state(EnterResultsStates.waiting_for_1st)
    await callback.answer()
    await show_result_driver_selection(callback, state, "1st")


@router.callback_query(F.data.startswith("overwrite_result_"), AdminFilter())
async def callback_overwrite_result(callback: CallbackQuery, state: FSMContext):
    """Confirm overwrite result."""
    race_id = int(callback.data.split("_")[-1])
    await state.update_data(race_id=race_id)
    await state.set_state(EnterResultsStates.waiting_for_1st)
    await show_result_driver_selection(callback, state, "1st")
    await callback.answer()


async def show_result_driver_selection(callback: CallbackQuery, state: FSMContext, position: str):
    """Show driver selection for results."""
    drivers = await get_all_drivers(active_only=True)
    data = await state.get_data()
    selected_drivers = []
    
    # Get already selected drivers to exclude them
    if position == "2nd":
        selected_drivers.append(data.get("driver_1st"))
    elif position == "3rd":
        selected_drivers.append(data.get("driver_1st"))
        selected_drivers.append(data.get("driver_2nd"))
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    for driver in drivers:
        if driver.code not in selected_drivers:
            builder.add(InlineKeyboardButton(
                text=f"{driver.code} - {driver.full_name}",
                callback_data=f"result_driver_{position}_{driver.code}"
            ))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_results"))
    builder.adjust(2)
    
    position_text = {
        "1st": "🥇 1-е место",
        "2nd": "🥈 2-е место",
        "3rd": "🥉 3-е место"
    }
    
    await callback.message.edit_text(
        f"🏁 <b>Ввести результаты гонки</b>\n\n"
        f"Выберите гонщика для {position_text[position]}:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("result_driver_1st_"), AdminFilter())
async def callback_result_driver_1st(callback: CallbackQuery, state: FSMContext):
    """Handle 1st place driver selection for results."""
    driver_code = callback.data.split("_")[-1]
    await state.update_data(driver_1st=driver_code)
    await state.set_state(EnterResultsStates.waiting_for_2nd)
    await callback.answer()
    await show_result_driver_selection(callback, state, "2nd")


@router.callback_query(F.data.startswith("result_driver_2nd_"), AdminFilter())
async def callback_result_driver_2nd(callback: CallbackQuery, state: FSMContext):
    """Handle 2nd place driver selection for results."""
    driver_code = callback.data.split("_")[-1]
    await state.update_data(driver_2nd=driver_code)
    await state.set_state(EnterResultsStates.waiting_for_3rd)
    await callback.answer()
    await show_result_driver_selection(callback, state, "3rd")


@router.callback_query(F.data.startswith("result_driver_3rd_"), AdminFilter())
async def callback_result_driver_3rd(callback: CallbackQuery, state: FSMContext):
    """Handle 3rd place driver selection for results."""
    driver_code = callback.data.split("_")[-1]
    await state.update_data(driver_3rd=driver_code)
    await state.set_state(EnterResultsStates.waiting_for_confirm)
    
    data = await state.get_data()
    race_id = data.get("race_id")
    race = await get_race_by_id(race_id)
    
    if not race:
        await callback.answer("Гонка не найдена.", show_alert=True)
        await state.clear()
        return
    
    driver_1st = await get_driver_by_code(data.get("driver_1st"))
    driver_2nd = await get_driver_by_code(data.get("driver_2nd"))
    driver_3rd = await get_driver_by_code(data.get("driver_3rd"))
    
    summary_text = (
        f"🏁 <b>Подтвердите результаты гонки</b>\n\n"
        f"Гонка: <b>{race.name}</b>\n"
        f"Дата: {race.date} в {race.start_time}\n\n"
        f"Результаты:\n"
        f"🥇 1-е: {driver_1st.code if driver_1st else data.get('driver_1st')} - {driver_1st.full_name if driver_1st else ''}\n"
        f"🥈 2-е: {driver_2nd.code if driver_2nd else data.get('driver_2nd')} - {driver_2nd.full_name if driver_2nd else ''}\n"
        f"🥉 3-е: {driver_3rd.code if driver_3rd else data.get('driver_3rd')} - {driver_3rd.full_name if driver_3rd else ''}\n\n"
        f"После подтверждения очки будут рассчитаны для всех ставок.\n\n"
        f"Подтвердить?"
    )
    
    await callback.message.edit_text(
        summary_text,
        reply_markup=get_confirm_keyboard("confirm_results", "cancel_results")
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_results", AdminFilter())
async def callback_confirm_results(callback: CallbackQuery, state: FSMContext):
    """Handle results confirmation and calculate points."""
    data = await state.get_data()
    race_id = data.get("race_id")
    driver_1st = data.get("driver_1st")
    driver_2nd = data.get("driver_2nd")
    driver_3rd = data.get("driver_3rd")
    
    race = await get_race_by_id(race_id)
    if not race:
        await callback.answer("Гонка не найдена.", show_alert=True)
        await state.clear()
        return
    
    try:
        # Save results
        result = await create_or_update_result(race_id, driver_1st, driver_2nd, driver_3rd)
        
        # Calculate and save points
        points_summary = await calculate_and_save_points(race_id, result)
        
        # Update race status to finished
        await update_race(race_id, status="finished")
        
        # Build summary message
        from services.driver_service import get_driver_by_code
        driver_1st_obj = await get_driver_by_code(driver_1st)
        driver_2nd_obj = await get_driver_by_code(driver_2nd)
        driver_3rd_obj = await get_driver_by_code(driver_3rd)
        
        summary_text = (
            f"✅ <b>Результаты сохранены!</b>\n\n"
            f"Гонка: <b>{race.name}</b>\n"
            f"Дата: {race.date}\n\n"
            f"Результаты:\n"
            f"🥇 1-е: {driver_1st_obj.code if driver_1st_obj else driver_1st} - {driver_1st_obj.full_name if driver_1st_obj else ''}\n"
            f"🥈 2-е: {driver_2nd_obj.code if driver_2nd_obj else driver_2nd} - {driver_2nd_obj.full_name if driver_2nd_obj else ''}\n"
            f"🥉 3-е: {driver_3rd_obj.code if driver_3rd_obj else driver_3rd} - {driver_3rd_obj.full_name if driver_3rd_obj else ''}\n\n"
        )
        
        if points_summary:
            # Sort by points descending
            points_summary.sort(key=lambda x: x['points'], reverse=True)
            summary_text += "📊 <b>Топ игроков:</b>\n\n"
            for i, entry in enumerate(points_summary[:5], 1):  # Top 5
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                summary_text += f"{medal} {entry['user_name']} – {entry['points']} очков\n"
        else:
            summary_text += "На эту гонку не было сделано ставок.\n"
        
        await callback.message.edit_text(summary_text)
        await callback.answer("Результаты сохранены и очки рассчитаны!")
        
    except Exception as e:
        await callback.answer(
            f"Не удалось рассчитать очки. Попробуйте позже или свяжитесь с администратором.",
            show_alert=True
        )
        await callback.message.edit_text(
            f"❌ Ошибка при сохранении результатов: {str(e)}\n\n"
            "Попробуйте снова."
        )
    
    await state.clear()


@router.callback_query(F.data == "cancel_results")
async def callback_cancel_results(callback: CallbackQuery, state: FSMContext):
    """Handle results cancellation."""
    await state.clear()
    await callback.message.edit_text("❌ Ввод результатов отменен.")
    await callback.answer()


# User management (whitelist)
@router.message(Command("admin_users"), AdminFilter())
async def cmd_admin_users(message: Message):
    """Handle /admin_users command for managing user whitelist."""
    try:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        
        users = await get_all_users()
        
        if not users:
            await message.answer(
                "👥 <b>Управление пользователями</b>\n\n"
                "Пользователи не найдены."
            )
            return
        
        # Separate allowed and not allowed users
        # Handle case where is_allowed field might not exist in old database
        allowed_users = []
        not_allowed_users = []
        
        for user in users:
            try:
                # Check if is_allowed attribute exists
                is_allowed = getattr(user, 'is_allowed', None)
                if is_allowed is None:
                    # Field doesn't exist - assume all existing users are allowed for backward compatibility
                    is_allowed = True
                
                if is_allowed:
                    allowed_users.append(user)
                else:
                    not_allowed_users.append(user)
            except AttributeError:
                # If is_allowed doesn't exist, treat as allowed for backward compatibility
                allowed_users.append(user)
        
        text = "👥 <b>Управление пользователями</b>\n\n"
        
        if allowed_users:
            text += "✅ <b>Разрешенные пользователи:</b>\n"
            for user in allowed_users:
                name = user.full_name or user.username or f"User {user.telegram_id}"
                username_str = f" @{user.username}" if user.username else ""
                admin_mark = " (админ)" if user.is_admin else ""
                text += f"• {name}{username_str} (ID: {user.telegram_id}){admin_mark}\n"
            text += "\n"
        
        if not_allowed_users:
            text += "❌ <b>Ожидающие доступа:</b>\n"
            for user in not_allowed_users:
                name = user.full_name or user.username or f"User {user.telegram_id}"
                username_str = f" @{user.username}" if user.username else ""
                text += f"• {name}{username_str} (ID: {user.telegram_id})\n"
            text += "\n"
        
        text += "Используйте команды:\n"
        text += "• /allow_user <ID или @username> - разрешить доступ\n"
        text += "• /deny_user <ID или @username> - запретить доступ\n"
        text += "• /user_info <ID или @username> - информация о пользователе\n\n"
        text += "Примеры:\n"
        text += "• /allow_user 123456789\n"
        text += "• /allow_user @username"
        
        await message.answer(text)
    except Exception as e:
        import traceback
        error_msg = f"❌ Ошибка при получении списка пользователей: {str(e)}\n\n"
        error_msg += "Проверьте логи бота для деталей."
        await message.answer(error_msg)
        # Log the full error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in cmd_admin_users: {traceback.format_exc()}")


@router.message(Command("allow_user"), AdminFilter())
async def cmd_allow_user(message: Message):
    """Allow user access by Telegram ID or username."""
    from services.user_service import get_user_by_username
    
    try:
        # Get user identifier from command arguments
        args = message.text.split()[1:] if message.text else []
        if not args:
            await message.answer(
                "❌ <b>Использование:</b> /allow_user <ID или @username>\n\n"
                "Примеры:\n"
                "• /allow_user 123456789\n"
                "• /allow_user @username"
            )
            return
        
        identifier = args[0].strip()
        user = None
        
        # Try to find user by ID or username
        if identifier.startswith('@'):
            # Search by username
            user = await get_user_by_username(identifier)
        elif identifier.isdigit():
            # Search by ID
            user = await get_user_by_telegram_id(int(identifier))
        else:
            # Try as username without @
            user = await get_user_by_username(identifier)
        
        if not user:
            await message.answer(
                f"❌ Пользователь '{identifier}' не найден.\n"
                "Пользователь должен сначала написать боту /start."
            )
            return
        
        if user.is_allowed:
            name = user.full_name or user.username or f"User {user.telegram_id}"
            username_str = f" @{user.username}" if user.username else ""
            await message.answer(
                f"ℹ️ Пользователь {name}{username_str} уже имеет доступ."
            )
            return
        
        # Allow user
        success = await set_user_allowed(user.telegram_id, True)
        if success:
            name = user.full_name or user.username or f"User {user.telegram_id}"
            username_str = f" @{user.username}" if user.username else ""
            await message.answer(
                f"✅ <b>Доступ разрешен!</b>\n\n"
                f"Пользователь: {name}{username_str}\n"
                f"ID: {user.telegram_id}\n\n"
                f"Теперь пользователь может использовать бота."
            )
        else:
            await message.answer("❌ Ошибка при изменении доступа.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("deny_user"), AdminFilter())
async def cmd_deny_user(message: Message):
    """Deny user access by Telegram ID or username."""
    from services.user_service import get_user_by_username
    
    try:
        # Get user identifier from command arguments
        args = message.text.split()[1:] if message.text else []
        if not args:
            await message.answer(
                "❌ <b>Использование:</b> /deny_user <ID или @username>\n\n"
                "Примеры:\n"
                "• /deny_user 123456789\n"
                "• /deny_user @username"
            )
            return
        
        identifier = args[0].strip()
        user = None
        
        # Try to find user by ID or username
        if identifier.startswith('@'):
            # Search by username
            user = await get_user_by_username(identifier)
        elif identifier.isdigit():
            # Search by ID
            user = await get_user_by_telegram_id(int(identifier))
        else:
            # Try as username without @
            user = await get_user_by_username(identifier)
        
        if not user:
            await message.answer(
                f"❌ Пользователь '{identifier}' не найден."
            )
            return
        
        # Check if user is admin (can't deny admin access)
        from config import is_admin
        if is_admin(user.telegram_id):
            await message.answer(
                "❌ Нельзя запретить доступ администратору."
            )
            return
        
        if not user.is_allowed:
            name = user.full_name or user.username or f"User {user.telegram_id}"
            username_str = f" @{user.username}" if user.username else ""
            await message.answer(
                f"ℹ️ Пользователь {name}{username_str} уже не имеет доступа."
            )
            return
        
        # Deny user
        success = await set_user_allowed(user.telegram_id, False)
        if success:
            name = user.full_name or user.username or f"User {user.telegram_id}"
            username_str = f" @{user.username}" if user.username else ""
            await message.answer(
                f"❌ <b>Доступ запрещен</b>\n\n"
                f"Пользователь: {name}{username_str}\n"
                f"ID: {user.telegram_id}\n\n"
                f"Пользователь больше не может использовать бота."
            )
        else:
            await message.answer("❌ Ошибка при изменении доступа.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("user_info"), AdminFilter())
async def cmd_user_info(message: Message):
    """Get user information by Telegram ID or username."""
    from services.user_service import get_user_by_username
    
    try:
        # Get user identifier from command arguments
        args = message.text.split()[1:] if message.text else []
        if not args:
            await message.answer(
                "❌ <b>Использование:</b> /user_info <ID или @username>\n\n"
                "Примеры:\n"
                "• /user_info 123456789\n"
                "• /user_info @username"
            )
            return
        
        identifier = args[0].strip()
        user = None
        
        # Try to find user by ID or username
        if identifier.startswith('@'):
            # Search by username
            user = await get_user_by_username(identifier)
        elif identifier.isdigit():
            # Search by ID
            user = await get_user_by_telegram_id(int(identifier))
        else:
            # Try as username without @
            user = await get_user_by_username(identifier)
        
        if not user:
            await message.answer(
                f"❌ Пользователь '{identifier}' не найден."
            )
            return
        
        from services.bet_service import get_user_bets
        bets = await get_user_bets(user.id)
        
        text = (
            f"👤 <b>Информация о пользователе</b>\n\n"
            f"ID: {user.telegram_id}\n"
            f"Имя: {user.full_name or 'Не указано'}\n"
            f"Username: @{user.username or 'Не указано'}\n"
            f"Админ: {'✅ Да' if user.is_admin else '❌ Нет'}\n"
            f"Доступ: {'✅ Разрешен' if user.is_allowed else '❌ Запрещен'}\n"
            f"Ставок: {len(bets)}\n"
            f"Зарегистрирован: {user.created_at.strftime('%Y-%m-%d %H:%M') if user.created_at else 'Неизвестно'}\n"
        )
        
        await message.answer(text)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

