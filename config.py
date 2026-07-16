import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

## Pasta de entradas (planilha)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok = True)

# Nome planilha
EXCEL_FILENAME = os.getenv("EXCEL_FILE", "planilha.xlsx")
# Caminho planilha
EXCEL_PATH = Path(os.getenv("EXCEL_PATH", str(DATA_DIR / EXCEL_FILENAME)))

# Caminho pro banco de dados
DB_PATH = DATA_DIR / "cimmvi_amvi.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Mapeamento das abas da planilha
# Impede falhas por erros de digitação
# Dados fixos por aba (ex: aba da AMVI sempre vai ser a mesma conta, entidade e banco)
SHEETS_CONFIG = {
    "CIMMVI - Rateio Banco do Brasil": {
        "conta": "CIMMVI - Rateio Banco do Brasil",
        "entidade": "CIMMVI",
        "banco": "Banco do Brasil",
    },
    "CIMMVI - Licenciamento Caixa - ": {
        "conta": "CIMMVI - Licenciamento Caixa",
        "entidade": "CIMMVI",
        "banco": "Caixa Econômica Federal",
    },
    "AMVI - Banco do Brasil - CC 439": {
        "conta": "AMVI - Banco do Brasil - CC 439",
        "entidade": "AMVI",
        "banco": "Banco do Brasil",
    },
}

# Nomes das colunas da planilha na ordem que aparecem
# Usado pelo extract.py pra ver se a planilha não mudou

EXPECTED_COLUMNS = [
    "Descrição",       # descrição do lançamento
    "NF/ Nº doc",     # número da nota fiscal / documento
    "Data pagamento",      # data do lançamento
    "Situação",       # Pago / Em aberto / Aguardando Aprovação
    "Entidade",       # CIMMVI / AMVI
    "Forma Pagamento",    # forma de pagamento (Pix, Boleto, ...)
    "Entradas",       # valor de entrada (R$)
    "Saídas",         # valor de saída (R$)
    "Saldo Acumulado",      # saldo acumulado do dia
    "Obs",            # observação 1
    "Obs 2",          # observação 2
    "Banco",          # banco (coluna presente na planilha, hoje sem uso)
]

# Renomeia as colunas da planilha para facilitar o uso no código
# Impede falhas por erros de digitação
RENAME_MAP = {
    "Descrição": "descricao",
    "NF/ Nº doc": "nf_doc",      # espaço após '/' — igual ao EXPECTED_COLUMNS
    "NF/Nº doc": "nf_doc",       # variante sem espaço (fallback)
    "Data pagamento": "data_pagamento",
    "Situação": "situacao",
    "Entidade": "entidade_planilha",  # renomeia para evitar conflito com df["entidade"] fixo
    "Forma Pagamento": "forma_pagamento",
    "Entradas": "entradas",
    "Saídas": "saidas",
    "Saldo Acumulado": "saldo_acumulado",
    "Obs": "obs",
    "Obs 2": "obs2",
    "Banco": "banco_planilha",   # renomeia para evitar conflito com df["banco"] fixo
    "_linha_planilha": "linha_planilha",  # gerado pelo extract.py
}

# Nomes que indicam saldo do dia (em qualquer variação de maiúsculas e minúsculas)
# Usado no transform.py — todos em lowercase pois _classificar_linha faz .lower() antes de comparar
SALDO_DIA_LABELS = {"saldo do dia", "saldo dia"}
# Nomes que indicam saldo inicial
SALDO_INICIAL_LABELS = {"saldo inicial"}


# Define o nível das informações mostradas pelo logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO") # info mostra informações mais básicas
