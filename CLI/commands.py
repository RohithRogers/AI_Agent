import argparse
import asyncio
import os
from agents.chat_agent import ChatAgent
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.panel import Panel
from rich.console import Group
import time as t
from tools.mcp_registry import mcp_manager

console = Console()

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
    console.print(Panel(f"[bold blue]AI Agent CLI Ready[/bold blue]\n\n"
                        f"[bold cyan]Mode:[/bold cyan] {agent.mode}\n[bold cyan]Context:[/bold cyan] {current_mode}\n"
                        f"[bold cyan]Model:[/bold cyan] {agent.model}\n\n"
                        f"[bold cyan]Slash Commands:[/bold cyan]\n"
                        "  /chat   - Chat Mode\n"
                        "  /run    - Run Mode (Code only)\n"
                        "  /voice  - Voice Input\n"
                        "  /cls    - Clear Screen\n"
                        "  /help   - List all commands\n"
                        "  /exit   - Close CLI", title="System"))

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
            # Show current mode in the prompt
            mode_color = "cyan" if current_mode == "chat" else "red"
            user_input = console.input(f"[bold green]User[/bold green] [({agent.mode}) [{mode_color}]{current_mode}[/{mode_color}]] [bold green]❯ [/bold green]").strip()
            
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
                    console.print("[bold yellow]Exiting...[/bold yellow]")
                    t.sleep(1)
                    break
                elif cmd == "/cls":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    show_welcome_panel(agent, current_mode)
                    continue
                elif cmd == "/help":
                    help_content = (
                        "[bold cyan]Available Commands:[/bold cyan]\n"
                        "  /chat           - Switch to CHAT Mode (conversational)\n"
                        "  /run            - Switch to RUN Mode (direct code execution)\n"
                        "  /voice          - Interactive voice input mode\n"
                        "  /cls            - Clear console screen (keeps history)\n"
                        "  /online         - Use Gemini Cloud API (Advanced capabilities)\n"
                        "  /offline        - Use Ollama Local LLMs (Private & Free)\n"
                        "  /set_model <m>  - Switch the current model (e.g., deepseek-coder)\n"
                        "  /list_models    - See available local/online models\n"
                        "  /mcp <n> <c>    - Connect an MCP Tool Server\n"
                        "  /save           - Save current conversation to JSON\n"
                        "  /clear          - Clear conversation history\n"
                        "  /help           - Show this command list\n"
                        "  /exit           - Close the application"
                    )
                    console.print(Panel(help_content, title="Help Menu", border_style="green"))
                    continue
                elif cmd == "/online":
                    current_mode = "chat"
                    agent.set_mode("online")
                    console.print(f"[bold green]Mode switched to ONLINE (Model: {agent.model})[/bold green]")
                    continue
                elif cmd == "/offline":
                    current_mode = "chat"
                    agent.set_mode("offline")
                    console.print(f"[bold red]Mode switched to OFFLINE (Model: {agent.model})[/bold red]")
                    continue
                elif cmd == "/chat":
                    current_mode = "chat"
                    agent.set_system_prompt(CHAT_MODE_PROMPT)
                    console.print("[bold cyan]Mode switched to CHAT (Conversational)[/bold cyan]")
                    continue
                elif cmd == "/run":
                    current_mode = "run"
                    agent.set_system_prompt(RUN_MODE_PROMPT)
                    console.print("[bold red]Mode switched to RUN (Code Only)[/bold red]")
                    continue
                elif cmd == "/clear":
                    agent.messages = [{"role": "system", "content": agent.base_system_prompt + agent.tools_prompt}]
                    console.print("[yellow]Conversation history cleared.[/yellow]")
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
                    console.print(f"[bold green]Conversation saved to {filename} (system prompts excluded)[/bold green]")
                    continue
                elif cmd == "/list_models":
                    console.print("[bold cyan]Local Models:[/bold cyan]")
                    for model in agent.get_available_models():
                        console.print(f"  - {model}")
                    continue
                elif cmd.startswith("/set_model"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) >= 2:
                        model = parts[1].strip()
                        agent.set_model(model)
                        console.print(f"[bold green]Model set to {model}[/bold green]")
                    else:
                        console.print("[yellow]Usage: /set_model <model>[/yellow]")
                    continue
                else:
                    console.print(f"[bold red]Unknown command: {cmd}[/bold red]")
                    continue

            if user_input.lower() in ["exit", "quit"]:
                console.print("[bold yellow]Exiting...[/bold yellow]")
                t.sleep(1)
                break
            
            prefix_text = "[bold blue]Agent ❯ [/bold blue]"
            full_response = ""
            
            current_status = ""
            with Live("", console=console, refresh_per_second=15) as live:
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
                                console.print(f"\n[bold yellow]🛡️ Permission Required:[/bold yellow] Tool [bold cyan]{tool_name}[/bold cyan] called with parameters [dim]{tool_params}[/dim]")
                                choice = console.input("[bold green]Allow? (Y/n): [/bold green]").strip().lower()
                                approved = choice in ["", "y", "yes"]
                                
                                live.start()
                                chunk = gen.send(approved)
                            elif isinstance(chunk, str) and chunk.startswith("__UI_STATUS__"):
                                current_status = chunk.replace("__UI_STATUS__:", "")
                                live.update(Group(
                                    prefix_text,
                                    Markdown(full_response),
                                    f"\n [italic yellow]⚡ {current_status}[/italic yellow]"
                                ))
                                chunk = next(gen)
                            else:
                                if chunk is not None:
                                    if current_status:
                                        current_status = "" 

                                    full_response += chunk
                                    clean_response = full_response.replace("```", "\n```\n").replace("\n\n```", "\n```")
                                    
                                    live.update(Group(
                                        prefix_text,
                                        Markdown(clean_response)
                                    ))
                                
                                chunk = next(gen)
                    except StopIteration:
                        # Update Live display one final time with just the response
                        live.update(Markdown(full_response))
                except KeyboardInterrupt:
                    live.update(Markdown(full_response + " [dim](stopped)[/dim]"))
            
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
        full_response = ""
        current_status = ""
        with Live("", console=console, refresh_per_second=15) as live:
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
                            console.print(Panel(f"Agent wants to use [bold cyan]{tool_name}[/bold cyan]\n[dim]Params: {tool_params}[/dim]", 
                                                title="🛡️ Permission Required", border_style="yellow", expand=False))
                            choice = console.input("[bold green]Confirm? (Y/n): [/bold green]").strip().lower()
                            approved = choice in ["", "y", "yes"]
                            
                            live.start()
                            chunk = gen.send(approved)
                        elif isinstance(chunk, str) and chunk.startswith("__UI_STATUS__"):
                            current_status = chunk.replace("__UI_STATUS__:", "")
                            live.update(Group(
                                Markdown(full_response),
                                f"\n [italic yellow]⚡ {current_status}[/italic yellow]"
                            ))
                            chunk = next(gen)
                        else:
                            if chunk is not None:
                                if current_status:
                                    current_status = "" 
                                full_response += chunk
                                clean_response = full_response.replace("```", "\n```\n").replace("\n\n```", "\n```")
                                live.update(Markdown(clean_response))
                            chunk = next(gen)
                except StopIteration:
                    pass
            except KeyboardInterrupt:
                live.update(Markdown(full_response + " [dim](stopped)[/dim]"))
        console.print()
    else:
        parser.print_help()
