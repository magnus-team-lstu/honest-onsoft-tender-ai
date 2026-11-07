"""Страница B. Код проверок живёт в src/checks/, сюда попадают только вердикты."""

from __future__ import annotations

import streamlit as st

from dashboard.charts import bars
from dashboard.load import load_verdicts


def render() -> None:
    st.header("Проверки")
    st.caption("Сигнатура для участника B: verify(answer, package) -> Verdict. Verdict — это ok или текст причины.")
    st.caption("Вердикты клади в results/verdicts.jsonl, по строке JSON: id, check, verdict. Расчёт проверок на этой странице не делается.")
    rows = load_verdicts()
    if not rows:
        st.info("Файла results/verdicts.jsonl ещё нет. Когда появятся проверки, столбцы отказов нарисуются сами.")
        return
    refused = [row for row in rows if str(row.get("verdict", "")) != "ok"]
    left, right = st.columns(2)
    left.metric("Проверок", len(rows))
    right.metric("Отказов", len(refused))
    counts: dict[str, int] = {}
    for row in refused:
        name = str(row.get("check") or "без имени")
        counts[name] = counts.get(name, 0) + 1
    if counts:
        labels = sorted(counts)
        st.plotly_chart(
            bars(labels, [counts[label] for label in labels], "Отказы по проверкам"),
            width="stretch",
        )
    st.dataframe(
        [
            {
                "id": row.get("id", ""),
                "check": row.get("check", ""),
                "verdict": row.get("verdict", ""),
            }
            for row in rows
        ],
        width="stretch",
        hide_index=True,
    )
