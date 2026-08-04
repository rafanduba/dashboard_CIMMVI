"""Página: Municípios Consorciados — Visão de Arrecadação, Adimplência e Lançamentos."""

from dash import dcc, dash_table, html

from dashboard.components import card, kpi, section_title
from dashboard.config import (
    BORDER, CARD, CARD2, DANGER, FONT, INFO,
    PRIMARY, SUCCESS, TEXT, TEXT_DIM, WARNING,
)

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

_TABLE_COND_ADIM = [
    {"if": {"row_index": "odd"}, "backgroundColor": CARD2},
    {"if": {"filter_query": '{status} = "✅ Adimplente"'}, "color": "#34d399", "fontWeight": "600"},
    {"if": {"filter_query": '{status} = "❌ Inadimplente"'}, "color": "#f87171", "fontWeight": "600"},
    {"if": {"column_id": "recebido_fmt"}, "color": "#34d399", "fontWeight": "600"},
    {"if": {"column_id": "saldo_fmt"}, "color": "#fbbf24", "fontWeight": "600"},
    {"if": {"column_id": "previsto_fmt"}, "color": "#38bdf8", "fontWeight": "600"},
]

_TABLE_COND_LANC = [
    {"if": {"row_index": "odd"}, "backgroundColor": CARD2},
    {"if": {"filter_query": '{situacao} = "Em aberto"'}, "color": "#f87171", "fontWeight": "600"},
    {"if": {"filter_query": '{situacao} = "Pago"'}, "color": "#34d399"},
    {"if": {"filter_query": '{situacao} = "Aguardando Aprovação"'}, "color": "#fbbf24"},
    {"if": {"column_id": "entradas"}, "color": "#34d399"},
    {"if": {"column_id": "saidas"}, "color": "#f87171"},
    {"if": {"column_id": "saldo_acumulado"}, "color": "#38bdf8", "fontWeight": "600"},
]


def layout() -> html.Div:
    """Retorna o conteúdo da tela Municípios Consorciados."""
    return html.Div([

        # ── 1. Resumo em Cards KPI (Município | Previsto | Recebido | Saldo) ──
        html.Div([
            kpi("kpi-muni-total", "Municípios Consorciados", "🏛️", color=PRIMARY, sublabel="total de consorciados"),
            kpi("kpi-muni-previsto", "Previsto Total", "📅", color=INFO, sublabel="previsão anual de rateio"),
            kpi("kpi-muni-recebido", "Recebido (Arrecadado)", "📥", color=SUCCESS, sublabel="total arrecadado no período"),
            kpi("kpi-muni-saldo", "Saldo a Arrecadar", "⏳", color=WARNING, sublabel="diferença a receber"),
        ], style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fit, minmax(220px, 1fr))",
            "gap": "16px",
            "marginBottom": "24px",
        }),

        # ── 2. Tabela Resumo: Município | Previsto | Recebido | Saldo ────────
        section_title("Resumo por Município — Previsto vs. Recebido vs. Saldo"),
        html.Div([
            dash_table.DataTable(
                id="tabela-adimplencia",
                columns=[
                    {"name": "Município", "id": "municipio"},
                    {"name": "Previsto", "id": "previsto_fmt"},
                    {"name": "Recebido", "id": "recebido_fmt"},
                    {"name": "Saldo", "id": "saldo_fmt"},
                    {"name": "Parcelas", "id": "parcelas"},
                    {"name": "Situação", "id": "status"},
                ],
                data=[],
                page_size=20,
                page_action="native",
                sort_action="native",
                style_table={"overflowX": "auto"},
                style_header=_TABLE_HEADER,
                style_cell=_TABLE_CELL,
                style_data_conditional=_TABLE_COND_ADIM,
            ),
        ], style={"marginBottom": "28px"}),

        # ── 3. Indicadores (3 Gráficos empilhados) ──────────────────────────
        section_title("Indicadores"),
        html.Div([

            # Indicador 1: Valor arrecadado por município
            card([
                html.Div("📊 Valor arrecadado por município", style={
                    "fontSize": "13px", "fontWeight": "700", "color": TEXT,
                    "marginBottom": "16px", "textTransform": "uppercase", "letterSpacing": "0.05em",
                }),
                dcc.Graph(id="chart-municipios-arrecadacao", config={"displayModeBar": False}, style={"height": "380px"}),
            ]),

            # Indicador 2: % de adimplência e Inadimplência
            card([
                html.Div("🎯 % de Adimplência e Inadimplência", style={
                    "fontSize": "13px", "fontWeight": "700", "color": TEXT,
                    "marginBottom": "16px", "textTransform": "uppercase", "letterSpacing": "0.05em",
                }),
                dcc.Graph(id="chart-municipios-adimplencia", config={"displayModeBar": False}, style={"height": "380px"}),
            ]),

            # Indicador 3: Ranking de maior arrecadação
            card([
                html.Div("🏆 Ranking de maior arrecadação", style={
                    "fontSize": "13px", "fontWeight": "700", "color": TEXT,
                    "marginBottom": "16px", "textTransform": "uppercase", "letterSpacing": "0.05em",
                }),
                dcc.Graph(id="chart-municipios-ranking", config={"displayModeBar": False}, style={"height": "380px"}),
            ]),

        ], style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "20px",
            "marginBottom": "40px",
        }),

        # Tabela oculta (mantida para o callback não quebrar)
        html.Div(
            dash_table.DataTable(
                id="tabela-lancamentos",
                columns=[
                    {"name": "Data", "id": "data_pagamento"},
                    {"name": "Conta", "id": "conta"},
                    {"name": "Categoria", "id": "categoria"},
                    {"name": "Descrição", "id": "descricao"},
                    {"name": "NF / Doc", "id": "nf_doc"},
                    {"name": "Situação", "id": "situacao"},
                    {"name": "Forma Pgto.", "id": "forma_pagamento"},
                    {"name": "Parcelas", "id": "parc_info"},
                    {"name": "Entradas", "id": "entradas", "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Saídas", "id": "saidas", "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Saldo Acum.", "id": "saldo_acumulado", "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Obs.", "id": "observacao"},
                ],
                data=[],
                page_size=20,
                page_action="native",
                sort_action="native",
                style_table={"overflowX": "auto"},
                style_header=_TABLE_HEADER,
                style_cell=_TABLE_CELL,
                style_data_conditional=_TABLE_COND_LANC,
            ),
            style={"display": "none"},
        ),
    ])
