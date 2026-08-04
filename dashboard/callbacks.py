"""Callbacks do dashboard — toda a lógica de atualização."""

import logging

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, html, no_update

from dashboard.components import formata_brl, chart_layout, empty_fig
from dashboard.config import (
    BORDER, CONTA_ESTILOS, DANGER, FONT, MUTED,
    PALETA, PRIMARY, SITUACAO_CORES, SUCCESS, TEXT, TEXT_DIM, WARNING,
)

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════
# Queries (com fallback caso o banco não exista)
# ════════════════════════════════════════════════════════════════════════════
try:
    from etl.load import garantir_dados_carregados
    garantir_dados_carregados()
    from dashboard.queries import (
        contagem_por_situacao,
        entradas_em_aberto,
        entradas_saidas_mensais,
        evolucao_saldo_mensal,
        lancamentos_detalhados,
        saidas_em_aberto,
        saidas_por_categoria,
        saidas_por_forma_pagamento,
        saldo_final_conta_1,
        saldo_final_conta_2,
        saldo_final_conta_3,
        saldo_final_geral,
        top_saidas,
        total_entradas,
        total_liquido,
        total_saidas,
        ultima_carga,
        valor_aguardando_aprovacao,
        adimplencia_municipios,
    )
    _DB_READY = True
except Exception as _e:
    logger.warning("Banco não disponível: %s", _e)
    _DB_READY = False


# ════════════════════════════════════════════════════════════════════════════
# Mapeamento de páginas
# ════════════════════════════════════════════════════════════════════════════
_PAGE_TITLES = {
    "visao_executiva":        "🏠  Visão Executiva",
    "execucao_orcamentaria":  "📈  Execução Orçamentária",
    "municipios_consorciados": "📋  Municípios Consorciados",
    "contratos":              "📊  Contratos",
}

_NAV_PAGES = ["visao_executiva", "execucao_orcamentaria", "municipios_consorciados", "contratos"]


# ════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════

def _normalizar(conta: str, entidade: str):
    """Converte string vazia → None (sem filtro)."""
    return (conta or None), (entidade or None)


def _page_from_url(pathname: str) -> str:
    """Extrai o nome da página da URL (ex: /visao_executiva → 'visao_executiva')."""
    if pathname and pathname != "/":
        slug = pathname.strip("/").split("/")[0]
        if slug in _NAV_PAGES:
            return slug
    return "visao_executiva"


# ════════════════════════════════════════════════════════════════════════════
# Registro dos callbacks
# ════════════════════════════════════════════════════════════════════════════

