# config.py

# Значение по умолчанию для лимита жеребьёвок (меняется командой /set_limit)
DAILY_LIMIT_PER_CHAT = 1  # Можно поменять по умолчанию, но для гибкости — через команду

RESET_HOUR = 0  # Время сброса лимита (0 = 00:00)
TIMEZONE = "Europe/Moscow"

STATS_FILE = "stats.json"
TRUSTED_PICKERS_FILE = "trusted_pickers.json"
SETTINGS_FILE = "settings.json"
CUSTOM_PHRASES_FILE = "custom_phrases.json"
EXCLUDE_FILE = "exclude.json"
REMINDER_SUSPEND_FILE = "reminder_suspend.json"

MIN_MEMBERS_TO_PICK = 2  # Минимальное число участников для жеребьёвки

WELCOME_GROUP_MESSAGE = (
    "👋 Я — бот для игры «Жертва дня».\n"
    "Владелец группы или доверенный может запускать команду /victim (максимум {limit} раз в сутки), чтобы выбрать «жертву дня».\n"
    "Команда /statistics покажет таблицу попаданий каждого участника.\n"
    "Больше информации: /help"
)

WELCOME_PRIVATE_MESSAGE = (
    "Я работаю только в групповых чатах. "
    "Добавь меня в рабочий чат и используй /victim!"
)

REMINDER_MESSAGE = (
    "⚠️ Не забыли выбрать жертву дня? Используйте /victim!"
)

COMMANDS = [
    {"command": "start", "description": "Краткое приветствие"},
    {"command": "help", "description": "Справка и все команды"},
    {"command": "victim", "description": "Выбрать жертву дня (раз в сутки или по лимиту)"},
    {"command": "statistics", "description": "Показать статистику по попаданиям"},
    {"command": "set_limit", "description": "Изменить лимит жеребьёвок в сутки"},
    {"command": "add_picker", "description": "Добавить доверенного пикера"},
    {"command": "del_picker", "description": "Удалить доверенного пикера"},
    {"command": "list_pickers", "description": "Список доверенных пикеров"},
    {"command": "chance_owner", "description": "Задать шанс для владельца"},
    {"command": "reminder_off", "description": "Отключить напоминания на N дней"},
    {"command": "reminder_on", "description": "Включить напоминания"},
    {"command": "reminder_time", "description": "Изменить время напоминания"},
    {"command": "reminder_weekends_on", "description": "Включить напоминания в выходные"},
    {"command": "reminder_weekends_off", "description": "Отключить напоминания в выходные"},
    {"command": "exclude", "description": "Исключить участника из жеребьёвки"},
    {"command": "include", "description": "Вернуть участника в жеребьёвку"},
    {"command": "list_excluded", "description": "Показать список исключённых"},
    {"command": "phrases_source", "description": "Источник фраз для типа"},
    {"command": "add_phrase", "description": "Добавить свою фразу"},
    {"command": "del_phrase", "description": "Удалить фразу"},
    {"command": "list_phrases", "description": "Показать все фразы"},
]
