"""Обзор данных и три страницы команды. Запуск: uv run dashboard [a|b|c]."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.charts import bars
from dashboard.load import count_by, load_gold, load_packages, load_questions
from design.copy import NAV_A, NAV_B, NAV_C, NAV_OVERVIEW, PAGE_TITLE
from design.sidebar import render_sidebar


def _render(filename: str):
    path = Path(__file__).resolve().parent / "screens" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"не найден модуль страницы {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render


def _choice() -> str:
    for arg in sys.argv[1:]:
        if arg.lower() in {"a", "b", "c"}:
            return arg.lower()
    return ""


def overview() -> None:
    st.header("Обзор")
    st.caption("Одинаковые данные закупок лежат в data/. Прогоны, кэш и вердикты остаются на этом компьютере.")
    questions = load_questions()
    gold = load_gold()
    packages = load_packages()
    one, two, three, four = st.columns(4)
    one.metric("Пакетов", len(packages))
    two.metric("Вопросов", len(questions))
    three.metric("Файлов", sum(int(item["files"]) for item in packages))
    four.metric("С изменениями извещения", sum(1 for item in packages if item["changes"]))
    by_package = count_by(questions, "package")
    if by_package:
        labels, values = zip(*by_package, strict=True)
        st.plotly_chart(bars(list(labels), list(values), "Вопросы по закупкам"), width="stretch")
    by_type = count_by(gold, "type")
    if by_type:
        labels, values = zip(*by_type, strict=True)
        st.plotly_chart(
            bars(
                list(labels),
                list(values),
                "Типы вопросов организатора, не прогон модели",
                horizontal=True,
            ),
            width="stretch",
        )
    st.dataframe(
        [
            {
                "пакет": item["id"],
                "файлов": item["files"],
                "изменения извещения": "есть" if item["changes"] else "нет",
                "файлы": ", ".join(item["names"]),
            }
            for item in packages
        ],
        width="stretch",
        hide_index=True,
    )


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, layout="wide", initial_sidebar_state="expanded")
    render_sidebar()
    choice = _choice()
    navigation = st.navigation(
        [
            st.Page(overview, title=NAV_OVERVIEW, default=choice == ""),
            st.Page(_render("01_A_пайплайн.py"), title=NAV_A, url_path="a", default=choice == "a"),
            st.Page(_render("02_B_проверки.py"), title=NAV_B, url_path="b", default=choice == "b"),
            st.Page(_render("03_C_графики.py"), title=NAV_C, url_path="c", default=choice == "c"),
        ],
        expanded=True,
    )
    navigation.run()


main()
