"""Maps reply primitives to aiogram Bot calls; converts tg errors to Result.

Port of BotMessageSender.
"""

from __future__ import annotations

from typing import Protocol

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError, TelegramRetryAfter
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from expression import Error as Err
from expression import Ok, Result

from tg_dialog_system import errors
from tg_dialog_system.errors import Error
from tg_dialog_system.models.context import ChatId, MessageId
from tg_dialog_system.models.replies.keyboard import ReplyKeyboardBuilder, ReplyKeyboardOptions
from tg_dialog_system.models.replies.menu import MenuGrid

SendResult = Result[MessageId, list[Error]]


def _inline_markup(grid: MenuGrid) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=b.text, callback_data=b.callback_data.encode())
                for b in row
            ]
            for row in grid.rows
        ]
    )


def _reply_markup(
    keyboard: ReplyKeyboardBuilder, options: ReplyKeyboardOptions | None
) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=b.text) for b in row] for row in keyboard.rows if row]
    opts = options or ReplyKeyboardOptions()
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=opts.resize_keyboard,
        one_time_keyboard=opts.one_time_keyboard,
        selective=opts.selective,
        input_field_placeholder=opts.input_field_placeholder or None,
    )


class MessageSender(Protocol):
    async def send_message(self, chat_id: ChatId, message: str) -> SendResult: ...
    async def send_menu(self, chat_id: ChatId, text: str, buttons: MenuGrid) -> SendResult: ...
    async def send_reply_keyboard(
        self,
        chat_id: ChatId,
        text: str,
        keyboard: ReplyKeyboardBuilder,
        options: ReplyKeyboardOptions | None = None,
    ) -> SendResult: ...
    async def remove_reply_keyboard(
        self, chat_id: ChatId, text: str = "", selective: bool = False
    ) -> SendResult: ...
    async def edit_message_text(
        self, chat_id: ChatId, message_id: MessageId, text: str
    ) -> SendResult: ...
    async def edit_message_menu(
        self, chat_id: ChatId, message_id: MessageId, text: str, buttons: MenuGrid
    ) -> SendResult: ...


class BotMessageSender:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def _guard(self, coro_factory, action: str) -> SendResult:
        try:
            message = await coro_factory()
            return Ok(message.message_id)
        except TelegramRetryAfter as exc:
            return Err([errors.telegram_api(
                "Telegram.Api.429", "Too many requests", retry_after=exc.retry_after
            )])
        except (TelegramAPIError, TelegramNetworkError) as exc:
            return Err([errors.telegram_api(
                f"Telegram.Api.{type(exc).__name__}", f"Failed to {action}"
            )])
        except Exception as exc:  # noqa: BLE001 - never leak details to users
            return Err([errors.unexpected(
                f"Exception.{type(exc).__name__}", f"Failed to {action}"
            )])

    async def send_message(self, chat_id: ChatId, message: str) -> SendResult:
        return await self._guard(
            lambda: self._bot.send_message(chat_id=chat_id, text=message), "send message"
        )

    async def send_menu(self, chat_id: ChatId, text: str, buttons: MenuGrid) -> SendResult:
        return await self._guard(
            lambda: self._bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=_inline_markup(buttons),
            ),
            "send menu",
        )

    async def send_reply_keyboard(
        self,
        chat_id: ChatId,
        text: str,
        keyboard: ReplyKeyboardBuilder,
        options: ReplyKeyboardOptions | None = None,
    ) -> SendResult:
        return await self._guard(
            lambda: self._bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=_reply_markup(keyboard, options),
            ),
            "send reply keyboard",
        )

    async def remove_reply_keyboard(
        self, chat_id: ChatId, text: str = "", selective: bool = False
    ) -> SendResult:
        return await self._guard(
            lambda: self._bot.send_message(
                chat_id=chat_id,
                text=text or "Keyboard removed",
                reply_markup=ReplyKeyboardRemove(selective=selective),
            ),
            "remove reply keyboard",
        )

    async def edit_message_text(
        self, chat_id: ChatId, message_id: MessageId, text: str
    ) -> SendResult:
        return await self._guard(
            lambda: self._bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text
            ),
            "edit message",
        )

    async def edit_message_menu(
        self, chat_id: ChatId, message_id: MessageId, text: str, buttons: MenuGrid
    ) -> SendResult:
        return await self._guard(
            lambda: self._bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=_inline_markup(buttons),
            ),
            "edit menu",
        )
