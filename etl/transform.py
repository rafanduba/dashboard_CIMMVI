import pandas as pd
import hashlib
import numpy as np
from config import SALDO_DIA_LABELS, SALDO_INICIAL_LABELS, RENAME_MAP, SHEETS_CONFIG, SITUACAO_MAP

# normalizar as tabelas pra usar no resto do código
# não altera a tabela em si


def clean_saldo_value(value):
    # Limpa valores de saldo (remove 'R$', ponto e converte pra float)
    if pd.isna(value) or value == "":
        return None
    # Se já é numérico (pandas leu direto do Excel como float/int),
    # não aplicar substituição de string — evita remover o ponto decimal
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    try:
        # Formato BR em string: remove R$, pontos de milhar e troca vírgula por ponto
        value = (str(value)
                 .replace("R$", "")
                 .replace(".", "")
                 .replace(",", ".")
                 .strip()
                 )
        return float(value)
    except Exception:
        return None


# classifica em um dos três tipos de lançamento (movimento, saldo inicial, saldo do dia) do sql
def _classificar_linha(descricao: str) -> str:  # recebe string, retorna string
    if pd.isna(descricao):
        return "MOVIMENTO"
    descricao_normalizada = descricao.strip().lower()
    if descricao_normalizada in SALDO_INICIAL_LABELS:
        return "SALDO_INICIAL"
    if descricao_normalizada in SALDO_DIA_LABELS:
        return "SALDO_DIA"
    return "MOVIMENTO"


# normaliza o valor de situação para o padrão do banco
# ex: 'FINALIZADO' -> 'Pago', 'pago' -> 'Pago'
def _normalizar_situacao(valor) -> str | None:
    if pd.isna(valor) or valor is None:
        return None
    chave = str(valor).strip().lower()
    return SITUACAO_MAP.get(chave, str(valor).strip())  # se não encontrar, mantém o valor original


# evita dados duplicados
def _gerar_hash(row: pd.Series) -> str:
    campos = [
        str(row.get("conta")),
        str(row.get("linha_planilha")),
        str(row.get("categoria")),
        str(row.get("descricao")),
        str(row.get("observacao")),
        str(row.get("data_pagamento")),
        str(row.get("situacao")),
        str(row.get("forma_pagamento")),
        str(row.get("entradas")),
        str(row.get("saidas")),
        str(row.get("saldo_acumulado")),
    ]
    texto = "|".join(campos)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _limpar_numero(valor):
    # Converte para float com 2 casas decimais; retorna None se inválido
    if pd.isna(valor):
        return None
    try:
        return round(float(valor), 2)
    except (TypeError, ValueError):
        return None


def _derivar_entradas_saidas(df: pd.DataFrame) -> pd.DataFrame:
    """Deriva entradas e saidas a partir da coluna MOVIMENTAÇÃO (formato novo):
      - movimentacao > 0  →  entradas = movimentacao, saidas = 0
      - movimentacao < 0  →  entradas = 0,             saidas = abs(movimentacao)
      - movimentacao == 0 →  entradas = 0,             saidas = 0

    Se a planilha já vier com entradas/saidas separadas (formato antigo via fallback),
    usa esses valores diretamente e garante que movimentacao seja calculada.
    """
    if "movimentacao" in df.columns:
        mov = df["movimentacao"].apply(_limpar_numero)
        df["entradas"] = mov.apply(lambda v: round(v, 2) if v and v > 0 else 0.0)
        df["saidas"]   = mov.apply(lambda v: round(abs(v), 2) if v and v < 0 else 0.0)
    else:
        # Formato antigo: colunas entradas_old / saidas_old já renomeadas
        if "entradas_old" in df.columns:
            df["entradas"] = df["entradas_old"].apply(_limpar_numero).fillna(0.0)
        if "saidas_old" in df.columns:
            df["saidas"] = df["saidas_old"].apply(_limpar_numero).fillna(0.0)
        if "entradas" not in df.columns:
            df["entradas"] = 0.0
        if "saidas" not in df.columns:
            df["saidas"] = 0.0
    return df


def transform_sheet(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    # Transforma o DataFrame bruto de UMA aba aplicando todas as regras de negócio
    # Pega os dados brutos do extrair_todos_os_dados() do extract.py

    info = SHEETS_CONFIG[sheet_name]

    # Rename case-insensitive: normaliza strip+lower antes de comparar
    rename_map_lower = {k.lower().strip(): v for k, v in RENAME_MAP.items()}
    df.columns = [rename_map_lower.get(c.lower().strip(), c) for c in df.columns]
    df = df.copy()

    # Descarta linhas totalmente vazias (usa apenas as colunas que existem no df)
    colunas_chave = ["descricao", "data_pagamento", "movimentacao", "entradas_old", "saidas_old", "saldo_acumulado"]
    colunas_chave = [c for c in colunas_chave if c in df.columns]
    df = df.dropna(how="all", subset=colunas_chave)

    # Metadados fixos da conta (fonte da verdade: config.py)
    df["conta"]    = info["conta"]
    df["entidade"] = info["entidade"]
    df["banco"]    = info["banco"]

    # Datas
    df["data_pagamento"] = pd.to_datetime(df["data_pagamento"], errors="coerce").dt.date

    # Números — entradas e saidas derivadas da coluna MOVIMENTAÇÃO
    df = _derivar_entradas_saidas(df)
    df["saldo_acumulado"] = df["saldo_acumulado"].apply(clean_saldo_value)
    df["valor_liquido"]   = (df["entradas"].fillna(0) - df["saidas"].fillna(0)).round(2)

    # Texto: remove espaços extras e normaliza vazio -> None
    for col in ["categoria", "descricao", "nf_doc", "situacao", "forma_pagamento", "observacao"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: str(v).strip() if pd.notna(v) else None)

    # Normalização da situação (FINALIZADO -> Pago, etc.)
    if "situacao" in df.columns:
        df["situacao"] = df["situacao"].apply(_normalizar_situacao)

    # Parcelas: converte para inteiro (nullable)
    for col in ["parc_atual", "parc_restante", "parc_total"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").where(pd.notna(df[col]), None)
            df[col] = df[col].apply(lambda v: int(v) if v is not None and not pd.isna(v) else None)

    # Classificação do tipo de lançamento
    df["tipo_lancamento"] = df["descricao"].apply(_classificar_linha)
    df.loc[df["situacao"].isna() & (df["tipo_lancamento"] != "MOVIMENTO"), "situacao"] = "Pago"

    # Hash de deduplicação
    df["hash_linha"] = df.apply(_gerar_hash, axis=1)

    colunas_finais = [
        "conta", "entidade", "banco", "linha_planilha",
        "categoria", "descricao", "nf_doc", "observacao",
        "parc_atual", "parc_restante", "parc_total",
        "data_pagamento", "situacao", "forma_pagamento",
        "entradas", "saidas", "saldo_acumulado",
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