def registrar_callbacks(app):
    """Registra todos os callbacks no app Dash."""

    # ── 1. Navegação: clique nos itens do sidebar → atualiza URL ─────────
    @app.callback(
        Output("url", "pathname"),
        [Input(f"nav-{p}", "n_clicks") for p in _NAV_PAGES],
        prevent_initial_call=True,
    )
    def navegar(*clicks):
        from dash import ctx
        if not ctx.triggered_id:
            return no_update
        # ID format: "nav-<page>"
        page = ctx.triggered_id.replace("nav-", "")
        return f"/{page}"

    # ── 2. Renderização da página ativa — show/hide ───────────────────────
    @app.callback(
        Output("topbar-title", "children"),
        # Alterna display de cada página
        *[Output(f"page-{p}", "style") for p in _NAV_PAGES],
        # Destaca item ativo no sidebar
        *[Output(f"nav-{p}", "className") for p in _NAV_PAGES],
        Input("url", "pathname"),
    )
    def render_page(pathname):
        page = _page_from_url(pathname)
        title = _PAGE_TITLES.get(page, "🏠  Visão Executiva")

        # Exibe apenas a página ativa; oculta as demais
        styles = [
            {"display": "block"} if p == page else {"display": "none"}
            for p in _NAV_PAGES
        ]

        # Classes CSS dos itens de nav (ativo vs. normal)
        classes = [
            "sidebar-nav-item active" if p == page else "sidebar-nav-item"
            for p in _NAV_PAGES
        ]

        return title, *styles, *classes


    # ── 3. Toggle do sidebar (colapso / expansão) ─────────────────────────
    @app.callback(
        Output("sidebar", "className"),
        Output("main-area", "className"),
        Output("sidebar-collapsed", "data"),
        Input("btn-sidebar-toggle", "n_clicks"),
        State("sidebar-collapsed", "data"),
        prevent_initial_call=True,
    )
    def toggle_sidebar(n_clicks, is_collapsed):
        collapsed = not is_collapsed
        sidebar_cls  = "sidebar collapsed" if collapsed else "sidebar"
        main_cls     = "main-area expanded" if collapsed else "main-area"
        return sidebar_cls, main_cls, collapsed

    # ── 3.5. Alternar Tema Claro / Escuro ──────────────────────────────────
    @app.callback(
        Output("theme-store", "data"),
        Output("btn-theme-toggle", "children"),
        Output("app-container", "data-theme"),
        Input("btn-theme-toggle", "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=False,
    )
    def alternar_tema(n_clicks, tema_atual):
        if not tema_atual:
            tema_atual = "light"
        if n_clicks and n_clicks > 0:
            novo_tema = "dark" if tema_atual == "light" else "light"
        else:
            novo_tema = tema_atual

        texto_botao = "🌙" if novo_tema == "light" else "☀️"
        return novo_tema, texto_botao, novo_tema

    # ── 4. Atualização dos dados (filtros) ────────────────────────────────
    @app.callback(
        # Header ETL
        Output("header-etl",         "children"),
        # Saldos globais (Painel)
        Output("saldo-geral",        "children"),
        Output("saldo-cimmvi",       "children"),
        Output("saldo-amvi",         "children"),
        # Saldo por conta individual (Painel)
        Output("saldo-c1",           "children"),
        Output("saldo-c2",           "children"),
        Output("saldo-c3",           "children"),
        # KPIs (Painel)
        Output("kpi-entradas",       "children"),
        Output("kpi-saidas",         "children"),
        Output("kpi-liquido",        "children"),
        Output("kpi-aberto-saidas",  "children"),
        Output("kpi-aberto-ent",     "children"),
        Output("kpi-aguardando",     "children"),
        # Gráficos — painel
        Output("chart-saldo",        "figure"),
        Output("chart-situacao",     "figure"),
        Output("chart-mensal",       "figure"),
        # Gráficos — análise
        Output("chart-categoria",        "figure"),
        Output("chart-categoria-pizza",  "figure"),
        # KPIs — Municípios Consorciados
        Output("kpi-muni-total",         "children"),
        Output("kpi-muni-previsto",      "children"),
        Output("kpi-muni-recebido",      "children"),
        Output("kpi-muni-saldo",         "children"),
        # Gráficos — Municípios Consorciados
        Output("chart-municipios-arrecadacao", "figure"),
        Output("chart-municipios-adimplencia", "figure"),
        Output("chart-municipios-ranking",     "figure"),
        # Tabela — lançamentos
        Output("tabela-lancamentos", "data"),
        # Tabela — adimplência
        Output("tabela-adimplencia", "data"),
        # Relatórios
        Output("rel-entradas",       "children"),
        Output("rel-saidas",         "children"),
        Output("rel-liquido",        "children"),
        Output("rel-saldo",          "children"),
        Output("rel-ab-saidas",      "children"),
        Output("rel-ab-ent",         "children"),
        Output("rel-aguardando",     "children"),
        Output("rel-saldo-c1",       "children"),
        Output("rel-saldo-c2",       "children"),
        Output("rel-saldo-c3",       "children"),
        # Inputs
        Input("filtro-conta",        "value"),
        Input("filtro-data",         "start_date"),
        Input("filtro-data",         "end_date"),
        Input("theme-store",         "data"),
    )
    def atualizar(conta_sel, data_ini, data_fim, tema=None):
        EMPTY = "—"
        tema = tema or "light"

        # ── Banco indisponível ─────────────────────────────────────────────
        if not _DB_READY:
            aviso = html.Span(
                "⚠️ Execute o ETL para carregar os dados.",
                style={"color": WARNING},
            )
            fig_v = empty_fig("Banco não inicializado — execute o ETL primeiro.", theme=tema)
            return (
                aviso,
                EMPTY, EMPTY, EMPTY,
                EMPTY, EMPTY, EMPTY,
                EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY,
                fig_v, fig_v, fig_v,
                fig_v, fig_v,
                "0", EMPTY, EMPTY, EMPTY,
                fig_v, fig_v, fig_v,
                [],
                [],
                EMPTY, EMPTY, EMPTY, EMPTY,
                EMPTY, EMPTY, EMPTY,
                EMPTY, EMPTY, EMPTY,
            )

        conta = conta_sel or None

        # ── Info do ETL ───────────────────────────────────────────────────
        try:
            uc = ultima_carga()
            if uc:
                ts = str(uc["iniciado_em"])[:16].replace("T", " ")
                header_etl = [
                    html.Span("✅ ", style={"color": SUCCESS}),
                    html.Span(f"Última carga: {ts}  ·  "),
                    html.Span(
                        f"{uc['linhas_inseridas']} linhas inseridas",
                        style={"color": TEXT_DIM},
                    ),
                ]
            else:
                header_etl = html.Span(
                    "Nenhuma carga registrada", style={"color": WARNING},
                )
        except Exception:
            header_etl = EMPTY

        # ── Saldos ────────────────────────────────────────────────────────
        try:
            _v1 = saldo_final_conta_1() or 0.0
            _v2 = saldo_final_conta_2() or 0.0
            _v3 = saldo_final_conta_3() or 0.0
            sg       = formata_brl(saldo_final_geral())
            sc1      = formata_brl(_v1)
            sc2      = formata_brl(_v2)
            sc3      = formata_brl(_v3)
            s_cimmvi = formata_brl(_v1 + _v2)
            s_amvi   = formata_brl(_v3)
        except Exception:
            sg = sc1 = sc2 = sc3 = s_cimmvi = s_amvi = EMPTY

        # ── KPIs ──────────────────────────────────────────────────────────
        try:
            kpi_ent    = formata_brl(total_entradas(data_ini, data_fim, conta))
            kpi_sai    = formata_brl(total_saidas(data_ini, data_fim, conta))
            kpi_liq    = formata_brl(total_liquido(data_ini, data_fim, conta), show_sign=True)
            kpi_ab_sai = formata_brl(saidas_em_aberto(conta, data_inicio=data_ini, data_fim=data_fim))
            kpi_ab_ent = formata_brl(entradas_em_aberto(conta, data_inicio=data_ini, data_fim=data_fim))
            kpi_ag     = formata_brl(valor_aguardando_aprovacao(conta, data_inicio=data_ini, data_fim=data_fim))
        except Exception:
            kpi_ent = kpi_sai = kpi_liq = kpi_ab_sai = kpi_ab_ent = kpi_ag = EMPTY

        # ── Gráfico 1: Evolução do saldo mensal ───────────────────────────
        try:
            df_s = evolucao_saldo_mensal(
                conta=conta, data_inicio=data_ini, data_fim=data_fim,
            )
            if df_s.empty:
                fig_saldo = empty_fig(theme=tema)
            else:
                fig_saldo = go.Figure()
                for nome_conta, grp in df_s.groupby("conta"):
                    cor_linha, cor_fill = CONTA_ESTILOS.get(
                        nome_conta, (PRIMARY, "rgba(129,140,248,0.08)"),
                    )
                    grp = grp.sort_values("ano_mes")
                    fig_saldo.add_trace(go.Scatter(
                        x=grp["ano_mes"], y=grp["saldo_acumulado"],
                        name=nome_conta.split(" - ")[-1],
                        mode="lines+markers",
                        line=dict(color=cor_linha, width=2.5),
                        marker=dict(size=5, color=cor_linha),
                        fill="tozeroy", fillcolor=cor_fill,
                        hovertemplate=(
                            "<b>%{x}</b><br>"
                            "Saldo: R$\u00a0%{y:,.2f}<extra></extra>"
                        ),
                    ))
                fig_saldo.update_layout(**chart_layout(
                    theme=tema,
                    yaxis=dict(
                        tickprefix="R$\u00a0", tickformat=",.0f",
                        gridcolor="rgba(150,150,150,0.2)",
                    ),
                ))
        except Exception as ex:
            fig_saldo = empty_fig(f"Erro: {ex}", theme=tema)

        # ── Gráfico 2: Situação (donut) ───────────────────────────────────
        try:
            df_sit = contagem_por_situacao(
                conta=conta,
                data_inicio=data_ini, data_fim=data_fim,
            )
            if df_sit.empty:
                fig_sit = empty_fig(theme=tema)
            else:
                cores = [SITUACAO_CORES.get(s, PRIMARY) for s in df_sit["situacao"]]
                fig_sit = go.Figure(go.Pie(
                    labels=df_sit["situacao"],
                    values=df_sit["total_saidas"],
                    hole=0.54,
                    marker=dict(colors=cores, line=dict(color="rgba(0,0,0,0.1)", width=2)),
                    textinfo="percent",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "R$\u00a0%{value:,.2f}  (%{percent})<extra></extra>"
                    ),
                ))
                fig_sit.update_layout(**chart_layout(
                    theme=tema,
                    margin=dict(l=12, r=12, t=12, b=12),
                    legend=dict(
                        bgcolor="rgba(0,0,0,0)", orientation="v",
                        yanchor="middle", y=0.5, xanchor="left", x=1.0,
                    ),
                    showlegend=True,
                ))
        except Exception as ex:
            fig_sit = empty_fig(f"Erro: {ex}", theme=tema)

        # ── Gráfico 3: Entradas e saídas mensais ──────────────────────────
        try:
            df_m = entradas_saidas_mensais(
                conta=conta,
                data_inicio=data_ini, data_fim=data_fim,
            )
            if df_m.empty:
                fig_mensal = empty_fig(theme=tema)
            else:
                agg = (
                    df_m.groupby("ano_mes", as_index=False)
                    .agg(entradas=("entradas", "sum"), saidas=("saidas", "sum"))
                    .sort_values("ano_mes")
                )
                fig_mensal = go.Figure([
                    go.Bar(
                        name="Entradas", x=agg["ano_mes"], y=agg["entradas"],
                        marker_color=SUCCESS, opacity=0.85,
                        hovertemplate=(
                            "Entradas · <b>%{x}</b><br>"
                            "R$\u00a0%{y:,.2f}<extra></extra>"
                        ),
                    ),
                    go.Bar(
                        name="Saídas", x=agg["ano_mes"], y=agg["saidas"],
                        marker_color=DANGER, opacity=0.85,
                        hovertemplate=(
                            "Saídas · <b>%{x}</b><br>"
                            "R$\u00a0%{y:,.2f}<extra></extra>"
                        ),
                    ),
                ])
                fig_mensal.update_layout(**chart_layout(
                    theme=tema,
                    barmode="group", bargap=0.2,
                    yaxis=dict(
                        tickprefix="R$\u00a0", tickformat=",.0f",
                        gridcolor="rgba(150,150,150,0.2)",
                    ),
                ))
        except Exception as ex:
            fig_mensal = empty_fig(f"Erro: {ex}", theme=tema)

        # ── Gráfico 4: Saídas por categoria (Barras e Pizza) ─────────────
        try:
            df_cat = saidas_por_categoria(
                conta=conta,
                data_inicio=data_ini, data_fim=data_fim,
            )
            df_cat = df_cat[df_cat["total_saidas"] > 0].head(12)
            if df_cat.empty:
                fig_cat = empty_fig(theme=tema)
                fig_cat_pizza = empty_fig(theme=tema)
            else:
                df_cat = df_cat.sort_values("total_saidas", ascending=True)
                cores_cat = (PALETA * 4)[:len(df_cat)]
                fig_cat = go.Figure(go.Bar(
                    x=df_cat["total_saidas"],
                    y=df_cat["categoria"],
                    orientation="h",
                    marker_color=cores_cat,
                    hovertemplate="<b>%{y}</b><br>R$\u00a0%{x:,.2f}<extra></extra>",
                    text=df_cat["total_saidas"].apply(
                        lambda v: f"R$\u00a0{v:,.0f}".replace(",", "X")
                        .replace(".", ",").replace("X", ".")
                    ),
                    textposition="outside",
                ))
                fig_cat.update_layout(**chart_layout(
                    theme=tema,
                    margin=dict(l=12, r=110, t=20, b=12),
                    xaxis=dict(visible=False),
                    showlegend=False,
                    hovermode="y unified",
                ))

                # Rótulos para a legenda com a porcentagem ao lado do nome
                total_saidas_cat = df_cat["total_saidas"].sum()
                labels_legenda = [
                    f"{cat} ({val / total_saidas_cat * 100:.1f}%)" if total_saidas_cat > 0 else str(cat)
                    for cat, val in zip(df_cat["categoria"], df_cat["total_saidas"])
                ]

                # Gráfico de Pizza/Rosca com Porcentagens
                fig_cat_pizza = go.Figure(go.Pie(
                    labels=labels_legenda,
                    values=df_cat["total_saidas"],
                    hole=0.4,
                    marker=dict(colors=cores_cat),
                    textinfo="percent",
                    textposition="inside",
                    hovertemplate="<b>%{label}</b><br>R$\u00a0%{value:,.2f}<extra></extra>",
                ))
                fig_cat_pizza.update_layout(**chart_layout(
                    theme=tema,
                    margin=dict(l=10, r=20, t=20, b=20),
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        y=0.5,
                        yanchor="middle",
                        x=1.02,
                        xanchor="left",
                    ),
                ))
        except Exception as ex:
            fig_cat = empty_fig(f"Erro: {ex}", theme=tema)
            fig_cat_pizza = empty_fig(f"Erro: {ex}", theme=tema)

        # ── Gráfico 5: Forma de pagamento ─────────────────────────────────
        try:
            df_fp = saidas_por_forma_pagamento(
                conta=conta,
                data_inicio=data_ini, data_fim=data_fim,
            )
            if df_fp.empty:
                fig_fp = empty_fig()
            else:
                cores_fp = (PALETA * 4)[:len(df_fp)]
                fig_fp = go.Figure(go.Bar(
                    x=df_fp["total_saidas"],
                    y=df_fp["forma_pagamento"],
                    orientation="h",
                    marker_color=cores_fp,
                    hovertemplate="<b>%{y}</b><br>R$\u00a0%{x:,.2f}<extra></extra>",
                    text=df_fp["total_saidas"].apply(
                        lambda v: f"R$\u00a0{v:,.0f}".replace(",", "X")
                        .replace(".", ",").replace("X", ".")
                    ),
                    textposition="outside",
                    textfont=dict(color=TEXT_DIM, size=11),
                ))
                fig_fp.update_layout(**chart_layout(
                    margin=dict(l=12, r=100, t=20, b=12),
                    xaxis=dict(visible=False, gridcolor=BORDER),
                    yaxis=dict(
                        autorange="reversed",
                        tickfont=dict(color=TEXT_DIM, size=12),
                        gridcolor=BORDER, linecolor=BORDER,
                    ),
                    showlegend=False,
                    hovermode="y unified",
                ))
        except Exception as ex:
            fig_fp = empty_fig(f"Erro: {ex}")

        # ── Gráfico 6: Top 10 maiores saídas ──────────────────────────────
        try:
            df_top = top_saidas(
                n=10, conta=conta,
                data_inicio=data_ini, data_fim=data_fim,
            )
            if df_top.empty:
                fig_top = empty_fig()
            else:
                df_top = df_top.sort_values("saidas", ascending=True)
                df_top["label"] = df_top.apply(
                    lambda r: (
                        str(r.get("descricao") or "—")
                    )[:40].rstrip()
                    + ("…" if len(str(r.get("descricao") or "")) > 40 else ""),
                    axis=1,
                )
                cores_top = [
                    CONTA_ESTILOS.get(c, (DANGER, ""))[0] for c in df_top["conta"]
                ]
                fig_top = go.Figure(go.Bar(
                    x=df_top["saidas"],
                    y=df_top["label"],
                    orientation="h",
                    marker_color=cores_top,
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Saída: R$\u00a0%{x:,.2f}<extra></extra>"
                    ),
                    text=df_top["saidas"].apply(
                        lambda v: f"R$\u00a0{v:,.0f}".replace(",", "X")
                        .replace(".", ",").replace("X", ".")
                    ),
                    textposition="outside",
                    textfont=dict(color=TEXT_DIM, size=10),
                ))
                fig_top.update_layout(**chart_layout(
                    margin=dict(l=12, r=120, t=20, b=12),
                    xaxis=dict(visible=False, gridcolor=BORDER),
                    yaxis=dict(
                        tickfont=dict(color=TEXT_DIM, size=11),
                        gridcolor=BORDER, linecolor=BORDER,
                    ),
                    showlegend=False,
                    hovermode="y unified",
                ))
        except Exception as ex:
            fig_top = empty_fig(f"Erro: {ex}")

        # ── Tabela de lançamentos ──────────────────────────────────────────
        try:
            df_tab = lancamentos_detalhados(
                conta=conta,
                data_inicio=data_ini, data_fim=data_fim,
                tipo_lancamento="MOVIMENTO",
                limit=500,
            )
            if df_tab.empty:
                dados_tabela = []
            else:
                for col in ("entradas", "saidas", "saldo_acumulado"):
                    if col in df_tab.columns:
                        df_tab[col] = df_tab[col].apply(
                            lambda v: round(float(v), 2) if pd.notna(v) else None,
                        )
                if "data_pagamento" in df_tab.columns:
                    df_tab["data_pagamento"] = df_tab["data_pagamento"].apply(
                        lambda v: str(v)[:10] if v else "",
                    )
                if ("parc_atual" in df_tab.columns or "parc_restante" in df_tab.columns) and "parc_total" in df_tab.columns:
                    def _fmt_parc(row):
                        pa = row.get("parc_atual") if pd.notna(row.get("parc_atual")) else row.get("parc_restante")
                        pt = row.get("parc_total")
                        if pd.notna(pa) and pd.notna(pt) and pa > 0:
                            return f"{int(pa)}/{int(pt)}"
                        return ""
                    df_tab["parc_info"] = df_tab.apply(_fmt_parc, axis=1)
                else:
                    df_tab["parc_info"] = ""
                if "categoria" not in df_tab.columns:
                    df_tab["categoria"] = None
                dados_tabela = df_tab.to_dict("records")
        except Exception:
            dados_tabela = []

        # ── Municípios Consorciados (KPIs, Tabela Resumo e 3 Gráficos Indicadores) ──
        try:
            df_adim = adimplencia_municipios(data_inicio=data_ini, data_fim=data_fim)
            if df_adim.empty:
                kpi_muni_total = "0"
                kpi_muni_previsto = EMPTY
                kpi_muni_recebido = EMPTY
                kpi_muni_saldo = EMPTY
                dados_adimplencia = []
                fig_muni_arr = empty_fig("Sem dados de arrecadação", theme=tema)
                fig_muni_adim = empty_fig("Sem dados de adimplência", theme=tema)
                fig_muni_rank = empty_fig("Sem dados de ranking", theme=tema)
            else:
                total_munis = len(df_adim)
                records = []
                tot_prev = 0.0
                tot_rec = 0.0
                tot_saldo = 0.0
                c_adim = 0
                c_inadim = 0

                for _, r in df_adim.iterrows():
                    muni = str(r["municipio"])
                    rec = float(r.get("recebido") or 0.0)
                    pt = int(r.get("parc_total") or 12)
                    pr = r.get("parc_restante")
                    pa = r.get("parc_atual")
                    adim = int(r.get("adimplente") or 0)
                    qp = int(r.get("qtd_pagas") or 0)

                    if pd.notna(pr):
                        p_pagas = max(1, pt - int(pr))
                    elif pd.notna(pa):
                        p_pagas = max(1, int(pa))
                    else:
                        p_pagas = max(1, qp)

                    if rec > 0:
                        val_parc = rec / p_pagas
                        prev = max(rec, val_parc * pt)
                    else:
                        prev = 0.0

                    saldo = max(0.0, prev - rec)

                    tot_rec += rec
                    tot_prev += prev
                    tot_saldo += saldo

                    if adim == 1:
                        c_adim += 1
                    else:
                        c_inadim += 1

                    if pd.notna(pa) and pd.notna(pt):
                        p_info = f"{int(pa)}/{int(pt)}"
                    elif pd.notna(pr) and pd.notna(pt):
                        p_info = f"{int(pt - pr)}/{int(pt)}"
                    else:
                        p_info = f"{p_pagas}/{pt}"

                    status_str = "✅ Adimplente" if adim == 1 else "❌ Inadimplente"

                    records.append({
                        "municipio": muni,
                        "previsto": prev,
                        "recebido": rec,
                        "saldo": saldo,
                        "previsto_fmt": formata_brl(prev),
                        "recebido_fmt": formata_brl(rec),
                        "saldo_fmt": formata_brl(saldo),
                        "parcelas": p_info,
                        "status": status_str,
                        "adimplente": adim,
                    })

                kpi_muni_total = str(total_munis)
                kpi_muni_previsto = formata_brl(tot_prev)
                kpi_muni_recebido = formata_brl(tot_rec)
                kpi_muni_saldo = formata_brl(tot_saldo)
                dados_adimplencia = records

                # Gráfico 1: Valor arrecadado por município (Horizontal Bar Chart)
                df_rec_sort = pd.DataFrame(records).sort_values("recebido", ascending=True)
                fig_muni_arr = go.Figure(go.Bar(
                    x=df_rec_sort["recebido"],
                    y=df_rec_sort["municipio"],
                    orientation="h",
                    marker=dict(
                        color=df_rec_sort["recebido"],
                        colorscale=[[0, "#818cf8"], [1, "#10b981"]],
                        line=dict(color="rgba(0,0,0,0.15)", width=1)
                    ),
                    text=df_rec_sort["recebido"].apply(formata_brl),
                    textposition="outside",
                    textfont=dict(size=10, color=TEXT_DIM),
                    cliponaxis=False,
                    hovertemplate="<b>%{y}</b><br>Arrecadado: R$\u00a0%{x:,.2f}<extra></extra>",
                ))
                fig_muni_arr.update_layout(**chart_layout(
                    theme=tema,
                    margin=dict(l=10, r=220, t=10, b=10),
                    xaxis=dict(visible=False, range=[0, df_rec_sort["recebido"].max() * 1.35]),
                    yaxis=dict(tickfont=dict(size=11, color=TEXT_DIM)),
                    showlegend=False
                ))

                # Gráfico 2: % de Adimplência e Inadimplência (Donut Chart)
                pct_adim = (c_adim / total_munis * 100) if total_munis > 0 else 0
                fig_muni_adim = go.Figure(go.Pie(
                    labels=["Adimplente", "Inadimplente"],
                    values=[c_adim, c_inadim],
                    hole=0.62,
                    marker=dict(colors=[SUCCESS, DANGER], line=dict(color="rgba(0,0,0,0.1)", width=2)),
                    textinfo="percent+label",
                    hovertemplate="<b>%{label}</b><br>%{value} município(s) (%{percent})<extra></extra>",
                ))
                fig_muni_adim.update_layout(**chart_layout(
                    theme=tema,
                    margin=dict(l=10, r=10, t=10, b=10),
                    annotations=[dict(
                        text=f"<b>{pct_adim:.0f}%</b><br><span style='font-size:10px;color:{TEXT_DIM}'>Adimplência</span>",
                        x=0.5, y=0.5, font=dict(size=18, family=FONT, color=TEXT), showarrow=False
                    )],
                    legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
                    showlegend=True
                ))

                # Gráfico 3: Ranking de maior arrecadação (Ranked Bar Chart with badges)
                df_rank = pd.DataFrame(records).sort_values("recebido", ascending=False).reset_index(drop=True)
                df_rank["pct_total"] = (df_rank["recebido"] / tot_rec * 100) if tot_rec > 0 else 0

                def _get_rank_label(idx):
                    muni = df_rank.loc[idx, "municipio"]
                    if idx == 0:
                        return f"🥇 #1 {muni}"
                    elif idx == 1:
                        return f"🥈 #2 {muni}"
                    elif idx == 2:
                        return f"🥉 #3 {muni}"
                    else:
                        return f"#{idx+1} {muni}"

                df_rank["rank_label"] = [_get_rank_label(i) for i in range(len(df_rank))]
                df_rank_sorted = df_rank.sort_values("recebido", ascending=True)

                cores_rank = []
                for lbl in df_rank_sorted["rank_label"]:
                    if "🥇" in lbl:
                        cores_rank.append("#f59e0b")
                    elif "🥈" in lbl:
                        cores_rank.append("#94a3b8")
                    elif "🥉" in lbl:
                        cores_rank.append("#d97706")
                    else:
                        cores_rank.append("#6366f1")

                fig_muni_rank = go.Figure(go.Bar(
                    x=df_rank_sorted["recebido"],
                    y=df_rank_sorted["rank_label"],
                    orientation="h",
                    marker_color=cores_rank,
                    text=df_rank_sorted.apply(lambda r: f"{formata_brl(r['recebido'])} ({r['pct_total']:.1f}%)", axis=1),
                    textposition="outside",
                    textfont=dict(size=10, color=TEXT_DIM),
                    cliponaxis=False,
                    hovertemplate="<b>%{y}</b><br>Arrecadação: R$\u00a0%{x:,.2f}<extra></extra>",
                ))
                fig_muni_rank.update_layout(**chart_layout(
                    theme=tema,
                    margin=dict(l=10, r=240, t=10, b=10),
                    xaxis=dict(visible=False, range=[0, df_rank_sorted["recebido"].max() * 1.45]),
                    yaxis=dict(tickfont=dict(size=11, color=TEXT)),
                    showlegend=False
                ))

        except Exception as ex:
            kpi_muni_total = "0"
            kpi_muni_previsto = kpi_muni_recebido = kpi_muni_saldo = EMPTY
            dados_adimplencia = []
            fig_muni_arr = empty_fig(f"Erro: {ex}", theme=tema)
            fig_muni_adim = empty_fig(f"Erro: {ex}", theme=tema)
            fig_muni_rank = empty_fig(f"Erro: {ex}", theme=tema)

        # ── Valores para a tela Relatórios ────────────────────────────────
        try:
            rel_ent    = formata_brl(total_entradas(data_ini, data_fim, conta))
            rel_sai    = formata_brl(total_saidas(data_ini, data_fim, conta))
            rel_liq    = formata_brl(total_liquido(data_ini, data_fim, conta), show_sign=True)
            rel_saldo  = formata_brl(saldo_final_geral())
            rel_ab_sai = formata_brl(saidas_em_aberto(conta, data_inicio=data_ini, data_fim=data_fim))
            rel_ab_ent = formata_brl(entradas_em_aberto(conta, data_inicio=data_ini, data_fim=data_fim))
            rel_ag     = formata_brl(valor_aguardando_aprovacao(conta, data_inicio=data_ini, data_fim=data_fim))
            _r1 = saldo_final_conta_1() or 0.0
            _r2 = saldo_final_conta_2() or 0.0
            _r3 = saldo_final_conta_3() or 0.0
            rel_sc1 = formata_brl(_r1)
            rel_sc2 = formata_brl(_r2)
            rel_sc3 = formata_brl(_r3)
        except Exception:
            rel_ent = rel_sai = rel_liq = rel_saldo = EMPTY
            rel_ab_sai = rel_ab_ent = rel_ag = EMPTY
            rel_sc1 = rel_sc2 = rel_sc3 = EMPTY

        return (
            header_etl,
            sg, s_cimmvi, s_amvi,
            sc1, sc2, sc3,
            kpi_ent, kpi_sai, kpi_liq, kpi_ab_sai, kpi_ab_ent, kpi_ag,
            fig_saldo, fig_sit, fig_mensal,
            fig_cat, fig_cat_pizza,
            kpi_muni_total, kpi_muni_previsto, kpi_muni_recebido, kpi_muni_saldo,
            fig_muni_arr, fig_muni_adim, fig_muni_rank,
            dados_tabela,
            dados_adimplencia,
            rel_ent, rel_sai, rel_liq, rel_saldo,
            rel_ab_sai, rel_ab_ent, rel_ag,
            rel_sc1, rel_sc2, rel_sc3,
        )
