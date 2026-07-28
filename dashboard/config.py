"""Design tokens e constantes do dashboard."""

# ════════════════════════════════════════════════════════════════════════════
# Cores
# ════════════════════════════════════════════════════════════════════════════
BG        = "#0d0f1a"
CARD      = "#141624"
CARD2     = "#1a1d2e"
BORDER    = "#252840"
PRIMARY   = "#818cf8"
SECONDARY = "#a78bfa"
SUCCESS   = "#34d399"
DANGER    = "#f87171"
WARNING   = "#fbbf24"
INFO      = "#38bdf8"
MUTED     = "#64748b"
TEXT      = "#e2e8f0"
TEXT_DIM  = "#94a3b8"
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