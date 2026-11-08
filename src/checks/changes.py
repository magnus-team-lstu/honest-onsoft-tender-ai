"""Изменения извещения важнее самого извещения: старое значение считается обманом."""

from __future__ import annotations

from src.checks.core import SKIP_STATUSES, Context


def check_changes(ctx: Context) -> str:
    if ctx.status in SKIP_STATUSES or not ctx.quote:
        return "ok"
    for name in ctx.where():
        if not ctx.index.is_superseded(name, ctx.quote):
            return "ok"  # цитата есть хотя бы в одном действующем месте
    for old, new in ctx.index.replacements:
        if ctx.quote in old or old[:60] in ctx.quote or ctx.context().startswith(old[:40]):
            return (
                "этот пункт изменён в файле изменений извещения, старое значение недействительно; "
                f"новая редакция: «{new[:200]}»"
            )
    if ctx.where():
        return "этот пункт изменён в файле изменений извещения, возьми значение оттуда"
    return "ok"
