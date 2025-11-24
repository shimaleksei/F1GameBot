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
        "🏁 <b>Race Management</b>\n\n"
        "Choose an action:",
        reply_markup=get_admin_races_menu()
    )


@router.message(Command("admin_races"))
async def cmd_admin_races_not_admin(message: Message):
    """Handle /admin_races command for non-admins."""
    await message.answer("You are not allowed to use this command.")


# View races
@router.callback_query(F.data == "admin_races_view", AdminFilter())
async def callback_view_races(callback: CallbackQuery):
    """View all races."""
    races = await get_all_races()
    
    if not races:
        await callback.message.edit_text(
            "📋 <b>All Races</b>\n\n"
            "No races found. Add your first race!",
            reply_markup=get_admin_races_menu()
        )
        await callback.answer()
        return
    
    text = "📋 <b>All Races</b>\n\n"
    for race in races:
        status_emoji = "✅" if race.status == "finished" else "🏁"
        text += f"{status_emoji} <b>{race.name}</b>\n"
        text += f"   📅 {race.date} at {race.start_time} ({race.timezone})\n"
        text += f"   Status: {race.status}\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_admin_races_menu())
    await callback.answer()


# Add race flow
@router.callback_query(F.data == "admin_races_add", AdminFilter())
async def callback_add_race_start(callback: CallbackQuery, state: FSMContext):
    """Start add race flow."""
    await state.set_state(AddRaceStates.waiting_for_name)
    await callback.message.edit_text(
        "➕ <b>Add New Race</b>\n\n"
        "Please send the race name (e.g., 'Bahrain Grand Prix'):",
        reply_markup=get_cancel_keyboard("admin_races_cancel")
    )
    await callback.answer()


