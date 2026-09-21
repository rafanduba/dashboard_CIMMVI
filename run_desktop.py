"""Ponto de entrada para compilação Desktop (PyInstaller) do Dashboard CIMMVI / AMVI.

Executa o servidor Dash localmente e abre a interface automaticamente no navegador padrão.
"""

import logging
import os
import shutil
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Importações explícitas para garantir empacotamento completo pelo PyInstaller
import openpyxl
import pandas as pd
import sqlalchemy

# Garante que a raiz do projeto esteja no sys.path
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR, DB_PATH
from dashboard.app import criar_app
from etl.load import checkpoint_wal, garantir_dados_carregados

logger = logging.getLogger(__name__)


def aguardar_servidor(url: str, timeout: float = 60.0, intervalo: float = 0.2) -> bool:
    """Aguarda o servidor HTTP local estar pronto para receber conexões."""
    tempo_inicial = time.time()
    while time.time() - tempo_inicial < timeout:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as resposta:
                if resposta.status in (200, 302, 404):
                    return True
        except Exception:
            time.sleep(intervalo)
    return False


def abrir_navegador(url: str = "http://127.0.0.1:8050") -> None:
    """Aguarda o servidor iniciar completamente e abre o navegador padrão no endereço indicado."""
    if aguardar_servidor(url):
        logger.info("Servidor pronto! Abrindo dashboard no navegador: %s", url)
        webbrowser.open(url)
    else:
        logger.warning("Tempo limite ao aguardar servidor. Abrindo navegador mesmo assim.")
        webbrowser.open(url)


def configurar_logging() -> None:
    """Configura logging em console e em arquivo de log rotativo para depuração com --noconsole."""
    log_file = DATA_DIR / "dashboard_desktop.log"
    handlers = [
        RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=2, encoding="utf-8"),
    ]
    # Se houver stdout/stderr ativo (ex: rodando via prompt)
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )
    logger.info("Inicializando Dashboard Desktop CIMMVI / AMVI...")
    logger.info("Diretório base: %s | Banco de dados: %s", BASE_DIR, DB_PATH)


def main() -> None:
    configurar_logging()

    # Prepara o banco e consolida o WAL antes de levantar o servidor
    try:
        garantir_dados_carregados()
        checkpoint_wal()
    except Exception as exc:
        logger.error("Erro na checagem inicial do banco de dados: %s", exc, exc_info=True)

    # Thread em segundo plano para abrir a página assim que o servidor subir
    threading.Thread(target=abrir_navegador, daemon=True).start()

    # Inicializa o app Dash e inicia o servidor HTTP local
    app = criar_app()
    app.run(debug=False, host="127.0.0.1", port=8050)


if __name__ == "__main__":
    main()

