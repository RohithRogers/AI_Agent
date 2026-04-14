import flet as ft

# ─────────────────────────────────────────────
#  COLOUR PALETTE   (dark-mode first)
# ─────────────────────────────────────────────
SURFACE_DIM    = "#0D0F14"   # deepest background
SURFACE        = "#13161E"   # sidebar / panel bg
SURFACE_CARD   = "#1C2030"   # message bubble bg
SURFACE_HOVER  = "#232840"   # hover state
BORDER         = "#2A2F45"   # subtle divider

ACCENT         = "#7C6FCD"   # primary purple
ACCENT_ALT     = "#5B8AF0"   # blue secondary
ACCENT_GLOW    = "#A89BFF"   # lighter glow purple

USER_BUBBLE    = "#1E2A45"   # user message bg
AGENT_BUBBLE   = "#1A1C28"   # agent message bg
TERMINAL_BG    = "#0A0C10"   # terminal panel bg
TERMINAL_FG    = "#C0E0A0"   # terminal text green

TEXT_PRIMARY   = "#E8EAF6"
TEXT_SECONDARY = "#9098B8"
TEXT_DIM       = "#555E80"

SUCCESS        = "#4CAF78"
WARNING        = "#F0A840"
ERROR          = "#E05560"
INFO           = ACCENT_ALT

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
