import random, g4f, aiosqlite
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import DB_PATH, bot
from database import get_user_data, add_exp # Импортируем наши функции

user_router = Router()

class RegStates(StatesGroup):
    name = State(); age = State(); gender = State()

def main_kb():
    return types.ReplyKeyboardMarkup(keyboard=[
        [types.KeyboardButton(text="🔮 Гадание"), types.KeyboardButton(text="🤝 Найти пару")],
        [types.KeyboardButton(text="👤 Профиль"), types.KeyboardButton(text="💎 Магазин")]
    ], resize_keyboard=True)

# ... (хендлеры регистрации оставляем как были) ...

@user_router.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    from config import ADMIN_ID
    u = await get_user_data(message.from_user.id)
    if not u: return
    
    is_admin = (message.from_user.id == ADMIN_ID)
    
    # Настраиваем отображение лимитов
    ai_lim = "∞" if is_admin else u['limits_ai']
    search_lim = "∞" if is_admin else u['limits_search']
    rank_suffix = " (Администратор)" if is_admin else ""

    progress = "🔹" * (u['exp'] // 20)
    
    text = (
        f"👤 **Профиль: {u['name']}**\n"
        f"🎖 Уровень: `{u['level']}{rank_suffix}`\n"
        f"✨ Опыт: `{u['exp']}`\n"
        f"{progress}\n\n"
        f"🔮 Гадания: **{ai_lim}**\n"
        f"🤝 Поиски: **{search_lim}**"
    )
    await message.answer(text, parse_mode="Markdown")

@user_router.message(F.text == "🔮 Гадание")
async def fortune(message: types.Message):
    from database import get_user_data, add_exp
    from config import ADMIN_ID
    
    uid = message.from_user.id
    u = await get_user_data(uid)
    
    # ПРОВЕРКА: Если не админ и лимиты кончились
    if uid != ADMIN_ID and u['limits_ai'] <= 0: 
        return await message.answer("Твоя магическая энергия на нуле. Приходи завтра!")
    
    m = await message.answer("🔮 Оракул входит в транс...")
    
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.default,
            messages=[{"role": "user", "content": f"Дай короткое предсказание для {u['name']}, {u['age']} лет."}]
        )
        ans = response
    except:
        ans = "Звезды скрыты туманом, но чувствую — день будет важным."

    await add_exp(uid, 10)
    
    # СПИСЫВАЕМ ЛИМИТ ТОЛЬКО У ОБЫЧНЫХ ПОЛЬЗОВАТЕЛЕЙ
    if uid != ADMIN_ID:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET limits_ai = limits_ai - 1 WHERE user_id = ?", (uid,))
            await db.commit()
        
    await m.edit_text(f"📜 **Предсказание:**\n\n{ans}\n\n*+10 EXP*", parse_mode="Markdown")

    # Начисляем 10 опыта за гадание
    await add_exp(message.from_user.id, 10)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET limits_ai = limits_ai - 1 WHERE user_id = ?", (u['user_id'],))
        await db.commit()
        
    await m.edit_text(f"📜 **Предсказание:**\n\n{ans}\n\n*+10 EXP за обращение к звездам*", parse_mode="Markdown")