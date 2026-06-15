"""User-facing error formatting (port BotErrorsProcessor)."""

from __future__ import annotations

from aiogram import Bot

from tg_dialog_system import errors
from tg_dialog_system.errors import Error, Errors
from tg_dialog_system.models.context import ChatId


class BotErrorsProcessor:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_errors(self, chat_id: ChatId, error_list: Errors) -> None:
        await self._bot.send_message(chat_id=chat_id, text=self._format(error_list))

    async def send_unexpected_error(self, chat_id: ChatId) -> None:
        await self._bot.send_message(
            chat_id=chat_id, text="⚠️ Something went wrong. Please try again later."
        )

    @staticmethod
    def _format(error_list: Errors) -> str:
        if not error_list:
            return "⚠️ An unknown error occurred."
        lines: list[str] = []
        for error in error_list:
            lines.append(BotErrorsProcessor._line(error))
        return "\n".join(lines)

    @staticmethod
    def _line(error: Error) -> str:
        if errors.is_validation(error):
            return f"• {error.description}"
        if errors.is_not_found(error):
            return "• Command not found"
        if errors.is_telegram_api(error):
            return "• Service temporarily unavailable"
        return "• A technical error occurred"
