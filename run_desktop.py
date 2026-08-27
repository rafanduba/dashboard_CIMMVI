"""Ponto de entrada para compilação Desktop (PyInstaller) do Dashboard CIMMVI / AMVI.

Executa o servidor Dash localmente e abre a interface automaticamente no navegador padrão.
"""

import logging
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

# Garante que a raiz do projeto esteja no sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dashboard.app import criar_app

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
