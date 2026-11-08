"""Чтение пакетов закупок. Пустой или чужая кодировка не роняют процесс."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Package:
    id: str
    files: dict[str, str]
    reasons: dict[str, str] = field(default_factory=dict)


def read_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if not raw.strip():
        return "", "пустой файл"
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), ""
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), ""
    try:
        return raw.decode("utf-8"), ""
    except UnicodeDecodeError:
        return raw.decode("cp1251"), ""


def load_package(directory: Path) -> Package:
    if not directory.is_dir():
        raise FileNotFoundError(f"нет пакета {directory}")
    files: dict[str, str] = {}
    reasons: dict[str, str] = {}
    for path in sorted(directory.glob("*.txt")):
        text, reason = read_text(path)
        files[path.name] = text
        if reason:
            reasons[path.name] = reason
    return Package(directory.name, files, reasons)


def load_questions(path: Path) -> list[dict[str, str]]:
    import csv

    text = path.read_text(encoding="utf-8-sig")
    header = text.splitlines()[0] if text else ""
    delimiter = ";" if header.count(";") >= header.count(",") else ","
    rows: list[dict[str, str]] = []
    for raw in csv.DictReader(text.splitlines(), delimiter=delimiter):
        row = {(key or "").strip().lower(): (value or "").strip() for key, value in raw.items()}
        if row.get("id"):
            rows.append(row)
    return rows
