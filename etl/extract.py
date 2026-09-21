# Extrai os dados da planilha diretamente do Google Sheets.

import io
import logging
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

# Importação estática para garantir empacotamento completo pelo PyInstaller
import openpyxl
import pandas as pd

from config import GOOGLE_SHEETS_EXPORT_URL, SHEETS_CONFIG

logger = logging.getLogger(__name__)


class EstruturaInvalidaError(ValueError):  # dispara quando as colunas não batem com o esperado
    pass


def _criar_contexto_ssl() -> ssl.SSLContext:
    """Cria contexto SSL seguro com fallback para evitar erros de certificados em executáveis Windows."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    try:
        return ssl.create_default_context()
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


def baixar_planilha_google_sheets(url: str = GOOGLE_SHEETS_EXPORT_URL) -> bytes:
    """Baixa o conteúdo em bytes da planilha exportada do Google Sheets (sem cache)."""
    sep = "&" if "?" in url else "?"
    url_nocache = f"{url}{sep}_t={int(time.time())}"
    logger.info("Baixando planilha atualizada diretamente do Google Sheets: %s", url_nocache)
    req = urllib.request.Request(
        url_nocache,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    ctx = _criar_contexto_ssl()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            content = resp.read()
    except Exception as err:
        logger.warning("Tentativa com contexto SSL padrão falhou (%s). Tentando fallback...", err)
        ctx_insecure = ssl.create_default_context()
        ctx_insecure.check_hostname = False
        ctx_insecure.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=30, context=ctx_insecure) as resp:
            content = resp.read()

    logger.info("Planilha baixada com sucesso (%d bytes).", len(content))
    return content


def _obter_excel_file() -> pd.ExcelFile:
    """Baixa a planilha do Google Sheets e retorna um objeto pd.ExcelFile."""
    content = baixar_planilha_google_sheets()
    return pd.ExcelFile(io.BytesIO(content), engine="openpyxl")


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


def _encontrar_nome_aba_real(excel_file: pd.ExcelFile, nome_aba_config: str) -> str:
    """Encontra a aba na planilha correspondente ao nome em SHEETS_CONFIG,
    permitindo pequenas divergências de espaços ou hífens no final.
    """
    sheet_names = excel_file.sheet_names
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
def _detectar_header_row(excel_file: pd.ExcelFile, aba_real: str, expected_columns: list[str], max_scan: int = 15) -> int:
    """
    Varre as primeiras `max_scan` linhas da aba para encontrar a linha que contém
    as colunas obrigatórias (ex: CATEGORIA, MOVIMENTAÇÃO). Retorna o índice (0-based)
    da linha de cabeçalho detectada. Se não encontrar, retorna 0.

    Isso torna o ETL imune a linhas extras inseridas antes do cabeçalho na planilha.
    """
    if not expected_columns:
        return 0

    # Lê sem cabeçalho para poder inspecionar linha a linha
    df_raw = pd.read_excel(excel_file, sheet_name=aba_real, header=None, nrows=max_scan, engine="openpyxl")

    col_targets = [c.lower().strip() for c in expected_columns]

    for i, row in df_raw.iterrows():
        row_values = [str(v).lower().strip() for v in row.values if pd.notna(v)]
        # Considera encontrado quando pelo menos metade das colunas esperadas está na linha
        matches = sum(1 for c in col_targets if any(c in rv for rv in row_values))
        if matches >= max(1, len(col_targets) // 2):
            logger.info("Header detectado automaticamente na linha %d (0-based) da aba '%s'.", i, aba_real)
            return int(i)

    logger.warning("Header não detectado automaticamente em '%s'. Usando linha 0 como fallback.", aba_real)
    return 0


def extrair_dados(nome_aba: str, excel_file: pd.ExcelFile) -> pd.DataFrame:
    aba_real = _encontrar_nome_aba_real(excel_file, nome_aba)
    expected_columns = SHEETS_CONFIG[nome_aba].get("expected_columns", [])

    # Detecta automaticamente a linha do cabeçalho (imune a linhas extras inseridas antes)
    header_row = _detectar_header_row(excel_file, aba_real, expected_columns)

    logger.info("Lendo aba '%s' (aba real: '%s', header na linha %d)", nome_aba, aba_real, header_row)
    df = pd.read_excel(excel_file, sheet_name=aba_real, header=header_row, engine="openpyxl")

    _validar_colunas(df, nome_aba)

    # Coluna auxiliar com o número da linha original na planilha Excel (para auditoria)
    # +1 pelo cabeçalho consumido pelo pandas, +1 porque o Excel começa em 1
    # +header_row pelas linhas puladas antes do cabeçalho
    df["_linha_planilha"] = df.index + 2 + header_row

    logger.info("Aba '%s': %d linhas extraídas.", nome_aba, len(df))
    return df


def extrair_todos_os_dados() -> dict[str, pd.DataFrame]:
    """Extrai todas as abas configuradas em SHEETS_CONFIG diretamente do Google Sheets.
    Retorna um dicionário {nome_da_aba: DataFrame}.
    """
    excel_file = _obter_excel_file()
    resultado: dict[str, pd.DataFrame] = {}
    for nome_aba in SHEETS_CONFIG:
        resultado[nome_aba] = extrair_dados(nome_aba, excel_file=excel_file)
    return resultado


if __name__ == "__main__":  # esse bloco só roda se executar o arquivo diretamente, pra testes
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    dados = extrair_todos_os_dados()
    for nome, df in dados.items():
        print(f"\n=== {nome} ===")
        print(df.head())
        print(f"Total de linhas: {len(df)}")