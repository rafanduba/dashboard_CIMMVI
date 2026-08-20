"""Página: Contratos — resumos consolidados por período e entidade."""

from datetime import date
from dash import dcc, dash_table, html

from dashboard.components import card, label, section_title
from dashboard.config import (
    BORDER, CARD, CARD2, DANGER, FONT, INFO, MUTED,
    PRIMARY, SECONDARY, SUCCESS, TEXT, TEXT_DIM, WARNING,
)

# ════════════════════════════════════════════════════════════════════════════
# Configuração de datas padrão e estilos de filtro
# ════════════════════════════════════════════════════════════════════════════
_hoje = str(date.today())
_ano_inicio = str(date.today().replace(month=1, day=1))

try:
    from dashboard.queries import periodo_disponivel
    _p = periodo_disponivel()
    DATE_MIN     = _p.get("data_min") or _ano_inicio
    DATE_MAX     = _p.get("data_max") or _hoje
    START_PADRAO = DATE_MIN
    END_PADRAO   = DATE_MAX
except Exception:
    DATE_MIN = START_PADRAO = _ano_inicio
    DATE_MAX = END_PADRAO   = _hoje

_DD_STYLE = {
    "backgroundColor": CARD2,
    "border": f"1px solid {BORDER}",
    "borderRadius": "8px",
    "color": TEXT,
    "fontSize": "13px",
}

_TABLE_HEADER = {
    "backgroundColor": CARD2,
    "color": TEXT_DIM,
    "fontWeight": "700",
    "fontSize": "11px",
    "textTransform": "uppercase",
    "letterSpacing": "0.08em",
    "border": "none",
    "borderBottom": f"2px solid {BORDER}",
    "padding": "14px 16px",
    "fontFamily": FONT,
}

_TABLE_CELL = {
    "backgroundColor": CARD,
    "color": TEXT,
    "fontSize": "13px",
    "border": "none",
    "borderBottom": f"1px solid {BORDER}",
    "padding": "12px 16px",
    "fontFamily": FONT,
    "textOverflow": "ellipsis",
    "overflow": "hidden",
    "whiteSpace": "normal",
    "height": "auto",
}

_TABLE_CELL_COND = [
    {"if": {"column_id": "contrato"}, "textAlign": "left", "width": "40%", "fontWeight": "600", "color": TEXT},
    {"if": {"column_id": "parc_info"}, "textAlign": "center", "width": "22%", "fontWeight": "600", "color": INFO, "fontVariantNumeric": "tabular-nums"},
    {"if": {"column_id": "total_saidas_fmt"}, "textAlign": "right", "width": "16%", "fontWeight": "700", "color": DANGER, "fontVariantNumeric": "tabular-nums"},
    {"if": {"column_id": "data_pagamento"}, "textAlign": "center", "width": "11%", "color": TEXT_DIM, "fontVariantNumeric": "tabular-nums"},
    {"if": {"column_id": "situacao"}, "textAlign": "center", "width": "11%"},
]

_TABLE_COND_CONTRATOS = [
    {"if": {"row_index": "odd"}, "backgroundColor": CARD2},
    {
        "if": {"column_id": "situacao", "filter_query": '{situacao} = "Pago"'},
        "backgroundColor": "rgba(16, 185, 129, 0.15)",
        "color": SUCCESS,
        "fontWeight": "700",
        "borderRadius": "20px",
    },
    {
        "if": {"column_id": "situacao", "filter_query": '{situacao} = "Em aberto"'},
        "backgroundColor": "rgba(239, 68, 68, 0.15)",
        "color": DANGER,
        "fontWeight": "700",
        "borderRadius": "20px",
    },
    {
        "if": {"column_id": "situacao", "filter_query": '{situacao} = "Aguardando Aprovação"'},
        "backgroundColor": "rgba(245, 158, 11, 0.15)",
        "color": WARNING,
        "fontWeight": "700",
        "borderRadius": "20px",
    },
    {
        "if": {"column_id": "situacao", "filter_query": '{situacao} = "Aprovado - Aguardando Pagamento"'},
        "backgroundColor": "rgba(6, 182, 212, 0.15)",
        "color": INFO,
        "fontWeight": "700",
        "borderRadius": "20px",
    },
    {
        "if": {"column_id": "situacao", "filter_query": '{situacao} = "Nao informado"'},
        "backgroundColor": "rgba(100, 116, 139, 0.15)",
        "color": MUTED,
        "fontWeight": "600",
        "borderRadius": "20px",
    },
]


def _stat_card(titulo: str, id_valor: str, cor: str, descricao: str = "") -> html.Div:
    """Card de estatística simples para a tela de contratos."""
    return card([
        html.Div(titulo, style={
            "fontSize": "10px", "color": TEXT_DIM, "fontWeight": "700",
            "textTransform": "uppercase", "letterSpacing": "0.1em",
            "marginBottom": "10px",
        }),
        html.Div(id=id_valor, style={
            "fontSize": "28px", "fontWeight": "800",
            "color": cor, "fontVariantNumeric": "tabular-nums",
            "letterSpacing": "-0.03em",
        }),
        html.Div(descricao, style={
            "fontSize": "11px", "color": MUTED, "marginTop": "6px",
        }),
    ], extra={"borderTop": f"3px solid {cor}", "flex": "1", "minWidth": "180px"})


