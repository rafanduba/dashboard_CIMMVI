# pyrefly: ignore [missing-import]
# dashboard/queries.py
# Todas as queries SQL usadas pelo dashboard.
# Centralizar aqui evita SQL espalhado pelo código e facilita manutenção.
#
# Cada função usa o "caminho rápido" (leitura direta da view do schema.sql)
# quando não há filtros dinâmicos. Com filtros, monta a query parametrizada.

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parent.parent))
from etl.load import get_engine, criar_schema, garantir_dados_carregados


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _conn():
    """Retorna uma conexão a partir da engine singleton rápida."""
    return get_engine().connect()


def _scalar(sql: str, params: dict | None = None):
    """Executa uma query e retorna o primeiro valor da primeira linha (ou None)."""
    with _conn() as conn:
        row = conn.execute(text(sql), params or {}).fetchone()
        return row[0] if row else None


def _df(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Executa uma query e retorna um DataFrame."""
    with _conn() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def _filtros_periodo(
    data_inicio: str | None,
    data_fim: str | None,
    conta: str | None = None,
    entidade: str | None = None,
) -> tuple[str, dict]:
    """
    Monta a clausula WHERE extra (como string) e o dict de parametros
    correspondentes para filtros de periodo, conta e entidade.

    Retorna ("AND coluna = :param ...", {param: valor, ...})
    """
    clausulas = []
    params: dict = {}

    if data_inicio:
        clausulas.append("AND data_pagamento >= :data_inicio")
        params["data_inicio"] = data_inicio
    if data_fim:
        clausulas.append("AND data_pagamento <= :data_fim")
        params["data_fim"] = data_fim
    if conta:
        clausulas.append("AND conta = :conta")
        params["conta"] = conta
    if entidade:
        clausulas.append("AND entidade = :entidade")
        params["entidade"] = entidade

    return " ".join(clausulas), params


# ===========================================================================
# 1. SALDOS FINAIS
# ===========================================================================

def saldo_final_geral() -> float | None:
    """Saldo acumulado total das 3 contas (ultima data de cada conta)."""
    return _scalar("SELECT vw_saldo_final_geral FROM vw_saldo_final_geral")


def saldo_final_conta_1() -> float | None:
    """Saldo final - CIMMVI Rateio Banco do Brasil."""
    return _scalar("SELECT saldo_final FROM vw_saldo_final_conta_1")


def saldo_final_conta_2() -> float | None:
    """Saldo final - CIMMVI Licenciamento Caixa."""
    return _scalar("SELECT saldo_final FROM vw_saldo_final_conta_2")


def saldo_final_conta_3() -> float | None:
    """Saldo final - AMVI Banco do Brasil CC 439."""
    return _scalar("SELECT saldo_final FROM vw_saldo_final_conta_3")


def saldos_por_conta() -> pd.DataFrame:
    """
    Saldo final de cada conta em um unico DataFrame.
    Usa a view vw_saldos_por_conta (sem filtros dinamicos).

    Colunas: conta, saldo_final
    """
    return _df("SELECT * FROM vw_saldos_por_conta")


# ===========================================================================
# 2. MOVIMENTACAO NO PERIODO
# ===========================================================================

def total_entradas(
    data_inicio: str | None = None,
    data_fim: str | None = None,
    conta: str | None = None,
    entidade: str | None = None,
) -> float:
    """
    Soma das entradas no periodo/conta/entidade informados.
    Considera apenas lancamentos do tipo MOVIMENTO.
    """
    filtros, params = _filtros_periodo(data_inicio, data_fim, conta, entidade)
    sql = f"""
        SELECT COALESCE(SUM(entradas), 0)
        FROM lancamentos
        WHERE tipo_lancamento = 'MOVIMENTO'
          {filtros}
    """
    return _scalar(sql, params) or 0.0


def total_saidas(
    data_inicio: str | None = None,
    data_fim: str | None = None,
    conta: str | None = None,
    entidade: str | None = None,
) -> float:
    """
    Soma das saidas no periodo/conta/entidade informados.
    Considera apenas lancamentos do tipo MOVIMENTO.
    """
    filtros, params = _filtros_periodo(data_inicio, data_fim, conta, entidade)
    sql = f"""
        SELECT COALESCE(SUM(saidas), 0)
        FROM lancamentos
        WHERE tipo_lancamento = 'MOVIMENTO'
          {filtros}
    """
    return _scalar(sql, params) or 0.0


def total_liquido(
    data_inicio: str | None = None,
    data_fim: str | None = None,
    conta: str | None = None,
    entidade: str | None = None,
) -> float:
    """Resultado liquido (entradas - saidas) no periodo."""
    filtros, params = _filtros_periodo(data_inicio, data_fim, conta, entidade)
    sql = f"""
        SELECT COALESCE(SUM(valor_liquido), 0)
        FROM lancamentos
        WHERE tipo_lancamento = 'MOVIMENTO'
          {filtros}
    """
    return _scalar(sql, params) or 0.0


# ===========================================================================
# 3. EVOLUCAO DO SALDO (serie temporal)
# ===========================================================================

def evolucao_saldo_diario(
    conta: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> pd.DataFrame:
    """
    Saldo acumulado por dia, opcionalmente filtrado por conta e periodo.
    Sem filtros: usa a view vw_evolucao_saldo_diario (caminho rapido).

    Colunas: data_pagamento, conta, saldo_acumulado
    """
    if not any([conta, data_inicio, data_fim]):
        return _df("SELECT * FROM vw_evolucao_saldo_diario")

    filtros, params = _filtros_periodo(data_inicio, data_fim, conta)
    sql = f"""
        SELECT
            data_pagamento,
            conta,
            MAX(saldo_acumulado) AS saldo_acumulado
        FROM lancamentos
        WHERE saldo_acumulado IS NOT NULL
          AND data_pagamento IS NOT NULL
          {filtros}
        GROUP BY data_pagamento, conta
        ORDER BY data_pagamento, conta
    """
    return _df(sql, params)


def evolucao_saldo_mensal(
    conta: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> pd.DataFrame:
    """
    Saldo acumulado do ultimo dia de cada mes, opcionalmente filtrado.
    Sem filtros: usa a view vw_evolucao_saldo_mensal (caminho rapido).

    Colunas: ano_mes, conta, saldo_acumulado
    """
    if not any([conta, data_inicio, data_fim]):
        return _df("SELECT * FROM vw_evolucao_saldo_mensal")

    filtros, params = _filtros_periodo(data_inicio, data_fim, conta)
    sql = f"""
        WITH ultimo_dia AS (
            SELECT
                strftime('%Y-%m', data_pagamento) AS ano_mes,
                conta,
                MAX(data_pagamento) AS ultima_data
            FROM lancamentos
            WHERE saldo_acumulado IS NOT NULL
              AND data_pagamento IS NOT NULL
              {filtros}
            GROUP BY ano_mes, conta
        )
        SELECT
            ud.ano_mes,
            ud.conta,
            MAX(l.saldo_acumulado) AS saldo_acumulado
        FROM ultimo_dia ud
        JOIN lancamentos l
          ON l.conta = ud.conta
         AND l.data_pagamento = ud.ultima_data
         AND l.saldo_acumulado IS NOT NULL
        GROUP BY ud.ano_mes, ud.conta
        ORDER BY ud.ano_mes, ud.conta
    """
    return _df(sql, params)


# ===========================================================================
# 4. ENTRADAS E SAIDAS POR MES
# ===========================================================================

def entradas_saidas_mensais(
    conta: str | None = None,
    entidade: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> pd.DataFrame:
    """
    Total de entradas e saidas agrupados por mes.
    Sem filtros: usa a view vw_entradas_saidas_mensais (caminho rapido).

    Colunas: ano_mes, conta, entradas, saidas, liquido
    """
    if not any([conta, entidade, data_inicio, data_fim]):
        return _df("SELECT * FROM vw_entradas_saidas_mensais")

    filtros, params = _filtros_periodo(data_inicio, data_fim, conta, entidade)
    sql = f"""
        SELECT
            strftime('%Y-%m', data_pagamento) AS ano_mes,
            conta,
            COALESCE(SUM(entradas), 0) AS entradas,
            COALESCE(SUM(saidas),  0) AS saidas,
            COALESCE(SUM(valor_liquido), 0) AS liquido
        FROM lancamentos
        WHERE tipo_lancamento = 'MOVIMENTO'
          AND data_pagamento IS NOT NULL
          {filtros}
        GROUP BY ano_mes, conta
        ORDER BY ano_mes, conta
    """
    return _df(sql, params)


# ===========================================================================
# 5. LANCAMENTOS DETALHADOS (tabela)
# ===========================================================================

def lancamentos_detalhados(
    conta: str | None = None,
    entidade: str | None = None,
    situacao: str | None = None,
    tipo_lancamento: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> pd.DataFrame:
    """
    Lista de lancamentos individuais com todos os campos relevantes,
    com suporte a paginacao e multiplos filtros.
    Sempre consulta a tabela diretamente (filtros dinamicos obrigatorios).

    Colunas: id, conta, entidade, banco, data_pagamento, descricao,
             nf_doc, situacao, forma_pagamento, entradas, saidas,
             saldo_acumulado, valor_liquido, tipo_lancamento, observacao
    """
    filtros, params = _filtros_periodo(data_inicio, data_fim, conta, entidade)

    if situacao:
        filtros += " AND situacao = :situacao"
        params["situacao"] = situacao
    if tipo_lancamento:
        filtros += " AND tipo_lancamento = :tipo_lancamento"
        params["tipo_lancamento"] = tipo_lancamento

    params["limit"] = limit
    params["offset"] = offset

    sql = f"""
        SELECT
            id, conta, entidade, banco,
            data_pagamento, descricao, categoria, nf_doc,
            situacao, forma_pagamento,
            parc_atual, parc_restante, parc_total,
            entradas, saidas, saldo_acumulado, valor_liquido,
            tipo_lancamento, observacao
        FROM lancamentos
        WHERE 1=1
          {filtros}
        ORDER BY data_pagamento DESC, linha_planilha DESC
        LIMIT :limit OFFSET :offset
    """
    return _df(sql, params)


# ===========================================================================
# 6. SITUACAO DOS LANCAMENTOS
# ===========================================================================

def contagem_por_situacao(
    conta: str | None = None,
    entidade: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> pd.DataFrame:
    """
    Quantidade e valor total por situacao (Pago, Em aberto, etc.).
    Sem filtros: usa a view vw_contagem_por_situacao (caminho rapido).

    Colunas: situacao, quantidade, total_saidas, total_entradas
    """
    if not any([conta, entidade, data_inicio, data_fim]):
        return _df("SELECT * FROM vw_contagem_por_situacao")

    filtros, params = _filtros_periodo(data_inicio, data_fim, conta, entidade)
    sql = f"""
        SELECT
            COALESCE(situacao, 'Nao informado') AS situacao,
            COUNT(*) AS quantidade,
            COALESCE(SUM(saidas),   0) AS total_saidas,
            COALESCE(SUM(entradas), 0) AS total_entradas
        FROM lancamentos
        WHERE tipo_lancamento = 'MOVIMENTO'
          {filtros}
        GROUP BY situacao
        ORDER BY total_saidas DESC
    """
    return _df(sql, params)


def saidas_em_aberto(
    conta: str | None = None,
    entidade: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> float:
    """
    Total de saidas com situacao 'Em aberto' (opcionalmente filtrado por periodo, conta e entidade).
    Sem filtros: usa a view vw_saidas_em_aberto.
    """
    if not any([conta, entidade, data_inicio, data_fim]):
        return _scalar("SELECT valor_saidas_em_aberto FROM vw_saidas_em_aberto") or 0.0

    filtros, params = _filtros_periodo(data_inicio, data_fim, conta, entidade)
    sql = f"""
        SELECT COALESCE(SUM(saidas), 0)
        FROM lancamentos
        WHERE situacao = 'Em aberto'
          AND tipo_lancamento = 'MOVIMENTO'
          {filtros}
    """
    return _scalar(sql, params) or 0.0


def entradas_em_aberto(
    conta: str | None = None,
    entidade: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> float:
    """
    Total de entradas com situacao 'Em aberto' (opcionalmente filtrado por periodo, conta e entidade).
    Sem filtros: usa a view vw_entradas_em_aberto.
    """
    if not any([conta, entidade, data_inicio, data_fim]):
        return _scalar("SELECT valor_entradas_em_aberto FROM vw_entradas_em_aberto") or 0.0

    filtros, params = _filtros_periodo(data_inicio, data_fim, conta, entidade)
    sql = f"""
        SELECT COALESCE(SUM(entradas), 0)
        FROM lancamentos
        WHERE situacao = 'Em aberto'
          AND tipo_lancamento = 'MOVIMENTO'
          {filtros}
    """
    return _scalar(sql, params) or 0.0


def valor_aguardando_aprovacao(
    conta: str | None = None,
    entidade: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> float:
    """
    Total de saidas com situacao de aguardando aprovacao/pagamento.
    Sem filtros: usa a view vw_valor_aguardando_aprovacao (caminho rapido).
    """
    if not any([conta, entidade, data_inicio, data_fim]):
        return _scalar("SELECT valor_aguardando_aprovacao FROM vw_valor_aguardando_aprovacao") or 0.0

    filtros, params = _filtros_periodo(data_inicio, data_fim, conta, entidade)
    sql = f"""
        SELECT COALESCE(SUM(saidas), 0)
        FROM lancamentos
        WHERE situacao IN (
                'Aguardando Aprovação',
                'Aprovado - Aguardando Pagamento',
                'Pagamento Realizado - Aguardando autorização Margarete'
              )
          AND tipo_lancamento = 'MOVIMENTO'
          {filtros}
    """
    return _scalar(sql, params) or 0.0


# ===========================================================================
# 7. RANKING DE MAIORES SAIDAS / ENTRADAS
# ===========================================================================

def top_saidas(
    n: int = 10,
    conta: str | None = None,
    entidade: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> pd.DataFrame:
    """
    Top N maiores saidas individuais.
    Sempre consulta a tabela (n e filtros sao dinamicos).

    Colunas: data_pagamento, conta, descricao, saidas, situacao, forma_pagamento
    """
    filtros, params = _filtros_periodo(data_inicio, data_fim, conta, entidade)
    params["n"] = n
    sql = f"""
        SELECT
            data_pagamento, conta, descricao, saidas, situacao, forma_pagamento
        FROM lancamentos
        WHERE tipo_lancamento = 'MOVIMENTO'
          AND saidas > 0
          {filtros}
        ORDER BY saidas DESC
        LIMIT :n
    """
    return _df(sql, params)


def top_entradas(
    n: int = 10,
    conta: str | None = None,
    entidade: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> pd.DataFrame:
    """
    Top N maiores entradas individuais.
    Sempre consulta a tabela (n e filtros sao dinamicos).

    Colunas: data_pagamento, conta, descricao, entradas, situacao, forma_pagamento
    """
    filtros, params = _filtros_periodo(data_inicio, data_fim, conta, entidade)
    params["n"] = n
    sql = f"""
        SELECT
            data_pagamento, conta, descricao, entradas, situacao, forma_pagamento
        FROM lancamentos
        WHERE tipo_lancamento = 'MOVIMENTO'
          AND entradas > 0
          {filtros}
        ORDER BY entradas DESC
        LIMIT :n
    """
    return _df(sql, params)


# ===========================================================================
# 8. FORMA DE PAGAMENTO
# ===========================================================================

def saidas_por_forma_pagamento(
    conta: str | None = None,
    entidade: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> pd.DataFrame:
    """
    Total de saidas agrupado por forma de pagamento.
    Sem filtros: usa a view vw_saidas_por_forma_pagamento (caminho rapido).

    Colunas: forma_pagamento, total_saidas, quantidade
    """
    if not any([conta, entidade, data_inicio, data_fim]):
        return _df("SELECT * FROM vw_saidas_por_forma_pagamento")

    filtros, params = _filtros_periodo(data_inicio, data_fim, conta, entidade)
    sql = f"""
        SELECT
            COALESCE(forma_pagamento, 'Nao informado') AS forma_pagamento,
            COALESCE(SUM(saidas), 0) AS total_saidas,
            COUNT(*) AS quantidade
        FROM lancamentos
        WHERE tipo_lancamento = 'MOVIMENTO'
          AND saidas > 0
          {filtros}
        GROUP BY forma_pagamento
        ORDER BY total_saidas DESC
    """
    return _df(sql, params)


def saidas_por_categoria(
    conta: str | None = None,
    entidade: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> pd.DataFrame:
    """
    Total de saidas agrupado por categoria.
    Sem filtros: usa a view vw_saidas_por_categoria (caminho rapido).

    Colunas: categoria, total_saidas, total_entradas, quantidade
    """
    if not any([conta, entidade, data_inicio, data_fim]):
        return _df("SELECT * FROM vw_saidas_por_categoria")

    filtros, params = _filtros_periodo(data_inicio, data_fim, conta, entidade)
    sql = f"""
        SELECT
            COALESCE(categoria, 'Não informado') AS categoria,
            COALESCE(SUM(saidas),   0) AS total_saidas,
            COALESCE(SUM(entradas), 0) AS total_entradas,
            COUNT(*) AS quantidade
        FROM lancamentos
        WHERE tipo_lancamento = 'MOVIMENTO'
          {filtros}
        GROUP BY categoria
        ORDER BY total_saidas DESC
    """
    return _df(sql, params)


# ===========================================================================
# 9. AUDITORIA DO ETL
# ===========================================================================

def historico_etl(limit: int = 20) -> pd.DataFrame:
    """
    Ultimas execucoes do ETL registradas na tabela etl_execucoes.

    Colunas: id, iniciado_em, finalizado_em, arquivo_origem,
             status, linhas_lidas, linhas_inseridas, linhas_ignoradas, mensagem_erro
    """
    sql = """
        SELECT
            id, iniciado_em, finalizado_em, arquivo_origem,
            status, linhas_lidas, linhas_inseridas, linhas_ignoradas, mensagem_erro
        FROM etl_execucoes
        ORDER BY id DESC
        LIMIT :limit
    """
    return _df(sql, {"limit": limit})


def ultima_carga() -> dict | None:
    """
    Retorna um dict com os dados da ultima execucao bem-sucedida do ETL,
    ou None se nao houver nenhuma.
    """
    sql = """
        SELECT iniciado_em, arquivo_origem, linhas_inseridas
        FROM etl_execucoes
        WHERE status = 'SUCESSO'
        ORDER BY id DESC
        LIMIT 1
    """
    with _conn() as conn:
        row = conn.execute(text(sql)).fetchone()
    if row is None:
        return None
    return {
        "iniciado_em": row[0],
        "arquivo_origem": row[1],
        "linhas_inseridas": row[2],
    }


# ===========================================================================
# 10. FILTROS DE SUPORTE (valores unicos para dropdowns)
# ===========================================================================

import functools


@functools.lru_cache(maxsize=16)
def contas_disponiveis() -> list[str]:
    """Lista de contas presentes no banco (para dropdowns)."""
    rows = _df("SELECT DISTINCT conta FROM lancamentos WHERE conta IS NOT NULL ORDER BY conta")
    return rows["conta"].tolist()


@functools.lru_cache(maxsize=16)
def entidades_disponiveis() -> list[str]:
    """Lista de entidades presentes no banco (para dropdowns)."""
    rows = _df("SELECT DISTINCT entidade FROM lancamentos WHERE entidade IS NOT NULL ORDER BY entidade")
    return rows["entidade"].tolist()


@functools.lru_cache(maxsize=16)
def situacoes_disponiveis() -> list[str]:
    """Lista de situacoes presentes no banco (para dropdowns)."""
    rows = _df("SELECT DISTINCT situacao FROM lancamentos WHERE situacao IS NOT NULL ORDER BY situacao")
    return rows["situacao"].tolist()


@functools.lru_cache(maxsize=16)
def periodo_disponivel() -> dict:
    """
    Retorna a data minima e maxima dos lancamentos.

    Retorna: {"data_min": "YYYY-MM-DD", "data_max": "YYYY-MM-DD"}
    """
    sql = """
        SELECT
            MIN(data_pagamento) AS data_min,
            MAX(data_pagamento) AS data_max
        FROM lancamentos
        WHERE data_pagamento IS NOT NULL
    """
    with _conn() as conn:
        row = conn.execute(text(sql)).fetchone()
    return {"data_min": row[0], "data_max": row[1]} if row else {}


def limpar_caches_queries():
    """Limpa os caches de memória após uma carga de ETL."""
    contas_disponiveis.cache_clear()
    entidades_disponiveis.cache_clear()
    situacoes_disponiveis.cache_clear()
    periodo_disponivel.cache_clear()


def adimplencia_municipios(data_inicio: str | None = None, data_fim: str | None = None) -> pd.DataFrame:
    """
    Retorna os municípios do Rateio Municipal CIMMVI e seu status de adimplência.

    - recebido: soma real das entradas dentro do período filtrado (valores exatos da planilha).
    - previsto_total: soma de TODOS os lançamentos registrados na planilha (sem filtro de data),
      representando o valor total previsto para o ciclo completo do município.
    """
    filtros = ""
    params = {}
    if data_inicio:
        filtros += " AND data_pagamento >= :data_inicio"
        params["data_inicio"] = data_inicio
    if data_fim:
        filtros += " AND data_pagamento <= :data_fim"
        params["data_fim"] = data_fim

    sql = f"""
        WITH mes_atual AS (
            SELECT CAST(strftime('%m', 'now') AS INTEGER) AS m
        ),
        -- Última linha de cada município (para pegar parc_atual, parc_restante, parc_total)
        ultimos_lancamentos AS (
            SELECT
                TRIM(descricao) AS municipio,
                parc_atual,
                parc_restante,
                COALESCE(parc_total, 12) AS parc_total,
                ROW_NUMBER() OVER(
                    PARTITION BY LOWER(TRIM(descricao))
                    ORDER BY linha_planilha DESC, id DESC
                ) AS rn
            FROM lancamentos
            WHERE conta = 'CIMMVI - Rateio Banco do Brasil'
              AND tipo_lancamento = 'MOVIMENTO'
              AND LOWER(TRIM(categoria)) LIKE '%rateio%'
              AND descricao IS NOT NULL
              AND TRIM(descricao) != ''
        ),
        -- Recebido: soma das entradas efetivamente recebidas no período selecionado
        totais_arrecadados AS (
            SELECT
                LOWER(TRIM(descricao)) AS municipio_key,
                COALESCE(SUM(entradas), 0) AS recebido,
                COUNT(CASE WHEN (situacao = 'Pago' OR entradas > 0) THEN 1 END) AS qtd_pagas
            FROM lancamentos
            WHERE conta = 'CIMMVI - Rateio Banco do Brasil'
              AND tipo_lancamento = 'MOVIMENTO'
              AND LOWER(TRIM(categoria)) LIKE '%rateio%'
              AND descricao IS NOT NULL
              AND TRIM(descricao) != ''
              {filtros}
            GROUP BY LOWER(TRIM(descricao))
        ),
        -- Previsto: soma de TODOS os lançamentos registrados na planilha (sem filtro de data).
        -- Cada linha da planilha tem seu valor real — mesmo que "Em aberto" com entradas=0,
        -- o que já está registrado é usado. Isso evita qualquer fórmula de estimativa no Python.
        totais_previstos AS (
            SELECT
                LOWER(TRIM(descricao)) AS municipio_key,
                COALESCE(SUM(entradas), 0) AS previsto_total
            FROM lancamentos
            WHERE conta = 'CIMMVI - Rateio Banco do Brasil'
              AND tipo_lancamento = 'MOVIMENTO'
              AND LOWER(TRIM(categoria)) LIKE '%rateio%'
              AND descricao IS NOT NULL
              AND TRIM(descricao) != ''
            GROUP BY LOWER(TRIM(descricao))
        )
        SELECT
            u.municipio,
            u.parc_atual,
            u.parc_restante,
            u.parc_total,
            CASE
                WHEN u.parc_restante IS NOT NULL AND u.parc_restante <= (u.parc_total - m.m + 1)
                THEN 1
                ELSE 0
            END AS adimplente,
            COALESCE(t.recebido, 0) AS recebido,
            COALESCE(t.qtd_pagas, 0) AS qtd_pagas,
            COALESCE(p.previsto_total, 0) AS previsto_total
        FROM ultimos_lancamentos u
        CROSS JOIN mes_atual m
        LEFT JOIN totais_arrecadados t ON LOWER(TRIM(u.municipio)) = t.municipio_key
        LEFT JOIN totais_previstos p ON LOWER(TRIM(u.municipio)) = p.municipio_key
        WHERE u.rn = 1
        ORDER BY adimplente DESC, recebido DESC, u.municipio
    """
    return _df(sql, params)


def contratos_rateio_parcelas(data_inicio: str | None = None, data_fim: str | None = None) -> pd.DataFrame:
    """
    Retorna os contratos da conta 'CIMMVI - Rateio Banco do Brasil' (categoria = 'Contratos')
    junto com a parcela atual, restante e total obtidas da última ocorrência de cada contrato.
    """
    filtros = ""
    params = {}
    if data_inicio:
        filtros += " AND data_pagamento >= :data_inicio"
        params["data_inicio"] = data_inicio
    if data_fim:
        filtros += " AND data_pagamento <= :data_fim"
        params["data_fim"] = data_fim

    sql = f"""
        WITH ultimos_contratos AS (
            SELECT
                TRIM(descricao) AS contrato,
                categoria,
                parc_atual,
                parc_restante,
                COALESCE(parc_total, 12) AS parc_total,
                data_pagamento,
                situacao,
                ROW_NUMBER() OVER(
                    PARTITION BY LOWER(TRIM(descricao))
                    ORDER BY linha_planilha DESC, id DESC
                ) AS rn
            FROM lancamentos
            WHERE conta = 'CIMMVI - Rateio Banco do Brasil'
              AND tipo_lancamento = 'MOVIMENTO'
              AND (LOWER(TRIM(categoria)) LIKE '%contrato%' OR LOWER(TRIM(categoria)) LIKE '%convênio%' OR LOWER(TRIM(categoria)) LIKE '%convenio%')
              AND descricao IS NOT NULL
              AND TRIM(descricao) != ''
        ),
        totais_contratos AS (
            SELECT
                TRIM(descricao) AS contrato,
                COALESCE(SUM(saidas), 0) AS total_saidas,
                COALESCE(SUM(entradas), 0) AS total_entradas,
                COUNT(*) AS qtd_lancamentos
            FROM lancamentos
            WHERE conta = 'CIMMVI - Rateio Banco do Brasil'
              AND tipo_lancamento = 'MOVIMENTO'
              AND (LOWER(TRIM(categoria)) LIKE '%contrato%' OR LOWER(TRIM(categoria)) LIKE '%convênio%' OR LOWER(TRIM(categoria)) LIKE '%convenio%')
              AND descricao IS NOT NULL
              AND TRIM(descricao) != ''
              {filtros}
            GROUP BY LOWER(TRIM(descricao))
        )
        SELECT
            u.contrato,
            u.categoria,
            u.parc_atual,
            u.parc_restante,
            u.parc_total,
            u.data_pagamento,
            u.situacao,
            COALESCE(t.total_saidas, 0) AS total_saidas,
            COALESCE(t.total_entradas, 0) AS total_entradas,
            COALESCE(t.qtd_lancamentos, 0) AS qtd_lancamentos
        FROM ultimos_contratos u
        LEFT JOIN totais_contratos t ON LOWER(TRIM(u.contrato)) = LOWER(TRIM(t.contrato))
        WHERE u.rn = 1
        ORDER BY u.contrato
    """
    return _df(sql, params)


# ════════════════════════════════════════════════════════════════════════════
# 11. Vigência de Contratos e Atas (Google Sheets)
# ════════════════════════════════════════════════════════════════════════════

_VIGENCIA_CACHE: dict = {"ts": 0.0, "data": {}}
_VIGENCIA_TTL_SECONDS = 1800  # 30 minutos


def contratos_vigencia() -> dict:
    """
    Carrega os dados de vigência da planilha externa de Contratos/Atas no Google Sheets.

    Retorna um dicionário indexado pelo Objeto do Contrato (em minúsculas) contendo:
      - dias_vencer: int | None (quantidade de dias para vencer)
      - data_vencimento: str
      - situacao: str
      - num_contrato: str
      - objeto_original: str
    """
    import io
    import time
    import urllib.request
    from config import GOOGLE_SHEETS_CONTRATOS_URL

    agora = time.time()
    if agora - _VIGENCIA_CACHE.get("ts", 0) < _VIGENCIA_TTL_SECONDS and _VIGENCIA_CACHE.get("data"):
        return _VIGENCIA_CACHE["data"]

    url = GOOGLE_SHEETS_CONTRATOS_URL
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            conteudo = resp.read().decode("utf-8", errors="replace")

        # Lê a planilha via export CSV do Google Sheets
        df_raw = pd.read_csv(io.StringIO(conteudo), header=None, dtype=str)
        if df_raw.empty:
            return _VIGENCIA_CACHE.get("data", {})

        # Localiza a linha do cabeçalho que contém 'Objeto do Contrato/Ata' ou 'Dias para Vencer'
        header_idx = None
        for idx, row in df_raw.iterrows():
            row_str = " ".join([str(v) for v in row.values if pd.notna(v)]).lower()
            if "objeto do contrato" in row_str or "dias para vencer" in row_str:
                header_idx = idx
                break

        if header_idx is None:
            header_idx = 9  # Fallback padrão (linha 10)

        df = pd.read_csv(io.StringIO(conteudo), skiprows=header_idx, header=0, dtype=str)
        df.columns = [str(c).strip() for c in df.columns]

        col_objeto = None
        col_dias = None
        col_venc = None
        col_sit = None
        col_num = None

        for c in df.columns:
            c_norm = c.lower()
            if "objeto" in c_norm:
                col_objeto = c
            elif "dias para vencer" in c_norm or "dias p/ vencer" in c_norm:
                col_dias = c
            elif "vencimento" in c_norm and "data" in c_norm:
                col_venc = c
            elif "situa" in c_norm:
                col_sit = c
            elif "nº" in c_norm or "numero" in c_norm or "contrato/ata" in c_norm:
                col_num = c

        if not col_objeto or not col_dias:
            return _VIGENCIA_CACHE.get("data", {})

        mapa_vigencia = {}
        for _, row in df.iterrows():
            obj_val = row.get(col_objeto)
            if pd.isna(obj_val) or not str(obj_val).strip():
                continue

            obj_str = str(obj_val).strip()
            dias_raw = row.get(col_dias)

            dias_num = None
            if pd.notna(dias_raw):
                try:
                    # Limpa e converte para inteiro
                    d_clean = str(dias_raw).strip().replace(".", "").replace(",", ".")
                    dias_num = int(float(d_clean))
                except Exception:
                    dias_num = None

            venc_str = str(row.get(col_venc)).strip() if col_venc and pd.notna(row.get(col_venc)) else ""
            sit_str = str(row.get(col_sit)).strip() if col_sit and pd.notna(row.get(col_sit)) else ""
            num_str = str(row.get(col_num)).strip() if col_num and pd.notna(row.get(col_num)) else ""

            info = {
                "dias_vencer": dias_num,
                "data_vencimento": venc_str,
                "situacao_vigencia": sit_str,
                "num_contrato": num_str,
                "objeto_original": obj_str,
            }

            # Chave normalizada em minúsculas
            mapa_vigencia[obj_str.lower()] = info

        _VIGENCIA_CACHE["ts"] = agora
        _VIGENCIA_CACHE["data"] = mapa_vigencia
        return mapa_vigencia

    except Exception:
        return _VIGENCIA_CACHE.get("data", {})


def invalidar_cache_vigencia():
    """Força recarregar os dados do Google Sheets na próxima chamada."""
    _VIGENCIA_CACHE["ts"] = 0.0
    _VIGENCIA_CACHE["data"] = {}

