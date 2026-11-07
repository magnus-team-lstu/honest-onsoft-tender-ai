from __future__ import annotations

import asyncio
from pathlib import Path

import httpx2
from openai import APIConnectionError, RateLimitError

from src.llm import Completion, LlmClient


class Clock:
    def __init__(self) -> None:
        self.t = 0.0
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.t

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


def rate_limit() -> RateLimitError:
    request = httpx2.Request("POST", "https://example.test/v1/chat/completions")
    response = httpx2.Response(429, request=request)
    return RateLimitError("rate limit", response=response, body=None)


def connection_error() -> APIConnectionError:
    request = httpx2.Request("POST", "https://example.test/v1/chat/completions")
    return APIConnectionError(request=request)


def test_concurrency_stays_at_two(tmp_path: Path) -> None:
    active = 0
    peak = 0

    async def complete(
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        nonlocal active, peak
        del temperature, max_tokens
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.05)
        active -= 1
        return Completion(messages[0]["content"], 3, 1)

    client = LlmClient(
        complete,
        model="qwen3-6-practice",
        rpm=100_000,
        concurrency=2,
        cache_dir=tmp_path,
    )

    async def run() -> None:
        await asyncio.gather(
            *[client.ask([{"role": "user", "content": str(i)}]) for i in range(5)]
        )

    asyncio.run(run())
    assert peak == 2


def test_repeat_comes_from_cache(tmp_path: Path) -> None:
    calls = 0

    async def complete(
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        nonlocal calls
        del messages, temperature, max_tokens
        calls += 1
        return Completion("готово", 10, 2)

    client = LlmClient(complete, model="m", rpm=100_000, cache_dir=tmp_path)
    messages = [{"role": "user", "content": "тот же вопрос"}]

    async def run() -> tuple[dict[str, object], dict[str, object]]:
        first = await client.ask(messages)
        second = await client.ask(messages)
        return first, second

    first, second = asyncio.run(run())
    assert calls == 1
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["text"] == "готово"


def test_think_block_is_removed(tmp_path: Path) -> None:
    async def complete(
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        del messages, temperature, max_tokens
        return Completion("<think>\nчерновик\n</think>\n18000", 4, 4)

    client = LlmClient(complete, model="m", rpm=100_000, cache_dir=tmp_path)
    result = asyncio.run(client.ask([{"role": "user", "content": "сумма"}]))
    assert result["text"] == "18000"
    assert "<think>" not in result["text"]


def test_rate_limit_retries(tmp_path: Path) -> None:
    calls = 0
    clock = Clock()

    async def complete(
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        nonlocal calls
        del messages, temperature, max_tokens
        calls += 1
        if calls == 1:
            raise rate_limit()
        return Completion("повтор", 1, 1)

    client = LlmClient(
        complete,
        model="m",
        rpm=100_000,
        cache_dir=tmp_path,
        sleep=clock.sleep,
        now=clock.now,
        rng=lambda _start, _end: 0.0,
    )
    result = asyncio.run(client.ask([{"role": "user", "content": "ещё"}]))
    assert calls == 2
    assert result["text"] == "повтор"
    assert any(60 <= pause <= 65 for pause in clock.sleeps)


def test_connection_error_uses_backoff(tmp_path: Path) -> None:
    calls = 0
    clock = Clock()

    async def complete(
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        nonlocal calls
        del messages, temperature, max_tokens
        calls += 1
        if calls < 3:
            raise connection_error()
        return Completion("сеть", 1, 1)

    client = LlmClient(
        complete,
        model="m",
        rpm=100_000,
        cache_dir=tmp_path,
        sleep=clock.sleep,
        now=clock.now,
        rng=lambda _start, _end: 0.0,
    )
    result = asyncio.run(client.ask([{"role": "user", "content": "сеть"}]))
    assert result["text"] == "сеть"
    assert [pause for pause in clock.sleeps if pause >= 1] == [1.0, 2.0]
