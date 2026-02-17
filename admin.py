import asyncio, aiosqlite
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID, DB_PATH, bot

admin_router = Router()
class AdminStates(StatesGroup): mail = State()

def admin_kb():
    return types.ReplyKeyboardMarkup(keyboard=[
        [types.KeyboardButton(text="📊 Статистика"), types.KeyboardButton(text="📢 Рассылка")],
        [types.KeyboardButton(text="🏠 Меню")]
    ], resize_keyboard=True)

@admin_router.message(Command("admin"))
async def admin(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🔧 Админка", reply_markup=admin_kb())

@admin_router.message(F.text == "📊 Статистика")
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            count = (await c.fetchone())[0]
    await message.answer(f"Всего юзеров: {count}")

@admin_router.message(F.text == "📢 Рассылка")
async def mail(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Текст рассылки:")
    await state.set_state(AdminStates.mail)

@admin_router.message(AdminStates.mail)
async def mail_run(message: types.Message, state: FSMContext):
    await state.clear()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            users = await cur.fetchall()
    for u in users:
        try:
            await bot.send_message(u[0], message.text)
            await asyncio.sleep(0.05)
        except: continue
    await message.answer("Выполнено!")