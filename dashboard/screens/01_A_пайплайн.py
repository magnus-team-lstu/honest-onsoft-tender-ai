"""Страница A. Пайплайн пишет results/answers.csv, кэш лежит в .cache/llm."""

from __future__ import annotations

import streamlit as st

from dashboard.charts import bars
from dashboard.load import count_by, load_answers, load_cache


def render() -> None:
    st.header("Пайплайн")
    st.caption("Файл прогона: results/answers.csv. Кэш модели: .cache/llm. Код запуска в src/.")
    answers = load_answers()
    cache = load_cache()
    left, middle, right = st.columns(3)
    left.metric("Строк в answers.csv", len(answers))
    middle.metric("Записей в кэше", cache["files"])
    right.metric("Токены запроса + ответа", cache["prompt_tokens"] + cache["completion_tokens"])
    if answers:
        labels, values = zip(*count_by(answers, "status"), strict=True)
        st.plotly_chart(bars(list(labels), list(values), "Статусы в answers.csv"), width="stretch")
        st.dataframe(
            [
                {
                    "id": row.get("id", ""),
                    "status": row.get("status", ""),
                    "answer": row.get("answer", ""),
                    "quote": row.get("quote", ""),
                    "file": row.get("file", ""),
                }
                for row in answers
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info(
            "Файла results/answers.csv ещё нет. Его создаст пайплайн. "
            "Команда будущего прогона: uv run python -m src.run "
            "--questions data/questions.csv --packages data/packages --out results/answers.csv"
        )
    if cache["files"] == 0:
        st.caption("Кэш пуст: повторных ответов модели на диске нет. Полные 71 вопрос отсюда не запускаются.")
