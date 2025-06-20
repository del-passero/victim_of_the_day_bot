import logging
import os
import json
import random
from datetime import datetime
import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject
from aiogram.enums import ChatType
from dotenv import load_dotenv
import config

# Убедимся, что директория data существует
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
    """Загрузить json-файл, вернуть default если файл пуст или не найден."""
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
    """Сохранить данные в json-файл."""
    try:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка записи {file}: {e}")

# =============== ВРЕМЯ ========================
def now_in_tz():
    """Текущее время в указанном часовом поясе."""
    tz = pytz.timezone(config.TIMEZONE)
    return datetime.now(tz)

# =============== СТАТИСТИКА ===================
def increment_stat(chat_id, user_id):
    """Добавить одно попадание в статистику."""
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
    """Получить статистику попаданий для чата."""
    stats = load_json(config.STATS_FILE)
    return stats.get(str(chat_id), {})

# =============== УЧАСТНИКИ И ПРОЯВЛЕНИЕ ================
def get_users(chat_id):
    """Список user_id проявленных пользователей в чате."""
    data = load_json(config.USERS_FILE)
    return data.get(str(chat_id), [])

def set_users(chat_id, users):
    """Сохранить список user_id для чата."""
    data = load_json(config.USERS_FILE)
    data[str(chat_id)] = users
    save_json(config.USERS_FILE, data)
    logging.info(f"Проявленные пользователи чата {chat_id}: {users}")

def add_user(chat_id, user_id):
    """Добавить user_id как проявленного пользователя."""
    users = get_users(chat_id)
    if user_id not in users:
        users.append(user_id)
        set_users(chat_id, users)

# ============= "Проявление" (универсальный обработчик) ============
@dp.message(lambda msg: msg.chat.type in [ChatType.SUPERGROUP, ChatType.GROUP] and not (msg.text and msg.text.startswith('/')))
async def mark_user_as_active(message: types.Message):
    add_user(message.chat.id, message.from_user.id)

# ============= КАСТОМНЫЕ ФРАЗЫ (ПО ЧАТАМ) ======================
def get_custom_phrases(chat_id):
    """Получить список пользовательских фраз для конкретного чата."""
    data = load_json(config.CUSTOM_PHRASES_FILE, default={})
    return data.get(str(chat_id), [])

def add_custom_phrase(chat_id, phrase):
    """Добавить новую фразу в конкретный чат."""
    data = load_json(config.CUSTOM_PHRASES_FILE, default={})
    arr = data.get(str(chat_id), [])
    arr.append(phrase)
    data[str(chat_id)] = arr
    save_json(config.CUSTOM_PHRASES_FILE, data)
    logging.info(f"Добавлена фраза: {phrase} в чате {chat_id}")

def del_custom_phrase(chat_id, idx):
    """Удалить фразу по индексу в конкретном чате."""
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
    """Получить полный список фраз для чата (стандартные + пользовательские)."""
    return VICTIM_PHRASES + get_custom_phrases(chat_id)

# =============== ИСКЛЮЧЁННЫЕ ==========================
def get_excluded(chat_id):
    data = load_json(config.EXCLUDE_FILE)
    return data.get(str(chat_id), [])

def add_excluded(chat_id, user_id):
    data = load_json(config.EXCLUDE_FILE)
    chat_excl = data.get(str(chat_id), [])
    if user_id not in chat_excl:
        chat_excl.append(user_id)
        data[str(chat_id)] = chat_excl
        save_json(config.EXCLUDE_FILE, data)
        logging.info(f"Исключён {user_id} из жеребьёвки в чате {chat_id}")

def del_excluded(chat_id, user_id):
    data = load_json(config.EXCLUDE_FILE)
    chat_excl = data.get(str(chat_id), [])
    if user_id in chat_excl:
        chat_excl.remove(user_id)
        data[str(chat_id)] = chat_excl
        save_json(config.EXCLUDE_FILE, data)
        logging.info(f"Вернул {user_id} в жеребьёвку чата {chat_id}")

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
    logging.info(f"Настройка {key}={value} для чата {chat_id}")

