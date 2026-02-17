from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import ADMIN_ID
from database import get_user_data

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
@user_router.message(F.text == "🏠 Главное меню")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear() # Сброс всех состояний, чтобы кнопки заработали
    u = await get_user_data(message.from_user.id)
    if not u:
        return await message.answer("Привет! Пройди регистрацию командой /reg")
    
    await message.answer(f"✨ Оракул приветствует тебя, {u.get('name')}!", reply_markup=main_kb())

@user_router.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    try:
        u = await get_user_data(message.from_user.id)
        if not u: return
        
        is_admin = (message.from_user.id == ADMIN_ID)
        exp = int(u.get('exp', 0))
        
        # Визуальная шкала (10 делений)
        filled = min(exp // 40, 10)
        progress_bar = "🔵" * filled + "⚪️" * (10 - filled)
        
        text = (
            f"👤 **Профиль: {u.get('name')}**\n"
            f"🎖 Уровень: `{u.get('level', 'Новичок')}`\n"
            f"✨ Опыт: `{exp}`/400\n"
            f"{progress_bar}\n\n"
            f"🔮 Гадания: **{'∞' if is_admin else u.get('limits_ai', 0)}**\n"
            f"🤝 Поиски: **{'∞' if is_admin else u.get('limits_search', 0)}**"
        )
        # Добавляем Inline-кнопку назад прямо под профиль
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="to_main")]
        ])
        await message.answer(text, parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        print(f"Ошибка в профиле: {e}")

@user_router.callback_query(F.data == "to_main")
async def back_to_main(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.message.answer("🏠 Главное меню", reply_markup=main_kb())