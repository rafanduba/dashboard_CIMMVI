# pyrefly: ignore [missing-import]
# dashboard/app.py
# Ponto de entrada do dashboard Dash – CIMMVI / AMVI.
#
# Uso (a partir da raiz do projeto):
#     python dashboard/app.py
#     python -m dashboard.app

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import logging
from datetime import date

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dash_table, dcc, html

logger = logging.getLogger(__name__)

# ── Importa queries com fallback caso o banco ainda não exista ───────────────
try:
    from dashboard.queries import (
        contagem_por_situacao,
        contas_disponiveis,
        entidades_disponiveis,
        entradas_saidas_mensais,
        evolucao_saldo_mensal,
        lancamentos_detalhados,
        periodo_disponivel,
        saidas_por_categoria,
        saidas_por_forma_pagamento,
        saldo_final_conta_1,
        saldo_final_conta_2,
        saldo_final_conta_3,
        saldo_final_geral,
        top_saidas,
        total_entradas,
        total_liquido,
        total_saidas,
        ultima_carga,
        valor_aguardando_aprovacao,
        saidas_em_aberto,
        entradas_em_aberto,
    )
    _DB_READY = True
except Exception as _e:
    logger.warning("Banco não disponível na inicialização: %s", _e)
    _DB_READY = False


# ════════════════════════════════════════════════════════════════════════════
# Design tokens
# ════════════════════════════════════════════════════════════════════════════
BG        = "#0d0f1a"
CARD      = "#141624"
CARD2     = "#1a1d2e"
BORDER    = "#252840"
PRIMARY   = "#818cf8"   # indigo-400
SECONDARY = "#a78bfa"   # violet-400
SUCCESS   = "#34d399"   # emerald-400
DANGER    = "#f87171"   # red-400
WARNING   = "#fbbf24"   # amber-400
INFO      = "#38bdf8"   # sky-400
MUTED     = "#64748b"   # slate-500
TEXT      = "#e2e8f0"   # slate-200
TEXT_DIM  = "#94a3b8"   # slate-400
FONT      = "Inter, system-ui, -apple-system, sans-serif"

CONTA_ESTILOS = {
    "CIMMVI - Rateio Banco do Brasil":  (PRIMARY,   "rgba(129,140,248,0.08)"),
    "CIMMVI - Licenciamento Caixa":     (SECONDARY, "rgba(167,139,250,0.08)"),
    "AMVI - Banco do Brasil - CC 439":  (INFO,      "rgba(56,189,248,0.08)"),
}

SITUACAO_CORES = {
    "Pago":                                                        SUCCESS,
    "Em aberto":                                                   DANGER,
    "Aguardando Aprovação":                                        WARNING,
    "Aprovado - Aguardando Pagamento":                             INFO,
    "Pagamento Realizado - Aguardando autorização Margarete":      MUTED,
    "Nao informado":                                               MUTED,
}

PALETA = [PRIMARY, SECONDARY, INFO, SUCCESS, WARNING, DANGER, "#fb923c", "#e879f9"]

ICON_BG = {
    SUCCESS:   "rgba(52,211,153,0.15)",
    DANGER:    "rgba(248,113,113,0.15)",
    WARNING:   "rgba(251,191,36,0.15)",
    PRIMARY:   "rgba(129,140,248,0.15)",
    INFO:      "rgba(56,189,248,0.15)",
    SECONDARY: "rgba(167,139,250,0.15)",
}


# ════════════════════════════════════════════════════════════════════════════
# Helpers visuais
# ════════════════════════════════════════════════════════════════════════════

def _brl(value, show_sign: bool = False) -> str:
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


def _chart_layout(**kwargs) -> dict:
    """Retorna o dict de layout base para os gráficos Plotly."""
    base = dict(
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font=dict(family=FONT, color=TEXT, size=12),
        margin=dict(l=12, r=12, t=36, b=12),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=BORDER,
            font=dict(color=TEXT_DIM, size=11),
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
        ),
        xaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=TEXT_DIM, size=11)),
        yaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=TEXT_DIM, size=11)),
        colorway=PALETA,
        hovermode="x unified",
    )
    base.update(kwargs)
    return base


def _empty_fig(msg: str = "Sem dados para exibir") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        annotations=[dict(
            text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(color=MUTED, size=13, family=FONT),
        )],
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=12, r=12, t=12, b=12),
    )
    return fig


def _card(children, extra: dict | None = None, **kwargs) -> html.Div:
    style = {
        "background": CARD,
        "border": f"1px solid {BORDER}",
        "borderRadius": "14px",
        "padding": "20px",
    }
    if extra:
        style.update(extra)
    return html.Div(children, style=style, **kwargs)


def _label(text: str) -> html.Div:
    return html.Div(text, style={
        "fontSize": "11px", "color": TEXT_DIM, "fontWeight": "600",
        "textTransform": "uppercase", "letterSpacing": "0.06em",
        "marginBottom": "6px",
    })


def _section_title(text: str) -> html.Div:
    """Título de seção com barra colorida e linha separadora."""
    return html.Div([
        html.Div([
            html.Span("\u258c ", style={"color": PRIMARY, "fontSize": "15px", "lineHeight": "1"}),
            html.Span(text, style={
                "fontSize": "11px", "fontWeight": "700",
                "color": TEXT_DIM, "textTransform": "uppercase", "letterSpacing": "0.1em",
            }),
        ], style={"display": "flex", "alignItems": "center"}),
        html.Hr(style={"borderColor": BORDER, "margin": "8px 0 16px 0", "opacity": "0.5"}),
    ])


