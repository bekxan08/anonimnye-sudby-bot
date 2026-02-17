import aiosqlite
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import DB_PATH, bot

chat_router = Router()

# Состояния для чата
class ChatStates(StatesGroup):
    in_chat = State()

# Очереди (в памяти, пока бот запущен)
queue = {"male": [], "female": []}
active_chats = {} # Словарь вида {user_id: partner_id}

@chat_router.message(F.text == "🤝 Найти пару")
async def find_pair(message: types.Message, state: FSMContext):
    from config import ADMIN_ID
    uid = message.from_user.id
    from database import get_user_data
    u = await get_user_data(uid)

    # АДМИНУ МОЖНО ВСЕГДА
    if uid != ADMIN_ID and u['limits_search'] <= 0:
        if u['bonus_given'] == 0:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET limits_search = 1, bonus_given = 1 WHERE user_id = ?", (uid,))
                await db.commit()
            await message.answer("✨ Энергия на нуле, но Оракул дарит тебе +1 поиск!")
        else:
            return await message.answer("Лимиты исчерпаны.")

    # ... (далее идет логика поиска без изменений) ...

    # В КОНЦЕ, где списывается лимит:
    if match:
        # ... (логика соединения пары) ...
        
        # СПИСЫВАЕМ ЛИМИТ ТОЛЬКО У ОБЫЧНЫХ ПОЛЬЗОВАТЕЛЕЙ
        if uid != ADMIN_ID:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET limits_search = limits_search - 1 WHERE user_id = ?", (uid,))
                await db.commit()

    if u['limits_search'] <= 0:
        if u['bonus_given'] == 0:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET limits_search = 1, bonus_given = 1 WHERE user_id = ?", (uid,))
                await db.commit()
            await message.answer("✨ Энергия на нуле, но Оракул дарит тебе +1 поиск!")
        else:
            return await message.answer("Лимиты исчерпаны. Приходи завтра или загляни в 💎 Магазин.")

    # Определяем, кого ищем
    my_gender = u['gender']
    target_gender = "female" if my_gender == "male" else "male"
    
    # Убираем из очереди, если юзер уже там был (защита от дублей)
    if uid in queue[my_gender]: queue[my_gender].remove(uid)

    # Ищем подходящего партнера в очереди
    for p_id in queue[target_gender]:
        from database import get_user_data
        partner = await get_user_data(p_id)
        
        # Логика подбора (можно усложнить)
        match = False
        if my_gender == "male" and partner['age'] <= u['age']: match = True
        if my_gender == "female" and partner['age'] <= u['age'] + 5: match = True

        if match:
            queue[target_gender].remove(p_id)
            active_chats[uid] = p_id
            active_chats[p_id] = uid
            
            await state.set_state(ChatStates.in_chat)
            # Устанавливаем состояние партнеру
            from config import dp
            partner_state = dp.fsm.get_context(bot, p_id, p_id)
            await partner_state.set_state(ChatStates.in_chat)
            
            # Списываем лимит
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET limits_search = limits_search - 1 WHERE user_id = ?", (uid,))
                await db.commit()
            
            await bot.send_message(p_id, "🤝 Собеседник найден! Напиши 'Привет'.\nЧтобы выйти, нажми /stop")
            return await message.answer("🤝 Пара найдена! Общайтесь анонимно.\nЧтобы выйти, нажми /stop")

    # Если никого не нашли, встаем в очередь
    queue[my_gender].append(uid)
    await message.answer("🔍 Ищу того, кто тебе предначертан... Как только пара найдется, я напишу!")

@chat_router.message(ChatStates.in_chat)
async def handle_anonymous_chat(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    partner_id = active_chats.get(uid)

    if message.text == "/stop":
        if partner_id:
            active_chats.pop(uid, None)
            active_chats.pop(partner_id, None)
            
            await state.clear()
            from config import dp
            await dp.fsm.get_context(bot, partner_id, partner_id).clear()
            
            from users import main_kb
            await bot.send_message(partner_id, "😔 Собеседник покинул чат.", reply_markup=main_kb())
        
        from users import main_kb
        return await message.answer("Вы вышли из чата.", reply_markup=main_kb())

    # Пересылка сообщения
    if partner_id:
        try:
            # Можно добавить фильтр мата здесь
            if message.text:
                await bot.send_message(partner_id, f"💬 {message.text}")
            elif message.sticker:
                await bot.send_sticker(partner_id, message.sticker.file_id)

# ... (внутри handle_anonymous_chat после пересылки сообщения) ...
    if partner_id:
        try:
            if message.text:
                await bot.send_message(partner_id, f"💬 {message.text}")
                # НАЧИСЛЯЕМ ОПЫТ ЗА ОБЩЕНИЕ
                from database import add_exp
                await add_exp(uid, 2) 
# ...
            # И так далее для фото/голосовых
        except Exception:
            await message.answer("⚠️ Не удалось отправить сообщение.")
