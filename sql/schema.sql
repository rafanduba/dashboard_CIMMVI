-- ESTRUTURA DO BANCO DE DADOS EXTRAÍDO DA PLANILHA --

CREATE TABLE IF NOT EXISTS lancamentos (

    -- gerenciamento do código
    id SERIAL PRIMARY KEY,

    conta TEXT CHECK (conta IN ('CIMMVI - Rateio Banco do Brasil', 'CIMMVI - Licenciamento Caixa', 'AMVI - Banco do Brasil - CC 439')),

    linha_planilha INTEGER NOT NULL,

    -- colunas planilha
    categoria TEXT,

    descricao TEXT,

    nf_doc VARCHAR(30),                -- presente na aba AMVI

    observacao TEXT,                   -- coluna OBSERVAÇÃO (abas CIMMVI)

    parc_atual INTEGER,
    parc_restante INTEGER,                -- coluna Parc.Rest / Parc.Atual — presente na aba Rateio BB
    parc_total INTEGER,                -- coluna Parc.Tr — presente na aba Rateio BB

    data_pagamento DATE,

    situacao TEXT CHECK (situacao IN (
        'Pago',
        'Em aberto',
        'Aprovado - Aguardando Pagamento',
        'Aguardando Aprovação',
        'Pagamento Realizado - Aguardando autorização Margarete'
    )),

    entidade TEXT CHECK (entidade IN ('CIMMVI', 'AMVI')),

    forma_pagamento TEXT CHECK (forma_pagamento IN ('Pix', 'Boleto', 'DIRF')),

    -- derivados da coluna MOVIMENTAÇÃO (positivo=entrada, negativo=saída)
    entradas NUMERIC(12,2) DEFAULT 0,
    saidas   NUMERIC(12,2) DEFAULT 0,

    saldo_acumulado NUMERIC(12,2),

    banco TEXT,

    -- adicional útil (não está na planilha)
    tipo_lancamento TEXT NOT NULL DEFAULT 'MOVIMENTO'
        CHECK (tipo_lancamento IN ('MOVIMENTO', 'SALDO_INICIAL', 'SALDO_DIA')),
    valor_liquido NUMERIC(12,2) DEFAULT 0, -- entrada - saída

    -- tratamento de erro
    hash_linha TEXT NOT NULL,
    UNIQUE(hash_linha)
);


-- VIEWS PARA O DASHBOARD --


-- Saldo final de todas as 3 contas juntas
DROP VIEW IF EXISTS vw_saldo_final_geral;
CREATE VIEW vw_saldo_final_geral AS
    WITH ultimo_saldo AS (
        SELECT
            conta,
            saldo_acumulado,
            ROW_NUMBER() OVER(
                PARTITION BY conta
                ORDER BY data_pagamento DESC, linha_planilha DESC
            ) AS id_ultimo_saldo -- pega o último saldo acumulado de cada conta e coloca de primeiro (índice 1) pra ser usado no where abaixo
        FROM lancamentos
        WHERE saldo_acumulado IS NOT NULL
    )
SELECT
    SUM(saldo_acumulado) AS vw_saldo_final_geral
    FROM ultimo_saldo
    WHERE id_ultimo_saldo = 1;


-- Saldo final da conta 1 (CIMMVI - Rateio Banco do Brasil)
DROP VIEW IF EXISTS vw_saldo_final_conta_1;
CREATE VIEW vw_saldo_final_conta_1 AS
SELECT
    saldo_acumulado AS saldo_final
FROM lancamentos
WHERE conta = 'CIMMVI - Rateio Banco do Brasil'
  AND situacao = 'Pago'
  AND saldo_acumulado IS NOT NULL
ORDER BY data_pagamento DESC, linha_planilha DESC
LIMIT 1;


-- Saldo final da conta 2 (CIMMVI - Licenciamento Caixa)
DROP VIEW IF EXISTS vw_saldo_final_conta_2;
CREATE VIEW vw_saldo_final_conta_2 AS
SELECT
    saldo_acumulado AS saldo_final
FROM lancamentos
WHERE conta = 'CIMMVI - Licenciamento Caixa'
  AND situacao = 'Pago'
  AND saldo_acumulado IS NOT NULL
ORDER BY data_pagamento DESC, linha_planilha DESC
LIMIT 1;


-- Saldo final da conta 3 (AMVI - Banco do Brasil - CC 439)
DROP VIEW IF EXISTS vw_saldo_final_conta_3;
CREATE VIEW vw_saldo_final_conta_3 AS
SELECT
    saldo_acumulado AS saldo_final
