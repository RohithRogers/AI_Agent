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
from groq import Groq
from skills.skill_registry import skill_registry
from agents.context import ContextManager

skill_registry_inst = skill_registry()
skill_registry_inst.register_skills()



# Create console for internal logging/debugging
console = Console()

class ChatAgent(BaseAgent):
    def __init__(self, model="deepseek-coder", system_prompt="", mode="offline", tools_enabled=True):
        # Store original prompts for mode switching
        self.mode = mode
        self.tools_enabled = tools_enabled
        self.base_system_prompt = system_prompt
        self.available_models = ["deepseek-coder","functiongemma"]
        
        # Initialize MCP if configured in .env or config (TBD)
        self._update_tools_prompt()
        
        super().__init__(model, self.base_system_prompt + (self.tools_prompt if self.tools_enabled else ""))
        
        self.online_models = []
        self.fallback_models = []
        
        # History management settings
        self.max_history_chars = 60_000   # ~15k tokens; triggers pruning
        self.emergency_history_chars = 20_000  # aggressive prune threshold for fallbacks
        self.max_tool_output_chars = 3_000  # max chars saved per tool response
        self.retain_messages = 6  # min recent messages always kept
        
        # Initialize GenAI client if in online mode
        if self.mode != "offline":
            from config import ONLINE_MODE_GEMINI,ONLINE_MODE_GROQ
            self.client = genai.Client(api_key=ONLINE_MODE_GEMINI)
            self.groq_client = Groq(api_key=ONLINE_MODE_GROQ)
            self._fetch_online_models()
            # Ensure model is a valid model if none provided
            if not any(x in self.model.lower() for x in ["gemini", "gemma", "llama", "mixtral", "groq"]):
                self.model = self.online_models[0] if self.online_models else "gemini-2.0-flash"
        # Initialize new Context Manager
        self.context = ContextManager(
            token_budget=self.max_history_chars,
            summary_threshold=int(self.max_history_chars * 0.8)
        )
        self.context.update_system_prompt(self.base_system_prompt + (self.tools_prompt if self.tools_enabled else ""))

    def _fetch_online_models(self):
        """Fetches available models from Gemini and Groq APIs."""
        self.online_models = []
        
        # 1. Fetch Gemini Models
        try:
            all_gemini = self.client.models.list()
            for m in all_gemini:
                name = m.name.replace("models/", "")
                if any(x in name for x in ["embedding", "aqa", "lyria", "robotics", "computer-use"]):
                    continue
                self.online_models.append(name)
        except Exception as e:
            console.log(f"[warning]Failed to fetch Gemini models: {e}[/warning]")

        # 2. Fetch Groq Models
        if hasattr(self, 'groq_client') and self.groq_client:
            try:
                all_groq = self.groq_client.models.list()
                for m in all_groq.data:
                    # Filter for chat-capable models (heuristic)
                    if any(x in m.id.lower() for x in ["llama", "mixtral", "gemma", "whisper"]):
                        if "whisper" in m.id.lower(): continue # Skip whisper (audio)
                        self.online_models.append(m.id)
            except Exception as e:
                console.log(f"[warning]Failed to fetch Groq models: {e}[/warning]")
        
        # Default fallback list if everything fails
        if not self.online_models:
            self.online_models = ["gemini-2.0-flash", "llama-3.3-70b-versatile", "mixtral-8x7b-32768"]

        # Prioritize fallbacks
        self.fallback_models = ["gemma-4-31b-it","gemma-4-26b-a4b-it","gemma-3-27b-it","llama-3.1-8b-instant","gemma-3-12b-it"]
        

    def set_system_prompt(self, new_prompt):
        """Updates the system prompt while maintaining the message structure."""
        self.base_system_prompt = new_prompt
        content = self.base_system_prompt + (self.tools_prompt if self.tools_enabled else "")
        self.context.update_system_prompt(content)


    def _update_tools_prompt(self):
        """Refreshes the tools JSON schema in the system prompt."""
        if not self.tools_enabled:
            self.tools_prompt = ""
            return

        tool_schemas = registry.get_tool_schemas()
        self.tools_prompt = f"""
You are an advanced AI agent with access to a REAL persistent PowerShell session.
Your actions persist (e.g., changing directories, installing packages).

TASK EXECUTION FLOW:
1. REASON: Explain your plan inside <thought>...</thought> tags.
2. ACT: Execute ONE tool (JSON) per response if the task is not done.
3. OBSERVE: Receive the tool output and then decide on the next action.
4. FINISH: Only provide a final summary IF the task is fully verified and complete.

SKILLS:
Skills are task-specific knowledge modules that you can call to get information to perform tasks. 
They provide you with exact process flow to finish a task. You can call them using the 'get_skill_content' tool.
Like how to create advanced level documents, pdfs, spreadsheets, presentations, how to use APIs, how to do complex coding tasks, etc.
Skills are optional but use them if the user wants the best results. If a relevant skill exists, it is recommended to call it as it can provide you with the exact steps to finish a task.
Example: {{"tool": "get_skill_content", "parameters": {{"skill_name": "pdf_skill.md"}}}}
{json.dumps(skill_registry_inst.list_skills(), indent=2)}

IMPORTANT RULES:
- If you say you will do something, you MUST execute the tool in the same response.
- NEVER ask "Would you like me to...". Just do it.
- For complex tasks with multiple steps, perform ONE tool call at a time. I will show you the result, then you call the next tool.

TOOL CALL FORMAT (for local models):
To use a tool, output a JSON object. 
Example: {{"tool": "command_executor", "parameters": {{"command": "ls"}}}}

AVAILABLE TOOLS:
{json.dumps(tool_schemas, indent=2)}
"""
        
        # Update context
        self.context.update_system_prompt(self.base_system_prompt + self.tools_prompt)

    def _get_gemini_tools(self):
        """Converts registry tools to Gemini genai.types.Tool format."""
        if not self.tools_enabled:
            return None
            
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

    def _get_gemini_messages(self, messages):
        """Converts internal message history to Google GenAI format, supporting tool calls."""
        gemini_messages = []
        for msg in messages:
            if msg["role"] == "system":
                continue
            
            role = "user" if msg["role"] == "user" else "model"
            content = msg.get("content", "")
            
            tool_call = msg.get("tool_call")
            tool_call_part = msg.get("tool_call_part")
            tool_response = msg.get("tool_response")
            
            parts = []
            
            if "gemini_attachments" in msg:
                for att in msg["gemini_attachments"]:
                    parts.append(types.Part.from_uri(
                        file_uri=att.uri,
                        mime_type=att.mime_type
                    ))
                    
            if content and not tool_call_part:
                parts.append(types.Part.from_text(text=content))
            elif content and tool_call_part:
                parts.append(types.Part.from_text(text=content))
                
            if tool_call_part:
                parts.append(tool_call_part)
            
            if tool_call:
                # Legacy handling for offline or older models without native part
                parts.append(types.Part.from_function_call(
                    name=tool_call["name"],
                    args=tool_call["args"]
                ))
            
            if tool_response:
                # Get ID but allow it to be None
                func_id = tool_response.get("id")
                
                # Format name and response correctly
                resp_name = tool_response["name"]
                # response must be a dictionary
                resp_content = tool_response["content"]
                if not isinstance(resp_content, (dict, list, str, int, float, bool)):
                    resp_content = str(resp_content)
                
                parts.append(types.Part.from_function_response(
                    name=resp_name,
                    response={"result": resp_content}
                ))
                
                # Only set ID if it was originally provided to avoid malformed requests
                if func_id:
                    parts[-1].function_response.id = func_id
                
                role = "user" 

            if not parts:
                continue

            if gemini_messages and gemini_messages[-1].role == role:
                gemini_messages[-1].parts.extend(parts)
            else:
                gemini_messages.append(types.Content(role=role, parts=parts))
                
        return gemini_messages

    def _get_groq_messages(self, messages):
        """Converts internal message history to Groq/OpenAI format."""
        groq_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")
            
            # Handle tool calls in Groq format
            tool_call_part = msg.get("tool_call_part")
            tool_response = msg.get("tool_response")
            
            if tool_call_part:
                # Groq tool call format
                import time
                groq_messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": [{
                        "id": getattr(tool_call_part.function_call, "id", "call_" + str(time.time())),
                        "type": "function",
                        "function": {
                            "name": tool_call_part.function_call.name,
                            "arguments": json.dumps(tool_call_part.function_call.args)
                        }
                    }]
                })
                continue
            
            if tool_response:
                groq_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_response.get("id", "call_none"),
                    "name": tool_response["name"],
                    "content": str(tool_response["content"])
                })
                continue

            groq_messages.append({"role": role, "content": content})
        return groq_messages

    def _get_groq_tools(self):
        """Converts registry tools to Groq/OpenAI tool format."""
        if not self.tools_enabled:
            return None
            
        groq_tools = []
        for tool_name, tool_info in registry.tools.items():
            groq_tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info["description"],
                    "parameters": tool_info["parameters"]
                }
            })
        return groq_tools if groq_tools else None

    def set_model(self, model):
        """Sets the model to use and refreshes tools."""
        self.model = model
        self._update_tools_prompt()

    def set_tools_enabled(self, enabled):
        """Enable or disable tool access."""
        self.tools_enabled = enabled
        self._update_tools_prompt()

    def set_mode(self, mode):
        """Sets the mode (online/offline) and refreshes tools."""
        if self.mode == mode:
            return
        
        self.mode = mode
        if self.mode != "offline":
            if not hasattr(self, 'client'):
                try:
                    from config import ONLINE_MODE_GEMINI, ONLINE_MODE_GROQ
                    # Handle API key initialization and verification
                    if ONLINE_MODE_GEMINI:
                        self.client = genai.Client(api_key=ONLINE_MODE_GEMINI)
                    if ONLINE_MODE_GROQ:
                        self.groq_client = Groq(api_key=ONLINE_MODE_GROQ)
                    
                    if not self.client and not self.groq_client:
                        console.log("[warning]No API keys found. Please set ONLINE_MODE_GEMINI or ONLINE_MODE_GROQ in config.py[/warning]")
                        self.mode = "offline"
                        return
                        
                except ImportError:
                    from config import CLOUD_MODE
                    self.client = genai.Client(api_key=CLOUD_MODE)
                    self.groq_client = None
            self._fetch_online_models()
            # Ensure a valid model is selected if current model is local
            if not any(x in self.model.lower() for x in ["gemini", "gemma", "llama", "mixtral", "groq"]):
                self.model = self.online_models[0] if self.online_models else "gemini-2.0-flash"
        else:
            self.model = "deepseek-coder"
        
        self._update_tools_prompt()
    
    def get_available_models(self):
        """Returns a list of available models."""
        return self.available_models

    def run(self, user_input, attachments=None):
        if attachments is None:
            attachments = []
            
        console.log(f"[info]Input Received:[/info] {user_input[:50]}...")
        
        uploaded_attachments = []
        if attachments and self.mode != "offline":
            import os
            for path in attachments:
                if os.path.exists(path):
                    # For UI feedback during upload, we would yield here, but run() is a generator
                    # so we will just log it for now and it will block briefly.
                    try:
                        console.log(f"[info]Uploading attachment:[/info] {os.path.basename(path)}")
                        uploaded_file = self.client.files.upload(file=path)
                        uploaded_attachments.append(uploaded_file)
                    except Exception as e:
                        console.log(f"[error]Failed to upload attachment:[/error] {os.path.basename(path)}")
                else:
                    console.log(f"[warning]File not found:[/warning] {path}")

        self.context.add_message("user", user_input, gemini_attachments=uploaded_attachments)
        
        if getattr(self, "auto_route", False) and self.mode != "offline":
            try:
                yield f"__UI_STATUS__:🤔 [dim]Routing task...[/dim]"
                route_prompt = f"Given the user request, classify intent/complexity as 'IMAGE_GEN' (generating pictures/images), 'VIDEO_GEN' (generating videos), 'COMPLEX' (testing, planning, deep reasoning), 'MODERATE' (coding, summaries) or 'SIMPLE' (basic questions). Reply ONLY with one keyword. Request: {user_input[:500]}"
                resp = self.client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview",
                    contents=route_prompt
                )
                resp_text = resp.text.upper()
                
                if "IMAGE_GEN" in resp_text:
                    self.model = "gemini-3.1-flash-image-preview"
                    yield f"__UI_STATUS__:🎨 [dim]Auto-routed to Image Model[/dim]"
                elif "VIDEO_GEN" in resp_text:
                    self.model = "veo-3.1-generate-preview"
                    console.log("[info]Using model - veo-3.1-generate-preview.[/info]")
                    yield f"__UI_STATUS__:🎬 Auto-routed to Video Generation model."
                elif "COMPLEX" in resp_text:
                    self.model = "gemini-3.1-pro-preview"
                    console.log("[info]Using model - gemini-3.1-pro-preview.[/info]")
                elif "MODERATE" in resp_text:
                    self.model = "gemini-3-flash-preview"
                    console.log("[info]Using model - gemini-3-flash-preview.[/info]")
                else:
                    self.model = "gemini-3.1-flash-lite-preview"
                    console.log("[info]Using model - gemini-3.1-flash-lite-preview.[/info]")
            except Exception as e:
                yield f"__UI_STATUS__:⚠️ [dim]Fallback to {self.model}[/dim]"
        
        # console.log(f"Streaming from model: [italic]{self.model}[/italic]...")
        
        max_steps = 10
        step_count = 0
        
        full_content = ""
        try:
            while True:
                if step_count >= max_steps:
                    approved = (yield f"__MAX_STEPS_REACHED__:{max_steps}")
                    if approved:
                        max_steps += 10
                    else:
                        yield "__UI_STATUS__:⚠️ Task stopped: Maximum allowed tool steps reached."
                        break

                step_count += 1
                full_content = ""
                
                # Provide model client for summarization if available
                if hasattr(self, 'client') and self.context.model_client is None:
                    self.context.model_client = self.client
                
                # Get optimized context
                current_context = self.context.get_context()
                
                try:
                    if self.mode == "offline":
                        stream = ollama.chat(model=self.model, messages=current_context, stream=True)
                    elif self.groq_client and any(x in self.model.lower() for x in ["llama", "mixtral", "groq", "gemma"]):
                        # Groq execution logic
                        groq_msgs = self._get_groq_messages(current_context)
                        active_model = self.model
                        stream = self.groq_client.chat.completions.create(
                            model=active_model,
                            messages=groq_msgs,
                            tools=self._get_groq_tools(),
                            stream=True
                        )
                    else:
                        # Gemini execution logic
                        gemini_msgs = self._get_gemini_messages(current_context)
                        system_instr = next((m["content"] for m in current_context if m["role"] == "system"), "")
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
                        elif self.groq_client and any(x in self.model.lower() for x in ["llama", "mixtral", "groq"]):
                            # Groq Stream Handling
                            if chunk.choices:
                                delta = chunk.choices[0].delta
                                token = delta.content or ""
                                if token:
                                    has_yielded_token = True
                                    full_content += token
                                
                                if delta.tool_calls:
                                    is_tool_call = True
                                    tc = delta.tool_calls[0]
                                    if not native_tool_call:
                                        native_tool_call = types.Part(
                                            function_call=types.FunctionCall(
                                                name=tc.function.name,
                                                args={},
                                                id=tc.id
                                            )
                                        )
                                    if tc.function.arguments:
                                        # Incremental JSON parsing/buffering
                                        if not hasattr(self, '_groq_tc_buffer'): self._groq_tc_buffer = ""
                                        self._groq_tc_buffer += tc.function.arguments
                                        try:
                                            native_tool_call.function_call.args = json.loads(self._groq_tc_buffer)
                                        except:
                                            pass
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
                            
                            # For some models, they might repeat their previous thought if history is long.
                            # We check if the token starts with something we already yielded in this turn.
                            # (Though usually full_content is new each step, so repetition is between steps)
                            
                            if token:
                                has_yielded_token = True
                                full_content += token

                        if not self.tools_enabled:
                            yield full_content[yielded_len:]
                            yielded_len = len(full_content)
                            continue

                        # Detect JSON tool call marker (for offline mode or online models like Gemma that might output JSON)
                        if not is_tool_call:
                            if '"tool"' in full_content and '{' in full_content:
                                # Look for the first complete JSON object that looks like a tool call
                                import re
                                # Find all possible JSON-like blocks
                                matches = list(re.finditer(r'\{[^{}]*"(tool|tool_name|function)"[^{}]*\}', full_content))
                                if not matches:
                                    # Fallback for nested objects (more expensive check)
                                    matches = list(re.finditer(r'\{.*\}', full_content, re.DOTALL))
                                
                                if matches:
                                    # We take the first match that looks valid
                                    for match in matches:
                                        potential_json = match.group(0)
                                        try:
                                            # Quick check if it's usable
                                            test_data = json.loads(potential_json)
                                            if any(k in test_data for k in ["tool", "tool_name", "function"]):
                                                is_tool_call = True
                                                start_idx = match.start()
                                                if start_idx > yielded_len:
                                                    yield full_content[yielded_len:start_idx]
                                                    yielded_len = start_idx
                                                break
                                        except:
                                            continue

                        # Yield text chunks even if we are expecting a tool call (prevents preamble loss)
                        if not is_tool_call:
                            # PROACTIVE TOOL DETECTION: 
                            # If we see a '{', it MIGHT be a tool call. Buffer it.
                            potential_start = full_content.find('{', yielded_len)
                            if potential_start != -1:
                                # We stay silent from the first '{' onwards if it looks like a tool call
                                # or until we are sure it's NOT a tool call.
                                peek = full_content[potential_start:]
                                # If it's short, we wait for more context before yielding '{'
                                if len(peek) < 15:
                                    continue # Don't yield yet
                                
                                if '"tool' in peek or '"function' in peek or '"tool_name' in peek:
                                    # It's definitely a tool call starting
                                    if potential_start > yielded_len:
                                        text_to_yield = full_content[yielded_len:potential_start]
                                        if text_to_yield:
                                            yield text_to_yield
                                            yielded_len = potential_start
                                    # Stay silent for the JSON part
                                else:
                                    # Not a tool call, yield the buffered '{' and everything after
                                    yield full_content[yielded_len:]
                                    yielded_len = len(full_content)
                            else:
                                # No '{' found, yield normally
                                yield full_content[yielded_len:]
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
                    elif any(err in err_str.lower() for err in ["429", "404", "not found"]):
                         if not getattr(self, "auto_route", False):
                             yield f"__UI_STATUS__:❌ [bold red]API Error[/bold red]: {err_str} (Use /auto to enable automatic model fallback)"
                             break
                             
                         yield "__UI_STATUS__:🚨 [bold red]API Error/Quota[/bold red]: Retrying with next fallback model..."
                         
                         # Memory relief: aggressively prune context before retrying
                         system_msg = self.messages[0]
                         self.messages = [system_msg] + self.messages[-4:]
                         self._prune_tool_responses()
                         console.log(f"[info]Context pruned for fallback. Size: {self._get_context_chars()} chars.[/info]")
                         
                         current_idx = -1
                         if self.fallback_models and active_model in self.fallback_models:
                             current_idx = self.fallback_models.index(active_model)
                         
                         if self.fallback_models and current_idx + 1 < len(self.fallback_models):
                             self.model = self.fallback_models[current_idx + 1]
                             console.log(f"[info]API Error. Switched to fallback model: {self.model}[/info]")
                             step_count -= 1 # Repeat the step with new model
                             continue
                         else:
                             yield "__UI_STATUS__:🚨 [bold red]API Error[/bold red]: All fallback models exhausted."
                             break
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
                            # Use a more robust approach to find the JSON blob among full_content
                            import re
                            # Try to find the exact block we identified earlier
                            match = re.search(r'\{[^{}]*"(tool|tool_name|function)"[^{}]*\}', full_content)
                            if not match:
                                match = re.search(r'\{.*\}', full_content, re.DOTALL)
                            
                            if match:
                                json_str = match.group(0)
                                tool_data = json.loads(json_str)
                            else:
                                raise ValueError("Could not extract valid JSON tool call from response.")
                            
                            # Be flexible with keys
                            tool_name = tool_data.get("tool") or tool_data.get("tool_name") or tool_data.get("function") or tool_data.get("skill")
                            
                            # Special case: if 'skill' was used as a direct key
                            if "skill" in tool_data and not tool_name:
                                tool_name = "get_skill_content"
                                tool_params = {"skill_name": tool_data["skill"]}
                            elif tool_data.get("skill") == tool_name:
                                # For {"skill": "read_codebase.md"}
                                tool_name = "get_skill_content"
                                tool_params = {"skill_name": tool_data["skill"]}
                            else:
                                tool_params = tool_data.get("parameters") or tool_data.get("args") or tool_data.get("arguments") or {}
                            
                            if not tool_name:
                                raise ValueError("No tool name found in JSON blob.")
                        
                        params_hint = json.dumps(tool_params)[:50] + "..." if len(json.dumps(tool_params)) > 50 else json.dumps(tool_params)
                        yield f"__UI_STATUS__:🛠️ Call [accent]{tool_name}[/accent] [dim]{params_hint}[/dim]"
                        yield f"__TOOL_CALL__:{tool_name}:{json.dumps(tool_params)}"
                        
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

                        # Truncate large tool outputs before storing in history
                        stored_result = self.context.truncate_content(result, max_chars=self.max_tool_output_chars)

                        # Update Context
                        if native_tool_call:
                            # Get the FunctionCall ID if available
                            func_id = getattr(native_tool_call.function_call, "id", None)
                            self.context.add_message("assistant", full_content, tool_call_part=native_tool_call)
                            self.context.add_message("user", "", tool_response={"id": func_id, "name": tool_name, "content": stored_result})
                        else:
                            self.context.add_message("assistant", full_content)
                            self.context.add_message("user", f"Tool '{tool_name}' returned: {stored_result}")
                        
                        continue
                    except Exception as e:
                        yield f"__UI_STATUS__:❌ Error executing tool: {e}"
                        break
                else:
                    self.context.add_message("assistant", full_content)
                    
                    import re
                    clean_text = re.sub(r'<thought>(.*?)</thought>', '', full_content, flags=re.DOTALL).strip()
                    
                    if not clean_text and "<thought>" in full_content:
                        self.context.add_message("user", "Proceed with the execution using tools.")
                        yield "__UI_STATUS__:🤔 Thought received. Prompting agent to execute plan..."
                        continue
                        
                    if clean_text:
                        console.log("🏁 [info]Response generation complete.[/info]")
                        break
                    else:
                        # If we have no clean text and no tool call, something is wrong
                        if not is_tool_call:
                            yield "__UI_STATUS__:🚨 Model returned an empty response. You might need to rephrase or check your quota."
                            break
                        continue # If is_tool_call was True but no text, we just continue normally
        except KeyboardInterrupt:
            console.log("\n[error]⚠️ Generation interrupted.[/error]")
            self.add_message("assistant", full_content + "... [Interrupted]")
