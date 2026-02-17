import asyncio
import logging
import sqlite3
import aiosqlite
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from openai import AsyncOpenAI

# ================= CONFIG =================
BOT_TOKEN = "8301617429:AAGGSpBGwCKQpgavoNUMiqkVdV1HCqeGzwo"
DEEPSEEK_KEY = "sk-c3b68397eabe43f682b66d02148f20da"
ADMIN_ID = 7587800410  # Вставь свой ID (узнать в @userinfobot)
DB_PATH = "bot_data.db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
ai_client = AsyncOpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# ================= DATABASE =================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT, age INTEGER, gender TEXT,
                limits_search INTEGER DEFAULT 3,
                limits_ai INTEGER DEFAULT 3,
                bonus_claimed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS fortune_history (
                user_id INTEGER, prediction TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        await db.commit()

# ================= STATES =================
class RegStates(StatesGroup):
    name = State()
    age = State()
    gender = State()

class ChatStates(StatesGroup):
    in_chat = State()

# ================= UTILS =================
queue = {"male": [], "female": []}
active_chats = {} # uid: partner_id

def main_kb():
    kb = [
        [types.KeyboardButton(text="🔮 Гадание"), types.KeyboardButton(text="🤝 Найти пару")],
        [types.KeyboardButton(text="👤 Профиль"), types.KeyboardButton(text="🎁 Сундук")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# ================= HANDLERS =================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (message.from_user.id,)) as c:
            if await c.fetchone():
                return await message.answer("С возвращением, путник!", reply_markup=main_kb())
    
    await message.answer("Приветствую! Я помогу тебе заглянуть в будущее. Как тебя зовут?")
    await state.set_state(RegStates.name)

@dp.message(RegStates.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе полных лет?")
    await state.set_state(RegStates.age)

@dp.message(RegStates.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (18 <= int(message.text) <= 90):
        return await message.answer("Ошибка! Введи возраст цифрами (18+).")
    await state.update_data(age=int(message.text))
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="М"), types.KeyboardButton(text="Ж")]], resize_keyboard=True)
    await message.answer("Твой пол? (М/Ж)", reply_markup=kb)
    await state.set_state(RegStates.gender)

@dp.message(RegStates.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    gender = "male" if "М" in message.text.upper() else "female"
    data = await state.get_data()
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, name, age, gender) VALUES (?,?,?,?)",
                         (message.from_user.id, data['name'], data['age'], gender))
        await db.commit()
    
    await state.clear()
    await message.answer(f"Регистрация завершена! Тебе доступно по 3 попытки.", reply_markup=main_kb())

@dp.message(F.text == "🔮 Гадание")
async def fortune_handler(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (message.from_user.id,)) as c:
            user = await c.fetchone()
    
    if user['limits_ai'] <= 0:
        return await message.answer("Твои лимиты гаданий на сегодня исчерпаны. Заходи завтра!")

    try:
        response = await ai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Ты - мудрый Оракул. Отвечай кратко (2-3 предложения), эмпатично и позитивно. Категорически запрещено: смерть, 18+, болезни."},
                {"role": "user", "content": f"Пользователь {user['name']}, {user['age']} лет. Дай предсказание."}
            ]
        )
        prediction = response.choices[0].message.content
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET limits_ai = limits_ai - 1 WHERE user_id = ?", (user['user_id'],))
            await db.execute("INSERT INTO fortune_history (user_id, prediction) VALUES (?,?)", (user['user_id'], prediction))
            await db.commit()
            
        await message.answer(f"📜 **Твое предсказание:**\n\n{prediction}", parse_mode="Markdown")
    except Exception:
        await message.answer("Звезды скрыты туманом... (Ошибка связи с ИИ)")

@dp.message(F.text == "🤝 Найти пару")
async def dating_handler(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (uid,)) as c:
            user = await c.fetchone()

    # Логика мягкого бонуса
    if user['limits_search'] <= 0:
        if user['bonus_claimed'] == 0:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET limits_search = 1, bonus_claimed = 1 WHERE user_id = ?", (uid,))
                await db.commit()
            await message.answer("Твоя энергия на нуле, но я дарю тебе +1 бонусный шанс! ✨")
            # Продолжаем поиск...
        else:
            return await message.answer("Лимиты исчерпаны. Попробуй завтра или повысь уровень!")

    gender = user['gender']
    age = user['age']
    target_gender = "female" if gender == "male" else "male"

    # Удаление из очереди если был
    if uid in queue[gender]: queue[gender].remove(uid)

    # Ищем партнера
    for peer_id in queue[target_gender]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT age FROM users WHERE user_id = ?", (peer_id,)) as c:
                peer_age = (await c.fetchone())[0]
        
        # Условия возраста (М: сверстницы, Ж: до +5 лет)
        match = False
        if gender == "male" and peer_age <= age: match = True
        if gender == "female" and peer_age <= age + 5: match = True

        if match:
            queue[target_gender].remove(peer_id)
            active_chats[uid] = peer_id
            active_chats[peer_id] = uid
            await state.set_state(ChatStates.in_chat)
            await dp.fsm.get_context(bot, peer_id, peer_id).set_state(ChatStates.in_chat)
            
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET limits_search = limits_search - 1 WHERE user_id = ?", (uid,))
                await db.commit()
                
            await bot.send_message(peer_id, "🤝 Партнер найден! Теперь вы можете общаться анонимно. /stop - выйти.")
            return await message.answer("🤝 Партнер найден! Общайтесь. /stop - завершить.")

    queue[gender].append(uid)
    await message.answer("Ищу того, кто предначертан тебе судьбой... (Ожидай)")

@dp.message(ChatStates.in_chat)
async def chatting(message: types.Message, state: FSMContext):
    if message.text == "/stop":
        uid = message.from_user.id
        partner_id = active_chats.pop(uid, None)
        if partner_id:
            active_chats.pop(partner_id, None)
            await state.clear()
            await dp.fsm.get_context(bot, partner_id, partner_id).clear()
            await bot.send_message(partner_id, "Собеседник покинул чат. /start для поиска.")
        return await message.answer("Чат завершен.", reply_markup=main_kb())
    
    # Пересылка сообщения партнеру
    partner_id = active_chats.get(message.from_user.id)
    if partner_id:
        try:
            await bot.send_message(partner_id, f"💬 {message.text}")
        except:
            await message.answer("Собеседник недоступен.")

@dp.message(F.text == "👤 Профиль")
async def profile_handler(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (message.from_user.id,)) as c:
            u = await c.fetchone()
    
    text = (f"👤 **{u['name']}, {u['age']} лет**\n"
            f"🔮 Лимиты гаданий: {u['limits_ai']}\n"
            f"🤝 Лимиты поиска: {u['limits_search']}\n"
            f"🏅 Твой уровень: {u['level']}")
    await message.answer(text, parse_mode="Markdown")

async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
