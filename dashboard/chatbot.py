"""Chatbot financeiro para o Dashboard CIMMVI/AMVI.

Integra o Google Gemini (API gratuita) com o banco de dados do dashboard.
Coleta um snapshot dos dados financeiros e envia como contexto para a IA,
permitindo respostas inteligentes em linguagem natural.

Configuração:
    Defina a variável de ambiente GEMINI_API_KEY com sua chave da API Gemini.
    Obtenha gratuitamente em: https://aistudio.google.com/apikey
"""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

MODEL_NAME = "gemini-2.0-flash"   # Alias genérico — sempre aponta para a versão estável mais recente

_SYSTEM_PROMPT = """Você é o assistente financeiro do CIMMVI/AMVI — um consórcio intermunicipal do Vale do Itajaí (SC).
Você tem acesso a dados financeiros reais do dashboard e responde perguntas sobre:
- Saldos e movimentações das contas
- Lançamentos (entradas, saídas, situações)
- Municípios consorciados e adimplência
- Contratos e atas vigentes
- Categorias de despesa e forma de pagamento

Regras:
- Responda SEMPRE em português brasileiro
- Seja objetivo e profissional, mas amigável
- Formate valores monetários como R$ X.XXX,XX
- Use os dados do contexto financeiro fornecido — não invente valores
- Se não souber algo, diga claramente que não encontrou essa informação nos dados
- Respostas curtas e diretas quando possível; detalhadas quando necessário
- Quando listar itens, use marcadores ou numeração para facilitar a leitura
"""


# ---------------------------------------------------------------------------
# Coleta de contexto financeiro
# ---------------------------------------------------------------------------

def _fmt_brl(v: float | None) -> str:
    """Formata float como R$ brasileiro."""
    if v is None:
        return "não disponível"
    try:
        abs_str = f"R$ {abs(float(v)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"- {abs_str}" if float(v) < 0 else abs_str
    except (TypeError, ValueError):
        return "não disponível"


