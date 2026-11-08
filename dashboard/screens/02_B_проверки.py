"""Страница B. Код проверок в src/checks/, сюда попадают вердикты и замер вклада.

Данные готовит команда: uv run python -m src.checks.report --answers results/answers.csv
"""

from __future__ import annotations

import json

import streamlit as st

from dashboard.charts import bars
from dashboard.load import RESULTS, load_verdicts


def _report() -> dict | None:
    path = RESULTS / "checks_report.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def render() -> None:
    st.header("Проверки")
    st.caption(
        "Цитату, числа, изменения извещения и расхождения проверяет код, а не модель. "
        "Данные: uv run python -m src.checks.report --answers results/answers.csv"
    )
    rows = load_verdicts()
    if not rows:
        st.info("Файла results/verdicts.jsonl ещё нет. Он появится после команды из подписи выше.")
        return

    refused = [row for row in rows if str(row.get("verdict", "")) != "ok"]
    answers = {str(row.get("id")) for row in rows}
    flagged = {str(row.get("id")) for row in refused}
    one, two, three = st.columns(3)
    one.metric("Ответов проверено", len(answers))
    two.metric("Ответов с отказом", len(flagged))
    three.metric("Отказов всего", len(refused))

    counts: dict[str, int] = {}
    for row in refused:
        name = str(row.get("check") or "без имени")
        counts[name] = counts.get(name, 0) + 1
    if counts:
        labels = sorted(counts, key=lambda name: -counts[name])
        st.plotly_chart(bars(labels, [counts[n] for n in labels], "Отказы по проверкам"), width="stretch")

    report = _report()
    if report:
        st.subheader("Вклад проверок в индекс доверия")
        st.caption(
            "Оценка без новых запросов: отклонённый ответ считается «не знаю». "
            "С повторным запросом в пайплайне прирост бывает больше."
        )
        left, right = st.columns(2)
        left.metric("Индекс без проверок", report.get("index_before", 0))
        right.metric(
            "Индекс с проверками",
            report.get("index_after", 0),
            delta=round(float(report.get("index_after", 0)) - float(report.get("index_before", 0)), 1),
        )
        st.dataframe(
            [
                {
                    "проверка": item["title"],
                    "поймала обманов": len(item["caught_lies"]),
                    "зря отклонила": len(item["false_alarms"]),
                    "индекс после": item["index_cumulative"],
                    "какие вопросы": ", ".join(item["caught_lies"]),
                }
                for item in report.get("checks", [])
            ],
            width="stretch",
            hide_index=True,
        )

    st.subheader("Отказы с причинами")
    st.dataframe(
        [{"id": r.get("id", ""), "проверка": r.get("check", ""), "причина": r.get("verdict", "")} for r in refused],
        width="stretch",
        hide_index=True,
    )
