-- ESTRUTURA DO BANCO DE DADOS EXTRAÍDO DA PLANILHA --

CREATE TABLE IF NOT EXISTS lancamentos (

    -- gerenciamento do código
    id SERIAL PRIMARY KEY,

    conta TEXT CHECK (conta IN ('CIMMVI - Rateio Banco do Brasil', 'CIMMVI - Licenciamento Caixa', 'AMVI - Banco do Brasil - CC 439')),

    linha_planilha INTEGER NOT NULL, 

    -- colunas planilha
    descricao TEXT,

    nf_doc VARCHAR(30),

    data_pagamento DATE,

    situacao TEXT CHECK (situacao IN ('Pago', 'Em aberto', 'Aprovado - Aguardando Pagamento', 'Aguardando Aprovação', 'Pagamento Realizado - Aguardando autorização Margarete')),

    entidade TEXT CHECK (entidade IN ('CIMMVI', 'AMVI')),

    forma_pagamento TEXT CHECK (forma_pagamento IN ('Pix', 'Boleto', 'DIRF')),

    entradas NUMERIC(12,2) DEFAULT 0,

    saidas NUMERIC(12,2) DEFAULT 0,

    saldo_acumulado NUMERIC(12,2), 

    observacao TEXT,

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
                ORDER BY data_pagamento DESC, id DESC
            ) AS id_ultimo_saldo -- pega a o útlimo saldo acumulado de cada conta e coloca de primeiro (índice 1) pra ser usado no where abaixo
        FROM lancamentos
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
ORDER BY data_pagamento DESC, id DESC
LIMIT 1;


-- Saldo final da conta 2 (CIMMVI - Licenciamento Caixa)
DROP VIEW IF EXISTS vw_saldo_final_conta_2;
CREATE VIEW vw_saldo_final_conta_2 AS
SELECT 
    saldo_acumulado AS saldo_final
FROM lancamentos
WHERE conta = 'CIMMVI - Licenciamento Caixa'
ORDER BY data_pagamento DESC, id DESC
LIMIT 1;


-- Saldo final da conta 3 (AMVI - Banco do Brasil - CC 439)
DROP VIEW IF EXISTS vw_saldo_final_conta_3
CREATE VIEW vw_saldo_final_conta_3 AS
SELECT
    saldo_acumulado AS saldo_final
FROM lancamentos
WHERE conta = 'AMVI - Banco do Brasil - CC 439'
ORDER BY data_pagamento DESC, id DESC
LIMIT 1;
