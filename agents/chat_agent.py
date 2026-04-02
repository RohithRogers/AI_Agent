import ollama
import json
from agents.base_agent import BaseAgent
from tools.registry import registry

class ChatAgent(BaseAgent):
    def __init__(self, model="deepseek-coder", system_prompt=""):
        # Store original prompts for mode switching
        self.base_system_prompt = system_prompt
        tool_schemas = registry.get_tool_schemas()
        self.tools_prompt = f"\n\nYou have access to the following tools:\n{json.dumps(tool_schemas, indent=2)}\n\nIf you need to use a tool, respond in this EXACT JSON format:\n{{\"tool\": \"TOOL_NAME\", \"parameters\": {{ \"PARAM_NAME\": \"VALUE\" }} }}\nDo not say anything else when calling a tool."
        
        super().__init__(model, self.base_system_prompt + self.tools_prompt)

    def set_system_prompt(self, new_prompt):
        """Updates the system prompt while maintaining the message structure."""
        self.base_system_prompt = new_prompt
        # Update the system message (usually at index 0)
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = self.base_system_prompt + self.tools_prompt
        else:
            # Fallback if no system message exists
            self.messages.insert(0, {"role": "system", "content": self.base_system_prompt + self.tools_prompt})

    def run(self, user_input):
        self.add_message("user", user_input)
        
        while True:
            # Check for tool call vs normal response by getting a non-streamed check or just streaming and buffering
            # For simplicity in this implementation, we stream and buffer. 
            # If the buffer looks like a tool call, we handle it.
            full_content = ""
            stream = ollama.chat(model=self.model, messages=self.messages, stream=True)
            
            is_tool_call = False
            for chunk in stream:
                token = chunk['message']['content']
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
                    
                    # Yield a status message
                    yield f"\n[bold yellow]⚙️ Executing {tool_name}...[/bold yellow]\n"
                    
                    result = registry.execute_tool(tool_name, tool_params)
                    
                    # Feed the result back
                    self.add_message("assistant", full_content)
                    self.add_message("user", f"Tool '{tool_name}' returned: {result}")
                    continue # Let the LLM process the result
                except Exception as e:
                    yield f"\n[bold red]❌ Error parsing tool call: {e}[/bold red]\n"
                    break
            else:
                self.add_message("assistant", full_content)
                break
