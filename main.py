import asyncio
from flask import Flask
from threading import Thread
from config import bot, dp
from database import init_db
from users import user_router
from admin import admin_router
from chat import chat_router

# Важен порядок: сначала админ, потом юзер
dp.include_router(admin_router)
dp.include_router(user_router)
dp.include_router(chat_router)

app = Flask('')

@app.route('/')
def home():
    return "Бот работает 24/7"

def run():
    app.run(host='0.0.0.0', port=8080)

async def start():
    # Инициализация базы данных
    await init_db()
    
    # Запуск Flask в отдельном потоке для Keep-Alive
    Thread(target=run).start()
    
    print("✅ Бот и все его модули запущены!")
    
    # Удаляем вебхуки и запускаем лонг-поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(start())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")