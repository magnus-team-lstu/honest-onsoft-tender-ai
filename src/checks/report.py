"""Замер вклада проверок без новых запросов к модели.

uv run python -m src.checks.report --answers results/answers.csv

Пишет:
  results/verdicts.jsonl      по строке на (вопрос, проверка): id, check, verdict. Читает страница B дашборда.
  results/checks_report.json  сколько обманов поймала каждая проверка и сколько верных ответов зря отклонила.
  results/critics.json        прирост индекса по проверкам в формате дашборда участника C.

Оценка считает, что отклонённый ответ превратился в «не знаю». В пайплайне после
отказа идёт повторный запрос, так что реальный прирост бывает и больше.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path
from types import ModuleType, SimpleNamespace

from src.checks import CHECKS, TITLES, run_checks


def read_table(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return []
    header = text.splitlines()[0]
    delimiter = ";" if header.count(";") >= header.count(",") else ","
    rows = []
    for raw in csv.DictReader(text.splitlines(), delimiter=delimiter):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        if row.get("id"):
            rows.append(row)
    return rows


def read_package(directory: Path) -> SimpleNamespace:
    files = {}
    for path in sorted(directory.glob("*.txt")):
        raw = path.read_bytes()
        try:
            files[path.name] = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            files[path.name] = raw.decode("cp1251")
    return SimpleNamespace(id=directory.name, files=files)


def load_checker(path: Path) -> ModuleType | None:
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("organizer_check", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def index_of(verdicts: list[str]) -> float:
    counts = Counter(verdicts)
    return (counts["верно"] - counts["обман"]) / len(verdicts) * 100 if verdicts else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--answers", type=Path, default=Path("results/answers.csv"))
    parser.add_argument("--questions", type=Path, default=Path("data/questions.csv"))
    parser.add_argument("--packages", type=Path, default=Path("data/packages"))
    parser.add_argument("--gold", type=Path, default=Path("data/answers_public.json"))
    parser.add_argument("--checker", type=Path, default=Path("data/check.py"))
    parser.add_argument("--out-dir", type=Path, default=Path("results"))
    args = parser.parse_args()

    questions = {row["id"]: row for row in read_table(args.questions)}
    answers = read_table(args.answers)
    packages: dict[str, SimpleNamespace] = {}
    table: dict[str, dict[str, str]] = {}

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "verdicts.jsonl").open("w", encoding="utf-8") as log:
        for row in answers:
            meta = questions.get(row["id"], {})
            package_id = meta.get("package") or row["id"].split("-")[0]
            if package_id not in packages:
                packages[package_id] = read_package(args.packages / package_id)
            answer = SimpleNamespace(
                id=row["id"],
                status=row.get("status", ""),
                answer=row.get("answer", ""),
                quote=row.get("quote", ""),
                file=row.get("file", ""),
            )
            table[row["id"]] = dict(run_checks(answer, packages[package_id], meta.get("question", "")))
            for name, verdict in table[row["id"]].items():
                log.write(json.dumps({"id": row["id"], "check": name, "verdict": verdict}, ensure_ascii=False) + "\n")

    refused = Counter(name for verdicts in table.values() for name, v in verdicts.items() if v != "ok")
    print(f"Ответов: {len(table)}. Отказы по проверкам:")
    for name in CHECKS:
        print(f"  {name:10} {refused[name]:>3}  {TITLES[name]}")

    checker = load_checker(args.checker)
    if checker is None or not args.gold.is_file():
        print("Нет data/check.py или answers_public.json: вклад в индекс не считаю.")
        return
    gold = json.loads(args.gold.read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in answers}
    docs: dict[str, dict[str, str]] = {}

    def judge_all(dropped: set[str]) -> dict[str, str]:
        result = {}
        for item in gold:
            package_id = item["package"]
            if package_id not in docs:
                folder = args.packages / package_id
                docs[package_id] = {f.name: checker.norm(checker.read_file(f)) for f in sorted(folder.glob("*.txt"))}
            row = by_id.get(item["id"])
            if row is not None and item["id"] in dropped:
                row = {**row, "status": "не знаю", "answer": "", "quote": "", "file": ""}
            result[item["id"]] = checker.judge(item, row, docs[package_id])[0]
        return result

    base = judge_all(set())
    report = {"index_before": round(index_of(list(base.values())), 1), "checks": []}
    critics = []
    dropped: set[str] = set()
    current = report["index_before"]
    for name in CHECKS:
        mine = {qid for qid, verdicts in table.items() if verdicts.get(name, "ok") != "ok"}
        caught = sorted(qid for qid in mine if base.get(qid) == "обман")
        wasted = sorted(qid for qid in mine if base.get(qid) == "верно")
        alone = round(index_of(list(judge_all(mine).values())), 1)
        dropped |= mine
        after = round(index_of(list(judge_all(dropped).values())), 1)
        report["checks"].append(
            {"check": name, "title": TITLES[name], "refused": len(mine), "caught_lies": caught,
             "false_alarms": wasted, "index_alone": alone, "index_cumulative": after}
        )
        critics.append({"name": TITLES[name], "trust_before": current, "trust_after": after})
        current = after
    report["index_after"] = current
    (args.out_dir / "checks_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out_dir / "critics.json").write_text(json.dumps(critics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nИндекс без проверок: {report['index_before']}. Со всеми проверками (оценка): {current}")
    print(f"{'проверка':10} {'поймала обманов':>16} {'зря отклонила':>14} {'индекс':>7}")
    for item in report["checks"]:
        print(f"{item['check']:10} {len(item['caught_lies']):>16} {len(item['false_alarms']):>14} {item['index_cumulative']:>7}")


if __name__ == "__main__":
    main()
