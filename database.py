import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Строку подключения засунем в Secrets как MONGO_URL
MONGO_URL = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(MONGO_URL)
db = client.oracle_bot
users_col = db.users

async def init_db():
    # В MongoDB таблицы (коллекции) создаются автоматически
    print("Подключено к MongoDB Atlas")

async def get_user_data(user_id):
    return await users_col.find_one({"user_id": user_id})

async def add_exp(user_id, amount):
    user = await users_col.find_one({"user_id": user_id})
    if not user: return
    
    new_exp = user.get('exp', 0) + amount
    
    # Логика уровней
    if new_exp < 50: level = 'Новичок'
    elif new_exp < 150: level = 'Путник'
    elif new_exp < 400: level = 'Мастер'
    else: level = 'Магистр'
    
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"exp": new_exp, "level": level}}
    )