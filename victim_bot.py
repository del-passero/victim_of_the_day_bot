import logging
import os
import json
import random
from datetime import datetime, timedelta

import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject
from aiogram.enums import ChatType
from dotenv import load_dotenv

from telethon import TelegramClient
from telethon.errors.rpcerrorlist import UserIdInvalidError
from telethon.tl.types import ChannelParticipantCreator, ChannelParticipantAdmin

import config
from phrases.victim_phrases import VICTIM_PHRASES
from phrases.owner_phrases import OWNER_PHRASES
from phrases.only_owner_phrases import ONLY_OWNER_PHRASES

# ---- Инициализация ----
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
if not (API_TOKEN and API_ID and API_HASH):
    raise Exception("В .env должны быть BOT_TOKEN, API_ID, API_HASH")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Telethon для работы с участниками
telethon_client = TelegramClient("victim_bot.session", API_ID, API_HASH)

# ==== JSON utils ====

def load_json(file, default=None):
    if default is None:
        default = {}
    try:
        if not os.path.exists(file):
            return default
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def now_in_tz():
    tz = pytz.timezone(config.TIMEZONE)
    return datetime.now(tz)

# ==== Работа с участниками чата через Telethon ====

async def get_chat_owner_and_members(chat_id):
    """Вернёт (owner_id, список_юзеров) для чата через Telethon"""
    await telethon_client.connect()
    members = []
    owner_id = None
    async for p in telethon_client.iter_participants(chat_id):
        if not p.bot:
            members.append(p)
        if getattr(p, "is_creator", False) or isinstance(p.participant, ChannelParticipantCreator):
            owner_id = p.id
    # fallback: если не нашли owner, пробуем поискать admin с правом owner
    if not owner_id:
        async for p in telethon_client.iter_participants(chat_id):
            if getattr(p, "is_creator", False):
                owner_id = p.id
                break
    return owner_id, members

async def get_member_by_username(chat_id, username):
    """Получить участника чата по username через Telethon"""
    await telethon_client.connect()
    username = username.lstrip("@")
    async for user in telethon_client.iter_participants(chat_id, search=username):
        if user.username and user.username.lower() == username.lower():
            return user
    return None

async def get_user_html(user):
    """HTML-упоминание пользователя"""
    if user.username:
        return f"@{user.username}"
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return f'<a href="tg://user?id={user.id}">{name}</a>'

# ==== Универсальный парсер пользователя ====

async def extract_user_id(message: types.Message):
    if message.reply_to_message:
        return message.reply_to_message.from_user.id
    entities = message.entities or []
    for entity in entities:
        if entity.type == "mention":
            username = message.text[entity.offset+1:entity.offset+entity.length]
            member = await get_member_by_username(message.chat.id, username)
            if member:
                return member.id
        elif entity.type == "text_mention" and entity.user:
            return entity.user.id
    args = message.text.split()
    for arg in args[1:]:
        if arg.isdigit():
            return int(arg)
    return None

# ==== Статистика ====

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

def get_stats_for_chat(chat_id):
    stats = load_json(config.STATS_FILE)
    return stats.get(str(chat_id), {})

# ==== Trusted pickers ====

def get_trusted_pickers(chat_id):
    data = load_json(config.TRUSTED_PICKERS_FILE)
    return data.get(str(chat_id), [])

def set_trusted_pickers(chat_id, pickers):
    data = load_json(config.TRUSTED_PICKERS_FILE)
    data[str(chat_id)] = pickers
    save_json(config.TRUSTED_PICKERS_FILE, data)

def add_trusted_picker(chat_id, user_id):
    pickers = get_trusted_pickers(chat_id)
    if user_id not in pickers:
        pickers.append(user_id)
        set_trusted_pickers(chat_id, pickers)

def del_trusted_picker(chat_id, user_id):
    pickers = get_trusted_pickers(chat_id)
    if user_id in pickers:
        pickers.remove(user_id)
        set_trusted_pickers(chat_id, pickers)

# ==== Кастомные фразы ====

def get_custom_phrases():
    return load_json(config.CUSTOM_PHRASES_FILE, default={
        "victim": [],
        "owner": [],
        "only_owner": []
    })

