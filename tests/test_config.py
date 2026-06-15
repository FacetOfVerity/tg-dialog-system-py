import pytest

from tg_dialog_system.config import BotMode, TelegramSettings

VALID_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz0123456789"


def test_defaults_with_valid_token():
    s = TelegramSettings(bot_token=VALID_TOKEN)
    assert s.mode is BotMode.POLLING
    assert s.max_messages_per_second == 30
    assert s.enable_rate_limiting is True


def test_empty_token_rejected():
    with pytest.raises(ValueError):
        TelegramSettings(bot_token="")


def test_placeholder_token_rejected():
    with pytest.raises(ValueError):
        TelegramSettings(bot_token="YOUR_BOT_TOKEN_HERE")


def test_malformed_token_rejected():
    with pytest.raises(ValueError):
        TelegramSettings(bot_token="not-a-token")


def test_loads_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM__BOT_TOKEN", VALID_TOKEN)
    monkeypatch.setenv("TELEGRAM__MAX_MESSAGES_PER_SECOND", "10")
    s = TelegramSettings()
    assert s.bot_token == VALID_TOKEN
    assert s.max_messages_per_second == 10
