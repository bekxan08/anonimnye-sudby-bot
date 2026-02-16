# main.py — Анонимные Судьбы (Telegram-бот с гаданиями, анонимными чатами, премиум и рефералкой)
import asyncio
import random
import time
import re
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.utils.deep_linking import create_start_link, decode_payload
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Конфиг ─────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN") or "8301617429:AAHmuvl58b_955W_TUr_djCdRrkw5FqoM6Y"
OPENROUTER_KEY = os.getenv("sk-42497cd88eef43c7907fa4a777ba2264") or None
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "7587800410").split(",") if i.strip().isdigit()]

client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_KEY)
MODEL = "deepseek/deepseek-r1-0528:free"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Хранилища (для теста — словари; в продакшене → redis)
users = {}                  # uid → dict (age, gender, seeking, pseudo, ...)
active_chats = {}           # uid → partner_uid
search_queue = []           # список uid в очереди
premium_users = {}          # uid → {"plan": "lunar", "expires": ts}
violations = {}             # uid → count
daily_attempts = {}         # uid:date → count
daily_fortunes = {}         # uid:date → count
ref_tree = {}               # uid → {"level1": [ids], "level2": [...], "level3": [...]}
ref_earnings = {}           # uid → stars_commission

# ─── Тарифы ─────────────────────────────────────────────────────────
PREMIUM_PLANS = {
    "free":  {"search_limit": 4,  "fortune_limit": 5,  "allow_contacts": False},
    "lunar": {"search_limit": 10, "fortune_limit": 15, "allow_contacts": True},
    "star":  {"search_limit": 20, "fortune_limit": 30, "allow_contacts": True},
    "fate":  {"search_limit": 999,"fortune_limit": 999,"allow_contacts": True},
}

# ─── Запрещённый контент ────────────────────────────────────────────
FORBIDDEN_PATTERNS = [
    r'\+?\d{9,15}', r'@\w{5,}',
    r'(?:https?://)?(?:www\.)?(?:instagram\.com|vk\.com|tiktok\.com|wa\.me)/[\w.-]+',
]

def is_contact_or_link(text: str) -> bool:
    return any(re.search(p, text, re.I) for p in FORBIDDEN_PATTERNS)

# ─── Состояния ──────────────────────────────────────────────────────
class ProfileForm(StatesGroup):
    age     = State()
    gender  = State()
    seeking = State()

class FindSoul(StatesGroup):
    pseudo = State()

# ─── Вспомогательные функции ────────────────────────────────────────
def get_today_str():
    return datetime.now().date().isoformat()

def is_premium(uid: int) -> bool:
    if uid not in premium_users:
        return False
    return premium_users[uid].get("expires", 0) > time.time()

def get_plan(uid: int) -> dict:
    plan_key = premium_users.get(uid, {}).get("plan", "free")
    return PREMIUM_PLANS.get(plan_key, PREMIUM_PLANS["free"])

# ─── Старт и профиль ────────────────────────────────────────────────
@dp.message(CommandStart(deep_link=True))
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, command: CommandObject = None):
    uid = message.from_user.id
    if uid not in users:
        users[uid] = {"age": None, "gender": None, "seeking": None, "pseudo": None}

    # Реферал
    if command and command.args:
        payload = decode_payload(command.args)
        if payload.isdigit() and int(payload) != uid:
            users[uid]["invited_by"] = int(payload)

    if not users[uid].get("age"):
        await message.answer("🌙 Добро пожаловать!\nСколько тебе лет?")
        await state.set_state(ProfileForm.age)
        return

    await message.answer(f"Привет! Готов искать судьбу? /find ✨")

@dp.message(ProfileForm.age)
async def process_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
        if 13 <= age <= 99:
            users[message.from_user.id]["age"] = age
            await message.answer("Твой пол?\nМ — мужчина\nЖ — женщина\nД — другой")
            await state.set_state(ProfileForm.gender)
        else:
            await message.answer("Возраст от 13 до 99")
    except:
        await message.answer("Напиши число")

@dp.message(ProfileForm.gender)
async def process_gender(message: types.Message, state: FSMContext):
    g = message.text.strip().upper()
    if g in ("М", "Ж", "Д"):
        users[message.from_user.id]["gender"] = g
        await message.answer("Кого ищешь?\nМ — парня\nЖ — девушку\nД — без разницы")
        await state.set_state(ProfileForm.seeking)
    else:
        await message.answer("М / Ж / Д")

@dp.message(ProfileForm.seeking)
async def process_seeking(message: types.Message, state: FSMContext):
    s = message.text.strip().upper()
    if s in ("М", "Ж", "Д"):
        users[message.from_user.id]["seeking"] = s
        users[message.from_user.id]["pseudo"] = message.from_user.first_name or "Странник"
        await message.answer("Профиль готов! /find ✨")
        await state.clear()
    else:
        await message.answer("М / Ж / Д")

