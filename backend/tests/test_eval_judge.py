"""Judge parsing, caching and throttled retries with a fake client (no API calls)."""

import json
from pathlib import Path
from typing import Any

import httpx
import openai
import pytest

from app.services.rate_limiter import SlidingWindowRateLimiter
from evals.judge import (
    Judge,
    JudgeCache,
    JudgeError,
    JudgeVerdict,
    build_judge_prompt,
    judge_cache_key,
)
from evals.throttle import rate_limit_signal

_VALID = json.dumps(
    {"refused": False, "faithfulness": 5, "correctness": 4, "rationale": "Supported."}
)


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.now += seconds


class _Client:
    def __init__(self, replies: list[str | Exception]) -> None:
        self._replies = list(replies)
        self.calls = 0

    async def complete_json(self, system: str, user: str) -> str:
        self.calls += 1
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def _judge(client: _Client, cache: JudgeCache, clock: _Clock | None = None) -> Judge:
    clock = clock or _Clock()
    limiter = SlidingWindowRateLimiter(100, 10**9, clock=clock, sleep=clock.sleep)
    return Judge(client, cache, limiter, model="judge-m", max_attempts=3)


async def _evaluate(judge: Judge, reference: str | None = "Ref.") -> JudgeVerdict:
    return await judge.evaluate(
        question="Q?", reference_answer=reference, answer="A [Source 1]", sources=[("S1", "text")]
    )


async def test_valid_verdict_is_cached(tmp_path: Path) -> None:
    cache = JudgeCache(tmp_path / "judge.jsonl")
    client = _Client([_VALID])
    judge = _judge(client, cache)

    first = await _evaluate(judge)
    second = await _evaluate(judge)

    assert first == second
    assert client.calls == 1
    assert judge.cache_hits == 1


async def test_cache_survives_save_and_load(tmp_path: Path) -> None:
    path = tmp_path / "judge.jsonl"
    cache = JudgeCache(path)
    await _evaluate(_judge(_Client([_VALID]), cache))
    cache.save()

    reloaded_client = _Client([])
    await _evaluate(_judge(reloaded_client, JudgeCache.load(path)))

    assert reloaded_client.calls == 0


async def test_invalid_json_is_retried_once_then_fails(tmp_path: Path) -> None:
    cache = JudgeCache(tmp_path / "judge.jsonl")
    ok = await _evaluate(_judge(_Client(["not json", _VALID]), cache))
    assert ok is not None

    with pytest.raises(JudgeError):
        await _evaluate(
            _judge(_Client(['{"faithfulness": 9}', "{}"]), JudgeCache(tmp_path / "j2.jsonl"))
        )


async def test_correctness_dropped_without_reference(tmp_path: Path) -> None:
    verdict = await _evaluate(_judge(_Client([_VALID]), JudgeCache(tmp_path / "j.jsonl")), None)
    assert verdict.correctness is None


def _rate_limit_error(retry_after: str | None, message: str = "slow down") -> openai.RateLimitError:
    headers = {"retry-after": retry_after} if retry_after else {}
    # openai>=3 types this as httpx2.Response, older versions as httpx.Response; both accept
    # an httpx.Response at runtime, so keep the test independent of the SDK's HTTP library.
    response: Any = httpx.Response(429, headers=headers, request=httpx.Request("POST", "https://x"))
    return openai.RateLimitError(message, response=response, body=None)


async def test_429_pauses_for_retry_after_then_succeeds(tmp_path: Path) -> None:
    clock = _Clock()
    client = _Client([_rate_limit_error("7"), _VALID])

    await _evaluate(_judge(client, JudgeCache(tmp_path / "j.jsonl"), clock))

    assert client.calls == 2
    assert clock.now == pytest.approx(7.0)


def test_rate_limit_signal_ignores_other_errors() -> None:
    assert rate_limit_signal(ValueError("x")) is None
    signal = rate_limit_signal(_rate_limit_error(None))
    assert signal is not None and signal.retry_after_seconds is None


async def test_groq_daily_token_limit_stops_without_retrying(tmp_path: Path) -> None:
    tpd = _rate_limit_error("252", "Rate limit reached ... on tokens per day (TPD): Limit 200000")
    client = _Client([tpd, _VALID])

    with pytest.raises(openai.RateLimitError):
        await _evaluate(_judge(client, JudgeCache(tmp_path / "j.jsonl")))

    assert client.calls == 1
    signal = rate_limit_signal(tpd)
    assert signal is not None and signal.daily_quota


def test_cache_key_changes_with_prompt_content() -> None:
    a = build_judge_prompt("Q", "R", "A", [("S1", "t")])
    b = build_judge_prompt("Q", "R", "A2", [("S1", "t")])
    assert judge_cache_key("m", a) != judge_cache_key("m", b)
    assert judge_cache_key("m", a) != judge_cache_key("m2", a)
