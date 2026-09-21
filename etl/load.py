# etl/load.py
# Responsável por:
#   1. Criar o schema do banco (tabelas + views), se ainda não existir.
#   2. Carregar os dados transformados com INSERT incremental, ignorando duplicatas.
#   3. Registrar cada execução na tabela etl_execucoes para auditoria.

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DATABASE_URL

logger = logging.getLogger(__name__)

# Caminho do schema SQL:
# - Em modo .exe (PyInstaller): o arquivo está na pasta temporária de extração (sys._MEIPASS)
#   pois foi incluído via --add-data e extraído automaticamente pelo PyInstaller.
# - Em modo desenvolvimento: caminho relativo ao próprio arquivo load.py.
if getattr(sys, "frozen", False):
    candidatos_schema = [
        Path(sys._MEIPASS) / "sql" / "schema.sql",
        Path(sys.executable).resolve().parent / "sql" / "schema.sql",
    ]
else:
    candidatos_schema = [
        Path(__file__).resolve().parent.parent / "sql" / "schema.sql",
    ]

SCHEMA_PATH = next((p for p in candidatos_schema if p.exists()), candidatos_schema[0])

# Engine reutilizada entre chamadas (singleton simples)
_engine: Engine | None = None
_SCHEMA_CRIADO: bool = False
_DADOS_VERIFICADOS: bool = False


def checkpoint_wal(engine: Engine | None = None) -> None:
    """Executa checkpoint TRUNCATE no WAL do SQLite para consolidar transações no arquivo .db."""
    try:
        eng = engine or get_engine()
        if eng.dialect.name == "sqlite":
            with eng.connect() as conn:
                conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
            logger.info("SQLite WAL checkpoint executado com sucesso.")
    except Exception as exc:
        logger.warning("Falha ao executar SQLite WAL checkpoint: %s", exc)


def get_engine() -> Engine:
    """Retorna (e reaproveita) a engine SQLAlchemy configurada em config.py com otimizações para SQLite."""
    global _engine
    if _engine is None:
        is_sqlite = "sqlite" in DATABASE_URL.lower()
        connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
        _engine = create_engine(DATABASE_URL, future=True, connect_args=connect_args)
        if is_sqlite:
            try:
                with _engine.connect() as conn:
                    conn.execute(text("PRAGMA journal_mode = WAL;"))
                    conn.execute(text("PRAGMA synchronous = NORMAL;"))
                    conn.execute(text("PRAGMA cache_size = -64000;"))
                    conn.execute(text("PRAGMA temp_store = MEMORY;"))
            except Exception as exc:
                logger.warning("Não foi possível aplicar pragmas de performance do SQLite: %s", exc)
    return _engine


def _migrar_schema_se_necessario(engine: Engine) -> None:
    """Detecta e corrige schemas antigos com CHECK constraints rígidos.

    Caso a tabela `lancamentos` tenha o antigo CHECK constraint em
    `forma_pagamento` ou ainda não suporte 'Recebido' e 'Devolvido' em `situacao`,
    a tabela é descartada para ser recriada com o schema atualizado pelo `criar_schema`.
    """
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type='table' AND name='lancamentos'")
            ).fetchone()
            if row and row[0] and ("forma_pagamento IN" in row[0] or "'Recebido'" not in row[0] or "'Devolvido'" not in row[0]):
                logger.warning(
                    "Schema antigo detectado (CHECK constraint desatualizado em situacao ou forma_pagamento). "
                    "Recriando tabela lancamentos com novo schema..."
                )
                with engine.begin() as conn2:
                    conn2.execute(text("DROP TABLE IF EXISTS lancamentos"))
                logger.info("Tabela lancamentos descartada — será recriada com schema atualizado.")
    except Exception as exc:
        logger.warning("Não foi possível verificar/migrar schema: %s", exc)


def criar_schema(engine: Engine | None = None, force: bool = False) -> None:
    """Executa o sql/schema.sql uma única vez por execução para evitar lentidão."""
    global _SCHEMA_CRIADO
    if _SCHEMA_CRIADO and not force:
        return

    engine = engine or get_engine()

    # Migra automaticamente bancos com schema antigo antes de aplicar o novo
    _migrar_schema_se_necessario(engine)

    sql_script = SCHEMA_PATH.read_text(encoding="utf-8")

    logger.info("Criando/atualizando schema a partir de %s", SCHEMA_PATH)
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            # SQLite precisa do executescript da conexão raw para múltiplos statements
            raw_conn = conn.connection.dbapi_connection
            raw_conn.executescript(sql_script)
        else:
            # Outros bancos: separa por ";" e executa um a um
            for statement in sql_script.split(";"):
                statement = statement.strip()
                if statement:
                    conn.execute(text(statement))

    _SCHEMA_CRIADO = True
    logger.info("Schema pronto.")


def executar_etl_completo(engine: Engine | None = None) -> dict:
    """Executa o pipeline ETL completo (Extract -> Transform -> Load) direto do Google Sheets."""
    global _DADOS_VERIFICADOS
    engine = engine or get_engine()
    criar_schema(engine, force=True)

    logger.info("Executando ETL completo a partir do Google Sheets...")
    from etl.extract import extrair_todos_os_dados
    from etl.transform import transform_all

    brutos = extrair_todos_os_dados()
    final = transform_all(brutos)
    resumo = carregar_dados(final, arquivo_origem="google_sheets", engine=engine)
    _DADOS_VERIFICADOS = True
    logger.info("ETL completo concluído com sucesso!")
    return resumo


