import argparse
import asyncio
import os
from agents.chat_agent import ChatAgent
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.live import Live
from rich.panel import Panel
from rich.align import Align
from rich.columns import Columns
from rich.text import Text
from rich.theme import Theme
import time as t
from tools.mcp_registry import mcp_manager

# Theme Definitions
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

current_theme_name = "green"   # Defualt theme

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

def format_response(text, theme):
    """Extracts <thought> tags and renders them separately. Handles unclosed tags during streaming."""
    import re
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

async def _load_mcp_from_env():
    """Initializes MCP servers listed in the environment."""
    server_list = os.getenv("MCP_SERVERS", "").split(",")
    for s in server_list:
        name = s.strip()
        if not name: continue
        cmd = os.getenv(f"MCP_SERVER_{name.upper()}_COMMAND")
        if cmd:
            await mcp_manager.add_server(name, cmd)

def show_welcome_panel(agent, current_mode):
    theme = get_theme()
    
    # ASCII Art Title (Clean Block)
    # Using a simple block representation for "FREE CODE"
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

def start_chat(mode="offline"):
    # Define our two mode prompts
    CHAT_MODE_PROMPT = "You are a helpful AI assistant with access to local tools. Use markdown for code and lists."
    RUN_MODE_PROMPT = "You are a technical assistant. If code is requested, return ONLY raw executable code without markdown, comments, or explanations."
    
    current_mode = "chat"
    agent = ChatAgent(system_prompt=CHAT_MODE_PROMPT,mode=mode)
    
    show_welcome_panel(agent, current_mode)
    
    # Load initial MCP servers
    asyncio.run(_load_mcp_from_env())
    agent._update_tools_prompt()
    
    while True:
        try:
            theme = get_theme()
            # Boxed input simulation
            console.print(f"[dim]╭[/dim]{'─' * (console.width - 2)}[dim]╮[/dim]")
            user_input = console.input(f"[dim]│[/dim] [{theme['user']}]❯ [/{theme['user']}]").strip()
            console.print(f"[dim]╰[/dim]{'─' * (console.width - 2)}[dim]╯[/dim]")
            
            if not user_input:
                continue

            # Command Handling
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd == "/voice":
                    while True:
                        console.print("[bold cyan]Voice Mode Activated. Type ctrl-C to exit voice mode.[/bold cyan]")
                        from tools.voice_handler import get_voice_input
                        try:
                            voiced_text = get_voice_input()
                            if voiced_text:
                                console.print(f"[bold cyan]You (Voice) ❯[/bold cyan] {voiced_text}")
                                # Check if they said a command
                                if voiced_text.startswith("/"):
                                    user_input = voiced_text
                                    break
                                # If it's just text, we send it to agent.run(user_input)
                                user_input = voiced_text
                                break
                            else:
                                console.print("[bold red]No speech detected.[/bold red]")
                                continue
                        except KeyboardInterrupt:
                            console.print("[bold cyan]Voice Mode Exited.[/bold cyan]")
                            break
                    if not user_input:
                        continue
                elif cmd == "/exit":
                    console.print(f"[{get_theme()['warning']}]Exiting...[/{get_theme()['warning']}]")
                    t.sleep(1)
                    break
                elif cmd == "/cls":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    show_welcome_panel(agent, current_mode)
                    continue
                elif cmd == "/help":
                    command_theme = get_theme()
                    help_content = (
                        f"[{command_theme['accent']}]Available Commands:[/{command_theme['accent']}]\n"
                        f"  /chat           - Switch to CHAT Mode (conversational)\n"
                        f"  /run            - Switch to RUN Mode (direct code execution)\n"
                        f"  /voice          - Interactive voice input mode\n"
                        f"  /cls            - Clear console screen (keeps history)\n"
                        f"  /online         - Use Gemini Cloud API (Advanced capabilities)\n"
                        f"  /offline        - Use Ollama Local LLMs (Private & Free)\n"
                        f"  /set_model <m>  - Switch the current model (e.g., deepseek-coder)\n"
                        f"  /list_models    - See available local/online models\n"
                        f"  /mcp <n> <c>    - Connect an MCP Tool Server\n"
                        f"  /save           - Save current conversation to JSON\n"
                        f"  /clear          - Clear conversation history\n"
                        f"  /help           - Show this command list\n"
                        "  /exit           - Close the application\n"
                        "  /theme <name>   - Switch UI theme (green/blue)"
                    )
                    console.print(Panel(help_content, title="Help Menu", border_style=get_theme()["accent"]))
                    continue
                elif cmd.startswith("/theme"):
                    global current_theme_name
                    parts = user_input.split(maxsplit=1)
                    if len(parts) >= 2:
                        new_theme = parts[1].strip().lower()
                        if new_theme in THEME_CONFIGS:
                            current_theme_name = new_theme
                            update_console_theme()
                            console.print(f"[success]Theme switched to {new_theme.upper()}[/success]")
                        else:
                            console.print(f"[warning]Available themes: {', '.join(THEME_CONFIGS.keys())}[/warning]")
                    else:
                        console.print(f"[info]Current theme: {current_theme_name}. Usage: /theme <name>[/info]")
                    continue
                elif cmd == "/online":
                    current_mode = "chat"
                    agent.set_mode("online")
                    console.print(f"[{get_theme()['success']}]Mode switched to ONLINE (Model: {agent.model})[/{get_theme()['success']}]")
                    continue
                elif cmd == "/offline":
                    current_mode = "chat"
                    agent.set_mode("offline")
                    console.print(f"[{get_theme()['accent']}]Mode switched to OFFLINE (Model: {agent.model})[/{get_theme()['accent']}]")
                    continue
                elif cmd == "/chat":
                    current_mode = "chat"
                    agent.set_system_prompt(CHAT_MODE_PROMPT)
                    console.print(f"[{get_theme()['info']}]Mode switched to CHAT (Conversational)[/{get_theme()['info']}]")
                    continue
                elif cmd == "/run":
                    current_mode = "run"
                    agent.set_system_prompt(RUN_MODE_PROMPT)
                    console.print(f"[{get_theme()['error']}]Mode switched to RUN (Code Only)[/{get_theme()['error']}]")
                    continue
                elif cmd == "/clear":
                    agent.messages = [{"role": "system", "content": agent.base_system_prompt + agent.tools_prompt}]
                    console.print(f"[{get_theme()['warning']}]Conversation history cleared.[/{get_theme()['warning']}]")
                    continue
                elif cmd.startswith("/mcp"):
                    parts = user_input.split(maxsplit=2)
                    if len(parts) >= 3:
                        name = parts[1]
                        exec_cmd = parts[2]
                        asyncio.run(mcp_manager.add_server(name, exec_cmd))
                        agent._update_tools_prompt()
                    else:
                        console.print("[yellow]Usage: /mcp <name> <command>[/yellow]")
                        console.print("[dim]Example: /mcp google npx -y @modelcontextprotocol/server-google-search[/dim]")
                    continue
                elif cmd == "/save":
                    import json
                    filename = f"chat_save_{int(t.time())}.json"
                    with open(filename, "w") as f:
                        # Filter out system messages as requested
                        save_history = [m for m in agent.messages if m["role"] != "system"]
                        json.dump(save_history, f, indent=2)
                    console.print(f"[{get_theme()['success']}]Conversation saved to {filename} (system prompts excluded)[/{get_theme()['success']}]")
                    continue
                elif cmd == "/list_models":
                    console.print(f"[{get_theme()['accent']}]Local Models:[/{get_theme()['accent']}]")
                    for model in agent.get_available_models():
                        console.print(f"  - {model}")
                    console.print(f"\n[{get_theme()['accent']}]Online Models (with Auto-Fallback):[/{get_theme()['accent']}]")
                    for m in agent.online_models:
                        console.print(f"  - {m}")
                    continue
                elif cmd.startswith("/set_model"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) >= 2:
                        model = parts[1].strip()
                        agent.set_model(model)
                        console.print(f"[{get_theme()['success']}]Model set to {model}[/{get_theme()['success']}]")
                    else:
                        console.print(f"[{get_theme()['warning']}]Usage: /set_model <model>[/{get_theme()['warning']}]")
                    continue
                else:
                    console.print(f"[{get_theme()['error']}]Unknown command: {cmd}[/{get_theme()['error']}]")
                    continue

            if user_input.lower() in ["exit", "quit"]:
                console.print(f"[{theme['warning']}]Exiting...[/{theme['warning']}]")
                t.sleep(1)
                break
            
            prefix_text = f"[{theme['agent']}]{agent.model}[{agent.mode}] ❯ [/{theme['agent']}]"
            full_response = ""
            current_status = ""
            terminal_command = ""
            terminal_output = ""
            
            with Live("", console=console, refresh_per_second=10) as live:
                try:
                    gen = agent.run(user_input)
                    try:
                        chunk = next(gen)
                        while True:
                            if isinstance(chunk, str) and chunk.startswith("__ASK_PERMISSION__"):
                                parts = chunk.split(":", 2)
                                tool_name = parts[1]
                                tool_params = parts[2]
                                
                                live.stop()
                                console.print(f"\n[{get_theme()['warning']}]🛡️ Permission Required:[/{get_theme()['warning']}] Tool [{get_theme()['accent']}]{tool_name}[/{get_theme()['accent']}] called with parameters [dim]{tool_params}[/dim]")
                                choice = console.input(f"[{get_theme()['success']}]Allow? (Y/n): [/{get_theme()['success']}]").strip().lower()
                                approved = choice in ["", "y", "yes"]
                                
                                live.start()
                                chunk = gen.send(approved)
                            elif isinstance(chunk, str) and chunk.startswith("__UI_STATUS__"):
                                status_raw = chunk.replace("__UI_STATUS__:", "")
                                if status_raw.startswith("EXEC_CMD:"):
                                    terminal_command = status_raw.replace("EXEC_CMD:", "")
                                    terminal_output = ""
                                    current_status = "" # Hide standard status when terminal is active
                                else:
                                    current_status = apply_theme_placeholders(status_raw)
                                    terminal_command = "" # Hide terminal if we switch back to normal status
                                
                                live.update(Group(
                                    prefix_text,
                                    format_response(full_response, theme),
                                    render_terminal_box(terminal_command, terminal_output) if terminal_command else Text(""),
                                    f"\n [italic yellow]⚡ {current_status}[/italic yellow]" if current_status else Text("")
                                ))
                                chunk = next(gen)
                            elif isinstance(chunk, str) and chunk.startswith("__TOOL_STREAM__"):
                                terminal_output += chunk.replace("__TOOL_STREAM__:", "")
                                live.update(Group(
                                    prefix_text,
                                    format_response(full_response, theme),
                                    render_terminal_box(terminal_command, terminal_output),
                                ))
                                chunk = next(gen)
                            else:
                                if chunk is not None:
                                    if current_status:
                                        current_status = "" 
                                    full_response += chunk
                                    
                                    live.update(Group(
                                        prefix_text,
                                        format_response(full_response, theme),
                                        render_terminal_box(terminal_command, terminal_output) if terminal_command else Text("")
                                    ))
                                chunk = next(gen)
                    except StopIteration:
                        # Final update
                        live.update(format_response(full_response, theme))
                except KeyboardInterrupt:
                    # Check if a command was running
                    if terminal_command:
                        live.stop()
                        console.print(f"\n[{theme['warning']}]⚠️ Command is still running.[/{theme['warning']}]")
                        choice = console.input("[bold]Action? (k: kill, b: background, c: continue): [/bold]").strip().lower()
                        from tools.terminal_manager import terminal_manager
                        if choice == 'k':
                            terminal_manager.interrupt()
                            console.print("[red]Process Interrupted.[/red]")
                            break
                        elif choice == 'b':
                            console.print("[green]Process moved to background.[/green]")
                            break
                        else:
                            live.start()
                            # How to resume? We'd need to re-enter the loop. 
                            # For now, we'll just stop the current turn gracefully.
                            break
                    else:
                        live.update(format_response(full_response + " [dim](stopped)[/dim]", theme))
            
            console.print()
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Exiting...[/bold yellow]")
            break