def get_setting(chat_id, key, default=None):
    settings = get_settings(chat_id)
    return settings.get(key, default)

# =============== АВТО-ЗАПУСК ===========================
def get_autorun():
    data = load_json(config.AUTORUN_FILE, default={})
    return data.get("auto_run_days", config.AUTO_RUN_DAYS)

def set_autorun(days):
    data = load_json(config.AUTORUN_FILE, default={})
    data["auto_run_days"] = days
    save_json(config.AUTORUN_FILE, data)
    logging.info(f"Параметр auto_run_days изменён на {days}")

def get_limit_for_chat(chat_id):
    s = get_settings(chat_id)
    return s.get("daily_limit", config.DAILY_LIMIT_PER_CHAT)

def get_auto_run_days():
    return get_autorun()

# ========== УНИВЕРСАЛЬНЫЙ ПАРСЕР ====================
async def extract_user_id(message: types.Message):
    # 1. Reply
    if message.reply_to_message:
        return message.reply_to_message.from_user.id
    # 2. text_mention
    if message.entities:
        for entity in message.entities:
            if entity.type == "text_mention":
                return entity.user.id
    # 3. @username (mention)
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                username = message.text[entity.offset+1:entity.offset+entity.length]
                try:
                    member = await message.bot.get_chat_member(message.chat.id, username)
                    return member.user.id
                except Exception:
                    continue
    # 4. user_id в аргументах
    args = message.text.split()
    for arg in args[1:]:
        if arg.isdigit():
            return int(arg)
    return None

