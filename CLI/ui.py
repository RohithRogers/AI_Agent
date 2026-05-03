import re
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich.markdown import Markdown
from rich.align import Align
from rich import box
from CLI.theme import get_theme, console

# --- Gradient Title Art Generators ---
BLOCK_ART = """
███████╗██╗   ██╗███╗   ██╗████████╗██╗  ██╗██╗ ██████╗ 
██╔════╝╚██╗ ██╔╝████╗  ██║╚══██╔══╝██║  ██║██║██╔════╝ 
███████╗ ╚████╔╝ ██╔██╗ ██║   ██║   ███████║██║██║      
╚════██║  ╚██╔╝  ██║╚██╗██║   ██║   ██╔══██║██║██║      
███████║   ██║   ██║ ╚████║   ██║   ██║  ██║██║╚██████╗ 
╚══════╝   ╚═╝   ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝ ╚═════╝ 
"""

def _hex_to_rgb(hex_code: str):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

def _rgb_to_hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"

def _interpolate_color(c1, c2, t):
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    t = t * t * (3 - 2 * t)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return _rgb_to_hex(r, g, b)

def _interpolate_multi(colors, t):
    if len(colors) == 1: return colors[0]
    segments = len(colors) - 1
    scaled_t = t * segments
    idx = int(scaled_t)
    if idx >= segments: return colors[-1]
    return _interpolate_color(colors[idx], colors[idx+1], scaled_t - idx)

def generate_gradient_art(colors: list) -> Text:
    lines = [line for line in BLOCK_ART.strip("\n").split("\n")]
    max_len = max(len(line) for line in lines) if lines else 1
    gradient_text = Text()
    
    for line in lines:
        for x, char in enumerate(line):
            t = x / max_len if max_len > 0 else 0
            if char in "╚═╗╔╝║╝":
                color = _interpolate_multi(colors, t * 0.8)
                gradient_text.append(char, style=f"dim {color}")
            else:
                color = _interpolate_multi(colors, t)
                gradient_text.append(char, style=f"bold {color}")
        gradient_text.append("\n")
    return gradient_text
# ------------------------------------

def format_response(text, theme):
    """Extracts <thought> tags and renders them separately."""
    thought_pattern = re.compile(r'<thought>(.*?)</thought>', re.DOTALL)
    thoughts = thought_pattern.findall(text)
    
    last_thought_start = text.rfind('<thought>')
    last_thought_end = text.rfind('</thought>')
    
    streaming_thought = ""
    if last_thought_start > last_thought_end:
        streaming_thought = text[last_thought_start + 9:]
        clean_text = text[:last_thought_start]
        clean_text = thought_pattern.sub("", clean_text).strip()
    else:
        clean_text = thought_pattern.sub("", text).strip()
    
    elements = []
    if thoughts or streaming_thought:
        all_thoughts = thoughts + ([streaming_thought] if streaming_thought else [])
        combined_thoughts = "\n".join(all_thoughts).strip()
        elements.append(Panel(
            Text(combined_thoughts, style=theme.get('thought', 'italic grey50')),
            title=f"[{theme.get('accent', 'white')}]🧠 Reasoning[/{theme.get('accent', 'white')}]",
            title_align="left",
            border_style=theme.get('thought_border', 'grey30'),
            box=box.MINIMAL_HEAVY_HEAD,
            padding=(0, 2),
            expand=False
        ))
    
    if clean_text:
        elements.append(Markdown(clean_text, code_theme="dracula"))
    
    return Group(*elements) if elements else Text("")

def render_terminal_box(command, output_history):
    theme = get_theme()
    terminal_text = Text()
    if command:
        terminal_text.append(f"❯ {command}\n", style=f"bold {theme['accent']}")
    
    lines = output_history.splitlines()
    if len(lines) > 15:
        output_history = "\n".join(lines[-15:])
        terminal_text.append("... (earlier output truncated)\n", style="dim")
    
    terminal_text.append(output_history, style="white")
    
    return Panel(
        terminal_text,
        title="[bold #FF5F56]●[/] [bold #FFBD2E]●[/] [bold #27C93F]●[/] [dim]System Execution[/dim]",
        title_align="left",
        border_style=theme.get('thought_border', 'grey50'),
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True
    )

def show_welcome_panel(agent, current_mode):
    theme = get_theme()
    
    # 3D Gradient Art overriding the core color scheme
    gradient_colors = theme.get("gradient", ["#00F0FF", "#FF007F"])
    custom_art = generate_gradient_art(gradient_colors)
    
    subtitle = Align.left(f"[dim]Synthic can write, test and debug code right from your terminal.\nTry asking me something!\n[/dim]")
    
    
    status_lines = Group(
        Text.assemble((f" ● ", theme["accent"]), (f"Logged in: ", "white"), (f"System User", "dim")),
        Text.assemble((f" ● ", theme["accent"]), (f"Process: ", "white"), (f"{agent.mode}", "dim")),
        Text.assemble((f" ● ", theme["accent"]), (f"Model: ", "white"), (f"{agent.model}", "dim")),
        Text.assemble((f" ● ", theme["accent"]), (f"Context: ", "white"), (f"{current_mode}", "dim")),
    )

    content = Group(
        Align.left(custom_art),
        subtitle,
        status_lines
    )

    main_banner = Panel(
        content,
        border_style=theme["accent"],
        padding=(1, 4),
        title="[dim]Welcome[/dim]",
        title_align="left"
    )

    console.print(main_banner)
    console.print(f"\n[dim]Enter [/dim][{theme['accent']}]/help[/{theme['accent']}] [dim]for list of commands.[/dim]\n")
