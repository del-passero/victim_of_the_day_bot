# config.py

import os

# Корневая директория для json-файлов
DATA_DIR = os.getenv("DATA_DIR") or "/data"

# JSON-файлы (в /data)
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
CUSTOM_PHRASES_FILE = os.path.join(DATA_DIR, "custom_phrases.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")

# Временная зона
TIMEZONE = "Europe/Moscow"

# Лимиты (только из config.py!)
DAILY_LIMIT_PER_CHAT = 1
MIN_MEMBERS_TO_PICK = 2

# Команды меню
COMMANDS = [
    {"command": "victim", "description": "Выбрать жертву дня"},
    {"command": "statistics", "description": "Статистика жертв"},
    {"command": "add_phrase", "description": "Добавить свою фразу"},
    {"command": "del_phrase", "description": "Удалить свою фразу"},
    {"command": "list_phrases", "description": "Показать все фразы"},
    {"command": "help", "description": "Помощь"},
]

WELCOME_GROUP_MESSAGE = (
    "Бот жеребьёвки активирован!\n\n"
    "Достаточно чтобы каждый участник написал хотя бы одно сообщение или поставил реакцию, "
    "иначе он не попадёт в жеребьёвку!\n\n"
    "Лимит жеребьёвок в этом чате: {limit} в сутки.\n"
    "Для помощи: /help"
)
HELP_MESSAGE = (
    "<b>Команды бота:</b>\n"
    "/victim — выбрать жертву дня\n"
    "/statistics — статистика попаданий\n"
    "/add_phrase текст — добавить свою фразу\n"
    "/del_phrase номер — удалить свою фразу\n"
    "/list_phrases — показать все фразы\n"
)
AUTO_RUN_MESSAGE = "Давно никто не выбирал жертву дня, запускаю жеребьёвку!"