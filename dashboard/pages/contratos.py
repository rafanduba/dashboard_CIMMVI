"""Página: Contratos — resumos consolidados por período e entidade."""

from dash import dash_table, html

from dashboard.components import card, section_title
from dashboard.config import (
    BORDER, CARD, CARD2, DANGER, FONT, INFO, MUTED,
    PRIMARY, SECONDARY, SUCCESS, TEXT, TEXT_DIM, WARNING,
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

_TABLE_COND_CONTRATOS = [
    {"if": {"row_index": "odd"}, "backgroundColor": CARD2},
    {"if": {"filter_query": '{situacao} = "Pago"'}, "color": "#34d399", "fontWeight": "600"},
    {"if": {"filter_query": '{situacao} = "Em aberto"'}, "color": "#f87171", "fontWeight": "600"},
    {"if": {"column_id": "total_saidas_fmt"}, "color": "#f87171", "fontWeight": "600"},
    {"if": {"column_id": "parc_info"}, "color": "#38bdf8", "fontWeight": "600"},
    {"if": {"column_id": "parc_restante"}, "color": "#fbbf24", "fontWeight": "600"},
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
        # ── Contratos de Rateio (Parcelas e Situação) ────────────────────────
        section_title("Contratos de Rateio — Parcelas e Situação (Última Ocorrência)"),
        html.Div([
            dash_table.DataTable(
                id="tabela-contratos-rateio",
                columns=[
                    {"name": "Contrato", "id": "contrato"},
                    {"name": "Parc. Pagas", "id": "parc_atual"},
                    {"name": "Parc. Restantes", "id": "parc_restante"},
                    {"name": "Parc. Total", "id": "parc_total"},
                    {"name": "Situação Parcelas", "id": "parc_info"},
                    {"name": "Total Saídas", "id": "total_saidas_fmt"},
                    {"name": "Último Pagamento", "id": "data_pagamento"},
                    {"name": "Situação", "id": "situacao"},
                ],
                data=[],
                page_size=15,
                page_action="native",
                sort_action="native",
                style_table={"overflowX": "auto"},
                style_header=_TABLE_HEADER,
                style_cell=_TABLE_CELL,
                style_data_conditional=_TABLE_COND_CONTRATOS,
            ),
        ], style={"marginBottom": "28px"}),

        # ── Nota informativa ────────────────────────────────────────────────
        html.Div([
            html.Div("ℹ️", style={"fontSize": "20px", "marginRight": "12px"}),
            html.Div([
                html.Div("Esta tela consolida os principais indicadores financeiros e parcelas de contratos.", style={
                    "fontSize": "13px", "color": TEXT, "fontWeight": "500",
                }),
                html.Div(
                    "Use os filtros de período, conta e entidade no topo para refinar os dados.",
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

