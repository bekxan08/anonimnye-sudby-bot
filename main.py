import asyncio
from config import bot, dp
from database import init_db
from users import user_router
from admin import admin_router
from payment import pay_router
from flask import Flask
from threading import Thread

# Подключаем все модули (роутеры)
dp.include_router(user_router)
dp.include_router(admin_router)
dp.include_router(pay_router)

# Flask для Uptime
app = Flask('')
@app.route('/')
def home(): return "Бот работает"
def run(): app.run(host='0.0.0.0', port=8080)

async def main():
    await init_db()
    Thread(target=run).start() # Keep alive
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())