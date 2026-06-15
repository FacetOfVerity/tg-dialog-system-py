"""Rate-limit + retry decorator over a MessageSender (port RateLimitedBotMessageSender)."""

from __future__ import annotations

from typing import Protocol

from tg_dialog_system.models.context import ChatId, MessageId
from tg_dialog_system.models.replies.keyboard import ReplyKeyboardBuilder, ReplyKeyboardOptions
from tg_dialog_system.models.replies.menu import MenuGrid
from tg_dialog_system.sending.rate_limit import SlidingWindowRateLimiter
from tg_dialog_system.sending.sender import MessageSender, SendResult


class _Retry(Protocol):
    async def execute_with_retry(self, operation, chat_id: ChatId) -> SendResult: ...


class RateLimitedBotMessageSender:
    def __init__(
        self,
        inner: MessageSender,
        rate_limiter: SlidingWindowRateLimiter,
        retry: _Retry,
    ) -> None:
        self._inner = inner
        self._rate_limiter = rate_limiter
        self._retry = retry

    async def _run(self, op_factory, chat_id: ChatId) -> SendResult:
        async def operation() -> SendResult:
            await self._rate_limiter.wait_for_availability()
            return await op_factory()

        return await self._retry.execute_with_retry(operation, chat_id)

    async def send_message(self, chat_id: ChatId, message: str) -> SendResult:
        return await self._run(lambda: self._inner.send_message(chat_id, message), chat_id)

    async def send_menu(self, chat_id: ChatId, text: str, buttons: MenuGrid) -> SendResult:
        return await self._run(lambda: self._inner.send_menu(chat_id, text, buttons), chat_id)

    async def send_reply_keyboard(
        self,
        chat_id: ChatId,
        text: str,
        keyboard: ReplyKeyboardBuilder,
        options: ReplyKeyboardOptions | None = None,
    ) -> SendResult:
        return await self._run(
            lambda: self._inner.send_reply_keyboard(chat_id, text, keyboard, options), chat_id
        )

    async def remove_reply_keyboard(
        self, chat_id: ChatId, text: str = "", selective: bool = False
    ) -> SendResult:
        return await self._run(
            lambda: self._inner.remove_reply_keyboard(chat_id, text, selective), chat_id
        )

    async def edit_message_text(
        self, chat_id: ChatId, message_id: MessageId, text: str
    ) -> SendResult:
        return await self._run(
            lambda: self._inner.edit_message_text(chat_id, message_id, text), chat_id
        )

    async def edit_message_menu(
        self, chat_id: ChatId, message_id: MessageId, text: str, buttons: MenuGrid
    ) -> SendResult:
        return await self._run(
            lambda: self._inner.edit_message_menu(chat_id, message_id, text, buttons), chat_id
        )
