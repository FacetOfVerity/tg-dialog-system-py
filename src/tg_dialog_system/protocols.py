"""Consumer-implemented extension points (structural Protocols)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from aiogram.types import BotCommand

from tg_dialog_system.errors import Errors
from tg_dialog_system.models.context import ChatId, MessageContext
from tg_dialog_system.models.replies import ReplyResult


@runtime_checkable
class ChatMenuButtonProvider(Protocol):
    def get_chat_menu_buttons_by_language_code(self) -> dict[str, list[BotCommand]]: ...


@runtime_checkable
class ArbitraryTextMessageHandler(Protocol):
    async def handle(self, ctx: MessageContext, payload: str) -> ReplyResult: ...


@runtime_checkable
class BotErrorsProcessor(Protocol):
    async def send_errors(self, chat_id: ChatId, errors: Errors) -> None: ...

    async def send_unexpected_error(self, chat_id: ChatId) -> None: ...
