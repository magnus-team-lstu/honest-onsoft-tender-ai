"""Демо JSON для панели «критики», пока B не пишет results/critics.json сам."""

from __future__ import annotations

import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"

critics = [
    {"name": "Проверка цитаты (дословно)", "trust_before": 12.7, "trust_after": 25.0},
    {"name": "Проверка чисел в цитате", "trust_before": 25.0, "trust_after": 38.5},
    {"name": "Изменения извещения", "trust_before": 38.5, "trust_after": 50.0},
    {"name": "Детектор расхождений", "trust_before": 50.0, "trust_after": 58.0},
]


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / "critics.json"
    path.write_text(json.dumps(critics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Записано: {path}")


if __name__ == "__main__":
    main()
