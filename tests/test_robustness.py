"""Трудные файлы: документ больше окна модели, отказ сервера, нет папки пакета."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.llm import Completion, LlmClient
from src.loader import Package
from src.pipeline import answer_question
from src.retrieval import MAX_CONTEXT, MAX_PIECE, build_context, cut
from src.run import build_parser, execute
from src.schema import read_csv

BOILERPLATE = "Раздел {n}. Стороны руководствуются законодательством о контрактной системе. Цена контракта является твёрдой.\n"


def huge_package() -> Package:
    body = "".join(BOILERPLATE.format(n=n) for n in range(20_000))
    needle = "Исполнитель обеспечивает круглосуточную техническую поддержку с временем реакции не более 2 (двух) часов.\n"
    opisanie = "ОПИСАНИЕ ОБЪЕКТА ЗАКУПКИ\n2. Требования\n" + body[: len(body) // 2] + needle + body[len(body) // 2 :]
    notice = "".join(f"2.{n}. Пункт извещения номер {n} про сроки и цену.\n" for n in range(200))
    return Package("K02", {"01_izveshchenie.txt": notice, "03_opisanie_obekta.txt": opisanie})


def test_cut_keeps_pieces_short() -> None:
    text = "Очень длинная строка без переносов. " * 2000
    pieces = cut("f.txt", text)
    assert len(pieces) > 1
    assert all(len(piece) <= MAX_PIECE for _name, piece in pieces)
    assert " ".join(piece for _name, piece in pieces).split() == text.split()


def test_huge_file_fits_and_needle_is_found() -> None:
    package = huge_package()
    assert len(package.files["03_opisanie_obekta.txt"]) > 2_000_000
    context = build_context(package, "Какое максимальное время реакции технической поддержки, в часах?")
    assert len(context) < MAX_CONTEXT + 2_000
    assert "не более 2 (двух) часов" in context


def test_server_error_becomes_unknown(tmp_path: Path) -> None:
    async def complete(messages, temperature, max_tokens):
        raise ValueError("context length exceeded")

    client = LlmClient(complete, model="test", rpm=100_000, cache_dir=tmp_path)
    package = Package("P01", {"01_izveshchenie.txt": "Обеспечение заявки 18 000,00 рублей."})
    answer = asyncio.run(answer_question(client, "P01-03", "размер", package, mode="full"))
    assert answer.status == "не знаю"


def test_missing_package_does_not_stop_the_run(tmp_path: Path) -> None:
    packages = tmp_path / "packages" / "P01"
    packages.mkdir(parents=True)
    (packages / "01_izveshchenie.txt").write_text("Обеспечение заявки 18 000,00 рублей.", encoding="utf-8")
    questions = tmp_path / "questions.csv"
    questions.write_text("id;package;question\nP01-01;P01;размер\nX09-01;X09;нет такой папки\n", encoding="utf-8")
    out = tmp_path / "answers.csv"

    async def complete(messages, temperature, max_tokens):
        payload = {"status": "ответ", "answer": "18000", "quote": "18 000,00 рублей", "file": "01_izveshchenie.txt"}
        return Completion(json.dumps(payload, ensure_ascii=False), 1, 1)

    client = LlmClient(complete, model="test", rpm=100_000, cache_dir=tmp_path / "cache")
    args = build_parser().parse_args(
        ["--questions", str(questions), "--packages", str(tmp_path / "packages"), "--out", str(out), "--mode", "full"]
    )
    execute(client, args)
    rows = {row.id: row.status for row in read_csv(out)}
    assert rows == {"P01-01": "ответ", "X09-01": "не знаю"}
