from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import bot, ADMIN_ID
from database import users_col, get_user_data, add_exp

chat_router = Router()

# Состояния для чата
class ChatStates(StatesGroup):
    in_chat = State()

# Очереди остаются в оперативной памяти для скорости работы
queue = {"male": [], "female": []}
active_chats = {} # Словарь вида {user_id: partner_id}

@chat_router.message(F.text == "🤝 Найти пару")
async def find_pair(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    u = await get_user_data(uid)
    
    if not u:
        return await message.answer("Сначала пройди регистрацию в профиле!")

    # Проверка лимитов (Админу — безлимит)
    if uid != ADMIN_ID and u.get('limits_search', 0) <= 0:
        return await message.answer("Лимиты поисков исчерпаны. Приходи завтра или загляни в 💎 Магазин.")

    # Определяем параметры поиска
    my_gender = u['gender']
    target_gender = "female" if my_gender == "male" else "male"
    
    # Защита от дублей в очереди
    if uid in queue[my_gender]: 
        queue[my_gender].remove(uid)

    # Ищем партнера в очереди (логика подбора)
    for p_id in queue[target_gender]:
        partner = await get_user_data(p_id)
        if not partner: continue
        
        # Условие подбора (разница в возрасте не более 10 лет)
        if abs(u['age'] - partner['age']) <= 10:
            queue[target_gender].remove(p_id)
            active_chats[uid] = p_id
            active_chats[p_id] = uid
            
            # Устанавливаем состояния
            await state.set_state(ChatStates.in_chat)
            from config import dp
            p_state = dp.fsm.get_context(bot, p_id, p_id)
            await p_state.set_state(ChatStates.in_chat)
            
            # Списываем лимит в MongoDB (если не админ)
            if uid != ADMIN_ID:
                await users_col.update_one({"user_id": uid}, {"$inc": {"limits_search": -1}})
            
            await bot.send_message(p_id, "🤝 Собеседник найден! Напиши 'Привет'.\nЧтобы выйти, нажми /stop")
            return await message.answer("🤝 Пара найдена! Общайтесь анонимно.\nЧтобы выйти, нажми /stop")

    # Если никого не нашли, встаем в очередь
    if uid not in queue[my_gender]:
        queue[my_gender].append(uid)
    await message.answer("🔍 Ищу того, кто тебе предначертан... Как только пара найдется, я напишу!")

@chat_router.message(ChatStates.in_chat)
async def handle_anonymous_chat(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    partner_id = active_chats.get(uid)

    # Команда выхода из чата
    if message.text == "/stop":
        if partner_id:
            active_chats.pop(uid, None)
            active_chats.pop(partner_id, None)
            
            from users import main_kb
            await state.clear()
            from config import dp
            await dp.fsm.get_context(bot, partner_id, partner_id).clear()
            
            await bot.send_message(partner_id, "😔 Собеседник покинул чат.", reply_markup=main_kb())
        
        from users import main_kb
        return await message.answer("Вы вышли из чата.", reply_markup=main_kb())

    # Пересылка сообщений
    if partner_id:
        try:
            # Начисляем 2 опыта за каждое сообщение (через MongoDB)
            await add_exp(uid, 2)
            
            if message.text:
                await bot.send_message(partner_id, f"💬 {message.text}")
            elif message.sticker:
                await bot.send_sticker(partner_id, message.sticker.file_id)
            elif message.photo:
                await bot.send_photo(partner_id, message.photo[-1].file_id)
            elif message.voice:
                await bot.send_voice(partner_id, message.voice.file_id)
            elif message.video_note:
                await bot.send_video_note(partner_id, message.video_note.file_id)
                
        except Exception:
            await message.answer("⚠️ Не удалось отправить сообщение. Возможно, собеседник заблокировал бота.")