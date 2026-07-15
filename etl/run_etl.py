# pyrefly: ignore [missing-import]
# etl/run_etl.py
# Ponto de entrada único do pipeline ETL: Extract -> Transform -> Load.
#
# Uso:
#     python -m etl.run_etl
#     python -m etl.run_etl --excel /caminho/outra_planilha.xlsx
#
# A carga é incremental (deduplicada por hash), então rodar várias vezes é seguro.

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import EXCEL_PATH, LOG_LEVEL
from etl.extract import EstruturaInvalidaError, PlanilhaNaoEncontradaError, extrair_todos_os_dados
from etl.load import carregar_dados, criar_schema
from etl.transform import transform_all

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="ETL da planilha financeira CIMMVI/AMVI")
    parser.add_argument(
        "--excel",
        type=Path,
        default=EXCEL_PATH,
        help=f"Caminho da planilha Excel de origem (padrão: {EXCEL_PATH})",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    inicio = time.time()
    logger.info("========== Iniciando pipeline ETL ==========")
    logger.info("Arquivo de origem: %s", args.excel)

    try:
        logger.info("Passo 1/3: criando schema do banco (se necessário)...")
        criar_schema()

        logger.info("Passo 2/3: extraindo dados da planilha...")
        dados_brutos = extrair_todos_os_dados(caminho=str(args.excel))

        logger.info("Passo 3/3: transformando e carregando dados...")
        df_final = transform_all(dados_brutos)
        resumo = carregar_dados(df_final, arquivo_origem=str(args.excel))

        duracao = time.time() - inicio
        logger.info("========== Pipeline concluído em %.1fs ==========", duracao)
        logger.info(
            "Linhas lidas: %d | Inseridas: %d | Ignoradas (já existiam): %d",
            resumo["linhas_lidas"], resumo["linhas_inseridas"], resumo["linhas_ignoradas"],
        )
        return 0

    except (PlanilhaNaoEncontradaError, EstruturaInvalidaError) as exc:
        logger.error("Falha de validação: %s", exc)
        return 1
    except Exception:
        logger.exception("Falha inesperada durante o ETL")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
