import re
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich.markdown import Markdown
from rich.align import Align
from CLI.theme import get_theme, console

def format_response(text, theme):
    """Extracts <thought> tags and renders them separately. Handles unclosed tags during streaming."""
    # Match fully closed <thought>...</thought>
    thought_pattern = re.compile(r'<thought>(.*?)</thought>', re.DOTALL)
    thoughts = thought_pattern.findall(text)
    
    # Check for an unclosed <thought> tag at the end (for streaming)
    last_thought_start = text.rfind('<thought>')
    last_thought_end = text.rfind('</thought>')
    
    streaming_thought = ""
    if last_thought_start > last_thought_end:
        streaming_thought = text[last_thought_start + 9:]
        # Remove the unclosed thought from main text
        clean_text = text[:last_thought_start]
        # Also apply the pattern sub to remove any closed thoughts before it
        clean_text = thought_pattern.sub("", clean_text).strip()
    else:
        # standard case: everything is closed or no unclosed at the end
        clean_text = thought_pattern.sub("", text).strip()
    
    elements = []
    if thoughts or streaming_thought:
        all_thoughts = thoughts + ([streaming_thought] if streaming_thought else [])
        combined_thoughts = "\n".join(all_thoughts).strip()
        elements.append(Panel(
            Text(combined_thoughts, style="italic grey50"),
            title="[dim]Reasoning[/dim]",
            border_style="grey30",
            padding=(0, 1),
            expand=False
        ))
    
    if clean_text:
        elements.append(Markdown(clean_text))
    
    return Group(*elements) if elements else Text("")

def render_terminal_box(command, output_history):
    theme = get_theme()
    terminal_text = Text()
    if command:
        terminal_text.append(f"❯ {command}\n", style=f"bold {theme['accent']}")
    
    # We only show the last 15 lines of output in the box to keep it compact
    lines = output_history.splitlines()
    if len(lines) > 15:
        output_history = "\n".join(lines[-15:])
        terminal_text.append("... (earlier output truncated)\n", style="dim")
    
    terminal_text.append(output_history, style="white")
    
    return Panel(
        terminal_text,
        title="[bold grey70]PowerShell Session[/bold grey70]",
        border_style="grey50",
        padding=(0, 1),
        expand=True
    )

def show_welcome_panel(agent, current_mode):
    theme = get_theme()
    
    # ASCII Art Title (Clean Block)
    ascii_art = f"""
  [{theme['accent']}] ___  ___  ___  ___    ___  ___  ___  ___ 
  | __|| _ \| __|| __|  / __|/ _ \|   \| __|
  | _| |   /| _| | _|  | (__| (_) | |) | _| 
  |_|  |_|_\|___||___|  \___|\___/|___/|___|[/{theme['accent']}]
"""
    
    subtitle = Align.left(f"[dim]AI Agent Command-line Interface[/dim]")
    
    description = Text.assemble(
        (f"\nFree Code can write, test and debug code right from your terminal.\n", "white"),
        (f"Describe a task to get started or enter ", "white"),
        (f"?", theme["accent"]), (f" for help. AI, check for mistakes.\n", "white")
    )
    
    status_lines = Group(
        Text.assemble((f" ● ", theme["accent"]), (f"Logged in: ", "white"), (f"System User", "dim")),
        Text.assemble((f" ● ", theme["accent"]), (f"Process: ", "white"), (f"{agent.mode}", "dim")),
        Text.assemble((f" ● ", theme["accent"]), (f"Model: ", "white"), (f"{agent.model}", "dim")),
        Text.assemble((f" ● ", theme["accent"]), (f"Context: ", "white"), (f"{current_mode}", "dim")),
    )

    content = Group(
        Align.left(ascii_art),
        subtitle,
        description,
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
