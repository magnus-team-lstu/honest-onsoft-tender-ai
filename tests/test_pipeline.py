from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.llm import Completion, LlmClient
from src.loader import Package
from src.pipeline import answer_question, quote_in_file
from src.schema import Answer


def client(complete, tmp_path: Path) -> LlmClient:
    return LlmClient(complete, model="qwen3-6-practice", rpm=100_000, cache_dir=tmp_path)


def test_quote_must_sit_in_the_named_file() -> None:
    package = Package("P01", {"01_izveshchenie.txt": "Обеспечение заявки 18 000,00 рублей."})
    good = Answer(
        id="P01-03",
        status="ответ",
        answer="18000",
        quote="18 000,00 рублей",
        file="01_izveshchenie.txt",
    )
    bad = good.model_copy(update={"quote": "этой строки нет"})
    assert quote_in_file(good, package) == "ok"
    assert quote_in_file(bad, package) != "ok"


def test_baseline_asks_once_and_repeat_is_cached(tmp_path: Path) -> None:
    calls = 0
    package = Package("P01", {"01_izveshchenie.txt": "Обеспечение заявки 18 000,00 рублей."})

    async def complete(messages, temperature, max_tokens):
        nonlocal calls
        del messages, temperature, max_tokens
        calls += 1
        return Completion(
            json.dumps(
                {
                    "status": "ответ",
                    "answer": "18000",
                    "quote": "18 000,00 рублей",
                    "file": "01_izveshchenie.txt",
                },
                ensure_ascii=False,
            ),
            5,
            5,
        )

    model = client(complete, tmp_path)

    async def run():
        first = await answer_question(model, "P01-03", "размер обеспечения", package, mode="baseline")
        second = await answer_question(model, "P01-03", "размер обеспечения", package, mode="baseline")
        return first, second

    first, second = asyncio.run(run())
    assert calls == 1
    assert first.status == "ответ"
    assert second.status == "ответ"


def test_failed_quote_becomes_unknown(tmp_path: Path) -> None:
    calls = 0
    seen: list[str] = []
    package = Package("P01", {"01_izveshchenie.txt": "Обеспечение заявки 18 000,00 рублей."})

    async def complete(messages, temperature, max_tokens):
        nonlocal calls
        del temperature, max_tokens
        calls += 1
        seen.append(messages[-1]["content"])
        return Completion(
            json.dumps(
                {"status": "ответ", "answer": "1", "quote": "этой строки нет", "file": "01_izveshchenie.txt"},
                ensure_ascii=False,
            ),
            3,
            3,
        )

    answer = asyncio.run(
        answer_question(client(complete, tmp_path), "P01-03", "размер", package, mode="full", max_attempts=3)
    )
    assert calls == 3
    assert answer.status == "не знаю"
    assert any("цитаты нет" in note for note in seen)
