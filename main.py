import asyncio
from flask import Flask
from threading import Thread
from config import bot, dp
from database import init_db
from users import user_router
from admin import admin_router
from payment import pay_router

# Регистрация модулей
dp.include_router(user_router)
dp.include_router(admin_router)
dp.include_router(pay_router)

app = Flask('')
@app.route('/')
def home(): return "Online"
def run(): app.run(host='0.0.0.0', port=8080)

async def start():
    await init_db()
    Thread(target=run).start()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start())