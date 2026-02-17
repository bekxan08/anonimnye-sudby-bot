from aiogram import Router, F, types
from aiogram.types import LabeledPrice, PreCheckoutQuery
from config import bot
from database import users_col

pay_router = Router()

# Расширенный прайс-лист
PRICES = {
    # Гадания
    "ai_10": {"stars": 50, "amount": 10, "label": "🔮 10 Гаданий", "type": "ai"},
    "ai_50": {"stars": 190, "amount": 50, "label": "🔮 50 Гаданий (Скидка!)", "type": "ai"},
    
    # Поиски пары
    "search_20": {"stars": 60, "amount": 20, "label": "🤝 20 Поисков", "type": "search"},
    "search_100": {"stars": 250, "amount": 100, "label": "🤝 100 Поисков (Выгода!)", "type": "search"},
    
    # Опыт и Уровни
    "exp_100": {"stars": 100, "amount": 100, "label": "✨ +100 Опыта", "type": "exp"},
    "vip_pack": {"stars": 500, "amount": 999, "label": "💎 VIP Набор (Все по 999)", "type": "vip"},
}

@pay_router.message(F.text == "💎 Магазин")
async def show_shop(message: types.Message):
    # Создаем клавиатуру с категориями
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔮 10 Гаданий (50 ⭐️)", callback_data="buy_ai_10")],
        [types.InlineKeyboardButton(text="🔮 50 Гаданий (190 ⭐️)", callback_data="buy_ai_50")],
        [types.InlineKeyboardButton(text="🤝 20 Поисков (60 ⭐️)", callback_data="buy_search_20")],
        [types.InlineKeyboardButton(text="🤝 100 Поисков (250 ⭐️)", callback_data="buy_search_100")],
        [types.InlineKeyboardButton(text="✨ +100 Опыта (100 ⭐️)", callback_data="buy_exp_100")],
        [types.InlineKeyboardButton(text="💎 VIP Набор (500 ⭐️)", callback_data="buy_vip_pack")],
        [types.InlineKeyboardButton(text="🏠 В меню", callback_data="to_main")]
    ])
    
    await message.answer(
        "🔮 **Магическая Лавка Оракула**\n\nВыберите артефакт для усиления ваших способностей. Оплата производится через Telegram Stars.",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@pay_router.callback_query(F.data.startswith("buy_"))
async def create_invoice(callback: types.CallbackQuery):
    # Достаем ключ товара (например, ai_10 или vip_pack)
    item_key = callback.data.replace("buy_", "")
    item = PRICES.get(item_key)

    if not item:
        return await callback.answer("Товар не найден.")

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=item["label"],
        description=f"Приобретение: {item['label']}",
        payload=f"pay_{item_key}",
        provider_token="", # Для Stars пусто
        currency="XTR",
        prices=[LabeledPrice(label=item["label"], amount=item["stars"])]
    )
    await callback.answer()

@pay_router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Обработка успешной оплаты
@pay_router.message(F.successful_payment)
async def success_pay(message: types.Message):
    payload = message.successful_payment.invoice_payload.replace("pay_", "")
    uid = message.from_user.id
    item = PRICES.get(payload)
    
    if not item: return

    # Логика начисления в зависимости от типа товара
    if item["type"] == "ai":
        await users_col.update_one({"user_id": uid}, {"$inc": {"limits_ai": item["amount"]}})
        res_text = f"Начислено {item['amount']} гаданий!"
        
    elif item["type"] == "search":
        await users_col.update_one({"user_id": uid}, {"$inc": {"limits_search": item["amount"]}})
        res_text = f"Начислено {item['amount']} поисков!"
        
    elif item["type"] == "exp":
        from database import add_exp # Используем твою функцию из database.py
        await add_exp(uid, item["amount"])
        res_text = f"Начислено {item['amount']} единиц опыта!"
        
    elif item["type"] == "vip":
        await users_col.update_one(
            {"user_id": uid}, 
            {"$set": {"limits_ai": 999, "limits_search": 999, "level": "👑 VIP"}}
        )
        res_text = "Вы получили статус VIP и полные лимиты!"

    await message.answer(f"✅ **Успешно!**\n{res_text}", parse_mode="Markdown")