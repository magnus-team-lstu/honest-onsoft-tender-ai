# Цвета для графиков
COLORS = {
    "before": "#a0a0a0",      # Серый "было"
    "after": "#1d9e75",       # Зеленый "стало"
    "deception": "#d85a30",   # Красный "обман"
    "unknown": "#f2a93b",     # Желтый "не знаю"
}

# Цвета для разных вердиктов (нужно для функции verdict_stack в charts.py)
VERDICT_COLORS = {
    "верно": COLORS["after"],
    "осторожно": COLORS["unknown"],
    "обман": COLORS["deception"],
}

# Шрифт
FONT_FAMILY = "sans serif"

# Размеры графиков (высота в пикселях)
CHART_HEIGHT_TRUST = 400      # Главный график (Индекс доверия)
CHART_HEIGHT_BAR = 400        # Запасной вариант
CHART_HEIGHT_TYPES = 400      # Разбивка по типам вопросов
CHART_HEIGHT_CRITICS = 300    # Вклад проверок

# Отступы
CHART_MARGIN_DEFAULT = dict(t=40, b=20, l=20, r=20)