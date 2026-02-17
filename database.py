import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(MONGO_URL)
db = client.oracle_bot
users_col = db.users

async def init_db():
    try:
        await client.admin.command('ping')
        print("✅ Подключено к MongoDB Atlas")
    except Exception as e:
        print(f"❌ Ошибка подключения к базе: {e}")

async def get_user_data(user_id):
    return await users_col.find_one({"user_id": user_id})

async def add_exp(user_id, amount):
    # Принудительно приводим к int, чтобы не сломать математику профиля
    await users_col.update_one(
        {"user_id": user_id},
        {"$inc": {"exp": int(amount)}}
    )
    
    user = await users_col.find_one({"user_id": user_id})
    if not user: return
    
    e = user.get('exp', 0)
    if e < 50: level = 'Новичок'
    elif e < 150: level = 'Путник'
    elif e < 400: level = 'Мастер'
    else: level = 'Магистр'
    
    if user.get('level') != level:
        await users_col.update_one({"user_id": user_id}, {"$set": {"level": level}})