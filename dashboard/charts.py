"""Графики дашборда. Новые рисунки участник C добавляет в этот файл."""

from __future__ import annotations

import plotly.graph_objects as go

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
            marker_color=["#90a4ae", "#1565c0"],
            text=[f"{before:.1f}", f"{after:.1f}"],
            textposition="outside",
        )
    )
    figure.update_layout(
        title="Индекс доверия",
        font={"family": _FONT},
        margin={"l": 20, "r": 20, "t": 48, "b": 20},
        height=380,
        yaxis={"range": [-100, 110]},
    )
    return figure
