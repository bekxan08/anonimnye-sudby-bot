from aiogram import Router, F, types
from aiogram.types import LabeledPrice, PreCheckoutQuery
from config import bot
from database import users_col, add_exp

pay_router = Router()

# Цены и описание товаров
PRICES = {
    "ai_10": {"stars": 50, "amount": 10, "label": "🔮 10 Гаданий", "type": "ai"},
    "ai_50": {"stars": 200, "amount": 50, "label": "🔮 50 Гаданий", "type": "ai"},
    "search_30": {"stars": 100, "amount": 30, "label": "🤝 30 Поисков пары", "type": "search"},
    "exp_200": {"stars": 150, "amount": 200, "label": "✨ +200 Опыта", "type": "exp"},
    "vip": {"stars": 500, "amount": 999, "label": "💎 VIP Статус", "type": "vip"},
}

@pay_router.message(F.text == "💎 Магазин")
async def show_shop(message: types.Message):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔮 10 Гаданий (50 ⭐️)", callback_data="buy_ai_10")],
        [types.InlineKeyboardButton(text="🔮 50 Гаданий (200 ⭐️)", callback_data="buy_ai_50")],
        [types.InlineKeyboardButton(text="🤝 30 Поисков (100 ⭐️)", callback_data="buy_search_30")],
        [types.InlineKeyboardButton(text="✨ +200 Опыта (150 ⭐️)", callback_data="buy_exp_200")],
        [types.InlineKeyboardButton(text="👑 VIP Доступ (500 ⭐️)", callback_data="buy_vip")],
        [types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="to_main")]
    ])
    
    await message.answer(
        "✨ **Магическая Лавка Оракула**\n\nВыбери товар для усиления своих способностей:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@pay_router.callback_query(F.data.startswith("buy_"))
async def create_invoice(call: types.CallbackQuery):
    item_id = call.data.replace("buy_", "")
    item = PRICES.get(item_id)
    
    if not item: return

    await bot.send_invoice(
        chat_id=call.from_user.id,
        title=item["label"],
        description=f"Покупка: {item['label']}",
        payload=f"pay_{item_id}",
        currency="XTR",
        prices=[LabeledPrice(label="Оплата", amount=item["stars"])],
        provider_token="" # Для Stars всегда пусто
    )
    await call.answer()

@pay_router.pre_checkout_query()
async def process_pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

# --- НАЧИСЛЕНИЕ ПОСЛЕ ОПЛАТЫ ---

@pay_router.message(F.successful_payment)
async def success_pay(message: types.Message):
    # Достаем ID товара из payload
    payload = message.successful_payment.invoice_payload.replace("pay_", "")
    uid = message.from_user.id
    item = PRICES.get(payload)
    
    if not item: return

    if item["type"] == "ai":
        await users_col.update_one({"user_id": uid}, {"$inc": {"limits_ai": item["amount"]}})
        text = f"Начислено {item['amount']} гаданий!"
        
    elif item["type"] == "search":
        await users_col.update_one({"user_id": uid}, {"$inc": {"limits_search": item["amount"]}})
        text = f"Начислено {item['amount']} поисков!"
        
    elif item["type"] == "exp":
        await add_exp(uid, item["amount"]) # Используем твою функцию с проверкой уровней
        text = f"Начислено {item['amount']} опыта! Проверь свой уровень в профиле."
        
    elif item["type"] == "vip":
        await users_col.update_one(
            {"user_id": uid}, 
            {"$set": {"limits_ai": 999, "limits_search": 999, "level": "👑 VIP"}}
        )
        text = "Тебе присвоен статус VIP! Все лимиты увеличены."

    await message.answer(f"✅ **Оплата прошла успешно!**\n{text}", parse_mode="Markdown")