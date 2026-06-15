"""Bot command menu per language (port ChatMenuButtonProvider)."""

from __future__ import annotations

from aiogram.types import BotCommand


class ChatMenuButtonProvider:
    def get_chat_menu_buttons_by_language_code(self) -> dict[str, list[BotCommand]]:
        return {
            "en": [
                BotCommand(command="start", description="Start the bot"),
                BotCommand(command="contact", description="Contact support"),
                BotCommand(command="hide", description="Hide keyboard"),
            ],
            "ru": [
                BotCommand(command="start", description="Запустить бота"),
                BotCommand(command="contact", description="Поддержка"),
                BotCommand(command="hide", description="Скрыть клавиатуру"),
            ],
        }
