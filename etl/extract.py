# Extrai os dados da planilha

from pathlib import Path
import pandas as pd
import logging
from config import EXCEL_PATH, SHEETS_CONFIG

logger = logging.getLogger(__name__)

# Tratamento de erros
class PlanilhaNaoEncontradaError(FileNotFoundError):  # excel no caminho errado ou arquivo com nome errado
    pass

class EstruturaInvalidaError(ValueError):  # dispara quando as colunas não batem com o esperado
    pass

def _validar_arquivo(caminho: Path) -> None:
    if not caminho.exists():
        raise PlanilhaNaoEncontradaError(
            f"Arquivo não encontrado: {caminho}\n"
            f"Coloque a planilha em '{caminho}'"
        )

def _validar_colunas(df: pd.DataFrame, aba: str) -> None:
    """Valida se as colunas esperadas para a aba estão presentes no DataFrame.

    Cada aba pode ter um conjunto diferente de colunas (definido em SHEETS_CONFIG).
    A comparação é feita de forma case-insensitive e ignora espaços extras.
    """
    expected = SHEETS_CONFIG[aba].get("expected_columns", [])
    if not expected:
        logger.warning("Aba '%s': nenhuma expected_columns definida, pulando validação.", aba)
        return

    colunas_lidas_norm = [str(c).lower().strip() for c in df.columns]
    faltando = [
        col for col in expected
        if col.lower().strip() not in colunas_lidas_norm
    ]

    if faltando:
        raise EstruturaInvalidaError(
            f"A estrutura de colunas da aba '{aba}' não bate com o esperado.\n"
            f"Colunas faltando: {faltando}\n"
            f"Colunas encontradas: {list(df.columns)}"
        )

def _encontrar_nome_aba_real(path: Path, nome_aba_config: str) -> str:
    """Encontra a aba na planilha correspondente ao nome em SHEETS_CONFIG,
    permitindo pequenas divergências de espaços ou hífens no final.
    """
    try:
        excel_file = pd.ExcelFile(path, engine="openpyxl")
        sheet_names = excel_file.sheet_names
    except Exception as e:
        logger.error("Erro ao ler abas da planilha %s: %s", path, e)
        return nome_aba_config

    if nome_aba_config in sheet_names:
        return nome_aba_config

    norm_target = nome_aba_config.strip().lower().rstrip(" -_")
    for s in sheet_names:
        norm_s = s.strip().lower().rstrip(" -_")
        if norm_s == norm_target or norm_s.startswith(norm_target) or norm_target.startswith(norm_s):
            logger.info("Aba configurada '%s' mapeada para a aba real '%s'", nome_aba_config, s)
            return s

    return nome_aba_config


# Extração de dados
def extrair_dados(nome_aba: str, caminho: str = EXCEL_PATH) -> pd.DataFrame:
    path = Path(caminho)
    _validar_arquivo(path)

    aba_real = _encontrar_nome_aba_real(path, nome_aba)
    header_row = SHEETS_CONFIG[nome_aba].get("header_row", 0)

    logger.info("Lendo aba '%s' (aba real: '%s') de %s", nome_aba, aba_real, path)
    df = pd.read_excel(path, sheet_name=aba_real, header=header_row, engine="openpyxl")

    _validar_colunas(df, nome_aba)

    # Coluna auxiliar com o número da linha original na planilha Excel (para auditoria)
    # +1 pelo cabeçalho consumido pelo pandas, +1 porque o Excel começa em 1
    # +header_row pelas linhas puladas antes do cabeçalho
    df["_linha_planilha"] = df.index + 2 + header_row

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