import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, name TEXT, age INTEGER, gender TEXT,
            limits_search INTEGER DEFAULT 3, limits_ai INTEGER DEFAULT 3,
            bonus_given INTEGER DEFAULT 0, level TEXT DEFAULT 'Путник')""")
        await db.commit()

async def get_user_data(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as c:
            return await c.fetchone()