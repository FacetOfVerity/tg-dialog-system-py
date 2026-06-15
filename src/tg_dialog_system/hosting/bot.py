"""Bot host: wiring + lifecycle (port BotHostedService + AddTelegramBot)."""

from __future__ import annotations

import logging
from types import ModuleType
from typing import Any

from aiogram import Bot, Dispatcher

from tg_dialog_system.config import BotMode, TelegramSettings
from tg_dialog_system.hosting.commands_init import set_bot_commands
from tg_dialog_system.hosting.startup import start_with_retry
from tg_dialog_system.protocols import (
    ArbitraryTextMessageHandler,
    BotErrorsProcessor,
    ChatMenuButtonProvider,
)
from tg_dialog_system.routing.discovery import discover_handlers
from tg_dialog_system.routing.dispatcher import BotDispatcher
from tg_dialog_system.routing.registry import HandlerRegistry, default_registry
from tg_dialog_system.sending.rate_limit import SlidingWindowRateLimiter
from tg_dialog_system.sending.rate_limited import RateLimitedBotMessageSender
from tg_dialog_system.sending.reply_sender import ReplyMessageSender
from tg_dialog_system.sending.retry import RetryService
from tg_dialog_system.sending.sender import BotMessageSender

logger = logging.getLogger("tg_dialog_system.bot")


class TgDialogBot:
    def __init__(
        self,
        *,
        settings: TelegramSettings,
        chat_menu_button_provider: ChatMenuButtonProvider,
        arbitrary_text_message_handler: ArbitraryTextMessageHandler,
        errors_processor: BotErrorsProcessor,
        dependencies: dict[str, Any] | None = None,
        handler_packages: list[ModuleType] | None = None,
        registry: HandlerRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._provider = chat_menu_button_provider
        self._bot = Bot(token=settings.bot_token)
        self._dp = Dispatcher()

        registry = registry or default_registry
        for package in handler_packages or []:
            discover_handlers(package)

        core_sender = BotMessageSender(self._bot)
        rate_limiter = SlidingWindowRateLimiter(
            settings.max_messages_per_second, enabled=settings.enable_rate_limiting
        )
        retry = RetryService(settings.max_retries, settings.initial_retry_delay_ms)
        self._sender = RateLimitedBotMessageSender(core_sender, rate_limiter, retry)
        reply_sender = ReplyMessageSender(self._sender)

        deps = dict(dependencies or {})
        deps.setdefault("bot_message_sender", self._sender)

        self._dispatcher = BotDispatcher(
            registry=registry,
            reply_sender=reply_sender,
            errors_processor=errors_processor,
            arbitrary_text_handler=arbitrary_text_message_handler,
            dependencies=deps,
        )
        self._register_handlers()

    @property
    def aiogram_bot(self) -> Bot:
        return self._bot

    @property
    def aiogram_dispatcher(self) -> Dispatcher:
        return self._dp

    def _register_handlers(self) -> None:
        self._dp.message.register(self._on_message)
        self._dp.callback_query.register(self._on_callback)

    async def _on_message(self, message: Any) -> None:
        await self._dispatcher.handle_message(message)

    async def _on_callback(self, query: Any) -> None:
        await self._dispatcher.handle_callback(query)
        try:
            await query.answer()
        except Exception:  # noqa: BLE001
            logger.debug("callback answer failed", exc_info=True)

    async def run(self) -> None:
        if self._settings.mode is BotMode.WEBHOOK:
            raise NotImplementedError("Webhook mode is not implemented; use polling.")

        await start_with_retry(lambda: self._bot.get_me(), self._settings)
        await set_bot_commands(self._bot, self._provider)
        logger.info("Starting polling")
        await self._dp.start_polling(self._bot, handle_signals=False)
