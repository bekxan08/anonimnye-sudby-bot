import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.environ.get('8301617429:AAGGSpBGwCKQpgavoNUMiqkVdV1HCqeGzwo')
ADMIN_ID = 7587800410  # ВСТАВЬ СВОЙ ID
DB_PATH = "bot_data.db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())