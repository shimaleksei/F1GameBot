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
from utils.filters import AllowedUserFilter
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
        
        # Check if user is allowed (admins are always allowed)
        if not user.is_allowed and not is_admin(message.from_user.id):
            await message.answer(
                "🔒 <b>Доступ ограничен</b>\n\n"
                "Этот бот доступен только для приглашенных пользователей.\n"
                "Обратитесь к администратору для получения доступа."
            )
            return
        
        # Welcome message
        welcome_text = (
            "Привет! Я бот для ставок на Формулу 1. Я помогаю делать виртуальные ставки на топ-3 гонщиков перед каждой гонкой.\n\n"
            "📋 Основные команды:\n"
            "• /bet – сделать или изменить ставку\n"
            "• /my_bets – посмотреть свои ставки\n"
            "• /leaderboard – таблица лидеров\n"
            "• /me – моя статистика\n"
        )
        
        # Add admin commands if user is admin
        if is_admin(message.from_user.id):
            welcome_text += (
                "\n🔧 Команды администратора:\n"
                "• /admin_races – управление гонками\n"
                "• /admin_users – управление пользователями\n"
                "• /results – ввести результаты гонки\n"
            )
        
        await message.answer(welcome_text)
        
    except Exception as e:
        await message.answer(
            "Извините, что-то пошло не так. Попробуйте снова с /start."
        )


@router.message(Command("bet"), AllowedUserFilter())
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
                "🏁 <b>Сделать ставку</b>\n\n"
                "Сейчас нет гонок, открытых для ставок.\n"
                "Проверьте позже или попросите администратора добавить гонки."
            )
            return
        
        # If only one race, go directly to driver selection
        if len(open_races) == 1:
            race = open_races[0]
            # Check if user already has a bet
            existing_bet = await get_bet(user.id, race.id)
            if existing_bet:
                await message.answer(
                    f"🏁 <b>Сделать ставку</b>\n\n"
                    f"У вас уже есть ставка на <b>{race.name}</b>:\n"
                    f"1️⃣ {existing_bet.driver_1st}\n"
                    f"2️⃣ {existing_bet.driver_2nd}\n"
                    f"3️⃣ {existing_bet.driver_3rd}\n\n"
                    "Хотите заменить её?",
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
                "🏁 <b>Сделать ставку</b>\n\n"
                "Выберите гонку:",
                reply_markup=builder.as_markup()
            )
    
    except Exception as e:
        await message.answer(
            "Не удалось загрузить список гонок. Попробуйте позже."
        )


