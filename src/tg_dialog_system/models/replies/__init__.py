"""Reply message types and the ReplyMessage union."""

from __future__ import annotations

from expression import Result

from tg_dialog_system.errors import Error
from tg_dialog_system.models.replies.keyboard import (
    ReplyKeyboardBuilder,
    ReplyKeyboardButton,
    ReplyKeyboardMessageReply,
    ReplyKeyboardOptions,
    ReplyKeyboardRemoveMessageReply,
)
from tg_dialog_system.models.replies.menu import (
    EditMenuMessageReply,
    MenuButton,
    MenuGrid,
    MenuMessageReply,
)
from tg_dialog_system.models.replies.text import EditTextMessageReply, TextMessageReply

type ReplyMessage = (
    TextMessageReply
    | EditTextMessageReply
    | MenuMessageReply
    | EditMenuMessageReply
    | ReplyKeyboardMessageReply
    | ReplyKeyboardRemoveMessageReply
)

type ReplyResult = Result[ReplyMessage, list[Error]]

__all__ = [
    "TextMessageReply",
    "EditTextMessageReply",
    "MenuButton",
    "MenuGrid",
    "MenuMessageReply",
    "EditMenuMessageReply",
    "ReplyKeyboardButton",
    "ReplyKeyboardOptions",
    "ReplyKeyboardBuilder",
    "ReplyKeyboardMessageReply",
    "ReplyKeyboardRemoveMessageReply",
    "ReplyMessage",
    "ReplyResult",
]
