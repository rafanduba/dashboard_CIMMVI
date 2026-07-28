"""Layout principal do dashboard — Sidebar colapsável + 4 telas."""

from datetime import date

from dash import dcc, html

from dashboard.components import card, label
from dashboard.config import (
    BG, BORDER, CARD, CARD2, FONT, INFO, MUTED,
    PRIMARY, SUCCESS, TEXT, TEXT_DIM, WARNING,
)

# ════════════════════════════════════════════════════════════════════════════
# Estilo do DatePickerRange / Dropdowns (barra de filtros)
# ════════════════════════════════════════════════════════════════════════════
_DD_STYLE = {
    "backgroundColor": CARD2,
    "border": f"1px solid {BORDER}",
    "borderRadius": "8px",
    "color": TEXT,
    "fontSize": "13px",
}

# ════════════════════════════════════════════════════════════════════════════
# Valores iniciais
# ════════════════════════════════════════════════════════════════════════════
_hoje       = str(date.today())
_ano_inicio = str(date.today().replace(month=1, day=1))

try:
    from dashboard.queries import (
        contas_disponiveis, periodo_disponivel,
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
except Exception:
    _CONTAS = [{"label": "Todas as contas", "value": ""}]


# ════════════════════════════════════════════════════════════════════════════
# Itens de navegação do sidebar
# ════════════════════════════════════════════════════════════════════════════
_NAV_ITEMS = [
    {"icon": "🏠", "label": "Visão Executiva",          "page": "visao_executiva"},
    {"icon": "📈", "label": "Execução Orçamentária",    "page": "execucao_orcamentaria"},
    {"icon": "📋", "label": "Municípios Consorciados",  "page": "municipios_consorciados"},
    {"icon": "📊", "label": "Contratos",                "page": "contratos"},
]


def _sidebar() -> html.Aside:
    """Sidebar colapsável com navegação entre as 4 telas."""

    nav_items = []
    for item in _NAV_ITEMS:
        nav_items.append(
            html.Div(
                id=f"nav-{item['page']}",
                className="sidebar-nav-item",
                **{"data-page": item["page"]},
                n_clicks=0,
                children=[
                    html.Span(item["icon"], className="nav-icon"),
                    html.Span(item["label"], className="nav-label"),
                ],
            )
        )

    return html.Aside(
        id="sidebar",
        className="sidebar",
        children=[

            # ── Logo / Título ──────────────────────────────────────────────
            html.Div([
                html.Div("📊", style={"fontSize": "22px", "lineHeight": "1"}),
                html.Div([
                    html.Div("CIMMVI/AMVI", style={
                        "fontSize": "14px", "fontWeight": "700",
                        "color": TEXT, "letterSpacing": "-0.01em",
                        "lineHeight": "1",
                    }),
                ], className="sidebar-logo-text"),
            ], className="sidebar-logo"),

            # ── Divisor ───────────────────────────────────────────────────
            html.Div(className="sidebar-divider"),

            # ── Navegação ─────────────────────────────────────────────────
            html.Nav(nav_items, className="sidebar-nav"),

            # ── Footer: status ETL + botão colapso ─────────────────────────
            html.Div([
                html.Div(id="sidebar-etl-status", className="sidebar-etl"),
                html.Button(
                    id="btn-sidebar-toggle",
                    className="sidebar-toggle-btn",
                    n_clicks=0,
                    title="Recolher menu",
                    children=html.Span("◀", className="toggle-icon"),
                ),
            ], className="sidebar-footer"),
        ],
    )


def _topbar() -> html.Header:
    """Barra superior com título da página ativa e status do ETL."""
    return html.Header(
        id="topbar",
        className="topbar",
        children=[
            html.Div([
                html.Div(id="topbar-title", className="topbar-title", children="Visão Executiva"),
                html.Div(id="header-etl", style={
                    "fontSize": "12px", "color": TEXT_DIM, "textAlign": "right",
                }),
            ], className="topbar-inner"),
        ],
    )


def _filtros() -> html.Div:
    """Barra de filtros — sempre visível em todas as telas."""
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
            ], style={"flex": "0 0 auto"}),
            html.Div([
                label("Conta"),
                dcc.Dropdown(
                    id="filtro-conta",
                    options=_CONTAS,
                    value="",
                    clearable=False,
                    style=_DD_STYLE,
                ),
            ], style={"flex": "1", "maxWidth": "380px", "minWidth": "240px"}),
        ], style={
            "display": "flex",
            "gap": "24px",
            "alignItems": "flex-end",
            "flexWrap": "wrap",
        }),
    ], extra={"marginBottom": "20px", "padding": "16px 24px"})



# ════════════════════════════════════════════════════════════════════════════
# Layout principal
# ════════════════════════════════════════════════════════════════════════════

def criar_layout() -> html.Div:
    """Retorna o layout completo da aplicação com sidebar.

    Todas as 4 páginas são renderizadas no DOM desde o início e alternadas
    via display:block/none. Isso garante que todos os IDs existam sempre,
    evitando o erro 'nonexistent object in Output' do Dash.
    """
    from dashboard.pages import (
        visao_executiva,
        execucao_orcamentaria,
        municipios_consorciados,
        contratos,
    )

    _NAV_PAGES = ["visao_executiva", "execucao_orcamentaria", "municipios_consorciados", "contratos"]

    pages_content = []
    for page_name in _NAV_PAGES:
        mod = {
            "visao_executiva":        visao_executiva,
            "execucao_orcamentaria":  execucao_orcamentaria,
            "municipios_consorciados": municipios_consorciados,
            "contratos":              contratos,
        }[page_name]
        pages_content.append(
            html.Div(
                id=f"page-{page_name}",
                children=mod.layout(),
                # Visão Executiva visível por padrão; demais ocultos
                style={"display": "block" if page_name == "visao_executiva" else "none"},
            )
        )

    return html.Div([

        # Google Fonts
        html.Link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap",
        ),

        # Estado do sidebar (colapsado ou não)
        dcc.Store(id="sidebar-collapsed", data=False),

        # Navegação por URL interna
        dcc.Location(id="url", refresh=False),

        # ── Sidebar ───────────────────────────────────────────────────────
        _sidebar(),

        # ── Área principal ────────────────────────────────────────────────
        html.Div(
            id="main-area",
            className="main-area",
            children=[
                _topbar(),
                html.Div([
                    _filtros(),
                    # Wrapper com todas as páginas pré-renderizadas
                    html.Div(id="page-content", children=pages_content),
                ], style={"padding": "24px"}),
            ],
        ),

    ], style={
        "background": BG,
        "minHeight": "100vh",
        "fontFamily": FONT,
        "color": TEXT,
        "display": "flex",
    })