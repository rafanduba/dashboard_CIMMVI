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

from dash import Dash

from dashboard.callbacks import registrar_callbacks
from dashboard.layout import criar_layout

logger = logging.getLogger(__name__)


def criar_app() -> Dash:
    """Cria e configura a aplicação Dash."""
    app = Dash(
        __name__,
        title="Dashboard CIMMVI / AMVI",
        update_title=None,
        suppress_callback_exceptions=True,
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