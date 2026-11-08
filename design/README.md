# Дизайн дашборда

Правь файлы здесь - логика данных остаётся в `dashboard/`.

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
