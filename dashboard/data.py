import json
from pathlib import Path

RESULTS_DIR = Path("results")

def _load_json(filename):
    """Вспомогательная функция для чтения JSON"""
    filepath = RESULTS_DIR / filename
    if not filepath.exists():
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def load_runs():
    """Загружает данные о запусках (было/стало)"""
    return _load_json("runs.json")

def load_caught():
    """Загружает данные о пойманных обманах"""
    return _load_json("caught.json")

def load_critics():
    """Загружает данные о вкладе проверок"""
    return _load_json("critics.json")