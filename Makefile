# Прогоны одной командой. Нужны uv и GNU make, ключ в .env.
# make all        было + стало + оценка + вклад проверок
# make control CQ=путь/questions.csv CP=путь/packages   контрольный набор на защите

export PYTHONIOENCODING := utf-8

Q  := data/questions.csv
P  := data/packages
R  := results
CQ ?= control/questions.csv
CP ?= control/packages

.PHONY: all baseline full eval report dashboard demo test control

all: baseline full eval report

baseline:
	uv run python -m src.run --questions $(Q) --packages $(P) --out $(R)/answers_baseline.csv --mode baseline

full:
	uv run python -m src.run --questions $(Q) --packages $(P) --out $(R)/answers_full.csv --mode full

eval:
	uv run python data/check.py $(R)/answers_baseline.csv --out $(R)/eval_before.csv
	uv run python data/check.py $(R)/answers_full.csv --out $(R)/eval_after.csv

report:
	uv run python -m src.checks.report --answers $(R)/answers_baseline.csv

dashboard:
	uv run python -c "import shutil; shutil.copy('$(R)/answers_full.csv', '$(R)/answers.csv'); shutil.copy('$(R)/eval_after.csv', '$(R)/eval.csv')"
	uv run dashboard

demo:
	uv run python -m src.checks.demo

test:
	uv run pytest -q

control:
	uv run python -m src.run --questions $(CQ) --packages $(CP) --out $(R)/answers_control.csv --mode full
