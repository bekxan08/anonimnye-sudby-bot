from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- КЛАВИАТУРЫ ---

def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔮 Гадание"), KeyboardButton(text="🤝 Найти пару")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🎁 Бонус")],
        [KeyboardButton(text="💎 Магазин")]
    ], resize_keyboard=True)

def back_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🏠 Главное меню")]
    ], resize_keyboard=True)

# --- ОБРАБОТЧИКИ МЕНЮ ---

@user_router.message(F.text == "🏠 Главное меню")
async def back_to_menu(message: types.Message, state: FSMContext):
    await state.clear() # Очищаем все ожидания ввода, чтобы кнопки ожили
    await message.answer("Вы вернулись в главное меню", reply_markup=main_kb())

@user_router.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    try:
        u = await get_user_data(message.from_user.id)
        if not u: 
            return await message.answer("Сначала пройди регистрацию через /start")
        
        is_admin = (message.from_user.id == ADMIN_ID)
        
        # Безопасные лимиты
        ai_lim = "∞" if is_admin else u.get('limits_ai', 0)
        search_lim = "∞" if is_admin else u.get('limits_search', 0)
        
        # Безопасная шкала опыта (10 делений)
        current_exp = u.get('exp', 0)
        filled = min(int(current_exp // 40), 10) 
        progress_bar = "🔵" * filled + "⚪️" * (10 - filled)
        
        text = (
            f"👤 **Профиль: {u.get('name', 'Странник')}**\n"
            f"🗓 В игре с: `{u.get('reg_date', '---')}`\n"
            f"🎖 Уровень: `{u.get('level', 'Новичок')}`\n"
            f"✨ Опыт: `{current_exp}`/400\n"
            f"{progress_bar}\n\n"
            f"🔮 Гадания: **{ai_lim}**\n"
            f"🤝 Поиски: **{search_lim}**"
        )
        # Добавляем кнопку "Назад" к профилю для удобства
        await message.answer(text, parse_mode="Markdown", reply_markup=main_kb())
        
    except Exception as e:
        print(f"❌ Критическая ошибка профиля: {e}")
        await message.answer("Произошла ошибка при загрузке профиля. Напиши /start")