"""Нормализация текста, числа, даты, единицы. Правила совпадают с data/check.py."""

from __future__ import annotations

import re

_QUOTES = re.compile("[«»„“”\"']")
_DASHES = re.compile("[–—−]")
_SPACES = re.compile(r"\s+")

NUM = r"\d+(?:[   ]\d{3})*(?:[.,]\d+)?"
_NUM = re.compile(NUM)
_DATE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
_TIME = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_SENTENCE_END = re.compile(r"(?<=[^\d\s][.!?;])\s+")
_WORD = re.compile(r"[а-яa-z]+")

UNIT_WORD = (
    r"календарн\w* дн\w*|рабоч\w* дн\w*|дн(?:ей|я|ь)\b|месяц\w*|"
    r"%|процент\w*|руб\w*|лет\b|год\w*"
)
_PAIR = re.compile(
    rf"(?P<num>{NUM})\)?\s*(?:\([^)]{{0,40}}\)\s*)?(?P<unit>{UNIT_WORD})"
)

STOP = {
    "какой", "какая", "какие", "каком", "сколько", "ответьте", "является", "который",
    "которая", "которые", "этого", "настоящ", "размер", "размере", "составляет",
    "составит", "должен", "должна", "более", "менее", "также", "между",
}


def norm(text: str | None) -> str:
    text = (text or "").lower().replace("ё", "е").replace(" ", " ").replace(" ", " ")
    text = _QUOTES.sub('"', text)
    text = _DASHES.sub("-", text)
    return _SPACES.sub(" ", text).strip()


def dates(text: str) -> set[str]:
    return {f"{int(d):02d}.{int(m):02d}.{y}" for d, m, y in _DATE.findall(text or "")}


def times(text: str) -> set[str]:
    return {f"{int(h):02d}:{m}" for h, m in _TIME.findall(text or "")}


def _to_float(raw: str) -> float | None:
    try:
        return float(re.sub(r"[   ]", "", raw).replace(",", "."))
    except ValueError:
        return None


def numbers(text: str) -> list[float]:
    """Числа без дат и времени: 18 000,00 и 18000 дают одно и то же."""
    rest = _TIME.sub(" ", _DATE.sub(" ", text or ""))
    out = []
    for raw in _NUM.findall(rest):
        value = _to_float(raw)
        if value is not None:
            out.append(value)
    return out


def has_number(values: list[float], value: float) -> bool:
    return any(abs(item - value) < 0.01 for item in values)


def unit_of(word: str) -> str:
    word = word.lower()
    if word.startswith("календарн"):
        return "кдн"
    if word.startswith("рабоч"):
        return "рдн"
    if word.startswith("дн"):
        return "дн"
    if word.startswith("месяц"):
        return "мес"
    if word == "%" or word.startswith("процент"):
        return "%"
    if word.startswith("руб"):
        return "руб"
    return "год"


def pairs(text: str) -> list[tuple[float, str]]:
    """Пары (число, единица): «36 (тридцать шесть) месяцев» даёт (36, мес)."""
    out = []
    for match in _PAIR.finditer(text):
        value = _to_float(match.group("num"))
        if value is not None:
            out.append((value, unit_of(match.group("unit"))))
    return out


def stems(text: str) -> set[str]:
    """Смысловые основы слов: первые 4 буквы, без служебных слов и единиц."""
    out = set()
    for word in _WORD.findall(text):
        if len(word) < 4 or word in STOP:
            continue
        stem = word[:4]
        if stem in {"кале", "рабо", "меся", "проц", "рубл"}:
            continue
        out.add(stem)
    return out


def sentences(line: str) -> list[str]:
    return [part for part in _SENTENCE_END.split(line) if part]