def _kpi(output_id: str, label: str, icon: str, color: str = PRIMARY, sublabel: str = "") -> html.Div:
    children = [
        html.Div([
            html.Span(icon, style={
                "fontSize": "18px",
                "background": ICON_BG.get(color, ICON_BG[PRIMARY]),
                "borderRadius": "10px",
                "padding": "7px 10px",
            }),
        ], style={"marginBottom": "14px"}),
        html.Div(label, style={
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
    return _card(children)


# ════════════════════════════════════════════════════════════════════════════
# Valores iniciais (datas e opções dos dropdowns)
# ════════════════════════════════════════════════════════════════════════════
_hoje = str(date.today())
_ano_inicio = str(date.today().replace(month=1, day=1))

try:
    _p = periodo_disponivel() if _DB_READY else {}
    DATE_MIN     = _p.get("data_min") or _ano_inicio
    DATE_MAX     = _p.get("data_max") or _hoje
    START_PADRAO = DATE_MIN
    END_PADRAO   = DATE_MAX
except Exception:
    DATE_MIN = START_PADRAO = _ano_inicio
    DATE_MAX = END_PADRAO   = _hoje

try:
    _CONTAS = [{"label": "Todas as contas", "value": ""}] + [
        {"label": c, "value": c} for c in (contas_disponiveis() if _DB_READY else [])
    ]
    _ENTIDADES = [{"label": "Todas as entidades", "value": ""}] + [
        {"label": e, "value": e} for e in (entidades_disponiveis() if _DB_READY else [])
    ]
except Exception:
    _CONTAS    = [{"label": "Todas as contas", "value": ""}]
    _ENTIDADES = [{"label": "Todas as entidades", "value": ""}]


# ════════════════════════════════════════════════════════════════════════════
# Estilos reutilizáveis
# ════════════════════════════════════════════════════════════════════════════
_DD_STYLE = {
    "backgroundColor": CARD2,
    "border": f"1px solid {BORDER}",
    "borderRadius": "8px",
    "color": TEXT,
    "fontSize": "13px",
}

_TABLE_HEADER = {
    "backgroundColor": CARD2, "color": TEXT_DIM,
    "fontWeight": "600", "fontSize": "10px",
    "textTransform": "uppercase", "letterSpacing": "0.05em",
    "border": f"1px solid {BORDER}", "padding": "10px 12px",
    "fontFamily": FONT,
}

_TABLE_CELL = {
    "backgroundColor": CARD, "color": TEXT,
    "fontSize": "12px", "border": f"1px solid {BORDER}",
    "padding": "8px 12px", "fontFamily": FONT,
    "textOverflow": "ellipsis", "overflow": "hidden", "maxWidth": "200px",
}

_TABLE_COND = [
    {"if": {"row_index": "odd"}, "backgroundColor": CARD2},
    {"if": {"filter_query": '{situacao} = "Em aberto"'},            "color": DANGER,   "fontWeight": "600"},
    {"if": {"filter_query": '{situacao} = "Pago"'},                 "color": SUCCESS},
    {"if": {"filter_query": '{situacao} = "Aguardando Aprovação"'}, "color": WARNING},
    {"if": {"column_id": "entradas"},        "color": SUCCESS},
    {"if": {"column_id": "saidas"},          "color": DANGER},
    {"if": {"column_id": "saldo_acumulado"}, "color": INFO, "fontWeight": "600"},
]

_TAB_STYLE = {
    "background": CARD,
    "borderTop": "2px solid transparent",
    "border": f"1px solid {BORDER}",
    "borderBottom": "none",
    "color": TEXT_DIM,
    "fontFamily": FONT,
    "fontWeight": "600",
    "fontSize": "13px",
    "padding": "11px 22px",
    "borderRadius": "10px 10px 0 0",
    "marginRight": "4px",
    "cursor": "pointer",
}

_SELECTED_TAB_STYLE = {
    **_TAB_STYLE,
    "background": CARD2,
    "color": TEXT,
    "borderTop": f"2px solid {PRIMARY}",
}


# ════════════════════════════════════════════════════════════════════════════
# App e layout
# ════════════════════════════════════════════════════════════════════════════
app = Dash(
    __name__,
    title="Dashboard CIMMVI / AMVI",
    update_title=None,
    suppress_callback_exceptions=True,
)

# CSS injetado no <head>: escurece Dropdown e DatePickerRange
# (html.Style não existe em versões antigas do Dash; index_string é a forma correta)
app.index_string = """
<!DOCTYPE html>
<html>
  <head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <style>
      /* ── Dropdown (react-select v1 interno do Dash) ── */
      .Select-control {
        background-color: #1a1d2e !important;
        border: 1px solid #252840 !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
        box-shadow: none !important;
      }
      .Select-control:hover { border-color: #818cf8 !important; }
      .Select.is-open > .Select-control {
        border-color: #818cf8 !important;
        border-radius: 8px 8px 0 0 !important;
      }
      .Select-placeholder, .Select-value-label { color: #e2e8f0 !important; font-size: 13px !important; }
      .Select-arrow { border-top-color: #64748b !important; }
      .Select.is-open .Select-arrow { border-bottom-color: #818cf8 !important; }

      /* Menu de opções */
      .Select-menu-outer {
        background-color: #1a1d2e !important;
        border: 1px solid #818cf8 !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
        box-shadow: 0 8px 28px rgba(0,0,0,0.6) !important;
      }
      .Select-menu { background-color: #1a1d2e !important; }
      .Select-option {
        background-color: #1a1d2e !important;
        color: #e2e8f0 !important;
        font-size: 13px !important;
        padding: 9px 12px !important;
      }
      .Select-option.is-focused {
        background-color: rgba(129,140,248,0.18) !important;
        color: #818cf8 !important;
      }
      .Select-option.is-selected {
        background-color: rgba(129,140,248,0.25) !important;
        color: #818cf8 !important;
        font-weight: 600 !important;
      }
      .Select-noresults {
        background-color: #1a1d2e !important;
        color: #64748b !important;
        font-size: 13px !important;
      }
      .Select-input > input {
        color: #e2e8f0 !important;
        caret-color: #818cf8 !important;
        background-color: transparent !important;
      }

      /* ── DatePickerRange ── */
      .DateInput, .DateInput_input {
        background-color: #1a1d2e !important;
        color: #e2e8f0 !important;
        font-size: 13px !important;
        border: none !important;
      }
      .DateInput_input::placeholder { color: #64748b !important; }
      .DateInput_input__focused { border-bottom: 2px solid #818cf8 !important; }
      .DateRangePickerInput {
        background-color: #1a1d2e !important;
        border: 1px solid #252840 !important;
        border-radius: 8px !important;
        display: flex !important;
        align-items: center !important;
      }
      .DateRangePickerInput:hover { border-color: #818cf8 !important; }
      .DateRangePickerInput_arrow, .DateRangePickerInput_arrow_svg { color: #64748b !important; fill: #64748b !important; }
      .DateRangePicker_picker, .DayPicker, .DayPicker_transitionContainer,
      .CalendarMonthGrid, .CalendarMonth {
        background-color: #141624 !important;
        color: #e2e8f0 !important;
      }
      .CalendarMonth_caption { color: #e2e8f0 !important; font-size: 14px !important; font-weight: 600 !important; }
      .DayPickerNavigation_button {
        background-color: #1a1d2e !important;
        border: 1px solid #252840 !important;
        border-radius: 6px !important;
      }
      .DayPickerNavigation_button:hover { border-color: #818cf8 !important; }
      .DayPicker_weekHeader_li small { color: #64748b !important; font-size: 11px !important; font-weight: 600 !important; }
      .CalendarDay__default {
        background-color: #141624 !important;
        border-color: #252840 !important;
        color: #e2e8f0 !important;
      }
      .CalendarDay__default:hover {
        background-color: rgba(129,140,248,0.2) !important;
        border-color: #818cf8 !important;
        color: #818cf8 !important;
      }
      .CalendarDay__selected, .CalendarDay__selected:active, .CalendarDay__selected:hover {
        background-color: #818cf8 !important;
        border-color: #818cf8 !important;
        color: #fff !important;
        font-weight: 700 !important;
      }
      .CalendarDay__selected_span {
        background-color: rgba(129,140,248,0.2) !important;
        border-color: #252840 !important;
        color: #818cf8 !important;
      }
      .CalendarDay__hovered_span, .CalendarDay__hovered_span:hover {
        background-color: rgba(129,140,248,0.15) !important;
        color: #818cf8 !important;
      }
      .CalendarDay__blocked_out_of_range, .CalendarDay__blocked_out_of_range:hover {
        background-color: #141624 !important;
        color: #64748b !important;
        opacity: 0.4 !important;
      }
    </style>
  </head>
  <body>
    {%app_entry%}
    <footer>
      {%config%}
      {%scripts%}
      {%renderer%}
    </footer>
  </body>
</html>
"""

app.layout = html.Div([

    # Google Fonts
    html.Link(
        rel="stylesheet",
        href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap",
    ),


    # ── Header ──────────────────────────────────────────────────────────────
    html.Header([
        html.Div([
            html.Div([
                html.Div("\U0001f4ca", style={"fontSize": "30px", "marginRight": "14px", "lineHeight": "1"}),
                html.Div([
                    html.H1("Dashboard Financeiro", style={
                        "margin": "0", "fontSize": "17px",
                        "fontWeight": "700", "color": TEXT, "letterSpacing": "-0.02em",
                    }),
                    html.P("CIMMVI  \u00b7  AMVI", style={
                        "margin": "0", "fontSize": "12px", "color": TEXT_DIM, "fontWeight": "400",
                    }),
                ]),
            ], style={"display": "flex", "alignItems": "center"}),
            html.Div(id="header-etl", style={"fontSize": "12px", "color": TEXT_DIM, "textAlign": "right"}),
        ], style={
            "display": "flex", "justifyContent": "space-between", "alignItems": "center",
            "maxWidth": "1600px", "margin": "0 auto", "padding": "0 28px",
        }),
    ], style={
        "background": CARD, "borderBottom": f"1px solid {BORDER}",
        "padding": "14px 0", "position": "sticky", "top": "0", "zIndex": "100",
        "boxShadow": "0 4px 24px rgba(0,0,0,0.4)",
    }),

    # ── Conteúdo principal ───────────────────────────────────────────────────
    html.Main([

        # ════════════════════════════════════════════════════════════════════
        # HERO — Patrimônio total (todas as contas, sempre visível)
        # ════════════════════════════════════════════════════════════════════
        html.Div([

            # Saldo geral
            html.Div([
                html.Div("\U0001f3e6  Patrimônio Total — Todas as Contas", style={
                    "fontSize": "10px", "color": TEXT_DIM, "fontWeight": "700",
                    "textTransform": "uppercase", "letterSpacing": "0.1em",
                    "marginBottom": "10px",
                }),
                html.Div(id="saldo-geral", style={
                    "fontSize": "40px", "fontWeight": "800",
                    "color": SUCCESS, "fontVariantNumeric": "tabular-nums",
                    "letterSpacing": "-0.04em", "lineHeight": "1",
                }),
                html.Div("saldo consolidado de todas as contas", style={
                    "fontSize": "11px", "color": MUTED, "marginTop": "8px",
                }),
            ], style={"flex": "1", "minWidth": "260px"}),

            # Subtotais por entidade
            html.Div([
                html.Div([
                    html.Div([
                        html.Span("CIMMVI", style={
                            "fontSize": "10px", "color": TEXT_DIM, "fontWeight": "700",
                            "textTransform": "uppercase", "letterSpacing": "0.1em",
                        }),
                        html.Span(" \u00b7 Banco do Brasil + Caixa", style={
                            "fontSize": "10px", "color": MUTED,
                        }),
                    ], style={"marginBottom": "6px"}),
                    html.Div(id="saldo-cimmvi", style={
                        "fontSize": "22px", "fontWeight": "700", "color": PRIMARY,
                        "fontVariantNumeric": "tabular-nums",
                    }),
                ], style={
                    "background": "rgba(129,140,248,0.05)",
                    "border": f"1px solid rgba(129,140,248,0.2)",
                    "borderLeft": f"3px solid {PRIMARY}",
                    "borderRadius": "10px", "padding": "16px 20px",
                    "flex": "1", "minWidth": "200px",
                }),
                html.Div([
                    html.Div([
                        html.Span("AMVI", style={
                            "fontSize": "10px", "color": TEXT_DIM, "fontWeight": "700",
                            "textTransform": "uppercase", "letterSpacing": "0.1em",
                        }),
                        html.Span(" \u00b7 Banco do Brasil CC 439", style={
                            "fontSize": "10px", "color": MUTED,
                        }),
                    ], style={"marginBottom": "6px"}),
                    html.Div(id="saldo-amvi", style={
                        "fontSize": "22px", "fontWeight": "700", "color": INFO,
                        "fontVariantNumeric": "tabular-nums",
                    }),
                ], style={
                    "background": "rgba(56,189,248,0.05)",
                    "border": f"1px solid rgba(56,189,248,0.2)",
                    "borderLeft": f"3px solid {INFO}",
                    "borderRadius": "10px", "padding": "16px 20px",
                    "flex": "1", "minWidth": "200px",
                }),
            ], style={"display": "flex", "gap": "12px", "flex": "1.5", "flexWrap": "wrap"}),

        ], style={
            "display": "flex", "gap": "28px", "alignItems": "center",
            "background": f"linear-gradient(135deg, {CARD} 0%, {CARD2} 55%, {CARD} 100%)",
            "border": f"1px solid {BORDER}",
            "borderLeft": f"4px solid {SUCCESS}",
            "borderRadius": "16px",
            "padding": "28px 32px",
            "marginBottom": "20px",
            "flexWrap": "wrap",
            "boxShadow": "0 0 60px rgba(52,211,153,0.06)",
        }),

        # ════════════════════════════════════════════════════════════════════
        # Filtros
        # ════════════════════════════════════════════════════════════════════
        _card([
            html.Div([
                html.Div([
                    _label("Período"),
                    dcc.DatePickerRange(
                        id="filtro-data",
                        start_date=START_PADRAO,
                        end_date=END_PADRAO,
                        min_date_allowed=DATE_MIN,
                        max_date_allowed=DATE_MAX,
                        display_format="DD/MM/YYYY",
                        style={"fontFamily": FONT},
                    ),
                ]),
                html.Div([
                    _label("Conta"),
                    dcc.Dropdown(
                        id="filtro-conta",
                        options=_CONTAS,
                        value="",
                        clearable=False,
                        style=_DD_STYLE,
                    ),
                ], style={"flex": "1", "minWidth": "200px"}),
                html.Div([
                    _label("Entidade"),
                    dcc.Dropdown(
                        id="filtro-entidade",
                        options=_ENTIDADES,
                        value="",
                        clearable=False,
                        style=_DD_STYLE,
                    ),
                ], style={"flex": "0 1 160px", "minWidth": "140px"}),
            ], style={
                "display": "flex", "gap": "20px",
                "alignItems": "flex-end", "flexWrap": "wrap",
            }),
        ], extra={"marginBottom": "20px", "padding": "14px 20px"}),

        # ════════════════════════════════════════════════════════════════════
        # Tabs
        # ════════════════════════════════════════════════════════════════════
        dcc.Tabs(
            id="tabs-principal",
            value="painel",
            style={"borderBottom": f"1px solid {BORDER}"},
            content_style={
                "border": f"1px solid {BORDER}",
                "borderTop": "none",
                "borderRadius": "0 14px 14px 14px",
                "background": CARD,
                "padding": "24px",
            },
            children=[

                # ──────────────────────────────────────────────────────────
                # TAB 1 — Painel
                # ──────────────────────────────────────────────────────────
                dcc.Tab(
                    label="\U0001f3e0  Painel",
                    value="painel",
                    style=_TAB_STYLE,
                    selected_style=_SELECTED_TAB_STYLE,
                    children=[

                        # Saldo por conta (individual)
                        _section_title("Saldo por Conta"),
                        html.Div([

                            _card([
                                html.Div("CIMMVI \u00b7 Banco do Brasil", style={
                                    "fontSize": "10px", "color": TEXT_DIM, "fontWeight": "600",
                                    "textTransform": "uppercase", "letterSpacing": "0.07em",
                                    "marginBottom": "10px",
                                }),
                                html.Div(id="saldo-c1", style={
                                    "fontSize": "26px", "fontWeight": "700",
                                    "color": PRIMARY, "fontVariantNumeric": "tabular-nums",
                                }),
                                html.Div("Rateio Banco do Brasil", style={
                                    "fontSize": "11px", "color": MUTED, "marginTop": "6px",
                                }),
                            ], extra={"borderTop": f"3px solid {PRIMARY}", "flex": "1", "minWidth": "200px"}),

                            _card([
                                html.Div("CIMMVI \u00b7 Caixa Econômica", style={
                                    "fontSize": "10px", "color": TEXT_DIM, "fontWeight": "600",
                                    "textTransform": "uppercase", "letterSpacing": "0.07em",
                                    "marginBottom": "10px",
                                }),
                                html.Div(id="saldo-c2", style={
                                    "fontSize": "26px", "fontWeight": "700",
                                    "color": SECONDARY, "fontVariantNumeric": "tabular-nums",
                                }),
                                html.Div("Licenciamento Caixa", style={
                                    "fontSize": "11px", "color": MUTED, "marginTop": "6px",
                                }),
                            ], extra={"borderTop": f"3px solid {SECONDARY}", "flex": "1", "minWidth": "200px"}),

                            _card([
                                html.Div("AMVI \u00b7 Banco do Brasil", style={
                                    "fontSize": "10px", "color": TEXT_DIM, "fontWeight": "600",
                                    "textTransform": "uppercase", "letterSpacing": "0.07em",
                                    "marginBottom": "10px",
                                }),
                                html.Div(id="saldo-c3", style={
                                    "fontSize": "26px", "fontWeight": "700",
                                    "color": INFO, "fontVariantNumeric": "tabular-nums",
                                }),
                                html.Div("Conta Corrente 439", style={
                                    "fontSize": "11px", "color": MUTED, "marginTop": "6px",
                                }),
                            ], extra={"borderTop": f"3px solid {INFO}", "flex": "1", "minWidth": "200px"}),

                        ], style={"display": "flex", "gap": "16px", "marginBottom": "28px", "flexWrap": "wrap"}),

                        # KPIs (filtrados pelo período)
                        _section_title("Movimentação no Período"),
                        html.Div([
                            _kpi("kpi-entradas",      "Total de Entradas",    "\u2b06\ufe0f", SUCCESS,  "no período selecionado"),
                            _kpi("kpi-saidas",        "Total de Saídas",      "\u2b07\ufe0f", DANGER,   "no período selecionado"),
                            _kpi("kpi-liquido",       "Resultado Líquido",    "\u2696\ufe0f", WARNING,  "entradas \u2212 saídas"),
                            _kpi("kpi-aberto-saidas", "Saídas em Aberto",     "\U0001f4e4", DANGER,   "pendentes de pagamento"),
                            _kpi("kpi-aberto-ent",    "Entradas em Aberto",   "\U0001f4e5", SUCCESS,  "pendentes de recebimento"),
                            _kpi("kpi-aguardando",    "Aguardando Aprovação", "\U0001f514", WARNING,  "saídas em análise"),
                        ], style={
                            "display": "grid",
                            "gridTemplateColumns": "repeat(auto-fit, minmax(160px, 1fr))",
                            "gap": "16px",
                            "marginBottom": "28px",
                        }),

                        # Gráficos linha 1
                        html.Div([
                            _card([
                                _section_title("Evolução do Saldo Mensal"),
                                dcc.Graph(id="chart-saldo", config={"displayModeBar": False},
                                          style={"height": "300px"}),
                            ], extra={"flex": "2", "minWidth": "300px"}),
                            _card([
                                _section_title("Distribuição por Situação"),
                                dcc.Graph(id="chart-situacao", config={"displayModeBar": False},
                                          style={"height": "300px"}),
                            ], extra={"flex": "1", "minWidth": "260px"}),
                        ], style={"display": "flex", "gap": "16px", "marginBottom": "20px", "flexWrap": "wrap"}),

                        # Gráficos linha 2
                        _card([
                            _section_title("Entradas e Saídas Mensais"),
                            dcc.Graph(id="chart-mensal", config={"displayModeBar": False},
                                      style={"height": "300px"}),
                        ]),

                    ],
                ),

                # ──────────────────────────────────────────────────────────
                # TAB 2 — Análise
                # ──────────────────────────────────────────────────────────
                dcc.Tab(
                    label="\U0001f4c8  Análise",
                    value="analise",
                    style=_TAB_STYLE,
                    selected_style=_SELECTED_TAB_STYLE,
                    children=[

                        html.Div([
                            _card([
                                _section_title("Saídas por Categoria"),
                                dcc.Graph(id="chart-categoria", config={"displayModeBar": False},
                                          style={"height": "360px"}),
                            ], extra={"flex": "3", "minWidth": "300px"}),
                            _card([
                                _section_title("Saídas por Forma de Pagamento"),
                                dcc.Graph(id="chart-forma-pgto", config={"displayModeBar": False},
                                          style={"height": "360px"}),
                            ], extra={"flex": "2", "minWidth": "240px"}),
                        ], style={"display": "flex", "gap": "16px", "marginBottom": "20px", "flexWrap": "wrap"}),

                        _card([
                            _section_title("Top 10 Maiores Saídas Individuais"),
                            dcc.Graph(id="chart-top-saidas", config={"displayModeBar": False},
                                      style={"height": "380px"}),
                        ]),

                    ],
                ),

                # ──────────────────────────────────────────────────────────
                # TAB 3 — Lançamentos
                # ──────────────────────────────────────────────────────────
                dcc.Tab(
                    label="\U0001f4cb  Lançamentos",
                    value="lancamentos",
                    style=_TAB_STYLE,
                    selected_style=_SELECTED_TAB_STYLE,
                    children=[

                        _section_title("Lançamentos Detalhados — Apenas Movimentos"),
                        dash_table.DataTable(
                            id="tabela-lancamentos",
                            columns=[
                                {"name": "Data",         "id": "data_pagamento"},
                                {"name": "Conta",        "id": "conta"},
                                {"name": "Categoria",    "id": "categoria"},
                                {"name": "Descrição",    "id": "descricao"},
                                {"name": "NF / Doc",     "id": "nf_doc"},
                                {"name": "Situação",     "id": "situacao"},
                                {"name": "Forma Pgto.",  "id": "forma_pagamento"},
                                {"name": "Parcelas",     "id": "parc_info"},
                                {"name": "Entradas",     "id": "entradas",
                                 "type": "numeric", "format": {"specifier": ",.2f"}},
                                {"name": "Saídas",       "id": "saidas",
                                 "type": "numeric", "format": {"specifier": ",.2f"}},
                                {"name": "Saldo Acum.",  "id": "saldo_acumulado",
                                 "type": "numeric", "format": {"specifier": ",.2f"}},
                                {"name": "Obs.",         "id": "observacao"},
                            ],
                            data=[],
                            page_size=30,
                            page_action="native",
                            sort_action="native",
                            filter_action="native",
                            style_table={"overflowX": "auto"},
                            style_header=_TABLE_HEADER,
                            style_cell=_TABLE_CELL,
                            style_data_conditional=_TABLE_COND,
                            style_filter={
                                "backgroundColor": CARD2, "color": TEXT, "border": f"1px solid {BORDER}",
                            },
                        ),

                    ],
                ),

            ],
        ),

    ], style={"maxWidth": "1600px", "margin": "0 auto", "padding": "24px"}),

], style={
    "background": BG, "minHeight": "100vh",
    "fontFamily": FONT, "color": TEXT,
})


# ════════════════════════════════════════════════════════════════════════════
# Callbacks
# ════════════════════════════════════════════════════════════════════════════

def _normalizar(conta: str, entidade: str):
    """Converte '' → None (sem filtro)."""
    return (conta or None), (entidade or None)


@app.callback(
    # Header
    Output("header-etl",         "children"),
    # Hero — global, sempre visível
    Output("saldo-geral",        "children"),
    Output("saldo-cimmvi",       "children"),
    Output("saldo-amvi",         "children"),
    # Painel — saldo por conta
    Output("saldo-c1",           "children"),
    Output("saldo-c2",           "children"),
    Output("saldo-c3",           "children"),
    # KPIs
    Output("kpi-entradas",       "children"),
    Output("kpi-saidas",         "children"),
    Output("kpi-liquido",        "children"),
    Output("kpi-aberto-saidas",  "children"),
    Output("kpi-aberto-ent",     "children"),
    Output("kpi-aguardando",     "children"),
    # Gráficos — painel
    Output("chart-saldo",        "figure"),
    Output("chart-situacao",     "figure"),
    Output("chart-mensal",       "figure"),
    # Gráficos — análise
    Output("chart-categoria",    "figure"),
    Output("chart-forma-pgto",   "figure"),
    Output("chart-top-saidas",   "figure"),
    # Tabela
    Output("tabela-lancamentos", "data"),
    # Inputs
    Input("filtro-conta",        "value"),
    Input("filtro-entidade",     "value"),
    Input("filtro-data",         "start_date"),
    Input("filtro-data",         "end_date"),
)
def atualizar(conta_sel, entidade_sel, data_ini, data_fim):
    EMPTY = "—"

    if not _DB_READY:
        aviso = html.Span("\u26a0\ufe0f Execute o ETL para carregar os dados.", style={"color": WARNING})
        fig_v = _empty_fig("Banco não inicializado — execute o ETL primeiro.")
        return (aviso,
                EMPTY, EMPTY, EMPTY,
                EMPTY, EMPTY, EMPTY,
                EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY,
                fig_v, fig_v, fig_v, fig_v, fig_v, fig_v,
                [])

    conta, entidade = _normalizar(conta_sel, entidade_sel)

    # ── Info do ETL ──────────────────────────────────────────────────────
    try:
        uc = ultima_carga()
        if uc:
            ts = str(uc["iniciado_em"])[:16].replace("T", " ")
            header_etl = [
                html.Span("\u2705 ", style={"color": SUCCESS}),
                html.Span(f"Última carga: {ts}  \u00b7  "),
                html.Span(f"{uc['linhas_inseridas']} linhas inseridas", style={"color": TEXT_DIM}),
            ]
        else:
            header_etl = html.Span("Nenhuma carga registrada", style={"color": WARNING})
    except Exception:
        header_etl = EMPTY

    # ── Saldos ───────────────────────────────────────────────────────────
    try:
        _v1 = saldo_final_conta_1() or 0.0
        _v2 = saldo_final_conta_2() or 0.0
        _v3 = saldo_final_conta_3() or 0.0
        sg       = _brl(saldo_final_geral())
        sc1      = _brl(_v1)
        sc2      = _brl(_v2)
        sc3      = _brl(_v3)
        s_cimmvi = _brl(_v1 + _v2)
        s_amvi   = _brl(_v3)
    except Exception:
        sg = sc1 = sc2 = sc3 = s_cimmvi = s_amvi = EMPTY

    # ── KPIs ─────────────────────────────────────────────────────────────
    try:
        kpi_ent    = _brl(total_entradas(data_ini, data_fim, conta, entidade))
        kpi_sai    = _brl(total_saidas(data_ini, data_fim, conta, entidade))
        kpi_liq    = _brl(total_liquido(data_ini, data_fim, conta, entidade), show_sign=True)
        kpi_ab_sai = _brl(saidas_em_aberto(conta, entidade))
        kpi_ab_ent = _brl(entradas_em_aberto(conta, entidade))
        kpi_ag     = _brl(valor_aguardando_aprovacao(conta, entidade))
    except Exception:
        kpi_ent = kpi_sai = kpi_liq = kpi_ab_sai = kpi_ab_ent = kpi_ag = EMPTY

    # ── Gráfico 1: Saldo mensal ──────────────────────────────────────────
    try:
        df_s = evolucao_saldo_mensal(conta=conta, data_inicio=data_ini, data_fim=data_fim)
        if df_s.empty:
            fig_saldo = _empty_fig()
        else:
            fig_saldo = go.Figure()
            for nome_conta, grp in df_s.groupby("conta"):
                cor_linha, cor_fill = CONTA_ESTILOS.get(nome_conta, (PRIMARY, "rgba(129,140,248,0.08)"))
                grp = grp.sort_values("ano_mes")
                fig_saldo.add_trace(go.Scatter(
                    x=grp["ano_mes"], y=grp["saldo_acumulado"],
                    name=nome_conta.split(" - ")[-1],
                    mode="lines+markers",
                    line=dict(color=cor_linha, width=2.5),
                    marker=dict(size=5, color=cor_linha),
                    fill="tozeroy", fillcolor=cor_fill,
                    hovertemplate="<b>%{x}</b><br>Saldo: R$\u00a0%{y:,.2f}<extra></extra>",
                ))
            fig_saldo.update_layout(**_chart_layout(
                yaxis=dict(
                    tickprefix="R$\u00a0", tickformat=",.0f",
                    gridcolor=BORDER, linecolor=BORDER,
                    tickfont=dict(color=TEXT_DIM, size=11),
                ),
            ))
    except Exception as ex:
        fig_saldo = _empty_fig(f"Erro: {ex}")

    # ── Gráfico 2: Situação (donut) ──────────────────────────────────────
    try:
        df_sit = contagem_por_situacao(conta=conta, entidade=entidade, data_inicio=data_ini, data_fim=data_fim)
        if df_sit.empty:
            fig_sit = _empty_fig()
        else:
            cores = [SITUACAO_CORES.get(s, PRIMARY) for s in df_sit["situacao"]]
            fig_sit = go.Figure(go.Pie(
                labels=df_sit["situacao"],
                values=df_sit["total_saidas"],
                hole=0.54,
                marker=dict(colors=cores, line=dict(color=BG, width=2)),
                textinfo="percent",
                hovertemplate="<b>%{label}</b><br>R$\u00a0%{value:,.2f}  (%{percent})<extra></extra>",
            ))
            fig_sit.update_layout(**_chart_layout(
                margin=dict(l=12, r=12, t=12, b=12),
                legend=dict(
                    bgcolor="rgba(0,0,0,0)", orientation="v",
                    font=dict(color=TEXT_DIM, size=10),
                    yanchor="middle", y=0.5, xanchor="left", x=1.0,
                ),
                showlegend=True,
            ))
    except Exception as ex:
        fig_sit = _empty_fig(f"Erro: {ex}")

    # ── Gráfico 3: Entradas e Saídas mensais ─────────────────────────────
    try:
        df_m = entradas_saidas_mensais(conta=conta, entidade=entidade, data_inicio=data_ini, data_fim=data_fim)
        if df_m.empty:
            fig_mensal = _empty_fig()
        else:
            agg = df_m.groupby("ano_mes", as_index=False).agg(
                entradas=("entradas", "sum"), saidas=("saidas", "sum")
            ).sort_values("ano_mes")
            fig_mensal = go.Figure([
                go.Bar(
                    name="Entradas", x=agg["ano_mes"], y=agg["entradas"],
                    marker_color=SUCCESS, opacity=0.85,
                    hovertemplate="Entradas \u00b7 <b>%{x}</b><br>R$\u00a0%{y:,.2f}<extra></extra>",
                ),
                go.Bar(
                    name="Saídas", x=agg["ano_mes"], y=agg["saidas"],
                    marker_color=DANGER, opacity=0.85,
                    hovertemplate="Saídas \u00b7 <b>%{x}</b><br>R$\u00a0%{y:,.2f}<extra></extra>",
                ),
            ])
            fig_mensal.update_layout(**_chart_layout(
                barmode="group", bargap=0.2,
                yaxis=dict(
                    tickprefix="R$\u00a0", tickformat=",.0f",
                    gridcolor=BORDER, linecolor=BORDER,
                    tickfont=dict(color=TEXT_DIM, size=11),
                ),
            ))
    except Exception as ex:
        fig_mensal = _empty_fig(f"Erro: {ex}")

    # ── Gráfico 4: Saídas por Categoria ──────────────────────────────────
    try:
        df_cat = saidas_por_categoria(conta=conta, entidade=entidade, data_inicio=data_ini, data_fim=data_fim)
        df_cat = df_cat[df_cat["total_saidas"] > 0].head(12)
        if df_cat.empty:
            fig_cat = _empty_fig()
        else:
            df_cat = df_cat.sort_values("total_saidas", ascending=True)
            cores_cat = (PALETA * 4)[:len(df_cat)]
            fig_cat = go.Figure(go.Bar(
                x=df_cat["total_saidas"],
                y=df_cat["categoria"],
                orientation="h",
                marker_color=cores_cat,
                hovertemplate="<b>%{y}</b><br>R$\u00a0%{x:,.2f}<extra></extra>",
                text=df_cat["total_saidas"].apply(
                    lambda v: f"R$\u00a0{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
                ),
                textposition="outside",
                textfont=dict(color=TEXT_DIM, size=10),
            ))
            fig_cat.update_layout(**_chart_layout(
                margin=dict(l=12, r=110, t=20, b=12),
                xaxis=dict(visible=False, gridcolor=BORDER),
                yaxis=dict(tickfont=dict(color=TEXT_DIM, size=11), gridcolor=BORDER, linecolor=BORDER),
                showlegend=False,
                hovermode="y unified",
            ))
    except Exception as ex:
        fig_cat = _empty_fig(f"Erro: {ex}")

    # ── Gráfico 5: Forma de Pagamento ─────────────────────────────────────
    try:
        df_fp = saidas_por_forma_pagamento(conta=conta, entidade=entidade, data_inicio=data_ini, data_fim=data_fim)
        if df_fp.empty:
            fig_fp = _empty_fig()
        else:
            cores_fp = (PALETA * 4)[:len(df_fp)]
            fig_fp = go.Figure(go.Bar(
                x=df_fp["total_saidas"],
                y=df_fp["forma_pagamento"],
                orientation="h",
                marker_color=cores_fp,
                hovertemplate="<b>%{y}</b><br>R$\u00a0%{x:,.2f}<extra></extra>",
                text=df_fp["total_saidas"].apply(
                    lambda v: f"R$\u00a0{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
                ),
                textposition="outside",
                textfont=dict(color=TEXT_DIM, size=11),
            ))
            fig_fp.update_layout(**_chart_layout(
                margin=dict(l=12, r=100, t=20, b=12),
                xaxis=dict(visible=False, gridcolor=BORDER),
                yaxis=dict(
                    autorange="reversed",
                    tickfont=dict(color=TEXT_DIM, size=12),
                    gridcolor=BORDER, linecolor=BORDER,
                ),
                showlegend=False,
                hovermode="y unified",
            ))
    except Exception as ex:
        fig_fp = _empty_fig(f"Erro: {ex}")

    # ── Gráfico 6: Top 10 Maiores Saídas ─────────────────────────────────
    try:
        df_top = top_saidas(n=10, conta=conta, entidade=entidade, data_inicio=data_ini, data_fim=data_fim)
        if df_top.empty:
            fig_top = _empty_fig()
        else:
            df_top = df_top.sort_values("saidas", ascending=True)
            df_top["label"] = df_top.apply(
                lambda r: (str(r.get("descricao") or "—"))[:40].rstrip()
                + ("\u2026" if len(str(r.get("descricao") or "")) > 40 else ""),
                axis=1,
            )
            cores_top = [CONTA_ESTILOS.get(c, (DANGER, ""))[0] for c in df_top["conta"]]
            fig_top = go.Figure(go.Bar(
                x=df_top["saidas"],
                y=df_top["label"],
                orientation="h",
                marker_color=cores_top,
                hovertemplate="<b>%{y}</b><br>Saída: R$\u00a0%{x:,.2f}<extra></extra>",
                text=df_top["saidas"].apply(
                    lambda v: f"R$\u00a0{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
                ),
                textposition="outside",
                textfont=dict(color=TEXT_DIM, size=10),
            ))
            fig_top.update_layout(**_chart_layout(
                margin=dict(l=12, r=120, t=20, b=12),
                xaxis=dict(visible=False, gridcolor=BORDER),
                yaxis=dict(tickfont=dict(color=TEXT_DIM, size=11), gridcolor=BORDER, linecolor=BORDER),
                showlegend=False,
                hovermode="y unified",
            ))
    except Exception as ex:
        fig_top = _empty_fig(f"Erro: {ex}")

    # ── Tabela ────────────────────────────────────────────────────────────
    try:
        df_tab = lancamentos_detalhados(
            conta=conta, entidade=entidade,
            data_inicio=data_ini, data_fim=data_fim,
            tipo_lancamento="MOVIMENTO",
            limit=500,
        )
        if df_tab.empty:
            dados_tabela = []
        else:
            for col in ("entradas", "saidas", "saldo_acumulado"):
                if col in df_tab.columns:
                    df_tab[col] = df_tab[col].apply(
                        lambda v: round(float(v), 2) if pd.notna(v) else None
                    )
            if "data_pagamento" in df_tab.columns:
                df_tab["data_pagamento"] = df_tab["data_pagamento"].apply(
                    lambda v: str(v)[:10] if v else ""
                )
            # Formata parcelas: "3/12"
            if "parc_atual" in df_tab.columns and "parc_total" in df_tab.columns:
                def _fmt_parc(row):
                    pa, pt = row.get("parc_atual"), row.get("parc_total")
                    if pd.notna(pa) and pd.notna(pt) and pa > 0:
                        return f"{int(pa)}/{int(pt)}"
                    return ""
                df_tab["parc_info"] = df_tab.apply(_fmt_parc, axis=1)
            else:
                df_tab["parc_info"] = ""
            if "categoria" not in df_tab.columns:
                df_tab["categoria"] = None
            dados_tabela = df_tab.to_dict("records")
    except Exception:
        dados_tabela = []

    return (
        header_etl,
        sg, s_cimmvi, s_amvi,
        sc1, sc2, sc3,
        kpi_ent, kpi_sai, kpi_liq, kpi_ab_sai, kpi_ab_ent, kpi_ag,
        fig_saldo, fig_sit, fig_mensal,
        fig_cat, fig_fp, fig_top,
        dados_tabela,
    )


# ════════════════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app.run(debug=True, host="0.0.0.0", port=8050)




import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dash_table, dcc, html

logger = logging.getLogger(__name__)

# ── Importa queries com fallback caso o banco ainda não exista ───────────────
try:
    from dashboard.queries import (
        contagem_por_situacao,
        contas_disponiveis,
        entidades_disponiveis,
        entradas_saidas_mensais,
        evolucao_saldo_mensal,
        lancamentos_detalhados,
        periodo_disponivel,
        saldo_final_conta_1,
        saldo_final_conta_2,
        saldo_final_conta_3,
        saldo_final_geral,
        saidas_por_forma_pagamento,
        total_entradas,
        total_liquido,
        total_saidas,
        ultima_carga,
        valor_aguardando_aprovacao,
        saidas_em_aberto,
        entradas_em_aberto,
    )
    _DB_READY = True
except Exception as _e:
    logger.warning("Banco não disponível na inicialização: %s", _e)
    _DB_READY = False


# ════════════════════════════════════════════════════════════════════════════
# Design tokens
# ════════════════════════════════════════════════════════════════════════════
BG        = "#0d0f1a"
CARD      = "#141624"
CARD2     = "#1a1d2e"
BORDER    = "#252840"
PRIMARY   = "#818cf8"   # indigo-400
SECONDARY = "#a78bfa"   # violet-400
SUCCESS   = "#34d399"   # emerald-400
DANGER    = "#f87171"   # red-400
WARNING   = "#fbbf24"   # amber-400
INFO      = "#38bdf8"   # sky-400
MUTED     = "#64748b"   # slate-500
TEXT      = "#e2e8f0"   # slate-200
TEXT_DIM  = "#94a3b8"   # slate-400
FONT      = "Inter, system-ui, -apple-system, sans-serif"

# Cores de linha e área de preenchimento por conta
CONTA_ESTILOS = {
    "CIMMVI - Rateio Banco do Brasil":   (PRIMARY,   "rgba(129,140,248,0.08)"),
    "CIMMVI - Licenciamento Caixa":      (SECONDARY, "rgba(167,139,250,0.08)"),
    "AMVI - Banco do Brasil - CC 439":   (INFO,      "rgba(56,189,248,0.08)"),
}

SITUACAO_CORES = {
    "Pago":                                                       SUCCESS,
    "Em aberto":                                                  DANGER,
    "Aguardando Aprovação":                                       WARNING,
    "Aprovado - Aguardando Pagamento":                            INFO,
    "Pagamento Realizado - Aguardando autorizacao Margarete":     MUTED,
    "Nao informado":                                              MUTED,
}

PALETA = [PRIMARY, SECONDARY, INFO, SUCCESS, WARNING, DANGER]
ICON_BG = {
    SUCCESS:   "rgba(52,211,153,0.15)",
    DANGER:    "rgba(248,113,113,0.15)",
    WARNING:   "rgba(251,191,36,0.15)",
    PRIMARY:   "rgba(129,140,248,0.15)",
    INFO:      "rgba(56,189,248,0.15)",
}


# ════════════════════════════════════════════════════════════════════════════
# Helpers visuais
# ════════════════════════════════════════════════════════════════════════════

def _brl(value, show_sign: bool = False) -> str:
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


def _chart_layout(**kwargs) -> dict:
    """Retorna o dict de layout base para os gráficos Plotly."""
    base = dict(
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font=dict(family=FONT, color=TEXT, size=12),
        margin=dict(l=12, r=12, t=36, b=12),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=BORDER,
            font=dict(color=TEXT_DIM, size=11),
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
        ),
        xaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=TEXT_DIM, size=11)),
        yaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=TEXT_DIM, size=11)),
        colorway=PALETA,
        hovermode="x unified",
    )
    base.update(kwargs)
    return base


