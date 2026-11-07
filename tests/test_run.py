from __future__ import annotations

import json
from pathlib import Path

from src.llm import Completion, LlmClient
from src.run import build_parser, execute
from src.schema import read_csv


def test_limit_resume_and_cached_repeat(tmp_path: Path) -> None:
    calls = 0
    packages = tmp_path / "packages" / "P01"
    packages.mkdir(parents=True)
    (packages / "01_izveshchenie.txt").write_text("Обеспечение заявки 18 000,00 рублей.", encoding="utf-8")
    questions = tmp_path / "questions.csv"
    questions.write_text(
        "id;package;question\nP01-01;P01;первая\nP01-02;P01;вторая\n",
        encoding="utf-8",
    )
    out = tmp_path / "answers.csv"

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
            4,
            2,
        )

    model = LlmClient(complete, model="qwen3-6-practice", rpm=100_000, cache_dir=tmp_path / "cache")
    parser = build_parser()
    first = execute(
        model,
        parser.parse_args(
            ["--questions", str(questions), "--packages", str(tmp_path / "packages"), "--out", str(out), "--mode", "baseline", "--limit", "1"]
        ),
    )
    assert first.questions == 1
    assert calls == 1
    assert [row.id for row in read_csv(out)] == ["P01-01"]

    second = execute(
        model,
        parser.parse_args(
            ["--questions", str(questions), "--packages", str(tmp_path / "packages"), "--out", str(out), "--mode", "baseline", "--resume"]
        ),
    )
    assert second.questions == 1
    assert calls == 2
    assert [row.id for row in read_csv(out)] == ["P01-01", "P01-02"]

    third = execute(
        model,
        parser.parse_args(
            ["--questions", str(questions), "--packages", str(tmp_path / "packages"), "--out", str(out), "--mode", "baseline"]
        ),
    )
    assert third.calls == 0
    assert third.cached == 2
    assert calls == 2