def coletar_contexto_financeiro() -> str:
    """Consulta o banco SQLite e monta um resumo textual dos dados financeiros atuais.

    Este contexto é enviado ao Gemini junto com cada pergunta, permitindo
    que a IA responda com base nos dados reais do dashboard.
    """
    try:
        from dashboard.queries import (
            saldo_final_geral,
            saldo_final_conta_1,
            saldo_final_conta_2,
            saldo_final_conta_3,
            total_entradas,
            total_saidas,
            saidas_em_aberto,
            entradas_em_aberto,
            valor_aguardando_aprovacao,
            saidas_por_categoria,
            top_saidas,
            contagem_por_situacao,
            adimplencia_municipios,
            periodo_disponivel,
            ultima_carga,
        )
    except ImportError as e:
        logger.warning("Não foi possível importar queries: %s", e)
        return "Dados financeiros não disponíveis no momento."

    linhas: list[str] = []
    hoje = str(date.today())

    # ── Período dos dados ───────────────────────────────────────────────────
    try:
        periodo = periodo_disponivel() or {}
        d_min = periodo.get("data_min", "?")
        d_max = periodo.get("data_max", "?")
        linhas.append(f"DATA DE REFERÊNCIA: {hoje}")
        linhas.append(f"PERÍODO DOS DADOS: {d_min} até {d_max}")
    except Exception:
        linhas.append(f"DATA DE REFERÊNCIA: {hoje}")

    # ── Última atualização ─────────────────────────────────────────────────
    try:
        uc = ultima_carga()
        if uc:
            linhas.append(f"ÚLTIMA SINCRONIZAÇÃO: {uc.get('iniciado_em', '?')}")
    except Exception:
        pass

    linhas.append("")

    # ── Saldos por conta ───────────────────────────────────────────────────
    linhas.append("=== SALDOS ATUAIS ===")
    try:
        linhas.append(f"Saldo geral (todas as contas): {_fmt_brl(saldo_final_geral())}")
        linhas.append(f"  - CIMMVI Rateio Banco do Brasil: {_fmt_brl(saldo_final_conta_1())}")
        linhas.append(f"  - CIMMVI Licenciamento Caixa:    {_fmt_brl(saldo_final_conta_2())}")
        linhas.append(f"  - AMVI Banco do Brasil CC 439:   {_fmt_brl(saldo_final_conta_3())}")
    except Exception as e:
        linhas.append(f"(Erro ao buscar saldos: {e})")

    linhas.append("")

    # ── Movimentação geral (todo o período) ────────────────────────────────
    linhas.append("=== MOVIMENTAÇÃO TOTAL (todo o período) ===")
    try:
        linhas.append(f"Total de entradas: {_fmt_brl(total_entradas())}")
        linhas.append(f"Total de saídas:   {_fmt_brl(total_saidas())}")
        linhas.append(f"Em aberto (saídas pendentes): {_fmt_brl(saidas_em_aberto())}")
        linhas.append(f"Em aberto (entradas a receber): {_fmt_brl(entradas_em_aberto())}")
        linhas.append(f"Aguardando aprovação/pagamento: {_fmt_brl(valor_aguardando_aprovacao())}")
    except Exception as e:
        linhas.append(f"(Erro ao buscar movimentação: {e})")

    linhas.append("")

    # ── Situação dos lançamentos ───────────────────────────────────────────
    linhas.append("=== SITUAÇÃO DOS LANÇAMENTOS ===")
    try:
        df_sit = contagem_por_situacao()
        if not df_sit.empty:
            for _, row in df_sit.iterrows():
                sit = row.get("situacao", "?")
                qtd = int(row.get("quantidade", 0))
                s = float(row.get("total_saidas", 0))
                e = float(row.get("total_entradas", 0))
                if s > 0 and e > 0:
                    linhas.append(f"  {sit}: {qtd} lançamentos | saídas={_fmt_brl(s)} | entradas={_fmt_brl(e)}")
                elif s > 0:
                    linhas.append(f"  {sit}: {qtd} lançamentos | total saídas={_fmt_brl(s)}")
                elif e > 0:
                    linhas.append(f"  {sit}: {qtd} lançamentos | total entradas={_fmt_brl(e)}")
                else:
                    linhas.append(f"  {sit}: {qtd} lançamentos")
    except Exception as e:
        linhas.append(f"(Erro ao buscar situações: {e})")

    linhas.append("")

    # ── Top 10 maiores saídas ──────────────────────────────────────────────
    linhas.append("=== TOP 10 MAIORES SAÍDAS ===")
    try:
        df_top = top_saidas(n=10)
        if not df_top.empty:
            for i, row in enumerate(df_top.itertuples(), 1):
                data = getattr(row, "data_pagamento", "?")
                desc = getattr(row, "descricao", "?")
                val  = getattr(row, "saidas", 0)
                sit  = getattr(row, "situacao", "?")
                linhas.append(f"  {i}. {data} | {desc} | {_fmt_brl(val)} | {sit}")
        else:
            linhas.append("  Nenhum dado disponível.")
    except Exception as e:
        linhas.append(f"(Erro ao buscar top saídas: {e})")

    linhas.append("")

    # ── Saídas por categoria ───────────────────────────────────────────────
    linhas.append("=== SAÍDAS POR CATEGORIA ===")
    try:
        df_cat = saidas_por_categoria()
        if not df_cat.empty:
            for _, row in df_cat.head(15).iterrows():
                cat = row.get("categoria", "?")
                val = float(row.get("total_saidas", 0))
                qtd = int(row.get("quantidade", 0))
                if val > 0:
                    linhas.append(f"  {cat}: {_fmt_brl(val)} ({qtd} lançamentos)")
        else:
            linhas.append("  Nenhum dado disponível.")
    except Exception as e:
        linhas.append(f"(Erro ao buscar categorias: {e})")

    linhas.append("")

    # ── Adimplência dos municípios ─────────────────────────────────────────
    linhas.append("=== ADIMPLÊNCIA DOS MUNICÍPIOS CONSORCIADOS ===")
    try:
        df_mun = adimplencia_municipios()
        if not df_mun.empty:
            adimplentes = []
            inadimplentes = []
            for _, row in df_mun.iterrows():
                mun = row.get("municipio", "?")
                status = row.get("status_adimplencia", "?")
                recebido = float(row.get("recebido", 0))
                previsto = float(row.get("previsto_total", 0))
                pct = float(row.get("percentual_adimplencia", 0))
                info = f"    - {mun}: recebido={_fmt_brl(recebido)} de {_fmt_brl(previsto)} ({pct:.0f}%)"
                if status in ("Adimplente", "adimplente"):
                    adimplentes.append(info)
                else:
                    inadimplentes.append(info)

            linhas.append(f"Adimplentes ({len(adimplentes)} municípios):")
            linhas.extend(adimplentes if adimplentes else ["    Nenhum"])
            linhas.append(f"Inadimplentes ({len(inadimplentes)} municípios):")
            linhas.extend(inadimplentes if inadimplentes else ["    Nenhum"])
        else:
            linhas.append("  Nenhum dado de municípios disponível.")
    except Exception as e:
        linhas.append(f"(Erro ao buscar municípios: {e})")

    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Integração com Gemini