def layout() -> html.Div:
    return html.Div([
        # ── Contratos de Rateio ───────────────────────────────────────────────
        section_title("Contratos de Rateio — Parcelas e Situação"),

        # ── Barra de Filtros Interativa ──────────────────────────────────────
        card([
            html.Div([
                # 1. Intervalo de Tempo (Período)
                html.Div([
                    label("📅 Intervalo de Tempo"),
                    dcc.DatePickerRange(
                        id="filtro-contrato-periodo",
                        start_date=START_PADRAO,
                        end_date=END_PADRAO,
                        min_date_allowed=DATE_MIN,
                        max_date_allowed=DATE_MAX,
                        display_format="DD/MM/YYYY",
                        style={"fontFamily": FONT},
                    ),
                ], style={"flex": "0 0 auto"}),

                # 2. Categoria Selecionável (Dinâmica - Atualizada via Callback)
                html.Div([
                    label("🏷️ Categoria"),
                    dcc.Dropdown(
                        id="filtro-contrato-categoria",
                        options=[{"label": "Todas as categorias", "value": ""}],
                        value="",
                        clearable=True,
                        placeholder="Todas as categorias...",
                        style=_DD_STYLE,
                    ),
                ], style={"flex": "1", "minWidth": "200px"}),

                # 3. Filtro de Parcelas
                html.Div([
                    label("🔢 Parcelas"),
                    dcc.Dropdown(
                        id="filtro-contrato-parcelas",
                        options=[
                            {"label": "Todas as parcelas", "value": ""},
                            {"label": "⏳ Com parcelas pendentes", "value": "pendentes"},
                            {"label": "✅ Totalmente quitadas", "value": "quitadas"},
                            {"label": "ℹ️ Sem parcelas informadas", "value": "sem_parcela"},
                        ],
                        value="",
                        clearable=False,
                        style=_DD_STYLE,
                    ),
                ], style={"flex": "1", "minWidth": "200px"}),

                # 4. Busca por Objeto / Nome do Contrato
                html.Div([
                    label("🔍 Buscar Contrato"),
                    dcc.Input(
                        id="filtro-contrato-busca",
                        type="text",
                        placeholder="Nome ou palavra-chave...",
                        style={
                            "backgroundColor": CARD2,
                            "border": f"1px solid {BORDER}",
                            "borderRadius": "8px",
                            "color": TEXT,
                            "padding": "8px 12px",
                            "fontSize": "13px",
                            "width": "100%",
                            "fontFamily": FONT,
                            "height": "36px",
                            "boxSizing": "border-box",
                        },
                    ),
                ], style={"flex": "1", "minWidth": "180px"}),


            ], style={
                "display": "flex",
                "gap": "20px",
                "alignItems": "flex-end",
                "flexWrap": "wrap",
            }),
        ], extra={"marginBottom": "20px", "padding": "18px 24px"}),

        # ── Card da Tabela de Contratos ───────────────────────────────────────
        card([
            html.Div([
                html.Div([
                    html.Div("📜 Relação Consolidada de Contratos", style={
                        "fontSize": "16px", "fontWeight": "700", "color": TEXT, "marginBottom": "4px",
                    }),
                    html.Div("Consolidado por período: categoria, parcelas quitadas, total de saídas e status", style={
                        "fontSize": "12px", "color": TEXT_DIM,
                    }),
                ]),
            ], style={
                "display": "flex", "justifyContent": "space-between",
                "alignItems": "center", "marginBottom": "20px", "paddingBottom": "12px",
                "borderBottom": f"1px solid {BORDER}",
            }),

            dash_table.DataTable(
                id="tabela-contratos-rateio",
                columns=[
                    {"name": "Contrato / Objeto", "id": "contrato"},
                    {"name": "Parcelas (Pagas/Total)", "id": "parc_info"},
                    {"name": "Total Saídas", "id": "total_saidas_fmt"},
                    {"name": "Último Pagamento", "id": "data_pagamento"},
                    {"name": "Situação", "id": "situacao"},
                ],
                data=[],
                page_size=15,
                page_action="native",
                sort_action="native",
                sort_mode="multi",
                style_table={"overflowX": "auto", "minWidth": "100%"},
                style_header=_TABLE_HEADER,
                style_cell=_TABLE_CELL,
                style_cell_conditional=_TABLE_CELL_COND,
                style_data_conditional=_TABLE_COND_CONTRATOS,
            ),
        ], extra={"marginBottom": "28px", "padding": "24px"}),

        # ── Nota informativa ────────────────────────────────────────────────
        html.Div([
            html.Div("ℹ️", style={"fontSize": "20px", "marginRight": "12px"}),
            html.Div([
                html.Div("Esta tela consolida os principais indicadores financeiros e parcelas de contratos.", style={
                    "fontSize": "13px", "color": TEXT, "fontWeight": "500",
                }),
                html.Div(
                    "Use os filtros de intervalo de tempo, categoria e parcelas no topo para refinar os dados.",
                    style={"fontSize": "12px", "color": TEXT_DIM, "marginTop": "4px"},
                ),
            ]),
        ], style={
            "display": "flex", "alignItems": "flex-start",
            "background": "rgba(56,189,248,0.05)",
            "border": f"1px solid rgba(56,189,248,0.2)",
            "borderLeft": f"3px solid {INFO}",
            "borderRadius": "10px",
            "padding": "16px 20px",
        }),
    ])