@router.callback_query(F.data.startswith("bet_race_"))
async def callback_bet_race_select(callback: CallbackQuery, state: FSMContext):
    """Handle race selection for betting."""
    race_id = int(callback.data.split("_")[-1])
    race = await get_race_by_id(race_id)
    
    if not race:
        await callback.answer("Гонка не найдена.", show_alert=True)
        await callback.message.edit_text("Гонка не найдена.")
        await state.clear()
        return
    
    # Check if betting is still open
    if not is_betting_open(race.date, race.start_time, race.timezone):
        await callback.answer("Ставки на эту гонку закрыты.", show_alert=True)
        await callback.message.edit_text(
            "❌ Ставки на эту гонку закрыты."
        )
        await state.clear()
        return
    
    # Get user
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        await state.clear()
        return
    
    # Check if user already has a bet
    existing_bet = await get_bet(user.id, race.id)
    if existing_bet:
        await callback.message.edit_text(
            f"🏁 <b>Сделать ставку</b>\n\n"
            f"У вас уже есть ставка на <b>{race.name}</b>:\n"
            f"1️⃣ {existing_bet.driver_1st}\n"
            f"2️⃣ {existing_bet.driver_2nd}\n"
            f"3️⃣ {existing_bet.driver_3rd}\n\n"
            "Хотите заменить её?",
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
        "1st": "🥇 1-е место",
        "2nd": "🥈 2-е место",
        "3rd": "🥉 3-е место"
    }
    
    await message.answer(
        f"🏁 <b>Сделать ставку</b>\n\n"
        f"Выберите гонщика для {position_text[position]}:",
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
        "1st": "🥇 1-е место",
        "2nd": "🥈 2-е место",
        "3rd": "🥉 3-е место"
    }
    
    await callback.message.edit_text(
        f"🏁 <b>Сделать ставку</b>\n\n"
        f"Выберите гонщика для {position_text[position]}:",
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
        await callback.answer("Гонка не найдена.", show_alert=True)
        await state.clear()
        return
    
    from services.driver_service import get_driver_by_code
    driver_1st = await get_driver_by_code(data.get("driver_1st"))
    driver_2nd = await get_driver_by_code(data.get("driver_2nd"))
    driver_3rd = await get_driver_by_code(data.get("driver_3rd"))
    
    summary_text = (
        f"🏁 <b>Подтвердите вашу ставку</b>\n\n"
        f"Гонка: <b>{race.name}</b>\n"
        f"Дата: {race.date} в {race.start_time}\n\n"
        f"Ваша ставка:\n"
        f"🥇 1-е: {driver_1st.code if driver_1st else data.get('driver_1st')} - {driver_1st.full_name if driver_1st else ''}\n"
        f"🥈 2-е: {driver_2nd.code if driver_2nd else data.get('driver_2nd')} - {driver_2nd.full_name if driver_2nd else ''}\n"
        f"🥉 3-е: {driver_3rd.code if driver_3rd else data.get('driver_3rd')} - {driver_3rd.full_name if driver_3rd else ''}\n\n"
        f"Подтвердить?"
    )
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Подтвердить", callback_data="bet_confirm"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_bet"))
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
        await callback.answer("Гонка не найдена.", show_alert=True)
        await state.clear()
        return
    
    # Check if betting is still open
    if not is_betting_open(race.date, race.start_time, race.timezone):
        await callback.answer("Ставки на эту гонку закрыты.", show_alert=True)
        await callback.message.edit_text(
            "❌ Ставки на эту гонку закрыты."
        )
        await state.clear()
        return
    
    # Get user
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
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
            f"{'✅ Ставка обновлена!' if existing else '✅ Ставка сделана!'}\n\n"
            f"Гонка: <b>{race.name}</b>\n"
            f"Дата: {race.date} в {race.start_time}\n\n"
            f"Ваша ставка:\n"
            f"🥇 1-е: {driver_1st_obj.code if driver_1st_obj else driver_1st} - {driver_1st_obj.full_name if driver_1st_obj else ''}\n"
            f"🥈 2-е: {driver_2nd_obj.code if driver_2nd_obj else driver_2nd} - {driver_2nd_obj.full_name if driver_2nd_obj else ''}\n"
            f"🥉 3-е: {driver_3rd_obj.code if driver_3rd_obj else driver_3rd} - {driver_3rd_obj.full_name if driver_3rd_obj else ''}\n\n"
            f"Удачи! 🍀"
        )
        
        await callback.message.edit_text(message_text)
        await callback.answer("Ставка сохранена!")
    except Exception as e:
        await callback.answer("Ошибка при сохранении ставки. Попробуйте снова.", show_alert=True)
        await callback.message.edit_text(
            "❌ Ошибка при сохранении ставки. Попробуйте снова."
        )
    
    await state.clear()


@router.callback_query(F.data == "cancel_bet")
async def callback_cancel_bet(callback: CallbackQuery, state: FSMContext):
    """Handle bet cancellation."""
    await state.clear()
    await callback.message.edit_text("❌ Ставка отменена.")
    await callback.answer()


