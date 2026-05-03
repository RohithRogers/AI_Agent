import flet as ft

# ─────────────────────────────────────────────
#  THEME PRESETS
# ─────────────────────────────────────────────
THEMES = {
    "synthic": {
        "SURFACE_DIM":    "#0D0F14",
        "SURFACE":        "#13161E",
        "SURFACE_CARD":   "#1C2030",
        "SURFACE_HOVER":  "#232840",
        "BORDER":         "#2A2F45",
        "ACCENT":         "#7C6FCD",
        "ACCENT_ALT":     "#5B8AF0",
        "ACCENT_GLOW":    "#A89BFF",
        "USER_BUBBLE":    "#1E2A45",
        "AGENT_BUBBLE":   "#1A1C28",
        "TERMINAL_BG":    "#0A0C10",
        "TERMINAL_FG":    "#C0E0A0",
        "TEXT_PRIMARY":   "#E8EAF6",
        "TEXT_SECONDARY": "#9098B8",
        "TEXT_DIM":       "#555E80",
    },
    "grey": {
        "SURFACE_DIM":    "#121212",
        "SURFACE":        "#1E1E1E",
        "SURFACE_CARD":   "#2C2C2C",
        "SURFACE_HOVER":  "#383838",
        "BORDER":         "#333333",
        "ACCENT":         "#9E9E9E",
        "ACCENT_ALT":     "#757575",
        "ACCENT_GLOW":    "#BDBDBD",
        "USER_BUBBLE":    "#242424",
        "AGENT_BUBBLE":   "#1A1A1A",
        "TERMINAL_BG":    "#0D0D0D",
        "TERMINAL_FG":    "#E0E0E0",
        "TEXT_PRIMARY":   "#FFFFFF",
        "TEXT_SECONDARY": "#B0B0B0",
        "TEXT_DIM":       "#707070",
    }
}

# Current active colors
SURFACE_DIM    = THEMES["synthic"]["SURFACE_DIM"]
SURFACE        = THEMES["synthic"]["SURFACE"]
SURFACE_CARD   = THEMES["synthic"]["SURFACE_CARD"]
SURFACE_HOVER  = THEMES["synthic"]["SURFACE_HOVER"]
BORDER         = THEMES["synthic"]["BORDER"]
ACCENT         = THEMES["synthic"]["ACCENT"]
ACCENT_ALT     = THEMES["synthic"]["ACCENT_ALT"]
ACCENT_GLOW    = THEMES["synthic"]["ACCENT_GLOW"]
USER_BUBBLE    = THEMES["synthic"]["USER_BUBBLE"]
AGENT_BUBBLE   = THEMES["synthic"]["AGENT_BUBBLE"]
TERMINAL_BG    = THEMES["synthic"]["TERMINAL_BG"]
TERMINAL_FG    = THEMES["synthic"]["TERMINAL_FG"]
TEXT_PRIMARY   = THEMES["synthic"]["TEXT_PRIMARY"]
TEXT_SECONDARY = THEMES["synthic"]["TEXT_SECONDARY"]
TEXT_DIM       = THEMES["synthic"]["TEXT_DIM"]

def set_theme(name: str):
    global SURFACE_DIM, SURFACE, SURFACE_CARD, SURFACE_HOVER, BORDER, ACCENT, ACCENT_ALT, ACCENT_GLOW
    global USER_BUBBLE, AGENT_BUBBLE, TERMINAL_BG, TERMINAL_FG, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM
    if name not in THEMES: return
    t = THEMES[name]
    SURFACE_DIM    = t["SURFACE_DIM"]
    SURFACE        = t["SURFACE"]
    SURFACE_CARD   = t["SURFACE_CARD"]
    SURFACE_HOVER  = t["SURFACE_HOVER"]
    BORDER         = t["BORDER"]
    ACCENT         = t["ACCENT"]
    ACCENT_ALT     = t["ACCENT_ALT"]
    ACCENT_GLOW    = t["ACCENT_GLOW"]
    USER_BUBBLE    = t["USER_BUBBLE"]
    AGENT_BUBBLE   = t["AGENT_BUBBLE"]
    TERMINAL_BG    = t["TERMINAL_BG"]
    TERMINAL_FG    = t["TERMINAL_FG"]
    TEXT_PRIMARY   = t["TEXT_PRIMARY"]
    TEXT_SECONDARY = t["TEXT_SECONDARY"]
    TEXT_DIM       = t["TEXT_DIM"]

SUCCESS        = "#4CAF78"
WARNING        = "#F0A840"
ERROR          = "#E05560"
INFO           = "#5B8AF0" # Static for now

# ─────────────────────────────────────────────
#  TYPOGRAPHY
# ─────────────────────────────────────────────
FONT_MONO   = "Consolas"
FONT_UI     = "Segoe UI"

# ─────────────────────────────────────────────
#  RADIUS / SPACING
# ─────────────────────────────────────────────
RADIUS_SM  = 8
RADIUS_MD  = 14
RADIUS_LG  = 20
RADIUS_XL  = 28

def build_color_scheme() -> ft.ColorScheme:
    return ft.ColorScheme(
        primary=ACCENT,
        on_primary=TEXT_PRIMARY,
        secondary=ACCENT_ALT,
        on_secondary=TEXT_PRIMARY,
        surface=SURFACE_DIM,
        on_surface=TEXT_PRIMARY,
        error=ERROR,
        on_error=TEXT_PRIMARY,
        surface_container=SURFACE_CARD,
        outline=BORDER,
    )


def build_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=ACCENT,
        color_scheme=build_color_scheme(),
        visual_density=ft.VisualDensity.COMFORTABLE,
        font_family=FONT_UI,
        use_material3=True,
    )
