import random
import g4f
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import bot, ADMIN_ID
from database import users_col, get_user_data, add_exp

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
        return await message.answer(f"✨ С возвращением, {u['name']}!", reply_markup=main_kb())
    
    await message.answer("Приветствую! Я — Оракул. Как мне тебя называть?")
    await state.set_state(RegStates.name)

@user_router.message(RegStates.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(RegStates.age)

@user_router.message(RegStates.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Введи возраст числом.")
    await state.update_data(age=int(message.text))
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="М"), types.KeyboardButton(text="Ж")]], resize_keyboard=True)
    await message.answer("Твой пол?", reply_markup=kb)
    await state.set_state(RegStates.gender)

@user_router.message(RegStates.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    g = "male" if "М" in message.text.upper() else "female"
    data = await state.get_data()
    uid = message.from_user.id
    
    # Создаем документ для MongoDB
    user_doc = {
        "user_id": uid,
        "name": data['name'],
        "age": data['age'],
        "gender": g,
        "limits_ai": 3,
        "limits_search": 3,
        "exp": 0,
        "level": "Новичок",
        "last_bonus": "2000-01-01 00:00:00"
    }
    
    # Сохраняем в облако
    await users_col.insert_one(user_doc)
    
    await state.clear()
    await message.answer("Регистрация завершена! Твоя судьба открыта.", reply_markup=main_kb())

    # Уведомление админу
    try:
        await bot.send_message(ADMIN_ID, f"🆕 Новый юзер: {data['name']}, {data['age']} лет, {g}")
    except: pass

# --- ПРОФИЛЬ ---

@user_router.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    u = await get_user_data(message.from_user.id)
    if not u: return
    
    is_admin = (message.from_user.id == ADMIN_ID)
    ai_lim = "∞" if is_admin else u.get('limits_ai', 0)
    search_lim = "∞" if is_admin else u.get('limits_search', 0)
    
    progress = "🔹" * (u.get('exp', 0) // 20)
    
    text = (
        f"👤 **Профиль: {u['name']}**\n"
        f"🎖 Уровень: `{u.get('level', 'Новичок')}` {'(Админ)' if is_admin else ''}\n"
        f"✨ Опыт: `{u.get('exp', 0)}`/400\n"
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
    
    if uid != ADMIN_ID and u.get('limits_ai', 0) <= 0: 
        return await message.answer("⏳ Энергия исчерпана. Загляни в 🎁 Бонус!")
    
    m = await message.answer("🔮 *Оракул входит в транс...*", parse_mode="Markdown")
    
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.default,
            messages=[{"role": "user", "content": f"Дай короткое предсказание для {u['name']}, {u['age']} лет."}]
        )
        ans = response
    except:
        ans = "Звезды молчат, но твое сердце знает ответ."

    await add_exp(uid, 10) # Добавляем опыт через нашу функцию
    
    # Списываем лимит в MongoDB
    if uid != ADMIN_ID:
        await users_col.update_one({"user_id": uid}, {"$inc": {"limits_ai": -1}})
        
    await m.edit_text(f"📜 **Предсказание:**\n\n{ans}\n\n*+10 EXP*", parse_mode="Markdown")

# --- БОНУС ---

@user_router.message(F.text == "🎁 Бонус")
async def daily_bonus(message: types.Message):
    uid = message.from_user.id
    u = await get_user_data(uid)
    
    last_bonus_str = u.get('last_bonus', '2000-01-01 00:00:00')
    last_bonus_time = datetime.strptime(last_bonus_str, '%Y-%m-%d %H:%M:%S')
    
    if datetime.now() < last_bonus_time + timedelta(days=1) and uid != ADMIN_ID:
        return await message.answer("⏳ Бонус можно брать раз в 24 часа!")

    await users_col.update_one(
        {"user_id": uid},
        {
            "$inc": {"limits_ai": 2, "limits_search": 2, "exp": 20},
            "$set": {"last_bonus": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        }
    )
    
    await message.answer("✨ **Благословение получено!**\n+2 Гадания, +2 Поиска, +20 EXP")