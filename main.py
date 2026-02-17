import asyncio
from flask import Flask
from threading import Thread
from config import bot, dp
from database import init_db
from users import user_router
from admin import admin_router
from payment import pay_router
from chat import chat_router  # ИМПОРТ НОВОГО МОДУЛЯ

# Регистрация всех модулей
dp.include_router(user_router)
dp.include_router(admin_router)
dp.include_router(pay_router)
dp.include_router(chat_router) # ПОДКЛЮЧЕНИЕ ЧАТА

app = Flask('')
@app.route('/')
def home(): return "Бот работает"
def run(): app.run(host='0.0.0.0', port=8080)

async def start():
    await init_db()
    Thread(target=run).start()
    print("Бот и все его модули запущены!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start())