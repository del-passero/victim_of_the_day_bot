import logging
import os
import json
import random
import pytz
from datetime import datetime, timedelta

import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject
from aiogram.enums import ChatType
from dotenv import load_dotenv

import config

os.makedirs(config.DATA_DIR, exist_ok=True)

from phrases.victim_phrases import VICTIM_PHRASES

# ================== ИНИЦИАЛИЗАЦИЯ ====================
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    raise Exception("Укажите токен бота в .env (BOT_TOKEN=...)")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# =============== JSON-УТИЛИТЫ ==================
def load_json(file, default=None):
    if default is None:
        default = {}
    try:
        if not os.path.exists(file):
            return default
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Ошибка чтения {file}: {e}")
        return default

def save_json(file, data):
    try:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка записи {file}: {e}")

# =============== ВРЕМЯ ========================
def now_in_tz():
    tz = pytz.timezone(config.TIMEZONE)
    return datetime.now(tz)

def today_str():
    return now_in_tz().strftime("%Y-%m-%d")

def is_new_day(old_date):
    return old_date != today_str()

# =============== СТАТИСТИКА ===================
def increment_stat(chat_id, user_id):
    stats = load_json(config.STATS_FILE)
    chat_id = str(chat_id)
    user_id = str(user_id)
    if chat_id not in stats:
        stats[chat_id] = {}
    if user_id not in stats[chat_id]:
        stats[chat_id][user_id] = 0
    stats[chat_id][user_id] += 1
    save_json(config.STATS_FILE, stats)
    logging.info(f"Статистика: +1 попадание {user_id} в чате {chat_id}")

def get_stats_for_chat(chat_id):
    stats = load_json(config.STATS_FILE)
    return stats.get(str(chat_id), {})

# =============== УЧАСТНИКИ И ПРОЯВЛЕНИЕ ================
def get_users(chat_id):
    data = load_json(config.USERS_FILE)
    return data.get(str(chat_id), [])

def set_users(chat_id, users):
    data = load_json(config.USERS_FILE)
    data[str(chat_id)] = users
    save_json(config.USERS_FILE, data)
    logging.info(f"Проявленные пользователи чата {chat_id}: {users}")

def add_user(chat_id, user_id):
    users = get_users(chat_id)
    if user_id not in users:
        users.append(user_id)
        set_users(chat_id, users)

@dp.message(lambda msg: msg.chat.type in [ChatType.SUPERGROUP, ChatType.GROUP] and not (msg.text and msg.text.startswith('/')))
async def mark_user_as_active(message: types.Message):
    add_user(message.chat.id, message.from_user.id)

# --------------------- КАСТОМНЫЕ ФРАЗЫ ---------------------
def get_custom_phrases(chat_id):
    data = load_json(config.CUSTOM_PHRASES_FILE, default={})
    return data.get(str(chat_id), [])

def add_custom_phrase(chat_id, phrase):
    data = load_json(config.CUSTOM_PHRASES_FILE, default={})
    arr = data.get(str(chat_id), [])
    arr.append(phrase)
    data[str(chat_id)] = arr
    save_json(config.CUSTOM_PHRASES_FILE, data)
    logging.info(f"Добавлена фраза: {phrase} в чате {chat_id}")

def del_custom_phrase(chat_id, idx):
    data = load_json(config.CUSTOM_PHRASES_FILE, default={})
    arr = data.get(str(chat_id), [])
    if 0 <= idx < len(arr):
        removed = arr.pop(idx)
        data[str(chat_id)] = arr
        save_json(config.CUSTOM_PHRASES_FILE, data)
        logging.info(f"Удалена фраза: {removed} из чата {chat_id}")
        return True
    return False

def get_all_phrases(chat_id):
    return VICTIM_PHRASES + get_custom_phrases(chat_id)

# =============== НАСТРОЙКИ ============================
def get_settings(chat_id):
    data = load_json(config.SETTINGS_FILE)
    return data.get(str(chat_id), {})

def set_setting(chat_id, key, value):
    data = load_json(config.SETTINGS_FILE)
    chat_settings = data.get(str(chat_id), {})
    chat_settings[key] = value
    data[str(chat_id)] = chat_settings
    save_json(config.SETTINGS_FILE, data)

def get_setting(chat_id, key, default=None):
    settings = get_settings(chat_id)
    return settings.get(key, default)

def get_limit_for_chat(chat_id):
    return config.DAILY_LIMIT_PER_CHAT

# ========== УНИВЕРСАЛЬНЫЙ ПАРСЕР ====================
async def extract_user_id(message: types.Message):
    if message.reply_to_message:
        return message.reply_to_message.from_user.id
    return None

