"""Нарезка документов и отбор фрагментов. Короткий пакет уходит целиком.

Длинный пакет режется на пункты, а слишком длинный пункт ещё и на куски по MAX_PIECE
символов: так огромный файл (больше окна модели) не попадает в запрос целиком.
Весь запрос ограничен MAX_CONTEXT символами.
"""

from __future__ import annotations

import re

import bm25s

from src.loader import Package

SHORT_PACKAGE = 30_000
TOP_K = 8
MAX_PIECE = 2_000      # символов в одном фрагменте
MAX_CHANGES = 10_000   # файл изменений длиннее этого режется как обычный документ
MAX_CONTEXT = 60_000   # символов во всём контексте, с большим запасом до окна модели
_SECTION = re.compile(r"(?m)^(?=\d+(?:\.\d+)*\.\s)")
_SENTENCE = re.compile(r"(?<=[.!?;])\s+")
_SPACES = re.compile(r"\s+")


def is_changes(name: str) -> bool:
    return name.startswith("05_izmeneniya")


def _short_lines(text: str, limit: int) -> list[str]:
    """Строки текста; строка длиннее limit делится по предложениям, а если нужно, то по limit."""
    lines: list[str] = []
    for line in text.splitlines():
        if len(line) <= limit:
            lines.append(line)
            continue
        for sentence in _SENTENCE.split(line):
            lines.extend(sentence[start:start + limit] for start in range(0, len(sentence), limit))
    return lines


def cut(name: str, text: str, limit: int = MAX_PIECE) -> list[tuple[str, str]]:
    """Делит длинный текст на куски не длиннее limit, по границам строк и предложений."""
    if len(text) <= limit:
        return [(name, text)]
    pieces: list[tuple[str, str]] = []
    buffer: list[str] = []
    size = 0
    for line in _short_lines(text, limit):
        if buffer and size + len(line) + 1 > limit:
            pieces.append((name, "\n".join(buffer)))
            buffer, size = [], 0
        buffer.append(line)
        size += len(line) + 1
    if buffer:
        pieces.append((name, "\n".join(buffer)))
    return pieces


def split_sections(name: str, text: str) -> list[tuple[str, str]]:
    if is_changes(name) and len(text) <= MAX_CHANGES:
        return [(name, text)]
    parts = [part.strip() for part in _SECTION.split(text) if part.strip()] or [text]
    pieces: list[tuple[str, str]] = []
    for part in parts:
        pieces.extend(cut(name, part))
    return pieces


def _unique(chunks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Убирает повторы: в длинных документах один и тот же шаблонный текст встречается сотни раз."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for name, text in chunks:
        key = _SPACES.sub(" ", text).strip()
        if key and key not in seen:
            seen.add(key)
            out.append((name, text))
    return out


def _limit(chunks: list[tuple[str, str]], budget: int = MAX_CONTEXT) -> list[tuple[str, str]]:
    """Берёт фрагменты по порядку, пока не кончится бюджет символов."""
    out: list[tuple[str, str]] = []
    used = 0
    for name, text in chunks:
        if used + len(text) > budget and out:
            break
        out.append((name, text[:budget]))
        used += len(text)
    return out


def _render(chunks: list[tuple[str, str]]) -> str:
    return "\n\n".join(f"Файл: {name}\n{text}" for name, text in chunks)


def _ordered(files: dict[str, str]) -> list[tuple[str, str]]:
    changes = sorted((name, text) for name, text in files.items() if is_changes(name))
    rest = sorted((name, text) for name, text in files.items() if not is_changes(name))
    return changes + rest


def _top(chunks: list[tuple[str, str]], question: str, k: int) -> list[tuple[str, str]]:
    if len(chunks) <= k:
        return chunks
    texts = [text for _name, text in chunks]
    corpus = bm25s.tokenize(texts, stopwords=[], show_progress=False, return_ids=False)
    engine = bm25s.BM25()
    engine.index(corpus, show_progress=False)
    query = bm25s.tokenize([question], stopwords=[], show_progress=False, return_ids=False)
    documents, _scores = engine.retrieve(query, k=k, show_progress=False, n_threads=0)
    return [chunks[int(index)] for index in documents[0]]


def build_context(package: Package, question: str) -> str:
    total = sum(len(text) for text in package.files.values())
    if total <= SHORT_PACKAGE:
        return _render(_ordered(package.files))
    changes = [
        (name, text) for name, text in _ordered(package.files) if is_changes(name) and len(text) <= MAX_CHANGES
    ]
    kept = {name for name, _text in changes}
    pieces: list[tuple[str, str]] = []
    for name, text in sorted(package.files.items()):
        if name in kept or not text.strip():
            continue
        pieces.extend(split_sections(name, text))
    return _render(_limit(changes + _top(_unique(pieces), question, TOP_K)))
