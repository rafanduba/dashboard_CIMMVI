-- Estrutura do banco de dados extraído da planilha --

CREATE TABLE IF NOT EXISTS lancamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    conta TEXT CHECK (conta IN 'CIMMVI - Rateio Banco do Brasil', 'CIMMVI - Licenciamento Caixa', 'AMVI - Banco do Brasil - CC 439'),

    entidade TEXT CHECK (entidade IN 'CIMMVI', 'AMVI'),

    banco TEXT, -- Banco do Brasil, Caixa, etc

    linha_planilha INTEGER NOT NULL, -- nº da linha da planilha original

    descricao TEXT,

    nf_doc Varchar(30),

    data_pagamento DATE,

    situacao TEXT CHECK (situacao IN 'Pago', 'Em aberto', 'Aprovado - Aguardando Pagamento','Aguardando Aprovação', 'Pagamento Realizado - Aguardando autorização Margarete'),

    forma_pagamento TEXT CHECK (forma_pagamento IN 'Pix', 'Boleto', 'DIRF'),

    entradas NUMERIC(12,2) DEFAULT 0,

    saidas NUMERIC(12,2) DEFAULT 0,

    valor_liquido NUMERIC(12,2) DEFAULT 0, -- entrada menos saída de cada linha

    saldo_acumulado NUMERIC(12,2), -- Saldo acumulado do dia

    observacao TEXT,

    tipo_lancamento TEXT NOT NULL DEFAULT 'MOVIMENTAÇÃO',

    hash_linha TEXT NOT NULL, -- evita dados duplicados, é tratado nos arquivos .py
    UNIQUE(hash_linha)
);

-- Views para o Dashboard


-- Saldo final de todas as 3 contas juntas
DROP VIEW IF EXISTS vw_saldo_final_geral
CREATE VIEW vw_saldo_final_geral AS
    WITH ultimo_saldo AS (
        SELECT
            conta, 
            saldo_acumulado,
            ROW_NUMBER() OVER(
                PARTITION BY conta
                ORDER BY data_pagamento DESC, id DESC
            ) AS id_ultimo_saldo -- pega a o útlimo saldo acumulado de cada dia e coloca de primeiro (índice 1) pra ser usado no where abaixo
        FROM lancamentos
    )
SELECT 
    SUM(saldo_acumulado) AS vw_saldo_final_geral
    FROM ultimo_saldo
    WHERE id_ultimo_saldo = 1;


-- Saldo final da conta 1 (CIMMVI - Rateio Banco do Brasil)





-- Saldo final da conta 2 (CIMMVI - Licenciamento Caixa)




-- Saldo final da conta 3 (AMVI - Banco do Brasil - CC 439)
