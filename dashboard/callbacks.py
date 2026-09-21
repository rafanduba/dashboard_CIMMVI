"""Callbacks do dashboard — toda a lógica de atualização modularizada."""

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
# Queries (funções puras)
# ════════════════════════════════════════════════════════════════════════════
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
    contratos_rateio_parcelas,
    contratos_vigencia,
    invalidar_cache_vigencia,
    limpar_caches_queries,
    periodo_disponivel,
)

_DB_READY = False


def is_db_ready() -> bool:
    """Verifica de forma dinâmica e resiliente se o banco está pronto e com dados."""
    global _DB_READY
    if _DB_READY:
        return True
    try:
        from etl.load import garantir_dados_carregados, get_engine
        from sqlalchemy import text
        garantir_dados_carregados()
        with get_engine().connect() as conn:
            c = conn.execute(text("SELECT COUNT(*) FROM lancamentos")).scalar()
            if c and c > 0:
                _DB_READY = True
                return True
    except Exception as _e:
        logger.warning("Banco ainda não disponível: %s", _e)
    return False


# Tentativa inicial de preparo do banco
try:
    is_db_ready()
except Exception:
    pass


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
EMPTY = "—"


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


def _get_header_etl_info():
    """Gera os elementos de status do ETL para o cabeçalho."""
    if not is_db_ready():
        return html.Span("⚠️ Execute o ETL para carregar os dados.", style={"color": WARNING})
    try:
        uc = ultima_carga()
        if uc:
            ts_raw = str(uc["iniciado_em"])[:16].replace("T", " ")
            try:
                # Formata para pt-BR: DD/MM/YYYY HH:MM
                from datetime import datetime as _dt
                ts = _dt.strptime(ts_raw, "%Y-%m-%d %H:%M").strftime("%d/%m/%Y %H:%M")
            except Exception:
                ts = ts_raw
            origem = uc.get("arquivo_origem", "")
            label_origem = "Google Sheets" if "google_sheets" in str(origem).lower() or "http" in str(origem).lower() else "Planilha Excel"
            return [
                html.Span(className="status-dot-pulse"),
                html.Span(f"{label_origem}: {ts}", style={"fontWeight": "600"}),
                html.Span(f" • {uc['linhas_inseridas']} linhas", style={"opacity": "0.8", "fontSize": "11px", "marginLeft": "4px"}),
            ]
        else:
            return [
                html.Span("⚠️", style={"marginRight": "6px"}),
                html.Span("Nenhuma carga registrada", style={"fontWeight": "500"}),
            ]
    except Exception:
        return EMPTY


