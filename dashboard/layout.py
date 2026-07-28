"""Layout principal do dashboard."""

from dashboard.config import DANGER
from datetime import date

from dash import dash_table, dcc, html

from dashboard.components import card, kpi, label, section_title
from dashboard.config import (
    BG, BORDER, CARD, CARD2, FONT, INFO, MUTED,
    PRIMARY, SECONDARY, SUCCESS, TEXT, TEXT_DIM, WARNING,
)

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
    {"if": {"filter_query": '{situacao} = "Em aberto"'},            "color": "#f87171", "fontWeight": "600"},
    {"if": {"filter_query": '{situacao} = "Pago"'},                 "color": "#34d399"},
    {"if": {"filter_query": '{situacao} = "Aguardando Aprovação"'}, "color": "#fbbf24"},
    {"if": {"column_id": "entradas"},        "color": "#34d399"},
    {"if": {"column_id": "saidas"},          "color": "#f87171"},
    {"if": {"column_id": "saldo_acumulado"}, "color": "#38bdf8", "fontWeight": "600"},
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
# Valores iniciais (datas e opções dos dropdowns)
# ════════════════════════════════════════════════════════════════════════════
_hoje = str(date.today())
_ano_inicio = str(date.today().replace(month=1, day=1))

try:
    from dashboard.queries import (
        contas_disponiveis, entidades_disponiveis, periodo_disponivel,
    )
    _DB_READY = True
except Exception:
    _DB_READY = False

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
# Blocos do layout
# ════════════════════════════════════════════════════════════════════════════

def _header() -> html.Header:
    return html.Header([
        html.Div([
            html.Div([
                html.Div("\U0001f4ca", style={"fontSize": "30px", "marginRight": "14px", "lineHeight": "1"}),
                html.Div([
                    html.H1("Dashboard CIMMVI-AMVI", style={
                        "margin": "0", "fontSize": "50px",
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
    })


def _hero() -> html.Div:
    """Patrimônio total — sempre visível."""
    return html.Div([

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

        html.Div([
            html.Div([
                html.Div([
                    html.Span("CIMMVI", style={
                        "fontSize": "10px", "color": TEXT_DIM, "fontWeight": "700",
                        "textTransform": "uppercase", "letterSpacing": "0.1em",
                    }),
                    html.Span(" \u00b7 Banco do Brasil + Caixa", style={"fontSize": "10px", "color": MUTED}),
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
                    html.Span(" \u00b7 Banco do Brasil CC 439", style={"fontSize": "10px", "color": MUTED}),
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
    })


def _filtros() -> html.Div:
    return card([
        html.Div([
            html.Div([
                label("Período"),
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
                label("Conta"),
                dcc.Dropdown(
                    id="filtro-conta",
                    options=_CONTAS,
                    value="",
                    clearable=False,
                    style=_DD_STYLE,
                ),
            ], style={"flex": "1", "minWidth": "200px"}),
            html.Div([
                label("Entidade"),
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
    ], extra={"marginBottom": "20px", "padding": "14px 20px"})


def _tab_painel() -> dcc.Tab:
    return dcc.Tab(
        label="\U0001f3e0  Painel",
        value="painel",
        style=_TAB_STYLE,
        selected_style=_SELECTED_TAB_STYLE,
        children=[

            # Saldo por conta (individual)
            section_title("Saldo por Conta"),
            html.Div([
                card([
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

                card([
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

                card([
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

            # KPIs
            section_title("Movimentação no Período"),
            html.Div([
                kpi("kpi-entradas",      "Total de Entradas",    "\u2b06\ufe0f", SUCCESS,  "no período selecionado"),
                kpi("kpi-saidas",        "Total de Saídas",      "\u2b07\ufe0f", DANGER,   "no período selecionado"),
                kpi("kpi-liquido",       "Resultado Líquido",    "\u2696\ufe0f", WARNING,  "entradas \u2212 saídas"),
                kpi("kpi-aberto-saidas", "Saídas em Aberto",     "\U0001f4e4", DANGER,   "pendentes de pagamento"),
                kpi("kpi-aberto-ent",    "Entradas em Aberto",   "\U0001f4e5", SUCCESS,  "pendentes de recebimento"),
                kpi("kpi-aguardando",    "Aguardando Aprovação", "\U0001f514", WARNING,  "saídas em análise"),
            ], style={
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fit, minmax(160px, 1fr))",
                "gap": "16px",
                "marginBottom": "28px",
            }),

            # Gráficos linha 1
            html.Div([
                card([
                    section_title("Evolução do Saldo Mensal"),
                    dcc.Graph(id="chart-saldo", config={"displayModeBar": False}, style={"height": "300px"}),
                ], extra={"flex": "2", "minWidth": "300px"}),
                card([
                    section_title("Distribuição por Situação"),
                    dcc.Graph(id="chart-situacao", config={"displayModeBar": False}, style={"height": "300px"}),
                ], extra={"flex": "1", "minWidth": "260px"}),
            ], style={"display": "flex", "gap": "16px", "marginBottom": "20px", "flexWrap": "wrap"}),

            # Gráficos linha 2
            card([
                section_title("Entradas e Saídas Mensais"),
                dcc.Graph(id="chart-mensal", config={"displayModeBar": False}, style={"height": "300px"}),
            ]),
        ],
    )


def _tab_analise() -> dcc.Tab:
    return dcc.Tab(
        label="\U0001f4c8  Análise",
        value="analise",
        style=_TAB_STYLE,
        selected_style=_SELECTED_TAB_STYLE,
        children=[
            html.Div([
                card([
                    section_title("Saídas por Categoria"),
                    dcc.Graph(id="chart-categoria", config={"displayModeBar": False}, style={"height": "360px"}),
                ], extra={"flex": "3", "minWidth": "300px"}),
                card([
                    section_title("Saídas por Forma de Pagamento"),
                    dcc.Graph(id="chart-forma-pgto", config={"displayModeBar": False}, style={"height": "360px"}),
                ], extra={"flex": "2", "minWidth": "240px"}),
            ], style={"display": "flex", "gap": "16px", "marginBottom": "20px", "flexWrap": "wrap"}),

            card([
                section_title("Top 10 Maiores Saídas Individuais"),
                dcc.Graph(id="chart-top-saidas", config={"displayModeBar": False}, style={"height": "380px"}),
            ]),
        ],
    )


def _tab_lancamentos() -> dcc.Tab:
    return dcc.Tab(
        label="\U0001f4cb  Lançamentos",
        value="lancamentos",
        style=_TAB_STYLE,
        selected_style=_SELECTED_TAB_STYLE,
        children=[
            section_title("Lançamentos Detalhados — Apenas Movimentos"),
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
                    {"name": "Entradas",     "id": "entradas",     "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Saídas",       "id": "saidas",       "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Saldo Acum.",  "id": "saldo_acumulado", "type": "numeric", "format": {"specifier": ",.2f"}},
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
    )


def criar_layout() -> html.Div:
    """Retorna o layout completo da aplicação."""
    return html.Div([

        # Google Fonts
        html.Link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap",
        ),

        _header(),

        html.Main([

            _hero(),
            _filtros(),

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
                    _tab_painel(),
                    _tab_analise(),
                    _tab_lancamentos(),
                ],
            ),

        ], style={"maxWidth": "1600px", "margin": "0 auto", "padding": "24px"}),

    ], style={
        "background": BG, "minHeight": "100vh",
        "fontFamily": FONT, "color": TEXT,
    })