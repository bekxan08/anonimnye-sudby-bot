import random
import g4f
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import DB_PATH, bot, ADMIN_ID
from database import get_user_data, add_exp

user_router = Router()

class RegStates(StatesGroup):
    name = State()
    age = State()
    gender = State()

def main_kb():
    return types.ReplyKeyboardMarkup(keyboard=[
        [types.KeyboardButton(text="🔮 Гадание"), types.KeyboardButton(text="🤝 Найти пару")],
        [types.KeyboardButton(text="👤 Профиль"), types.KeyboardButton(text="🎁 Бонус")],
        [types.KeyboardButton(text="💎 Магазин")]
    ], resize_keyboard=True)

# --- РЕГИСТРАЦИЯ ---

@user_router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    u = await get_user_data(message.from_user.id)
    if u:
        return await message.answer(f"✨ С возвращением, {u['name']}! Звезды ждут тебя.", reply_markup=main_kb())
    
    await message.answer("Приветствую! Я — Оракул. Чтобы я мог видеть твою судьбу, назови свое имя:")
    await state.set_state(RegStates.name)

@user_router.message(RegStates.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе полных лет?")
    await state.set_state(RegStates.age)

@user_router.message(RegStates.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Пожалуйста, введи возраст цифрами.")
    await state.update_data(age=int(message.text))
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="М"), types.KeyboardButton(text="Ж")]], resize_keyboard=True)
    await message.answer("Твой пол?", reply_markup=kb)
    await state.set_state(RegStates.gender)

@user_router.message(RegStates.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    g = "male" if "М" in message.text.upper() else "female"
    data = await state.get_data()
    uid = message.from_user.id
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (user_id, name, age, gender, last_bonus) VALUES (?,?,?,?,?)",
            (uid, data['name'], data['age'], g, '2000-01-01 00:00:00')
        )
        await db.commit()
    
    await state.clear()
    await message.answer("Регистрация завершена! Твоя судьба в твоих руках.", reply_markup=main_kb())

    # Уведомление админа
    try:
        gender_icon = "👨" if g == "male" else "👩"
        await bot.send_message(
            ADMIN_ID, 
            f"🆕 **Новый пользователь!**\n{gender_icon} {data['name']}, {data['age']} лет\n🆔 ID: `{uid}`",
            parse_mode="Markdown"
        )
    except: pass

# --- ПРОФИЛЬ ---

@user_router.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    u = await get_user_data(message.from_user.id)
    if not u: return
    
    is_admin = (message.from_user.id == ADMIN_ID)
    ai_lim = "∞" if is_admin else u['limits_ai']
    search_lim = "∞" if is_admin else u['limits_search']
    
    progress = "🔹" * (u['exp'] // 20) if u['exp'] < 200 else "🔹" * 10
    
    text = (
        f"👤 **Профиль: {u['name']}**\n"
        f"🎖 Уровень: `{u['level']}` {'(Админ)' if is_admin else ''}\n"
        f"✨ Опыт: `{u['exp']}`\n"
        f"{progress}\n\n"
        f"🔮 Гадания: **{ai_lim}**\n"
        f"🤝 Поиски: **{search_lim}**"
    )
    await message.answer(text, parse_mode="Markdown")

# --- ГАДАНИЕ ---

@user_router.message(F.text == "🔮 Гадание")
async def fortune(message: types.Message):
    uid = message.from_user.id
    u = await get_user_data(uid)
    
    if uid != ADMIN_ID and u['limits_ai'] <= 0: 
        return await message.answer("⏳ Твоя энергия исчерпана. Приходи завтра или забери бонус!")
    
    m = await message.answer("🔮 *Оракул всматривается в туман...*", parse_mode="Markdown")
    
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.default,
            messages=[{"role": "user", "content": f"Дай короткое доброе предсказание для {u['name']}, {u['age']} лет в 2 предложениях."}]
        )
        ans = response
    except:
        ans = "Звезды сегодня скрыты, но я чувствую, что тебя ждет приятный сюрприз."

    await add_exp(uid, 10)
    
    if uid != ADMIN_ID:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET limits_ai = limits_ai - 1 WHERE user_id = ?", (uid,))
            await db.commit()
        
    await m.edit_text(f"📜 **Предсказание:**\n\n{ans}\n\n*+10 EXP за обращение к звездам*", parse_mode="Markdown")

# --- ЕЖЕДНЕВНЫЙ БОНУС ---

@user_router.message(F.text == "🎁 Бонус")
async def daily_bonus(message: types.Message):
    uid = message.from_user.id
    u = await get_user_data(uid)
    
    last_bonus_time = datetime.strptime(u['last_bonus'], '%Y-%m-%d %H:%M:%S')
    
    if datetime.now() < last_bonus_time + timedelta(days=1) and uid != ADMIN_ID:
        time_left = (last_bonus_time + timedelta(days=1)) - datetime.now()
        hours = time_left.seconds // 3600
        return await message.answer(f"⏳ Оракул еще восстанавливает силы. Возвращайся через {hours} ч.")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET limits_ai = limits_ai + 2, limits_search = limits_search + 2, exp = exp + 20, last_bonus = ? WHERE user_id = ?",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), uid)
        )
        await db.commit()
    
    await message.answer("✨ **Благословение получено!**\n\n+2 Гадания\n+2 Поиска\n+20 EXP", parse_mode="Markdown")