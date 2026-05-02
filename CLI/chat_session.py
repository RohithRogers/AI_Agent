import asyncio
import os
import sys
import time as t
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from agents.chat_agent import ChatAgent
from tools.mcp_registry import mcp_manager
import CLI.theme as theme_mod
from CLI.theme import console, get_theme, update_console_theme, apply_theme_placeholders
from CLI.ui import format_response, render_terminal_box, show_welcome_panel
from CLI.mcp_loader import _load_mcp_from_env
from remote.telegram_tool import start_bot_chat 

def start_chat(mode="offline"):
    # Define our two mode prompts
    CHAT_MODE_PROMPT = "You are a helpful AI assistant. You are in CHAT mode and do NOT have access to tools. Focus on conversation and answering questions. If you need to use tools ask the user to change to AGENT mode (/agent) for task execution."
    RUN_MODE_PROMPT = "You are a powerful AI Agent with full access to system tools. Use them to help the user complete their tasks."
    TELEGRAM_MODE_PROMPT = "You are an AI Agent controlled via Telegram. You have access to system tools. Respond through the Telegram bridge."
    
    current_mode = "chat"
    agent = ChatAgent(system_prompt=CHAT_MODE_PROMPT, mode=mode, tools_enabled=False)
    multiline_mode = False
    
    show_welcome_panel(agent, current_mode)
    
    # Load initial MCP servers
    asyncio.run(_load_mcp_from_env())
    agent._update_tools_prompt()
    
    attachments = []
    
    while True:
        try:
            theme = get_theme()
            if attachments:
                console.print(f"[dim]📎 Attachments: {', '.join(os.path.basename(a) for a in attachments)}[/dim]")
                
            # Boxed input simulation
            console.print(f"[dim]╭[/dim]{'─' * (console.width - 2)}[dim]╮[/dim]")
            if multiline_mode:
                console.print(f"[dim]│[/dim] [{theme['error']}]MULTI-LINE MODE[/{theme['error']}] (Ctrl+Z + Enter to submit)")
                user_input = sys.stdin.read().strip()
            else:
                user_input = console.input(f"[dim]│[/dim] [{theme['user']}]❯ [/{theme['user']}]").strip()
            console.print(f"[dim]╰[/dim]{'─' * (console.width - 2)}[dim]╯[/dim]")
            
            # Triple quote detection for quick multi-line paste
            if user_input.startswith('"""') and not user_input.endswith('"""', 3):
                console.print(f"[{theme['info']}]Triple-quote detected. Entering multi-line mode. End with '\"\"\"' to submit.[/{theme['info']}]")
                lines = [user_input[3:]]
                while True:
                    line = input("... ")
                    if '"""' in line:
                        lines.append(line.replace('"""', ''))
                        break
                    lines.append(line)
                user_input = "\n".join(lines).strip()

            if not user_input:
                continue

            # Command Handling
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd.startswith("/attach"):
                    parts = user_input.split(" ", 1)
                    if len(parts) > 1:
                        path_str = parts[1].strip().strip('"').strip("'")
                        if os.path.exists(path_str):
                            attachments.append(path_str)
                            console.print(f"[{theme['success']}]Attached {os.path.basename(path_str)}[/]")
                        else:
                            console.print(f"[{theme['error']}]File not found: {path_str}[/]")
                    else:
                        console.print(f"[{theme['warning']}]Usage: /attach <path>[/]")
                    continue
                elif cmd == "/paste_image":
                    try:
                        from PIL import ImageGrab
                        img = ImageGrab.grabclipboard()
                        if img is not None:
                            import tempfile
                            import time
                            temp_path = os.path.join(tempfile.gettempdir(), f"clipboard_{int(time.time())}.png")
                            img.save(temp_path, "PNG")
                            attachments.append(temp_path)
                            console.print(f"[{theme['success']}]Image pasted from clipboard and attached.[/]")
                        else:
                            console.print(f"[{theme['warning']}]No image found in clipboard.[/]")
                    except ImportError:
                        console.print(f"[{theme['error']}]Pillow is required for clipboard support. Run: pip install Pillow[/]")
                    except Exception as e:
                        console.print(f"[{theme['error']}]Error reading clipboard: {e}[/]")
                    continue
                elif cmd == "/auto":
                    agent.auto_route = True
                    agent.manual_mode = False
                    console.print(f"[{theme['success']}]Auto Model Routing ENABLED[/]")
                    continue
                elif cmd == "/manual":
                    agent.auto_route = False
                    agent.manual_mode = True
                    console.print(f"[{theme['success']}]Manual Model Selection ENABLED[/]")
                    continue
                elif cmd == "/clear_attachments":
                    attachments.clear()
                    console.print(f"[{theme['success']}]Attachments cleared.[/]")
                    continue
                elif cmd == "/voice":
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
                    # If voice returned a command, re-enter the loop so it gets handled properly
                    if user_input.startswith("/"):
                        continue
                elif cmd == "/exit":
                    console.print(f"[{get_theme()['warning']}]Exiting...[/{get_theme()['warning']}]")
                    t.sleep(1)
                    break
                elif cmd == "/cls":
                    os.system('cls')
                    show_welcome_panel(agent, current_mode)
                    continue
                elif cmd == "/help":
                    command_theme = get_theme()
                    help_content = (
                        f"[{command_theme['accent']}]Available Commands:[/{command_theme['accent']}]\n"
                        f"  /chat           - Switch to CHAT Mode (conversational)\n"
                        f"  /agent          - Switch to AGENT Mode (direct code execution)\n"
                        f"  /voice          - Interactive voice input mode\n"
                        f"  /cls            - Clear console screen (keeps history)\n"
                        f"  /online         - Use Gemini/Groq Cloud API (Advanced capabilities)\n"
                        f"  /offline        - Use Ollama Local LLMs (Private & Free)\n"
                        f"  /auto           - Toggle intelligent model routing (auto-selects models according to request)\n"
                        f"  /manual         - Toggle to manual model selection\n"
                        f"  /attach <path>  - Attach a file (image, pdf, doc) to the next prompt\n"
                        f"  /paste_image    - Attach the current image from your clipboard\n"
                        f"  /clear_attachments - Remove all pending attachments\n"
                        f"  /set_model <m>  - Switch the current model (e.g., deepseek-coder)\n"
                        f"  /list_models    - See available local/online models\n"
                        f"  /mcp <n> <c>    - Connect an MCP Tool Server\n"
                        f"  /mount <path>   - Mount/change working directory for tools\n"
                        f"  /save           - Save current conversation to JSON\n"
                        f"  /clear          - Clear conversation history\n"
                        f"  /paste          - Multi-line paste mode (Ctrl+Z to finish)\n"
                        f"  /multiline      - Toggle permanent multi-line input mode\n"
                        f"  /help           - Show this command list\n"
                        f"  /telegram       - Gives the controls to bot session\n"
                        "  /exit           - Close the application\n"
                        "  /theme <name>   - Switch UI theme (green/blue)"
                    )
                    console.print(Panel(help_content, title="Help Menu", border_style=get_theme()["accent"]))
                    continue
                elif cmd.startswith("/theme"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) >= 2:
                        new_theme = parts[1].strip().lower()
                        if new_theme in theme_mod.THEME_CONFIGS:
                            theme_mod.current_theme_name = new_theme
                            theme_mod.update_console_theme()
                            console.print(f"[success]Theme switched to {new_theme.upper()}[/success]")
                        else:
                            console.print(f"[warning]Available themes: {', '.join(theme_mod.THEME_CONFIGS.keys())}[/warning]")
                    else:
                        console.print(f"[info]Current theme: {theme_mod.current_theme_name}. Usage: /theme <name>[/info]")
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
                elif cmd == "/telegram":
                    import config
                    import importlib
                    importlib.reload(config)
                    
                    if not config.TELEGRAM_BOT_TOKEN:
                        console.print(f"[{get_theme()['error']}]❌ Error: TELEGRAM_BOT_TOKEN missing in environment or .env file.[/{get_theme()['error']}]")
                        continue
                        
                    current_mode = "telegram"
                    agent.set_tools_enabled(True)
                    agent.set_system_prompt(TELEGRAM_MODE_PROMPT)
                    console.print(f"[{get_theme()['error']}]Mode switched to TELEGRAM (Listening on Bot...)[/{get_theme()['error']}]")
                    try:
                        asyncio.run(start_bot_chat(agent))
                    except KeyboardInterrupt:
                        pass # Normal exit handled below
                    except Exception as e:
                        console.print(f"[{get_theme()['error']}]❌ Bot Error: {e}[/{get_theme()['error']}]")
                    
                    # Ensure we always return to a safe state
                    console.print(f"\n[{get_theme()['warning']}]Telegram mode exited. Returning to CLI.[/{get_theme()['warning']}]")
                    current_mode = "chat"
                    agent.set_tools_enabled(False)
                    agent.set_system_prompt(CHAT_MODE_PROMPT)
                    continue
                elif cmd == "/chat":
                    current_mode = "chat"
                    agent.set_tools_enabled(False)
                    agent.set_system_prompt(CHAT_MODE_PROMPT)
                    console.print(f"[{get_theme()['info']}]Mode switched to CHAT (Tools Disabled)[/{get_theme()['info']}]")
                    continue
                elif cmd == "/agent":
                    current_mode = "agent"
                    agent.set_tools_enabled(True)
                    agent.set_system_prompt(RUN_MODE_PROMPT)
                    console.print(f"[{get_theme()['error']}]Mode switched to AGENT (Tools Enabled)[/{get_theme()['error']}]")
                    continue
                elif cmd == "/clear":
                    agent.context.store.clear()
                    agent.context.update_system_prompt(agent.base_system_prompt + (agent.tools_prompt if agent.tools_enabled else ""))
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
                elif cmd.startswith("/mount") or cmd.startswith("/cd"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) >= 2:
                        path_str = parts[1].strip().strip('"').strip("'")
                        try:
                            # Expand user's home directory if they use ~
                            path_str = os.path.expanduser(path_str)
                            os.chdir(path_str)
                            console.print(f"[{get_theme()['success']}]Mounted. Working directory is now: {os.getcwd()}[/{get_theme()['success']}]")
                        except Exception as e:
                            console.print(f"[{get_theme()['error']}]Error mounting to {path_str}: {e}[/{get_theme()['error']}]")
                    else:
                        console.print(f"[{get_theme()['info']}]Current directory: {os.getcwd()}\nUsage: /mount <path>[/{get_theme()['info']}]")
                    continue
                elif cmd == "/save":
                    import json
                    filename = f"chat_save_{int(t.time())}.json"
                    with open(filename, "w") as f:
                        # Filter out system messages and internal tier metadata
                        save_history = [
                            {k: v for k, v in m.items() if k != "tier"}
                            for m in agent.context.store.get_all()
                            if m["role"] != "system"
                        ]
                        json.dump(save_history, f, indent=2)
                    console.print(f"[{get_theme()['success']}]Conversation saved to {filename} (system prompts excluded)[/{get_theme()['success']}]")
                    continue
                elif cmd == "/paste":
                    console.print(f"[{theme['info']}]Paste your multi-line prompt below. Press Ctrl+Z (Windows) then Enter to finish:[/{theme['info']}]")
                    content = sys.stdin.read()
                    user_input = content.strip()
                    if not user_input:
                        continue
                elif cmd == "/multiline":
                    multiline_mode = not multiline_mode
                    state = "ENABLED" if multiline_mode else "DISABLED"
                    console.print(f"[{theme['success']}]Multi-line mode {state}[/{theme['success']}]")
                    continue
                elif cmd == "/list_models":
                    console.log(f"[{get_theme()['accent']}]Local Models:[/{get_theme()['accent']}]")
                    for model in agent.get_available_models():
                        console.print(f"  - {model}")
                    if agent.mode != "offline":
                        console.print(f"\n[{get_theme()['accent']}]Online Models (Dynamically Fetched):[/{get_theme()['accent']}]")
                        for m in agent.online_models:
                            status = "[green](available)[/]" if m not in agent.fallback_models else "[yellow](fallback)[/]"
                            console.print(f"  - {m} {status}")
                    else:
                         console.print(f"\n[{get_theme()['warning']}]Switch to /online to see all API models.[/{get_theme()['warning']}]")
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
            
            if hasattr(agent, 'auto_route') and agent.auto_route:
                model_display = "Auto"
            else:
                model_display = agent.model
            
            if hasattr(agent, 'manual_mode') and agent.manual_mode:
                model_display = "Manual"
            
            # --- Print the prefix ONCE as static text (fixes the repeated prefix bug) ---
            prefix_text = f"[{theme['agent']}]{model_display}[{agent.mode}] ❯[/{theme['agent']}]"
            console.print(prefix_text)
            
            full_response = ""
            current_status = ""
            terminal_command = ""
            terminal_output = ""
            tool_steps = []  # Sequential list of tool calls/results to display
            
            def _build_live_group():
                """Builds the renderable group for the live display."""
                items = []
                # Show sequential tool steps
                for step in tool_steps:
                    items.append(Text.from_markup(step))
                # Show current running status
                if current_status:
                    items.append(Text.from_markup(f" [italic yellow]⚡ {current_status}[/italic yellow]"))
                # Show terminal output if active
                if terminal_command:
                    items.append(render_terminal_box(terminal_command, terminal_output))
                # Show streaming response text
                if full_response:
                    items.append(format_response(full_response, theme))
                return Group(*items) if items else Text("")
            
            with Live("", console=console, refresh_per_second=15, vertical_overflow="visible") as live:
                try:
                    gen = agent.run(user_input, attachments=attachments.copy())
                    attachments.clear()
                    try:
                        chunk = next(gen)
                        while True:
                            if isinstance(chunk, str) and chunk.startswith("__ASK_PERMISSION__"):
                                parts = chunk.split(":", 2)
                                tool_name = parts[1]
                                tool_params = parts[2]
                                if len(tool_params) > 60:
                                    tool_params = tool_params[:60] + "...}"
                                
                                live.stop()
                                console.print(f"\n[{get_theme()['warning']}]🛡️ Permission Required:[/{get_theme()['warning']}] Tool [{get_theme()['accent']}]{tool_name}[/{get_theme()['accent']}] called with parameters [dim]{tool_params}[/dim]")
                                choice = console.input(f"[{get_theme()['success']}]Allow? (Y/n): [/{get_theme()['success']}]").strip().lower()
                                approved = choice in ["", "y", "yes"]
                                
                                live.start()
                                chunk = gen.send(approved)
                            elif isinstance(chunk, str) and chunk.startswith("__MAX_STEPS_REACHED__"):
                                parts = chunk.split(":", 1)
                                steps = parts[1]
                                
                                live.stop()
                                console.print(f"\n[{get_theme()['warning']}]⚠️ Maximum tool steps ({steps}) reached.[/{get_theme()['warning']}]")
                                choice = console.input(f"[{get_theme()['success']}]Increase limit by 10 and continue? (Y/n): [/{get_theme()['success']}]").strip().lower()
                                approved = choice in ["", "y", "yes"]
                                
                                if approved:
                                    live.start()
                                    chunk = gen.send(True)
                                else:
                                    chunk = gen.send(False)
                            elif isinstance(chunk, str) and chunk.startswith("__TOOL_CALL__"):
                                # Skip, we accumulate in __UI_STATUS__
                                chunk = next(gen)
                            elif isinstance(chunk, str) and chunk.startswith("__TOOL_RESULT__"):
                                parts = chunk.split(":", 2)
                                tool_name = parts[1]
                                tool_result = parts[2]
                                
                                # Truncate for display
                                display_result = tool_result
                                if len(display_result) > 300:
                                    display_result = display_result[:300] + "... [dim][truncated][/dim]"
                                
                                # Replace the last "running..." step entry with a "done" entry
                                first_line = display_result.splitlines()[0][:80] if display_result.strip() else "(no output)"
                                done_step = f"  [dim]└─[/dim] [bold cyan]{tool_name}[/bold cyan] [dim]{first_line}[/dim]"
                                if tool_steps:
                                    tool_steps[-1] = done_step
                                else:
                                    tool_steps.append(done_step)
                                
                                live.update(_build_live_group())
                                chunk = next(gen)
                            elif isinstance(chunk, str) and chunk.startswith("__UI_STATUS__"):
                                status_raw = chunk.replace("__UI_STATUS__:", "")
                                if status_raw.startswith("EXEC_CMD:"):
                                    terminal_command = status_raw.replace("EXEC_CMD:", "")
                                    terminal_output = ""
                                    current_status = ""
                                elif "Call " in status_raw and "[accent]" in status_raw:
                                    # This is a tool-call status — add as a new sequential step
                                    clean = apply_theme_placeholders(status_raw)
                                    tool_steps.append(f"  [dim]├─[/dim] {clean} [italic yellow]...[/italic yellow]")
                                    current_status = ""
                                    terminal_command = ""
                                else:
                                    current_status = apply_theme_placeholders(status_raw)
                                    terminal_command = ""
                                
                                live.update(_build_live_group())
                                chunk = next(gen)
                            elif isinstance(chunk, str) and chunk.startswith("__TOOL_STREAM__"):
                                terminal_output += chunk.replace("__TOOL_STREAM__:", "")
                                live.update(_build_live_group())
                                chunk = next(gen)
                            else:
                                if chunk is not None:
                                    if current_status:
                                        current_status = ""
                                    
                                    strip_chunk = chunk.strip()
                                    if strip_chunk and full_response.strip().endswith(strip_chunk) and len(strip_chunk) > 10:
                                        pass  # Skip duplicate preamble
                                    else:
                                        full_response += chunk
                                    
                                    live.update(_build_live_group())
                                chunk = next(gen)
                    except StopIteration:
                        # Final paint — only show the response text, tool steps already visible above
                        if full_response:
                            live.update(format_response(full_response, theme))
                        elif current_status:
                            live.update(Text.from_markup(f" [italic yellow]⚡ {current_status}[/italic yellow]"))
                        else:
                            live.update(Text(""))
                except KeyboardInterrupt:
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
                            break
                    else:
                        live.update(format_response(full_response + " [dim](stopped)[/dim]", theme))
            
            console.print()
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Exiting...[/bold yellow]")
            break


