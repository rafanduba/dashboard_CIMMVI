"""Design tokens e constantes do dashboard."""

# ════════════════════════════════════════════════════════════════════════════
# Cores
# ════════════════════════════════════════════════════════════════════════════
BG        = "var(--bg)"
CARD      = "var(--card)"
CARD2     = "var(--card2)"
BORDER    = "var(--border)"
PRIMARY   = "#6366f1"
SECONDARY = "#8b5cf6"
SUCCESS   = "#10b981"
DANGER    = "#ef4444"
WARNING   = "#f59e0b"
INFO      = "#06b6d4"
MUTED     = "#64748b"
TEXT      = "var(--text)"
TEXT_DIM  = "var(--text-dim)"
FONT      = "Inter, system-ui, -apple-system, sans-serif"

# ════════════════════════════════════════════════════════════════════════════
# Estilos por conta
# ════════════════════════════════════════════════════════════════════════════
CONTA_ESTILOS = {
    "CIMMVI - Rateio Banco do Brasil":  (PRIMARY,   "rgba(129,140,248,0.08)"),
    "CIMMVI - Licenciamento Caixa":     (SECONDARY, "rgba(167,139,250,0.08)"),
    "AMVI - Banco do Brasil - CC 439":  (INFO,      "rgba(56,189,248,0.08)"),
}

SITUACAO_CORES = {
    "Pago":                                                        SUCCESS,
    "Em aberto":                                                   DANGER,
    "Aguardando Aprovação":                                        WARNING,
    "Aprovado - Aguardando Pagamento":                             INFO,
    "Pagamento Realizado - Aguardando autorização Margarete":      MUTED,
    "Nao informado":                                               MUTED,
}

PALETA = [PRIMARY, SECONDARY, INFO, SUCCESS, WARNING, DANGER, "#fb923c", "#e879f9"]

ICON_BG = {
    SUCCESS:   "rgba(52,211,153,0.15)",
    DANGER:    "rgba(248,113,113,0.15)",
    WARNING:   "rgba(251,191,36,0.15)",
    PRIMARY:   "rgba(129,140,248,0.15)",
    INFO:      "rgba(56,189,248,0.15)",
    SECONDARY: "rgba(167,139,250,0.15)",
}