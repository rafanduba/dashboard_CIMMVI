# pyrefly: ignore [missing-import]
# etl/run_etl.py
# Ponto de entrada único do pipeline ETL: Extract -> Transform -> Load.
#
# Uso:
#     python -m etl.run_etl

import logging
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import LOG_LEVEL
from etl.extract import EstruturaInvalidaError, extrair_todos_os_dados
from etl.load import executar_etl_completo

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    inicio = time.time()

    logger.info("========== Iniciando pipeline ETL (Google Sheets) ==========")

    try:
        resumo = executar_etl_completo()

        duracao = time.time() - inicio
        logger.info("========== Pipeline concluído em %.1fs ==========", duracao)
        logger.info(
            "Linhas lidas: %d | Inseridas: %d | Ignoradas (já existiam): %d",
            resumo["linhas_lidas"], resumo["linhas_inseridas"], resumo["linhas_ignoradas"],
        )
        return 0

    except EstruturaInvalidaError as exc:
        logger.error("Falha de validação: %s", exc)
        return 1
    except Exception:
        logger.exception("Falha inesperada durante o ETL")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
