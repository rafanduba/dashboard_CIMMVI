"""Ponto de entrada para compilação Desktop (PyInstaller) do Dashboard CIMMVI / AMVI.

Executa o servidor Dash localmente e abre a interface automaticamente no navegador padrão.
"""

import logging
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Garante que a raiz do projeto esteja no sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dashboard.app import criar_app

logger = logging.getLogger(__name__)


def abrir_navegador(url: str = "http://127.0.0.1:8050") -> None:
    """Aguarda o servidor iniciar e abre o navegador padrão no endereço indicado."""
    time.sleep(1.5)
    logger.info("Abrindo dashboard no navegador: %s", url)
    webbrowser.open(url)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Thread em segundo plano para abrir a página assim que o servidor subir
    threading.Thread(target=abrir_navegador, daemon=True).start()

    # Inicializa o app Dash e inicia o servidor HTTP local
    app = criar_app()
    app.run(debug=False, host="127.0.0.1", port=8050)


if __name__ == "__main__":
    main()
