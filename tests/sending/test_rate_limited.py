from expression import Ok

from tg_dialog_system.sending.rate_limited import RateLimitedBotMessageSender


class FakeInner:
    def __init__(self):
        self.calls = []

    async def send_message(self, chat_id, message):
        self.calls.append("send_message")
        return Ok(1)


class FakeRateLimiter:
    def __init__(self):
        self.waited = 0

    async def wait_for_availability(self):
        self.waited += 1


class PassthroughRetry:
    async def execute_with_retry(self, operation, chat_id):
        return await operation()


async def test_waits_then_delegates():
    inner = FakeInner()
    limiter = FakeRateLimiter()
    sender = RateLimitedBotMessageSender(inner, limiter, PassthroughRetry())
    result = await sender.send_message(100, "hi")
    assert result == Ok(1)
    assert limiter.waited == 1
    assert inner.calls == ["send_message"]
