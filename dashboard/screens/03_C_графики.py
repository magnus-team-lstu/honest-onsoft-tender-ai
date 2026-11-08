"""Страница C: панели участника C на реальных CSV и JSON из results/."""

from __future__ import annotations

import streamlit as st

from dashboard.charts import critics_bar, trust_bar, types_compare
from dashboard.metrics import load_caught, load_critics, load_runs
from design.copy import C_LEAD, C_TAB_CAUGHT, C_TAB_DETAILS, C_TAB_MAIN, C_TITLE


def render() -> None:
    st.title(C_TITLE)
    st.markdown(C_LEAD)

    runs = load_runs()
    caught = load_caught()
    critics = load_critics()

    if not runs:
        st.warning(
            "Нет замеров. Сначала прогон и оценка:\n\n"
            "`uv run python -m src.run --questions data/questions.csv --packages data/packages --out results/answers.csv`\n\n"
            "`uv run python data/check.py results/answers.csv --out results/eval.csv`"
        )
        st.caption("Для сравнения два прогона сохрани как `results/eval_before.csv` и `results/eval_after.csv`.")
        st.caption("Демо вклада проверок: `uv run python eval/make_mock.py` -> `results/critics.json`.")
        return

    has_pair = len(runs) >= 2 and runs[0]["name"] == "было" and runs[1]["name"] == "стало"
    before = runs[0] if has_pair else None
    after = runs[-1]

    tab1, tab2, tab3 = st.tabs([C_TAB_MAIN, C_TAB_CAUGHT, C_TAB_DETAILS])

    with tab1:
        st.subheader("1. Главная метрика: Индекс доверия")
        st.markdown("Формула: *(верные - обманы) / все вопросы * 100*.")

        col1, col2, col3 = st.columns(3)
        if has_pair and before:
            with col1:
                st.metric(label="Было", value=f"{float(before['trust_index']):.1f}")
            with col2:
                delta = float(after["trust_index"]) - float(before["trust_index"])
                st.metric(label="Стало", value=f"{float(after['trust_index']):.1f}", delta=f"{delta:+.1f}")
        else:
            with col1:
                st.metric(label="Текущий прогон", value=f"{float(after['trust_index']):.1f}")
        with col3:
            st.metric(label="Всего вопросов", value=int(after["total"]))

        st.plotly_chart(trust_bar(runs if has_pair else [after]), width="stretch")

        st.divider()
        st.subheader("2. Разбивка по типам вопросов")
        if has_pair and before:
            st.plotly_chart(
                types_compare(before["by_type"], after["by_type"]),
                width="stretch",
            )
        else:
            st.caption("Нужны оба файла `eval_before.csv` и `eval_after.csv` для сравнения по типам.")

    with tab2:
        st.subheader("3. Пойманные обманы")
        st.markdown("Строки с вердиктом **обман** в `results/eval.csv` плюс ответы из `results/answers.csv`.")
        if not caught:
            st.success("В текущем замере обманов по оценщику нет.")
        else:
            types = ["Все"] + sorted({item["type"] for item in caught if item.get("type")})
            selected = st.selectbox("Фильтр по типу:", types)
            filtered = caught if selected == "Все" else [item for item in caught if item.get("type") == selected]
            for item in filtered:
                with st.expander(f"{item['id']} - {item.get('type', '')}"):
                    st.markdown(f"**Вопрос:** {item.get('question', '')}")
                    st.markdown(f"**Ответ модели:** {item.get('wrong_answer', '')}")
                    st.markdown(f"**Почему обман:** {item.get('caught_by', '')}")
                    st.markdown(f"**Ожидание организатора:** {item.get('fixed_answer', '')}")

    with tab3:
        st.subheader("4. Расход ресурсов")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if has_pair and before:
                st.metric(
                    label="Запросов в кэше (было -> стало)",
                    value=f"{int(after.get('requests', 0))}",
                    delta=f"{int(after.get('requests', 0)) - int(before.get('requests', 0))}",
                    delta_color="off",
                )
            else:
                st.metric(label="Файлов в кэше LLM", value=int(after.get("requests", 0)))
        with col_b:
            st.metric(label="Токенов (из кэша)", value=f"{int(after.get('tokens', 0)):,}")
        with col_c:
            st.metric(label="Секунд в замере", value=int(after.get("seconds", 0)) or "нет")

        st.divider()
        st.subheader("5. Вклад проверок (критиков)")
        if not critics:
            st.info("Пока нет `results/critics.json`. Заготовка: `uv run python eval/make_mock.py`.")
        else:
            st.plotly_chart(critics_bar(critics), width="stretch")