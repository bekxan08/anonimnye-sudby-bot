from aiogram import Router, F, types
from aiogram.types import LabeledPrice, PreCheckoutQuery
import aiosqlite
from config import bot, DB_PATH

pay_router = Router()

# Цены (1 звезда ≈ 2 рубля в среднем)
PRICES = {
    "small_ai": {"stars": 50, "amount": 10, "label": "10 Гаданий"},
    "big_search": {"stars": 150, "amount": 50, "label": "50 Поисков пары"},
}

@pay_router.message(F.text == "💎 Магазин")
async def show_shop(message: types.Message):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔮 +10 Гаданий (50 ⭐️)", callback_data="buy_ai")],
        [types.InlineKeyboardButton(text="🤝 +50 Поисков (150 ⭐️)", callback_data="buy_search")]
    ])
    
    await message.answer(
        "✨ **Магическая лавка**\n\nЗдесь ты можешь восполнить свою энергию моментально за Telegram Stars.",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@pay_router.callback_query(F.data.startswith("buy_"))
async def create_invoice(callback: types.CallbackQuery):
    action = callback.data.split("_")[1]
    
    if action == "ai":
        item = PRICES["small_ai"]
    else:
        item = PRICES["big_search"]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=item["label"],
        description=f"Пополнение баланса: {item['label']}",
        payload=f"pay_{action}",
        provider_token="", # Для Telegram Stars токен не нужен (оставляем пустым)
        currency="XTR",    # Код валюты для Telegram Stars
        prices=[LabeledPrice(label=item["label"], amount=item["stars"])]
    )
    await callback.answer()

# Подтверждение платежа (обязательный шаг)
@pay_router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Успешная оплата
@pay_router.message(F.successful_payment)
async def success_pay(message: types.Message):
    payload = message.successful_payment.invoice_payload
    uid = message.from_user.id
    
    async with aiosqlite.connect(DB_PATH) as db:
        if payload == "pay_ai":
            await db.execute("UPDATE users SET limits_ai = limits_ai + 10 WHERE user_id = ?", (uid,))
            text = "🔮 +10 Гаданий начислено! Твой взор стал яснее."
        elif payload == "pay_search":
            await db.execute("UPDATE users SET limits_search = limits_search + 50 WHERE user_id = ?", (uid,))
            text = "🤝 +50 Поисков начислено! Твоя половинка где-то рядом."
        
        await db.commit()
    
    await message.answer(f"✅ **Оплата прошла успешно!**\n{text}", parse_mode="Markdown")