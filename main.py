import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import CommandStart
from gspread_asyncio import AsyncioGspreadClientManager
import gspread
import json
from datetime import datetime
import logging

# Настройки
with open("config.json", "r") as f:
    config = json.load(f)

bot_token = config["BOT_TOKEN"]
sheet_id = config["SHEET_ID"]
service_account_info = config["SERVICE_ACCOUNT"]

# Логгирование
logging.basicConfig(level=logging.INFO)

# Google Sheets авторизация
def get_creds():
    return service_account_info

agcm = AsyncioGspreadClientManager(get_creds)

# Бот
bot = Bot(token=bot_token)
dp = Dispatcher()

user_names = {}

async def get_response(command):
    agc = await agcm.authorize()
    sh = await agc.open_by_key(sheet_id)
    ws = await sh.worksheet("content")
    data = await ws.get_all_records()
    for row in data:
        if row["command"] == command:
            return row["response_text"]
    return "🛠 Ответ не найден. Обратитесь к врачу, или к разработчику :)"

async def log_action(user: types.User, command: str):
    agc = await agcm.authorize()
    sh = await agc.open_by_key(sheet_id)
    log_ws = await sh.worksheet("logs")
    await log_ws.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user.id,
        user_names.get(user.id, ""),
        user.username or "",
        command
    ])

@dp.message(CommandStart())
async def start(message: Message):
    await log_action(message.from_user, "/start")
    response = await get_response("start")
    await message.answer(response)

@dp.message()
async def catch_name(message: Message):
    user_names[message.from_user.id] = message.text.strip()
    await log_action(message.from_user, "set_name")
    greeting = await get_response("greeting")
    await message.answer(greeting.replace("{name}", message.text.strip()))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())