def _empty_fig(msg: str = "Sem dados para exibir") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        annotations=[dict(
            text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(color=MUTED, size=13, family=FONT),
        )],
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=12, r=12, t=12, b=12),
    )
    return fig


def _card(children, extra: dict | None = None, **kwargs) -> html.Div:
    style = {
        "background": CARD,
        "border": f"1px solid {BORDER}",
        "borderRadius": "14px",
        "padding": "20px",
    }
    if extra:
        style.update(extra)
    return html.Div(children, style=style, **kwargs)


def _label(text: str) -> html.Div:
    return html.Div(text, style={
        "fontSize": "11px", "color": TEXT_DIM, "fontWeight": "600",
        "textTransform": "uppercase", "letterSpacing": "0.06em",
        "marginBottom": "6px",
    })


def _section(title: str) -> html.Div:
    return html.Div([
        html.Span(title, style={
            "fontSize": "13px", "fontWeight": "600",
            "color": TEXT, "textTransform": "uppercase", "letterSpacing": "0.07em",
        }),
        html.Hr(style={"borderColor": BORDER, "margin": "8px 0 16px 0"}),
    ])


def _kpi(output_id: str, label: str, icon: str, color: str = PRIMARY) -> html.Div:
    return _card([
        html.Div([
            html.Span(icon, style={
                "fontSize": "20px",
                "background": ICON_BG.get(color, ICON_BG[PRIMARY]),
                "borderRadius": "10px",
                "padding": "7px 10px",
            }),
        ], style={"marginBottom": "14px"}),
        html.Div(label, style={
            "fontSize": "11px", "color": TEXT_DIM, "fontWeight": "600",
            "textTransform": "uppercase", "letterSpacing": "0.06em",
            "marginBottom": "6px",
        }),
        html.Div(id=output_id, style={
            "fontSize": "22px", "fontWeight": "700",
            "color": color, "fontVariantNumeric": "tabular-nums",
            "letterSpacing": "-0.02em",
        }),
    ])


