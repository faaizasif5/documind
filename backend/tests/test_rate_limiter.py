import pytest

from app.services.rate_limiter import SlidingWindowRateLimiter


class _FakeClock:
    """Deterministic time: sleeping advances the clock instantly."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _limiter(clock: _FakeClock, rpm: int = 100, tpm: int = 1_000_000) -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(rpm, tpm, margin_seconds=0, clock=clock, sleep=clock.sleep)


async def test_admits_immediately_within_limit() -> None:
    clock = _FakeClock()
    limiter = _limiter(clock)

    await limiter.acquire(60, 10)
    await limiter.acquire(40, 10)

    assert clock.sleeps == []


async def test_waits_until_oldest_grant_leaves_window() -> None:
    clock = _FakeClock()
    limiter = _limiter(clock)
    await limiter.acquire(64, 10)
    clock.now = 5.0

    await limiter.acquire(64, 10)

    # The first 64 must expire (t=60) before another 64 fits under 100.
    assert clock.now == pytest.approx(60.0)


async def test_never_exceeds_limit_in_any_window() -> None:
    clock = _FakeClock()
    limiter = _limiter(clock, rpm=100)
    grants: list[tuple[float, int]] = []

    for _ in range(20):
        await limiter.acquire(32, 1)
        grants.append((clock.now, 32))

    for start, _ in grants:
        in_window = sum(n for at, n in grants if start <= at < start + 60.0)
        assert in_window <= 100


async def test_token_limit_is_enforced() -> None:
    clock = _FakeClock()
    limiter = _limiter(clock, rpm=100, tpm=1_000)
    await limiter.acquire(1, 800)

    await limiter.acquire(1, 300)

    assert clock.now == pytest.approx(60.0)


async def test_reserve_holds_back_headroom_for_queries() -> None:
    clock = _FakeClock()
    limiter = _limiter(clock, rpm=100)
    await limiter.acquire(80, 1, reserve_requests=10)

    # Background batch of 20 would leave fewer than 10 free -> must wait.
    await limiter.acquire(20, 1, reserve_requests=10)
    assert clock.now == pytest.approx(60.0)


async def test_query_can_use_reserve_while_background_waits() -> None:
    clock = _FakeClock()
    limiter = _limiter(clock, rpm=100)
    await limiter.acquire(90, 1, reserve_requests=10)

    await limiter.acquire(1, 1)

    assert clock.sleeps == []


async def test_oversized_batch_is_rejected() -> None:
    limiter = _limiter(_FakeClock(), rpm=100)
    with pytest.raises(ValueError, match="never fit"):
        await limiter.acquire(95, 1, reserve_requests=10)


async def test_oversized_token_request_is_admitted_alone() -> None:
    clock = _FakeClock()
    limiter = _limiter(clock, rpm=100, tpm=1_000)

    await limiter.acquire(1, 5_000)

    assert clock.sleeps == []


async def test_safety_margin_extends_window() -> None:
    clock = _FakeClock()
    limiter = SlidingWindowRateLimiter(100, 1_000_000, clock=clock, sleep=clock.sleep)
    await limiter.acquire(64, 1)

    await limiter.acquire(64, 1)

    assert clock.now == pytest.approx(65.0)


async def test_pause_holds_all_callers() -> None:
    clock = _FakeClock()
    limiter = _limiter(clock)
    limiter.pause_for(40.0)

    await limiter.acquire(1, 1)

    assert clock.now == pytest.approx(40.0)
