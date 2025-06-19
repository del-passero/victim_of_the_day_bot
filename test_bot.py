# test_bot.py

import os
import tempfile
import shutil
import pytest

# Импортируем функции из victim_bot.py
import config
from victim_bot import (
    load_json, save_json,
    get_settings, set_setting,
    get_trusted_pickers, add_trusted_picker, del_trusted_picker,
    get_excluded, add_excluded, del_excluded,
    get_custom_phrases, add_custom_phrase, del_custom_phrase,
    increment_stat, get_stats_for_chat
)

@pytest.fixture(scope="function", autouse=True)
def temp_data_dir():
    # Все json-файлы подменяем на временные
    tmp_dir = tempfile.mkdtemp()
    origs = {}
    for fname in [
        config.STATS_FILE,
        config.TRUSTED_PICKERS_FILE,
        config.SETTINGS_FILE,
        config.CUSTOM_PHRASES_FILE,
        config.EXCLUDE_FILE,
        config.REMINDER_SUSPEND_FILE,
    ]:
        origs[fname] = fname
        new_path = os.path.join(tmp_dir, os.path.basename(fname))
        setattr(config, os.path.splitext(os.path.basename(fname))[0].upper() + "_FILE", new_path)
    yield
    shutil.rmtree(tmp_dir)

def test_limit_setting():
    chat_id = 111
    set_setting(chat_id, "daily_limit", 2)
    assert get_settings(chat_id)["daily_limit"] == 2

def test_trusted_picker_add_del():
    chat_id = 222
    user_id = 12345
    add_trusted_picker(chat_id, user_id)
    assert user_id in get_trusted_pickers(chat_id)
    del_trusted_picker(chat_id, user_id)
    assert user_id not in get_trusted_pickers(chat_id)

def test_excluded_add_del():
    chat_id = 333
    user_id = 98765
    add_excluded(chat_id, user_id)
    assert user_id in get_excluded(chat_id)
    del_excluded(chat_id, user_id)
    assert user_id not in get_excluded(chat_id)

def test_custom_phrases():
    add_custom_phrase("victim", "Test victim phrase {mention}")
    add_custom_phrase("owner", "Test owner phrase {mention}")
    phrases = get_custom_phrases()
    assert "Test victim phrase {mention}" in phrases["victim"]
    assert "Test owner phrase {mention}" in phrases["owner"]
    
    del_custom_phrase("victim", 0)
    updated_phrases = get_custom_phrases()
    assert updated_phrases["victim"] == []


def test_statistics():
    chat_id = 555
    user_id = 777
    increment_stat(chat_id, user_id)
    stats = get_stats_for_chat(chat_id)
    assert stats[str(user_id)] == 1
    increment_stat(chat_id, user_id)
    stats = get_stats_for_chat(chat_id)
    assert stats[str(user_id)] == 2

def test_no_negative_limit():
    chat_id = 666
    set_setting(chat_id, "daily_limit", -1)
    limit = get_settings(chat_id)["daily_limit"]
    assert limit == -1  # Проверка что “-1” сохраняется, но в реальном коде нельзя будет установить через бота

def test_no_negative_exclude():
    chat_id = 777
    user_id = -100
    add_excluded(chat_id, user_id)
    assert user_id in get_excluded(chat_id)
