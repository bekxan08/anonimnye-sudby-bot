from aiogram import Router, F, types
from aiogram.types import LabeledPrice, PreCheckoutQuery
from config import bot
from database import users_col

shop_router = Router()

# Цены в Telegram Stars
PRICES = {
    "ai_10": {"stars": 50, "label": "🔮 10 Гаданий"},
    "ai_50": {"stars": 200, "label": "🔮 50 Гаданий (Скидка!)"},
    "search_20": {"stars": 70, "label": "🤝 20 Поисков"},
    "exp_100": {"stars": 100, "label": "✨ +100 Опыта"},
    "vip": {"stars": 500, "label": "💎 VIP Статус (Full)"}
}

@shop_router.message(F.text == "💎 Магазин")
async def show_shop(message: types.Message):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔮 10 Гаданий (50 ⭐️)", callback_data="buy_ai_10")],
        [types.InlineKeyboardButton(text="🔮 50 Гаданий (200 ⭐️)", callback_data="buy_ai_50")],
        [types.InlineKeyboardButton(text="🤝 20 Поисков (70 ⭐️)", callback_data="buy_search_20")],
        [types.InlineKeyboardButton(text="✨ +100 Опыта (100 ⭐️)", callback_data="buy_exp_100")],
        [types.InlineKeyboardButton(text="👑 VIP Доступ (500 ⭐️)", callback_data="buy_vip")],
        [types.InlineKeyboardButton(text="🏠 Назад", callback_data="to_main")]
    ])
    
    await message.answer("🛍 **Магическая Лавка**\nВыбери товар для усиления:", reply_markup=kb)

@shop_router.callback_query(F.data.startswith("buy_"))
async def create_invoice(call: types.CallbackQuery):
    item_id = call.data.replace("buy_", "")
    item = PRICES.get(item_id)
    
    await bot.send_invoice(
        call.from_user.id,
        title=item["label"],
        description="Пополнение магических сил",
        payload=f"pay_{item_id}",
        currency="XTR",
        prices=[LabeledPrice(label="Оплата", amount=item["stars"])],
        provider_token=""
    )
    await call.answer()