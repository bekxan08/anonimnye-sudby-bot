import asyncio
import logging
import os
import random
import aiosqlite
import g4f  # Бесплатный ИИ
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ================= CONFIG =================
# Токен берем из Secrets Replit
BOT_TOKEN = os.environ.get('8301617429:AAGGSpBGwCKQpgavoNUMiqkVdV1HCqeGzwo')
ADMIN_ID = 7587800410  # !!! ОБЯЗАТЕЛЬНО ЗАМЕНИ НА СВОЙ ID (узнай в @userinfobot) !!!
DB_PATH = "bot_data.db"

# Запасные предсказания (если ИИ долго отвечает)
OFFLINE_FORTUNES = [
    "Сегодня звезды сулят неожиданную встречу, которая изменит твою неделю.",
    "Твое упорство скоро окупится. Жди добрых вестей в делах.",
    "Оракул видит: сейчас лучшее время, чтобы довериться интуиции.",
    "Кто-то из твоего окружения тайно восхищается твоей энергией.",
    "Не бойся сделать первый шаг — дорога появится сама собой.",
    "Вечер обещает быть спокойным и принесет ответ на давний вопрос."
]

# ================= KEEP ALIVE (Uptime) =================
app = Flask('')
@app.route('/')
def home(): return "Бот работает 24/7"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# ================= INITIALIZATION =================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class RegStates(StatesGroup):
    name = State(); age = State(); gender = State()

class ChatStates(StatesGroup):
    in_chat = State()

class AdminStates(StatesGroup):
    mailing = State()

queue = {"male": [], "female": []}
active_chats = {}