def garantir_dados_carregados(engine: Engine | None = None, force: bool = False) -> None:
    """Verifica se o banco de dados possui lançamentos.
    Se estiver vazio, tenta restaurar banco embutido do executável ou executa o schema e roda ETL.
    """
    global _DADOS_VERIFICADOS
    if _DADOS_VERIFICADOS and not force:
        return

    import shutil
    from config import DB_PATH

    # Se estiver rodando como executável e o banco estiver zerado ou ausente, restaura o embutido
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = Path(sys._MEIPASS) / "data" / "cimmvi_amvi.db"
        if bundled.exists() and (not DB_PATH.exists() or DB_PATH.stat().st_size == 0):
            try:
                shutil.copy2(bundled, DB_PATH)
                logger.info("Banco embutido restaurado em %s", DB_PATH)
            except Exception as _ce:
                logger.warning("Falha ao restaurar banco embutido: %s", _ce)

    engine = engine or get_engine()
    criar_schema(engine, force=True)

    try:
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM lancamentos")).scalar()
            if count and count > 0:
                _DADOS_VERIFICADOS = True
                return
    except Exception:
        pass

    logger.info("Banco de dados vazio. Executando ETL automático via Google Sheets...")
    try:
        executar_etl_completo(engine=engine)
        _DADOS_VERIFICADOS = True
    except Exception as exc:
        logger.error("Erro no ETL automático: %s", exc, exc_info=True)


def _registrar_execucao(engine: Engine, arquivo_origem: str) -> int | None:
    #Insere uma linha na tabela de auditoria com status EM_ANDAMENTO e retorna o id gerado
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO etl_execucoes (iniciado_em, arquivo_origem, status) "
                "VALUES (:iniciado_em, :arquivo, 'EM_ANDAMENTO')"
            ),
            {"iniciado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "arquivo": arquivo_origem},
        )
        return result.lastrowid if hasattr(result, "lastrowid") else None


def _finalizar_execucao(engine: Engine, execucao_id: int | None, **kwargs) -> None:
    #Atualiza a linha de auditoria com o resultado da execução
    if execucao_id is None:
        return
    kwargs["finalizado_em"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = :{k}" for k in kwargs)
    with engine.begin() as conn:
        conn.execute(
            text(f"UPDATE etl_execucoes SET {set_clause} WHERE id = :id"),
            {**kwargs, "id": execucao_id},
        )


def carregar_dados(
    df: pd.DataFrame,
    arquivo_origem: str = "planilha.xlsx",
    engine: Engine | None = None,
    substituir: bool = True,
) -> dict:
    """
    Insere as linhas de `df` na tabela `lancamentos`.

    Se `substituir=True` (padrão), limpa a tabela `lancamentos` antes de inserir,
    garantindo que qualquer alteração de status ou valor feita no Google Sheets
    seja refletida 100% no banco de dados.

    Retorna um resumo com linhas_lidas, linhas_inseridas e linhas_ignoradas.
    """
    engine = engine or get_engine()
    execucao_id = _registrar_execucao(engine, arquivo_origem)

    try:
        linhas_lidas = len(df)

        df_para_inserir = df.drop(
            columns=["entradas_old", "saidas_old", "obs2_ignorado",
                     "entidade_planilha", "banco_planilha"],
            errors="ignore",
        )

        with engine.begin() as conn:
            if substituir:
                conn.execute(text("DELETE FROM lancamentos"))
                df_novo = df_para_inserir
                linhas_ignoradas = 0
            else:
                hashes_existentes = {
                    row[0]
                    for row in conn.execute(text("SELECT hash_linha FROM lancamentos"))
                }
                df_novo = df_para_inserir[~df_para_inserir["hash_linha"].isin(hashes_existentes)]
                linhas_ignoradas = linhas_lidas - len(df_novo)

            if len(df_novo) > 0:
                df_novo.to_sql("lancamentos", conn, if_exists="append", index=False)

        linhas_inseridas = len(df_novo)

        _finalizar_execucao(
            engine,
            execucao_id,
            status="SUCESSO",
            linhas_lidas=linhas_lidas,
            linhas_inseridas=linhas_inseridas,
            linhas_ignoradas=linhas_ignoradas,
        )

        checkpoint_wal(engine)

        resumo = {
            "linhas_lidas": linhas_lidas,
            "linhas_inseridas": linhas_inseridas,
            "linhas_ignoradas": linhas_ignoradas,
        }
        logger.info("Carga concluída: %s", resumo)
        return resumo

    except Exception as exc:
        _finalizar_execucao(engine, execucao_id, status="ERRO", mensagem_erro=str(exc))
        logger.exception("Erro durante a carga")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from etl.extract import extrair_todos_os_dados
    from etl.transform import transform_all

    criar_schema()
    brutos = extrair_todos_os_dados()
    final = transform_all(brutos)
    print(carregar_dados(final))
