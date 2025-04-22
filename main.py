import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import CommandStart
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
gc = gspread.service_account_from_dict(service_account_info)
sh = gc.open_by_key(sheet_id)

# Бот
bot = Bot(token=bot_token)
dp = Dispatcher()

user_names = {}

def get_response(command):
    try:
        ws = sh.worksheet("content")
        data = ws.get_all_records()
        for row in data:
            if row["command"] == command:
                return row["response_text"]
        return "🛠 Ответ не найден. Обратитесь к врачу, или к разработчику :)"
    except Exception as e:
        return f"Ошибка при получении ответа: {e}"

def log_action(user: types.User, command: str):
    try:
        log_ws = sh.worksheet("logs")
        log_ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user.id,
            user_names.get(user.id, ""),
            user.username or "",
            command
        ])
    except Exception as e:
        logging.error(f"Ошибка при логировании: {e}")

@dp.message(CommandStart())
async def start(message: Message):
    log_action(message.from_user, "/start")
    response = get_response("start")
    await message.answer(response)

@dp.message()
async def catch_name(message: Message):
    user_names[message.from_user.id] = message.text.strip()
    log_action(message.from_user, "set_name")
    greeting = get_response("greeting")
    await message.answer(greeting.replace("{name}", message.text.strip()))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())