def add_custom_phrase(phrase_type, phrase):
    phrases = get_custom_phrases()
    phrases[phrase_type].append(phrase)
    save_json(config.CUSTOM_PHRASES_FILE, phrases)

def del_custom_phrase(phrase_type, idx):
    phrases = get_custom_phrases()
    if 0 <= idx < len(phrases[phrase_type]):
        del phrases[phrase_type][idx]
        save_json(config.CUSTOM_PHRASES_FILE, phrases)
        return True
    return False

def list_phrases_by_type(phrase_type):
    file_phrases = {
        "victim": VICTIM_PHRASES,
        "owner": OWNER_PHRASES,
        "only_owner": ONLY_OWNER_PHRASES
    }[phrase_type]
    custom_phrases = get_custom_phrases()[phrase_type]
    return file_phrases, custom_phrases

# ==== Исключённые ====

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

def del_excluded(chat_id, user_id):
    data = load_json(config.EXCLUDE_FILE)
    chat_excl = data.get(str(chat_id), [])
    if user_id in chat_excl:
        chat_excl.remove(user_id)
        data[str(chat_id)] = chat_excl
        save_json(config.EXCLUDE_FILE, data)

# ==== Settings (живые настройки) ====

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

# ==== Напоминания ====

def get_reminder_suspend():
    return load_json(config.REMINDER_SUSPEND_FILE)

def set_reminder_suspend(chat_id, until_date):
    data = load_json(config.REMINDER_SUSPEND_FILE)
    if until_date:
        data[str(chat_id)] = until_date
    else:
        data.pop(str(chat_id), None)
    save_json(config.REMINDER_SUSPEND_FILE, data)

def get_limit_for_chat(chat_id):
    s = get_settings(chat_id)
    if "daily_limit" in s:
        return s["daily_limit"]
    return config.DAILY_LIMIT_PER_CHAT

# ==== Проверка доверия ====

async def is_trusted(message: types.Message):
    owner_id, _ = await get_chat_owner_and_members(message.chat.id)
    if message.from_user.id == owner_id:
        return True
    pickers = get_trusted_pickers(message.chat.id)
    return message.from_user.id in pickers

# ==== Команды бота ====

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.chat.type in [ChatType.SUPERGROUP, ChatType.GROUP]:
        lim = get_limit_for_chat(message.chat.id)
        await message.reply(config.WELCOME_GROUP_MESSAGE.format(limit=lim))
    else:
        await message.reply(config.WELCOME_PRIVATE_MESSAGE)

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.reply(
        "🤖 <b>Жертва дня</b> — бот для групп. Основные команды:\n"
        "/victim — жеребьёвка дня\n"
        "/statistics — кто сколько раз был жертвой\n"
        "/set_limit N — лимит жеребьёвок\n"
        "/add_picker, /del_picker, /list_pickers — доверенные пикеры\n"
        "/exclude, /include, /list_excluded — исключения\n"
        "/phrases_source, /add_phrase, /del_phrase, /list_phrases — работа с фразами\n"
        "/reminder_on, /reminder_off, /reminder_time, /reminder_weekends_on, /reminder_weekends_off — напоминания\n",
        parse_mode="HTML"
    )

