"""Plain-text reply messages (port TextMessageReply / EditTextMessageReply)."""

from __future__ import annotations

from dataclasses import dataclass

from tg_dialog_system.models.context import MessageId


@dataclass(frozen=True, slots=True)
class TextMessageReply:
    value: str


@dataclass(frozen=True, slots=True)
class EditTextMessageReply:
    message_id: MessageId
    value: str
