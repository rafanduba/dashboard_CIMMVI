# Dashboard CIMMVI / AMVI

Dashboard financeiro para o consórcio municipal **CIMMVI/AMVI**, com um pipeline ETL que extrai dados diretamente de planilhas do Google Sheets, os carrega em um banco de dados e os exibe em um painel interativo construído com [Dash](https://dash.plotly.com/) (Plotly).

## Funcionalidades

- **Pipeline ETL** (Extract → Transform → Load) que baixa as planilhas financeiras do Google Sheets, normaliza colunas e valores, e carrega os lançamentos em um banco relacional, evitando duplicidade via hash de linha.
- **Painel interativo** com múltiplas páginas:
  - **Visão Executiva** — saldo por conta, movimentação no período, status de adimplência dos municípios e saídas por categoria.
  - **Execução Orçamentária**.
  - **Municípios Consorciados** — resumo por município (previsto vs. recebido vs. saldo) e indicadores.
  - **Contratos** — parcelas e situação dos contratos de rateio.
- **Views SQL** pré-calculadas para saldos, evolução mensal/diária, entradas e saídas, adimplência por município, entre outras.
- **Execução como aplicativo desktop**, empacotado com PyInstaller (`Dashboard_CIMMVI.exe`), que sobe o servidor local e abre o navegador automaticamente.

## Estrutura do projeto

```
dashboard_CIMMVI/
├── config.py               # Configurações gerais (URLs das planilhas, mapeamento de colunas, etc.)
├── run_desktop.py          # Ponto de entrada para a versão desktop (PyInstaller)
├── build_exe.py            # Script para gerar o executável (.exe)
├── sql/
│   └── schema.sql          # Estrutura das tabelas e views do banco de dados
├── etl/
│   ├── extract.py          # Extração dos dados do Google Sheets
│   ├── transform.py        # Limpeza e normalização dos dados
│   ├── load.py             # Carga no banco de dados
│   └── run_etl.py          # Orquestração do pipeline (Extract → Transform → Load)
├── dashboard/
│   ├── app.py               # Ponto de entrada do app Dash
│   ├── layout.py             # Layout geral do painel
│   ├── callbacks.py          # Callbacks de interatividade
│   ├── components.py         # Componentes reutilizáveis (cards, KPIs, etc.)
│   ├── queries.py            # Consultas SQL usadas pelo painel
│   ├── assets/                # CSS e outros arquivos estáticos
│   └── pages/
│       ├── visao_executiva.py
│       ├── execucao_orcamentaria.py
│       ├── municipios_consorciados.py
│       └── contratos.py
└── data/                    # Banco de dados SQLite gerado localmente
```

## Requisitos

- Python 3.11+
- Bibliotecas: `dash`, `pandas`, `numpy`, `plotly`, `sqlalchemy`, `openpyxl`

Instale as dependências:

```bash
pip install dash pandas numpy plotly sqlalchemy openpyxl
```

## Configuração

O projeto usa variáveis de ambiente opcionais (com valores padrão definidos em `config.py`):

| Variável | Descrição | Padrão |
|---|---|---|
| `DATABASE_URL` | URL de conexão do banco de dados | SQLite local em `data/cimmvi_amvi.db` |
| `GOOGLE_SHEETS_ID` | ID da planilha financeira principal | definido em `config.py` |
| `GOOGLE_SHEETS_CONTRATOS_ID` | ID da planilha de controle de contratos e atas | definido em `config.py` |
| `LOG_LEVEL` | Nível de log do pipeline ETL | `INFO` |

## Como executar

### É possível acessar o programa a partir do executável: [Dashboard.exe](https://exemplo.com](https://github.com/rafanduba/dashboard_CIMMVI/blob/main/Dashboard_CIMMVI.exe))

### Ou, a partir dos arquivos base:

### 1. Rodar o pipeline ETL

Extrai os dados mais recentes das planilhas e atualiza o banco de dados:

```bash
python -m etl.run_etl
```

### 2. Rodar o dashboard em modo desenvolvimento

```bash
python dashboard/app.py
```

O painel abrirá em `http://localhost:8050`.

### 3. Rodar como aplicativo desktop

```bash
python run_desktop.py
```

Isso inicia o servidor localmente e abre o navegador automaticamente em `http://127.0.0.1:8050`.

### 4. Gerar o executável (.exe)

```bash
python build_exe.py
```

Requer o pacote `pyinstaller` instalado. O executável final é gerado na raiz do projeto.

## Banco de dados

O schema principal está em [`sql/schema.sql`](sql/schema.sql), incluindo:
- Tabela `lancamentos`, com os lançamentos financeiros de cada conta.
- Tabela `etl_execucoes`, para auditoria das execuções do pipeline.
- Views agregadas para saldos, evolução mensal/diária, entradas/saídas por categoria e forma de pagamento, e adimplência por município.

## Licença

Projeto de uso interno do consórcio CIMMVI/AMVI.
