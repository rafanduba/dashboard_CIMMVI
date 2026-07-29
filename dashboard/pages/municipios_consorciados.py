"""Página: Municípios Consorciados — tabela detalhada de movimentos financeiros."""

from dash import dash_table, html

from dashboard.components import section_title
from dashboard.config import BORDER, CARD, CARD2, FONT, TEXT, TEXT_DIM
from dashboard.layout import filtros_bar



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


def layout() -> html.Div:
    """Retorna o conteúdo da tela Municípios Consorciados."""
    return html.Div([
        filtros_bar(),
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
                {"name": "Entradas",     "id": "entradas",        "type": "numeric", "format": {"specifier": ",.2f"}},
                {"name": "Saídas",       "id": "saidas",          "type": "numeric", "format": {"specifier": ",.2f"}},
                {"name": "Saldo Acum.",  "id": "saldo_acumulado", "type": "numeric", "format": {"specifier": ",.2f"}},
                {"name": "Obs.",         "id": "observacao"},
            ],
            data=[],
            page_size=30,
            page_action="native",
            sort_action="native",
            style_table={"overflowX": "auto"},
            style_header=_TABLE_HEADER,
            style_cell=_TABLE_CELL,
            style_data_conditional=_TABLE_COND,
        ),
    ])