# ─── Поиск пары ─────────────────────────────────────────────────────
@dp.message(Command("find"))
async def cmd_find(message: types.Message):
    uid = message.from_user.id
    if uid not in users or not users[uid].get("pseudo"):
        await message.answer("Сначала заполни профиль — /start")
        return

    plan = get_plan(uid)
    used = daily_attempts.get(f"{uid}:{get_today_str()}", 0)

    if used >= plan["search_limit"]:
        texts = [
            f"Сегодня ты использовал {used}/{plan['search_limit']} попыток… Судьба ждёт, но лимит закрыт 🌑\n"
            "Хочешь больше? Лунный тариф — 10 поисков в день за ~200 Stars\n/premium ✨",

            f"Лимит на сегодня исчерпан ({used}/{plan['search_limit']}).\n"
            "Но где-то кто-то думает о тебе… /premium — продолжим поиск вместе 💫"
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("Посмотреть тарифы", callback_data="show_premium")]
        ])
        await message.answer(random.choice(texts), reply_markup=kb)
        return

    daily_attempts[f"{uid}:{get_today_str()}"] = used + 1

    search_queue.append(uid)
    await message.answer("Ищу тебе пару... 🔍")

    if len(search_queue) >= 2:
        u1 = search_queue.pop(0)
        u2 = search_queue.pop(0)
        active_chats[u1] = u2
        active_chats[u2] = u1
        p1 = users[u1]["pseudo"]
        p2 = users[u2]["pseudo"]
        await bot.send_message(u1, f"{p1} встретил(а) {p2} 🌙\nЧат открыт!")
        await bot.send_message(u2, f"{p2} встретил(а) {p1} 🌙\nЧат открыт!")

# ─── Пересылка сообщений ────────────────────────────────────────────
@dp.message()
async def relay(message: types.Message):
    uid = message.from_user.id
    if uid not in active_chats:
        return

    partner = active_chats[uid]
    text = message.text

    plan = get_plan(uid)
    if not plan["allow_contacts"] and is_contact_or_link(text):
        await message.delete()
        await message.answer(
            "🌙 На бесплатном тарифе обмен номерами и @username скрыт.\n"
            "Хочешь свободно делиться контактами? Подними тариф → /premium ✨"
        )
        return

    pseudo = users[uid]["pseudo"]
    await bot.send_message(partner, f"[{pseudo}]: {text}")

# ─── Выход из чата ──────────────────────────────────────────────────
@dp.message(Command("stop"))
async def cmd_stop(message: types.Message):
    uid = message.from_user.id
    if uid in active_chats:
        partner = active_chats.pop(uid)
        active_chats.pop(partner, None)
        await message.answer("Чат завершён. /find чтобы начать новый.")
        await bot.send_message(partner, "Собеседник ушёл... Чат закрыт.")
    else:
        await message.answer("Ты не в чате.")

# ─── Премиум — каталог ──────────────────────────────────────────────
@dp.message(Command("premium"))
async def cmd_premium(message: types.Message):
    uid = message.from_user.id
    plan_key = premium_users.get(uid, {}).get("plan", "free")
    expires = premium_users.get(uid, {}).get("expires", 0)
    expires_str = datetime.fromtimestamp(expires).strftime('%d.%m.%Y') if expires else "—"

    text = (
        f"✨ Твой тариф: **{plan_key.capitalize()}** до {expires_str}\n\n"
        "Выбери уровень:\n\n"
    )

    for key, p in PREMIUM_PLANS.items():
        text += f"**{p['name']}** — {p['price_stars']} Stars\n{p['description']}\n\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Купить Лунный 🌙", callback_data="buy:lunar")],
        [InlineKeyboardButton("Купить Звёздный ⭐", callback_data="buy:star")],
        [InlineKeyboardButton("Купить Судьбоносный ✨", callback_data="buy:fate")],
    ])

    await message.answer(text, reply_markup=kb)

# ─── Покупка премиум ────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data.startswith("buy:"))
async def process_buy(callback: types.CallbackQuery):
    plan_key = callback.data.split(":")[1]
    plan = PREMIUM_PLANS.get(plan_key)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"{plan['name']} — 30 дней",
        description=plan["description"],
        payload=f"premium_{plan_key}_{callback.from_user.id}_{int(time.time())}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=plan["name"], amount=plan["price_stars"])],
    )

@dp.message(lambda m: m.successful_payment)
async def successful_payment(message: types.Message):
    uid = message.from_user.id
    payload = message.successful_payment.invoice_payload
    if not payload.startswith("premium_"):
        return

    _, plan_key, _, _ = payload.split("_")
    expires = int(time.time()) + 86400 * 30
    premium_users[uid] = {"plan": plan_key, "expires": expires}

    await message.answer(
        f"✨ Спасибо! Тариф **{PREMIUM_PLANS[plan_key]['name']}** активирован до "
        f"{datetime.fromtimestamp(expires).strftime('%d.%m.%Y')}\n"
        "Теперь у тебя больше возможностей ✨"
    )

# ─── Запуск ─────────────────────────────────────────────────────────
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
