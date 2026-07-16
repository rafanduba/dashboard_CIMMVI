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
from etl.load import get_engine


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _conn():
    """Retorna uma conexão a partir da engine singleton."""
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
            data_pagamento, descricao, nf_doc, situacao, forma_pagamento,
            entradas, saidas, saldo_acumulado, valor_liquido,
            tipo_lancamento, observacao
        FROM lancamentos
        WHERE 1=1
          {filtros}
        ORDER BY data_pagamento DESC, id DESC
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
) -> float:
    """
    Total de saidas com situacao 'Em aberto' que aparecem APÓS o último 'Pago' da mesma conta.
    Sem filtros: usa a view vw_saidas_em_aberto.
    """
    if not any([conta, entidade]):
        return _scalar("SELECT valor_saidas_em_aberto FROM vw_saidas_em_aberto") or 0.0

    filtros, params = _filtros_periodo(None, None, conta, entidade)
    sql = f"""
        SELECT COALESCE(SUM(l.saidas), 0)
        FROM lancamentos l
        WHERE l.situacao = 'Em aberto'
          AND l.tipo_lancamento = 'MOVIMENTO'
          AND l.id > (
              SELECT COALESCE(MAX(l2.id), -1)
              FROM lancamentos l2
              WHERE l2.conta = l.conta
                AND l2.situacao = 'Pago'
          )
          {filtros.replace('AND conta', 'AND l.conta').replace('AND entidade', 'AND l.entidade')}
    """
    return _scalar(sql, params) or 0.0


def entradas_em_aberto(
    conta: str | None = None,
    entidade: str | None = None,
) -> float:
    """
    Total de entradas com situacao 'Em aberto' que aparecem APÓS o último 'Pago' da mesma conta.
    Sem filtros: usa a view vw_entradas_em_aberto.
    """
    if not any([conta, entidade]):
        return _scalar("SELECT valor_entradas_em_aberto FROM vw_entradas_em_aberto") or 0.0

    filtros, params = _filtros_periodo(None, None, conta, entidade)
    sql = f"""
        SELECT COALESCE(SUM(l.entradas), 0)
        FROM lancamentos l
        WHERE l.situacao = 'Em aberto'
          AND l.tipo_lancamento = 'MOVIMENTO'
          AND l.id > (
              SELECT COALESCE(MAX(l2.id), -1)
              FROM lancamentos l2
              WHERE l2.conta = l.conta
                AND l2.situacao = 'Pago'
          )
          {filtros.replace('AND conta', 'AND l.conta').replace('AND entidade', 'AND l.entidade')}
    """
    return _scalar(sql, params) or 0.0


def valor_aguardando_aprovacao(
    conta: str | None = None,
    entidade: str | None = None,
) -> float:
    """
    Total de saidas com situacao de aguardando aprovacao/pagamento.
    Sem filtros: usa a view vw_valor_aguardando_aprovacao (caminho rapido).
    """
    if not any([conta, entidade]):
        return _scalar("SELECT valor_aguardando_aprovacao FROM vw_valor_aguardando_aprovacao") or 0.0

    filtros, params = _filtros_periodo(None, None, conta, entidade)
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

def contas_disponiveis() -> list[str]:
    """Lista de contas presentes no banco (para dropdowns)."""
    rows = _df("SELECT DISTINCT conta FROM lancamentos WHERE conta IS NOT NULL ORDER BY conta")
    return rows["conta"].tolist()


def entidades_disponiveis() -> list[str]:
    """Lista de entidades presentes no banco (para dropdowns)."""
    rows = _df("SELECT DISTINCT entidade FROM lancamentos WHERE entidade IS NOT NULL ORDER BY entidade")
    return rows["entidade"].tolist()


def situacoes_disponiveis() -> list[str]:
    """Lista de situacoes presentes no banco (para dropdowns)."""
    rows = _df("SELECT DISTINCT situacao FROM lancamentos WHERE situacao IS NOT NULL ORDER BY situacao")
    return rows["situacao"].tolist()


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