async def get_user_mention(chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        user = member.user
        if user.username:
            return f"@{user.username}"
        elif user.full_name:
            return user.full_name
        else:
            return f"User {user_id}"
    except Exception:
        return f"User {user_id}"

# ============= ОБРАБОТЧИКИ КОМАНД ========================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.reply(config.WELCOME_GROUP_MESSAGE.format(limit=get_limit_for_chat(message.chat.id)))

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.reply(config.HELP_MESSAGE, parse_mode="HTML")

@dp.message(Command("add_phrase"))
async def add_phrase_cmd(message: types.Message, command: CommandObject):
    if not command.args:
        await message.reply("Используй: /add_phrase текст фразы")
        return
    add_custom_phrase(message.chat.id, command.args.strip())
    await message.reply("Фраза добавлена!")

@dp.message(Command("del_phrase"))
async def del_phrase_cmd(message: types.Message, command: CommandObject):
    try:
        idx = int(command.args.strip())
        ok = del_custom_phrase(message.chat.id, idx)
        if ok:
            await message.reply("Фраза удалена.")
        else:
            await message.reply("Нет такой фразы.")
    except Exception:
        await message.reply("Укажи номер фразы: /del_phrase номер")

@dp.message(Command("list_phrases"))
async def list_phrases_cmd(message: types.Message):
    phrases = get_custom_phrases(message.chat.id)
    if not phrases:
        await message.reply("Пользовательские фразы отсутствуют.")
        return
    txt = "<b>Пользовательские фразы:</b>\n"
    for i, s in enumerate(phrases):
        txt += f"{i}. {s}\n"
    await message.reply(txt, parse_mode="HTML")

@dp.message(Command("statistics"))
async def statistics_cmd(message: types.Message):
    stats = get_stats_for_chat(message.chat.id)
    if not stats:
        await message.reply("Пока никто не был жертвой дня в этом чате.")
        return
    rows = []
    for user_id, count in sorted(stats.items(), key=lambda x: -x[1]):
        mention = await get_user_mention(message.chat.id, int(user_id))
        rows.append(f"{mention} — <b>{count}</b>")
    table = "\n".join(f"{i+1}. {row}" for i, row in enumerate(rows))
    await message.reply(f"<b>Статистика жертв дня:</b>\n\n{table}", parse_mode="HTML")

# ============== КОМАНДА /victim ====================
@dp.message(Command("victim"))
async def victim_cmd(message: types.Message):
    # Получить список проявленных пользователей
    users = get_users(message.chat.id)
    if len(users) < config.MIN_MEMBERS_TO_PICK:
        await message.reply(f"Недостаточно участников для жеребьёвки (нужно хотя бы {config.MIN_MEMBERS_TO_PICK}).")
        return

    # Проверка лимита по дням
    settings = get_settings(message.chat.id)
    today = today_str()
    limit = get_limit_for_chat(message.chat.id)
    last_run_date = settings.get("last_run_date", "")
    runs_today = settings.get("runs_today", 0)
    if last_run_date != today:
        runs_today = 0
    if runs_today >= limit:
        await message.reply(f"Сегодня лимит жеребьёвок исчерпан! ({limit}) Попробуйте снова завтра.")
        return

    # Выбираем жертву
    victim_id = random.choice(users)
    mention = await get_user_mention(message.chat.id, victim_id)
    is_self = victim_id == message.from_user.id

    # Сообщение жеребьёвки (с "самоистязанием" если self)
    phrases = get_all_phrases(message.chat.id)
    phrase = random.choice(phrases) if phrases else "{mention} — жертва дня!"
    if is_self:
        msg = f"Кажется сегодня кто-то займется самоистязанием!\n\n" + phrase.format(mention=mention)
    else:
        msg = phrase.format(mention=mention)
    await message.reply(msg, parse_mode="HTML")

    # Сохраняем дату и счётчик запусков
    set_setting(message.chat.id, "last_run_date", today)
    set_setting(message.chat.id, "runs_today", runs_today + 1)
    increment_stat(message.chat.id, victim_id)

# ========== АВТО-ЗАПУСК ПО ПРОСТОЮ ==================
import asyncio

async def autorun_scheduler():
    while True:
        all_settings = load_json(config.SETTINGS_FILE)
        tz = pytz.timezone(config.TIMEZONE)
        now = now_in_tz()
        for chat_id, settings in all_settings.items():
            last_run_date = settings.get("last_run_date", "")
            runs_today = settings.get("runs_today", 0)
            limit = get_limit_for_chat(chat_id)
            users = get_users(chat_id)
            if len(users) < config.MIN_MEMBERS_TO_PICK:
                continue

            # Сравниваем даты с учетом таймзоны
            should_run = False
            if not last_run_date:
                should_run = True
            else:
                try:
                    last_dt = tz.localize(datetime.strptime(last_run_date, "%Y-%m-%d"))
                    delta = (now - last_dt).total_seconds()
                    should_run = delta >= 86400
                except Exception as e:
                    logging.error(f"Ошибка сравнения времени для чата {chat_id}: {e}")
                    should_run = False

            if should_run:
                # Проверка: не превышен ли лимит за сегодня
                if last_run_date != today_str():
                    runs_today = 0
                if runs_today < limit:
                    victim_id = random.choice(users)
                    mention = await get_user_mention(chat_id, victim_id)
                    phrases = get_all_phrases(chat_id)
                    phrase = random.choice(phrases) if phrases else "{mention} — жертва дня!"
                    msg = f"{config.AUTO_RUN_MESSAGE}\n\n{phrase.format(mention=mention)}"
                    await bot.send_message(chat_id, msg, parse_mode="HTML")
                    set_setting(chat_id, "last_run_date", today_str())
                    set_setting(chat_id, "runs_today", runs_today + 1)
                    increment_stat(chat_id, victim_id)
        await asyncio.sleep(600)  # Проверять каждые 10 минут

# ========== УСТАНОВКА КОМАНД БОТА ===================
async def set_bot_commands(bot: Bot):
    await bot.set_my_commands([
        types.BotCommand(command=cmd["command"], description=cmd["description"])
        for cmd in config.COMMANDS
    ])
    logging.info("Команды бота установлены")

# ========== ЗАПУСК ===================
if __name__ == "__main__":
    import asyncio

    async def main():
        await set_bot_commands(bot)
        asyncio.create_task(autorun_scheduler())
        logging.info("Бот стартует!")
        await dp.start_polling(bot)

    asyncio.run(main())
