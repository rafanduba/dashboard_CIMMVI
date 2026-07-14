import pandas as pd
import hashlib
import numpy as np
from config import SALDO_DIA_LABELS, SALDO_INICIAL_LABELS, RENAME_MAP, SHEETS_CONFIG

# normalizar as tabelas pra usar no resto do código
# não altera a tabela em si

def clean_saldo_value(value):
    # Limpa valores de saldo (remove 'R$', ponto e converte pra float)
    if pd.isna(value) or value == "":
        return None
    try:
        # Remove R$, espaços e pontos de milhar
        value = (str(value)
                 .replace("R$", "")
                 .replace(".", "")
                 .replace(",", ".")
                 .strip()
                 )
        return float(value)
    except:
        return None


# classifica em um dos três tipos de lançamento (movimento, saldo inicial, saldo do dia) do sql
def _classificar_linha(descricao: str) -> str: # recebe string, retorna string
    if pd.isna(descricao):
        return "MOVIMENTO"
    descricao_normalizada = descricao.strip().lower()
    if descricao_normalizada in SALDO_INICIAL_LABELS:
        return "SALDO_INICIAL"
    if descricao_normalizada in SALDO_DIA_LABELS:
        return "SALDO_DIA"
    return "MOVIMENTO"


# evita dados duplicados
def _gerar_hash(row: pd.Series) -> str:
    campos = [
        str(row.get("conta")),
        str(row.get("linha_planilha")),
        str(row.get("descricao")),
        str(row.get("data_pagamento")),
        str(row.get("entradas")),
        str(row.get("saidas")),
        str(row.get("saldo_acumulado")),
    ]
    texto = "|".join(campos)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _limpar_numero(valor):
    #Converte para float com 2 casas decimais; retorna None se inválido
    if pd.isna(valor):
        return None
    try:
        return round(float(valor), 2)
    except (TypeError, ValueError):
        return None


def transform_sheet(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    #Transforma o DataFrame bruto de UMA aba aplicando todas as regras de negócio
    #Pega os dados brutos do extract_all_sheets do extract.py

    info = SHEETS_CONFIG[sheet_name]
    df = df.rename(columns=RENAME_MAP).copy()

    # Descarta linhas totalmente vazias
    colunas_chave = ["descricao", "data_pagamento", "entradas", "saidas", "saldo_acumulado"]
    df = df.dropna(how="all", subset=colunas_chave)

    # Metadados fixos da conta (fonte da verdade: config.py)
    df["conta"] = info["conta"]
    df["entidade"] = info["entidade"]
    df["banco"] = info["banco"]

    # Datas
    df["data_pagamento"] = pd.to_datetime(df["data_pagamento"], errors="coerce").dt.date

    # Números
    df["entradas"] = df["entradas"].apply(_limpar_numero)
    df["saidas"] = df["saidas"].apply(_limpar_numero)
    df["saldo_acumulado"] = df["saldo_acumulado"].apply(clean_saldo_value)
    df["valor_liquido"] = (df["entradas"].fillna(0) - df["saidas"].fillna(0)).round(2)

    # Texto: remove espaços extras e normaliza vazio -> None
    for col in ["descricao", "nf_doc", "situacao", "forma_pagamento", "obs", "obs2"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: str(v).strip() if pd.notna(v) else None)

    # Classificação do tipo de lançamento
    df["tipo_lancamento"] = df["descricao"].apply(_classificar_linha)
    df.loc[df["situacao"].isna() & (df["tipo_lancamento"] != "MOVIMENTO"), "situacao"] = "Pago"

    # Hash de deduplicação
    df["hash_linha"] = df.apply(_gerar_hash, axis=1)

    colunas_finais = [
        "conta", "entidade", "banco", "linha_planilha",
        "descricao", "nf_doc", "data_pagamento", "situacao", "forma_pagamento",
        "entradas", "saidas", "saldo_acumulado", "obs", "obs2",
        "tipo_lancamento", "valor_liquido", "hash_linha",
    ]
    # Inclui apenas colunas que existem no df transformado
    colunas_finais = [c for c in colunas_finais if c in df.columns]
    return df[colunas_finais]


def transform_all(dados_brutos: dict) -> pd.DataFrame:
    partes = []
    for sheet_name, df_bruto in dados_brutos.items():
        print(f"[transform] Processando aba: {sheet_name!r}")
        partes.append(transform_sheet(df_bruto, sheet_name))

    if not partes:
        raise ValueError("Nenhuma aba encontrada em dados_brutos.")

    df_final = pd.concat(partes, ignore_index=True)

    # Remove duplicatas exatas (mesmo hash) dentro do próprio arquivo
    antes = len(df_final)
    df_final = df_final.drop_duplicates(subset="hash_linha", keep="first")
    duplicatas = antes - len(df_final)
    if duplicatas:
        print(f"[transform] {duplicatas} linha(s) duplicada(s) removida(s).")

    df_final = df_final.replace({np.nan: None})
    print(f"[transform] Concluído: {len(df_final)} linhas finais.")
    return df_final
