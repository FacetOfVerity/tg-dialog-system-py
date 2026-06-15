"""Routes aiogram updates to handlers, injects deps, applies Result handling.

Ports BotUserInputRouter + BotMessagesRouter + CallbackQueriesRouter.
"""

from __future__ import annotations

import logging
from typing import Any

from expression import Error as Err
from expression import Result

from tg_dialog_system import errors
from tg_dialog_system.models.callback_data import CallbackData
from tg_dialog_system.models.context import CallbackContext, ChatId, MessageContext
from tg_dialog_system.protocols import ArbitraryTextMessageHandler, BotErrorsProcessor
from tg_dialog_system.routing.registry import HandlerEntry, HandlerRegistry

logger = logging.getLogger("tg_dialog_system.dispatcher")


class BotDispatcher:
    def __init__(
        self,
        *,
        registry: HandlerRegistry,
        reply_sender: Any,
        errors_processor: BotErrorsProcessor,
        arbitrary_text_handler: ArbitraryTextMessageHandler,
        dependencies: dict[str, Any] | None = None,
    ) -> None:
        self._registry = registry
        self._reply_sender = reply_sender
        self._errors = errors_processor
        self._arbitrary = arbitrary_text_handler
        self._deps = dependencies or {}

    async def _invoke(self, entry: HandlerEntry, context: Any) -> Result:
        params = list(entry.signature.parameters.values())
        kwargs: dict[str, Any] = {}
        for param in params[1:]:
            if param.name not in self._deps:
                raise LookupError(
                    f"Dependency '{param.name}' for handler '{entry.key}' is not registered"
                )
            kwargs[param.name] = self._deps[param.name]
        return await entry.func(context, **kwargs)

    async def _send_result(self, chat_id: ChatId, result: Result) -> None:
        if result.is_error():
            await self._errors.send_errors(chat_id, result.error)
            return
        send_result = await self._reply_sender.send(chat_id, result.ok)
        if send_result.is_error():
            await self._errors.send_errors(chat_id, send_result.error)

    async def handle_message(self, message: Any) -> None:
        chat_id = message.chat.id
        try:
            text = (message.text or "").strip()
            if not text:
                result: Result = Err([errors.failure(
                    "Telegram.Routing.EmptyMessageText", "Message text cannot be empty"
                )])
            else:
                context = MessageContext(
                    user_id=message.from_user.id,
                    chat_id=chat_id,
                    message_id=message.message_id,
                    language_code=message.from_user.language_code,
                )
                if not text.startswith("/"):
                    result = await self._arbitrary.handle(context, text)
                else:
                    lookup = self._registry.get_command(text)
                    if lookup.is_error():
                        result = Err(lookup.error)
                    else:
                        result = await self._invoke(lookup.ok, context)
            await self._send_result(chat_id, result)
        except Exception:  # noqa: BLE001 - top-level safety net
            logger.exception("Unhandled error processing message")
            await self._try_unexpected(chat_id)

    async def handle_callback(self, query: Any) -> None:
        chat_id = query.message.chat.id
        try:
            parsed = CallbackData.parse(query.data)
            if parsed.is_error():
                result: Result = Err(parsed.error)
            else:
                callback_data = parsed.ok
                lookup = self._registry.get_callback(callback_data.route_key)
                if lookup.is_error():
                    result = Err(lookup.error)
                else:
                    context = CallbackContext(
                        user_id=query.from_user.id,
                        chat_id=chat_id,
                        message_id=query.message.message_id,
                        language_code=query.from_user.language_code,
                        payload=callback_data.payload,
                    )
                    result = await self._invoke(lookup.ok, context)
            await self._send_result(chat_id, result)
        except Exception:  # noqa: BLE001 - top-level safety net
            logger.exception("Unhandled error processing callback")
            await self._try_unexpected(chat_id)

    async def _try_unexpected(self, chat_id: ChatId) -> None:
        try:
            await self._errors.send_unexpected_error(chat_id)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to send unexpected-error message")
