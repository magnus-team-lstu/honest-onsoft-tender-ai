"""Нарезка документов и отбор фрагментов. Короткий пакет уходит целиком."""

from __future__ import annotations

import re

import bm25s

from src.loader import Package

SHORT_PACKAGE = 30_000
TOP_K = 8
_SECTION = re.compile(r"(?m)^(?=\d+(?:\.\d+)*\.\s)")


def is_changes(name: str) -> bool:
    return name.startswith("05_izmeneniya")


def split_sections(name: str, text: str) -> list[tuple[str, str]]:
    if is_changes(name):
        return [(name, text)]
    parts = [part.strip() for part in _SECTION.split(text) if part.strip()]
    if not parts:
        return [(name, text)]
    return [(name, part) for part in parts]


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
    changes = [(name, text) for name, text in _ordered(package.files) if is_changes(name)]
    pieces: list[tuple[str, str]] = []
    for name, text in package.files.items():
        if is_changes(name):
            continue
        pieces.extend(split_sections(name, text))
    return _render(changes + _top(pieces, question, TOP_K))
