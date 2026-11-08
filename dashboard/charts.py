"""Графики дашборда. Новые рисунки участник C добавляет в этот файл."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go

from dashboard.theme import COLORS

_FONT = "Segoe UI, sans-serif"
_VERDICT_COLORS = {
    "верно": "#2e7d32",
    "осторожно": "#f9a825",
    "обман": "#c62828",
}


def bars(labels: list[str], values: list[int | float], title: str, *, horizontal: bool = False) -> go.Figure:
    if horizontal:
        chart = go.Bar(y=labels, x=values, orientation="h")
    else:
        chart = go.Bar(x=labels, y=values)
    figure = go.Figure(chart)
    figure.update_layout(
        title=title,
        font={"family": _FONT},
        margin={"l": 20, "r": 20, "t": 48, "b": 20},
        height=max(320, 42 * len(labels)) if horizontal else 380,
        yaxis={"autorange": "reversed"} if horizontal else {},
    )
    return figure


def verdict_stack(by_type: dict[str, dict[str, int]], title: str) -> go.Figure:
    labels = sorted(by_type)
    figure = go.Figure()
    for verdict, color in _VERDICT_COLORS.items():
        figure.add_bar(
            name=verdict,
            x=labels,
            y=[by_type[label][verdict] for label in labels],
            marker_color=color,
        )
    figure.update_layout(
        barmode="stack",
        title=title,
        font={"family": _FONT},
        margin={"l": 20, "r": 20, "t": 48, "b": 80},
        height=420,
        legend={"orientation": "h"},
    )
    return figure


def index_pair(before: float, after: float) -> go.Figure:
    figure = go.Figure(
        go.Bar(
            x=["было", "стало"],
            y=[before, after],
            marker_color=[COLORS["before"], COLORS["after"]],
            text=[f"{before:.1f}", f"{after:.1f}"],
            textposition="outside",
        )
    )
    figure.update_layout(
        title="Рост индекса доверия",
        font={"family": _FONT},
        margin={"l": 20, "r": 20, "t": 48, "b": 20},
        height=400,
        showlegend=False,
        yaxis={"range": [-100, 110]},
    )
    return figure


def trust_bar(runs: list[dict[str, object]], title: str = "Рост индекса доверия") -> go.Figure:
    import pandas as pd

    frame = pd.DataFrame(runs)
    figure = px.bar(
        frame,
        x="name",
        y="trust_index",
        color="name",
        color_discrete_map={"было": COLORS["before"], "стало": COLORS["after"]},
        text_auto=".1f",
        labels={"name": "Версия", "trust_index": "Индекс доверия"},
        title=title,
    )
    figure.update_layout(showlegend=False, height=400, margin=dict(t=40, b=0, l=0, r=0), font={"family": _FONT})
    return figure


def types_compare(before: dict[str, dict[str, int]], after: dict[str, dict[str, int]]) -> go.Figure:
    import pandas as pd

    rows: list[dict[str, object]] = []
    for q_type, stats in before.items():
        total = max(int(stats["total"]), 1)
        rows.append({"Тип вопроса": q_type, "Версия": "было", "Доля верных": stats["correct"] / total * 100})
    for q_type, stats in after.items():
        total = max(int(stats["total"]), 1)
        rows.append({"Тип вопроса": q_type, "Версия": "стало", "Доля верных": stats["correct"] / total * 100})
    frame = pd.DataFrame(rows)
    figure = px.bar(
        frame,
        x="Тип вопроса",
        y="Доля верных",
        color="Версия",
        barmode="group",
        color_discrete_map={"было": COLORS["before"], "стало": COLORS["after"]},
        labels={"Доля верных": "Процент верных ответов (%)", "Тип вопроса": ""},
        text_auto=".0f",
    )
    figure.update_layout(
        height=450,
        margin=dict(t=20, b=0, l=0, r=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font={"family": _FONT},
    )
    return figure


def critics_bar(critics: list[dict[str, object]]) -> go.Figure:
    import pandas as pd

    frame = pd.DataFrame(critics)
    frame["Добавлено баллов"] = frame["trust_after"] - frame["trust_before"]
    figure = px.bar(
        frame,
        x="Добавлено баллов",
        y="name",
        orientation="h",
        color_discrete_sequence=[COLORS["after"]],
        text_auto=".1f",
        labels={"name": "", "Добавлено баллов": "Прирост индекса доверия"},
    )
    figure.update_layout(height=350, margin=dict(t=10, b=0, l=0, r=0), yaxis=dict(autorange="reversed"), font={"family": _FONT})
    return figure
