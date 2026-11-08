"""Числа и даты из ответа должны стоять в цитате. Расчёт по проценту тоже проверяется."""

from __future__ import annotations

import re

from src.checks.core import SKIP_STATUSES, Context
from src.checks.text import NUM, dates, has_number, numbers, times

_PERCENT = re.compile(rf"({NUM})\s*(?:%|процент)")
_MONEY = re.compile(rf"({NUM})\s*(?:\([^)]{{0,80}}\)\s*)?руб")

_QUESTION_UNITS = (
    (re.compile(r"в процент|сколько процент"), re.compile(r"%|процент"), "процентах"),
    (re.compile(r"в рубл|сколько рубл"), re.compile(r"руб"), "рублях"),
    (re.compile(r"в месяц|сколько месяц"), re.compile(r"месяц"), "месяцах"),
    (re.compile(r"дн(ях|ей)\b"), re.compile(r"\bдн(ей|я|ь)\b"), "днях"),
)


def _value(raw: str) -> float:
    return float(re.sub(r"\s", "", raw).replace(",", "."))


def calculated(ctx: Context, value: float) -> bool:
    """value = процент из цитаты × денежная сумма из пакета (например, НМЦК)."""
    percents = [_value(raw) for raw in _PERCENT.findall(ctx.context())]
    if not percents:
        return False
    bases = set()
    for text in ctx.index.files.values():
        bases.update(_value(raw) for raw in _MONEY.findall(text))
    return any(abs(base * percent / 100 - value) < 0.5 for base in bases for percent in percents)


def _support(ctx: Context) -> str:
    """Текст, в котором должны найтись числа ответа: цитата и её предложение."""
    return f"{ctx.quote} {ctx.context()}"


def missing_values(ctx: Context) -> list[str]:
    answer = ctx.answer.answer or ""
    support = _support(ctx)
    missing = [day for day in dates(answer) if day not in dates(support)]
    missing += [hour for hour in times(answer) if hour not in times(support)]
    found = numbers(support)
    for value in numbers(answer):
        if not has_number(found, value) and not calculated(ctx, value):
            missing.append(f"{value:g}")
    return missing


def check_numbers(ctx: Context) -> str:
    if ctx.status in SKIP_STATUSES or not ctx.quote:
        return "ok"
    if ctx.status == "расхождение":
        return "ok"  # оба значения проверяет check_conflict
    missing = missing_values(ctx)
    if missing:
        return (
            f"в цитате нет значения {', '.join(missing)} из ответа; "
            "возьми число из той же фразы, которую цитируешь"
        )
    return "ok"


def check_units(ctx: Context) -> str:
    """Вопрос «в месяцах», а в цитате месяцев нет: значит, взято не то число."""
    if ctx.status != "ответ" or not numbers(ctx.answer.answer or ""):
        return "ok"
    support = _support(ctx)
    for asked, present, label in _QUESTION_UNITS:
        if asked.search(ctx.question) and not present.search(support):
            if label == "рублях" and any(calculated(ctx, v) for v in numbers(ctx.answer.answer)):
                return "ok"
            return f"вопрос про значение в {label}, а в цитате такой единицы нет; это, вероятно, другое число"
    return "ok"
