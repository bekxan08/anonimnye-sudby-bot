from aiogram import Router, F, types
from config import bot

pay_router = Router()

@pay_router.message(F.text == "💎 Магазин")
async def shop(message: types.Message):
    # Офферы: 50 звезд - 100 рублей и т.д.
    pass