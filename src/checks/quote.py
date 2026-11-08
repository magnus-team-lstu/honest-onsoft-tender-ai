"""Цитата должна дословно стоять в документах пакета."""

from __future__ import annotations

from difflib import SequenceMatcher

from src.checks.core import SKIP_STATUSES, Context


def _closest(ctx: Context) -> str:
    best, score = "", 0.0
    for sentence in ctx.index.sentences:
        ratio = SequenceMatcher(None, ctx.quote, sentence.text).ratio()
        if ratio > score:
            best, score = sentence.text, ratio
    return best[:160] if score >= 0.5 else ""


def check_quote(ctx: Context) -> str:
    if ctx.status in SKIP_STATUSES:
        return "ok"
    if len(ctx.quote) < 8:
        return "нет цитаты: нужен дословный фрагмент документа не короче 8 символов"
    if ctx.where():
        return "ok"
    hint = _closest(ctx)
    reason = "цитаты нет в документах, скопируй фрагмент дословно"
    return f"{reason}; похожее место: «{hint}»" if hint else reason
