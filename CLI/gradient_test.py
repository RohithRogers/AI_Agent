import sys
from rich.console import Console
from rich.text import Text

# Hardcoded Solid Block ASCII Art for "FreeCode"
# This mimics the thick, premium 8-bit blocky styles.
BLOCK_ART = """
███████╗██████╗ ███████╗███████╗    ██████╗ ██████╗ ██████╗ ███████╗
██╔════╝██╔══██╗██╔════╝██╔════╝   ██╔════╝██╔═══██╗██╔══██╗██╔════╝
█████╗  ██████╔╝█████╗  █████╗     ██║     ██║   ██║██║  ██║█████╗  
██╔══╝  ██╔══██╗██╔══╝  ██╔══╝     ██║     ██║   ██║██║  ██║██╔══╝  
██║     ██║  ██║███████╗███████╗   ╚██████╗╚██████╔╝██████╔╝███████╗
╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝    ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
"""

def hex_to_rgb(hex_code: str) -> tuple:
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"

def interpolate_color(color1: str, color2: str, t: float) -> str:
    """Interpolate between two hex colors by percentage t (0.0 to 1.0)"""
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)
    
    # We use ease_in_out for a smoother vibrant pop in the middle
    t = t * t * (3 - 2 * t) 
    
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    
    return rgb_to_hex(r, g, b)

def interpolate_multi(colors: list, t: float) -> str:
    if len(colors) == 1: return colors[0]
    segments = len(colors) - 1
    scaled_t = t * segments
    idx = int(scaled_t)
    if idx >= segments: return colors[-1]
    segment_t = scaled_t - idx
    return interpolate_color(colors[idx], colors[idx+1], segment_t)

def generate_gradient_art(art_string: str, colors: list) -> Text:
    lines = [line for line in art_string.strip("\n").split("\n")]
    max_len = max(len(line) for line in lines) if lines else 1
    
    gradient_text = Text()
    
    for line in lines:
        for x, char in enumerate(line):
            t = x / max_len if max_len > 0 else 0
            
            # The trick: Darken the frame '╚' '╗' '╔' characters to act as pseudo-shadows!
            if char in "╚═╗╔╝║╝":
                shadow_t = t * 0.8  # darken the shadow
                color = interpolate_multi(colors, shadow_t)
                gradient_text.append(char, style=f"dim {color}")
            else:
                color = interpolate_multi(colors, t)
                gradient_text.append(char, style=f"bold {color}")
        gradient_text.append("\n")
        
    return gradient_text

if __name__ == "__main__":
    console = Console()
    
    # Ultra-Vibrant, Mind-Blowing Gradients
    THEMES = {
        "Cyberpunk": ["#FCEE0A", "#FF003C", "#711c91", "#00F0FF"], 
        "Miami Vice": ["#FF7B00", "#FF007F", "#A700FF", "#00E5FF"],
        "Aurora": ["#00FF9D", "#00C9FF", "#92FE9D", "#AB47BC"],
        "Lava": ["#FF0000", "#FF5400", "#FF9900", "#FFD000"],
        "Galaxy": ["#FF00FF", "#5C258D", "#4389A2", "#00F0FF"],
        "Toxic": ["#00FF87", "#60EFFF", "#00FF87"]
    }
    
    for theme_name, colors in THEMES.items():
        console.print(f"\n[bold white]--- {theme_name} Theme ---[/bold white]")
        art = generate_gradient_art(BLOCK_ART, colors)
        console.print(art)
        
    console.print("\n  [dim]Tips for getting started:[/dim]")
    console.print("  [white]Describe a task or use[/white] [bold #00F0FF]\"\"\"...[/bold #00F0FF] [white]for multi-line prompts.[/white]\n")
