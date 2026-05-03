import argparse
from rich.live import Live
from rich.console import Group
from rich.text import Text

from agents.chat_agent import ChatAgent
from CLI.theme import console, get_theme, apply_theme_placeholders
from CLI.ui import format_response, render_terminal_box
from CLI.chat_session import start_chat

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

    # Workspace command
    workspace_parser = subparsers.add_parser("workspace", help="Manage the agent workspace")
    workspace_parser.add_argument("--list", action="store_true", help="List persistent workspace exports and sessions stats")

    args = parser.parse_args()

    if args.command == "chat":
        start_chat(args.mode)
    elif args.command == "workspace":
        from tools.workspace_manager import workspace_manager
        stats = workspace_manager.workspace_stats()
        console.print("[bold cyan]Agent Workspace Stats[/bold cyan]")
        console.print(f"Usage: [yellow]{stats['total_size_mb']} MB[/yellow] / {stats['max_size_mb']} MB")
        
        console.print("\n[bold green]Persistent Exports:[/bold green]")
        if stats['persistent_exports']:
            for exp in stats['persistent_exports']:
                console.print(f"  • {exp}")
        else:
            console.print("  [dim]None[/dim]")
            
        console.print("\n[bold blue]Active Sessions:[/bold blue]")
        if stats['active_sessions']:
            for sess in stats['active_sessions']:
                console.print(f"  • {sess}")
        else:
            console.print("  [dim]None[/dim]")
    elif args.command == "run":
        RUN_MODE_PROMPT = "You are a powerful AI Agent with full access to system tools. Use them to help the user complete their tasks."
        agent = ChatAgent(system_prompt=RUN_MODE_PROMPT, mode=args.mode, tools_enabled=True)
        console.print(f"[bold red]Running Task:[/bold red] {args.task}")
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
                        elif isinstance(chunk, str) and chunk.startswith("__TOOL_CALL__"):
                            # Consume silently — __UI_STATUS__ already shows the tool name
                            chunk = next(gen)
                        elif isinstance(chunk, str) and chunk.startswith("__TOOL_RESULT__"):
                            parts = chunk.split(":", 2)
                            tool_name = parts[1]
                            tool_result = parts[2]
                            full_response += f"\n\n🛠️ **Tool [{tool_name}] Result:**\n{tool_result}\n"
                            live.update(Group(
                                prefix_text,
                                format_response(full_response, theme),
                                render_terminal_box(terminal_command, terminal_output) if terminal_command else Text(""),
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
