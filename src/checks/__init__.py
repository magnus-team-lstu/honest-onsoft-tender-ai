"""Проверки ответа модели. Участник B.

Контракт с пайплайном (src/pipeline.py, параметр verify):
    verify(answer, package) -> "ok" или текст причины

Причина уходит модели при повторе, поэтому написана как подсказка, что исправить.
Вопрос нужен части проверок (единицы, «да или нет»), поэтому есть build_verify(question).
"""

from __future__ import annotations

from collections.abc import Callable

from src.checks.changes import check_changes
from src.checks.conflicts import check_conflict
from src.checks.core import AnswerLike, Context, PackageLike, make_context
from src.checks.injection import check_injection, clean_files, find_injections
from src.checks.negation import check_negation
from src.checks.numbers import check_numbers, check_units
from src.checks.quote import check_quote

Check = Callable[[Context], str]

# Порядок важен: дешёвые и самые строгие сначала. Имена попадают в verdicts.jsonl.
CHECKS: dict[str, Check] = {
    "quote": check_quote,
    "injection": check_injection,
    "changes": check_changes,
    "numbers": check_numbers,
    "units": check_units,
    "negation": check_negation,
    "conflict": check_conflict,
}

TITLES = {
    "quote": "Цитата дословно есть в документах",
    "injection": "Защита от инструкций в документах",
    "changes": "Приоритет изменений извещения",
    "numbers": "Число из ответа есть в цитате",
    "units": "Единица из вопроса есть в цитате",
    "negation": "Требования нет, хотя слово есть",
    "conflict": "Расхождение извещения и контракта",
}


def run_checks(
    answer: AnswerLike,
    package: PackageLike,
    question: str = "",
    only: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Все проверки подряд, без остановки. Для журнала и замера вклада."""
    ctx = make_context(answer, package, question)
    names = only or list(CHECKS)
    return [(name, CHECKS[name](ctx)) for name in names]


def build_verify(question: str = "", only: list[str] | None = None) -> Callable[[AnswerLike, PackageLike], str]:
    """Функция для answer_question(..., verify=build_verify(question)). Первая ошибка останавливает."""

    def verify(answer: AnswerLike, package: PackageLike) -> str:
        ctx = make_context(answer, package, question)
        for name in only or list(CHECKS):
            verdict = CHECKS[name](ctx)
            if verdict != "ok":
                return verdict
        return "ok"

    return verify


verify = build_verify()

__all__ = [
    "CHECKS",
    "TITLES",
    "build_verify",
    "clean_files",
    "find_injections",
    "run_checks",
    "verify",
]
