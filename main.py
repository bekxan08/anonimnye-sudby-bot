# main.py — Анонимные Судьбы (минимальная версия для теста на Termux)
# 17 февраля 2026

import asyncio
import random
import time
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import AsyncOpenAI
import os

# ─── Конфиг (замени!) ──────────────────────────────────────────────
BOT_TOKEN = "8301617429:AAHmuvl58b_955W_TUr_djCdRrkw5FqoM6Y"
OPENROUTER_KEY =  "sk-42497cd88eef43c7907fa4a777ba2264"

client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=sk-42497cd88eef43c7907fa4a777ba2264)
MODEL = "deepseek/deepseek-r1-0528:free"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Временное хранилище (для теста вместо Redis)
users = {}          # uid → dict
active_chats = {}   # uid → partner_uid
search_queue = []

# ─── Состояния ─────────────────────────────────────────────────────
class ProfileForm(StatesGroup):
    age     = State()
    gender  = State()
    seeking = State()

class FindSoul(StatesGroup):
    pseudo = State()

# ─── Старт ─────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    if uid not in users:
        users[uid] = {"age": None, "gender": None, "seeking": None, "pseudo": None}

    if not users[uid].get("age"):
        await message.answer("🌙 Привет! Я — бот Анонимные Судьбы.\nСколько тебе лет?")
        await state.set_state(ProfileForm.age)
        return

    await message.answer(
        f"Привет, {users[uid].get('pseudo', 'странник')}! "
        "Готов искать пару? /find ✨"
    )

# ─── Заполнение профиля ────────────────────────────────────────────
@dp.message(ProfileForm.age)
async def process_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
        if 13 <= age <= 99:
            users[message.from_user.id]["age"] = age
            await message.answer("Отлично. Твой пол?\nМ — мужчина\nЖ — женщина\nД — другой")
            await state.set_state(ProfileForm.gender)
        else:
            await message.answer("Возраст от 13 до 99")
    except:
        await message.answer("Напиши число")

# ─── Дальше аналогично для gender и seeking ────────────────────────
# (добавь сам или попроси меня — это просто)

# ─── Поиск пары ────────────────────────────────────────────────────
@dp.message(Command("find"))
async def cmd_find(message: types.Message):
    uid = message.from_user.id
    if uid not in users or not users[uid].get("pseudo"):
        await message.answer("Сначала заполни профиль — /start")
        return

    if uid in active_chats:
        await message.answer("Ты уже в чате. /stop чтобы выйти")
        return

    search_queue.append(uid)
    await message.answer("Ищу тебе пару... 🔍")

    # Простой матчинг (для теста)
    if len(search_queue) >= 2:
        u1 = search_queue.pop(0)
        u2 = search_queue.pop(0)
        active_chats[u1] = u2
        active_chats[u2] = u1
        p1 = users[u1]["pseudo"]
        p2 = users[u2]["pseudo"]
        await bot.send_message(u1, f"{p1} встретил(а) {p2} 🌙 Чат открыт!")
        await bot.send_message(u2, f"{p2} встретил(а) {p1} 🌙 Чат открыт!")

# ─── Пересылка сообщений ───────────────────────────────────────────
@dp.message()
async def relay(message: types.Message):
    uid = message.from_user.id
    if uid not in active_chats:
        return

    partner = active_chats[uid]
    pseudo = users[uid]["pseudo"]
    await bot.send_message(partner, f"[{pseudo}]: {message.text}")

# ─── Запуск ────────────────────────────────────────────────────────
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
