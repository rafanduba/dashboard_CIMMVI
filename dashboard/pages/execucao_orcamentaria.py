"""Página: Execução Orçamentária — gráficos por categoria, forma de pagamento e top saídas."""

from dash import dcc, html

from dashboard.components import card, section_title


def layout() -> html.Div:
    """Retorna o conteúdo da tela Execução Orçamentária."""
    return html.Div([

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

    ])
