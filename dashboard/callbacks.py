"""Callbacks do dashboard — toda a lógica de atualização."""

import logging

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, html

from dashboard.components import formata_brl, chart_layout, empty_fig
from dashboard.config import (
    BORDER, CONTA_ESTILOS, DANGER, MUTED,
    PALETA, PRIMARY, SITUACAO_CORES, SUCCESS, TEXT_DIM, WARNING,
)

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════
# Queries (com fallback caso o banco não exista)
# ════════════════════════════════════════════════════════════════════════════
try:
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
    )
    _DB_READY = True
except Exception as _e:
    logger.warning("Banco não disponível: %s", _e)
    _DB_READY = False


# ════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════

def _normalizar(conta: str, entidade: str):
    """Converte string vazia → None (sem filtro)."""
    return (conta or None), (entidade or None)


# ════════════════════════════════════════════════════════════════════════════
# Registro dos callbacks
# ════════════════════════════════════════════════════════════════════════════

def registrar_callbacks(app):
    """Registra todos os callbacks no app Dash."""

    @app.callback(
        # Header
        Output("header-etl",         "children"),
        # Hero — saldos globais
        Output("saldo-geral",        "children"),
        Output("saldo-cimmvi",       "children"),
        Output("saldo-amvi",         "children"),
        # Painel — saldo por conta individual
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
        # Gráficos — painel
        Output("chart-saldo",        "figure"),
        Output("chart-situacao",     "figure"),
        Output("chart-mensal",       "figure"),
        # Gráficos — análise
        Output("chart-categoria",    "figure"),
        Output("chart-forma-pgto",   "figure"),
        Output("chart-top-saidas",   "figure"),
        # Tabela
        Output("tabela-lancamentos", "data"),
        # Inputs
        Input("filtro-conta",        "value"),
        Input("filtro-entidade",     "value"),
        Input("filtro-data",         "start_date"),
        Input("filtro-data",         "end_date"),
    )
    def atualizar(conta_sel, entidade_sel, data_ini, data_fim):
        EMPTY = "—"

        # ── Banco indisponível ───────────────────────────────────────────
        if not _DB_READY:
            aviso = html.Span(
                "\u26a0\ufe0f Execute o ETL para carregar os dados.",
                style={"color": WARNING},
            )
            fig_v = empty_fig("Banco não inicializado — execute o ETL primeiro.")
            return (
                aviso,
                EMPTY, EMPTY, EMPTY,
                EMPTY, EMPTY, EMPTY,
                EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY,
                fig_v, fig_v, fig_v,
                fig_v, fig_v, fig_v,
                [],
            )

        conta, entidade = _normalizar(conta_sel, entidade_sel)

        # ── Info do ETL ──────────────────────────────────────────────────
        try:
            uc = ultima_carga()
            if uc:
                ts = str(uc["iniciado_em"])[:16].replace("T", " ")
                header_etl = [
                    html.Span("\u2705 ", style={"color": SUCCESS}),
                    html.Span(f"Última carga: {ts}  \u00b7  "),
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

        # ── Saldos ───────────────────────────────────────────────────────
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

        # ── KPIs ─────────────────────────────────────────────────────────
        try:
            kpi_ent    = formata_brl(total_entradas(data_ini, data_fim, conta, entidade))
            kpi_sai    = formata_brl(total_saidas(data_ini, data_fim, conta, entidade))
            kpi_liq    = formata_brl(total_liquido(data_ini, data_fim, conta, entidade), show_sign=True)
            kpi_ab_sai = formata_brl(saidas_em_aberto(conta, entidade))
            kpi_ab_ent = formata_brl(entradas_em_aberto(conta, entidade))
            kpi_ag     = formata_brl(valor_aguardando_aprovacao(conta, entidade))
        except Exception:
            kpi_ent = kpi_sai = kpi_liq = kpi_ab_sai = kpi_ab_ent = kpi_ag = EMPTY

        # ── Gráfico 1: Evolução do saldo mensal ──────────────────────────
        try:
            df_s = evolucao_saldo_mensal(
                conta=conta, data_inicio=data_ini, data_fim=data_fim,
            )
            if df_s.empty:
                fig_saldo = empty_fig()
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
                    yaxis=dict(
                        tickprefix="R$\u00a0", tickformat=",.0f",
                        gridcolor=BORDER, linecolor=BORDER,
                        tickfont=dict(color=TEXT_DIM, size=11),
                    ),
                ))
        except Exception as ex:
            fig_saldo = empty_fig(f"Erro: {ex}")

        # ── Gráfico 2: Situação (donut) ──────────────────────────────────
        try:
            df_sit = contagem_por_situacao(
                conta=conta, entidade=entidade,
                data_inicio=data_ini, data_fim=data_fim,
            )
            if df_sit.empty:
                fig_sit = empty_fig()
            else:
                cores = [SITUACAO_CORES.get(s, PRIMARY) for s in df_sit["situacao"]]
                fig_sit = go.Figure(go.Pie(
                    labels=df_sit["situacao"],
                    values=df_sit["total_saidas"],
                    hole=0.54,
                    marker=dict(colors=cores, line=dict(color="#0d0f1a", width=2)),
                    textinfo="percent",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "R$\u00a0%{value:,.2f}  (%{percent})<extra></extra>"
                    ),
                ))
                fig_sit.update_layout(**chart_layout(
                    margin=dict(l=12, r=12, t=12, b=12),
                    legend=dict(
                        bgcolor="rgba(0,0,0,0)", orientation="v",
                        font=dict(color=TEXT_DIM, size=10),
                        yanchor="middle", y=0.5, xanchor="left", x=1.0,
                    ),
                    showlegend=True,
                ))
        except Exception as ex:
            fig_sit = empty_fig(f"Erro: {ex}")

        # ── Gráfico 3: Entradas e saídas mensais ─────────────────────────
        try:
            df_m = entradas_saidas_mensais(
                conta=conta, entidade=entidade,
                data_inicio=data_ini, data_fim=data_fim,
            )
            if df_m.empty:
                fig_mensal = empty_fig()
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
                            "Entradas \u00b7 <b>%{x}</b><br>"
                            "R$\u00a0%{y:,.2f}<extra></extra>"
                        ),
                    ),
                    go.Bar(
                        name="Saídas", x=agg["ano_mes"], y=agg["saidas"],
                        marker_color=DANGER, opacity=0.85,
                        hovertemplate=(
                            "Saídas \u00b7 <b>%{x}</b><br>"
                            "R$\u00a0%{y:,.2f}<extra></extra>"
                        ),
                    ),
                ])
                fig_mensal.update_layout(**chart_layout(
                    barmode="group", bargap=0.2,
                    yaxis=dict(
                        tickprefix="R$\u00a0", tickformat=",.0f",
                        gridcolor=BORDER, linecolor=BORDER,
                        tickfont=dict(color=TEXT_DIM, size=11),
                    ),
                ))
        except Exception as ex:
            fig_mensal = empty_fig(f"Erro: {ex}")

        # ── Gráfico 4: Saídas por categoria ──────────────────────────────
        try:
            df_cat = saidas_por_categoria(
                conta=conta, entidade=entidade,
                data_inicio=data_ini, data_fim=data_fim,
            )
            df_cat = df_cat[df_cat["total_saidas"] > 0].head(12)
            if df_cat.empty:
                fig_cat = empty_fig()
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
                    textfont=dict(color=TEXT_DIM, size=10),
                ))
                fig_cat.update_layout(**chart_layout(
                    margin=dict(l=12, r=110, t=20, b=12),
                    xaxis=dict(visible=False, gridcolor=BORDER),
                    yaxis=dict(
                        tickfont=dict(color=TEXT_DIM, size=11),
                        gridcolor=BORDER, linecolor=BORDER,
                    ),
                    showlegend=False,
                    hovermode="y unified",
                ))
        except Exception as ex:
            fig_cat = empty_fig(f"Erro: {ex}")

        # ── Gráfico 5: Forma de pagamento ────────────────────────────────
        try:
            df_fp = saidas_por_forma_pagamento(
                conta=conta, entidade=entidade,
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

        # ── Gráfico 6: Top 10 maiores saídas ─────────────────────────────
        try:
            df_top = top_saidas(
                n=10, conta=conta, entidade=entidade,
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
                    + ("\u2026" if len(str(r.get("descricao") or "")) > 40 else ""),
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

        # ── Tabela de lançamentos ────────────────────────────────────────
        try:
            df_tab = lancamentos_detalhados(
                conta=conta, entidade=entidade,
                data_inicio=data_ini, data_fim=data_fim,
                tipo_lancamento="MOVIMENTO",
                limit=500,
            )
            if df_tab.empty:
                dados_tabela = []
            else:
                # Arredonda valores monetários
                for col in ("entradas", "saidas", "saldo_acumulado"):
                    if col in df_tab.columns:
                        df_tab[col] = df_tab[col].apply(
                            lambda v: round(float(v), 2) if pd.notna(v) else None,
                        )
                # Formata data
                if "data_pagamento" in df_tab.columns:
                    df_tab["data_pagamento"] = df_tab["data_pagamento"].apply(
                        lambda v: str(v)[:10] if v else "",
                    )
                # Formata parcelas: "3/12"
                if "parc_atual" in df_tab.columns and "parc_total" in df_tab.columns:
                    def _fmt_parc(row):
                        pa, pt = row.get("parc_atual"), row.get("parc_total")
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

        return (
            header_etl,
            sg, s_cimmvi, s_amvi,
            sc1, sc2, sc3,
            kpi_ent, kpi_sai, kpi_liq, kpi_ab_sai, kpi_ab_ent, kpi_ag,
            fig_saldo, fig_sit, fig_mensal,
            fig_cat, fig_fp, fig_top,
            dados_tabela,
        )