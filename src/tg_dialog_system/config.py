"""Typed bot configuration (port TelegramOptions + ValidateBotToken)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER = "your_bot_token_here"


class BotMode(StrEnum):
    POLLING = "polling"
    WEBHOOK = "webhook"


class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TELEGRAM__",
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    bot_token: str
    mode: BotMode = BotMode.POLLING
    max_messages_per_second: int = 30
    max_retries: int = 3
    initial_retry_delay_ms: int = 1000
    enable_rate_limiting: bool = True
    startup_max_retries: int = 5
    startup_initial_retry_delay_ms: int = 2000
    enable_startup_retries: bool = True

    @field_validator("bot_token")
    @classmethod
    def _validate_token(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Telegram bot token is not configured (TELEGRAM__BOT_TOKEN).")
        if value.lower() == _PLACEHOLDER:
            raise ValueError("Replace the placeholder bot token with a real token from @BotFather.")
        parts = value.split(":")
        if len(parts) != 2 or not parts[0].isdigit() or len(parts[1]) < 30:
            raise ValueError(
                "Invalid Telegram bot token format. Expected '<bot_id>:<token>'."
            )
        return value
