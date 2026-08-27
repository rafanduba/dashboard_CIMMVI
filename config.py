import os
import sys
from pathlib import Path

# Quando empacotado como .exe (PyInstaller --onefile), os arquivos de código
# ficam em uma pasta temporária (_MEIxxxxxx) que é apagada ao fechar o programa.
# Para garantir que o banco de dados e a pasta data/ persistam ao lado do .exe,
# usamos sys.executable (caminho do .exe) em vez de __file__ (pasta temporária).
if getattr(sys, "frozen", False):
    # Rodando como .exe: usa o diretório onde o .exe está
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # Rodando como script Python normal (desenvolvimento)
    BASE_DIR = Path(__file__).resolve().parent

## Pasta de dados (banco SQLite)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Caminho pro banco de dados
DB_PATH = DATA_DIR / "cimmvi_amvi.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Google Sheets — Planilha Financeira Principal
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "1EYzC435Suhu9aFi6NLNZtr0T6u2w8flPma5_jcDEgzM")
GOOGLE_SHEETS_EXPORT_URL = os.getenv(
    "GOOGLE_SHEETS_EXPORT_URL",
    f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=xlsx",
)

# Google Sheets — Planilha de Controle de Contratos e Atas (Vigência)
GOOGLE_SHEETS_CONTRATOS_ID = os.getenv("GOOGLE_SHEETS_CONTRATOS_ID", "11rtfy7dO31la70Fy48aTUUZDgXY3Aga0")
GOOGLE_SHEETS_CONTRATOS_URL = os.getenv(
    "GOOGLE_SHEETS_CONTRATOS_URL",
    f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_CONTRATOS_ID}/export?format=csv",
)

# Mapeamento das abas da planilha
# Impede falhas por erros de digitação
# Dados fixos por aba (ex: aba da AMVI sempre vai ser a mesma conta, entidade e banco)
# expected_columns: colunas mínimas que devem existir em cada aba (case-insensitive)
SHEETS_CONFIG = {
    "CIMMVI - Rateio Banco do Brasil": {
        "conta": "CIMMVI - Rateio Banco do Brasil",
        "entidade": "CIMMVI",
        "banco": "Banco do Brasil",
        "header_row": 1,  # linha 1 em branco, cabeçalho na linha 2
        "expected_columns": [
            "CATEGORIA", "DESCRIÇÃO", "OBSERVAÇÃO", "Parc. Atual", "Parc. Rest", "Parc. Total",
            "DATA PAGAMENTO", "SITUAÇÃO", "FORMA PAGAMENTO", "MOVIMENTAÇÃO", "SALDO ACUMULADO",
        ],
    },
    "CIMMVI - Licenciamento Caixa - ": {
        "conta": "CIMMVI - Licenciamento Caixa",
        "entidade": "CIMMVI",
        "banco": "Caixa Econômica Federal",
        "header_row": 0,  # cabeçalho direto na linha 1
        "expected_columns": [
            "CATEGORIA", "DESCRIÇÃO", "OBSERVAÇÃO",
            "DATA PAGAMENTO", "SITUAÇÃO", "FORMA PAGAMENTO", "MOVIMENTAÇÃO", "SALDO ACUMULADO",
        ],
    },
    "AMVI - Banco do Brasil - CC 439": {
        "conta": "AMVI - Banco do Brasil - CC 439",
        "entidade": "AMVI",
        "banco": "Banco do Brasil",
        "header_row": 0,  # cabeçalho na linha 1
        "expected_columns": [
            "CATEGORIA", "DESCRIÇÃO", "NF/ Nº doc",
            "DATA PAGAMENTO", "SITUAÇÃO", "FORMA PAGAMENTO", "MOVIMENTAÇÃO", "SALDO ACUMULADO",
        ],
    },
}

# Renomeia as colunas da planilha para facilitar o uso no código
# Impede falhas por erros de digitação
# Inclui variantes dos nomes antigos e novas nomenclaturas para compatibilidade
RENAME_MAP = {
    "CATEGORIA":          "categoria",
    "DESCRIÇÃO":          "descricao",
    "OBSERVAÇÕES":        "observacao",
    "OBSERVAÇÃO":         "observacao",

    # Mapeamentos para coluna de parcela atual / restante
    "PARC.ATUAL":         "parc_atual",
    "PARC.TOTAIS":        "parc_total",
    "PARC. ATUAL":        "parc_atual",
    "PARC. TOTAL":        "parc_total",
    "Parc.Atual":          "parc_atual",
    "Parc.Totais":         "parc_total",
    "Parc. Atual":         "parc_atual",
    "Parc. Total":         "parc_total",

    # Suporte à nova nomenclatura Parc.Rest / Parc. Rest
    "PARC.REST":          "parc_restante",
    "PARC. REST":         "parc_restante",
    "Parc.Rest":          "parc_restante",
    "Parc. Rest":         "parc_restante",
    "Parc Rest":          "parc_restante",
    "PARC REST":          "parc_restante",
    "parc.rest":          "parc_restante",
    "parc. rest":         "parc_restante",
    "parc rest":          "parc_restante",
    "Parc.A":             "parc_atual",

    "DATA PAGAMENTO":     "data_pagamento",
    "SITUAÇÃO":           "situacao",
    "FORMA PAGAMENTO":    "forma_pagamento",
    "MOVIMENTAÇÃO":       "movimentacao",   # positivo=entrada, negativo=saída
    "SALDO ACUMULADO":    "saldo_acumulado",

    # ----- Formato antigo (fallback) -----
    "Descrição":          "descricao",
    "NF/ Nº doc":         "nf_doc",
    "NF/Nº doc":          "nf_doc",         # variante sem espaço
    "Data pagamento":     "data_pagamento",
    "Situação":           "situacao",
    "Entidade":           "entidade_planilha",
    "Forma Pagamento":    "forma_pagamento",
    "Entradas":           "entradas_old",    # descartado no transform
    "Saídas":             "saidas_old",      # descartado no transform
    "Saldo Acumulado":    "saldo_acumulado",
    "Obs":                "observacao",
    "Obs 2":              "obs2_ignorado",   # descartado no transform
    "Banco":              "banco_planilha",  # descartado no transform

    # ----- Coluna auxiliar gerada pelo extract.py -----
    "_linha_planilha":    "linha_planilha",
}

# Normalização dos valores de Situação
# Mapeia variações para o valor padrão do banco
# Chaves em lowercase — o transform faz .lower().strip() antes de comparar
SITUACAO_MAP = {
    "pago": "Pago",
    "em aberto": "Em aberto",
    "aprovado - aguardando pagamento": "Aprovado - Aguardando Pagamento",
    "aguardando aprovação": "Aguardando Aprovação",
    "pagamento realizado - aguardando autorização margarete": "Pagamento Realizado - Aguardando autorização Margarete",
}

# Nomes que indicam saldo do dia (em qualquer variação de maiúsculas e minúsculas)
# Usado no transform.py — todos em lowercase pois _classificar_linha faz .lower() antes de comparar
SALDO_DIA_LABELS = {"saldo do dia", "saldo dia"}
# Nomes que indicam saldo inicial
SALDO_INICIAL_LABELS = {"saldo inicial"}

# Define o nível das informações mostradas pelo logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # info mostra informações mais básicas
