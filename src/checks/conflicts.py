"""Детектор расхождений: то же условие в другом документе с другим числом."""

from __future__ import annotations

from dataclasses import dataclass

from src.checks.core import CHANGES_PREFIX, SKIP_STATUSES, Context
from src.checks.text import dates, has_number, numbers, pairs, stems

MIN_SHARED = 2      # сколько общих смысловых слов нужно, чтобы считать фразы об одном
MIN_OVERLAP = 0.45  # доля веса общих слов от меньшей фразы (редкие слова весят больше)


@dataclass(frozen=True)
class Conflict:
    file: str
    sentence: str
    ours: float
    theirs: float
    unit: str


def find_conflict(ctx: Context) -> Conflict | None:
    sentence = ctx.context()
    names = ctx.where()
    if not sentence or not names:
        return None
    home = names[0]
    ours = pairs(sentence)
    topic = stems(sentence)
    if not ours or not topic:
        return None
    best: tuple[float, Conflict] | None = None
    for other in ctx.index.sentences:
        if other.file == home or other.file.startswith(CHANGES_PREFIX):
            continue
        if ctx.index.is_superseded(other.file, other.text):
            continue
        theirs = pairs(other.text)
        if not theirs:
            continue
        other_topic = stems(other.text)
        shared = topic & other_topic
        if len(shared) < MIN_SHARED:
            continue
        smaller = min(ctx.index.weight(topic), ctx.index.weight(other_topic)) or 1.0
        overlap = ctx.index.weight(shared) / smaller
        if overlap < MIN_OVERLAP:
            continue
        their_values = [value for value, _unit in theirs]
        for value, unit in ours:
            for other_value, other_unit in theirs:
                if unit == other_unit and not has_number(their_values, value):
                    found = Conflict(other.file, other.text, value, other_value, unit)
                    if best is None or overlap > best[0]:
                        best = (overlap, found)
    return best[1] if best else None


def _everywhere(ctx: Context) -> str:
    return " ".join(ctx.index.files.values())


def check_conflict(ctx: Context) -> str:
    if ctx.status in SKIP_STATUSES or not ctx.quote:
        return "ok"
    if ctx.status == "расхождение":
        answer = ctx.answer.answer or ""
        values = set(numbers(answer)) | dates(answer)
        if len(values) < 2:
            return "при статусе «расхождение» в ответе нужны оба значения, например «60 и 75 дней»"
        everywhere = _everywhere(ctx)
        found = numbers(everywhere)
        absent = [f"{v:g}" for v in numbers(answer) if not has_number(found, v)]
        if absent:
            return f"значения {', '.join(absent)} нет ни в одном документе пакета"
        if find_conflict(ctx) is None and not _two_files(ctx, numbers(answer)):
            return "расхождение не подтверждается: второго значения в другом документе не нашлось"
        return "ok"
    conflict = find_conflict(ctx)
    if conflict is None:
        return "ok"
    return (
        f"возможное расхождение: в {conflict.file} то же условие с другим значением "
        f"({conflict.theirs:g} вместо {conflict.ours:g}): «{conflict.sentence[:160]}». "
        "Если документы противоречат, ответь со статусом «расхождение» и укажи оба значения"
    )


def _two_files(ctx: Context, values: list[float]) -> bool:
    homes = set()
    for value in values:
        for name, text in ctx.index.files.items():
            if has_number(numbers(text), value):
                homes.add(name)
    return len(homes) >= 2
