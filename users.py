from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
from config import DB_PATH

user_router = Router()

class RegStates(StatesGroup):
    name = State(); age = State(); gender = State()

@user_router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    # Логика проверки регистрации и начало опроса
    pass

@user_router.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    # Отображение данных из БД
    pass