# pyrefly: ignore [missing-import]
# etl/run_etl.py
# Ponto de entrada único do pipeline ETL: Extract -> Transform -> Load.
#
# Uso:
#     python -m etl.run_etl
#     python -m etl.run_etl --google-sheets
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
from etl.load import carregar_dados, criar_schema, executar_etl_completo
from etl.transform import transform_all

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="ETL da planilha financeira CIMMVI/AMVI")
    parser.add_argument(
        "--excel",
        type=str,
        default=None,
        help="Caminho da planilha Excel local de origem",
    )
    parser.add_argument(
        "--google-sheets",
        action="store_true",
        help="Executar ETL baixando diretamente do Google Sheets",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    inicio = time.time()
    fonte = "google_sheets" if args.google_sheets or not args.excel else args.excel

    logger.info("========== Iniciando pipeline ETL ==========")
    logger.info("Fonte de origem: %s", fonte)

    try:
        resumo = executar_etl_completo(fonte=fonte)

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

