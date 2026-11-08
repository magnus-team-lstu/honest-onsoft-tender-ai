"""Точка входа: uv run python -m src.run --questions ... --packages ... --out ..."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from src.loader import Package, load_package, load_questions
from src.llm import LlmClient, make_client
from src.pipeline import Usage, answer_question
from src.schema import Answer, read_csv, write_csv

try:  # проверки участника B; без них работает простая проверка цитаты
    from src.checks import build_verify
except ImportError:
    build_verify = None


@dataclass(frozen=True)
class Report:
    questions: int
    calls: int
    cached: int
    prompt_tokens: int
    completion_tokens: int
    seconds: float


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ответы на вопросы по пакетам закупок")
    parser.add_argument("--questions", required=True, type=Path)
    parser.add_argument("--packages", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--mode", choices=("baseline", "full"), default="full")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--only", default="", help="id вопроса, несколько id через запятую или id пакета")
    parser.add_argument("--resume", action="store_true")
    return parser


def choose(questions: list[dict[str, str]], *, only: str, limit: int | None, done: set[str]) -> list[dict[str, str]]:
    picked = questions
    if only:
        wanted = {item.strip() for item in only.split(",") if item.strip()}
        picked = [row for row in picked if row["id"] in wanted or row["package"] in wanted]
    if done:
        picked = [row for row in picked if row["id"] not in done]
    if limit is not None:
        picked = picked[:limit]
    return picked


def _merge(questions: list[dict[str, str]], existing: list[Answer], fresh: list[Answer]) -> list[Answer]:
    by_id = {answer.id: answer for answer in existing}
    by_id.update({answer.id: answer for answer in fresh})
    return [by_id[row["id"]] for row in questions if row["id"] in by_id]


async def _answer_all(
    client: LlmClient,
    questions: list[dict[str, str]],
    packages: Path,
    mode: str,
    usage: Usage,
) -> list[Answer]:
    loaded: dict[str, Package] = {}

    async def one(row: dict[str, str]) -> Answer:
        package_id = row["package"]
        if package_id not in loaded:
            loaded[package_id] = load_package(packages / package_id)
        return await answer_question(
            client,
            row["id"],
            row["question"],
            loaded[package_id],
            mode=mode,
            usage=usage,
            verify=build_verify(row["question"]) if build_verify else None
        )

    return list(await asyncio.gather(*(one(row) for row in questions)))


def execute(client: LlmClient, args: argparse.Namespace) -> Report:
    questions = load_questions(args.questions)
    existing = read_csv(args.out) if args.resume else []
    done = {answer.id for answer in existing}
    selected = choose(questions, only=args.only, limit=args.limit, done=done)
    usage = Usage()
    started = time.perf_counter()
    fresh = asyncio.run(_answer_all(client, selected, args.packages, args.mode, usage)) if selected else []
    seconds = time.perf_counter() - started
    write_csv(args.out, _merge(questions, existing, fresh))
    report = Report(
        questions=len(fresh),
        calls=usage.calls,
        cached=usage.cached,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        seconds=seconds,
    )
    print(
        f"Вопросов: {report.questions}. Новых запросов: {report.calls}. Из кэша: {report.cached}. "
        f"Токены: {report.prompt_tokens}+{report.completion_tokens}. Секунды: {report.seconds:.1f}"
    )
    score(args, questions)
    return report


def score(args: argparse.Namespace, questions: list[dict[str, str]]) -> None:
    if args.limit is not None or args.only:
        print("Индекс: пропущен, запуск не на всех вопросах файла")
        return
    if len(read_csv(args.out)) < len(questions):
        print("Индекс: пропущен, в answers.csv ещё не все вопросы")
        return
    gold = args.questions.parent / "answers_public.json"
    checker = args.questions.parent / "check.py"
    if not gold.is_file() or not checker.is_file():
        print("Индекс: рядом нет answers_public.json и check.py")
        return
    completed = subprocess.run(
        [sys.executable, str(checker), str(args.out), "--gold", str(gold), "--packages", str(args.packages)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    print(completed.stdout)
    if completed.returncode != 0:
        print(completed.stderr)


def main() -> None:
    args = build_parser().parse_args()
    execute(make_client(), args)


if __name__ == "__main__":
    main()
