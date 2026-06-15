"""Async sliding-window rate limiter (port TelegramRateLimitService)."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable


class SlidingWindowRateLimiter:
    def __init__(
        self,
        permit_limit: int,
        *,
        enabled: bool = True,
        window: float = 1.0,
        time_func: Callable[[], float] = time.monotonic,
        sleep_func: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._permit_limit = permit_limit
        self._enabled = enabled
        self._window = window
        self._time = time_func
        self._sleep = sleep_func
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    @property
    def queued_count(self) -> int:
        return len(self._timestamps)

    async def wait_for_availability(self) -> None:
        if not self._enabled:
            return
        async with self._lock:
            while True:
                now = self._time()
                while self._timestamps and now - self._timestamps[0] >= self._window:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._permit_limit:
                    self._timestamps.append(now)
                    return
                wait = self._window - (now - self._timestamps[0])
                if wait > 0:
                    await self._sleep(wait)
