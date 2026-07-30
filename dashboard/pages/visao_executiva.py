"""Página: Visão Executiva — visão geral, KPIs e gráficos de saldo."""

from dash import dash_table
from dash import dcc, html

from dashboard.components import card, kpi, section_title
from dashboard.config import (
    BORDER, CARD, CARD2, DANGER, FONT, INFO,
    MUTED, PRIMARY, SECONDARY, SUCCESS, TEXT, TEXT_DIM, WARNING,
)


def layout() -> html.Div:
    """Retorna o conteúdo da tela Visão Executiva."""
    from dashboard.layout import filtros_bar  # lazy import — evita ciclo
    return html.Div([

        # ── Hero: Patrimônio Total ──────────────────────────────────────────
        html.Div([

            html.Div([
                html.Div("🏦  Patrimônio Total — Todas as Contas", style={
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
                        html.Span(" · Banco do Brasil + Caixa", style={"fontSize": "10px", "color": MUTED}),
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
                        html.Span(" · Banco do Brasil CC 439", style={"fontSize": "10px", "color": MUTED}),
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
            "marginBottom": "24px",
            "flexWrap": "wrap",
            "boxShadow": "0 0 60px rgba(52,211,153,0.06)",
        }),

        # ── Saldo por Conta (individual) ────────────────────────────────────
        section_title("Saldo por Conta"),
        html.Div([
            card([
                html.Div("CIMMVI · Banco do Brasil", style={
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
                html.Div("CIMMVI · Caixa Econômica", style={
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
                html.Div("AMVI · Banco do Brasil", style={
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

        # ── KPIs ────────────────────────────────────────────────────────────
        filtros_bar(),
        section_title("Movimentação no Período"),
        html.Div([
            kpi("kpi-entradas",      "Total de Entradas",    "⬆️", SUCCESS,  "no período selecionado"),
            kpi("kpi-saidas",        "Total de Saídas",      "⬇️", DANGER,   "no período selecionado"),
            kpi("kpi-liquido",       "Resultado Líquido",    "⚖️", WARNING,  "entradas − saídas"),
            kpi("kpi-aberto-saidas", "Saídas em Aberto",     "📤", DANGER,   "pendentes de pagamento"),
            kpi("kpi-aberto-ent",    "Entradas em Aberto",   "📥", SUCCESS,  "pendentes de recebimento"),
            kpi("kpi-aguardando",    "Aguardando Aprovação", "🔔", WARNING,  "saídas em análise"),
        ], style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fit, minmax(160px, 1fr))",
            "gap": "16px",
            "marginBottom": "28px",
        }),

        # Status de Adimplência dos Municípios
        section_title("Status de Adimplência dos Municípios"),
        html.Div([
            dash_table.DataTable(
                id="tabela-adimplencia",
                columns=[
                    {"name": "Município", "id": "municipio"},
                    {"name": "Status", "id": "status"},
                    {"name": "Parcelas Pagas", "id": "parcelas"},
                ],
                data=[],
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": CARD2, "color": TEXT_DIM,
                    "fontWeight": "600", "fontSize": "11px",
                    "textTransform": "uppercase", "letterSpacing": "0.05em",
                    "border": f"1px solid {BORDER}", "padding": "10px 14px",
                    "fontFamily": FONT,
                },
                style_cell={
                    "backgroundColor": CARD, "color": TEXT,
                    "fontSize": "13px", "border": f"1px solid {BORDER}",
                    "padding": "10px 14px", "fontFamily": FONT,
                },
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": CARD2},
                    {"if": {"filter_query": '{status} = "✅ Adimplente"'}, "color": SUCCESS, "fontWeight": "600"},
                    {"if": {"filter_query": '{status} = "❌ Inadimplente"'}, "color": DANGER, "fontWeight": "600"},
                ],
            ),
        ], style={"marginBottom": "28px"}),
        
    # DESPESAS 
        html.Div([
            card([
                section_title("Saídas por Categoria"),
                dcc.Graph(id="chart-categoria", config={"displayModeBar": False}, style={"height": "360px"}),
            ], extra={"flex": "3", "minWidth": "300px"}),
            card([
                section_title("Distribuição por Categoria (%)"),
                dcc.Graph(id="chart-categoria-pizza", config={"displayModeBar": False}, style={"height": "360px"}),
            ], extra={"flex": "2", "minWidth": "280px"}),
        ], style={"display": "flex", "gap": "16px", "marginBottom": "20px", "flexWrap": "wrap"}),
        card([
            section_title("Entradas e Saídas Mensais"),
            dcc.Graph(id="chart-mensal", config={"displayModeBar": False}, style={"height": "300px"}),
        ], extra={"flex": "3", "minWidth": "300px"}),

        # ── Gráficos linha 1 ────────────────────────────────────────────────
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
    ])