# ════════════════════════════════════════════════════════════════════════════
# Valores iniciais (datas e opções dos dropdowns)
# ════════════════════════════════════════════════════════════════════════════
_hoje = str(date.today())
_ano_inicio = str(date.today().replace(month=1, day=1))

try:
    _p = periodo_disponivel() if _DB_READY else {}
    DATE_MIN     = _p.get("data_min") or _ano_inicio
    DATE_MAX     = _p.get("data_max") or _hoje
    START_PADRAO = DATE_MIN
    END_PADRAO   = DATE_MAX
except Exception:
    DATE_MIN = START_PADRAO = _ano_inicio
    DATE_MAX = END_PADRAO   = _hoje

try:
    _CONTAS    = [{"label": "Todas as contas", "value": ""}] + [
        {"label": c, "value": c} for c in (contas_disponiveis() if _DB_READY else [])
    ]
    _ENTIDADES = [{"label": "Todas as entidades", "value": ""}] + [
        {"label": e, "value": e} for e in (entidades_disponiveis() if _DB_READY else [])
    ]
except Exception:
    _CONTAS    = [{"label": "Todas as contas", "value": ""}]
    _ENTIDADES = [{"label": "Todas as entidades", "value": ""}]


# ════════════════════════════════════════════════════════════════════════════
# Estilos reutilizáveis
# ════════════════════════════════════════════════════════════════════════════
_DD_STYLE = {
    "backgroundColor": CARD2,
    "border": f"1px solid {BORDER}",
    "borderRadius": "8px",
    "color": TEXT,
    "fontSize": "13px",
}

