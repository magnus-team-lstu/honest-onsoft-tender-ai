import sys
from pathlib import Path

# Умный поиск корневой папки проекта
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import streamlit as st
import plotly.express as px
import pandas as pd

from dashboard.data import load_runs, load_caught, load_critics
from dashboard.theme import COLORS

# Настройка страницы
st.set_page_config(page_title="Замеры ОНСОФТ", layout="wide", initial_sidebar_state="expanded")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    logo_path = Path(__file__).parent / "logo.jpg"
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
    else:
        st.markdown("<h1 style='text-align: center; font-size: 60px; margin-bottom: 0;'>🛡️</h1>", unsafe_allow_html=True)
        
    st.title("Проект ОНСОФТ")
    st.markdown("""
    **Задача:** ИИ, который не обманывает.
    
    **Метрика:** Индекс доверия = *(верные − обманы) / все вопросы × 100*.
    
    **Команда:** 
    - Участник A (Пайплайн)
    - Участник B (Проверки)
    - Участник C (Замеры и дашборд)
    """)
    st.divider()
    st.caption("Сделано для ИТ-Феста Школы 21, ноябрь 2026.")

# Загружаем данные
runs = load_runs()
caught = load_caught()
critics = load_critics()

st.title("Оценка качества ИИ")
st.markdown("Сравнение: как ИИ обманывал **до** внедрения проверок и как работает **после**.")

if not runs:
    st.warning("Данные не найдены. Запустите `uv run python eval/make_mock.py`")
else:
    df_runs = pd.DataFrame(runs)
    before = df_runs[df_runs["name"] == "было"].iloc[0]
    after = df_runs[df_runs["name"] == "стало"].iloc[0]

    # --- СОЗДАЕМ ВКЛАДКИ ---
    tab1, tab2, tab3 = st.tabs(["📊 Главное", "🛡️ Пойманные обманы", "⚙️ Детали замеров"])

    # ВКЛАДКА 1: ГЛАВНОЕ (Панели 1 и 2)
    with tab1:
        st.subheader("1. Главная метрика: Индекс доверия")
        st.markdown("Формула: *(верные ответы − обманы) / все вопросы × 100*. Чем выше, тем лучше.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Было", value=f"{before['trust_index']:.1f}")
        with col2:
            delta = after['trust_index'] - before['trust_index']
            st.metric(label="Стало", value=f"{after['trust_index']:.1f}", delta=f"+{delta:.1f}")
        with col3:
            st.metric(label="Всего вопросов", value=before['total'])
            
        fig_trust = px.bar(
            df_runs, x="name", y="trust_index", color="name",
            color_discrete_map={"было": COLORS["before"], "стало": COLORS["after"]},
            text_auto=".1f", labels={"name": "Версия", "trust_index": "Индекс доверия"},
            title="Рост индекса доверия"
        )
        fig_trust.update_layout(showlegend=False, height=400, margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig_trust, use_container_width=True)
        
        st.info("💡 **Что это значит?** ИИ стал ошибаться в 2 раза реже. Проверки заставляют его признаваться, когда он не уверен.")

        st.divider()

        st.subheader("2. Разбивка по типам вопросов")
        by_type_data = []
        for q_type, stats in before['by_type'].items():
            by_type_data.append({"Тип вопроса": q_type, "Версия": "было", "Доля верных": stats['correct'] / stats['total'] * 100})
        for q_type, stats in after['by_type'].items():
            by_type_data.append({"Тип вопроса": q_type, "Версия": "стало", "Доля верных": stats['correct'] / stats['total'] * 100})
        
        df_types = pd.DataFrame(by_type_data)
        fig_types = px.bar(
            df_types, x="Тип вопроса", y="Доля верных", color="Версия", barmode="group",
            color_discrete_map={"было": COLORS["before"], "стало": COLORS["after"]},
            labels={"Доля верных": "Процент верных ответов (%)", "Тип вопроса": ""},
            text_auto=".0f"
        )
        fig_types.update_layout(height=450, margin=dict(t=20, b=0, l=0, r=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_types, use_container_width=True)

    # ВКЛАДКА 2: ПОЙМАННЫЕ ОБМАНЫ (Панель 3)
    with tab2:
        st.subheader("3. Пойманные обманы")
        st.markdown("Примеры того, как ИИ пытался обмануть, но система проверок (от участников A и B) поймала его.")
        
        if not caught:
            st.info("Пока нет пойманных обманов для отображения.")
        else:
            types = ["Все"] + list(set([c["type"] for c in caught]))
            selected_type = st.selectbox("Фильтр по типу обмана:", types)
            filtered_caught = caught if selected_type == "Все" else [c for c in caught if c["type"] == selected_type]

            for item in filtered_caught:
                title = f"{item['id']} — Тип: {item['type']}"
                with st.expander(title):
                    st.markdown(f"**Вопрос:** {item['question']}")
                    st.markdown(f"❌ **Неверный ответ ИИ:** :red[{item['wrong_answer']}]")
                    st.markdown(f"🛡️ **Кто поймал:** {item['caught_by']}")
                    st.markdown(f"✅ **Исправленный ответ:** :green[{item['fixed_answer']}]")

    # ВКЛАДКА 3: ДЕТАЛИ (Панели 4 и 5)
    with tab3:
        st.subheader("4. Расход ресурсов и время")
        col4_1, col4_2, col4_3 = st.columns(3)
        with col4_1:
            st.metric(label="Запросов к модели (было → стало)", value=f"{after['requests']}", delta=f"+{after['requests'] - before['requests']}", delta_color="inverse")
        with col4_2:
            st.metric(label="Потрачено токенов", value=f"{after['tokens']:,}")
        with col4_3:
            minutes = after['seconds'] // 60
            st.metric(label="Время на один набор (мин)", value=f"{minutes}")

        st.divider()

        st.subheader("5. Вклад проверок (критиков)")
        if not critics:
            st.info("Данные о вкладе проверок пока не готовы.")
        else:
            df_critics = pd.DataFrame(critics)
            df_critics["Добавлено баллов"] = df_critics["trust_after"] - df_critics["trust_before"]
            fig_critics = px.bar(
                df_critics, x="Добавлено баллов", y="name", orientation="h",
                color_discrete_sequence=[COLORS["after"]], text_auto=".1f",
                labels={"name": "", "Добавлено баллов": "Прирост индекса доверия"}
            )
            fig_critics.update_layout(height=350, margin=dict(t=10, b=0, l=0, r=0), yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_critics, use_container_width=True)