# ================= DATABASE =================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, name TEXT, age INTEGER, gender TEXT,
            limits_search INTEGER DEFAULT 3, limits_ai INTEGER DEFAULT 3,
            bonus_given INTEGER DEFAULT 0, level TEXT DEFAULT 'Путник')""")
        await db.commit()

# ================= KEYBOARDS =================
def main_menu():
    kb = [
        [types.KeyboardButton(text="🔮 Гадание"), types.KeyboardButton(text="🤝 Найти пару")],
        [types.KeyboardButton(text="👤 Профиль")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_kb():
    kb = [
        [types.KeyboardButton(text="📊 Статистика"), types.KeyboardButton(text="📢 Рассылка")],
        [types.KeyboardButton(text="🏠 Главное меню")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# ================= ADMIN HANDLERS =================
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🔧 Админ-панель активирована", reply_markup=admin_kb())

@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            count = (await c.fetchone())[0]
    await message.answer(f"📈 Всего пользователей: {count}")

@dp.message(F.text == "📢 Рассылка")
async def start_mailing(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Введите текст рассылки (или напишите /cancel):")
    await state.set_state(AdminStates.mailing)

@dp.message(AdminStates.mailing)
async def exec_mailing(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("Отменено", reply_markup=admin_kb())
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            users = await cur.fetchall()
    
    await message.answer(f"Начинаю рассылку...")
    count = 0
    for u in users:
        try:
            await bot.send_message(u[0], message.text)
            count += 1
            await asyncio.sleep(0.05)
        except: continue
    await state.clear()
    await message.answer(f"✅ Рассылка завершена. Получили: {count}", reply_markup=admin_kb())

# ================= USER HANDLERS =================
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (message.from_user.id,)) as c:
            if await c.fetchone():
                return await message.answer("✨ С возвращением!", reply_markup=main_menu())
    
    await message.answer("Приветствую! Я — Оракул. Как тебя зовут?")
    await state.set_state(RegStates.name)

@dp.message(RegStates.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(RegStates.age)

@dp.message(RegStates.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (18 <= int(message.text) <= 90):
        return await message.answer("Введите возраст цифрами (18+)")
    await state.update_data(age=int(message.text))
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="М"), types.KeyboardButton(text="Ж")]], resize_keyboard=True)
    await message.answer("Твой пол?", reply_markup=kb)
    await state.set_state(RegStates.gender)

@dp.message(RegStates.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    gender = "male" if "М" in message.text.upper() else "female"
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO users (user_id, name, age, gender) VALUES (?,?,?,?)",
                         (message.from_user.id, data['name'], data['age'], gender))
        await db.commit()
    await state.clear()
    await message.answer("Регистрация завершена!", reply_markup=main_menu())

# --- ГАДАНИЕ ЧЕРЕЗ GPT4FREE ---
@dp.message(F.text == "🔮 Гадание")
async def fortune(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (message.from_user.id,)) as c:
            user = await c.fetchone()
    
    if user['limits_ai'] <= 0: 
        return await message.answer("Лимиты гаданий на сегодня исчерпаны.")

    m = await message.answer("🔮 *Оракул входит в транс...*", parse_mode="Markdown")
    
    try:
        # Пытаемся получить бесплатный ответ ИИ
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.default,
            messages=[{"role": "user", "content": f"Я {user['name']}, мне {user['age']}. Дай короткое доброе предсказание на сегодня (2 предложения)."}],
        )
        ans = response
    except Exception:
        # Если ИИ не ответил, берем из списка
        ans = random.choice(OFFLINE_FORTUNES)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET limits_ai = limits_ai - 1 WHERE user_id = ?", (user['user_id'],))
        await db.commit()
    
    await m.edit_text(f"📜 **Предсказание:**\n\n{ans}", parse_mode="Markdown")

# --- АНОНИМНЫЙ ЧАТ ---
@dp.message(F.text == "🤝 Найти пару")
async def find_pair(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (uid,)) as c:
            u = await c.fetchone()

    if u['limits_search'] <= 0:
        if u['bonus_given'] == 0:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET limits_search = 1, bonus_given = 1 WHERE user_id = ?", (uid,))
                await db.commit()
            await message.answer("✨ Энергия на нуле, но я дарю тебе +1 поиск!")
        else: return await message.answer("Лимиты исчерпаны. Жди завтра!")

    target = "female" if u['gender'] == "male" else "male"
    if uid in queue[u['gender']]: queue[u['gender']].remove(uid)

    for p_id in queue[target]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT age FROM users WHERE user_id = ?", (p_id,)) as c:
                p_age = (await c.fetchone())[0]
        
        # Логика подбора (М: сверстницы, Ж: до +5 лет)
        match = False
        if u['gender'] == "male" and p_age <= u['age']: match = True
        if u['gender'] == "female" and p_age <= u['age'] + 5: match = True

        if match:
            queue[target].remove(p_id)
            active_chats[uid] = p_id; active_chats[p_id] = uid
            await state.set_state(ChatStates.in_chat)
            await dp.fsm.get_context(bot, p_id, p_id).set_state(ChatStates.in_chat)
            
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET limits_search = limits_search - 1 WHERE user_id = ?", (uid,))
                await db.commit()
            
            await bot.send_message(p_id, "🤝 Пара найдена! /stop - выйти.")
            return await message.answer("🤝 Пара найдена! /stop - выйти.")

    queue[u['gender']].append(uid)
    await message.answer("Ищу того, кто тебе предначертан... (Ожидай)")

@dp.message(ChatStates.in_chat)
async def chatting(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    if message.text == "/stop":
        p = active_chats.pop(uid, None)
        if p:
            active_chats.pop(p, None)
            await state.clear()
            await dp.fsm.get_context(bot, p, p).clear()
            await bot.send_message(p, "Собеседник покинул чат.")
        return await message.answer("Чат завершен.", reply_markup=main_menu())
    
    p = active_chats.get(uid)
    if p: await bot.send_message(p, f"💬 {message.text}")

@dp.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (message.from_user.id,)) as c:
            u = await c.fetchone()
    await message.answer(f"👤 {u['name']}, {u['age']} лет\n🔮 Гадания: {u['limits_ai']}\n🤝 Поиски: {u['limits_search']}")

@dp.message(F.text == "🏠 Главное меню")
async def menu_back(message: types.Message):
    await message.answer("Главное меню", reply_markup=main_menu())

async def main():
    await init_db()
    keep_alive() # Запуск сервера для Uptime
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())