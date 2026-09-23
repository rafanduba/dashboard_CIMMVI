"""Ponto de entrada do dashboard Dash — CIMMVI / AMVI.

Uso (a partir da raiz do projeto):
    python dashboard/app.py
    python -m dashboard.app
"""

import logging
import sys
from pathlib import Path

# Garante que a raiz do projeto esteja no path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Carrega variáveis do arquivo .env (se existir) — ex: GEMINI_API_KEY
try:
    from dotenv import load_dotenv  # type: ignore[import]
    _env_file = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(_env_file, override=False)
except ImportError:
    pass  # python-dotenv não instalado; variáveis do sistema são usadas

from dash import Dash

from dashboard.callbacks import registrar_callbacks
from etl.load import garantir_dados_carregados

logger = logging.getLogger(__name__)


def criar_app() -> Dash:
    """Cria e configura a aplicação Dash."""
    # Garante que o banco exista e esteja povoado com os dados da planilha
    garantir_dados_carregados()

    from dashboard.layout import criar_layout

    assets_dir = Path(__file__).resolve().parent / "assets"
    app = Dash(
        __name__,
        title="Dashboard CIMMVI / AMVI",
        update_title=None,
        suppress_callback_exceptions=True,
        assets_folder=str(assets_dir),
    )

    app.layout = criar_layout()
    registrar_callbacks(app)

    return app


# ════════════════════════════════════════════════════════════════════════════
# Inicializar
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app = criar_app()
    app.run(debug=True, host="0.0.0.0", port=8050, dev_tools_ui=False)