_TABLE_HEADER = {
    "backgroundColor": CARD2, "color": TEXT_DIM,
    "fontWeight": "600", "fontSize": "11px",
    "textTransform": "uppercase", "letterSpacing": "0.05em",
    "border": f"1px solid {BORDER}", "padding": "10px 12px",
    "fontFamily": FONT,
}

_TABLE_CELL = {
    "backgroundColor": CARD, "color": TEXT,
    "fontSize": "13px", "border": f"1px solid {BORDER}",
    "padding": "8px 12px", "fontFamily": FONT,
    "textOverflow": "ellipsis", "overflow": "hidden", "maxWidth": "240px",
}

_TABLE_COND = [
    {"if": {"row_index": "odd"}, "backgroundColor": CARD2},
    {"if": {"filter_query": '{situacao} = "Em aberto"'},      "color": DANGER, "fontWeight": "600"},
    {"if": {"filter_query": '{situacao} = "Pago"'},           "color": SUCCESS},
    {"if": {"filter_query": '{situacao} = "Aguardando Aprovação"'}, "color": WARNING},
    {"if": {"column_id": "entradas"},  "color": SUCCESS},
    {"if": {"column_id": "saidas"},    "color": DANGER},
]


# ════════════════════════════════════════════════════════════════════════════
# App e layout
# ════════════════════════════════════════════════════════════════════════════
app = Dash(
    __name__,
    title="Dashboard CIMMVI / AMVI",
    update_title=None,
    suppress_callback_exceptions=True,
)

