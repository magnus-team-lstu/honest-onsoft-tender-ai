"""Общий контекст для проверок. Пакет разбирается один раз и кэшируется."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

import math

from src.checks.text import norm, sentences, stems

CHANGES_PREFIX = "05_izmeneniya"
SKIP_STATUSES = {"не знаю", "нет в документах"}


class AnswerLike(Protocol):
    id: str
    status: str
    answer: str
    quote: str
    file: str


class PackageLike(Protocol):
    id: str
    files: dict[str, str]


@dataclass(frozen=True)
class Sentence:
    file: str
    text: str  # нормализованный текст предложения


@dataclass
class PackageIndex:
    files: dict[str, str]                       # имя -> нормализованный текст целиком
    sentences: list[Sentence]
    superseded: list[tuple[str, str]] = field(default_factory=list)   # (файл, старый пункт)
    replacements: list[tuple[str, str]] = field(default_factory=list)  # (старый пункт, новая редакция)
    injections: list[Sentence] = field(default_factory=list)

    idf: dict[str, float] = field(default_factory=dict)

    def weight(self, words: set[str]) -> float:
        """Сумма редкости слов: частые «контракт», «цена» весят мало."""
        return sum(self.idf.get(word, 1.0) for word in words)

    def is_superseded(self, file: str, text: str) -> bool:
        return any(name == file and (text in old or old in text) for name, old in self.superseded)


@dataclass
class Context:
    answer: AnswerLike
    question: str
    index: PackageIndex

    @property
    def status(self) -> str:
        return norm(self.answer.status)

    @property
    def quote(self) -> str:
        return norm(self.answer.quote)

    def where(self) -> list[str]:
        """Файлы, где цитата встречается. Сначала названный в поле file."""
        found = [name for name, text in self.index.files.items() if self.quote and self.quote in text]
        named = self.answer.file
        return sorted(found, key=lambda name: name != named)

    def context(self) -> str:
        """Предложение документа вокруг цитаты. Если цитата длиннее, то сама цитата."""
        quote = self.quote
        if not quote:
            return ""
        names = self.where()
        for sentence in self.index.sentences:
            if sentence.file in names[:1] and quote in sentence.text:
                return sentence.text
        return quote


_ITEM = re.compile(
    r"«(?P<old>[^»]{8,}?)(?:…|\.\.\.)?»\s*\((?P<file>[\w.\-]+\.txt)\)[^«]{0,60}?редакции:?\s*«(?P<new>[^»]+)»"
)
_INJECTION = re.compile(
    r"игнорир\w* (?:предыдущ|все|инструкц|указан)|забудь\w*|не обращай внимани|"
    r"системн\w* (?:промпт|инструкц|сообщени)|\bsystem\b|\bassistant\b|\bprompt\b|"
    r"(?:ответь|напиши|верни|сообщи)\w*,? что |ты (?:-|—)? ?(?:языков\w* )?(?:модель|ассистент|ии)\b"
)

_CACHE: dict[tuple, PackageIndex] = {}


def _split_changes(name: str, text: str, index: PackageIndex) -> None:
    for match in _ITEM.finditer(re.sub(r"\s+", " ", text)):
        old = norm(match.group("old")).rstrip(".… ")
        target = match.group("file")
        new = norm(match.group("new"))
        index.replacements.append((old, new))
        index.superseded.append((name, old))  # старый текст внутри самого файла изменений
        document = index.files.get(target, "")
        for sentence in index.sentences:
            if sentence.file == target and old[:60] in sentence.text:
                index.superseded.append((target, sentence.text))
        if target in index.files and old[:60] in document:
            index.superseded.append((target, old))


def build_index(files: dict[str, str]) -> PackageIndex:
    key = tuple(sorted((name, hash(text)) for name, text in files.items()))
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    normalized = {name: norm(text) for name, text in files.items()}
    items: list[Sentence] = []
    for name, text in files.items():
        for line in text.splitlines():
            line = norm(line)
            if not line:
                continue
            items.extend(Sentence(name, part) for part in sentences(line))
    index = PackageIndex(normalized, items)
    for name, text in files.items():
        if name.startswith(CHANGES_PREFIX):
            _split_changes(name, text, index)
    index.injections = [item for item in items if _INJECTION.search(item.text)]
    counts: dict[str, int] = {}
    for item in items:
        for word in stems(item.text):
            counts[word] = counts.get(word, 0) + 1
    total = max(len(items), 1)
    index.idf = {word: math.log(total / count) for word, count in counts.items()}
    _CACHE[key] = index
    return index


def make_context(answer: AnswerLike, package: PackageLike, question: str = "") -> Context:
    return Context(answer=answer, question=norm(question), index=build_index(package.files))
