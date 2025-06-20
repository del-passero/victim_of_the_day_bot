import os
import json
import random
import shutil
import pytest

# Импортируем функции из victim_bot.py (если структура пакета позволяет)
from victim_bot import (
    save_json, load_json, get_users, set_users, add_user,
    get_custom_phrases, add_custom_phrase, del_custom_phrase,
    get_excluded, add_excluded, del_excluded,
    increment_stat, get_stats_for_chat
)

TEST_CHAT_ID = 12345
TEST_USER_ID = 999
TEST_JSON = "test_file.json"

@pytest.fixture(autouse=True)
def cleanup():
    # Очистка тестовых файлов перед/после теста
    for fname in [
        "stats.json", "users.json", "custom_phrases.json",
        "exclude.json", "settings.json", "autorun.json"
    ]:
        if os.path.exists(fname):
            os.remove(fname)
    yield
    for fname in [
        "stats.json", "users.json", "custom_phrases.json",
        "exclude.json", "settings.json", "autorun.json"
    ]:
        if os.path.exists(fname):
            os.remove(fname)

def test_json_save_and_load():
    data = {"a": 1}
    save_json(TEST_JSON, data)
    loaded = load_json(TEST_JSON)
    assert loaded == data
    os.remove(TEST_JSON)

def test_users():
    set_users(TEST_CHAT_ID, [])
    assert get_users(TEST_CHAT_ID) == []
    add_user(TEST_CHAT_ID, TEST_USER_ID)
    assert get_users(TEST_CHAT_ID) == [TEST_USER_ID]

def test_phrases():
    assert get_custom_phrases() == []
    add_custom_phrase("Hello, test!")
    phrases = get_custom_phrases()
    assert "Hello, test!" in phrases
    idx = phrases.index("Hello, test!")
    assert del_custom_phrase(idx) is True
    assert "Hello, test!" not in get_custom_phrases()

def test_excluded():
    assert get_excluded(TEST_CHAT_ID) == []
    add_excluded(TEST_CHAT_ID, TEST_USER_ID)
    assert get_excluded(TEST_CHAT_ID) == [TEST_USER_ID]
    del_excluded(TEST_CHAT_ID, TEST_USER_ID)
    assert get_excluded(TEST_CHAT_ID) == []

def test_statistics():
    increment_stat(TEST_CHAT_ID, TEST_USER_ID)
    stats = get_stats_for_chat(TEST_CHAT_ID)
    assert str(TEST_USER_ID) in stats
    assert stats[str(TEST_USER_ID)] == 1
    increment_stat(TEST_CHAT_ID, TEST_USER_ID)
    stats = get_stats_for_chat(TEST_CHAT_ID)
    assert stats[str(TEST_USER_ID)] == 2