app.layout = html.Div([

    # Google Fonts
    html.Link(
        rel="stylesheet",
        href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap",
    ),

    # ── Header ──────────────────────────────────────────────────────────────
    html.Header([
        html.Div([
            # Logo + título
            html.Div([
                html.Div("📊", style={"fontSize": "32px", "marginRight": "14px", "lineHeight": "1"}),
                html.Div([
                    html.H1("Dashboard Financeiro", style={
                        "margin": "0", "fontSize": "18px",
                        "fontWeight": "700", "color": TEXT, "letterSpacing": "-0.02em",
                    }),
                    html.P("CIMMVI  ·  AMVI", style={
                        "margin": "0", "fontSize": "12px", "color": TEXT_DIM, "fontWeight": "400",
                    }),
                ]),
            ], style={"display": "flex", "alignItems": "center"}),

            # Info última carga
            html.Div(id="header-etl", style={"fontSize": "12px", "color": TEXT_DIM, "textAlign": "right"}),
        ], style={
            "display": "flex", "justifyContent": "space-between", "alignItems": "center",
            "maxWidth": "1600px", "margin": "0 auto", "padding": "0 28px",
        }),
    ], style={
        "background": CARD, "borderBottom": f"1px solid {BORDER}",
        "padding": "14px 0", "position": "sticky", "top": "0", "zIndex": "100",
        "boxShadow": "0 4px 24px rgba(0,0,0,0.4)",
    }),

    # ── Conteúdo principal ───────────────────────────────────────────────────
    html.Main([

        # ── Barra de filtros ────────────────────────────────────────────────
        _card([
            html.Div([

                html.Div([
                    _label("Período"),
                    dcc.DatePickerRange(
                        id="filtro-data",
                        start_date=START_PADRAO,
                        end_date=END_PADRAO,
                        min_date_allowed=DATE_MIN,
                        max_date_allowed=DATE_MAX,
                        display_format="DD/MM/YYYY",
                        style={"fontFamily": FONT},
                    ),
                ]),

                html.Div([
                    _label("Conta"),
                    dcc.Dropdown(
                        id="filtro-conta",
                        options=_CONTAS,
                        value="",
                        clearable=False,
                        style=_DD_STYLE,
                    ),
                ], style={"flex": "1", "minWidth": "200px"}),

                html.Div([
                    _label("Entidade"),
                    dcc.Dropdown(
                        id="filtro-entidade",
                        options=_ENTIDADES,
                        value="",
                        clearable=False,
                        style=_DD_STYLE,
                    ),
                ], style={"flex": "0 1 160px", "minWidth": "140px"}),

            ], style={
                "display": "flex", "gap": "20px",
                "alignItems": "flex-end", "flexWrap": "wrap",
            }),
        ], extra={"marginBottom": "20px", "padding": "14px 20px"}),

        # ── Saldos por conta ────────────────────────────────────────────────
        html.Div([

            _card([
                html.Div("💰  Saldo Total Geral", style={
                    "fontSize": "11px", "color": TEXT_DIM, "fontWeight": "600",
                    "textTransform": "uppercase", "letterSpacing": "0.06em", "marginBottom": "10px",
                }),
                html.Div(id="saldo-geral", style={
                    "fontSize": "30px", "fontWeight": "800",
                    "color": SUCCESS, "fontVariantNumeric": "tabular-nums", "letterSpacing": "-0.03em",
                }),
            ], extra={"borderTop": f"3px solid {SUCCESS}", "flex": "1", "minWidth": "200px"}),

            _card([
                html.Div("🏦  CIMMVI · Banco do Brasil", style={
                    "fontSize": "11px", "color": TEXT_DIM, "fontWeight": "600",
                    "textTransform": "uppercase", "letterSpacing": "0.06em", "marginBottom": "10px",
                }),
                html.Div(id="saldo-c1", style={
                    "fontSize": "22px", "fontWeight": "700",
                    "color": PRIMARY, "fontVariantNumeric": "tabular-nums",
                }),
            ], extra={"borderTop": f"3px solid {PRIMARY}", "flex": "1", "minWidth": "200px"}),

            _card([
                html.Div("🏦  CIMMVI · Licenciamento Caixa", style={
                    "fontSize": "11px", "color": TEXT_DIM, "fontWeight": "600",
                    "textTransform": "uppercase", "letterSpacing": "0.06em", "marginBottom": "10px",
                }),
                html.Div(id="saldo-c2", style={
                    "fontSize": "22px", "fontWeight": "700",
                    "color": SECONDARY, "fontVariantNumeric": "tabular-nums",
                }),
            ], extra={"borderTop": f"3px solid {SECONDARY}", "flex": "1", "minWidth": "200px"}),

            _card([
                html.Div("🏦  AMVI · Banco do Brasil CC 439", style={
                    "fontSize": "11px", "color": TEXT_DIM, "fontWeight": "600",
                    "textTransform": "uppercase", "letterSpacing": "0.06em", "marginBottom": "10px",
                }),
                html.Div(id="saldo-c3", style={
                    "fontSize": "22px", "fontWeight": "700",
                    "color": INFO, "fontVariantNumeric": "tabular-nums",
                }),
            ], extra={"borderTop": f"3px solid {INFO}", "flex": "1", "minWidth": "200px"}),

        ], style={"display": "flex", "gap": "16px", "marginBottom": "20px", "flexWrap": "wrap"}),

        # ── KPIs ────────────────────────────────────────────────────────────
        html.Div([
            _kpi("kpi-entradas",      "Entradas no período",      "⬆️", color=SUCCESS),
            _kpi("kpi-saidas",        "Saídas no período",        "⬇️", color=DANGER),
            _kpi("kpi-liquido",       "Resultado líquido",        "⚖️", color=WARNING),
            _kpi("kpi-aberto-saidas", "Saídas em aberto",         "📤", color=DANGER),
            _kpi("kpi-aberto-ent",   "Entradas em aberto",       "📥", color=SUCCESS),
            _kpi("kpi-aguardando",    "Aguardando aprovação",     "🔔", color=WARNING),
        ], style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fit, minmax(170px, 1fr))",
            "gap": "16px",
            "marginBottom": "20px",
        }),

        # ── Charts linha 1: Saldo mensal + Situação ─────────────────────────
        html.Div([

            _card([
                _section("Evolução do Saldo Mensal"),
                dcc.Graph(id="chart-saldo", config={"displayModeBar": False},
                          style={"height": "300px"}),
            ], extra={"flex": "2", "minWidth": "300px"}),

            _card([
                _section("Situação dos Lançamentos"),
                dcc.Graph(id="chart-situacao", config={"displayModeBar": False},
                          style={"height": "300px"}),
            ], extra={"flex": "1", "minWidth": "260px"}),

        ], style={"display": "flex", "gap": "16px", "marginBottom": "20px", "flexWrap": "wrap"}),

        # ── Charts linha 2: Entradas/Saídas + Forma pgto ────────────────────
        html.Div([

            _card([
                _section("Entradas e Saídas Mensais"),
                dcc.Graph(id="chart-mensal", config={"displayModeBar": False},
                          style={"height": "300px"}),
            ], extra={"flex": "3", "minWidth": "300px"}),

            _card([
                _section("Saídas por Forma de Pagamento"),
                dcc.Graph(id="chart-forma-pgto", config={"displayModeBar": False},
                          style={"height": "300px"}),
            ], extra={"flex": "2", "minWidth": "260px"}),

        ], style={"display": "flex", "gap": "16px", "marginBottom": "20px", "flexWrap": "wrap"}),

        # ── Tabela de lançamentos ────────────────────────────────────────────
        _card([
            _section("Lançamentos Detalhados (apenas movimentos)"),
            dash_table.DataTable(
                id="tabela-lancamentos",
                columns=[
                    {"name": "Data",         "id": "data_pagamento"},
                    {"name": "Conta",        "id": "conta"},
                    {"name": "Descrição",    "id": "descricao"},
                    {"name": "NF / Doc",     "id": "nf_doc"},
                    {"name": "Situação",     "id": "situacao"},
                    {"name": "Forma Pgto.",  "id": "forma_pagamento"},
                    {"name": "Entradas",     "id": "entradas",        "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Saídas",       "id": "saidas",          "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Saldo Acum.",  "id": "saldo_acumulado", "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Obs.",         "id": "observacao"},
                ],
                data=[],
                page_size=25,
                page_action="native",
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto"},
                style_header=_TABLE_HEADER,
                style_cell=_TABLE_CELL,
                style_data_conditional=_TABLE_COND,
                style_filter={
                    "backgroundColor": CARD2, "color": TEXT, "border": f"1px solid {BORDER}",
                },
            ),
        ]),

    ], style={"maxWidth": "1600px", "margin": "0 auto", "padding": "24px"}),

], style={
    "background": BG, "minHeight": "100vh",
    "fontFamily": FONT, "color": TEXT,
})


