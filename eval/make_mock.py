import json
from pathlib import Path

# Создаем папку results, если ее нет
results_dir = Path("results")
results_dir.mkdir(exist_ok=True)

# 1. Данные по запускам (было и стало)
runs = [
    {
        "name": "было",
        "trust_index": 12.7,
        "correct": 31,
        "deceptions": 22,
        "unknown": 18,
        "total": 71,
        "requests": 71,
        "tokens": 900000,
        "seconds": 420,
        "by_type": {
            "число": {"correct": 10, "deceptions": 6, "unknown": 2, "total": 18},
            "срок": {"correct": 5, "deceptions": 4, "unknown": 3, "total": 12},
            "требование": {"correct": 6, "deceptions": 5, "unknown": 4, "total": 15},
            "изменение": {"correct": 2, "deceptions": 5, "unknown": 1, "total": 8},
            "расхождение": {"correct": 4, "deceptions": 1, "unknown": 3, "total": 8},
            "нет в документах": {"correct": 4, "deceptions": 1, "unknown": 5, "total": 10}
        }
    },
    {
        "name": "стало",
        "trust_index": 58.0,
        "correct": 50,
        "deceptions": 9,
        "unknown": 12,
        "total": 71,
        "requests": 190,
        "tokens": 1500000,
        "seconds": 1100,
        "by_type": {
            "число": {"correct": 15, "deceptions": 1, "unknown": 2, "total": 18},
            "срок": {"correct": 9, "deceptions": 1, "unknown": 2, "total": 12},
            "требование": {"correct": 12, "deceptions": 2, "unknown": 1, "total": 15},
            "изменение": {"correct": 7, "deceptions": 1, "unknown": 0, "total": 8},
            "расхождение": {"correct": 5, "deceptions": 2, "unknown": 1, "total": 8},
            "нет в документах": {"correct": 2, "deceptions": 2, "unknown": 6, "total": 10}
        }
    }
]

# 2. Пойманные обманы (для панели 3)
caught = [
    {
        "id": "P01-03",
        "type": "изменение",
        "question": "Какой срок подачи заявок?",
        "wrong_answer": "24.11.2026",
        "caught_by": "Проверка изменений извещения",
        "fixed_answer": "27.11.2026"
    },
    {
        "id": "P02-11",
        "type": "расхождение",
        "question": "Сколько дней на выполнение работ?",
        "wrong_answer": "60 дней",
        "caught_by": "Детектор расхождений (извещение и контракт)",
        "fixed_answer": "Расхождение: 60 и 75 дней"
    },
    {
        "id": "P03-07",
        "type": "число",
        "question": "Какой размер обеспечения заявки?",
        "wrong_answer": "180000 руб.",
        "caught_by": "Проверка цитаты (числа нет в цитате)",
        "fixed_answer": "18000 руб."
    }
]

# 3. Вклад проверок (появится позже)
critics = [
    {"name": "Проверка цитаты (дословно)", "trust_before": 12.7, "trust_after": 25.0},
    {"name": "Проверка чисел в цитате", "trust_before": 25.0, "trust_after": 38.5},
    {"name": "Изменения извещения", "trust_before": 38.5, "trust_after": 50.0},
    {"name": "Детектор расхождений", "trust_before": 50.0, "trust_after": 58.0}
]

# Сохраняем файлы
with open(results_dir / "runs.json", "w", encoding="utf-8") as f:
    json.dump(runs, f, ensure_ascii=False, indent=2)

with open(results_dir / "caught.json", "w", encoding="utf-8") as f:
    json.dump(caught, f, ensure_ascii=False, indent=2)

with open(results_dir / "critics.json", "w", encoding="utf-8") as f:
    json.dump(critics, f, ensure_ascii=False, indent=2)

print("✅ Условные данные успешно созданы в папке results/!")