FROM lancamentos
WHERE conta = 'AMVI - Banco do Brasil - CC 439'
  AND situacao = 'Pago'
  AND saldo_acumulado IS NOT NULL
ORDER BY data_pagamento DESC, linha_planilha DESC
LIMIT 1;



-- Saldo final por conta (uma linha por conta)
DROP VIEW IF EXISTS vw_saldos_por_conta;
CREATE VIEW vw_saldos_por_conta AS
    SELECT conta, saldo_acumulado AS saldo_final
    FROM lancamentos
    WHERE id IN (
        SELECT id
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY conta
                       ORDER BY data_pagamento DESC, linha_planilha DESC
                   ) AS rn
            FROM lancamentos
        ) sub
        WHERE rn = 1
    )
    ORDER BY conta;


-- Evolucao do saldo acumulado por dia e por conta
DROP VIEW IF EXISTS vw_evolucao_saldo_diario;
CREATE VIEW vw_evolucao_saldo_diario AS
    SELECT
        data_pagamento,
        conta,
        MAX(saldo_acumulado) AS saldo_acumulado
    FROM lancamentos
    WHERE saldo_acumulado IS NOT NULL
      AND data_pagamento IS NOT NULL
    GROUP BY data_pagamento, conta
    ORDER BY data_pagamento, conta;


-- Evolucao do saldo acumulado por mes e por conta (ultimo dia de cada mes)
DROP VIEW IF EXISTS vw_evolucao_saldo_mensal;
CREATE VIEW vw_evolucao_saldo_mensal AS
    WITH ultimo_dia AS (
        SELECT
            strftime('%Y-%m', data_pagamento) AS ano_mes,
            conta,
            MAX(data_pagamento) AS ultima_data
        FROM lancamentos
        WHERE saldo_acumulado IS NOT NULL
          AND data_pagamento IS NOT NULL
        GROUP BY ano_mes, conta
    )
    SELECT
        ud.ano_mes,
        ud.conta,
        MAX(l.saldo_acumulado) AS saldo_acumulado
    FROM ultimo_dia ud
    JOIN lancamentos l
      ON l.conta = ud.conta
     AND l.data_pagamento = ud.ultima_data
     AND l.saldo_acumulado IS NOT NULL
    GROUP BY ud.ano_mes, ud.conta
    ORDER BY ud.ano_mes, ud.conta;


-- Total de entradas e saidas por mes e conta
DROP VIEW IF EXISTS vw_entradas_saidas_mensais;
CREATE VIEW vw_entradas_saidas_mensais AS
    SELECT
        strftime('%Y-%m', data_pagamento) AS ano_mes,
        conta,
        COALESCE(SUM(entradas), 0) AS entradas,
        COALESCE(SUM(saidas),   0) AS saidas,
        COALESCE(SUM(valor_liquido), 0) AS liquido
    FROM lancamentos
    WHERE tipo_lancamento = 'MOVIMENTO'
      AND data_pagamento IS NOT NULL
    GROUP BY ano_mes, conta
    ORDER BY ano_mes, conta;


-- Contagem e valores por situacao (visao geral, sem filtro de periodo)
DROP VIEW IF EXISTS vw_contagem_por_situacao;
CREATE VIEW vw_contagem_por_situacao AS
    SELECT
        COALESCE(situacao, 'Nao informado') AS situacao,
        COUNT(*) AS quantidade,
        COALESCE(SUM(saidas),   0) AS total_saidas,
        COALESCE(SUM(entradas), 0) AS total_entradas
    FROM lancamentos
    WHERE tipo_lancamento = 'MOVIMENTO'
    GROUP BY situacao
    ORDER BY total_saidas DESC;


-- Total de saidas por forma de pagamento (visao geral, sem filtro de periodo)
DROP VIEW IF EXISTS vw_saidas_por_forma_pagamento;
CREATE VIEW vw_saidas_por_forma_pagamento AS
    SELECT
        COALESCE(forma_pagamento, 'Nao informado') AS forma_pagamento,
        COALESCE(SUM(saidas), 0) AS total_saidas,
        COUNT(*) AS quantidade
    FROM lancamentos
    WHERE tipo_lancamento = 'MOVIMENTO'
      AND saidas > 0
    GROUP BY forma_pagamento
    ORDER BY total_saidas DESC;


