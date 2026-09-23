"""Layout principal do dashboard — Sidebar colapsável + 4 telas."""

from datetime import date

from dash import dcc, html

from dashboard.components import card, label
from dashboard.config import (
    BG, BORDER, CARD, CARD2, FONT, INFO, MUTED,
    PRIMARY, SUCCESS, TEXT, TEXT_DIM, WARNING,
)

# ════════════════════════════════════════════════════════════════════════════
# Mensagem de boas-vindas do chatbot
# ════════════════════════════════════════════════════════════════════════════
_CHATBOT_WELCOME = (
    "Olá! Sou o assistente financeiro do CIMMVI/AMVI. "
    "Posso responder perguntas sobre saldos, lançamentos, "
    "municípios consorciados e contratos.\n\n"
    "Como posso ajudar?"
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

def _obter_init_filtros():
    try:
        from etl.load import garantir_dados_carregados
        garantir_dados_carregados()
        from dashboard.queries import contas_disponiveis, periodo_disponivel
        p = periodo_disponivel() or {}
        d_min = p.get("data_min") or _ano_inicio
        d_max = p.get("data_max") or _hoje
        contas_list = contas_disponiveis() or []
        contas_opts = [{"label": "Todas as contas", "value": ""}] + [
            {"label": c, "value": c} for c in contas_list
        ]
        return d_min, d_max, contas_opts
    except Exception:
        return _ano_inicio, _hoje, [{"label": "Todas as contas", "value": ""}]

DATE_MIN, DATE_MAX, _CONTAS = _obter_init_filtros()
START_PADRAO = DATE_MIN
END_PADRAO   = DATE_MAX


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
    """Barra superior com título da página ativa, botões de ação e status do ETL."""
    return html.Header(
        id="topbar",
        className="topbar",
        children=[
            html.Div([
                html.Div(id="topbar-title", className="topbar-title", children="Visão Executiva"),
                html.Div([
                    html.Button(
                        id="btn-theme-toggle",
                        className="theme-toggle-btn",
                        children="🌙 Modo Escuro",
                        n_clicks=0,
                        style={
                            "background": "var(--card2)",
                            "border": "1px solid var(--border)",
                            "color": "var(--text)",
                            "padding": "7px 14px",
                            "borderRadius": "20px",
                            "cursor": "pointer",
                            "fontSize": "12px",
                            "fontWeight": "600",
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "6px",
                            "marginRight": "12px",
                            "transition": "all 0.2s ease",
                        },
                    ),
                    html.Button(
                        id="btn-sync-sheets",
                        className="sync-sheets-btn",
                        n_clicks=0,
                        children=[
                            html.Span("🔄", className="sync-icon"),
                            html.Span("Sincronizar Google Sheets", className="sync-text"),
                        ],
                        style={
                            "background": "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
                            "border": "none",
                            "color": "#ffffff",
                            "padding": "8px 16px",
                            "borderRadius": "20px",
                            "cursor": "pointer",
                            "fontSize": "12px",
                            "fontWeight": "600",
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                            "marginRight": "12px",
                            "boxShadow": "0 2px 6px rgba(99, 102, 241, 0.25)",
                            "transition": "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
                        },
                    ),
                    html.Button(
                        id="btn-topbar-chatbot",
                        className="topbar-chatbot-btn",
                        n_clicks=0,
                        title="Abrir Assistente Financeiro IA (Gemini)",
                        children=[
                            html.Span("💬", style={"fontSize": "14px"}),
                            html.Span("Assistente IA"),
                        ],
                        style={
                            "background": "linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)",
                            "border": "none",
                            "color": "#ffffff",
                            "padding": "8px 16px",
                            "borderRadius": "20px",
                            "cursor": "pointer",
                            "fontSize": "12px",
                            "fontWeight": "600",
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "6px",
                            "boxShadow": "0 2px 8px rgba(139, 92, 246, 0.35)",
                            "transition": "all 0.2s ease",
                        },
                    ),
                    dcc.Loading(
                        id="loading-sync",
                        type="dot",
                        color="var(--primary)",
                        children=html.Div(id="header-etl", style={
                            "fontSize": "12px", "color": TEXT_DIM, "textAlign": "right",
                        }),
                    ),
                ], style={"display": "flex", "alignItems": "center"}),
            ], className="topbar-inner"),
        ],
    )


def filtros_bar() -> html.Div:
    """Barra de filtros — pode ser inserida em qualquer página."""
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
# Widget Chatbot Flutuante
# ════════════════════════════════════════════════════════════════════════════

def _chatbot_widget() -> html.Div:
    """Botão flutuante 💬 + painel de chat deslizante."""

    # Mensagem de boas-vindas (bolha do bot)
    welcome_msg = html.Div(
        className="chat-bubble chat-bubble-bot",
        children=[
            html.Div("🤖", className="chat-avatar"),
            html.Div(_CHATBOT_WELCOME, className="chat-text"),
        ],
    )

    return html.Div(
        id="chatbot-container",
        className="chatbot-container",
        style={
            "position": "fixed",
            "bottom": "28px",
            "right": "28px",
            "zIndex": "99999",
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "flex-end",
            "gap": "12px",
        },
        children=[

            # ── Painel de chat ────────────────────────────────────────────
            html.Div(
                id="chatbot-panel",
                className="chatbot-panel chatbot-panel-closed",
                children=[

                    # Cabeçalho
                    html.Div(
                        className="chatbot-header",
                        children=[
                            html.Div([
                                html.Span("🤖", style={"fontSize": "18px"}),
                                html.Div([
                                    html.Div("Assistente Financeiro", className="chatbot-header-title"),
                                    html.Div("CIMMVI / AMVI • Powered by Gemini", className="chatbot-header-sub"),
                                ]),
                            ], style={"display": "flex", "alignItems": "center", "gap": "10px"}),
                            html.Div([
                                html.Button(
                                    "🗑️",
                                    id="btn-chatbot-clear",
                                    className="chatbot-icon-btn",
                                    title="Limpar conversa",
                                    n_clicks=0,
                                ),
                                html.Button(
                                    "✕",
                                    id="btn-chatbot-close",
                                    className="chatbot-icon-btn",
                                    title="Fechar",
                                    n_clicks=0,
                                ),
                            ], style={"display": "flex", "gap": "4px"}),
                        ],
                    ),

                    # Área de mensagens
                    html.Div(
                        id="chatbot-messages",
                        className="chatbot-messages",
                        children=[welcome_msg],
                    ),

                    # Indicador de digitação (oculto por padrão)
                    html.Div(
                        id="chatbot-typing",
                        className="chatbot-typing hidden",
                        children=[
                            html.Div("🤖", className="chat-avatar"),
                            html.Div([
                                html.Span(className="typing-dot"),
                                html.Span(className="typing-dot"),
                                html.Span(className="typing-dot"),
                            ], className="typing-dots"),
                        ],
                    ),

                    # Input + botão enviar
                    html.Div(
                        className="chatbot-input-area",
                        children=[
                            dcc.Input(
                                id="chatbot-input",
                                type="text",
                                placeholder="Digite sua pergunta...",
                                className="chatbot-input",
                                debounce=False,
                                n_submit=0,
                                value="",
                            ),
                            html.Button(
                                "➤",
                                id="btn-chatbot-send",
                                className="chatbot-send-btn",
                                n_clicks=0,
                            ),
                        ],
                    ),
                ],
            ),

            # ── Botão flutuante ───────────────────────────────────────────
            html.Button(
                id="btn-chatbot-toggle",
                className="chatbot-fab",
                n_clicks=0,
                title="Assistente Financeiro (Gemini IA)",
                style={
                    "width": "56px",
                    "height": "56px",
                    "borderRadius": "50%",
                    "border": "none",
                    "background": "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
                    "color": "white",
                    "fontSize": "24px",
                    "cursor": "pointer",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "boxShadow": "0 4px 20px rgba(99, 102, 241, 0.5), 0 2px 8px rgba(0,0,0,0.2)",
                    "flexShrink": "0",
                    "position": "relative",
                },
                children=[
                    html.Span("💬", id="chatbot-fab-icon", className="chatbot-fab-icon", style={"lineHeight": "1"}),
                ],
            ),
        ],
    )


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

        # Estado do tema e do sidebar
        dcc.Store(id="theme-store", data="light", storage_type="local"),
        dcc.Store(id="sidebar-collapsed", data=False),

        # Gatilho de sincronização em tempo real (notifica todos os callbacks quando o ETL termina)
        dcc.Store(id="sync-trigger", data=0),

        # Cache de dados para contratos de rateio (evita query a cada filtro local)
        dcc.Store(id="store-contratos-rateio", data=[]),

        # Histórico de mensagens do chatbot
        dcc.Store(id="chatbot-historico", data=[]),

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
                    # Wrapper com todas as páginas pré-renderizadas
                    html.Div(id="page-content", children=pages_content),
                ], style={"padding": "24px"}),
            ],
        ),

        # ── Chatbot Flutuante ─────────────────────────────────────────────
        _chatbot_widget(),

    ],
    id="app-container",
    **{"data-theme": "light"},
    style={
        "background": "var(--bg)",
        "minHeight": "100vh",
        "fontFamily": FONT,
        "color": "var(--text)",
        "display": "flex",
    })