"""Один вопрос — один или несколько запросов. Проверку цитаты делает код."""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.loader import Package
from src.llm import LlmClient
from src.retrieval import build_context
from src.schema import Answer, parse_answer, unknown

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "answer.md"
Verify = Callable[[Answer, Package], str]
_SPACE = re.compile(r"\s+")


@dataclass
class Usage:
    calls: int = 0
    cached: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def add(self, result: dict[str, object]) -> None:
        if result["cached"]:
            self.cached += 1
            return
        self.calls += 1
        self.prompt_tokens += int(result["prompt_tokens"])
        self.completion_tokens += int(result["completion_tokens"])


def collapse(text: str) -> str:
    return _SPACE.sub(" ", text).strip()


def quote_in_file(answer: Answer, package: Package) -> str:
    if answer.status in {"не знаю", "нет в документах"}:
        return "ok"
    quote = collapse(answer.quote)
    if len(quote) < 8:
        return "цитата короче 8 символов"
    document = package.files.get(answer.file)
    if document is None:
        return "файл из поля file не найден в пакете"
    if quote not in collapse(document):
        return "цитаты нет в названном файле"
    return "ok"


def _messages(question_id: str, question: str, context: str, notes: list[str]) -> list[dict[str, str]]:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"id: {question_id}\nвопрос: {question}\n\n{context}"},
    ]
    messages.extend({"role": "user", "content": note} for note in notes)
    return messages


async def answer_question(
    client: LlmClient,
    question_id: str,
    question: str,
    package: Package,
    *,
    mode: str = "full",
    verify: Verify | None = None,
    max_attempts: int = 3,
    usage: Usage | None = None,
) -> Answer:
    if mode == "baseline":
        context = "\n\n".join(f"Файл: {name}\n{text}" for name, text in sorted(package.files.items()))
        attempts = 1
        checker = None
    else:
        context = build_context(package, question)
        attempts = max(max_attempts, 1)
        checker = verify or quote_in_file
    notes: list[str] = []
    meter = usage or Usage()
    last = unknown(question_id)
    for _attempt in range(attempts):
        try:
            result = await client.ask(
                _messages(question_id, question, context, notes),
                temperature=0,
                max_tokens=4096,
            )
        except Exception as error:  # сервер отказал, например запрос больше окна модели
            print(f"{question_id}: модель не ответила ({type(error).__name__}), записано «не знаю»", file=sys.stderr)
            return unknown(question_id)
        meter.add(result)
        try:
            last = parse_answer(str(result["text"]), question_id)
        except ValueError as error:
            notes.append(f"Проверка не прошла: {error}. Верни один JSON. Если не уверен, статус «не знаю».")
            continue
        if checker is None:
            return last
        verdict = checker(last, package)
        if verdict == "ok":
            return last
        notes.append(f"Проверка не прошла: {verdict}. Верни один JSON. Если не уверен, статус «не знаю».")
    return unknown(question_id)
