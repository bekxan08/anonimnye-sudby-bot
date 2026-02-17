from aiogram import Router, F, types
pay_router = Router()

@pay_router.message(F.text == "💎 Магазин")
async def shop(message: types.Message):
    await message.answer("🛒 **Магазин Звезд**\n\n1. 10 гаданий — 99₽\n2. Безлимитный поиск — 199₽\n\n*(Оплата временно недоступна)*")