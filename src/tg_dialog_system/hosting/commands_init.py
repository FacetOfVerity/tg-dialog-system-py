"""Register bot commands per language on startup (port TelegramBotCommandsInitService)."""

from __future__ import annotations

from typing import Any

from aiogram.types import BotCommandScopeDefault, MenuButtonCommands

from tg_dialog_system.protocols import ChatMenuButtonProvider

_DEFAULT_LANGUAGE = "en"


async def set_bot_commands(bot: Any, provider: ChatMenuButtonProvider) -> None:
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    commands_by_language = provider.get_chat_menu_buttons_by_language_code()
    for language_code, commands in commands_by_language.items():
        await bot.set_my_commands(
            commands, scope=BotCommandScopeDefault(), language_code=language_code
        )

    default_commands = commands_by_language.get(_DEFAULT_LANGUAGE)
    if default_commands is None:
        default_commands = next(iter(commands_by_language.values()), [])
    await bot.set_my_commands(
        default_commands, scope=BotCommandScopeDefault(), language_code=None
    )