async def get_user_mention(chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        user = member.user
        if user.username:
            return f"@{user.username}"
        elif user.full_name:
            return f"{user.full_name}"
        else:
            return f"User {user_id}"
    except Exception:
        return f"User {user_id}"

# ============= ОБРАБОТЧИКИ КОМАНД ========================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    logging.info(f"/start вызвал {message.from_user.id} в чате {message.chat.id}")
    await message.reply(config.WELCOME_GROUP_MESSAGE.format(limit=get_limit_for_chat(message.chat.id)))

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.reply(config.HELP_MESSAGE, parse_mode="HTML")

@dp.message(Command("set_limit"))
async def set_limit_cmd(message: types.Message, command: CommandObject):
    try:
        if not command.args:
            curr = get_limit_for_chat(message.chat.id)
            await message.reply(f"Текущий лимит: {curr} раз(а) в сутки.")
            return
        n = int(command.args.strip())
        assert 1 <= n <= 100
        set_setting(message.chat.id, "daily_limit", n)
        await message.reply(f"Лимит жеребьёвок теперь: {n} раз(а) в сутки.")
    except Exception:
        await message.reply("Пример: /set_limit 2 (целое число от 1 до 100)")

@dp.message(Command("set_autorun"))
async def set_autorun_cmd(message: types.Message, command: CommandObject):
    try:
        if not command.args:
            await message.reply(f"Текущий срок автозапуска: {get_auto_run_days()} дней.")
            return
        n = int(command.args.strip())
        assert 1 <= n <= 30
        set_autorun(n)
        await message.reply(f"Срок автозапуска теперь: {n} дней.")
    except Exception:
        await message.reply("Пример: /set_autorun 3 (целое число от 1 до 30)")

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
        await message.reply("Пользовательские фразы не добавлены.")
        return
    txt = "<b>Пользовательские фразы:</b>\n"
    for i, s in enumerate(phrases):
        txt += f"{i}. {s}\n"
    await message.reply(txt, parse_mode="HTML")

@dp.message(Command("exclude"))
async def exclude_cmd(message: types.Message):
    user_id = await extract_user_id(message)
    if not user_id:
        await message.reply("Ответьте на сообщение участника, которого хотите исключить или укажите @username.")
        return
    excl = get_excluded(message.chat.id)
    users = get_users(message.chat.id)
    non_excl = [uid for uid in users if uid not in excl and uid != user_id]
    if len(non_excl) < config.MIN_MEMBERS_TO_PICK:
        await message.reply(f"Нельзя исключить, иначе останется слишком мало кандидатов!")
        return
    add_excluded(message.chat.id, user_id)
    await message.reply("Участник исключён из жеребьёвки.")

@dp.message(Command("include"))
async def include_cmd(message: types.Message):
    user_id = await extract_user_id(message)
    if not user_id:
        await message.reply("Ответьте на сообщение участника, которого хотите включить или укажите @username.")
        return
    del_excluded(message.chat.id, user_id)
    await message.reply("Участник возвращён в жеребьёвку.")

@dp.message(Command("list_excluded"))
async def list_excluded_cmd(message: types.Message):
    excl = get_excluded(message.chat.id)
    if not excl:
        await message.reply("Список исключённых пуст.")
        return
    mentions = []
    for uid in excl:
        mention = await get_user_mention(message.chat.id, uid)
        mentions.append(mention)
    await message.reply("Исключены: " + ", ".join(mentions), parse_mode="HTML")

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
    logging.info(f"/victim вызвал {message.from_user.id} в чате {message.chat.id}")
    users = get_users(message.chat.id)
    exclude_ids = get_excluded(message.chat.id)
    candidates = [uid for uid in users if uid not in exclude_ids]
    if len(candidates) < config.MIN_MEMBERS_TO_PICK:
        await message.reply(f"Недостаточно участников для жеребьёвки (нужно хотя бы {config.MIN_MEMBERS_TO_PICK}).")
        return

    # Проверка лимита по дням
    settings = get_settings(message.chat.id)
    today = now_in_tz().strftime("%Y-%m-%d")
    limit = get_limit_for_chat(message.chat.id)
    last_run_date = settings.get("last_run_date", "")
    runs_today = settings.get("runs_today", 0)
    if last_run_date == today and runs_today >= limit:
        await message.reply(f"Сегодня лимит жеребьёвок исчерпан! ({limit}) Попробуйте снова завтра.")
        return

    victim_id = random.choice(candidates)
    mention = await get_user_mention(message.chat.id, victim_id)
    is_self = victim_id == message.from_user.id

    phrases = get_all_phrases(message.chat.id)
    phrase = random.choice(phrases)
    if is_self:
        msg = f"Кажется сегодня кто-то займется самоистязанием!\n\n" + phrase.format(mention=mention)
    else:
        msg = phrase.format(mention=mention)
    await message.reply(msg, parse_mode="HTML")
    logging.info(f"Выбрана жертва дня: {victim_id} ({mention})")

    if last_run_date != today:
        runs_today = 1
    else:
        runs_today += 1
    set_setting(message.chat.id, "last_run_date", today)
    set_setting(message.chat.id, "runs_today", runs_today)

    increment_stat(message.chat.id, victim_id)

# ========== АВТО-ЗАПУСК ПО ПРОСТОЮ ==================
import asyncio

async def autorun_scheduler():
    """Периодически запускает жеребьёвку, если не было команд больше N дней."""
    while True:
        all_settings = load_json(config.SETTINGS_FILE)
        for chat_id, settings in all_settings.items():
            last_run_date = settings.get("last_run_date")
            if not last_run_date:
                continue
            last = datetime.strptime(last_run_date, "%Y-%m-%d")
            now = now_in_tz()
            days_idle = (now.date() - last.date()).days
            days_max = get_auto_run_days()
            if days_idle >= days_max:
                users = get_users(chat_id)
                exclude_ids = get_excluded(chat_id)
                candidates = [uid for uid in users if uid not in exclude_ids]
                if len(candidates) >= config.MIN_MEMBERS_TO_PICK:
                    victim_id = random.choice(candidates)
                    mention = await get_user_mention(chat_id, victim_id)
                    phrases = get_all_phrases(chat_id)
                    phrase = random.choice(phrases)
                    msg = f"{config.AUTO_RUN_MESSAGE}\n\n{phrase.format(mention=mention)}"
                    await bot.send_message(chat_id, msg, parse_mode="HTML")
                    set_setting(chat_id, "last_run_date", now.strftime("%Y-%m-%d"))
                    set_setting(chat_id, "runs_today", 1)
                    increment_stat(chat_id, victim_id)
        await asyncio.sleep(3600)  # Проверять раз в час

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
