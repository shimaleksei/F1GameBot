"""User handlers for F1 Game Bot."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.user_service import get_or_create_user, get_user_by_telegram_id
from services.race_service import get_upcoming_races, get_race_by_id
from services.driver_service import get_all_drivers
from services.bet_service import get_bet, create_or_update_bet, is_betting_open
from utils.keyboards import get_cancel_keyboard
from config import is_admin

router = Router()


# FSM States for betting
class BetStates(StatesGroup):
    waiting_for_race = State()
    waiting_for_1st = State()
    waiting_for_2nd = State()
    waiting_for_3rd = State()
    waiting_for_confirm = State()


@router.message(Command("start", "help"))
async def cmd_start_help(message: Message):
    """Handle /start and /help commands (F-001, C-001)."""
    try:
        # Register or update user
        user = await get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name or message.from_user.first_name,
        )
        
        # Welcome message
        welcome_text = (
            "Hi! I'm an F1 betting bot. I help you place virtual bets on the top 3 drivers for each race.\n\n"
            "📋 Main commands:\n"
            "• /bet – place or change a bet\n"
            "• /my_bets – see your current bets\n"
            "• /leaderboard – see top players\n"
            "• /me – see your points\n"
        )
        
        # Add admin commands if user is admin
        if is_admin(message.from_user.id):
            welcome_text += (
                "\n🔧 Admin commands:\n"
                "• /admin_races – manage races\n"
                "• /upload_races – upload race calendar\n"
                "• /results – enter race results\n"
            )
        
        await message.answer(welcome_text)
        
    except Exception as e:
        await message.answer(
            "Sorry, something went wrong. Please try again with /start."
        )


@router.message(Command("bet"))
async def cmd_bet(message: Message, state: FSMContext):
    """Handle /bet command (F-005, C-002)."""
    try:
        # Register or update user
        user = await get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name or message.from_user.first_name,
        )
        
        # Get upcoming races
        races = await get_upcoming_races()
        
        # Filter races where betting is still open
        open_races = []
        for race in races:
            if is_betting_open(race.date, race.start_time, race.timezone):
                open_races.append(race)
        
        if not open_races:
            await message.answer(
                "🏁 <b>Place a Bet</b>\n\n"
                "There are no races open for betting at the moment.\n"
                "Check back later or ask an admin to add races."
            )
            return
        
        # If only one race, go directly to driver selection
        if len(open_races) == 1:
            race = open_races[0]
            # Check if user already has a bet
            existing_bet = await get_bet(user.id, race.id)
            if existing_bet:
                await message.answer(
                    f"🏁 <b>Place a Bet</b>\n\n"
                    f"You already have a bet for <b>{race.name}</b>:\n"
                    f"1️⃣ {existing_bet.driver_1st}\n"
                    f"2️⃣ {existing_bet.driver_2nd}\n"
                    f"3️⃣ {existing_bet.driver_3rd}\n\n"
                    "Do you want to replace it?",
                    reply_markup=get_cancel_keyboard("cancel_bet")
                )
                await state.update_data(race_id=race.id, existing_bet=True)
                await state.set_state(BetStates.waiting_for_1st)
            else:
                await state.update_data(race_id=race.id, existing_bet=False)
                await state.set_state(BetStates.waiting_for_1st)
                await show_driver_selection(message, state, "1st")
        else:
            # Show race selection
            await state.set_state(BetStates.waiting_for_race)
            builder = InlineKeyboardBuilder()
            for race in open_races:
                builder.add(InlineKeyboardButton(
                    text=f"🏁 {race.name} ({race.date})",
                    callback_data=f"bet_race_{race.id}"
                ))
            builder.add(InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_bet"))
            builder.adjust(1)
            
            await message.answer(
                "🏁 <b>Place a Bet</b>\n\n"
                "Select a race:",
                reply_markup=builder.as_markup()
            )
    
    except Exception as e:
        await message.answer(
            "I cannot load the race list. Please try again later."
        )


@router.callback_query(F.data.startswith("bet_race_"))
async def callback_bet_race_select(callback: CallbackQuery, state: FSMContext):
    """Handle race selection for betting."""
    race_id = int(callback.data.split("_")[-1])
    race = await get_race_by_id(race_id)
    
    if not race:
        await callback.answer("Race not found.", show_alert=True)
        await callback.message.edit_text("Race not found.")
        await state.clear()
        return
    
    # Check if betting is still open
    if not is_betting_open(race.date, race.start_time, race.timezone):
        await callback.answer("Betting for this race is closed.", show_alert=True)
        await callback.message.edit_text(
            "❌ Betting for this race is closed."
        )
        await state.clear()
        return
    
    # Get user
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("User not found.", show_alert=True)
        await state.clear()
        return
    
    # Check if user already has a bet
    existing_bet = await get_bet(user.id, race.id)
    if existing_bet:
        await callback.message.edit_text(
            f"🏁 <b>Place a Bet</b>\n\n"
            f"You already have a bet for <b>{race.name}</b>:\n"
            f"1️⃣ {existing_bet.driver_1st}\n"
            f"2️⃣ {existing_bet.driver_2nd}\n"
            f"3️⃣ {existing_bet.driver_3rd}\n\n"
            "Do you want to replace it?",
            reply_markup=get_cancel_keyboard("cancel_bet")
        )
        await state.update_data(race_id=race.id, existing_bet=True)
    else:
        await state.update_data(race_id=race.id, existing_bet=False)
    
    await state.set_state(BetStates.waiting_for_1st)
    await callback.answer()
    await show_driver_selection_callback(callback, state, "1st")


async def show_driver_selection(message: Message, state: FSMContext, position: str):
    """Show driver selection keyboard."""
    drivers = await get_all_drivers(active_only=True)
    data = await state.get_data()
    selected_drivers = []
    
    # Get already selected drivers to exclude them
    if position == "2nd":
        selected_drivers.append(data.get("driver_1st"))
    elif position == "3rd":
        selected_drivers.append(data.get("driver_1st"))
        selected_drivers.append(data.get("driver_2nd"))
    
    builder = InlineKeyboardBuilder()
    for driver in drivers:
        if driver.code not in selected_drivers:
            builder.add(InlineKeyboardButton(
                text=f"{driver.code} - {driver.full_name}",
                callback_data=f"bet_driver_{position}_{driver.code}"
            ))
    builder.add(InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_bet"))
    builder.adjust(2)
    
    position_text = {
        "1st": "🥇 1st place",
        "2nd": "🥈 2nd place",
        "3rd": "🥉 3rd place"
    }
    
    await message.answer(
        f"🏁 <b>Place a Bet</b>\n\n"
        f"Select driver for {position_text[position]}:",
        reply_markup=builder.as_markup()
    )


async def show_driver_selection_callback(callback: CallbackQuery, state: FSMContext, position: str):
    """Show driver selection keyboard (callback version)."""
    drivers = await get_all_drivers(active_only=True)
    data = await state.get_data()
    selected_drivers = []
    
    # Get already selected drivers to exclude them
    if position == "2nd":
        selected_drivers.append(data.get("driver_1st"))
    elif position == "3rd":
        selected_drivers.append(data.get("driver_1st"))
        selected_drivers.append(data.get("driver_2nd"))
    
    builder = InlineKeyboardBuilder()
    for driver in drivers:
        if driver.code not in selected_drivers:
            builder.add(InlineKeyboardButton(
                text=f"{driver.code} - {driver.full_name}",
                callback_data=f"bet_driver_{position}_{driver.code}"
            ))
    builder.add(InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_bet"))
    builder.adjust(2)
    
    position_text = {
        "1st": "🥇 1st place",
        "2nd": "🥈 2nd place",
        "3rd": "🥉 3rd place"
    }
    
    await callback.message.edit_text(
        f"🏁 <b>Place a Bet</b>\n\n"
        f"Select driver for {position_text[position]}:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("bet_driver_1st_"))
async def callback_bet_driver_1st(callback: CallbackQuery, state: FSMContext):
    """Handle 1st place driver selection."""
    driver_code = callback.data.split("_")[-1]
    await state.update_data(driver_1st=driver_code)
    await state.set_state(BetStates.waiting_for_2nd)
    await callback.answer()
    await show_driver_selection_callback(callback, state, "2nd")


@router.callback_query(F.data.startswith("bet_driver_2nd_"))
async def callback_bet_driver_2nd(callback: CallbackQuery, state: FSMContext):
    """Handle 2nd place driver selection."""
    driver_code = callback.data.split("_")[-1]
    await state.update_data(driver_2nd=driver_code)
    await state.set_state(BetStates.waiting_for_3rd)
    await callback.answer()
    await show_driver_selection_callback(callback, state, "3rd")


@router.callback_query(F.data.startswith("bet_driver_3rd_"))
async def callback_bet_driver_3rd(callback: CallbackQuery, state: FSMContext):
    """Handle 3rd place driver selection."""
    driver_code = callback.data.split("_")[-1]
    await state.update_data(driver_3rd=driver_code)
    await state.set_state(BetStates.waiting_for_confirm)
    
    data = await state.get_data()
    race_id = data.get("race_id")
    race = await get_race_by_id(race_id)
    
    if not race:
        await callback.answer("Race not found.", show_alert=True)
        await state.clear()
        return
    
    from services.driver_service import get_driver_by_code
    driver_1st = await get_driver_by_code(data.get("driver_1st"))
    driver_2nd = await get_driver_by_code(data.get("driver_2nd"))
    driver_3rd = await get_driver_by_code(data.get("driver_3rd"))
    
    summary_text = (
        f"🏁 <b>Confirm Your Bet</b>\n\n"
        f"Race: <b>{race.name}</b>\n"
        f"Date: {race.date} at {race.start_time}\n\n"
        f"Your bet:\n"
        f"🥇 1st: {driver_1st.code if driver_1st else data.get('driver_1st')} - {driver_1st.full_name if driver_1st else ''}\n"
        f"🥈 2nd: {driver_2nd.code if driver_2nd else data.get('driver_2nd')} - {driver_2nd.full_name if driver_2nd else ''}\n"
        f"🥉 3rd: {driver_3rd.code if driver_3rd else data.get('driver_3rd')} - {driver_3rd.full_name if driver_3rd else ''}\n\n"
        f"Confirm?"
    )
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Confirm", callback_data="bet_confirm"))
    builder.add(InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_bet"))
    builder.adjust(2)
    
    await callback.message.edit_text(summary_text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "bet_confirm")
async def callback_bet_confirm(callback: CallbackQuery, state: FSMContext):
    """Handle bet confirmation."""
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
    
    # Check if betting is still open
    if not is_betting_open(race.date, race.start_time, race.timezone):
        await callback.answer("Betting for this race is closed.", show_alert=True)
        await callback.message.edit_text(
            "❌ Betting for this race is closed."
        )
        await state.clear()
        return
    
    # Get user
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("User not found.", show_alert=True)
        await state.clear()
        return
    
    # Create or update bet
    try:
        bet = await create_or_update_bet(user.id, race_id, driver_1st, driver_2nd, driver_3rd)
        
        from services.driver_service import get_driver_by_code
        driver_1st_obj = await get_driver_by_code(driver_1st)
        driver_2nd_obj = await get_driver_by_code(driver_2nd)
        driver_3rd_obj = await get_driver_by_code(driver_3rd)
        
        existing = data.get("existing_bet", False)
        message_text = (
            f"{'✅ Bet updated!' if existing else '✅ Bet placed!'}\n\n"
            f"Race: <b>{race.name}</b>\n"
            f"Date: {race.date} at {race.start_time}\n\n"
            f"Your bet:\n"
            f"🥇 1st: {driver_1st_obj.code if driver_1st_obj else driver_1st} - {driver_1st_obj.full_name if driver_1st_obj else ''}\n"
            f"🥈 2nd: {driver_2nd_obj.code if driver_2nd_obj else driver_2nd} - {driver_2nd_obj.full_name if driver_2nd_obj else ''}\n"
            f"🥉 3rd: {driver_3rd_obj.code if driver_3rd_obj else driver_3rd} - {driver_3rd_obj.full_name if driver_3rd_obj else ''}\n\n"
            f"Good luck! 🍀"
        )
        
        await callback.message.edit_text(message_text)
        await callback.answer("Bet saved!")
    except Exception as e:
        await callback.answer("Error saving bet. Please try again.", show_alert=True)
        await callback.message.edit_text(
            "❌ Error saving bet. Please try again."
        )
    
    await state.clear()


@router.callback_query(F.data == "cancel_bet")
async def callback_cancel_bet(callback: CallbackQuery, state: FSMContext):
    """Handle bet cancellation."""
    await state.clear()
    await callback.message.edit_text("❌ Bet cancelled.")
    await callback.answer()


@router.message(Command("my_bets"))
async def cmd_my_bets(message: Message):
    """Handle /my_bets command (F-006, C-003)."""
    try:
        # Register or update user
        user = await get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name or message.from_user.first_name,
        )
        
        # Get user bets
        from services.bet_service import get_user_bets
        bets = await get_user_bets(user.id)
        
        if not bets:
            await message.answer(
                "📋 <b>My Bets</b>\n\n"
                "You don't have any bets yet.\n"
                "Use /bet to place your first bet!"
            )
            return
        
        # Get upcoming races with bets
        from services.race_service import get_race_by_id
        from services.bet_service import is_betting_open
        from services.driver_service import get_driver_by_code
        
        upcoming_bets = []
        finished_bets = []
        
        for bet in bets:
            race = await get_race_by_id(bet.race_id)
            if not race:
                continue
            
            driver_1st = await get_driver_by_code(bet.driver_1st)
            driver_2nd = await get_driver_by_code(bet.driver_2nd)
            driver_3rd = await get_driver_by_code(bet.driver_3rd)
            
            bet_info = {
                "bet": bet,
                "race": race,
                "driver_1st": driver_1st,
                "driver_2nd": driver_2nd,
                "driver_3rd": driver_3rd,
            }
            
            if race.status == "finished" or not is_betting_open(race.date, race.start_time, race.timezone):
                finished_bets.append(bet_info)
            else:
                upcoming_bets.append(bet_info)
        
        # Build message
        text = "📋 <b>My Bets</b>\n\n"
        
        if upcoming_bets:
            text += "🏁 <b>Upcoming Races</b> (can be changed):\n\n"
            for bet_info in upcoming_bets:
                race = bet_info["race"]
                bet = bet_info["bet"]
                text += f"🏁 <b>{race.name}</b>\n"
                text += f"📅 {race.date} at {race.start_time}\n"
                text += f"1️⃣ {bet_info['driver_1st'].code if bet_info['driver_1st'] else bet.driver_1st} - {bet_info['driver_1st'].full_name if bet_info['driver_1st'] else ''}\n"
                text += f"2️⃣ {bet_info['driver_2nd'].code if bet_info['driver_2nd'] else bet.driver_2nd} - {bet_info['driver_2nd'].full_name if bet_info['driver_2nd'] else ''}\n"
                text += f"3️⃣ {bet_info['driver_3rd'].code if bet_info['driver_3rd'] else bet.driver_3rd} - {bet_info['driver_3rd'].full_name if bet_info['driver_3rd'] else ''}\n\n"
        
        if finished_bets:
            text += "✅ <b>Finished Races</b>:\n\n"
            for bet_info in finished_bets:
                race = bet_info["race"]
                bet = bet_info["bet"]
                text += f"✅ <b>{race.name}</b>\n"
                text += f"📅 {race.date}\n"
                text += f"1️⃣ {bet_info['driver_1st'].code if bet_info['driver_1st'] else bet.driver_1st} - {bet_info['driver_1st'].full_name if bet_info['driver_1st'] else ''}\n"
                text += f"2️⃣ {bet_info['driver_2nd'].code if bet_info['driver_2nd'] else bet.driver_2nd} - {bet_info['driver_2nd'].full_name if bet_info['driver_2nd'] else ''}\n"
                text += f"3️⃣ {bet_info['driver_3rd'].code if bet_info['driver_3rd'] else bet.driver_3rd} - {bet_info['driver_3rd'].full_name if bet_info['driver_3rd'] else ''}\n\n"
        
        # Create keyboard for upcoming bets
        if upcoming_bets:
            builder = InlineKeyboardBuilder()
            for bet_info in upcoming_bets:
                race = bet_info["race"]
                bet = bet_info["bet"]
                builder.add(InlineKeyboardButton(
                    text=f"✏️ Change {race.name}",
                    callback_data=f"change_bet_{bet.id}"
                ))
                builder.add(InlineKeyboardButton(
                    text=f"🗑️ Delete {race.name}",
                    callback_data=f"delete_bet_{bet.id}"
                ))
            builder.adjust(1)
            await message.answer(text, reply_markup=builder.as_markup())
        else:
            await message.answer(text)
    
    except Exception as e:
        await message.answer(
            "Sorry, something went wrong. Please try again later."
        )


@router.callback_query(F.data.startswith("change_bet_"))
async def callback_change_bet(callback: CallbackQuery, state: FSMContext):
    """Handle change bet request."""
    bet_id = int(callback.data.split("_")[-1])
    
    # Get bet
    from services.bet_service import get_user_bets
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("User not found.", show_alert=True)
        return
    
    bets = await get_user_bets(user.id)
    bet = next((b for b in bets if b.id == bet_id), None)
    
    if not bet:
        await callback.answer("Bet not found.", show_alert=True)
        return
    
    # Get race
    race = await get_race_by_id(bet.race_id)
    if not race:
        await callback.answer("Race not found.", show_alert=True)
        return
    
    # Check if betting is still open
    from services.bet_service import is_betting_open
    if not is_betting_open(race.date, race.start_time, race.timezone):
        await callback.answer(
            "You cannot change this bet. Betting is closed for this race.",
            show_alert=True
        )
        return
    
    # Start bet flow with existing bet data
    await state.update_data(race_id=race.id, existing_bet=True)
    await state.set_state(BetStates.waiting_for_1st)
    
    await callback.message.edit_text(
        f"✏️ <b>Change Bet</b>\n\n"
        f"Race: <b>{race.name}</b>\n"
        f"Current bet:\n"
        f"1️⃣ {bet.driver_1st}\n"
        f"2️⃣ {bet.driver_2nd}\n"
        f"3️⃣ {bet.driver_3rd}\n\n"
        f"Select new driver for 1st place:"
    )
    await callback.answer()
    await show_driver_selection_callback(callback, state, "1st")


@router.callback_query(F.data.startswith("delete_bet_"))
async def callback_delete_bet(callback: CallbackQuery, state: FSMContext):
    """Handle delete bet request."""
    bet_id = int(callback.data.split("_")[-1])
    
    # Get bet
    from services.bet_service import get_user_bets, delete_bet
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("User not found.", show_alert=True)
        return
    
    bets = await get_user_bets(user.id)
    bet = next((b for b in bets if b.id == bet_id), None)
    
    if not bet:
        await callback.answer("Bet not found.", show_alert=True)
        return
    
    # Get race
    race = await get_race_by_id(bet.race_id)
    if not race:
        await callback.answer("Race not found.", show_alert=True)
        return
    
    # Check if betting is still open
    from services.bet_service import is_betting_open
    if not is_betting_open(race.date, race.start_time, race.timezone):
        await callback.answer(
            "You cannot delete this bet. Betting is closed for this race.",
            show_alert=True
        )
        return
    
    # Show confirmation
    from services.driver_service import get_driver_by_code
    driver_1st = await get_driver_by_code(bet.driver_1st)
    driver_2nd = await get_driver_by_code(bet.driver_2nd)
    driver_3rd = await get_driver_by_code(bet.driver_3rd)
    
    await callback.message.edit_text(
        f"🗑️ <b>Delete Bet</b>\n\n"
        f"Race: <b>{race.name}</b>\n"
        f"Date: {race.date} at {race.start_time}\n\n"
        f"Your bet:\n"
        f"1️⃣ {driver_1st.code if driver_1st else bet.driver_1st} - {driver_1st.full_name if driver_1st else ''}\n"
        f"2️⃣ {driver_2nd.code if driver_2nd else bet.driver_2nd} - {driver_2nd.full_name if driver_2nd else ''}\n"
        f"3️⃣ {driver_3rd.code if driver_3rd else bet.driver_3rd} - {driver_3rd.full_name if driver_3rd else ''}\n\n"
        f"Are you sure you want to delete this bet?",
        reply_markup=get_confirm_keyboard(f"confirm_delete_bet_{bet.id}", "cancel_delete_bet")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_bet_"))
async def callback_confirm_delete_bet(callback: CallbackQuery):
    """Handle bet deletion confirmation."""
    bet_id = int(callback.data.split("_")[-1])
    
    # Get bet
    from services.bet_service import get_user_bets, delete_bet
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("User not found.", show_alert=True)
        return
    
    bets = await get_user_bets(user.id)
    bet = next((b for b in bets if b.id == bet_id), None)
    
    if not bet:
        await callback.answer("Bet not found.", show_alert=True)
        return
    
    # Get race for name
    race = await get_race_by_id(bet.race_id)
    race_name = race.name if race else "Unknown"
    
    # Delete bet
    success = await delete_bet(user.id, bet.race_id)
    
    if success:
        await callback.message.edit_text(
            f"✅ <b>Bet deleted successfully!</b>\n\n"
            f"Deleted bet for: <b>{race_name}</b>"
        )
        await callback.answer("Bet deleted!")
    else:
        await callback.answer("Error deleting bet. Please try again.", show_alert=True)
        await callback.message.edit_text("❌ Error deleting bet. Please try again.")


@router.callback_query(F.data == "cancel_delete_bet")
async def callback_cancel_delete_bet(callback: CallbackQuery):
    """Handle delete bet cancellation."""
    await callback.message.edit_text("❌ Deletion cancelled.")
    await callback.answer()


@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message):
    """Handle /leaderboard command (F-008, C-004)."""
    try:
        from services.scoring_service import get_leaderboard
        
        leaderboard = await get_leaderboard(limit=20)
        
        if not leaderboard:
            await message.answer(
                "🏆 <b>Leaderboard</b>\n\n"
                "No points yet. Play your first race to see the leaderboard."
            )
            return
        
        text = "🏆 <b>Leaderboard</b>\n\n"
        
        # Medal emojis for top 3
        medals = ["🥇", "🥈", "🥉"]
        
        for entry in leaderboard:
            rank = entry['rank']
            name = entry['full_name']
            points = entry['total_points']
            
            medal = medals[rank - 1] if rank <= 3 else f"{rank}."
            text += f"{medal} {name} – {points} points\n"
        
        await message.answer(text)
    
    except Exception as e:
        await message.answer(
            "Sorry, something went wrong. Please try again later."
        )


@router.message(Command("me", "mystats"))
async def cmd_me(message: Message):
    """Handle /me or /mystats command (F-009, C-005)."""
    try:
        # Register or update user
        user = await get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name or message.from_user.first_name,
        )
        
        from services.scoring_service import (
            get_user_total_points,
            get_user_points_per_race,
            get_user_bets_count
        )
        from services.bet_service import get_user_bets
        from services.race_service import get_race_by_id
        from services.driver_service import get_driver_by_code
        
        # Get user stats
        total_points = await get_user_total_points(user.id)
        bets_count = await get_user_bets_count(user.id)
        points_per_race = await get_user_points_per_race(user.id)
        
        if bets_count == 0:
            await message.answer(
                "📊 <b>My Stats</b>\n\n"
                "You don't have any bets yet.\n"
                "Use /bet to place your first bet!"
            )
            return
        
        # Build stats message
        text = f"📊 <b>My Stats</b>\n\n"
        text += f"👤 <b>{user.full_name or user.username or f'User {user.telegram_id}'}</b>\n\n"
        text += f"🏆 Total points: <b>{total_points}</b>\n"
        text += f"🏁 Races bet on: <b>{bets_count}</b>\n\n"
        
        # Show last 5 races with points
        if points_per_race:
            text += "📈 <b>Recent Races:</b>\n\n"
            for race_data in points_per_race[:5]:  # Last 5 races
                race_name = race_data['race_name']
                race_date = race_data['race_date']
                points = race_data['points']
                
                # Get bet for this race
                bets = await get_user_bets(user.id)
                bet = next((b for b in bets if b.race_id == race_data['race_id']), None)
                
                if bet:
                    race = await get_race_by_id(bet.race_id)
                    driver_1st = await get_driver_by_code(bet.driver_1st)
                    driver_2nd = await get_driver_by_code(bet.driver_2nd)
                    driver_3rd = await get_driver_by_code(bet.driver_3rd)
                    
                    text += f"🏁 <b>{race_name}</b> ({race_date})\n"
                    text += f"   Bet: {driver_1st.code if driver_1st else bet.driver_1st}, "
                    text += f"{driver_2nd.code if driver_2nd else bet.driver_2nd}, "
                    text += f"{driver_3rd.code if driver_3rd else bet.driver_3rd}\n"
                    text += f"   Points: <b>{points}</b>\n\n"
                else:
                    text += f"🏁 <b>{race_name}</b> ({race_date})\n"
                    text += f"   Points: <b>{points}</b>\n\n"
        else:
            # Show last bets without points (if results not entered yet)
            bets = await get_user_bets(user.id)
            if bets:
                text += "📋 <b>Recent Bets:</b>\n\n"
                for bet in bets[:3]:  # Last 3 bets
                    race = await get_race_by_id(bet.race_id)
                    if race:
                        driver_1st = await get_driver_by_code(bet.driver_1st)
                        driver_2nd = await get_driver_by_code(bet.driver_2nd)
                        driver_3rd = await get_driver_by_code(bet.driver_3rd)
                        
                        text += f"🏁 <b>{race.name}</b> ({race.date})\n"
                        text += f"   Bet: {driver_1st.code if driver_1st else bet.driver_1st}, "
                        text += f"{driver_2nd.code if driver_2nd else bet.driver_2nd}, "
                        text += f"{driver_3rd.code if driver_3rd else bet.driver_3rd}\n"
                        text += f"   Points: Not calculated yet\n\n"
        
        await message.answer(text)
    
    except Exception as e:
        await message.answer(
            "Sorry, something went wrong. Please try again later."
        )

