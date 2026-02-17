import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID, bot
from database import users_col, add_exp  # Импортируем коллекцию и функцию опыта

admin_router = Router()

class AdminStates(StatesGroup):
    mail = State()
    give_exp_id = State()
    give_exp_amount = State()

def admin_kb():
    return types.ReplyKeyboardMarkup(keyboard=[
        [types.KeyboardButton(text="📊 Статистика"), types.KeyboardButton(text="📢 Рассылка")],
        [types.KeyboardButton(text="🎁 Выдать опыт"), types.KeyboardButton(text="🔄 Обновить лимиты")],
        [types.KeyboardButton(text="🏠 Меню")]
    ], resize_keyboard=True)

@admin_router.message(Command("admin"))
async def admin(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🔧 **Панель управления (Cloud DB)**", reply_markup=admin_kb(), parse_mode="Markdown")

# --- СТАТИСТИКА (MongoDB) ---
@admin_router.message(F.text == "📊 Статистика")
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    # В MongoDB просто считаем документы в коллекции
    count = await users_col.count_documents({})
    await message.answer(f"📈 **Всего юзеров в базе:** {count}", parse_mode="Markdown")

# --- РАССЫЛКА (MongoDB) ---
@admin_router.message(F.text == "📢 Рассылка")
async def mail(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Введите текст рассылки:")
    await state.set_state(AdminStates.mail)

@admin_router.message(AdminStates.mail)
async def mail_run(message: types.Message, state: FSMContext):
    await state.clear()
    # Получаем все ID пользователей
    cursor = users_col.find({}, {"user_id": 1})
    users = await cursor.to_list(length=None)
    
    count = 0
    for u in users:
        try:
            await bot.send_message(u['user_id'], message.text)
            count += 1
            await asyncio.sleep(0.05)
        except: continue
    await message.answer(f"✅ Выполнено! Сообщение получили {count} пользователей.")

# --- ВЫДАЧА ОПЫТА (MongoDB) ---
@admin_router.message(F.text == "🎁 Выдать опыт")
async def give_exp_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Введите ID пользователя:")
    await state.set_state(AdminStates.give_exp_id)

@admin_router.message(AdminStates.give_exp_id)
async def give_exp_id_step(message: types.Message, state: FSMContext):
    await state.update_data(target_id=int(message.text))
    await message.answer("Сколько опыта добавить?")
    await state.set_state(AdminStates.give_exp_amount)

@admin_router.message(AdminStates.give_exp_amount)
async def give_exp_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    amount = int(message.text)
    await add_exp(data['target_id'], amount)
    await message.answer(f"✅ Начислено {amount} EXP пользователю {data['target_id']}")
    await state.clear()

# --- СБРОС ЛИМИТОВ ДЛЯ ВСЕХ (MongoDB) ---
@admin_router.message(F.text == "🔄 Обновить лимиты")
async def reset_limits(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    # Массовое обновление всех документов
    await users_col.update_many({}, {"$set": {"limits_ai": 3, "limits_search": 3}})
    await message.answer("⚡️ Лимиты всех пользователей сброшены до 3!")