@dp.message(Command("victim"))
async def victim_cmd(message: types.Message):
    if message.chat.type not in [ChatType.SUPERGROUP, ChatType.GROUP]:
        await message.reply("Я работаю только в групповых чатах!")
        return
    owner_id, members = await get_chat_owner_and_members(message.chat.id)
    if not owner_id:
        await message.reply("Не могу определить владельца группы.")
        return
    if not await is_trusted(message):
        trusted_ids = [owner_id] + get_trusted_pickers(message.chat.id)
        mentions = []
        for uid in trusted_ids:
            try:
                user = await telethon_client.get_entity(uid)
                mentions.append(await get_user_html(user))
            except Exception:
                mentions.append(str(uid))
        await message.reply(
            f"Только {', '.join(mentions)} могут назначать жертву!",
            parse_mode="HTML"
        )
        return
    settings = get_settings(message.chat.id)
    today = now_in_tz().strftime("%Y-%m-%d")
    limit = get_limit_for_chat(message.chat.id)
    last_run_date = settings.get("last_run_date", "")
    runs_today = settings.get("runs_today", 0)
    if last_run_date == today and runs_today >= limit:
        await message.reply(f"Сегодня лимит жеребьёвок исчерпан! ({limit}) Попробуйте завтра.")
        return
    exclude_ids = get_excluded(message.chat.id)
    candidates = [u for u in members if u.id not in exclude_ids]
    if len(candidates) < config.MIN_MEMBERS_TO_PICK:
        await message.reply(f"Недостаточно участников для жеребьёвки (нужно хотя бы {config.MIN_MEMBERS_TO_PICK}).")
        return
    chance_owner = get_setting(message.chat.id, "chance_owner", "auto")
    if chance_owner == "auto":
        owner_chance = 1 / len(candidates) if owner_id in [u.id for u in candidates] else 0
    else:
        try:
            owner_chance = float(chance_owner)
            if not (0 < owner_chance < 1):
                owner_chance = 0.1
        except Exception:
            owner_chance = 0.1
    candidates_owner = [u for u in candidates if u.id == owner_id]
    candidates_non_owner = [u for u in candidates if u.id != owner_id]
    if candidates_owner and (random.random() < owner_chance):
        victim = candidates_owner[0]
        phrase_type = "owner"
    else:
        victim = random.choice(candidates_non_owner) if candidates_non_owner else candidates_owner[0]
        phrase_type = "victim"
    phrase_source = get_setting(message.chat.id, "phrase_sources", {}).get(phrase_type, "all")
    file_phrases = {
        "victim": VICTIM_PHRASES,
        "owner": OWNER_PHRASES,
        "only_owner": ONLY_OWNER_PHRASES
    }[phrase_type]
    custom_phrases = get_custom_phrases()[phrase_type]
    if phrase_source == "all":
        pool = file_phrases + custom_phrases
    elif phrase_source == "file":
        pool = file_phrases
    elif phrase_source == "custom":
        pool = custom_phrases
    else:
        pool = file_phrases + custom_phrases
    if not pool:
        await message.reply("Нет ни одной фразы для этого типа! Добавьте через /add_phrase")
        return
    phrase = random.choice(pool)
    await message.reply(phrase.format(mention=await get_user_html(victim)), parse_mode="HTML")
    if last_run_date != today:
        runs_today = 1
    else:
        runs_today += 1
    set_setting(message.chat.id, "last_run_date", today)
    set_setting(message.chat.id, "runs_today", runs_today)
    increment_stat(message.chat.id, victim.id)

@dp.message(Command("statistics"))
async def statistics_cmd(message: types.Message):
    if message.chat.type not in [ChatType.SUPERGROUP, ChatType.GROUP]:
        await message.reply("Я показываю статистику только в группах!")
        return
    stats = get_stats_for_chat(message.chat.id)
    if not stats:
        await message.reply("Пока никто не был жертвой дня в этом чате.")
        return
    rows = []
    for user_id, count in sorted(stats.items(), key=lambda x: -x[1]):
        try:
            user = await telethon_client.get_entity(int(user_id))
            mention = await get_user_html(user)
        except Exception:
            mention = f"User {user_id}"
        rows.append(f"{mention} — <b>{count}</b>")
    table = "\n".join(f"{i+1}. {row}" for i, row in enumerate(rows))
    await message.reply(f"<b>Статистика жертв дня:</b>\n\n{table}", parse_mode="HTML")

@dp.message(Command("set_limit"))
async def set_limit_cmd(message: types.Message, command: CommandObject):
    if not await is_trusted(message):
        await message.reply("Только владелец или доверенный может менять лимит жеребьёвок!")
        return
    if not command.args:
        curr = get_limit_for_chat(message.chat.id)
        await message.reply(f"Текущий лимит: {curr} раз(а) в сутки.")
        return
    try:
        n = int(command.args.strip())
        assert 1 <= n <= 100
    except Exception:
        await message.reply("Пример: /set_limit 2 (целое число от 1 до 100)")
        return
    set_setting(message.chat.id, "daily_limit", n)
    await message.reply(f"Лимит жеребьёвок теперь: {n} раз(а) в сутки.")

