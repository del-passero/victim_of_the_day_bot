# config.py

import os

# Корневая директория для json-файлов
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)

# JSON-файлы
USERS_FILE = os.path.join(DATA_DIR, "users.json")
EXCLUDE_FILE = os.path.join(DATA_DIR, "exclude.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
CUSTOM_PHRASES_FILE = os.path.join(DATA_DIR, "custom_phrases.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
AUTORUN_FILE = os.path.join(DATA_DIR, "autorun.json")

TIMEZONE = "Europe/Moscow"


# Лимиты
DAILY_LIMIT_PER_CHAT = 5
MIN_MEMBERS_TO_PICK = 2
AUTO_RUN_DAYS = 3

# Команды (для меню)
COMMANDS = [
    {"command": "victim", "description": "Выбрать жертву дня"},
    {"command": "statistics", "description": "Статистика жертв"},
    {"command": "set_limit", "description": "Установить лимит жеребьевок"},
    {"command": "set_autorun", "description": "Сколько дней до автозапуска"},
    {"command": "exclude", "description": "Исключить участника"},
    {"command": "include", "description": "Вернуть в жеребьевку"},
    {"command": "list_excluded", "description": "Показать исключённых"},
    {"command": "add_phrase", "description": "Добавить свою фразу"},
    {"command": "del_phrase", "description": "Удалить свою фразу"},
    {"command": "list_phrases", "description": "Все фразы"},
    {"command": "help", "description": "Помощь"},
]

# Приветствие, help, сообщение автозапуска
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
    "/set_limit N — лимит жеребьевок в сутки\n"
    "/set_autorun N — сколько дней простоя до автозапуска\n"
    "/exclude @user — исключить участника\n"
    "/include @user — вернуть в жеребьевку\n"
    "/list_excluded — список исключённых\n"
    "/add_phrase текст — добавить свою фразу\n"
    "/del_phrase номер — удалить свою фразу\n"
    "/list_phrases — показать все фразы\n"
)
AUTO_RUN_MESSAGE = "Бот не вызывали давно, запускаю жеребьёвку!"

