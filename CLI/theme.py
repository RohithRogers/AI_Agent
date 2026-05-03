from rich.console import Console
from rich.theme import Theme

THEME_CONFIGS = {
    "cyberpunk": {
        "title": "bold #FF003C",
        "accent": "#00F0FF",
        "dim": "#711c91",
        "user": "bold #00F0FF",
        "agent": "bold #FF003C",
        "success": "bold #FCEE0A",
        "warning": "bold #FF71CE",
        "error": "bold #FF003C",
        "info": "bold #01CDFE",
        "thought": "italic #711c91",
        "thought_border": "#B967FF",
        "gradient": ["#FCEE0A", "#FF003C", "#711c91", "#00F0FF"]
    },
    "miami_vice": {
        "title": "bold #FF007F",
        "accent": "#00E5FF",
        "dim": "#A700FF",
        "user": "bold #00E5FF",
        "agent": "bold #FF007F",
        "success": "bold #00FF9D",
        "warning": "bold #FF7B00",
        "error": "bold #FF0055",
        "info": "bold #00E5FF",
        "thought": "italic #A700FF",
        "thought_border": "#FF7B00",
        "gradient": ["#FF7B00", "#FF007F", "#A700FF", "#00E5FF"]
    },
    "aurora": {
        "title": "bold #00C9FF",
        "accent": "#92FE9D",
        "dim": "#066A75",
        "user": "bold #92FE9D",
        "agent": "bold #00C9FF",
        "success": "bold #00FF9D",
        "warning": "bold #EAE509",
        "error": "bold #FF0055",
        "info": "bold #00E5FF",
        "thought": "italic #AB47BC",
        "thought_border": "#00C9FF",
        "gradient": ["#00FF9D", "#00C9FF", "#92FE9D", "#AB47BC"]
    },
    "lava": {
        "title": "bold #FF5400",
        "accent": "#FFD000",
        "dim": "#8A1C14",
        "user": "bold #FFD000",
        "agent": "bold #FF5400",
        "success": "bold #FF9900",
        "warning": "bold #FFD000",
        "error": "bold #FF0000",
        "info": "bold #FF5400",
        "thought": "italic #FF0000",
        "thought_border": "#FF5400",
        "gradient": ["#FF0000", "#FF5400", "#FF9900", "#FFD000"]
    },
    "galaxy": {
        "title": "bold #5C258D",
        "accent": "#00F0FF",
        "dim": "#4389A2",
        "user": "bold #00F0FF",
        "agent": "bold #FF00FF",
        "success": "bold #00FF9D",
        "warning": "bold #FDEB71",
        "error": "bold #FF0055",
        "info": "bold #4389A2",
        "thought": "italic #5C258D",
        "thought_border": "#FF00FF",
        "gradient": ["#FF00FF", "#5C258D", "#4389A2", "#00F0FF"]
    },
    "toxic": {
        "title": "bold #00FF87",
        "accent": "#60EFFF",
        "dim": "#008000",
        "user": "bold #60EFFF",
        "agent": "bold #00FF87",
        "success": "bold #00FF87",
        "warning": "bold #FFFF00",
        "error": "bold #FF0055",
        "info": "bold #60EFFF",
        "thought": "italic #008000",
        "thought_border": "#00FF87",
        "gradient": ["#00FF87", "#60EFFF", "#00FF87"]
    },
    "grey": {
        "title": "bold #E0E0E0",
        "accent": "#9E9E9E",
        "dim": "#616161",
        "user": "bold #FFFFFF",
        "agent": "bold #BDBDBD",
        "success": "bold #9E9E9E",
        "warning": "bold #757575",
        "error": "bold #424242",
        "info": "bold #BDBDBD",
        "thought": "italic #757575",
        "thought_border": "#BDBDBD",
        "gradient": ["#F5F5F5", "#9E9E9E", "#757575", "#424242"]
    }
}

current_theme_name = "grey"   # Default theme

def get_theme_config():
    return THEME_CONFIGS.get(current_theme_name, THEME_CONFIGS["grey"])

def _get_rich_theme_dict():
    config = get_theme_config().copy()
    if "gradient" in config:
        del config["gradient"]
    return config

# Initialize console with the default theme
console = Console(theme=Theme(_get_rich_theme_dict()))

def get_theme():
    return get_theme_config()

def update_console_theme():
    """Updates the console's theme based on current_theme_name."""
    global console
    console.theme = Theme(_get_rich_theme_dict())

def apply_theme_placeholders(text):
    """Replaces semantic style tags with the current theme's rich styles."""
    theme = _get_rich_theme_dict()
    for token, style in theme.items():
        text = text.replace(f"[{token}]", f"[{style}]").replace(f"[/{token}]", f"[/{style}]")
    return text
