from aiogram import Router, F, types
from aiogram.filters import Command
from config import ADMIN_ID, bot
import aiosqlite

admin_router = Router()

@admin_router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    # Кнопки админа
    pass

@admin_router.message(F.text == "📊 Статистика")
async def stats(message: types.Message):
    # Запрос к БД
    pass