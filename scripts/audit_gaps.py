"""Офлайн-разбор уже записанных ответов. Новых запросов к модели нет."""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

from src.loader import load_package
from src.pipeline import quote_in_file
from src.schema import read_csv

ROOT = Path(__file__).resolve().parents[1]
LOG = Path(r"c:\Dio\.cursor\debug-40dca6.log")


def log(hypothesis_id: str, message: str, data: dict) -> None:
    payload = {
        "sessionId": "40dca6",
        "runId": "audit",
        "hypothesisId": hypothesis_id,
        "location": "scripts/audit_gaps.py",
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_check():
    spec = importlib.util.spec_from_file_location("case_check", ROOT / "data" / "check.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> None:
    check = load_check()
    gold = json.loads((ROOT / "data" / "answers_public.json").read_text(encoding="utf-8"))
    answers = {item.id: item for item in read_csv(ROOT / "results" / "answers.csv")}
    packages = {item["package"]: load_package(ROOT / "data" / "packages" / item["package"]) for item in gold}
    value_gap = []
    quote_gap = []
    our_reject = []
    for item in gold:
        answer = answers.get(item["id"])
        package = packages[item["package"]]
        if answer is None:
            continue
        verdict = quote_in_file(answer, package)
        if verdict != "ok":
            our_reject.append(item["id"])
        docs = {name: check.norm(text) for name, text in package.files.items()}
        quote = check.norm(answer.quote)
        in_any = any(quote in text for text in docs.values()) if len(quote) >= 8 else False
        in_named = quote in docs.get(answer.file, "")
        if in_any and not in_named:
            quote_gap.append({"id": item["id"], "file": answer.file})
        if answer.status == "ответ":
            expected_numbers = check.numbers(answer.quote)
            got = check.numbers(answer.answer)
            if got and expected_numbers and not all(any(abs(x - y) < 0.01 for y in expected_numbers) for x in got):
                value_gap.append({"id": item["id"], "answer": answer.answer, "quote": answer.quote[:120]})
        judged, why = check.judge(item, answer.model_dump(), docs)
        if judged != "верно":
            log("D", "checker not correct", {"id": item["id"], "verdict": judged, "why": why, "status": answer.status})
    log(
        "A",
        "quote gaps",
        {"our_reject": our_reject, "in_other_file_only": quote_gap, "n": len(gold)},
    )
    log("B", "answer numbers missing from quote", {"rows": value_gap, "count": len(value_gap)})
    probe = read_csv(ROOT / "results" / "probe_answers.csv")
    log("E", "probe rows", {"n": len(probe), "statuses": [f"{row.id}:{row.status}" for row in probe]})


if __name__ == "__main__":
    main()
