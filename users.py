from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime
from config import ADMIN_ID
from database import get_user_data, users_col

user_router = Router()

# --- КЛАВИАТУРЫ ---

def main_kb():
    return types.ReplyKeyboardMarkup(keyboard=[
        [types.KeyboardButton(text="🔮 Гадание"), types.KeyboardButton(text="🤝 Найти пару")],
        [types.KeyboardButton(text="👤 Профиль"), types.KeyboardButton(text="🎁 Бонус")],
        [types.KeyboardButton(text="💎 Магазин")]
    ], resize_keyboard=True)

# --- ОБРАБОТЧИКИ ---

@user_router.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear() # Это "лечит" зависшие кнопки
    u = await get_user_data(message.from_user.id)
    if u:
        await message.answer(f"✨ С возвращением, {u.get('name')}!", reply_markup=main_kb())
    else:
        # Тут должна быть твоя логика регистрации
        await message.answer("Добро пожаловать! Напиши /reg для регистрации.")

@user_router.message(F.text == "🏠 Главное меню")
async def back_home(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Вы вернулись в меню", reply_markup=main_kb())

@user_router.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    try:
        u = await get_user_data(message.from_user.id)
        if not u:
            return await message.answer("Зарегистрируйтесь: /start")

        is_admin = (message.from_user.id == ADMIN_ID)
        
        # Данные из базы
        name = u.get('name', 'Странник')
        exp = int(u.get('exp', 0))
        level = u.get('level', 'Новичок')
        
        # Шкала прогресса (безопасная)
        filled = min(exp // 40, 10)
        progress_bar = "🔵" * filled + "⚪️" * (10 - filled)
        
        # Лимиты
        ai_lim = "∞" if is_admin else u.get('limits_ai', 0)
        search_lim = "∞" if is_admin else u.get('limits_search', 0)

        text = (
            f"👤 **Профиль: {name}**\n"
            f"🎖 Уровень: `{level}`\n"
            f"✨ Опыт: `{exp}`/400\n"
            f"{progress_bar}\n\n"
            f"🔮 Гадания: **{ai_lim}**\n"
            f"🤝 Поиски: **{search_lim}**"
        )
        await message.answer(text, parse_mode="Markdown", reply_markup=main_kb())
        
    except Exception as e:
        print(f"🔴 Ошибка профиля: {e}")
        await message.answer("❌ Ошибка загрузки профиля. Попробуйте /start")

@user_router.message(F.text == "💎 Магазин")
async def shop_menu(message: types.Message):
    # Пример вызова магазина из другого файла или здесь же
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔮 Купить гадания", callback_data="buy_ai")],
        [types.InlineKeyboardButton(text="💎 Купить VIP", callback_data="buy_vip")]
    ])
    await message.answer("🏪 **Магическая лавка**\nВыберите товар:", reply_markup=kb)