@router.message(AddRaceStates.waiting_for_name, AdminFilter())
async def process_race_name(message: Message, state: FSMContext):
    """Process race name."""
    race_name = message.text.strip()
    if not race_name:
        await message.answer("Please send a valid race name:")
        return
    
    await state.update_data(race_name=race_name)
    await state.set_state(AddRaceStates.waiting_for_date)
    await message.answer(
        f"Race name: <b>{race_name}</b>\n\n"
        "Now send the race date in format <b>YYYY-MM-DD</b>\n"
        "Example: 2025-03-02",
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
            "I don't understand this date. Please use the format <b>YYYY-MM-DD</b>\n"
            "Example: 2025-03-02",
            reply_markup=get_cancel_keyboard("admin_races_cancel")
        )
        return
    
    await state.update_data(race_date=date_str)
    await state.set_state(AddRaceStates.waiting_for_time)
    await message.answer(
        f"Date: <b>{date_str}</b>\n\n"
        "Now send the race start time in format <b>HH:MM</b> (24-hour format)\n"
        "Example: 16:00",
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
            "I don't understand this time. Please use the format <b>HH:MM</b> (24-hour format)\n"
            "Example: 16:00",
            reply_markup=get_cancel_keyboard("admin_races_cancel")
        )
        return
    
    data = await state.get_data()
    race_name = data.get("race_name")
    race_date = data.get("race_date")
    
    # Create race
    try:
        race = await create_race(race_name, race_date, time_str, DEFAULT_TIMEZONE)
        await message.answer(
            f"✅ <b>Race added successfully!</b>\n\n"
            f"Name: <b>{race.name}</b>\n"
            f"Date: {race.date}\n"
            f"Time: {race.start_time} ({race.timezone})\n"
            f"Status: {race.status}",
            reply_markup=get_admin_races_menu()
        )
    except Exception as e:
        await message.answer(
            f"❌ Error creating race: {str(e)}\n\n"
            "Please try again.",
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
            "No races found. Add your first race!",
            reply_markup=get_admin_races_menu()
        )
        await callback.answer()
        return
    
    await state.set_state(EditRaceStates.waiting_for_race)
    await callback.message.edit_text(
        "✏️ <b>Edit Race</b>\n\n"
        "Select a race to edit:",
        reply_markup=get_race_list_keyboard(races, "edit_race")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_race_"), AdminFilter())
async def callback_edit_race_select(callback: CallbackQuery, state: FSMContext):
    """Select race to edit."""
    race_id = int(callback.data.split("_")[-1])
    race = await get_race_by_id(race_id)
    
    if not race:
        await callback.answer("I cannot find this race. Please check the ID.", show_alert=True)
        await callback.message.edit_text(
            "Race not found.",
            reply_markup=get_admin_races_menu()
        )
        await state.clear()
        return
    
    await state.update_data(race_id=race_id)
    await state.set_state(EditRaceStates.waiting_for_field)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📝 Name", callback_data="edit_field_name"))
    builder.add(InlineKeyboardButton(text="📅 Date", callback_data="edit_field_date"))
    builder.add(InlineKeyboardButton(text="⏰ Time", callback_data="edit_field_time"))
    builder.add(InlineKeyboardButton(text="🌍 Timezone", callback_data="edit_field_timezone"))
    builder.add(InlineKeyboardButton(text="📊 Status", callback_data="edit_field_status"))
    builder.add(InlineKeyboardButton(text="❌ Cancel", callback_data="admin_races_cancel"))
    builder.adjust(2, 2, 1, 1)
    
    await callback.message.edit_text(
        f"✏️ <b>Edit Race</b>\n\n"
        f"Race: <b>{race.name}</b>\n"
        f"Date: {race.date}\n"
        f"Time: {race.start_time} ({race.timezone})\n"
        f"Status: {race.status}\n\n"
        "What would you like to edit?",
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
        "name": "Send the new race name:",
        "date": "Send the new date in format <b>YYYY-MM-DD</b>:",
        "time": "Send the new time in format <b>HH:MM</b>:",
        "timezone": "Send the new timezone (e.g., UTC, Europe/Moscow):",
        "status": "Send the new status (<b>upcoming</b> or <b>finished</b>):"
    }
    
    await callback.message.edit_text(
        f"✏️ <b>Edit {field.capitalize()}</b>\n\n"
        f"{field_prompts.get(field, 'Send the new value:')}",
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
        await message.answer("Race not found.", reply_markup=get_admin_races_menu())
        await state.clear()
        return
    
    # Validate based on field
    if field == "date":
        try:
            from datetime import datetime
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            await message.answer(
                "I don't understand this date. Please use the format <b>YYYY-MM-DD</b>",
                reply_markup=get_cancel_keyboard("admin_races_cancel")
            )
            return
    elif field == "time":
        try:
            from datetime import datetime
            datetime.strptime(value, "%H:%M")
        except ValueError:
            await message.answer(
                "I don't understand this time. Please use the format <b>HH:MM</b>",
                reply_markup=get_cancel_keyboard("admin_races_cancel")
            )
            return
    elif field == "status":
        if value.lower() not in ["upcoming", "finished"]:
            await message.answer(
                "Status must be either <b>upcoming</b> or <b>finished</b>",
                reply_markup=get_cancel_keyboard("admin_races_cancel")
            )
            return
        value = value.lower()
    
    # Update race
    update_data = {field: value}
    updated_race = await update_race(race_id, **update_data)
    
    if updated_race:
        await message.answer(
            f"✅ <b>Race updated successfully!</b>\n\n"
            f"Name: <b>{updated_race.name}</b>\n"
            f"Date: {updated_race.date}\n"
            f"Time: {updated_race.start_time} ({updated_race.timezone})\n"
            f"Status: {updated_race.status}",
            reply_markup=get_admin_races_menu()
        )
    else:
        await message.answer(
            "❌ Error updating race. Please try again.",
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
            "No races found. Add your first race!",
            reply_markup=get_admin_races_menu()
        )
        await callback.answer()
        return
    
    await state.set_state(DeleteRaceStates.waiting_for_race)
    await callback.message.edit_text(
        "🗑️ <b>Delete Race</b>\n\n"
        "⚠️ <b>Warning:</b> This will delete the race and all associated bets!\n\n"
        "Select a race to delete:",
        reply_markup=get_race_list_keyboard(races, "delete_race")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_race_"), AdminFilter())
async def callback_delete_race_select(callback: CallbackQuery, state: FSMContext):
    """Select race to delete."""
    race_id = int(callback.data.split("_")[-1])
    race = await get_race_by_id(race_id)
    
    if not race:
        await callback.answer("I cannot find this race. Please check the ID.", show_alert=True)
        await callback.message.edit_text(
            "Race not found.",
            reply_markup=get_admin_races_menu()
        )
        await state.clear()
        return
    
    await state.update_data(race_id=race_id)
    await state.set_state(DeleteRaceStates.waiting_for_confirm)
    
    await callback.message.edit_text(
        f"🗑️ <b>Delete Race</b>\n\n"
        f"⚠️ <b>Warning:</b> This will permanently delete:\n"
        f"• Race: <b>{race.name}</b>\n"
        f"• Date: {race.date} at {race.start_time}\n"
        f"• All bets for this race\n\n"
        f"Are you sure?",
        reply_markup=get_confirm_keyboard(f"confirm_delete_{race_id}", "admin_races_cancel")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"), AdminFilter())
async def callback_delete_race_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirm race deletion."""
    race_id = int(callback.data.split("_")[-1])
    race = await get_race_by_id(race_id)
    
    if not race:
        await callback.answer("Race not found.", show_alert=True)
        await callback.message.edit_text(
            "Race not found.",
            reply_markup=get_admin_races_menu()
        )
        await state.clear()
        return
    
    success = await delete_race(race_id)
    
    if success:
        await callback.message.edit_text(
            f"✅ <b>Race deleted successfully!</b>\n\n"
            f"Deleted: <b>{race.name}</b>",
            reply_markup=get_admin_races_menu()
        )
    else:
        await callback.message.edit_text(
            "❌ Error deleting race. Please try again.",
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
        "❌ Operation cancelled.",
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
            "🏁 <b>Enter Race Results</b>\n\n"
            "All races have results entered. Add a new race to enter results."
        )
        return
    
    await state.set_state(EnterResultsStates.waiting_for_race)
    await message.answer(
        "🏁 <b>Enter Race Results</b>\n\n"
        "Select a race to enter results:",
        reply_markup=get_race_list_keyboard(races, "result_race")
    )


@router.message(Command("results"))
async def cmd_results_not_admin(message: Message):
    """Handle /results command for non-admins."""
    await message.answer("You are not allowed to set results.")


@router.callback_query(F.data.startswith("result_race_"), AdminFilter())
async def callback_result_race_select(callback: CallbackQuery, state: FSMContext):
    """Select race for entering results."""
    race_id = int(callback.data.split("_")[-1])
    race = await get_race_by_id(race_id)
    
    if not race:
        await callback.answer("Race not found.", show_alert=True)
        await callback.message.edit_text("Race not found.")
        await state.clear()
        return
    
    # Check if result already exists
    existing_result = await get_result_by_race_id(race_id)
    if existing_result:
        await callback.message.edit_text(
            f"⚠️ <b>Results Already Set</b>\n\n"
            f"Race: <b>{race.name}</b>\n"
            f"Current results:\n"
            f"1️⃣ {existing_result.driver_1st}\n"
            f"2️⃣ {existing_result.driver_2nd}\n"
            f"3️⃣ {existing_result.driver_3rd}\n\n"
            "Do you want to overwrite?",
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
    builder.add(InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_results"))
    builder.adjust(2)
    
    position_text = {
        "1st": "🥇 1st place",
        "2nd": "🥈 2nd place",
        "3rd": "🥉 3rd place"
    }
    
    await callback.message.edit_text(
        f"🏁 <b>Enter Race Results</b>\n\n"
        f"Select driver for {position_text[position]}:",
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
        await callback.answer("Race not found.", show_alert=True)
        await state.clear()
        return
    
    driver_1st = await get_driver_by_code(data.get("driver_1st"))
    driver_2nd = await get_driver_by_code(data.get("driver_2nd"))
    driver_3rd = await get_driver_by_code(data.get("driver_3rd"))
    
    summary_text = (
        f"🏁 <b>Confirm Race Results</b>\n\n"
        f"Race: <b>{race.name}</b>\n"
        f"Date: {race.date} at {race.start_time}\n\n"
        f"Results:\n"
        f"🥇 1st: {driver_1st.code if driver_1st else data.get('driver_1st')} - {driver_1st.full_name if driver_1st else ''}\n"
        f"🥈 2nd: {driver_2nd.code if driver_2nd else data.get('driver_2nd')} - {driver_2nd.full_name if driver_2nd else ''}\n"
        f"🥉 3rd: {driver_3rd.code if driver_3rd else data.get('driver_3rd')} - {driver_3rd.full_name if driver_3rd else ''}\n\n"
        f"After confirmation, points will be calculated for all bets.\n\n"
        f"Confirm?"
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
        await callback.answer("Race not found.", show_alert=True)
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
            f"✅ <b>Results Saved!</b>\n\n"
            f"Race: <b>{race.name}</b>\n"
            f"Date: {race.date}\n\n"
            f"Results:\n"
            f"🥇 1st: {driver_1st_obj.code if driver_1st_obj else driver_1st} - {driver_1st_obj.full_name if driver_1st_obj else ''}\n"
            f"🥈 2nd: {driver_2nd_obj.code if driver_2nd_obj else driver_2nd} - {driver_2nd_obj.full_name if driver_2nd_obj else ''}\n"
            f"🥉 3rd: {driver_3rd_obj.code if driver_3rd_obj else driver_3rd} - {driver_3rd_obj.full_name if driver_3rd_obj else ''}\n\n"
        )
        
        if points_summary:
            # Sort by points descending
            points_summary.sort(key=lambda x: x['points'], reverse=True)
            summary_text += "📊 <b>Top Scorers:</b>\n\n"
            for i, entry in enumerate(points_summary[:5], 1):  # Top 5
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                summary_text += f"{medal} {entry['user_name']} – {entry['points']} points\n"
        else:
            summary_text += "No bets were placed for this race.\n"
        
        await callback.message.edit_text(summary_text)
        await callback.answer("Results saved and points calculated!")
        
    except Exception as e:
        await callback.answer(
            f"I could not calculate scores. Please try again later or contact the admin.",
            show_alert=True
        )
        await callback.message.edit_text(
            f"❌ Error saving results: {str(e)}\n\n"
            "Please try again."
        )
    
    await state.clear()


@router.callback_query(F.data == "cancel_results")
async def callback_cancel_results(callback: CallbackQuery, state: FSMContext):
    """Handle results cancellation."""
    await state.clear()
    await callback.message.edit_text("❌ Results entry cancelled.")
    await callback.answer()

