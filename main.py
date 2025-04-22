import asyncio
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import gspread
from datetime import datetime
import logging

# Переменные окружения
bot_token = os.getenv("BOT_TOKEN")
sheet_id = os.getenv("SHEET_ID")
service_account_info = json.loads(os.getenv("GOOGLE_CREDS"))

# Логгирование
logging.basicConfig(level=logging.INFO)

# Google Sheets
gc = gspread.service_account_from_dict(service_account_info)
sh = gc.open_by_key(sheet_id)
try:
    appointments_ws = sh.worksheet("appointments")
except:
    appointments_ws = sh.add_worksheet(title="appointments", rows="100", cols="10")
    appointments_ws.append_row(["timestamp", "user_id", "name", "date", "time", "symptoms"])

# FSM for step-by-step recording
class AppointmentForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_symptoms = State()

bot = Bot(token=bot_token)
dp = Dispatcher(storage=MemoryStorage())
user_names = {}

def log_appointment(user_id, name, date, time, symptoms):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    appointments_ws.append_row([timestamp, user_id, name, date, time, symptoms])

@dp.message(CommandStart())
async def start(message: Message):
    user_names.pop(message.from_user.id, None)
    await message.answer("👋 Привет! Я — Доктор Ай-бот. Как я могу к вам обращаться?")

@dp.message(Command("appointment"))
async def start_appointment(message: Message, state: FSMContext):
    await state.set_state(AppointmentForm.waiting_for_name)
    await message.answer("Хорошо! Давайте запишемся. Как вас зовут?")

@dp.message(AppointmentForm.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AppointmentForm.waiting_for_date)
    await message.answer("Отлично. На какую дату хотите записаться? (например, 27.04.2025)")

@dp.message(AppointmentForm.waiting_for_date)
async def get_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text)
    await state.set_state(AppointmentForm.waiting_for_time)
    await message.answer("А во сколько удобно? (например, 15:00)")

@dp.message(AppointmentForm.waiting_for_time)
async def get_time(message: Message, state: FSMContext):
    await state.update_data(time=message.text)
    await state.set_state(AppointmentForm.waiting_for_symptoms)
    await message.answer("Напишите, пожалуйста, кратко жалобы или повод обращения")

@dp.message(AppointmentForm.waiting_for_symptoms)
async def get_symptoms(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("name")
    date = data.get("date")
    time = data.get("time")
    symptoms = message.text
    log_appointment(message.from_user.id, name, date, time, symptoms)
    await state.clear()
    await message.answer("✅ Вы записаны!
Спасибо, я передам информацию врачу. До встречи!")

@dp.message()
async def handle_message(message: Message):
    if "записаться" in message.text.lower():
        await start_appointment(message, state=dp.fsm.get_context(message))
    else:
        await message.answer("Я вас слушаю. Напишите /appointment, чтобы записаться на приём.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
