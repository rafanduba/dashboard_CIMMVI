"""Componentes visuais reutilizáveis."""

import plotly.graph_objects as go
from dash import html

from dashboard.config import (
    BORDER, CARD, CARD2, FONT, ICON_BG, MUTED,
    PALETA, PRIMARY, TEXT, TEXT_DIM,
)


def formata_brl(value, show_sign: bool = False) -> str:
    """Formata float para R$ com separadores brasileiros."""
    if value is None:
        return "—"
    try:
        v = float(value)
        abs_str = f"R$\u00a0{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if v < 0:
            return f"- {abs_str}"
        if show_sign and v > 0:
            return f"+ {abs_str}"
        return abs_str
    except (TypeError, ValueError):
        return "—"


def chart_layout(theme: str = "light", **kwargs) -> dict:
    """Layout base para gráficos Plotly com suporte a tema claro e escuro."""
    is_dark = (theme == "dark")
    text_color = "#f8fafc" if is_dark else "#1e293b"
    text_dim_color = "#94a3b8" if is_dark else "#475569"
    border_color = "#1e2333" if is_dark else "#cbd5e1"

    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=text_color, size=12),
        margin=dict(l=12, r=12, t=36, b=12),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=border_color,
            font=dict(color=text_dim_color, size=11),
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
        ),
        xaxis=dict(gridcolor=border_color, linecolor=border_color, tickfont=dict(color=text_dim_color, size=11)),
        yaxis=dict(gridcolor=border_color, linecolor=border_color, tickfont=dict(color=text_dim_color, size=11)),
        colorway=PALETA,
        hovermode="x unified",
    )
    base.update(kwargs)
    return base


def empty_fig(msg: str = "Sem dados para exibir", theme: str = "light") -> go.Figure:
    """Figura vazia com mensagem."""
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(
            text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(color=MUTED, size=13, family=FONT),
        )],
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=12, r=12, t=12, b=12),
    )
    return fig


def card(children, extra: dict | None = None, **kwargs) -> html.Div:
    """Card padrão com borda demarcada e elevação."""
    style = {
        "background": CARD,
        "border": f"1px solid {BORDER}",
        "borderRadius": "14px",
        "padding": "24px",
        "boxShadow": "0 4px 20px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.03)",
        "transition": "all 0.2s ease",
    }
    if extra:
        style.update(extra)
    return html.Div(children, style=style, **kwargs)


def label(text: str) -> html.Div:
    """Label em caixa alta."""
    return html.Div(text, style={
        "fontSize": "12px", "color": TEXT_DIM, "fontWeight": "600",
        "textTransform": "uppercase", "letterSpacing": "0.06em",
        "marginBottom": "6px",
    })


def section_title(text: str) -> html.Div:
    """Título de seção com barra e linha."""
    return html.Div([
        html.Div([
            html.Span("\u258c ", style={"color": PRIMARY, "fontSize": "18px", "lineHeight": "1"}),
            html.Span(text, style={
                "fontSize": "14px", "fontWeight": "700",
                "color": TEXT, "textTransform": "uppercase", "letterSpacing": "0.08em",
            }),
        ], style={"display": "flex", "alignItems": "center"}),
        html.Hr(style={"borderColor": BORDER, "margin": "10px 0 20px 0", "opacity": "0.6"}),
    ])


def kpi(output_id: str, label_text: str, icon: str,
        color: str = PRIMARY, sublabel: str = "") -> html.Div:
    """Card de KPI."""
    children = [
        html.Div([
            html.Span(icon, style={
                "fontSize": "18px",
                "background": ICON_BG.get(color, ICON_BG[PRIMARY]),
                "borderRadius": "10px",
                "padding": "7px 10px",
            }),
        ], style={"marginBottom": "14px"}),
        html.Div(label_text, style={
            "fontSize": "10px", "color": TEXT_DIM, "fontWeight": "600",
            "textTransform": "uppercase", "letterSpacing": "0.06em",
            "marginBottom": "6px",
        }),
        html.Div(id=output_id, style={
            "fontSize": "20px", "fontWeight": "700",
            "color": color, "fontVariantNumeric": "tabular-nums",
            "letterSpacing": "-0.02em",
        }),
    ]
    if sublabel:
        children.append(html.Div(sublabel, style={
            "fontSize": "10px", "color": MUTED, "marginTop": "4px",
        }))
    return card(children)