@dp.message(Command("add_picker"))
async def add_picker_cmd(message: types.Message, command: CommandObject):
    if not await is_trusted(message):
        await message.reply("Только владелец или доверенный может добавлять пикеров.")
        return
    user_id = await extract_user_id(message)
    if not user_id:
        await message.reply("Ответьте на сообщение или укажите @username или user_id.")
        return
    owner_id, _ = await get_chat_owner_and_members(message.chat.id)
    if user_id == owner_id:
        await message.reply("Владелец всегда доверенный, не нужно добавлять его вручную.")
        return
    add_trusted_picker(message.chat.id, user_id)
    await message.reply("Пикер добавлен!")

@dp.message(Command("del_picker"))
async def del_picker_cmd(message: types.Message, command: CommandObject):
    if not await is_trusted(message):
        await message.reply("Только владелец или доверенный может удалять пикеров.")
        return
    user_id = await extract_user_id(message)
    if not user_id:
        await message.reply("Ответьте на сообщение или укажите @username или user_id.")
        return
    owner_id, _ = await get_chat_owner_and_members(message.chat.id)
    if user_id == owner_id:
        await message.reply("Владелец всегда доверенный, нельзя удалить его из пикеров.")
        return
    del_trusted_picker(message.chat.id, user_id)
    await message.reply("Пикер удалён.")

@dp.message(Command("list_pickers"))
async def list_pickers_cmd(message: types.Message):
    pickers = get_trusted_pickers(message.chat.id)
    if not pickers:
        await message.reply("В этом чате только владелец может назначать жертву.")
        return
    mentions = []
    for uid in pickers:
        try:
            user = await telethon_client.get_entity(uid)
            mentions.append(await get_user_html(user))
        except Exception:
            mentions.append(str(uid))
    await message.reply("Доверенные пикеры: " + ", ".join(mentions), parse_mode="HTML")

@dp.message(Command("chance_owner"))
async def chance_owner_cmd(message: types.Message, command: CommandObject):
    if not await is_trusted(message):
        await message.reply("Только владелец или доверенный может менять шансы.")
        return
    parts = (command.args or "").split()
    if not parts:
        curr = get_setting(message.chat.id, "chance_owner", "auto")
        if curr == "auto":
            await message.reply("Шанс выпадения владельца — авто (у всех равная вероятность).")
        else:
            await message.reply(f"Текущий шанс: {float(curr)*100:.2f}%")
        return
    arg = parts[0]
    if arg == "auto":
        set_setting(message.chat.id, "chance_owner", "auto")
        await message.reply("Теперь шанс выпадения владельца: авто.")
    else:
        try:
            v = float(arg)
            assert 0 < v < 1
        except Exception:
            await message.reply("Используй: /chance_owner 0.1 (от 0 до 1) или auto")
            return
        set_setting(message.chat.id, "chance_owner", v)
        await message.reply(f"Установлен шанс: {v*100:.2f}%")

@dp.message(Command("reminder_off"))
async def reminder_off_cmd(message: types.Message, command: CommandObject):
    if not await is_trusted(message):
        await message.reply("Только владелец или доверенный может управлять напоминаниями!")
        return
    n_days = 1
    if command.args:
        try:
            n_days = int(command.args.strip())
            assert n_days > 0
        except Exception:
            await message.reply("Пример: /reminder_off 3 (целое положительное число)")
            return
    until_date = (now_in_tz() + timedelta(days=n_days)).strftime("%Y-%m-%d")
    set_reminder_suspend(message.chat.id, until_date)
    await message.reply(f"Напоминания отключены на {n_days} дней (до {until_date})")

@dp.message(Command("reminder_on"))
async def reminder_on_cmd(message: types.Message):
    if not await is_trusted(message):
        await message.reply("Только владелец или доверенный может управлять напоминаниями!")
        return
    set_reminder_suspend(message.chat.id, None)
    await message.reply("Напоминания снова включены для этого чата!")

