from rich.console import Console
from rich.theme import Theme

THEME_CONFIGS = {
    "green": {
        "title": "bold spring_green1",
        "accent": "spring_green1",
        "dim": "grey50",
        "user": "bold spring_green1",
        "agent": "bold spring_green1",
        "success": "bold spring_green2",
        "warning": "bold yellow",
        "error": "bold red",
        "info": "bold cyan"
    },
    "blue": {
        "title": "bold sky_blue1",
        "accent": "sky_blue1",
        "dim": "grey50",
        "user": "bold sky_blue1",
        "agent": "bold sky_blue1",
        "success": "bold sky_blue1",
        "warning": "bold yellow",
        "error": "bold red",
        "info": "bold sky_blue1"
    },
    "violet": {
        "title": "bold violet",
        "accent": "violet",
        "dim": "grey50",
        "user": "bold violet",
        "agent": "bold violet",
        "success": "bold violet",
        "warning": "bold yellow",
        "error": "bold red",
        "info": "bold violet"
    },
    "orange": {
        "title": "bold orange1",
        "accent": "orange1",
        "dim": "grey50",
        "user": "bold orange1",
        "agent": "bold orange1",
        "success": "bold orange1",
        "warning": "bold yellow",
        "error": "bold red",
        "info": "bold orange1"
    }
}

current_theme_name = "green"   # Default theme

def get_theme_config():
    return THEME_CONFIGS.get(current_theme_name, THEME_CONFIGS["green"])

# Initialize console with the default theme
console = Console(theme=Theme(get_theme_config()))

def get_theme():
    return get_theme_config()

def update_console_theme():
    """Updates the console's theme based on current_theme_name."""
    global console
    console.theme = Theme(get_theme_config())

def apply_theme_placeholders(text):
    """Replaces semantic style tags with the current theme's rich styles."""
    theme = get_theme_config()
    for token, style in theme.items():
        text = text.replace(f"[{token}]", f"[{style}]").replace(f"[/{token}]", f"[/{style}]")
    return text
