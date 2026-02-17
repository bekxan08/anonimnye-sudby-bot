import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Берем ссылку из Secrets Replit
MONGO_URL = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(MONGO_URL)
db = client.oracle_bot
users_col = db.users

async def init_db():
    try:
        # Проверяем соединение с облаком
        await client.admin.command('ping')
        print("✅ Подключено к MongoDB Atlas")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

async def get_user_data(user_id):
    return await users_col.find_one({"user_id": user_id})

async def add_exp(user_id, amount):
    # Сначала добавляем опыт прямо в базе через $inc
    await users_col.update_one(
        {"user_id": user_id},
        {"$inc": {"exp": amount}}
    )
    
    # Теперь проверяем, не пора ли повысить уровень
    user = await users_col.find_one({"user_id": user_id})
    if not user: return
    
    new_exp = user.get('exp', 0)
    
    # Логика уровней
    if new_exp < 50: level = 'Новичок'
    elif new_exp < 150: level = 'Путник'
    elif new_exp < 400: level = 'Мастер'
    else: level = 'Магистр'
    
    # Обновляем уровень, если он изменился
    if user.get('level') != level:
        await users_col.update_one(
            {"user_id": user_id},
            {"$set": {"level": level}}
        )