@dp.message(Command("reminder_time"))
async def reminder_time_cmd(message: types.Message, command: CommandObject):
    if not await is_trusted(message):
        await message.reply("Только владелец или доверенный может менять время напоминаний!")
        return
    parts = (command.args or "").split()
    if len(parts) != 2:
        await message.reply("Используй: /reminder_time 12 30 (часы минуты)")
        return
    try:
        hour = int(parts[0])
        minute = int(parts[1])
        assert 0 <= hour < 24 and 0 <= minute < 60
    except Exception:
        await message.reply("Время должно быть от 0 до 23 (часы) и от 0 до 59 (минуты)")
        return
    set_setting(message.chat.id, "reminder_hour", hour)
    set_setting(message.chat.id, "reminder_minute", minute)
    await message.reply(f"Напоминания теперь будут в {hour:02d}:{minute:02d}")

@dp.message(Command("reminder_weekends_on"))
async def reminder_weekends_on_cmd(message: types.Message):
    set_setting(message.chat.id, "reminder_skip_weekends", False)
    await message.reply("Напоминания теперь будут и по выходным.")

@dp.message(Command("reminder_weekends_off"))
async def reminder_weekends_off_cmd(message: types.Message):
    set_setting(message.chat.id, "reminder_skip_weekends", True)
    await message.reply("Напоминания по выходным выключены.")

@dp.message(Command("exclude"))
async def exclude_cmd(message: types.Message, command: CommandObject):
    if not await is_trusted(message):
        await message.reply("Только владелец или доверенный может исключать участников.")
        return
    user_id = await extract_user_id(message)
    if not user_id:
        await message.reply("Ответьте на сообщение или укажите @username или user_id.")
        return
    excl = get_excluded(message.chat.id)
    owner_id, members = await get_chat_owner_and_members(message.chat.id)
    chat_member_ids = [u.id for u in members]
    non_excl = [uid for uid in chat_member_ids if uid not in excl and uid != user_id]
    if len(non_excl) < config.MIN_MEMBERS_TO_PICK:
        await message.reply(f"Нельзя исключить, иначе останется слишком мало кандидатов!")
        return
    add_excluded(message.chat.id, user_id)
    await message.reply("Участник исключён из жеребьёвки.")

@dp.message(Command("include"))
async def include_cmd(message: types.Message, command: CommandObject):
    if not await is_trusted(message):
        await message.reply("Только владелец или доверенный может включать участников.")
        return
    user_id = await extract_user_id(message)
    if not user_id:
        await message.reply("Ответьте на сообщение или укажите @username или user_id.")
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
        try:
            user = await telethon_client.get_entity(uid)
            mentions.append(await get_user_html(user))
        except Exception:
            mentions.append(str(uid))
    await message.reply("Исключены: " + ", ".join(mentions), parse_mode="HTML")

@dp.message(Command("phrases_source"))
async def phrases_source_cmd(message: types.Message, command: CommandObject):
    if not await is_trusted(message):
        await message.reply("Только владелец или доверенный может менять источник фраз.")
        return
    parts = (command.args or "").split()
    if len(parts) == 1:
        phrase_type = parts[0]
        src = get_setting(message.chat.id, "phrase_sources", {}).get(phrase_type, "all")
        await message.reply(f"Источник фраз для типа {phrase_type}: {src}")
        return
    if len(parts) == 2:
        phrase_type, src = parts
        if phrase_type not in ["victim", "owner", "only_owner"] or src not in ["all", "file", "custom"]:
            await message.reply("Используй: /phrases_source victim|owner|only_owner all|file|custom")
            return
        phrase_sources = get_setting(message.chat.id, "phrase_sources", {})
        phrase_sources[phrase_type] = src
        set_setting(message.chat.id, "phrase_sources", phrase_sources)
        await message.reply(f"Теперь для {phrase_type} используются фразы: {src}")
        return
    await message.reply("Используй: /phrases_source victim|owner|only_owner all|file|custom")

