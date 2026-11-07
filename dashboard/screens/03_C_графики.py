"""Страница C. Индекс рисуется из CSV оценщика. Новые графики — в dashboard/charts.py и в этом файле."""

from __future__ import annotations

import streamlit as st

from dashboard.charts import bars, index_pair, verdict_stack
from dashboard.load import count_by, load_eval, load_eval_pair, load_gold, summarize_eval


def _show_summary(title: str, summary: dict[str, object]) -> None:
    counts = summary["counts"]
    assert isinstance(counts, dict)
    index = float(summary["index"])
    one, two, three, four = st.columns(4)
    one.metric(title, f"{index:.1f}")
    two.metric("Верно", counts["верно"])
    three.metric("Осторожно", counts["осторожно"])
    four.metric("Обман", counts["обман"])
    by_type = summary["by_type"]
    assert isinstance(by_type, dict)
    st.plotly_chart(verdict_stack(by_type, "Разбивка по типам вопросов"), width="stretch")
    lies = summary["lies"]
    assert isinstance(lies, list)
    if lies:
        st.subheader("Где оценщик увидел обман")
        st.dataframe(
            [
                {"id": row.get("id", ""), "type": row.get("type", ""), "why": row.get("why", "")}
                for row in lies
            ],
            width="stretch",
            hide_index=True,
        )


def render() -> None:
    st.header("Было / стало")
    st.caption("Индекс считает data/check.py. Эта страница только рисует его CSV. Новые графики добавляй в dashboard/charts.py.")
    before_rows, after_rows = load_eval_pair()
    before = summarize_eval(before_rows)
    after = summarize_eval(after_rows)
    if before and after:
        st.plotly_chart(
            index_pair(float(before["index"]), float(after["index"])),
            width="stretch",
        )
        _show_summary("Стало", after)
    else:
        current = summarize_eval(load_eval())
        if current:
            _show_summary("Индекс доверия", current)
            st.caption(
                "Чтобы сравнить два замера, сохрани их как results/eval_before.csv и results/eval_after.csv."
            )
        else:
            st.info(
                "Прогона ещё нет. Индекс появится после команды: "
                "python data/check.py answers.csv --out results/eval.csv"
            )
    labels_values = count_by(load_gold(), "type")
    if labels_values:
        labels, values = zip(*labels_values, strict=True)
        st.plotly_chart(
            bars(list(labels), list(values), "Состав вопросов организатора, не прогон модели", horizontal=True),
            width="stretch",
        )
