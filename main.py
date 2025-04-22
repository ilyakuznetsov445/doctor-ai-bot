import asyncio
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
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

bot = Bot(token=bot_token)
dp = Dispatcher()

user_names = {}

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

def fetch_all_content():
    ws = sh.worksheet("content")
    return ws.get_all_records()

def match_keywords(text, data):
    for row in data:
        keywords = row.get("keywords", "")
        if keywords:
            for keyword in keywords.lower().split(","):
                if keyword.strip() in text.lower():
                    return row
    return None

def get_by_command(command, data):
    for row in data:
        if row.get("command", "") == command:
            return row
    return None

def build_keyboard(texts, commands):
    if not texts or not commands:
        return None
    btn_texts = [x.strip() for x in texts.split(",")]
    btn_cmds = [x.strip() for x in commands.split(",")]
    if len(btn_texts) != len(btn_cmds):
        return None
    buttons = [
        [InlineKeyboardButton(text=t, callback_data=c)]
        for t, c in zip(btn_texts, btn_cmds)
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    user_names.pop(user_id, None)
    log_action(message.from_user, "/start")
    await message.answer("👋 Привет! Я — Доктор Ай-бот. Как я могу к вам обращаться?")

@dp.message(Command("reset"))
async def reset(message: Message):
    user_id = message.from_user.id
    user_names.pop(user_id, None)
    log_action(message.from_user, "/reset")
    await message.answer("Хорошо, давай начнём заново. Как я могу к вам обращаться?")

@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    data = fetch_all_content()

    if user_id not in user_names:
        user_names[user_id] = text
        log_action(message.from_user, "set_name")
        row = get_by_command("greeting", data)
        reply = row.get("response_text", "Приятно познакомиться, {name}!").replace("{name}", text)
        await message.answer(reply)
        return

    row = match_keywords(text, data)
    if not row:
        await message.answer("Я вас слушаю, но не совсем понял, о чём вы. Попробуйте иначе или напишите /reset.")
        return

    log_action(message.from_user, f"msg:{row.get('command')}")
    reply = row.get("response_text", "")
    media_url = row.get("media_url", "").strip()
    keyboard = build_keyboard(row.get("button_texts", ""), row.get("button_commands", ""))

    if media_url:
        if media_url.endswith(('.jpg', '.jpeg', '.png')):
            await message.answer_photo(media_url, caption=reply, reply_markup=keyboard)
        elif media_url.endswith('.mp4'):
            await message.answer_video(media_url, caption=reply, reply_markup=keyboard)
        elif media_url.endswith('.gif'):
            await message.answer_animation(media_url, caption=reply, reply_markup=keyboard)
        elif media_url.endswith('.ogg'):
            await message.answer_voice(media_url, caption=reply, reply_markup=keyboard)
        else:
            await message.answer(reply, reply_markup=keyboard)
    else:
        await message.answer(reply, reply_markup=keyboard)

@dp.callback_query(F.data)
async def handle_callback(callback: types.CallbackQuery):
    data = fetch_all_content()
    row = get_by_command(callback.data, data)
    if not row:
        await callback.answer("Команда не найдена", show_alert=True)
        return

    reply = row.get("response_text", "")
    media_url = row.get("media_url", "").strip()
    keyboard = build_keyboard(row.get("button_texts", ""), row.get("button_commands", ""))

    log_action(callback.from_user, f"btn:{callback.data}")

    if media_url:
        if media_url.endswith(('.jpg', '.jpeg', '.png')):
            await callback.message.answer_photo(media_url, caption=reply, reply_markup=keyboard)
        elif media_url.endswith('.mp4'):
            await callback.message.answer_video(media_url, caption=reply, reply_markup=keyboard)
        elif media_url.endswith('.gif'):
            await callback.message.answer_animation(media_url, caption=reply, reply_markup=keyboard)
        elif media_url.endswith('.ogg'):
            await callback.message.answer_voice(media_url, caption=reply, reply_markup=keyboard)
        else:
            await callback.message.answer(reply, reply_markup=keyboard)
    else:
        await callback.message.answer(reply, reply_markup=keyboard)

    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