@dp.message(Command("add_phrase"))
async def add_phrase_cmd(message: types.Message, command: CommandObject):
    if not await is_trusted(message):
        await message.reply("Только владелец или доверенный может добавлять фразы.")
        return
    parts = (command.args or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.reply("Используй: /add_phrase victim|owner|only_owner Текст")
        return
    phrase_type, text = parts
    if phrase_type not in ["victim", "owner", "only_owner"]:
        await message.reply("Тип фразы: victim, owner, only_owner.")
        return
    add_custom_phrase(phrase_type, text)
    await message.reply(f"Добавлена новая фраза для {phrase_type}.")

@dp.message(Command("del_phrase"))
async def del_phrase_cmd(message: types.Message, command: CommandObject):
    if not await is_trusted(message):
        await message.reply("Только владелец или доверенный может удалять фразы.")
        return
    parts = (command.args or "").split()
    if len(parts) != 2:
        await message.reply("Используй: /del_phrase victim|owner|only_owner номер")
        return
    phrase_type, idx = parts
    if phrase_type not in ["victim", "owner", "only_owner"]:
        await message.reply("Тип фразы: victim, owner, only_owner.")
        return
    try:
        idx = int(idx)
    except Exception:
        await message.reply("Укажи номер фразы.")
        return
    ok = del_custom_phrase(phrase_type, idx)
    if ok:
        await message.reply("Фраза удалена.")
    else:
        await message.reply("Нет такой фразы.")

@dp.message(Command("list_phrases"))
async def list_phrases_cmd(message: types.Message, command: CommandObject):
    parts = (command.args or "").split()
    if not parts:
        await message.reply("Используй: /list_phrases victim|owner|only_owner")
        return
    phrase_type = parts[0]
    if phrase_type not in ["victim", "owner", "only_owner"]:
        await message.reply("Тип фразы: victim, owner, only_owner.")
        return
    file_phrases, custom_phrases = list_phrases_by_type(phrase_type)
    txt = f"<b>Стандартные фразы:</b>\n"
    for i, s in enumerate(file_phrases):
        txt += f"{i}. {s}\n"
    txt += f"\n<b>Пользовательские фразы:</b>\n"
    for i, s in enumerate(custom_phrases):
        txt += f"{i}. {s}\n"
    await message.reply(txt, parse_mode="HTML")

# ==== Планировщик напоминаний ====

import asyncio

async def reminder_scheduler():
    while True:
        all_settings = load_json(config.SETTINGS_FILE)
        for chat_id, settings in all_settings.items():
            enable = settings.get("enable_reminder", True)
            skip_weekends = settings.get("reminder_skip_weekends", True)
            hour = settings.get("reminder_hour", 12)
            minute = settings.get("reminder_minute", 0)
            tz = pytz.timezone(config.TIMEZONE)
            now = datetime.now(tz)
            if not enable:
                continue
            if skip_weekends and now.weekday() >= 5:
                continue
            suspend = get_reminder_suspend()
            if str(chat_id) in suspend:
                until_str = suspend[str(chat_id)]
                until = datetime.strptime(until_str, "%Y-%m-%d")
                if now.date() <= until.date():
                    continue
            if now.hour == hour and now.minute == minute:
                last_run_date = settings.get("last_run_date", "")
                today = now.strftime("%Y-%m-%d")
                limit = settings.get("daily_limit", config.DAILY_LIMIT_PER_CHAT)
                runs_today = settings.get("runs_today", 0)
                if not (last_run_date == today and runs_today >= limit):
                    try:
                        await bot.send_message(
                            chat_id,
                            config.REMINDER_MESSAGE
                        )
                    except Exception:
                        continue
        await asyncio.sleep(60)

# ==== Установка команд Telegram ====

async def set_bot_commands(bot: Bot):
    await bot.set_my_commands([
        types.BotCommand(command=cmd["command"], description=cmd["description"])
        for cmd in config.COMMANDS
    ])

# ==== Основной запуск ====

if __name__ == "__main__":
    import asyncio

    async def main():
        await telethon_client.start()
        await set_bot_commands(bot)
        asyncio.create_task(reminder_scheduler())
        await dp.start_polling(bot)

    asyncio.run(main())
