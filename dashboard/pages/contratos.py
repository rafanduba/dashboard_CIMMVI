"""Página: Contratos — resumos consolidados por período e entidade."""

from dash import html

from dashboard.components import card, section_title
from dashboard.layout import filtros_bar
from dashboard.config import (
    BORDER, CARD, CARD2, DANGER, INFO, MUTED,
    PRIMARY, SECONDARY, SUCCESS, TEXT, TEXT_DIM, WARNING,
)


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
    """Retorna o conteúdo da tela Contratos."""
    return html.Div([
        filtros_bar(),
        # ── Resumo Consolidado ───────────────────────────────────────────────
        section_title("Resumo Consolidado do Período"),
        html.Div([
            _stat_card("Total de Entradas",    "rel-entradas",  SUCCESS, "no período filtrado"),
            _stat_card("Total de Saídas",      "rel-saidas",    DANGER,  "no período filtrado"),
            _stat_card("Resultado Líquido",    "rel-liquido",   WARNING, "entradas − saídas"),
            _stat_card("Saldo Atual Total",    "rel-saldo",     PRIMARY, "todas as contas"),
        ], style={
            "display": "flex", "gap": "16px", "marginBottom": "28px", "flexWrap": "wrap",
        }),

        # ── Pendências ───────────────────────────────────────────────────────
        section_title("Pendências Financeiras"),
        html.Div([
            _stat_card("Saídas em Aberto",       "rel-ab-saidas",   DANGER,    "pendentes de pagamento"),
            _stat_card("Entradas em Aberto",      "rel-ab-ent",      SUCCESS,   "pendentes de recebimento"),
            _stat_card("Aguardando Aprovação",    "rel-aguardando",  WARNING,   "saídas em análise"),
        ], style={
            "display": "flex", "gap": "16px", "marginBottom": "28px", "flexWrap": "wrap",
        }),

        # ── Saldo por Conta ──────────────────────────────────────────────────
        section_title("Saldo Atual por Conta"),
        html.Div([
            _stat_card("CIMMVI · Banco do Brasil", "rel-saldo-c1", PRIMARY,   "Rateio BB"),
            _stat_card("CIMMVI · Caixa Econômica", "rel-saldo-c2", SECONDARY, "Licenciamento Caixa"),
            _stat_card("AMVI · Banco do Brasil",   "rel-saldo-c3", INFO,      "Conta Corrente 439"),
        ], style={
            "display": "flex", "gap": "16px", "marginBottom": "28px", "flexWrap": "wrap",
        }),

        # ── Nota informativa ────────────────────────────────────────────────
        html.Div([
            html.Div("ℹ️", style={"fontSize": "20px", "marginRight": "12px"}),
            html.Div([
                html.Div("Esta tela consolida os principais indicadores financeiros.", style={
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
