import pytest

from tg_dialog_system.config import TelegramSettings
from tg_dialog_system.hosting.startup import start_with_retry

VALID_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz0123456789"


def _settings(**kwargs):
    return TelegramSettings(bot_token=VALID_TOKEN, **kwargs)


async def test_succeeds_first_try():
    sleeps = []

    async def sleep(s):
        sleeps.append(s)

    async def probe():
        return "me"

    result = await start_with_retry(probe, _settings(), sleep_func=sleep)
    assert result == "me"
    assert sleeps == []


async def test_retries_transient_then_succeeds():
    sleeps = []
    calls = {"n": 0}

    async def sleep(s):
        sleeps.append(s)

    async def probe():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "me"

    result = await start_with_retry(
        probe, _settings(startup_initial_retry_delay_ms=1000), sleep_func=sleep
    )
    assert result == "me"
    assert sleeps == [1.0, 2.0]


async def test_non_retryable_aborts_immediately():
    async def sleep(s):
        raise AssertionError("should not sleep")

    async def probe():
        raise ValueError("fatal")

    with pytest.raises(ValueError):
        await start_with_retry(
            probe, _settings(), sleep_func=sleep, non_retryable=lambda e: isinstance(e, ValueError)
        )


async def test_gives_up_after_max_retries():
    async def sleep(s):
        pass

    async def probe():
        raise RuntimeError("always")

    with pytest.raises(RuntimeError):
        await start_with_retry(probe, _settings(startup_max_retries=2), sleep_func=sleep)
