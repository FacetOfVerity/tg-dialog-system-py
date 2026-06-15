"""Startup probe with exponential-backoff retry (port TryStartBotWithRetryAsync)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from aiogram.exceptions import TelegramUnauthorizedError

from tg_dialog_system.config import TelegramSettings

logger = logging.getLogger("tg_dialog_system.startup")


def _default_non_retryable(exc: Exception) -> bool:
    return isinstance(exc, TelegramUnauthorizedError)


async def start_with_retry[T](
    probe: Callable[[], Awaitable[T]],
    settings: TelegramSettings,
    *,
    sleep_func: Callable[[float], Awaitable[None]] = asyncio.sleep,
    non_retryable: Callable[[Exception], bool] = _default_non_retryable,
) -> T:
    attempt = 0
    last_exc: Exception | None = None

    while attempt < settings.startup_max_retries:
        attempt += 1
        try:
            return await probe()
        except Exception as exc:  # noqa: BLE001
            if non_retryable(exc):
                logger.error("Non-retryable startup error: %s", type(exc).__name__)
                raise
            last_exc = exc
            if not settings.enable_startup_retries or attempt >= settings.startup_max_retries:
                break
            delay = (settings.startup_initial_retry_delay_ms / 1000) * (2 ** (attempt - 1))
            logger.warning(
                "Bot startup attempt %d/%d failed (%s); retrying in %.1fs",
                attempt, settings.startup_max_retries, type(exc).__name__, delay,
            )
            await sleep_func(delay)

    raise RuntimeError(
        f"Failed to start Telegram bot after {settings.startup_max_retries} attempts"
    ) from last_exc
