"""Handler input contexts (port InlineMessageInfo / UserMessageInfo)."""

from __future__ import annotations

from dataclasses import dataclass

type ChatId = int
type UserId = int
type MessageId = int


@dataclass(frozen=True, slots=True)
class MessageContext:
    user_id: UserId
    chat_id: ChatId
    message_id: MessageId
    language_code: str | None = None


@dataclass(frozen=True, slots=True)
class CallbackContext:
    user_id: UserId
    chat_id: ChatId
    message_id: MessageId
    language_code: str | None = None
    payload: str | None = None
