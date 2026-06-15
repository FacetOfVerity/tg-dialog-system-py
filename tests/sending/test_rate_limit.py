from tg_dialog_system.sending.rate_limit import SlidingWindowRateLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def time(self):
        return self.now

    async def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


async def test_disabled_never_sleeps():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(
        2, enabled=False, time_func=clock.time, sleep_func=clock.sleep
    )
    for _ in range(5):
        await limiter.wait_for_availability()
    assert clock.sleeps == []


async def test_admits_up_to_limit_without_sleeping():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(
        2, window=1.0, time_func=clock.time, sleep_func=clock.sleep
    )
    await limiter.wait_for_availability()
    await limiter.wait_for_availability()
    assert clock.sleeps == []


async def test_third_call_waits_for_window():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(
        2, window=1.0, time_func=clock.time, sleep_func=clock.sleep
    )
    await limiter.wait_for_availability()
    await limiter.wait_for_availability()
    await limiter.wait_for_availability()
    assert clock.sleeps and clock.sleeps[0] > 0
