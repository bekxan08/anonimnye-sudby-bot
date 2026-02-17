import random, g4f, aiosqlite
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import DB_PATH, bot

user_router = Router()

class RegStates(StatesGroup):
    name = State(); age = State(); gender = State()

def main_kb():
    return types.ReplyKeyboardMarkup(keyboard=[
        [types.KeyboardButton(text="🔮 Гадание"), types.KeyboardButton(text="🤝 Найти пару")],
        [types.KeyboardButton(text="👤 Профиль"), types.KeyboardButton(text="💎 Магазин")]
    ], resize_keyboard=True)

@user_router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (message.from_user.id,)) as c:
            if await c.fetchone():
                return await message.answer("С возвращением!", reply_markup=main_kb())
    await message.answer("Привет! Как тебя зовут?")
    await state.set_state(RegStates.name)

@user_router.message(RegStates.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(RegStates.age)

@user_router.message(RegStates.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("Цифрами, пожалуйста.")
    await state.update_data(age=int(message.text))
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="М"), types.KeyboardButton(text="Ж")]], resize_keyboard=True)
    await message.answer("Твой пол?", reply_markup=kb)
    await state.set_state(RegStates.gender)

@user_router.message(RegStates.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    g = "male" if "М" in message.text.upper() else "female"
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO users (user_id, name, age, gender) VALUES (?,?,?,?)",
                         (message.from_user.id, data['name'], data['age'], g))
        await db.commit()
    await state.clear()
    await message.answer("Готово!", reply_markup=main_kb())

@user_router.message(F.text == "🔮 Гадание")
async def fortune(message: types.Message):
    from database import get_user_data
    u = await get_user_data(message.from_user.id)
    if u['limits_ai'] <= 0: return await message.answer("Лимиты кончились.")
    
    m = await message.answer("🔮 Оракул думает...")
    try:
        ans = await g4f.ChatCompletion.create_async(
            model=g4f.models.default,
            messages=[{"role": "user", "content": f"Дай предсказание для {u['name']}, {u['age']} лет в 2 предложениях."}]
        )
    except: ans = "Звезды сегодня молчат..."
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET limits_ai = limits_ai - 1 WHERE user_id = ?", (u['user_id'],))
        await db.commit()
    await m.edit_text(f"📜 {ans}")