def main():
    parser = argparse.ArgumentParser(description="LLM Agent CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Start a chat session")
    chat_parser.add_argument("--mode", type=str, default="offline", help="Mode to run the agent in (offline/online)")
    
    # Run task command
    run_parser = subparsers.add_parser("run", help="Run a single task string")
    run_parser.add_argument("task", type=str, help="The task for the agent to execute")
    run_parser.add_argument("--mode", type=str, default="offline", help="Mode to run the agent in (offline/online)")


    args = parser.parse_args()

    if args.command == "chat":
        start_chat(args.mode)
    elif args.command == "run":
        RUN_MODE_PROMPT = "You are a technical assistant. If code is requested, return ONLY raw executable code without markdown, comments, or explanations."
        agent = ChatAgent(system_prompt=RUN_MODE_PROMPT,mode=args.mode)
        console.print(f"[bold red]Running Automated Task:[/bold red] {args.task}")
        theme = get_theme()
        prefix_text = f"[{theme['agent']}]{agent.model}[{agent.mode}] ❯ [/{theme['agent']}]"
        full_response = ""
        current_status = ""
        terminal_command = ""
        terminal_output = ""

        with Live("", console=console, refresh_per_second=10) as live:
            try:
                gen = agent.run(args.task)
                try:
                    chunk = next(gen)
                    while True:
                        if isinstance(chunk, str) and chunk.startswith("__ASK_PERMISSION__"):
                            parts = chunk.split(":", 2)
                            tool_name = parts[1]
                            tool_params = parts[2]
                            
                            live.stop()
                            console.print(f"\n[bold yellow]🛡️ Permission Required:[/bold yellow] Tool [bold cyan]{tool_name}[/bold cyan] called with parameters [dim]{tool_params}[/dim]")
                            choice = console.input("[bold green]Confirm? (Y/n): [/bold green]").strip().lower()
                            approved = choice in ["", "y", "yes"]
                            
                            live.start()
                            chunk = gen.send(approved)
                        elif isinstance(chunk, str) and chunk.startswith("__UI_STATUS__"):
                            status_raw = chunk.replace("__UI_STATUS__:", "")
                            if status_raw.startswith("EXEC_CMD:"):
                                terminal_command = status_raw.replace("EXEC_CMD:", "")
                                terminal_output = ""
                                current_status = ""
                            else:
                                current_status = apply_theme_placeholders(status_raw)
                                terminal_command = ""
                            
                            live.update(Group(
                                prefix_text,
                                format_response(full_response, theme),
                                render_terminal_box(terminal_command, terminal_output) if terminal_command else Text(""),
                                f"\n [italic yellow]⚡ {current_status}[/italic yellow]" if current_status else Text("")
                            ))
                            chunk = next(gen)
                        elif isinstance(chunk, str) and chunk.startswith("__TOOL_STREAM__"):
                            terminal_output += chunk.replace("__TOOL_STREAM__:", "")
                            live.update(Group(
                                prefix_text,
                                format_response(full_response, theme),
                                render_terminal_box(terminal_command, terminal_output),
                            ))
                            chunk = next(gen)
                        else:
                            if chunk is not None:
                                if current_status:
                                    current_status = "" 
                                full_response += chunk
                                
                                live.update(Group(
                                    prefix_text,
                                    format_response(full_response, theme),
                                    render_terminal_box(terminal_command, terminal_output) if terminal_command else Text("")
                                ))
                            chunk = next(gen)
                except StopIteration:
                    live.update(format_response(full_response, theme))
            except KeyboardInterrupt:
                if terminal_command:
                    live.stop()
                    console.print(f"\n[{theme['warning']}]⚠️ Command is still running.[/{theme['warning']}]")
                    choice = console.input("[bold]Action? (k: kill, b: background, c: continue): [/bold]").strip().lower()
                    from tools.terminal_manager import terminal_manager
                    if choice == 'k':
                        terminal_manager.interrupt()
                        console.print("[red]Process Interrupted.[/red]")
                    elif choice == 'b':
                        console.print("[green]Process moved to background.[/green]")
                    else:
                        live.update(format_response(full_response, theme))
                else:
                    live.update(format_response(full_response + " [dim](stopped)[/dim]", theme))
        console.print()
    else:
        parser.print_help()
