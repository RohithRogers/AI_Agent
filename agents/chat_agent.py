import ollama
import json
import asyncio
from rich.console import Console
from rich.markdown import Markdown
from agents.base_agent import BaseAgent
from tools.registry import registry
from tools.mcp_registry import mcp_manager
from google import genai


# Create console for internal logging/debugging
console = Console()

class ChatAgent(BaseAgent):
    def __init__(self, model="deepseek-coder", system_prompt="", mode="offline"):
        # Store original prompts for mode switching
        self.mode = mode
        self.base_system_prompt = system_prompt
        self.available_models = ["deepseek-coder","functiongemma"]
        
        # Initialize MCP if configured in .env or config (TBD)
        self._update_tools_prompt()
        
        super().__init__(model, self.base_system_prompt + self.tools_prompt)
        
        # Initialize GenAI client if in online mode
        if self.mode != "offline":
            from config import CLOUD_MODE
            self.client = genai.Client(api_key=CLOUD_MODE)
            # Ensure model is a gemini model if none provided
            if "gemini" not in self.model.lower():
                self.model = "gemini-3-flash-preview"

    def set_system_prompt(self, new_prompt):
        """Updates the system prompt while maintaining the message structure."""
        self.base_system_prompt = new_prompt
        # Update the system message (usually at index 0)
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = self.base_system_prompt + self.tools_prompt
        else:
            # Fallback if no system message exists
            self.messages.insert(0, {"role": "system", "content": self.base_system_prompt + self.tools_prompt})

    def _update_tools_prompt(self):
        """Refreshes the tools JSON schema in the system prompt."""
        tool_schemas = registry.get_tool_schemas()
        self.tools_prompt = f"\n\nYou have access to the following tools:\n{json.dumps(tool_schemas, indent=2)}\n\nIf you need to use a tool, respond in this EXACT JSON format:\n{{\"tool\": \"TOOL_NAME\", \"parameters\": {{ \"PARAM_NAME\": \"VALUE\" }} }}\nDo not say anything else when calling a tool."
        
        # Update current system message if it exists
        if hasattr(self, 'messages') and self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = self.base_system_prompt + self.tools_prompt

    def _get_gemini_messages(self):
        """Converts internal message history to Google GenAI format."""
        gemini_messages = []
        for msg in self.messages:
            if msg["role"] == "system":
                continue  # System prompt is handled separately
            
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        return gemini_messages
    
    def get_available_models(self):
        """Returns a list of available models."""
        return self.available_models

    def run(self, user_input):
        console.log(f"[bold cyan]Input Received:[/bold cyan] {user_input[:50]}...")
        self.add_message("user", user_input)
        
        console.log(f"Streaming from model: [italic]{self.model}[/italic]...")
        try:
            while True:
                # Check for tool call vs normal response by getting a non-streamed check or just streaming and buffering
                # For simplicity in this implementation, we stream and buffer. 
                # If the buffer looks like a tool call, we handle it.
                full_content = ""
                if self.mode == "offline":
                    stream = ollama.chat(model=self.model, messages=self.messages, stream=True)
                else:
                    gemini_msgs = self._get_gemini_messages()
                    system_instr = self.messages[0]["content"] if self.messages[0]["role"] == "system" else ""
                    stream = self.client.models.generate_content_stream(
                        model=self.model, 
                        contents=gemini_msgs,
                        config={"system_instruction": system_instr}
                    )
                
                is_tool_call = False
                for chunk in stream:
                    if self.mode == "offline":
                        token = chunk['message']['content']
                    else:
                        token = chunk.text or ""
                    
                    full_content += token
                    
                    # If we haven't decided it's a tool yet, check the start
                    if not is_tool_call and '{"tool":' in full_content:
                        is_tool_call = True
                        # If it's a tool call, we stop yielding tokens to the UI
                    
                    if not is_tool_call:
                        yield token

                if is_tool_call:
                    try:
                        # Clean the content in case there is markdown or noise
                        start = full_content.find('{')
                        end = full_content.rfind('}') + 1
                        tool_data = json.loads(full_content[start:end])
                        
                        tool_name = tool_data["tool"]
                        tool_params = tool_data.get("parameters", {})
                        
                        console.log(f"🔧 [bold yellow]Tool Triggered:[/bold yellow] {tool_name}")
                        console.log(f"📝 [dim]Parameters:[/dim] {tool_params}")
                        
                        # Yield a status message
                        yield f"__UI_STATUS__:⚙️ Executing {tool_name}..."
                        
                        # Check for permission
                        tool_info = registry.tools.get(tool_name)
                        if tool_info and tool_info.get("requires_permission"):
                            # Signal that we need permission. 
                            # We'll use a special string prefix that the CLI can catch.
                            # The consumer should .send() back the result.
                            approved = (yield f"__ASK_PERMISSION__:{tool_name}:{json.dumps(tool_params)}")
                            if not approved:
                                result = "Error: User denied permission to execute this tool."
                                console.log(f"🚫 [bold red]Permission Denied:[/bold red] {tool_name}")
                            else:
                                result = registry.execute_tool(tool_name, tool_params)
                                console.log(f"✅ [bold green]Permission Granted:[/bold green] {tool_name}")
                        else:
                            result = registry.execute_tool(tool_name, tool_params)
                        
                        # Feed the result back
                        self.add_message("assistant", full_content)
                        self.add_message("user", f"Tool '{tool_name}' returned: {result}")
                        console.log(f"✅ [green]Tool result added to context.[/green]")
                        continue # Let the LLM process the result
                    except Exception as e:
                        yield f"__UI_STATUS__:❌ Error parsing tool call: {e}"
                        break
                else:
                    self.add_message("assistant", full_content)
                    console.log("🏁 [bold blue]Response generation complete.[/bold blue]")
                    break
        except KeyboardInterrupt:
            console.log("\n[bold red]⚠️  Generation interrupted by user.[/bold red]")
            self.add_message("assistant", full_content + "... [Interrupted]")
