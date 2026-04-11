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
        
        self.online_models = []
        self.fallback_models = []
        
        # History management settings
        self.max_history_messages = 20
        self.retain_messages = 6
        
        # Initialize GenAI client if in online mode
        if self.mode != "offline":
            from config import CLOUD_MODE
            self.client = genai.Client(api_key=CLOUD_MODE)
            self._fetch_online_models()
            # Ensure model is a valid model if none provided
            if "gemini" not in self.model.lower() and "gemma" not in self.model.lower():
                self.model = self.online_models[0] if self.online_models else "gemini-2.0-flash"

    def _fetch_online_models(self):
        """Fetches available models from the API and categorizes them."""
        try:
            all_models = self.client.models.list()
            # Most Gemini/Gemma models support generation. We filter out embeddings and other specialty models.
            self.online_models = []
            for m in all_models:
                name = m.name.replace("models/", "")
                # Skip embedding and other non-chat models
                if any(x in name for x in ["embedding", "aqa", "lyria", "robotics", "computer-use"]):
                    continue
                self.online_models.append(name)
            
            # Prioritize Gemma models as fallbacks
            self.fallback_models = [m for m in self.online_models if "gemma" in m.lower()]
            # Ensure gemma-4-31b-it is high in fallback priority if it exists
            self.fallback_models.sort(key=lambda x: "gemma-4" in x.lower() or "gemma-3" in x.lower(), reverse=True)
            
            # If no gemma models, use flash-lite as fallback
            if not self.fallback_models:
                self.fallback_models = [m for m in self.online_models if "flash-lite" in m.lower()]
        except Exception as e:
            console.log(f"[warning]Failed to fetch online models: {e}[/warning]")
            # Fallback to hardcoded list if API call fails
            self.online_models = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash", "gemma-2-9b-it"]
            self.fallback_models = ["gemma-2-9b-it"]

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
2. ACT: Execute ONE tool (JSON) per response if the task is not done.
3. OBSERVE: Receive the tool output and then decide on the next action.
4. FINISH: Only provide a final summary IF the task is fully verified and complete.

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
            
            if "gemini_attachments" in msg:
                for att in msg["gemini_attachments"]:
                    parts.append(att)
                    
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
                
                # Check for "auth error" related issues: 
                # Some models expect a specific key structure or no ID if not provided in call
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

    def _summarize_history(self):
        """Compresses long conversation history into a summary to save tokens."""
        if len(self.messages) <= self.max_history_messages:
            return

        # Keep system prompt (index 0) and the most recent N messages
        system_msg = self.messages[0]
        recent_messages = self.messages[-self.retain_messages:]
        messages_to_summarize = self.messages[1:-self.retain_messages]

        if not messages_to_summarize:
            return

        summary_prompt = "Summarize the following conversation history into a concise list of key points and important context. Focus on what has been accomplished and current state. Reply ONLY with the summary.\n\n"
        for msg in messages_to_summarize:
            role = msg["role"]
            content = msg.get("content", "")
            if not content and "tool_call" in msg:
                content = f"[Tool Call: {msg['tool_call']['name']}]"
            elif not content and "tool_call_part" in msg:
                 content = f"[Tool Call: {msg['tool_call_part'].function_call.name}]"
            elif not content and "tool_response" in msg:
                 content = f"[Tool Response: {msg['tool_response']['name']}]"
            summary_prompt += f"{role.upper()}: {content}\n"

        try:
            console.log("[info]Summarizing history to save tokens...[/info]")
            if self.mode == "offline":
                resp = ollama.chat(model=self.model, messages=[
                    {"role": "user", "content": summary_prompt}
                ])
                summary = resp['message']['content']
            else:
                # Use a lightweight model for summarization if possible
                summary_model = "gemini-2.0-flash-lite" if "gemini" in self.model.lower() else self.model
                resp = self.client.models.generate_content(
                    model=summary_model,
                    contents=summary_prompt
                )
                summary = resp.text

            new_summary_msg = {
                "role": "user", 
                "content": f"[Previous Conversation Summary: {summary}]"
            }
            
            # Reconstruct history: System + Summary + Recent
            self.messages = [system_msg, new_summary_msg] + recent_messages
            console.log("[info]History summarized successfully.[/info]")
        except Exception as e:
            console.log(f"[warning]Failed to summarize history: {e}[/warning]")

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
            self._fetch_online_models()
            # Ensure a valid Gemini model is selected if current model is local
            if "gemini" not in self.model.lower() and "gemma" not in self.model.lower():
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
                    console.log(f"[info]Uploading attachment:[/info] {os.path.basename(path)}")
                    uploaded_file = self.client.files.upload(file=path)
                    uploaded_attachments.append(uploaded_file)
                else:
                    console.log(f"[warning]File not found:[/warning] {path}")

        new_msg = {"role": "user", "content": user_input}
        if uploaded_attachments:
            new_msg["gemini_attachments"] = uploaded_attachments
        
        # Optional: For Ollama, we might be able to add images directly using base64, 
        # but requires specific keys. We skip for offline right now or handle later if requested.
        
        self.messages.append(new_msg)
        
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
            while step_count < max_steps:
                step_count += 1
                full_content = ""
                
                # Manage history size before each model call
                self._summarize_history()
                
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
                            # Check if we are potentially starting a tool call
                            # If we see '{"tool' or '{"function', we stop yielding and buffer to avoid printing raw JSON
                            potential_start = full_content.find('{', yielded_len)
                            if potential_start != -1:
                                peek = full_content[potential_start:]
                                if '"tool' in peek or '"function' in peek:
                                    # We have a potential tool call starting. 
                                    # Yield only what's before the '{'
                                    if potential_start > yielded_len:
                                        yield full_content[yielded_len:potential_start]
                                        yielded_len = potential_start
                                    # Stay silent for the rest (the JSON part)
                                else:
                                    # Not a tool call start yet, yield normally
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
                    elif "429" in err_str:
                         yield "__UI_STATUS__:🚨 [bold red]Quota Exceeded[/bold red]: Retrying with fallback model..."
                         if self.fallback_models and active_model != self.fallback_models[0]:
                             self.model = self.fallback_models[0]
                             console.log(f"[info]Quota hit. Switched to fallback model: {self.model}[/info]")
                             step_count -= 1 # Repeat the step with new model
                             continue
                         else:
                             yield "__UI_STATUS__:🚨 [bold red]Quota Exceeded[/bold red]: All fallback models exhausted or rate limit too high."
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
                            tool_name = tool_data.get("tool") or tool_data.get("tool_name") or tool_data.get("function")
                            tool_params = tool_data.get("parameters") or tool_data.get("args") or tool_data.get("arguments") or {}
                            
                            if not tool_name:
                                raise ValueError("No tool name found in JSON blob.")
                        
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
                            # Reconstruct the tool call part to ensure it's a clean data object
                            # rather than a 'live' part from the stream
                            clean_call_part = types.Part.from_function_call(
                                name=native_tool_call.function_call.name,
                                args=native_tool_call.function_call.args
                            )
                            
                            # Get the FunctionCall ID if available
                            func_id = getattr(native_tool_call.function_call, "id", None)
                            if func_id:
                                clean_call_part.function_call.id = func_id

                            self.messages.append({
                                "role": "assistant", 
                                "content": full_content, 
                                "tool_call_part": clean_call_part
                            })
                            
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
                        
                    if clean_text:
                        console.log("🏁 [info]Response generation complete.[/info]")
                        break
                    else:
                        # If we have no clean text and no tool call, something is wrong
                        if not is_tool_call:
                            yield "__UI_STATUS__:🚨 Model returned an empty response. You might need to rephrase or check your quota."
                            break
                        continue # If is_tool_call was True but no text, we just continue normally
            
            if step_count >= max_steps:
                yield "__UI_STATUS__:⚠️ Task stopped: Maximum allowed tool steps reached."
        except KeyboardInterrupt:
            console.log("\n[error]⚠️ Generation interrupted.[/error]")
            self.add_message("assistant", full_content + "... [Interrupted]")
