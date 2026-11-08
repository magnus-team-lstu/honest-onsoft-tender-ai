from __future__ import annotations

import json
from pathlib import Path

from dashboard.load import (
    load_cache,
    load_eval,
    load_gold,
    load_packages,
    load_questions,
    load_verdicts,
    read_table,
    summarize_eval,
)


def test_organizer_data_is_present() -> None:
    assert len(load_questions()) == 71
    assert len(load_gold()) == 71
    packages = load_packages()
    assert [item["id"] for item in packages] == ["P01", "P02", "P03", "P04", "P05", "P06"]
    assert sum(1 for item in packages if item["changes"]) == 3


def test_missing_files_are_empty(tmp_path: Path) -> None:
    assert read_table(tmp_path / "no.csv") == []
    assert load_verdicts(tmp_path / "no.jsonl") == []
    assert load_cache(tmp_path / "cache") == {"files": 0, "prompt_tokens": 0, "completion_tokens": 0}
    assert summarize_eval([]) is None


def test_eval_index_uses_only_the_file(tmp_path: Path) -> None:
    path = tmp_path / "eval.csv"
    path.write_text(
        "id;type;verdict;why\n"
        "P01-01;факт;верно;\n"
        "P01-02;факт;верно;\n"
        "P01-03;факт;обман;неверное значение\n"
        "P01-04;факт;осторожно;\n",
        encoding="utf-8",
    )
    summary = summarize_eval(load_eval(path))
    assert summary is not None
    assert summary["n"] == 4
    assert summary["index"] == 25
    assert len(summary["lies"]) == 1


def test_broken_verdict_line_is_skipped(tmp_path: Path) -> None:
    path = tmp_path / "verdicts.jsonl"
    path.write_text(
        '{"id": "P01-01", "check": "quote", "verdict": "ok"}\n'
        "не json\n"
        '{"id": "P01-02", "check": "number", "verdict": "числа нет в цитате"}\n',
        encoding="utf-8",
    )
    rows = load_verdicts(path)
    assert [row["id"] for row in rows] == ["P01-01", "P01-02"]


def test_cache_sums_tokens(tmp_path: Path) -> None:
    (tmp_path / "one.json").write_text(
        json.dumps({"prompt_tokens": 10, "completion_tokens": 4, "text": "ок"}),
        encoding="utf-8",
    )
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    assert load_cache(tmp_path) == {"files": 1, "prompt_tokens": 10, "completion_tokens": 4}
