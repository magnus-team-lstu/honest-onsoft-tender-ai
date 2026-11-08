# honest-onsoft-tender-ai
ИИ-помощник по документам госзакупок, который не обманывает: отвечает с дословной цитатой, проверяет числа и цитаты кодом и честно говорит «не знаю». Кейс ОНСОФТ, хакатон Школы 21, ноябрь 2026.

## Запуск ответов

Ключ лежит в `.env` и в код не попадает. На тренировочных данных ставь `--limit`, полный прогон 71 вопроса команда не делает сама.

```
uv run python -m src.run --questions data/questions.csv --packages data/packages --out results/answers.csv --mode baseline --limit 5
uv run python -m src.run --questions data/questions.csv --packages data/packages --out results/answers.csv --mode full --limit 5
```

Повтор той же команды берёт ответы из `.cache/llm` и новых запросов не делает. `--resume` пропускает id, которые уже есть в CSV. `--only P01-03` или `--only P01` берёт один вопрос или один пакет. `--mode baseline` отправляет пакет целиком и не проверяет цитату. `--mode full` режет длинный пакет, проверяет, что цитата есть в названном файле, и после трёх неудач пишет «не знаю».

## Дашборд

Каждый запускает его у себя. Откроется браузер на `127.0.0.1:8501`. Чужой компьютер этот адрес не видит. Данные закупок читаются из `data/`. Прогоны и кэш с диска подхватываются сами, если файлы уже лежат рядом.

```
uv run dashboard
uv run dashboard a
uv run dashboard b
uv run dashboard c
```

Первая команда открывает обзор. `a`, `b` и `c` сразу открывают страницу участника, остальные остаются в боковой панели.

| Страница | Что менять | Откуда цифры |
| --- | --- | --- |
| A. Пайплайн | `src/`, `dashboard/screens/01_A_пайплайн.py` | `results/answers.csv`, `.cache/llm` |
| B. Проверки | `src/checks/`, вердикты в `results/verdicts.jsonl` | `id`, `check`, `verdict` (`ok` или причина) |
| C. Было / стало | `dashboard/charts.py`, `dashboard/metrics.py`, `dashboard/screens/03_C_графики.py` | `results/eval.csv` или пара `eval_before.csv` / `eval_after.csv`; демо критиков — `uv run python eval/make_mock.py` |

Папка называется `screens`, а не `pages`: Streamlit забирает каталог `pages` под свой список страниц.

Индекс считает уже готовый оценщик, дашборд его не подменяет:

```
python data/check.py answers.csv --out results/eval.csv
```

Ключ модели в дашборд не передаётся.