-- Total de saidas por categoria (visao geral, sem filtro de periodo)
DROP VIEW IF EXISTS vw_saidas_por_categoria;
CREATE VIEW vw_saidas_por_categoria AS
    SELECT
        COALESCE(categoria, 'Não informado') AS categoria,
        COALESCE(SUM(saidas), 0) AS total_saidas,
        COALESCE(SUM(entradas), 0) AS total_entradas,
        COUNT(*) AS quantidade
    FROM lancamentos
    WHERE tipo_lancamento = 'MOVIMENTO'
    GROUP BY categoria
    ORDER BY total_saidas DESC;


-- Saídas em aberto pendentes: aparecem APÓS o último lançamento 'Pago' da mesma conta
DROP VIEW IF EXISTS vw_valor_em_aberto;
DROP VIEW IF EXISTS vw_saidas_em_aberto;
CREATE VIEW vw_saidas_em_aberto AS
SELECT COALESCE(SUM(l.saidas), 0) AS valor_saidas_em_aberto
FROM lancamentos l
WHERE l.situacao = 'Em aberto'
  AND l.tipo_lancamento = 'MOVIMENTO'
  AND l.id > (
      SELECT COALESCE(MAX(l2.id), -1)
      FROM lancamentos l2
      WHERE l2.conta = l.conta
        AND l2.situacao = 'Pago'
  );

-- Entradas em aberto pendentes: aparecem APÓS o último lançamento 'Pago' da mesma conta
DROP VIEW IF EXISTS vw_entradas_em_aberto;
CREATE VIEW vw_entradas_em_aberto AS
SELECT COALESCE(SUM(l.entradas), 0) AS valor_entradas_em_aberto
FROM lancamentos l
WHERE l.situacao = 'Em aberto'
  AND l.tipo_lancamento = 'MOVIMENTO'
  AND l.id > (
      SELECT COALESCE(MAX(l2.id), -1)
      FROM lancamentos l2
      WHERE l2.conta = l.conta
        AND l2.situacao = 'Pago'
  );

-- Total de saidas aguardando aprovacao ou pagamento (todas as contas)
DROP VIEW IF EXISTS vw_valor_aguardando_aprovacao;
CREATE VIEW vw_valor_aguardando_aprovacao AS
    SELECT COALESCE(SUM(saidas), 0) AS valor_aguardando_aprovacao
    FROM lancamentos
    WHERE situacao IN (
            'Aguardando Aprovação',
            'Aprovado - Aguardando Pagamento',
            'Pagamento Realizado - Aguardando autorização Margarete'
          )
      AND tipo_lancamento = 'MOVIMENTO';


-- Adimplência por município
-- Considera ADIMPLENTE se as parcelas restantes forem menores ou iguais a
-- (parc_total - mes_atual + 1). Exemplo: no mês 7, ter até 6 parcelas restantes (12 - 7 + 1 = 6).
DROP VIEW IF EXISTS vw_adimplencia_municipios;
CREATE VIEW vw_adimplencia_municipios AS
WITH mes_atual AS (
    SELECT CAST(strftime('%m', 'now') AS INTEGER) AS m
),
ultimos_lancamentos AS (
    SELECT
        TRIM(descricao) AS municipio,
        parc_atual,
        parc_restante,
        COALESCE(parc_total, 12) AS parc_total,
        ROW_NUMBER() OVER(
            PARTITION BY LOWER(TRIM(descricao))
            ORDER BY linha_planilha DESC, id DESC
        ) AS rn
    FROM lancamentos
    WHERE conta = 'CIMMVI - Rateio Banco do Brasil'
      AND LOWER(TRIM(categoria)) = 'rateio municipal'
      AND tipo_lancamento = 'MOVIMENTO'
      AND descricao IS NOT NULL
      AND TRIM(descricao) != ''
)
SELECT
    u.municipio,
    u.parc_atual,
    u.parc_restante,
    u.parc_total,
    CASE
        WHEN u.parc_restante IS NOT NULL AND u.parc_restante <= (u.parc_total - m.m + 1)
        THEN 1
        ELSE 0
    END AS adimplente
FROM ultimos_lancamentos u, mes_atual m
WHERE u.rn = 1
ORDER BY adimplente DESC, u.municipio;


-- AUDITORIA DO ETL --

CREATE TABLE IF NOT EXISTS etl_execucoes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    iniciado_em       TEXT    DEFAULT (datetime('now')),
    finalizado_em     TEXT,
    arquivo_origem    TEXT,
    status            TEXT    DEFAULT 'EM_ANDAMENTO',
    linhas_lidas      INTEGER,
    linhas_inseridas  INTEGER,
    linhas_ignoradas  INTEGER,
    mensagem_erro     TEXT
);
