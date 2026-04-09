import ollama
import json
import asyncio
from rich.console import Console
from rich.markdown import Markdown
from agents.base_agent import BaseAgent
from tools.registry import registry
from tools.mcp_registry import mcp_manager
from google import genai
from google.genai import types

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
        
        self.online_models = ["gemini-3.1-flash-lite-preview", "gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.5-pro"]
        
        # Initialize GenAI client if in online mode
        if self.mode != "offline":
            from config import CLOUD_MODE
            self.client = genai.Client(api_key=CLOUD_MODE)
            # Ensure model is a gemini model if none provided
            if "gemini" not in self.model.lower():
                self.model = self.online_models[0]

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
        self.tools_prompt = f"""
You are an advanced AI agent with access to a REAL persistent PowerShell session.
Your actions persist (e.g., changing directories, installing packages).

TASK EXECUTION FLOW:
1. REASON: Explain your plan inside <thought>...</thought> tags.
2. ACT: Execute a tool (JSON) IMMEDIATELY after reasoning if the task is not done.
3. FINISH: Only provide a final summary IF the task is fully verified and complete.

IMPORTANT RULES:
- If you say you will do something, you MUST execute the tool in the same response.
- NEVER ask "Would you like me to...". Just do it.
- Your goal is to reach the goal, not just to plan.

TOOL CALL FORMAT (for local models):
To use a tool, output a JSON object. 
Example: {{"tool": "command_executor", "parameters": {{"command": "ls"}}}}

AVAILABLE TOOLS:
{json.dumps(tool_schemas, indent=2)}
"""
        
        # Update current system message if it exists
        if hasattr(self, 'messages') and self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = self.base_system_prompt + self.tools_prompt

    def _get_gemini_tools(self):
        """Converts registry tools to Gemini genai.types.Tool format."""
        declarations = []
        for tool_name, tool_info in registry.tools.items():
            declarations.append(types.FunctionDeclaration(
                name=tool_name,
                description=tool_info["description"],
                parameters=tool_info["parameters"]
            ))
        
        if not declarations:
            return None
        return [types.Tool(function_declarations=declarations)]

    def _get_gemini_messages(self):
        """Converts internal message history to Google GenAI format, supporting tool calls."""
        gemini_messages = []
        for msg in self.messages:
            if msg["role"] == "system":
                continue
            
            role = "user" if msg["role"] == "user" else "model"
            content = msg.get("content", "")
            
            tool_call = msg.get("tool_call")
            tool_call_part = msg.get("tool_call_part")
            tool_response = msg.get("tool_response")
            
            parts = []
            if content and not tool_call_part:
                parts.append(types.Part(text=content))
            elif content and tool_call_part:
                parts.append(types.Part(text=content))
                
            if tool_call_part:
                parts.append(tool_call_part)
            
            if tool_call:
                # Legacy handling for offline or older models without native part
                parts.append(types.Part(function_call=types.FunctionCall(
                    name=tool_call["name"],
                    args=tool_call["args"]
                )))
            
            if tool_response:
                func_id = tool_response.get("id")
                parts.append(types.Part(function_response=types.FunctionResponse(
                    id=func_id,
                    name=tool_response["name"],
                    response={"result": str(tool_response["content"])}
                )))
                role = "user" # Responses are sent as 'user' turn with parts containing FunctionResponse

            if not parts:
                continue

            if gemini_messages and gemini_messages[-1].role == role:
                gemini_messages[-1].parts.extend(parts)
            else:
                gemini_messages.append(types.Content(role=role, parts=parts))
                
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
                self.model = self.online_models[0]
        else:
            self.model = "deepseek-coder"
        
        self._update_tools_prompt()
    
    def get_available_models(self):
        """Returns a list of available models."""
        return self.available_models

    def run(self, user_input):
        console.log(f"[info]Input Received:[/info] {user_input[:50]}...")
        self.add_message("user", user_input)
        
        console.log(f"Streaming from model: [italic]{self.model}[/italic]...")
        
        max_steps = 10
        step_count = 0
        
        full_content = ""
        try:
            while step_count < max_steps:
                step_count += 1
                full_content = ""
                try:
                    if self.mode == "offline":
                        stream = ollama.chat(model=self.model, messages=self.messages, stream=True)
                    else:
                        gemini_msgs = self._get_gemini_messages()
                        system_instr = self.messages[0]["content"] if self.messages[0]["role"] == "system" else ""
                        active_model = self.model
                        
                        stream = self.client.models.generate_content_stream(
                            model=active_model, 
                            contents=gemini_msgs,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instr,
                                tools=self._get_gemini_tools()
                            )
                        )
                    
                    is_tool_call = False
                    native_tool_call = None
                    yielded_len = 0
                    has_yielded_token = False
                    
                    for chunk in stream:
                        if self.mode == "offline":
                            token = chunk.get('message', {}).get('content', '')
                            if token:
                                has_yielded_token = True
                                full_content += token
                        else:
                            token = ""
                            # Handle native tool calls
                            if chunk.candidates:
                                candidate = chunk.candidates[0]
                                
                                # Check for safety blocks/interruption
                                if candidate.finish_reason and candidate.finish_reason not in [types.FinishReason.STOP, types.FinishReason.MAX_TOKENS]:
                                    yield f"__UI_STATUS__:🚨 [bold orange]Stream Interrupted[/bold orange]: {candidate.finish_reason}"
                                
                                for part in candidate.content.parts:
                                    if part.text:
                                        token += part.text
                                    if part.function_call:
                                        is_tool_call = True
                                        native_tool_call = part # Store the entire Part object!
                            if token:
                                has_yielded_token = True
                                full_content += token

                        if not is_tool_call:
                            # Look for tool call marker (flexible match for JSON)
                            if '"tool":' in full_content and '{' in full_content:
                                start_idx = full_content.find('{')
                                thought_open = full_content.rfind('<thought>')
                                thought_close = full_content.rfind('</thought>')
                                if thought_close > thought_open or thought_open == -1:
                                    if '"tool":' in full_content[start_idx:]:
                                        is_tool_call = True
                                        if start_idx > yielded_len:
                                            yield full_content[yielded_len:start_idx]
                                            yielded_len = start_idx
                        
                        if not is_tool_call:
                                chunk_to_yield = full_content[yielded_len:]
                                if chunk_to_yield:
                                    yield chunk_to_yield
                                    yielded_len = len(full_content)
                    
                    if not has_yielded_token and not is_tool_call:
                        yield f"__UI_STATUS__:🚨 No text output from {active_model}. This can happen if the prompt is blocked or the model is overloaded."
                    
                    # Flush any remaining buffer
                    if not is_tool_call and yielded_len < len(full_content):
                        yield full_content[yielded_len:]
                except Exception as e:
                    err_str = str(e)
                    # Handle specific API errors for better user feedback
                    if "503" in err_str or "high demand" in err_str.lower():
                        yield "__UI_STATUS__:🚨 [bold yellow]Model Overloaded[/bold yellow]: The API is busy. Retrying automatically in next step or wait few seconds."
                    elif "429" in err_str:
                         yield "__UI_STATUS__:🚨 [bold red]Quota Exceeded[/bold red]: Rate limit reached. Please wait or check your API quota."
                    elif "blocked" in err_str.lower() or "safety" in err_str.lower():
                        yield "__UI_STATUS__:🛡️ [bold orange]Response Blocked[/bold orange]: The model's safety filters prevented this response."
                    elif "401" in err_str or "key" in err_str.lower():
                         yield "__UI_STATUS__:🔑 [bold red]Auth Error[/bold red]: Invalid API Key."
                    else:
                        yield f"__UI_STATUS__:❌ [bold red]API Error[/bold red]: {err_str}"
                    break

                if is_tool_call:
                    try:
                        if native_tool_call:
                            # native_tool_call is a types.Part object constructed by the SDK
                            tool_name = native_tool_call.function_call.name
                            tool_params = native_tool_call.function_call.args
                        else:
                            # Parse JSON tool call for offline mode or fallback
                            start = full_content.find('{')
                            end = full_content.rfind('}') + 1
                            tool_data = json.loads(full_content[start:end])
                            tool_name = tool_data["tool"]
                            tool_params = tool_data.get("parameters", {})
                        
                        params_hint = json.dumps(tool_params)[:50] + "..." if len(json.dumps(tool_params)) > 50 else json.dumps(tool_params)
                        yield f"__UI_STATUS__:🛠️ Call [accent]{tool_name}[/accent] [dim]{params_hint}[/dim]"
                        
                        tool_info = registry.tools.get(tool_name)
                        if tool_info and tool_info.get("requires_permission"):
                            approved = (yield f"__ASK_PERMISSION__:{tool_name}:{json.dumps(tool_params)}")
                            if not approved:
                                result = "Error: User denied permission to execute this tool."
                            else:
                                result = registry.execute_tool(tool_name, tool_params)
                        else:
                            result = registry.execute_tool(tool_name, tool_params)
                        
                        import inspect
                        if inspect.isgenerator(result):
                            full_tool_output = ""
                            is_terminal = tool_name in ["command_executor", "program_run"]
                            if is_terminal:
                                cmd_str = tool_params.get("command") or tool_params.get("path")
                                yield f"__UI_STATUS__:EXEC_CMD:{cmd_str}"
                            for chunk in result:
                                full_tool_output += chunk
                                if is_terminal:
                                    yield f"__TOOL_STREAM__:{chunk}"
                            result = full_tool_output
                        else:
                            yield f"__UI_STATUS__:✅ Tool [accent]{tool_name}[/accent] finished."
                            result = str(result)

                        # Update History
                        if native_tool_call:
                            self.messages.append({
                                "role": "assistant", 
                                "content": full_content, 
                                "tool_call_part": native_tool_call
                            })
                            
                            # Get the FunctionCall ID if available
                            func_id = None
                            if hasattr(native_tool_call.function_call, "id"):
                                func_id = native_tool_call.function_call.id
                                
                            self.messages.append({
                                "role": "user", 
                                "content": "", 
                                "tool_response": {"id": func_id, "name": tool_name, "content": result}
                            })
                        else:
                            self.add_message("assistant", full_content)
                            self.add_message("user", f"Tool '{tool_name}' returned: {result}")
                        
                        continue
                    except Exception as e:
                        yield f"__UI_STATUS__:❌ Error executing tool: {e}"
                        break
                else:
                    self.add_message("assistant", full_content)
                    
                    import re
                    clean_text = re.sub(r'<thought>(.*?)</thought>', '', full_content, flags=re.DOTALL).strip()
                    
                    if not clean_text and "<thought>" in full_content:
                        self.add_message("user", "Proceed with the execution using tools.")
                        yield "__UI_STATUS__:🤔 Thought received. Prompting agent to execute plan..."
                        continue
                        
                    lower_clean = clean_text.lower()
                    if any(kw in lower_clean for kw in ["i will", "now i am going to", "let me", "i'll"]) and not is_tool_call:
                         if not any(kw in lower_clean for kw in ["i have", "is done", "task completed"]):
                            self.add_message("user", "You mentioned you would act. Please provide the tool call JSON now.")
                            yield "__UI_STATUS__:⚠️ Intent detected but tool call missing. Nudging..."
                            continue

                    console.log("🏁 [info]Response generation complete.[/info]")
                    break
            
            if step_count >= max_steps:
                yield "__UI_STATUS__:⚠️ Task stopped: Maximum allowed tool steps reached."
        except KeyboardInterrupt:
            console.log("\n[error]⚠️ Generation interrupted.[/error]")
            self.add_message("assistant", full_content + "... [Interrupted]")
