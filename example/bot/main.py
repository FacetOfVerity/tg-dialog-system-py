"""Run the example pizza/contact bot.

Usage:
    TELEGRAM__BOT_TOKEN=123:abc... uv run python -m example.bot.main
"""

from __future__ import annotations

import asyncio
import logging

import example.bot.features as features
from example.bot.infrastructure.arbitrary_text_handler import ArbitraryTextMessageHandler
from example.bot.infrastructure.chat_menu_button_provider import ChatMenuButtonProvider
from example.bot.infrastructure.errors_processor import BotErrorsProcessor
from example.bot.services.localization import LocalizationService
from example.bot.services.order_state import OrderState
from tg_dialog_system import TelegramSettings, TgDialogBot


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = TelegramSettings()  # reads TELEGRAM__BOT_TOKEN from env / .env

    localization = LocalizationService()
    order_state = OrderState()

    bot = TgDialogBot(
        settings=settings,
        chat_menu_button_provider=ChatMenuButtonProvider(),
        arbitrary_text_message_handler=ArbitraryTextMessageHandler(localization),
        errors_processor=BotErrorsProcessor(None),  # replaced below with the real Bot
        dependencies={"localization": localization, "order_state": order_state},
        handler_packages=[features],
    )
    # The errors processor needs the live aiogram Bot; inject it now that it exists.
    bot._dispatcher._errors = BotErrorsProcessor(bot.aiogram_bot)  # noqa: SLF001
    await bot.run()


if __name__ == "__main__":
    asyncio.run(_main())
