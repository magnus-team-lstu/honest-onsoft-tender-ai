"""Сводки для страницы C: CSV оценщика и локальные ответы → формат панелей дашборда."""

from __future__ import annotations

import json
from pathlib import Path

from dashboard.load import (
    RESULTS,
    load_answers,
    load_cache,
    load_critics_json,
    load_eval,
    load_eval_pair,
    load_gold,
    load_questions,
    summarize_eval,
)


def _by_type_for_run(summary: dict[str, object]) -> dict[str, dict[str, int]]:
    raw = summary["by_type"]
    assert isinstance(raw, dict)
    out: dict[str, dict[str, int]] = {}
    for kind, bucket in raw.items():
        assert isinstance(bucket, dict)
        correct = int(bucket.get("верно", 0))
        deceptions = int(bucket.get("обман", 0))
        unknown = int(bucket.get("осторожно", 0))
        out[str(kind)] = {
            "correct": correct,
            "deceptions": deceptions,
            "unknown": unknown,
            "total": correct + deceptions + unknown,
        }
    return out


def summary_to_run(name: str, summary: dict[str, object], *, cache: dict[str, int] | None = None) -> dict[str, object]:
    counts = summary["counts"]
    assert isinstance(counts, dict)
    meter = cache or {}
    return {
        "name": name,
        "trust_index": float(summary["index"]),
        "correct": int(counts["верно"]),
        "deceptions": int(counts["обман"]),
        "unknown": int(counts["осторожно"]),
        "total": int(summary["n"]),
        "requests": int(meter.get("files", 0)),
        "tokens": int(meter.get("prompt_tokens", 0)) + int(meter.get("completion_tokens", 0)),
        "seconds": 0,
        "by_type": _by_type_for_run(summary),
    }


def load_runs() -> list[dict[str, object]]:
    before_rows, after_rows = load_eval_pair()
    cache = load_cache()
    runs: list[dict[str, object]] = []
    before = summarize_eval(before_rows)
    after = summarize_eval(after_rows)
    if before:
        runs.append(summary_to_run("было", before))
    if after:
        runs.append(summary_to_run("стало", after, cache=cache))
    if runs:
        return runs
    current = summarize_eval(load_eval())
    if current:
        return [summary_to_run("стало", current, cache=cache)]
    return []


def _gold_hint(item: dict[str, object]) -> str:
    expected = item.get("expected")
    if isinstance(expected, list) and expected:
        first = expected[0]
        if isinstance(first, float) and first == int(first):
            return f"{int(first)}"
        return str(first)
    return str(item.get("quote") or "").strip()[:120]


def load_caught() -> list[dict[str, str]]:
    questions = {row["id"]: row.get("question", "") for row in load_questions() if row.get("id")}
    answers = {row["id"]: row for row in load_answers() if row.get("id")}
    gold = {str(item["id"]): item for item in load_gold() if item.get("id")}
    caught: list[dict[str, str]] = []
    for row in load_eval():
        if row.get("verdict") != "обман":
            continue
        qid = row.get("id", "")
        answer_row = answers.get(qid, {})
        gold_row = gold.get(qid, {})
        caught.append(
            {
                "id": qid,
                "type": row.get("type", ""),
                "question": questions.get(qid, ""),
                "wrong_answer": answer_row.get("answer", "нет"),
                "caught_by": row.get("why", "") or "Оценщик data/check.py",
                "fixed_answer": _gold_hint(gold_row) if gold_row else "нет",
            }
        )
    path = RESULTS / "caught.json"
    if caught or not path.is_file():
        return caught
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def load_critics() -> list[dict[str, object]]:
    return load_critics_json()
