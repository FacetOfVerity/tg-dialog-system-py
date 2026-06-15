"""Retry-on-429 with exponential backoff (port TelegramRetryService)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from expression import Result

from tg_dialog_system.errors import Error as DomainError
from tg_dialog_system.errors import ErrorType
from tg_dialog_system.models.context import ChatId

_RATE_LIMIT_CODE = "Telegram.Api.429"

Operation = Callable[[], Awaitable[Result]]


def _find_429(errs: list[DomainError]) -> DomainError | None:
    for err in errs:
        if err.type is ErrorType.TELEGRAM_API and err.code == _RATE_LIMIT_CODE:
            return err
    return None


class RetryService:
    def __init__(
        self,
        max_retries: int,
        initial_retry_delay_ms: int,
        *,
        sleep_func: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._max_retries = max_retries
        self._initial_delay_ms = initial_retry_delay_ms
        self._sleep = sleep_func

    async def execute_with_retry(self, operation: Operation, chat_id: ChatId) -> Result:
        attempt = 0
        while True:
            attempt += 1
            result = await operation()
            if result.is_ok():
                return result
            rate_error = _find_429(result.error)
            if rate_error is None or attempt >= self._max_retries:
                return result
            retry_after = (rate_error.metadata or {}).get("retry_after")
            if retry_after:
                delay = float(retry_after)
            else:
                delay = (self._initial_delay_ms / 1000) * (2 ** (attempt - 1))
            await self._sleep(delay)