# ════════════════════════════════════════════════════════════════════════════
# Callbacks
# ════════════════════════════════════════════════════════════════════════════

def _normalizar(conta: str, entidade: str):
    """Converte '' → None (sem filtro)."""
    return (conta or None), (entidade or None)


@app.callback(
    # Header
    Output("header-etl",    "children"),
    # Saldos
    Output("saldo-geral",   "children"),
    Output("saldo-c1",      "children"),
    Output("saldo-c2",      "children"),
    Output("saldo-c3",      "children"),
    # KPIs
    Output("kpi-entradas",      "children"),
    Output("kpi-saidas",        "children"),
    Output("kpi-liquido",       "children"),
    Output("kpi-aberto-saidas", "children"),
    Output("kpi-aberto-ent",   "children"),
    Output("kpi-aguardando",    "children"),
    # Gráficos
    Output("chart-saldo",       "figure"),
    Output("chart-situacao",    "figure"),
    Output("chart-mensal",      "figure"),
    Output("chart-forma-pgto",  "figure"),
    # Tabela
    Output("tabela-lancamentos", "data"),
    # Inputs
    Input("filtro-conta",    "value"),
    Input("filtro-entidade", "value"),
    Input("filtro-data",     "start_date"),
    Input("filtro-data",     "end_date"),
)
def atualizar(conta_sel, entidade_sel, data_ini, data_fim):

    # ── Banco indisponível ───────────────────────────────────────────────
    if not _DB_READY:
        aviso = html.Span("⚠️ Execute o ETL para carregar os dados.", style={"color": WARNING})
        fig_vazio = _empty_fig("Banco não inicializado — execute o ETL primeiro.")
        return (aviso, "—", "—", "—", "—", "—", "—", "—", "—", "—", "—",
                fig_vazio, fig_vazio, fig_vazio, fig_vazio, [])

    conta, entidade = _normalizar(conta_sel, entidade_sel)

    # ── Info do ETL ──────────────────────────────────────────────────────
    try:
        uc = ultima_carga()
        if uc:
            ts = str(uc["iniciado_em"])[:16].replace("T", " ")
            header_etl = [
                html.Span("✅ ", style={"color": SUCCESS}),
                html.Span(f"Última carga: {ts}  ·  "),
                html.Span(f"{uc['linhas_inseridas']} linhas inseridas", style={"color": TEXT_DIM}),
            ]
        else:
            header_etl = html.Span("Nenhuma carga registrada", style={"color": WARNING})
    except Exception:
        header_etl = "—"

    # ── Saldos ───────────────────────────────────────────────────────────
    try:
        sg  = _brl(saldo_final_geral())
        sc1 = _brl(saldo_final_conta_1())
        sc2 = _brl(saldo_final_conta_2())
        sc3 = _brl(saldo_final_conta_3())
    except Exception:
        sg = sc1 = sc2 = sc3 = "—"

    # ── KPIs ─────────────────────────────────────────────────────────────
    try:
        kpi_ent    = _brl(total_entradas(data_ini, data_fim, conta, entidade))
        kpi_sai    = _brl(total_saidas(data_ini, data_fim, conta, entidade))
        kpi_liq    = _brl(total_liquido(data_ini, data_fim, conta, entidade), show_sign=True)
        kpi_ab_sai = _brl(saidas_em_aberto(conta, entidade))
        kpi_ab_ent = _brl(entradas_em_aberto(conta, entidade))
        kpi_ag     = _brl(valor_aguardando_aprovacao(conta, entidade))
    except Exception:
        kpi_ent = kpi_sai = kpi_liq = kpi_ab_sai = kpi_ab_ent = kpi_ag = "—"

    # ── Gráfico 1: Saldo mensal ──────────────────────────────────────────
    try:
        df_s = evolucao_saldo_mensal(conta=conta, data_inicio=data_ini, data_fim=data_fim)
        if df_s.empty:
            fig_saldo = _empty_fig()
        else:
            fig_saldo = go.Figure()
            for nome_conta, grp in df_s.groupby("conta"):
                cor_linha, cor_fill = CONTA_ESTILOS.get(nome_conta, (PRIMARY, "rgba(129,140,248,0.08)"))
                grp = grp.sort_values("ano_mes")
                fig_saldo.add_trace(go.Scatter(
                    x=grp["ano_mes"], y=grp["saldo_acumulado"],
                    name=nome_conta.split(" - ")[-1],
                    mode="lines+markers",
                    line=dict(color=cor_linha, width=2.5),
                    marker=dict(size=5, color=cor_linha),
                    fill="tozeroy", fillcolor=cor_fill,
                    hovertemplate="<b>%{x}</b><br>Saldo: R$\u00a0%{y:,.2f}<extra></extra>",
                ))
            fig_saldo.update_layout(**_chart_layout(
                yaxis=dict(
                    tickprefix="R$\u00a0", tickformat=",.0f",
                    gridcolor=BORDER, linecolor=BORDER,
                    tickfont=dict(color=TEXT_DIM, size=11),
                ),
            ))
    except Exception as ex:
        fig_saldo = _empty_fig(f"Erro: {ex}")

    # ── Gráfico 2: Situação dos lançamentos (donut) ──────────────────────
    try:
        df_sit = contagem_por_situacao(conta=conta, entidade=entidade, data_inicio=data_ini, data_fim=data_fim)
        if df_sit.empty:
            fig_sit = _empty_fig()
        else:
            cores = [SITUACAO_CORES.get(s, PRIMARY) for s in df_sit["situacao"]]
            fig_sit = go.Figure(go.Pie(
                labels=df_sit["situacao"],
                values=df_sit["total_saidas"],
                hole=0.54,
                marker=dict(colors=cores, line=dict(color=BG, width=2)),
                textinfo="percent",
                hovertemplate="<b>%{label}</b><br>R$\u00a0%{value:,.2f}  (%{percent})<extra></extra>",
            ))
            fig_sit.update_layout(**_chart_layout(
                margin=dict(l=12, r=12, t=12, b=12),
                legend=dict(
                    bgcolor="rgba(0,0,0,0)", orientation="v",
                    font=dict(color=TEXT_DIM, size=10),
                    yanchor="middle", y=0.5, xanchor="left", x=1.0,
                ),
                showlegend=True,
            ))
    except Exception as ex:
        fig_sit = _empty_fig(f"Erro: {ex}")

    # ── Gráfico 3: Entradas e Saídas mensais (barras) ────────────────────
    try:
        df_m = entradas_saidas_mensais(conta=conta, entidade=entidade, data_inicio=data_ini, data_fim=data_fim)
        if df_m.empty:
            fig_mensal = _empty_fig()
        else:
            agg = df_m.groupby("ano_mes", as_index=False).agg(
                entradas=("entradas", "sum"), saidas=("saidas", "sum")
            ).sort_values("ano_mes")
            fig_mensal = go.Figure([
                go.Bar(
                    name="Entradas", x=agg["ano_mes"], y=agg["entradas"],
                    marker_color=SUCCESS, opacity=0.85,
                    hovertemplate="Entradas · <b>%{x}</b><br>R$\u00a0%{y:,.2f}<extra></extra>",
                ),
                go.Bar(
                    name="Saídas", x=agg["ano_mes"], y=agg["saidas"],
                    marker_color=DANGER, opacity=0.85,
                    hovertemplate="Saídas · <b>%{x}</b><br>R$\u00a0%{y:,.2f}<extra></extra>",
                ),
            ])
            fig_mensal.update_layout(**_chart_layout(
                barmode="group", bargap=0.2,
                yaxis=dict(
                    tickprefix="R$\u00a0", tickformat=",.0f",
                    gridcolor=BORDER, linecolor=BORDER,
                    tickfont=dict(color=TEXT_DIM, size=11),
                ),
            ))
    except Exception as ex:
        fig_mensal = _empty_fig(f"Erro: {ex}")

    # ── Gráfico 4: Forma de pagamento (barras horizontais) ───────────────
    try:
        df_fp = saidas_por_forma_pagamento(conta=conta, entidade=entidade, data_inicio=data_ini, data_fim=data_fim)
        if df_fp.empty:
            fig_fp = _empty_fig()
        else:
            cores = (PALETA * 4)[:len(df_fp)]
            fig_fp = go.Figure(go.Bar(
                x=df_fp["total_saidas"],
                y=df_fp["forma_pagamento"],
                orientation="h",
                marker_color=cores,
                hovertemplate="<b>%{y}</b><br>R$\u00a0%{x:,.2f}<extra></extra>",
                text=df_fp["total_saidas"].apply(
                    lambda v: f"R$\u00a0{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
                ),
                textposition="outside",
                textfont=dict(color=TEXT_DIM, size=11),
            ))
            fig_fp.update_layout(**_chart_layout(
                margin=dict(l=12, r=90, t=20, b=12),
                xaxis=dict(visible=False, gridcolor=BORDER),
                yaxis=dict(
                    autorange="reversed",
                    tickfont=dict(color=TEXT_DIM, size=12),
                    gridcolor=BORDER, linecolor=BORDER,
                ),
                showlegend=False,
                hovermode="y unified",
            ))
    except Exception as ex:
        fig_fp = _empty_fig(f"Erro: {ex}")

    # ── Tabela de lançamentos ────────────────────────────────────────────
    try:
        df_tab = lancamentos_detalhados(
            conta=conta, entidade=entidade,
            data_inicio=data_ini, data_fim=data_fim,
            tipo_lancamento="MOVIMENTO",
            limit=500,
        )
        if df_tab.empty:
            dados_tabela = []
        else:
            for col in ("entradas", "saidas", "saldo_acumulado"):
                if col in df_tab.columns:
                    df_tab[col] = df_tab[col].apply(
                        lambda v: round(float(v), 2) if pd.notna(v) else None
                    )
            if "data_pagamento" in df_tab.columns:
                df_tab["data_pagamento"] = df_tab["data_pagamento"].apply(
                    lambda v: str(v)[:10] if v else ""
                )
            dados_tabela = df_tab.to_dict("records")
    except Exception:
        dados_tabela = []

    return (
        header_etl,
        sg, sc1, sc2, sc3,
        kpi_ent, kpi_sai, kpi_liq, kpi_ab_sai, kpi_ab_ent, kpi_ag,
        fig_saldo, fig_sit, fig_mensal, fig_fp,
        dados_tabela,
    )


# ════════════════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app.run(debug=True, host="0.0.0.0", port=8050)
