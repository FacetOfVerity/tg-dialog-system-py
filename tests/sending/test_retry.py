from expression import Error as Err
from expression import Ok

from tg_dialog_system import errors
from tg_dialog_system.sending.retry import RetryService


def make_service(**kwargs):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    service = RetryService(
        max_retries=3, initial_retry_delay_ms=1000, sleep_func=fake_sleep, **kwargs
    )
    return service, sleeps


async def test_success_returns_immediately():
    service, sleeps = make_service()

    async def op():
        return Ok(1)

    result = await service.execute_with_retry(op, chat_id=10)
    assert result == Ok(1)
    assert sleeps == []


async def test_non_429_error_not_retried():
    service, sleeps = make_service()

    async def op():
        return Err([errors.validation("X", "bad")])

    result = await service.execute_with_retry(op, chat_id=10)
    assert result.is_error()
    assert sleeps == []


async def test_429_retries_then_succeeds_using_retry_after():
    service, sleeps = make_service()
    calls = {"n": 0}

    async def op():
        calls["n"] += 1
        if calls["n"] == 1:
            return Err([errors.telegram_api("Telegram.Api.429", "flood", retry_after=4)])
        return Ok(99)

    result = await service.execute_with_retry(op, chat_id=10)
    assert result == Ok(99)
    assert sleeps == [4]


async def test_429_gives_up_after_max_retries():
    service, sleeps = make_service()

    async def op():
        return Err([errors.telegram_api("Telegram.Api.429", "flood")])

    result = await service.execute_with_retry(op, chat_id=10)
    assert result.is_error()
    # max_retries=3 -> sleeps between attempts 1->2 and 2->3 (exponential backoff)
    assert sleeps == [1.0, 2.0]
