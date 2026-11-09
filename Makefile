# Прогоны одной командой.
#
# Что нужно:
#   uv        ставит зависимости и запускает Python из .venv (uv run ...);
#   GNU make  запускает цели из этого файла;
#   .env      ключ ONSOFT_API_KEY (или LLM_API_KEY), образец в .env.example.
#             Ключ нужен целям, которые спрашивают модель: all, baseline, full, control.
#
# Цели:
#   make all        baseline + full + eval + report: было, стало, оценка, вклад проверок
#   make baseline   ответы без проверок              -> results/answers_baseline.csv
#   make full       ответы с поиском и проверками    -> results/answers_full.csv
#   make eval       оценка обоих файлов ответов      -> results/eval_before.csv, eval_after.csv
#   make report     вклад каждой проверки            -> results/verdicts.jsonl, checks_report.json, critics.json
#   make dashboard  открыть дашборд (после make all)
#   make demo       демо проверок на 8 ответах, без модели
#   make test       тесты pytest, без модели
#   make control CQ=путь/questions.csv CP=путь/packages   контрольный набор на защите
#
# Ответы модели кэшируются в .cache/llm: повторный прогон тех же вопросов
# не тратит запросы. Чтобы спросить модель заново, удалите эту папку.
#
# @ перед командой: make не печатает саму команду, только её вывод.
# Посмотреть, какие команды выполнит цель, не запуская их: make -n <цель>.

# export передаёт переменную всем командам ниже и их дочерним процессам:
# Python пишет вывод в UTF-8. Без этого на Windows ломается русский текст,
# когда вывод идёт не в консоль, а в другую программу (например, run.py
# читает вывод data/check.py).
export PYTHONIOENCODING := utf-8

# Пути по умолчанию. Любой можно заменить из командной строки,
# например: make full Q=data/other_questions.csv
#   Q  файл с вопросами (id;package;question)
#   P  папка с пакетами закупок, по подпапке на пакет
#   R  куда писать результаты
Q  := data/questions.csv
P  := data/packages
R  := results

# Контрольный набор для make control. ?= задаёт значение, только если
# переменную не передали в командной строке или через окружение. Папки
# control/ в репозитории нет: выданный архив распаковывают в control/.
# Файл вопросов ищется как control/questions_control.csv, затем control/questions.csv.
CQ ?= $(firstword $(wildcard control/questions_control.csv control/questions.csv) control/questions.csv)
CP ?= control/packages

# Имена целей не файлы. Без .PHONY make не запустил бы цель, если рядом
# есть файл или папка с таким же именем: например, make dashboard ответил бы
# «up to date», потому что папка dashboard/ уже есть.
.PHONY: all baseline full eval report dashboard demo test control

# Полный прогон: было, стало, оценка, вклад проверок.
# Цели выполняются по очереди слева направо. Не запускайте с -j: eval и
# report читают файлы, которые пишут baseline и full, а зависимости между
# ними здесь не прописаны.
all: baseline full eval report

# Было: ответы без проверок, точка отсчёта.
# Запускает src/run.py в режиме baseline: в запрос к модели целиком идут все
# файлы пакета, одна попытка, ответ ничем не проверяется.
# Пишет results/answers_baseline.csv (id;status;answer;quote;file).
# Когда ответы есть на все вопросы, run.py сам считает индекс доверия
# через data/check.py и печатает его.
baseline:
	@uv run python -m src.run --questions $(Q) --packages $(P) --out $(R)/answers_baseline.csv --mode baseline

# Стало: полный пайплайн.
# Запускает src/run.py в режиме full: в запрос идут только фрагменты пакета,
# найденные поиском (src/retrieval.py), ответ проверяет код из src/checks/.
# Если проверка не прошла, модель спрашивают ещё раз с указанием ошибки, всего
# до 3 попыток; не прошёл ни один ответ, тогда записывается «не знаю».
# Пишет results/answers_full.csv и, как baseline, печатает индекс.
full:
	@uv run python -m src.run --questions $(Q) --packages $(P) --out $(R)/answers_full.csv --mode full

# Оценка организатора: data/check.py сравнивает ответы с data/answers_public.json.
# Печатает индекс доверия (верно минус обман, в процентах от всех вопросов)
# и таблицу по типам вопросов, а --out сохраняет вердикт по каждому вопросу:
#   results/eval_before.csv  для ответов baseline
#   results/eval_after.csv   для ответов full
# Модель не спрашивает. Нужны оба файла ответов (make baseline full).
eval:
	@uv run python data/check.py $(R)/answers_baseline.csv --out $(R)/eval_before.csv
	@uv run python data/check.py $(R)/answers_full.csv --out $(R)/eval_after.csv

# Вклад проверок: src/checks/report.py прогоняет все 7 проверок по ответам
# baseline (их никто не проверял) и считает для каждой, сколько обманов она
# поймала, сколько верных ответов зря отклонила и как вырос бы индекс, если
# отклонённый ответ заменить на «не знаю».
# Пишет для дашборда:
#   results/verdicts.jsonl      вердикт каждой проверки по каждому ответу
#   results/checks_report.json  итог по проверкам
#   results/critics.json        прирост индекса по проверкам
# Модель не спрашивает.
report:
	@uv run python -m src.checks.report --answers $(R)/answers_baseline.csv

# Дашборд на Streamlit. Сначала make all: страницы читают файлы из results/.
# 1-я команда копирует ответы и оценку full в results/answers.csv и
#   results/eval.csv, которые дашборд читает по умолчанию. Копирует через
#   Python, а не cp, чтобы одинаково работало на Windows и Linux.
# 2-я команда: uv run dashboard -> dashboard/launch.py -> streamlit run
#   dashboard/app.py. Дашборд откроется на http://127.0.0.1:8501,
#   остановить: Ctrl+C.
dashboard:
	@uv run python -c "import shutil; shutil.copy('$(R)/answers_full.csv', '$(R)/answers.csv'); shutil.copy('$(R)/eval_after.csv', '$(R)/eval.csv')"
	@uv run dashboard

# Демо проверок без модели и без ключа: src/checks/demo.py.
# Во временной копии пакета P01 дописывает в извещение фразу-инъекцию и
# оценивает 8 заранее написанных ответов: 1 верный и 7 обманов, по одному на
# каждую проверку. Ожидаемый итог: индекс −75.0 без проверок и 12.5 с ними.
# Файлы в data/ не меняются.
demo:
	@uv run python -m src.checks.demo

# Тесты из папки tests/, -q даёт краткий вывод. Модель и ключ не нужны,
# эти же тесты запускает GitHub Actions на каждый push и pull request.
test:
	@uv run pytest -q

# Контрольный набор на защите: тот же режим full, что в make full, но на
# вопросах организатора. Пути передают при запуске:
#   make control CQ=путь/questions.csv CP=путь/packages
# Пишет results/answers_control.csv. Индекс run.py посчитает, только если
# рядом с questions.csv лежат answers_public.json и check.py; иначе напишет,
# что пропустил.
control:
	@uv run python -m src.run --questions $(CQ) --packages $(CP) --out $(R)/answers_control.csv --mode full
