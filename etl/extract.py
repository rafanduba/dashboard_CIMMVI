# Extrai os dados da planilha

from pathlib import Path
import pandas as pd
import logging
from config import EXCEL_PATH, EXPECTED_COLUMNS, SHEETS_CONFIG

logger = logging.getLogger(__name__)

# Tratamento de erros
class PlanilhaNaoEncontradaError(FileNotFoundError):  # excel no caminho errado ou arquivo com nome errado
    pass

class EstruturaInvalidaError(ValueError):  # dispara quando as colunas não batem com o esperado
    pass

def _validar_arquivo(caminho:Path) -> None:
    if not caminho.exists():
        raise PlanilhaNaoEncontradaError(
            f"Arquivo não encontrado: {caminho}\n"
            f"Coloque a planilha em '{caminho}'"
        )

def _validar_colunas(df: pd.DataFrame, aba: str) -> None:
    colunas_lidas = list(df.columns[: len(EXPECTED_COLUMNS)])
    if [c.lower() for c in colunas_lidas] != [c.lower() for c in EXPECTED_COLUMNS]:
        raise EstruturaInvalidaError(
            f"A estrutura de colunas da aba '{aba}' mudou.\n"
            f"Esperado: {EXPECTED_COLUMNS}\n"
            f"Recebido: {colunas_lidas}"
        )

# Extração de dados
def extrair_dados(nome_aba: str, caminho: str = EXCEL_PATH) -> pd.DataFrame:
    path = Path(caminho)
    _validar_arquivo(path)

    logger.info("Lendo aba '%s' de %s", nome_aba, path)
    df = pd.read_excel(path, sheet_name=nome_aba, header=0, engine="openpyxl")

    _validar_colunas(df, nome_aba)

    # Coluna auxiliar com o número da linha original na planilha Excel (para auditoria)
    # +2: +1 pelo cabeçalho consumido pelo pandas, +1 porque o Excel começa em 1
    df["_linha_planilha"] = df.index + 2

    logger.info("Aba '%s': %d linhas extraídas.", nome_aba, len(df))
    return df


def extrair_todos_os_dados(caminho: str = EXCEL_PATH) -> dict[str, pd.DataFrame]:
    """Extrai todas as abas configuradas em SHEETS_CONFIG, uma por vez.
    Chama extrair_dados() para cada aba listada em SHEETS_CONFIG e retorna
    um dicionário {nome_da_aba: DataFrame}.
    """
    resultado: dict[str, pd.DataFrame] = {}
    for nome_aba in SHEETS_CONFIG:
        resultado[nome_aba] = extrair_dados(nome_aba, caminho)
    return resultado


if __name__ == "__main__":  # esse bloco só roda se executar o arquivo diretamente, pra testes
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    dados = extrair_todos_os_dados()
    for nome, df in dados.items():
        print(f"\n=== {nome} ===")
        print(df.head())
        print(f"Total de linhas: {len(df)}")