"""Ловушка «требования нет, хотя слово есть»: ответ должен совпадать с отрицанием в цитате."""

from __future__ import annotations

import re

from src.checks.core import SKIP_STATUSES, Context
from src.checks.text import numbers

NEGATION = re.compile(
    r"\bне (?:установлен\w*|требуется|предусмотрен\w*|предъявля\w*|нужн\w*|применя\w*|"
    r"предоставля\w*|допуска\w*)|\bотсутству\w*|\bне устанавлива\w*"
)
_YES = re.compile(r"(?<![а-я])да(?![а-я])")
_NO = re.compile(r"(?<![а-я])нет(?![а-я])|не требуется|не установлен|не нужн|отсутств")


def check_negation(ctx: Context) -> str:
    if ctx.status in SKIP_STATUSES or ctx.status == "расхождение" or not ctx.quote:
        return "ok"
    answer = (ctx.answer.answer or "").lower()
    sentence = ctx.context()
    negative_text = bool(NEGATION.search(sentence))
    says_no = bool(_NO.search(answer))
    says_yes = bool(_YES.search(answer)) and not says_no
    if negative_text and (says_yes or (numbers(answer) and not says_no)):
        return (
            f"в цитируемой фразе сказано, что требования нет («{sentence[:160]}»), "
            "а ответ утверждает обратное"
        )
    if says_no and not negative_text and ("да или нет" in ctx.question or answer.strip() in {"нет", "нет."}):
        return "ответ «нет», но цитата не говорит об отсутствии требования; найди фразу с «не установлено» или «не требуется»"
    return "ok"
