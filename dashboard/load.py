"""Чтение данных организатора и локальных прогонов.

Отсутствующий файл даёт пустой список. Цифры индекса считаются только из CSV оценщика.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
CACHE = ROOT / ".cache" / "llm"

VERDICTS = ("верно", "осторожно", "обман")


def read_table(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return []
    header = text.splitlines()[0]
    delimiter = ";" if header.count(";") >= header.count(",") else ","
    rows: list[dict[str, str]] = []
    for raw in csv.DictReader(text.splitlines(), delimiter=delimiter):
        row = {(key or "").strip().lower(): (value or "").strip() for key, value in raw.items()}
        if row.get("id") or any(row.values()):
            rows.append(row)
    return rows


def read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def load_questions(path: Path | None = None) -> list[dict[str, str]]:
    return read_table(path or DATA / "questions.csv")


def load_gold(path: Path | None = None) -> list[dict[str, object]]:
    source = path or DATA / "answers_public.json"
    if not source.is_file():
        return []
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    return [item for item in data if isinstance(item, dict)]


def load_packages(path: Path | None = None) -> list[dict[str, object]]:
    root = path or DATA / "packages"
    if not root.is_dir():
        return []
    packages: list[dict[str, object]] = []
    for folder in sorted(item for item in root.iterdir() if item.is_dir()):
        files = sorted(file.name for file in folder.glob("*.txt"))
        packages.append(
            {
                "id": folder.name,
                "files": len(files),
                "names": files,
                "changes": "05_izmeneniya_izveshcheniya.txt" in files,
            }
        )
    return packages


def load_cache(path: Path | None = None) -> dict[str, int]:
    root = path or CACHE
    summary = {"files": 0, "prompt_tokens": 0, "completion_tokens": 0}
    if not root.is_dir():
        return summary
    for file in sorted(root.glob("*.json")):
        try:
            item = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(item, dict):
            continue
        summary["files"] += 1
        summary["prompt_tokens"] += int(item.get("prompt_tokens") or 0)
        summary["completion_tokens"] += int(item.get("completion_tokens") or 0)
    return summary


def load_answers(path: Path | None = None) -> list[dict[str, str]]:
    return read_table(path or RESULTS / "answers.csv")


def load_eval(path: Path | None = None) -> list[dict[str, str]]:
    return read_table(path or RESULTS / "eval.csv")


def load_eval_pair(
    before: Path | None = None,
    after: Path | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    return (
        read_table(before or RESULTS / "eval_before.csv"),
        read_table(after or RESULTS / "eval_after.csv"),
    )


def load_verdicts(path: Path | None = None) -> list[dict[str, object]]:
    return read_jsonl(path or RESULTS / "verdicts.jsonl")


def load_critics_json(path: Path | None = None) -> list[dict[str, object]]:
    source = path or RESULTS / "critics.json"
    if not source.is_file():
        return []
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def count_by(rows: list[dict[str, object]], key: str) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter[str(row.get(key) or "без значения")] += 1
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def summarize_eval(rows: list[dict[str, str]]) -> dict[str, object] | None:
    if not rows:
        return None
    counts = {name: 0 for name in VERDICTS}
    by_type: dict[str, dict[str, int]] = {}
    for row in rows:
        verdict = row.get("verdict", "")
        kind = row.get("type") or "без типа"
        bucket = by_type.setdefault(kind, {name: 0 for name in VERDICTS})
        if verdict in counts:
            counts[verdict] += 1
            bucket[verdict] += 1
    total = len(rows)
    return {
        "n": total,
        "counts": counts,
        "index": (counts["верно"] - counts["обман"]) / total * 100,
        "by_type": by_type,
        "lies": [row for row in rows if row.get("verdict") == "обман"],
    }
