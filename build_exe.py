"""Script auxiliador para gerar o arquivo executável (.exe) do Dashboard CIMMVI / AMVI.

Execução:
    python build_exe.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def build() -> None:
    print("🚀 Iniciando a compilação do executável do Dashboard CIMMVI / AMVI...")

    try:
        import PyInstaller.__main__
    except ImportError:
        print("\n❌ PyInstaller não está instalado no seu ambiente Python.")
        print("💡 Para instalar, execute o comando:")
        print("    pip install pyinstaller\n")
        return

    # Separador de caminhos para o --add-data (';' no Windows, ':' no Linux/Mac)
    sep = ";" if sys.platform.startswith("win") else ":"

    cmd_args = [
        str(BASE_DIR / "run_desktop.py"),
        "--name=Dashboard_CIMMVI",
        "--noconfirm",
        "--onedir",  # Gera uma pasta com o executável e dependências
        "--noconsole",  # Oculta a janela de terminal/prompt de comando ao abrir
        "--clean",
        # Inclui a pasta de scripts SQL no executável
        f"--add-data={BASE_DIR / 'sql'}{sep}sql",
        # Inclui os assets visuais do Dash no executável
        f"--add-data={BASE_DIR / 'dashboard' / 'assets'}{sep}dashboard/assets",
    ]

    print("🔧 Parâmetros do PyInstaller:", " ".join(cmd_args))
    PyInstaller.__main__.run(cmd_args)

    dist_path = BASE_DIR / "dist" / "Dashboard_CIMMVI"
    print("\n✅ Compilação concluída com sucesso!")
    print(f"📁 O executável e os arquivos foram gerados em:\n   {dist_path}\n")
    print(f"▶️  Para rodar o programa, execute:\n   {dist_path / 'Dashboard_CIMMVI.exe'}\n")


if __name__ == "__main__":
    build()
