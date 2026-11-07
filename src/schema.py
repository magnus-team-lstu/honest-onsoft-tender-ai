"""Контракт ответа и запись answers.csv."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, model_validator

Status = Literal["ответ", "расхождение", "нет в документах", "не знаю"]
COLUMNS = ("id", "status", "answer", "quote", "file")


class Answer(BaseModel):
    id: str
    status: Status
    answer: str = ""
    quote: str = ""
    file: str = ""

    @model_validator(mode="before")
    @classmethod
    def blanks(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        cleaned = dict(value)
        for key in COLUMNS:
            if cleaned.get(key) is None:
                cleaned[key] = ""
            elif key in cleaned:
                cleaned[key] = str(cleaned[key]).strip()
        return cleaned

    @model_validator(mode="after")
    def answer_required(self) -> Answer:
        if self.status == "ответ" and not self.answer:
            raise ValueError("answer обязателен при статусе ответ")
        return self


def unknown(question_id: str) -> Answer:
    return Answer(id=question_id, status="не знаю")


def parse_answer(text: str, question_id: str) -> Answer:
    start = text.find("{")
    if start < 0:
        raise ValueError("в ответе модели нет JSON")
    payload, _end = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(payload, dict):
        raise ValueError("JSON ответа не объект")
    payload["id"] = question_id
    return Answer.model_validate(payload)


def read_csv(path: Path) -> list[Answer]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return []
    header = text.splitlines()[0]
    delimiter = ";" if header.count(";") >= header.count(",") else ","
    answers: list[Answer] = []
    for raw in csv.DictReader(text.splitlines(), delimiter=delimiter):
        row = {(key or "").strip().lower(): (value or "").strip() for key, value in raw.items()}
        if row.get("id"):
            answers.append(Answer.model_validate(row))
    return answers


def write_csv(path: Path, answers: list[Answer]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, delimiter=";", lineterminator="\n")
        writer.writeheader()
        for answer in answers:
            writer.writerow(answer.model_dump())
