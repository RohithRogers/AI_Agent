from agents.chat_agent import ChatAgent
from tools.time_tool import *
from tools.file_tool import *
from tools.registry import ToolRegistry

register = ToolRegistry()
register.register_tool("read_file", read_file, "Reads the content of a file at the specified path.", {"type": "object", "properties": {"path": {"type": "string", "description": "The full path to the file."}}, "required": ["path"]})
register.register_tool("get_current_time", get_current_time, "Returns the current local time.", {"type": "object", "properties": {}})
agent = ChatAgent()

while True:
    user_input = input("User >> ")
    if user_input.lower() in ["exit", "quit"]:
        break
    response = agent.run(user_input)
    print(f"Agent >> {response}")
