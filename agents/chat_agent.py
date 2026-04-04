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

    def set_model(self, model):
        """Sets the model to use and refreshes tools."""
        self.model = model
        self._update_tools_prompt()

    def set_mode(self, mode):
        """Sets the mode (online/offline) and refreshes tools."""
        if self.mode == mode:
            return
        
        self.mode = mode
        if self.mode != "offline":
            if not hasattr(self, 'client'):
                from config import CLOUD_MODE
                self.client = genai.Client(api_key=CLOUD_MODE)
            # Ensure a valid Gemini model is selected if current model is local
            if "gemini" not in self.model.lower():
                self.model = "gemini-3-flash-preview"
        else:
            self.model = "deepseek-coder"
        
        self._update_tools_prompt()
    
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
                try:
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
                except Exception as e:
                    err_str = str(e)
                    if "503" in err_str or "high demand" in err_str.lower():
                        yield f"__UI_STATUS__:🚨 Model Overloaded: The API is currently experiencing high demand. Please try again in a few seconds."
                    elif "429" in err_str:
                        yield f"__UI_STATUS__:🚨 Quota Exceeded: You've reached the rate limit. Please wait before asking again."
                    elif "401" in err_str or "API_KEY_INVALID" in err_str:
                        yield f"__UI_STATUS__:🔑 Authentication Error: Your API key is invalid or expired."
                    else:
                        yield f"__UI_STATUS__:❌ Model Error: {err_str}"
                    break

                if is_tool_call:
                    try:
                        # Clean the content in case there is markdown or noise
                        start = full_content.find('{')
                        end = full_content.rfind('}') + 1
                        tool_data = json.loads(full_content[start:end])
                        
                        tool_name = tool_data["tool"]
                        tool_params = tool_data.get("parameters", {})
                        
                        # Yield a cleaner status message for the UI
                        params_hint = json.dumps(tool_params)[:50] + "..." if len(json.dumps(tool_params)) > 50 else json.dumps(tool_params)
                        yield f"__UI_STATUS__:🛠️ Call [bold cyan]{tool_name}[/bold cyan] [dim]{params_hint}[/dim]"
                        
                        # Check for permission
                        tool_info = registry.tools.get(tool_name)
                        if tool_info and tool_info.get("requires_permission"):
                            approved = (yield f"__ASK_PERMISSION__:{tool_name}:{json.dumps(tool_params)}")
                            if not approved:
                                result = "Error: User denied permission to execute this tool."
                            else:
                                result = registry.execute_tool(tool_name, tool_params)
                        else:
                            result = registry.execute_tool(tool_name, tool_params)
                        
                        # Feed the result back
                        self.add_message("assistant", full_content)
                        self.add_message("user", f"Tool '{tool_name}' returned: {result}")
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
