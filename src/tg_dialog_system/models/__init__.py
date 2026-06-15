"""Pure domain models (no aiogram dependency)."""

from __future__ import annotations

from tg_dialog_system.models.callback_data import CallbackData
from tg_dialog_system.models.context import (
    CallbackContext,
    ChatId,
    MessageContext,
    MessageId,
    UserId,
)
from tg_dialog_system.models.version import Version

__all__ = [
    "CallbackData",
    "CallbackContext",
    "MessageContext",
    "ChatId",
    "MessageId",
    "UserId",
    "Version",
]
