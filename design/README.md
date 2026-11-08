# Дизайн дашборда

Правь файлы здесь. Логика данных остаётся в `dashboard/`.

**Для доработки через ИИ:** исходник участника C лежит в `from_participant_c/` (самодостаточный макет + `BRIEF_FOR_AI.md`).

| Файл | Зачем |
| --- | --- |
| `theme.py` | Цвета Plotly и отступы графиков |
| `copy.py` | Заголовки, подписи, вкладки, текст боковой панели |
| `streamlit.toml` | Тема Streamlit (фон, акцент, шрифт) |
| `assets/logo.jpg` | Логотип в сайдбаре |
| `sidebar.py` | Разметка боковой панели (можно менять блоки) |
| `apply.py` | Синхронизация `streamlit.toml` → `.streamlit/config.toml` |

После правок перезапусти дашборд:

```
uv run dashboard c
```

Команда `uv run dashboard` сама копирует `design/streamlit.toml` перед запуском.