# ════════════════════════════════════════════════════════════════════════════
# Registro dos callbacks modularizados
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
        page = ctx.triggered_id.replace("nav-", "")
        return f"/{page}"

    # ── 2. Renderização da página ativa — show/hide ───────────────────────
    @app.callback(
        Output("topbar-title", "children"),
        *[Output(f"page-{p}", "style") for p in _NAV_PAGES],
        *[Output(f"nav-{p}", "className") for p in _NAV_PAGES],
        Input("url", "pathname"),
    )
    def render_page(pathname):
        page = _page_from_url(pathname)
        title = _PAGE_TITLES.get(page, "🏠  Visão Executiva")

        styles = [
            {"display": "block"} if p == page else {"display": "none"}
            for p in _NAV_PAGES
        ]
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

    # ── 4. Alternar Tema Claro / Escuro ──────────────────────────────────
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

    # ── 5. Sincronização Google Sheets & Status no Header ────────────────
    @app.callback(
        Output("header-etl", "children"),
        Output("sync-trigger", "data"),
        Input("btn-sync-sheets", "n_clicks"),
        State("sync-trigger", "data"),
        prevent_initial_call=False,
    )
    def sincronizar_e_atualizar_header(n_clicks_sync, sync_count):
        from dash import ctx
        from etl.load import executar_etl_completo
        new_sync_count = (sync_count or 0)
        if ctx.triggered_id == "btn-sync-sheets" and n_clicks_sync and n_clicks_sync > 0:
            try:
                executar_etl_completo()
                try:
                    invalidar_cache_vigencia()
                    limpar_caches_queries()
                except Exception:
                    pass
                global _DB_READY
                _DB_READY = True
                new_sync_count += 1
            except Exception as exc:
                logger.error("Erro ao sincronizar com Google Sheets: %s", exc)
        return _get_header_etl_info(), new_sync_count

    # ── 6. Visão Executiva: Saldos, KPIs e Gráficos ─────────────────────
    @app.callback(
        # Saldos globais
        Output("saldo-geral",        "children"),
        Output("saldo-cimmvi",       "children"),
        Output("saldo-amvi",         "children"),
        # Saldo por conta
        Output("saldo-c1",           "children"),
        Output("saldo-c2",           "children"),
        Output("saldo-c3",           "children"),
        # KPIs
        Output("kpi-entradas",       "children"),
        Output("kpi-saidas",         "children"),
        Output("kpi-liquido",        "children"),
        Output("kpi-aberto-saidas",  "children"),
        Output("kpi-aberto-ent",     "children"),
        Output("kpi-aguardando",     "children"),
        # Gráficos
        Output("chart-saldo",        "figure"),
        Output("chart-situacao",     "figure"),
        Output("chart-mensal",       "figure"),
        Output("chart-categoria",        "figure"),
        Output("chart-categoria-pizza",  "figure"),
        Input("filtro-conta",        "value"),
        Input("filtro-data",         "start_date"),
        Input("filtro-data",         "end_date"),
        Input("theme-store",         "data"),
        Input("sync-trigger",        "data"),
    )
    def atualizar_visao_executiva(conta_sel, data_ini, data_fim, tema=None, _sync=None):
        tema = tema or "light"
        if not is_db_ready():
            fig_v = empty_fig("Banco não inicializado — execute o ETL primeiro.", theme=tema)
            return (
                EMPTY, EMPTY, EMPTY,
                EMPTY, EMPTY, EMPTY,
                EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY,
                fig_v, fig_v, fig_v, fig_v, fig_v,
            )

        conta = conta_sel or None

        # Saldos
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

        # KPIs
        try:
            kpi_ent    = formata_brl(total_entradas(data_ini, data_fim, conta))
            kpi_sai    = formata_brl(total_saidas(data_ini, data_fim, conta))
            kpi_liq    = formata_brl(total_liquido(data_ini, data_fim, conta), show_sign=True)
            kpi_ab_sai = formata_brl(saidas_em_aberto(conta, data_inicio=data_ini, data_fim=data_fim))
            kpi_ab_ent = formata_brl(entradas_em_aberto(conta, data_inicio=data_ini, data_fim=data_fim))
            kpi_ag     = formata_brl(valor_aguardando_aprovacao(conta, data_inicio=data_ini, data_fim=data_fim))
        except Exception:
            kpi_ent = kpi_sai = kpi_liq = kpi_ab_sai = kpi_ab_ent = kpi_ag = EMPTY

        # Gráfico: Evolução saldo mensal
        try:
            df_s = evolucao_saldo_mensal(conta=conta, data_inicio=data_ini, data_fim=data_fim)
            if df_s.empty:
                fig_saldo = empty_fig(theme=tema)
            else:
                fig_saldo = go.Figure()
                for nome_conta, grp in df_s.groupby("conta"):
                    cor_linha, cor_fill = CONTA_ESTILOS.get(nome_conta, (PRIMARY, "rgba(129,140,248,0.08)"))
                    grp = grp.sort_values("ano_mes")
                    fig_saldo.add_trace(go.Scatter(
                        x=grp["ano_mes"], y=grp["saldo_acumulado"],
                        name=nome_conta.split(" - ")[-1],
                        mode="lines+markers",
                        line=dict(color=cor_linha, width=2.5),
                        marker=dict(size=5, color=cor_linha),
                        fill="tozeroy", fillcolor=cor_fill,
                        hovertemplate="<b>%{x}</b><br>Saldo: R$\u00a0%{y:,.2f}<extra></extra>",
                    ))
                fig_saldo.update_layout(**chart_layout(
                    theme=tema,
                    yaxis=dict(tickprefix="R$\u00a0", tickformat=",.0f", gridcolor="rgba(150,150,150,0.2)"),
                ))
        except Exception as ex:
            fig_saldo = empty_fig(f"Erro: {ex}", theme=tema)

        # Gráfico: Situação
        try:
            df_sit = contagem_por_situacao(conta=conta, data_inicio=data_ini, data_fim=data_fim)
            if df_sit.empty:
                fig_sit = empty_fig(theme=tema)
            else:
                df_sit = df_sit.copy()
                df_sit["volume"] = df_sit["total_saidas"] + df_sit["total_entradas"]
                if df_sit["volume"].sum() == 0:
                    df_sit["volume"] = df_sit["quantidade"]
                df_sit = df_sit[df_sit["volume"] > 0]

                cores = [SITUACAO_CORES.get(s, PRIMARY) for s in df_sit["situacao"]]
                hover_text = []
                for _, r in df_sit.iterrows():
                    sit_nome = r["situacao"]
                    qtd = int(r["quantidade"])
                    val = float(r["volume"])
                    hover_text.append(f"<b>{sit_nome}</b><br>Volume: {formata_brl(val)}<br>Qtd: {qtd} lançamentos<extra></extra>")

                fig_sit = go.Figure(go.Pie(
                    labels=df_sit["situacao"],
                    values=df_sit["volume"],
                    hole=0.54,
                    marker=dict(colors=cores, line=dict(color="rgba(0,0,0,0.1)", width=2)),
                    textinfo="percent",
                    hovertemplate="%{customdata}",
                    customdata=hover_text,
                ))
                fig_sit.update_layout(**chart_layout(
                    theme=tema,
                    margin=dict(l=12, r=12, t=12, b=12),
                    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.0),
                    showlegend=True,
                ))
        except Exception as ex:
            fig_sit = empty_fig(f"Erro: {ex}", theme=tema)

        # Gráfico: Entradas e Saídas mensais
        try:
            df_m = entradas_saidas_mensais(conta=conta, data_inicio=data_ini, data_fim=data_fim)
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
                        hovertemplate="Entradas · <b>%{x}</b><br>R$\u00a0%{y:,.2f}<extra></extra>",
                    ),
                    go.Bar(
                        name="Saídas", x=agg["ano_mes"], y=agg["saidas"],
                        marker_color=DANGER, opacity=0.85,
                        hovertemplate="Saídas · <b>%{x}</b><br>R$\u00a0%{y:,.2f}<extra></extra>",
                    ),
                ])
                fig_mensal.update_layout(**chart_layout(
                    theme=tema,
                    barmode="group", bargap=0.2,
                    yaxis=dict(tickprefix="R$\u00a0", tickformat=",.0f", gridcolor="rgba(150,150,150,0.2)"),
                ))
        except Exception as ex:
            fig_mensal = empty_fig(f"Erro: {ex}", theme=tema)

        # Gráfico: Saídas por categoria
        try:
            df_cat = saidas_por_categoria(conta=conta, data_inicio=data_ini, data_fim=data_fim)
            df_cat = df_cat[df_cat["total_saidas"] > 0].head(12)
            if df_cat.empty:
                fig_cat = empty_fig(theme=tema)
                fig_cat_pizza = empty_fig(theme=tema)
            else:
                df_cat = df_cat.sort_values("total_saidas", ascending=True)
                cores_cat = (PALETA * 4)[:len(df_cat)]
                max_sai = float(df_cat["total_saidas"].max()) if not df_cat.empty else 100.0

                fig_cat = go.Figure(go.Bar(
                    x=df_cat["total_saidas"],
                    y=df_cat["categoria"],
                    orientation="h",
                    marker_color=cores_cat,
                    hovertemplate="<b>%{y}</b><br>Total de saídas: <b>R$\u00a0%{x:,.2f}</b><extra></extra>",
                    text=df_cat["total_saidas"].apply(
                        lambda v: f"R$\u00a0{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    ),
                    textposition="outside",
                    cliponaxis=False,
                ))
                fig_cat.update_layout(**chart_layout(
                    theme=tema,
                    margin=dict(l=12, r=135, t=10, b=12),
                    xaxis=dict(visible=False, showgrid=False, showspikes=False, range=[0, max_sai * 1.30]),
                    yaxis=dict(showgrid=False, showspikes=False, tickfont=dict(size=11)),
                    showlegend=False,
                    hovermode="y",
                ))

                total_saidas_cat = df_cat["total_saidas"].sum()
                labels_legenda = [
                    f"{cat} ({val / total_saidas_cat * 100:.1f}%)" if total_saidas_cat > 0 else str(cat)
                    for cat, val in zip(df_cat["categoria"], df_cat["total_saidas"])
                ]

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
                    legend=dict(orientation="v", y=0.5, yanchor="middle", x=1.02, xanchor="left"),
                ))
        except Exception as ex:
            fig_cat = empty_fig(f"Erro: {ex}", theme=tema)
            fig_cat_pizza = empty_fig(f"Erro: {ex}", theme=tema)

        return (
            sg, s_cimmvi, s_amvi,
            sc1, sc2, sc3,
            kpi_ent, kpi_sai, kpi_liq, kpi_ab_sai, kpi_ab_ent, kpi_ag,
            fig_saldo, fig_sit, fig_mensal,
            fig_cat, fig_cat_pizza,
        )

    # ── 7. Municípios Consorciados ─────────────────────────────────────────
    @app.callback(
        Output("kpi-muni-total",         "children"),
        Output("kpi-muni-previsto",      "children"),
        Output("kpi-muni-recebido",      "children"),
        Output("kpi-muni-saldo",         "children"),
        Output("chart-municipios-arrecadacao", "figure"),
        Output("chart-municipios-adimplencia", "figure"),
        Output("chart-municipios-ranking",     "figure"),
        Output("tabela-adimplencia", "data"),
        Output("tabela-lancamentos", "data"),
        Input("filtro-data",         "start_date"),
        Input("filtro-data",         "end_date"),
        Input("theme-store",         "data"),
        Input("sync-trigger",        "data"),
    )
    def atualizar_municipios_consorciados(data_ini, data_fim, tema=None, _sync=None):
        tema = tema or "light"
        if not is_db_ready():
            fig_v = empty_fig("Banco não inicializado — execute o ETL primeiro.", theme=tema)
            return "0", EMPTY, EMPTY, EMPTY, fig_v, fig_v, fig_v, [], []

        # Tabela lançamentos
        try:
            df_tab = lancamentos_detalhados(
                conta=None, data_inicio=data_ini, data_fim=data_fim,
                tipo_lancamento="MOVIMENTO", limit=500,
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
                    def _fmt_dt(v):
                        if pd.notna(v) and v:
                            try:
                                return pd.to_datetime(v).strftime("%d/%m/%Y")
                            except Exception:
                                return str(v)[:10]
                        return ""
                    df_tab["data_pagamento"] = df_tab["data_pagamento"].apply(_fmt_dt)
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

        # Municípios
        try:
            df_adim = adimplencia_municipios(data_inicio=data_ini, data_fim=data_fim)
            if df_adim.empty:
                kpi_muni_total = "0"
                kpi_muni_previsto = kpi_muni_recebido = kpi_muni_saldo = EMPTY
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

                    # Determina quantas parcelas foram pagas (com base nos dados da planilha)
                    if pd.notna(pa) and int(pa) > 0:
                        p_pagas = int(pa)
                    elif pd.notna(pr):
                        p_pagas = max(1, pt - int(pr))
                    elif qp > 0:
                        p_pagas = qp
                    else:
                        p_pagas = 1

                    # previsto_sql = soma de TODOS os lançamentos no DB para o município (sem filtro de data).
                    # Pode incluir parcelas que o filtro de categoria do recebido perdeu.
                    previsto_sql = float(r.get("previsto_total") or 0.0)

                    # Usa o maior entre recebido e previsto_sql como base para a média por parcela,
                    # garantindo que parcelas com categoria levemente diferente não sejam perdidas.
                    base_ref = max(rec, previsto_sql)

                    if base_ref > 0 and p_pagas > 0:
                        # Média real por parcela (derivada dos valores reais da planilha) × total do contrato
                        media_parc = base_ref / p_pagas
                        prev = media_parc * pt
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
                        p_info = f"{int(pt) - int(pr)}/{int(pt)}"
                    elif qp > 0:
                        p_info = f"{qp}/{pt}"
                    else:
                        p_info = f"—/{pt}"

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

                # Gráfico 1: Arrecadação
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

                # Gráfico 2: % Adimplência
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

                # Gráfico 3: Ranking
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

        return (
            kpi_muni_total, kpi_muni_previsto, kpi_muni_recebido, kpi_muni_saldo,
            fig_muni_arr, fig_muni_adim, fig_muni_rank,
            dados_adimplencia, dados_tabela,
        )

    # ── 8a. Contratos Rateio — carrega do banco APENAS quando o período muda ──────────
    @app.callback(
        Output("store-contratos-rateio", "data"),
        Input("filtro-contrato-periodo", "start_date"),
        Input("filtro-contrato-periodo", "end_date"),
        Input("filtro-data", "start_date"),
        Input("filtro-data", "end_date"),
        Input("sync-trigger", "data"),
    )
    def carregar_contratos_rateio(dt_ini_c, dt_fim_c, dt_ini_g, dt_fim_g, _sync=None):
        if not is_db_ready():
            return []
        try:
            data_ini = dt_ini_c or dt_ini_g
            data_fim = dt_fim_c or dt_fim_g
            df_cr = contratos_rateio_parcelas(data_inicio=data_ini, data_fim=data_fim)
            if df_cr.empty:
                return []
            return df_cr.to_dict("records")
        except Exception as ex_cr:
            logger.error("Erro ao carregar contratos de rateio: %s", ex_cr)
            return []

    def _obter_info_vigencia(contrato_nome: str, mapa_vig: dict) -> tuple[int | None, str, str]:
        """Retorna (dias_vencer, dias_vencer_fmt, dias_status)."""
        if not contrato_nome or not mapa_vig:
            return None, "—", ""

        nome_clean = contrato_nome.strip().lower()

        # 1. Match direto exato
        info = mapa_vig.get(nome_clean)

        # 2. Substring match (chave contida no nome ou nome contido na chave)
        if not info:
            for chave, dados in mapa_vig.items():
                if chave in nome_clean or nome_clean in chave:
                    info = dados
                    break

        # 3. Match por palavras-chave principais
        if not info:
            stopwords = {"contrato", "administrativo", "empresa", "programa", "termo", "aditivo", "para", "com", "dos", "das", "entre", "si"}
            palavras = [p for p in nome_clean.replace("-", " ").replace("/", " ").replace("º", " ").replace("n°", " ").split() if len(p) >= 3 and p not in stopwords]
            for chave, dados in mapa_vig.items():
                chave_palavras = [p for p in chave.replace("-", " ").replace("/", " ").replace("º", " ").replace("n°", " ").split() if len(p) >= 3 and p not in stopwords]
                inter = set(palavras) & set(chave_palavras)
                if inter:
                    info = dados
                    break

        if not info or info.get("dias_vencer") is None:
            return None, "—", ""

        dias = info["dias_vencer"]
        if dias < 0:
            dias_fmt = f"{dias} d (Vencido)"
            status = "vencido"
        elif dias <= 30:
            dias_fmt = f"{dias} d (Crítico)"
            status = "alerta"
        else:
            dias_fmt = f"{dias} dias"
            status = "ok"

        return dias, dias_fmt, status

    # ── 8b. Contratos Rateio — aplica filtros locais em memória (sem bater no banco) ──
    @app.callback(
        Output("tabela-contratos-rateio", "data"),
        Output("filtro-contrato-categoria", "options"),
        Input("store-contratos-rateio", "data"),
        Input("filtro-contrato-categoria", "value"),
        Input("filtro-contrato-parcelas", "value"),
        Input("filtro-contrato-busca", "value"),
    )
    def atualizar_contratos_rateio(dados_brutos, cat_sel, parc_sel, busca_txt):
        default_opts = [{"label": "Todas as categorias", "value": ""}]
        if not dados_brutos:
            return [], default_opts
        try:
            df_cr = pd.DataFrame(dados_brutos)

            # Busca dados de vigência da planilha externa Google Sheets
            try:
                mapa_vig = contratos_vigencia() or {}
            except Exception as e_vig:
                logger.warning("Não foi possível carregar vigência dos contratos: %s", e_vig)
                mapa_vig = {}

            # ── 1. Atualiza dinamicamente as Opções de Categoria (Sem hardcoding) ──
            if "categoria" in df_cr.columns:
                raw_cats = df_cr["categoria"].dropna().unique()
                cats_unicas = sorted(list(set(str(c).strip() for c in raw_cats if str(c).strip())))
            else:
                cats_unicas = []

            cat_options = default_opts + [{"label": c, "value": c} for c in cats_unicas]

            # ── 2. Filtra por Categoria Selecionada ─────────────────────────
            if cat_sel and str(cat_sel).strip():
                cat_target = str(cat_sel).strip().lower()
                df_cr = df_cr[df_cr["categoria"].astype(str).str.strip().str.lower() == cat_target]

            # ── 3. Filtra por Texto de Busca ─────────────────────────────────
            if busca_txt and str(busca_txt).strip():
                txt = str(busca_txt).strip().lower()
                df_cr = df_cr[df_cr["contrato"].astype(str).str.lower().str.contains(txt, regex=False, na=False)]

            rec_cr = []
            for _, r in df_cr.iterrows():
                contrato_nome = str(r.get("contrato") or "")
                cat_nome = str(r.get("categoria") or "")
                pa = r.get("parc_atual")
                pr = r.get("parc_restante")
                pt = r.get("parc_total")
                sit = str(r.get("situacao") or "\u2014")
                dt_pag = r.get("data_pagamento")
                if pd.notna(dt_pag) and dt_pag:
                    try:
                        dt_str = pd.to_datetime(dt_pag).strftime("%d/%m/%Y")
                    except Exception:
                        dt_str = str(dt_pag)
                else:
                    dt_str = "\u2014"
                tot_sai = float(r.get("total_saidas") or 0.0)

                pa_num = int(pa) if pd.notna(pa) else None
                pr_num = int(pr) if pd.notna(pr) else None
                pt_num = int(pt) if pd.notna(pt) else 12

                if pa_num is not None:
                    pagas = pa_num
                elif pr_num is not None:
                    pagas = max(0, pt_num - pr_num)
                else:
                    pagas = "\u2014"

                restantes = pr_num if pr_num is not None else (max(0, pt_num - pagas) if isinstance(pagas, int) else "\u2014")

                if isinstance(pagas, int):
                    p_info = f"{pagas}/{pt_num} ({restantes} restantes)"
                else:
                    p_info = "\u2014"

                # ── 4. Filtra por Situação de Parcelas ──────────────────────
                if parc_sel == "pendentes":
                    has_pending = False
                    if isinstance(restantes, int) and restantes > 0:
                        has_pending = True
                    elif sit not in ("Pago", "Recebido", "—") and sit != "":
                        has_pending = True
                    if not has_pending:
                        continue
                elif parc_sel == "quitadas":
                    # Só passa quem tem parc_restante explicitamente igual a 0
                    if not (isinstance(restantes, int) and restantes == 0):
                        continue
                elif parc_sel == "sem_parcela":
                    if p_info != "—":
                        continue

                # ── 5. Obtém Vigência (Dias para Vencer) ───────────────────
                dias_num, dias_fmt, dias_st = _obter_info_vigencia(contrato_nome, mapa_vig)

                rec_cr.append({
                    "contrato": contrato_nome,
                    "categoria": cat_nome,
                    "parc_atual": pagas,
                    "parc_restante": restantes,
                    "parc_total": pt_num,
                    "parc_info": p_info,
                    "dias_vencer": dias_num,
                    "dias_vencer_fmt": dias_fmt,
                    "dias_status": dias_st,
                    "total_saidas": tot_sai,
                    "total_saidas_fmt": formata_brl(tot_sai),
                    "data_pagamento": dt_str,
                    "situacao": sit,
                })

            return rec_cr, cat_options

        except Exception as ex_cr:
            logger.error("Erro ao carregar contratos de rateio: %s", ex_cr)
            return [], default_opts

    # ── 9. Atualização dinâmica dos limites de data após sincronização ────────
    @app.callback(
        Output("filtro-data", "min_date_allowed"),
        Output("filtro-data", "max_date_allowed"),
        Output("filtro-contrato-periodo", "min_date_allowed"),
        Output("filtro-contrato-periodo", "max_date_allowed"),
        Input("sync-trigger", "data"),
        prevent_initial_call=True,
    )
    def atualizar_limites_data(_sync):
        if not is_db_ready():
            return no_update, no_update, no_update, no_update
        try:
            p = periodo_disponivel()
            d_min = p.get("data_min")
            d_max = p.get("data_max")
            if d_min and d_max:
                return d_min, d_max, d_min, d_max
        except Exception:
            pass
        return no_update, no_update, no_update, no_update