# ---------------------------------------------------------------------------

def _get_client():
    """Inicializa e retorna o cliente Gemini."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "Chave de API não configurada. Defina a variável de ambiente GEMINI_API_KEY.\n"
            "Obtenha gratuitamente em: https://aistudio.google.com/apikey"
        )

    try:
        import google.generativeai as genai  # type: ignore[import]
    except ImportError:
        raise ImportError(
            "Pacote 'google-generativeai' não encontrado.\n"
            "Instale com: pip install google-generativeai"
        )

    genai.configure(api_key=api_key)
    return genai


def responder_pergunta(pergunta: str, historico: list[dict[str, Any]]) -> str:
    """Envia a pergunta + contexto financeiro ao Gemini e retorna a resposta.

    Args:
        pergunta: A pergunta do usuário.
        historico: Lista de mensagens anteriores no formato
                   [{"role": "user"|"model", "parts": ["texto"]}]

    Returns:
        String com a resposta da IA.
    """
    if not pergunta or not pergunta.strip():
        return "Por favor, digite uma pergunta."

    # Verifica API key antes de tudo
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return (
            "⚠️ **Chave de API não configurada.**\n\n"
            "Para usar o chatbot, configure a variável de ambiente `GEMINI_API_KEY`:\n\n"
            "1. Acesse [aistudio.google.com/apikey](https://aistudio.google.com/apikey)\n"
            "2. Crie uma chave gratuita\n"
            "3. Execute o dashboard com:\n"
            "   `set GEMINI_API_KEY=sua-chave-aqui` (Windows CMD)\n"
            "   ou defina no arquivo `.env` na raiz do projeto"
        )

    try:
        genai = _get_client()

        # Coleta contexto financeiro fresco
        contexto = coletar_contexto_financeiro()

        # Monta prompt do sistema com contexto
        system_with_context = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"--- DADOS FINANCEIROS ATUAIS DO DASHBOARD ---\n"
            f"{contexto}\n"
            f"--- FIM DOS DADOS ---"
        )

        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=system_with_context,
        )

        # Converte histórico para formato Gemini (máx. 10 mensagens anteriores)
        chat_history = historico[-10:] if historico else []

        chat = model.start_chat(history=chat_history)
        response = chat.send_message(pergunta.strip())

        return response.text

    except ImportError as e:
        logger.error("Pacote Gemini não instalado: %s", e)
        return (
            "⚠️ **Dependência não instalada.**\n\n"
            "Instale o SDK do Gemini com:\n"
            "```\npip install google-generativeai\n```"
        )
    except Exception as e:
        err_str = str(e)
        logger.error("Erro ao chamar Gemini API: %s", err_str)

        if "API_KEY" in err_str.upper() or "api key" in err_str.lower():
            return "⚠️ Chave de API inválida ou expirada. Verifique sua `GEMINI_API_KEY`."
        if "quota" in err_str.lower() or "429" in err_str:
            return "⚠️ Limite de requisições atingido. Aguarde alguns minutos e tente novamente."
        if "network" in err_str.lower() or "connection" in err_str.lower():
            return "⚠️ Erro de conexão. Verifique sua internet e tente novamente."

        return f"⚠️ Erro ao processar sua pergunta. Tente novamente em instantes.\n\n*Detalhes: {err_str[:200]}*"
