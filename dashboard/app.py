import sys
from pathlib import Path

# Добавляем корневую папку проекта в пути поиска Python
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import plotly.express as px
import pandas as pd
from dashboard.data import load_runs
from dashboard.theme import COLORS

# Настройка страницы (обязательно в самом начале)
st.set_page_config(page_title="Замеры ОНСОФТ", layout="wide", initial_sidebar_state="collapsed")

# Загружаем данные
runs = load_runs()

# Заголовок
st.title("Замеры качества ИИ")
st.markdown("Сравнение: как ИИ обманывал **до** внедрения проверок и как работает **после**.")

if not runs:
    st.warning("Данные не найдены. Запустите `uv run python eval/make_mock.py`")
else:
    # Достаем данные для графика "было/стало"
    df_runs = pd.DataFrame(runs)
    before = df_runs[df_runs["name"] == "было"].iloc[0]
    after = df_runs[df_runs["name"] == "стало"].iloc[0]

    # Панель 1: Главная цифра (Индекс доверия)
    st.subheader("1. Главная метрика: Индекс доверия")
    st.markdown("Формула: *(верные ответы − обманы) / все вопросы × 100*. Чем выше, тем лучше.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Было", value=f"{before['trust_index']:.1f}")
    with col2:
        # Дельта (разница) покажет зеленую стрелочку вверх
        delta = after['trust_index'] - before['trust_index']
        st.metric(label="Стало", value=f"{after['trust_index']:.1f}", delta=f"+{delta:.1f}")
    with col3:
        st.metric(label="Всего вопросов", value=before['total'])
        
    # Рисуем столбчатый график
    fig_trust = px.bar(
        df_runs, 
        x="name", 
        y="trust_index",
        color="name",
        color_discrete_map={"было": COLORS["before"], "стало": COLORS["after"]},
        text_auto=".1f", # Пишем цифру на столбике
        labels={"name": "Версия", "trust_index": "Индекс доверия"},
        title="Рост индекса доверия"
    )
    # Убираем легенду, так как названия и так подписаны
    fig_trust.update_layout(showlegend=False, height=400, margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_trust, use_container_width=True)
    
    st.info("💡 **Что это значит?** ИИ стал ошибаться в 2 раза реже. Если раньше он часто выдумывал числа, то теперь проверки (от участников A и B) заставляют его признаваться, когда он не уверен.")
    st.divider() # Красивая линия-разделитель

    # Панель 2: Разбивка по типам вопросов
    st.subheader("2. Разбивка по типам вопросов")
    st.markdown("Показывает, на каких именно вопросах ИИ стало ошибаться меньше всего.")

    # Подготавливаем данные для графика
    by_type_data = []
    for q_type, stats in before['by_type'].items():
        by_type_data.append({
            "Тип вопроса": q_type,
            "Версия": "было",
            "Доля верных": stats['correct'] / stats['total'] * 100
        })
    for q_type, stats in after['by_type'].items():
        by_type_data.append({
            "Тип вопроса": q_type,
            "Версия": "стало",
            "Доля верных": stats['correct'] / stats['total'] * 100
        })
    
    df_types = pd.DataFrame(by_type_data)

    # Рисуем сгруппированный график
    fig_types = px.bar(
        df_types,
        x="Тип вопроса",
        y="Доля верных",
        color="Версия",
        barmode="group", # Столбики стоят рядом
        color_discrete_map={"было": COLORS["before"], "стало": COLORS["after"]},
        labels={"Доля верных": "Процент верных ответов (%)", "Тип вопроса": ""},
        text_auto=".0f" # Округляем до целых
    )
    fig_types.update_layout(
        height=450, 
        margin=dict(t=20, b=0, l=0, r=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1) # Легенда сверху
    )
    st.plotly_chart(fig_types, use_container_width=True)

    # Таблица с обманами по типам
    st.markdown("**Количество обманов по типам (чем меньше, тем лучше):**")
    
    table_data = []
    for q_type in before['by_type'].keys():
        table_data.append({
            "Тип вопроса": q_type,
            "Обманов «было»": before['by_type'][q_type]['deceptions'],
            "Обманов «стало»": after['by_type'][q_type]['deceptions']
        })
    df_table = pd.DataFrame(table_data)
    
    # Красиво выводим таблицу без индексов
    st.dataframe(df_table, hide_index=True, use_container_width=True)
    st.divider()

    # Панель 3: Пойманные обманы
    st.subheader("3. Пойманные обманы")
    st.markdown("Примеры того, как ИИ пытался обмануть, но система проверок (от участников A и B) поймала его.")

    # Загружаем данные (если они еще не загружены в этой сессии)
    from dashboard.data import load_caught
    caught = load_caught()

    if not caught:
        st.info("Пока нет пойманных обманов для отображения.")
    else:
        # Делаем фильтр по типам
        types = ["Все"] + list(set([c["type"] for c in caught]))
        selected_type = st.selectbox("Фильтр по типу обмана:", types)

        # Фильтруем данные
        filtered_caught = caught if selected_type == "Все" else [c for c in caught if c["type"] == selected_type]

        # Выводим каждый обман в виде раскрывающегося блока
        for item in filtered_caught:
            # Заголовок блока (ID и тип)
            title = f"{item['id']} — Тип: {item['type']}"
            
            with st.expander(title):
                st.markdown(f"**Вопрос:** {item['question']}")
                st.markdown(f"❌ **Неверный ответ ИИ:** :red[{item['wrong_answer']}]")
                st.markdown(f"🛡️ **Кто поймал:** {item['caught_by']}")
                st.markdown(f"✅ **Исправленный ответ:** :green[{item['fixed_answer']}]")