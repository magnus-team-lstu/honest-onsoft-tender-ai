from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.schema import Answer, parse_answer, write_csv

ROOT = Path(__file__).resolve().parents[1]


def test_answer_is_required_for_status_answer() -> None:
    with pytest.raises(ValidationError):
        Answer(id="P01-01", status="ответ", answer="", quote="12345678", file="01_izveshchenie.txt")


def test_parse_takes_the_first_json_object() -> None:
    text = (
        'черновик {"id":"чужой","status":"не знаю","answer":"","quote":"","file":""}'
        ' {"id":"ещё","status":"ответ","answer":"1","quote":"12345678","file":"a.txt"}'
    )
    answer = parse_answer(text, "P01-01")
    assert answer.id == "P01-01"
    assert answer.status == "не знаю"


def test_check_py_accepts_the_csv(tmp_path: Path) -> None:
    path = tmp_path / "answers.csv"
    write_csv(path, [Answer(id="P01-13", status="нет в документах")])
    completed = subprocess.run(
        [sys.executable, str(ROOT / "data" / "check.py"), str(path)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT / "data",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert completed.returncode == 0
    assert "RESULT" in completed.stdout
