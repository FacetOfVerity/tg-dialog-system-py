"""Telegram dialog-system bot framework (Python port).

Public API for building dialog bots: routing decorators, reply types, builders,
the configuration model, and the TgDialogBot host.
"""

from __future__ import annotations

from tg_dialog_system import errors
from tg_dialog_system.config import BotMode, TelegramSettings
from tg_dialog_system.hosting import TgDialogBot
from tg_dialog_system.models import (
    CallbackContext,
    CallbackData,
    MessageContext,
    Version,
)
from tg_dialog_system.models.replies import (
    EditMenuMessageReply,
    EditTextMessageReply,
    MenuButton,
    MenuGrid,
    MenuMessageReply,
    ReplyKeyboardBuilder,
    ReplyKeyboardButton,
    ReplyKeyboardMessageReply,
    ReplyKeyboardOptions,
    ReplyKeyboardRemoveMessageReply,
    ReplyMessage,
    ReplyResult,
    TextMessageReply,
)
from tg_dialog_system.protocols import (
    ArbitraryTextMessageHandler,
    BotErrorsProcessor,
    ChatMenuButtonProvider,
)
from tg_dialog_system.routing import callback_route, command_route, discover_handlers

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "errors",
    "TgDialogBot",
    "TelegramSettings",
    "BotMode",
    "command_route",
    "callback_route",
    "discover_handlers",
    "CallbackData",
    "Version",
    "MessageContext",
    "CallbackContext",
    "TextMessageReply",
    "EditTextMessageReply",
    "MenuButton",
    "MenuMessageReply",
    "EditMenuMessageReply",
    "MenuGrid",
    "ReplyKeyboardButton",
    "ReplyKeyboardOptions",
    "ReplyKeyboardBuilder",
    "ReplyKeyboardMessageReply",
    "ReplyKeyboardRemoveMessageReply",
    "ReplyMessage",
    "ReplyResult",
    "ArbitraryTextMessageHandler",
    "BotErrorsProcessor",
    "ChatMenuButtonProvider",
]
