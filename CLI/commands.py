import argparse
from agents.chat_agent import ChatAgent
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.panel import Panel
import time as t

console = Console()

def start_chat():
    # Define our two mode prompts
    CHAT_MODE_PROMPT = "You are a helpful AI assistant with access to local tools. Use markdown for code and lists."
    RUN_MODE_PROMPT = "You are a technical assistant. If code is requested, return ONLY raw executable code without markdown, comments, or explanations."
    
    current_mode = "chat"
    agent = ChatAgent(system_prompt=CHAT_MODE_PROMPT)
    
    console.print(Panel("[bold blue]AI Agent CLI Ready[/bold blue]\n\n"
                        "[bold cyan]Slash Commands:[/bold cyan]\n"
                        "  /chat   - Switch to Chat Mode (conversational)\n"
                        "  /run    - Switch to Run Mode (code only)\n"
                        "  /voice  - Speak to the Agent (Microphone)\n"
                        "  /save   - Save conversation history\n"
                        "  /clear  - Clear history\n"
                        "  /exit   - Close CLI", title="System"))
    
    while True:
        try:
            # Show current mode in the prompt
            mode_color = "cyan" if current_mode == "chat" else "red"
            user_input = console.input(f"[bold green]User[/bold green] [[{mode_color}]{current_mode}[/{mode_color}]] [bold green]❯ [/bold green]").strip()
            
            if not user_input:
                continue

            # Command Handling
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd == "/voice":
                    from tools.voice_handler import get_voice_input
                    voiced_text = get_voice_input()
                    if voiced_text:
                        console.print(f"[bold cyan]You (Voice) ❯[/bold cyan] {voiced_text}")
                        user_input = voiced_text
                    else:
                        console.print("[bold red]No speech detected.[/bold red]")
                        continue
                elif cmd == "/exit":
                    console.print("[bold yellow]Exiting...[/bold yellow]")
                    t.sleep(1)
                    break
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
                elif cmd == "/save":
                    import json
                    filename = f"chat_save_{int(t.time())}.json"
                    with open(filename, "w") as f:
                        json.dump(agent.messages, f, indent=2)
                    console.print(f"[bold green]Conversation saved to {filename}[/bold green]")
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
            
            with Live("", console=console, refresh_per_second=15) as live:
                try:
                    for chunk in agent.run(user_input):
                        full_response += chunk
                        
                        # Use a Group to combine the prompt and the response
                        from rich.console import Group
                        
                        parts = [prefix_text]
                        if "⚙️" in chunk or "❌" in chunk or not ("`" in full_response or "\n" in full_response):
                            # Simple text or status icons
                            parts.append(full_response)
                            live.update(Group(*parts))
                        else:
                            # Markdown content (force a newline before markdown for better layout)
                            parts.append(Markdown(full_response))
                            live.update(Group(*parts))
                            
                except KeyboardInterrupt:
                    live.update(Group(prefix_text, full_response + " [dim](stopped)[/dim]"))
            
            console.print()
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Exiting...[/bold yellow]")
            break

def main():
    parser = argparse.ArgumentParser(description="LLM Agent CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Start a chat session")
    
    # Run task command
    run_parser = subparsers.add_parser("run", help="Run a single task string")
    run_parser.add_argument("task", type=str, help="The task for the agent to execute")

    args = parser.parse_args()

    if args.command == "chat":
        start_chat()
    elif args.command == "run":
        agent = ChatAgent(system_prompt="You are a helpful AI assistant with access to local tools.")
        console.print(f"[bold blue]Executing Task:[/bold blue] {args.task}")
        full_response = ""
        for chunk in agent.run(args.task):
            full_response += chunk
            # Just streaming raw for run tasks or we can use Live here too
            console.print(chunk, end="")
        console.print()
    else:
        parser.print_help()
