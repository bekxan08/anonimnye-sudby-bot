import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Добавляем колонку exp (опыт), если таблица создается с нуля
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, 
            name TEXT, 
            age INTEGER, 
            gender TEXT,
            limits_search INTEGER DEFAULT 3, 
            limits_ai INTEGER DEFAULT 3,
            bonus_given INTEGER DEFAULT 0, 
            level TEXT DEFAULT 'Новичок',
            exp INTEGER DEFAULT 0)""")
        await db.commit()

async def get_user_data(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as c:
            return await c.fetchone()

# Новая функция для добавления опыта
async def add_exp(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        # Прибавляем опыт
        await db.execute("UPDATE users SET exp = exp + ? WHERE user_id = ?", (amount, user_id))
        
        # Автоматическое обновление ранга на основе опыта
        # 0-50: Новичок, 51-150: Путник, 151-400: Мастер, 401+: Магистр
        await db.execute("""
            UPDATE users SET level = CASE 
                WHEN exp < 50 THEN 'Новичок'
                WHEN exp < 150 THEN 'Путник'
                WHEN exp < 400 THEN 'Мастер'
                ELSE 'Магистр'
            END WHERE user_id = ?
        """, (user_id,))
        await db.commit()