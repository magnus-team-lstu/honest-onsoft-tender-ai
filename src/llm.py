from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_ATTEMPTS = 4


class LlmResult(TypedDict):
    text: str
    prompt_tokens: int
    completion_tokens: int
    seconds: float
    cached: bool


@dataclass(frozen=True)
class Completion:
    text: str
    prompt_tokens: int
    completion_tokens: int


Complete = Callable[[list[dict[str, str]], float, int], Awaitable[Completion]]
Sleep = Callable[[float], Awaitable[None]]
Clock = Callable[[], float]
Rng = Callable[[float, float], float]


def strip_think(text: str) -> str:
    return _THINK.sub("", text).strip()


def cache_key(model: str, messages: list[dict[str, str]], temperature: float) -> str:
    payload = json.dumps(
        {"model": model, "messages": messages, "temperature": temperature},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LlmClient:
    def __init__(
        self,
        complete: Complete,
        *,
        model: str,
        rpm: float = 40,
        concurrency: int = 2,
        cache_dir: Path = Path(".cache/llm"),
        sleep: Sleep | None = None,
        now: Clock | None = None,
        rng: Rng | None = None,
    ) -> None:
        self._complete = complete
        self.model = model
        self._interval = 60.0 / max(rpm, 1)
        self._sem = asyncio.Semaphore(max(concurrency, 1))
        self._pace = asyncio.Lock()
        self._next_start = 0.0
        self._cache_dir = cache_dir
        self._sleep = sleep or asyncio.sleep
        self._now = now or time.monotonic
        self._rng = rng or random.uniform

    async def ask(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0,
        max_tokens: int = 800,
        use_cache: bool = True,
        tag: str = "",
    ) -> LlmResult:
        del tag
        if use_cache:
            cached = self._read_cache(messages, temperature)
            if cached is not None:
                return cached
        result = await self._call(messages, temperature, max_tokens)
        if use_cache and result["text"]:
            self._write_cache(messages, temperature, result)
        return result

    async def _call(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LlmResult:
        for attempt in range(1, _ATTEMPTS + 1):
            await self._wait_turn()
            await self._sem.acquire()
            started = self._now()
            try:
                completion = await self._complete(messages, temperature, max_tokens)
            except (RateLimitError, APIConnectionError, APITimeoutError) as error:
                failure = error
            else:
                return {
                    "text": strip_think(completion.text),
                    "prompt_tokens": completion.prompt_tokens,
                    "completion_tokens": completion.completion_tokens,
                    "seconds": self._now() - started,
                    "cached": False,
                }
            finally:
                self._sem.release()
            if attempt == _ATTEMPTS:
                raise failure
            if isinstance(failure, RateLimitError):
                await self._sleep(60 + self._rng(0, 5))
            else:
                await self._sleep(float(2 ** (attempt - 1)))
        raise RuntimeError("llm retries exhausted")

    async def _wait_turn(self) -> None:
        async with self._pace:
            now = self._now()
            delay = self._next_start - now
            if delay > 0:
                await self._sleep(delay)
                now = self._now()
            self._next_start = now + self._interval

    def _path(self, messages: list[dict[str, str]], temperature: float) -> Path:
        return self._cache_dir / f"{cache_key(self.model, messages, temperature)}.json"

    def _read_cache(self, messages: list[dict[str, str]], temperature: float) -> LlmResult | None:
        path = self._path(messages, temperature)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "text": str(data["text"]),
            "prompt_tokens": int(data["prompt_tokens"]),
            "completion_tokens": int(data["completion_tokens"]),
            "seconds": float(data["seconds"]),
            "cached": True,
        }

    def _write_cache(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        result: LlmResult,
    ) -> None:
        path = self._path(messages, temperature)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: value for key, value in result.items() if key != "cached"}
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)


def make_client() -> LlmClient:
    load_dotenv()
    key = os.environ.get("ONSOFT_API_KEY") or os.environ.get("LLM_API_KEY")
    if not key:
        raise RuntimeError("ONSOFT_API_KEY is not set")
    sdk = AsyncOpenAI(
        base_url=os.environ.get("LLM_BASE_URL", "https://ai.on-soft.ru/v1"),
        api_key=key,
        max_retries=0,
    )
    model = os.environ.get("LLM_MODEL", "qwen3-6-practice")
    rpm = float(os.environ.get("LLM_RPM", "40"))
    concurrency = int(os.environ.get("LLM_MAX_CONCURRENCY", "2"))

    async def complete(
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        response = await sdk.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body={"enable_thinking": False},
        )
        content = response.choices[0].message.content or ""
        usage = response.usage
        return Completion(
            text=content,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )

    return LlmClient(
        complete,
        model=model,
        rpm=rpm,
        concurrency=concurrency,
    )