@router.message(Command("my_bets"), AllowedUserFilter())
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
                "📋 <b>Мои ставки</b>\n\n"
                "У вас пока нет ставок.\n"
                "Используйте /bet, чтобы сделать первую ставку!"
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
        text = "📋 <b>Мои ставки</b>\n\n"
        
        if upcoming_bets:
            text += "🏁 <b>Предстоящие гонки</b> (можно изменить):\n\n"
            for bet_info in upcoming_bets:
                race = bet_info["race"]
                bet = bet_info["bet"]
                text += f"🏁 <b>{race.name}</b>\n"
                text += f"📅 {race.date} at {race.start_time}\n"
                text += f"1️⃣ {bet_info['driver_1st'].code if bet_info['driver_1st'] else bet.driver_1st} - {bet_info['driver_1st'].full_name if bet_info['driver_1st'] else ''}\n"
                text += f"2️⃣ {bet_info['driver_2nd'].code if bet_info['driver_2nd'] else bet.driver_2nd} - {bet_info['driver_2nd'].full_name if bet_info['driver_2nd'] else ''}\n"
                text += f"3️⃣ {bet_info['driver_3rd'].code if bet_info['driver_3rd'] else bet.driver_3rd} - {bet_info['driver_3rd'].full_name if bet_info['driver_3rd'] else ''}\n\n"
        
        if finished_bets:
            text += "✅ <b>Завершенные гонки</b>:\n\n"
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
                    text=f"✏️ Изменить {race.name}",
                    callback_data=f"change_bet_{bet.id}"
                ))
                builder.add(InlineKeyboardButton(
                    text=f"🗑️ Удалить {race.name}",
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
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    
    bets = await get_user_bets(user.id)
    bet = next((b for b in bets if b.id == bet_id), None)
    
    if not bet:
        await callback.answer("Ставка не найдена.", show_alert=True)
        return
    
    # Get race
    race = await get_race_by_id(bet.race_id)
    if not race:
        await callback.answer("Гонка не найдена.", show_alert=True)
        return
    
    # Check if betting is still open
    from services.bet_service import is_betting_open
    if not is_betting_open(race.date, race.start_time, race.timezone):
        await callback.answer(
            "Вы не можете изменить эту ставку. Ставки на эту гонку закрыты.",
            show_alert=True
        )
        return
    
    # Start bet flow with existing bet data
    await state.update_data(race_id=race.id, existing_bet=True)
    await state.set_state(BetStates.waiting_for_1st)
    
    await callback.message.edit_text(
        f"✏️ <b>Изменить ставку</b>\n\n"
        f"Гонка: <b>{race.name}</b>\n"
        f"Текущая ставка:\n"
        f"1️⃣ {bet.driver_1st}\n"
        f"2️⃣ {bet.driver_2nd}\n"
        f"3️⃣ {bet.driver_3rd}\n\n"
        f"Выберите нового гонщика для 1-го места:"
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
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    
    bets = await get_user_bets(user.id)
    bet = next((b for b in bets if b.id == bet_id), None)
    
    if not bet:
        await callback.answer("Ставка не найдена.", show_alert=True)
        return
    
    # Get race
    race = await get_race_by_id(bet.race_id)
    if not race:
        await callback.answer("Гонка не найдена.", show_alert=True)
        return
    
    # Check if betting is still open
    from services.bet_service import is_betting_open
    if not is_betting_open(race.date, race.start_time, race.timezone):
        await callback.answer(
            "Вы не можете удалить эту ставку. Ставки на эту гонку закрыты.",
            show_alert=True
        )
        return
    
    # Show confirmation
    from services.driver_service import get_driver_by_code
    driver_1st = await get_driver_by_code(bet.driver_1st)
    driver_2nd = await get_driver_by_code(bet.driver_2nd)
    driver_3rd = await get_driver_by_code(bet.driver_3rd)
    
    from utils.keyboards import get_confirm_keyboard
    await callback.message.edit_text(
        f"🗑️ <b>Удалить ставку</b>\n\n"
        f"Гонка: <b>{race.name}</b>\n"
        f"Дата: {race.date} в {race.start_time}\n\n"
        f"Ваша ставка:\n"
        f"1️⃣ {driver_1st.code if driver_1st else bet.driver_1st} - {driver_1st.full_name if driver_1st else ''}\n"
        f"2️⃣ {driver_2nd.code if driver_2nd else bet.driver_2nd} - {driver_2nd.full_name if driver_2nd else ''}\n"
        f"3️⃣ {driver_3rd.code if driver_3rd else bet.driver_3rd} - {driver_3rd.full_name if driver_3rd else ''}\n\n"
        f"Вы уверены, что хотите удалить эту ставку?",
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
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    
    bets = await get_user_bets(user.id)
    bet = next((b for b in bets if b.id == bet_id), None)
    
    if not bet:
        await callback.answer("Ставка не найдена.", show_alert=True)
        return
    
    # Get race for name
    race = await get_race_by_id(bet.race_id)
    race_name = race.name if race else "Неизвестно"
    
    # Delete bet
    success = await delete_bet(user.id, bet.race_id)
    
    if success:
        await callback.message.edit_text(
            f"✅ <b>Ставка успешно удалена!</b>\n\n"
            f"Удалена ставка на: <b>{race_name}</b>"
        )
        await callback.answer("Ставка удалена!")
    else:
        await callback.answer("Ошибка при удалении ставки. Попробуйте снова.", show_alert=True)
        await callback.message.edit_text("❌ Ошибка при удалении ставки. Попробуйте снова.")


@router.callback_query(F.data == "cancel_delete_bet")
async def callback_cancel_delete_bet(callback: CallbackQuery):
    """Handle delete bet cancellation."""
    await callback.message.edit_text("❌ Удаление отменено.")
    await callback.answer()


@router.message(Command("leaderboard"), AllowedUserFilter())
async def cmd_leaderboard(message: Message):
    """Handle /leaderboard command (F-008, C-004)."""
    try:
        from services.scoring_service import get_leaderboard
        
        leaderboard = await get_leaderboard(limit=20)
        
        if not leaderboard:
            await message.answer(
                "🏆 <b>Таблица лидеров</b>\n\n"
                "Пока нет очков. Сыграйте первую гонку, чтобы увидеть таблицу лидеров."
            )
            return
        
        text = "🏆 <b>Таблица лидеров</b>\n\n"
        
        # Medal emojis for top 3
        medals = ["🥇", "🥈", "🥉"]
        
        for entry in leaderboard:
            rank = entry['rank']
            name = entry['full_name']
            points = entry['total_points']
            
            medal = medals[rank - 1] if rank <= 3 else f"{rank}."
            text += f"{medal} {name} – {points} очков\n"
        
        await message.answer(text)
    
    except Exception as e:
        await message.answer(
            "Извините, что-то пошло не так. Попробуйте позже."
        )


@router.message(Command("me", "mystats"), AllowedUserFilter())
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
                "📊 <b>Моя статистика</b>\n\n"
                "У вас пока нет ставок.\n"
                "Используйте /bet, чтобы сделать первую ставку!"
            )
            return
        
        # Build stats message
        text = f"📊 <b>Моя статистика</b>\n\n"
        text += f"👤 <b>{user.full_name or user.username or f'Пользователь {user.telegram_id}'}</b>\n\n"
        text += f"🏆 Всего очков: <b>{total_points}</b>\n"
        text += f"🏁 Гонок со ставками: <b>{bets_count}</b>\n\n"
        
        # Show last 5 races with points
        if points_per_race:
            text += "📈 <b>Последние гонки:</b>\n\n"
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
                    text += f"   Ставка: {driver_1st.code if driver_1st else bet.driver_1st}, "
                    text += f"{driver_2nd.code if driver_2nd else bet.driver_2nd}, "
                    text += f"{driver_3rd.code if driver_3rd else bet.driver_3rd}\n"
                    text += f"   Очки: <b>{points}</b>\n\n"
                else:
                    text += f"🏁 <b>{race_name}</b> ({race_date})\n"
                    text += f"   Очки: <b>{points}</b>\n\n"
        else:
            # Show last bets without points (if results not entered yet)
            bets = await get_user_bets(user.id)
            if bets:
                text += "📋 <b>Последние ставки:</b>\n\n"
                for bet in bets[:3]:  # Last 3 bets
                    race = await get_race_by_id(bet.race_id)
                    if race:
                        driver_1st = await get_driver_by_code(bet.driver_1st)
                        driver_2nd = await get_driver_by_code(bet.driver_2nd)
                        driver_3rd = await get_driver_by_code(bet.driver_3rd)
                        
                        text += f"🏁 <b>{race.name}</b> ({race.date})\n"
                        text += f"   Ставка: {driver_1st.code if driver_1st else bet.driver_1st}, "
                        text += f"{driver_2nd.code if driver_2nd else bet.driver_2nd}, "
                        text += f"{driver_3rd.code if driver_3rd else bet.driver_3rd}\n"
                        text += f"   Очки: Еще не подсчитаны\n\n"
        
        await message.answer(text)
    
    except Exception as e:
        await message.answer(
            "Извините, что-то пошло не так. Попробуйте позже."
        )


# Handler for non-allowed users trying to use commands
# This must be the last handler to catch all messages from non-allowed users
# IMPORTANT: This handler should NOT catch commands - only regular text messages
@router.message(F.text & ~F.text.startswith("/"))
async def handle_non_allowed_user(message: Message):
    """Handle text messages (not commands) from users who are not allowed."""
    # Skip if user is admin (always allowed)
    if is_admin(message.from_user.id):
        return
    
    # Check if user is allowed
    user = await get_user_by_telegram_id(message.from_user.id)
    if user and user.is_allowed:
        return  # User is allowed, let other handlers process
    
    # User is not allowed - show message
    await message.answer(
        "🔒 <b>Доступ ограничен</b>\n\n"
        "Этот бот доступен только для приглашенных пользователей.\n"
        "Обратитесь к администратору для получения доступа.\n\n"
        "Используйте /start для проверки статуса."
    )
