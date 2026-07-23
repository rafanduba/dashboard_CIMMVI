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

# Caminho do schema SQL relativo a este arquivo
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"

# Engine reutilizada entre chamadas (singleton simples)
_engine: Engine | None = None


def get_engine() -> Engine:
    #Retorna (e reaproveita) a engine SQLAlchemy configurada em config.py
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, future=True)
    return _engine


def criar_schema(engine: Engine | None = None) -> None:
    #Executa o sql/schema.sql inteiro (idempotente: usa IF NOT EXISTS / DROP VIEW IF EXISTS)
    engine = engine or get_engine()
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

    logger.info("Schema pronto.")


def _registrar_execucao(engine: Engine, arquivo_origem: str) -> int | None:
    #Insere uma linha na tabela de auditoria com status EM_ANDAMENTO e retorna o id gerado
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO etl_execucoes (arquivo_origem, status) "
                "VALUES (:arquivo, 'EM_ANDAMENTO')"
            ),
            {"arquivo": arquivo_origem},
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
) -> dict:
    """
    Insere as linhas de `df` na tabela `lancamentos`.

    A deduplicação é feita pelo `hash_linha` (UNIQUE no schema): linhas já
    existentes são ignoradas, permitindo rodar o ETL várias vezes sem duplicar dados.

    Retorna um resumo com linhas_lidas, linhas_inseridas e linhas_ignoradas.
    """
    engine = engine or get_engine()
    execucao_id = _registrar_execucao(engine, arquivo_origem)

    try:
        linhas_lidas = len(df)

        # Busca hashes já presentes no banco para filtrar apenas as linhas novas
        with engine.begin() as conn:
            hashes_existentes = {
                row[0]
                for row in conn.execute(text("SELECT hash_linha FROM lancamentos"))
            }

        df_novo = df[~df["hash_linha"].isin(hashes_existentes)]
        linhas_ignoradas = linhas_lidas - len(df_novo)

        if len(df_novo) > 0:
            # Remove colunas auxiliares que não pertencem ao schema da tabela
            df_para_inserir = df_novo.drop(
                columns=["entradas_old", "saidas_old", "obs2_ignorado",
                         "entidade_planilha", "banco_planilha"],
                errors="ignore",
            )
            df_para_inserir.to_sql("lancamentos", engine, if_exists="append", index=False)

        linhas_inseridas = len(df_novo)

        _finalizar_execucao(
            engine,
            execucao_id,
            status="SUCESSO",
            linhas_lidas=linhas_lidas,
            linhas_inseridas=linhas_inseridas,
            linhas_ignoradas=linhas_ignoradas,
        )

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
