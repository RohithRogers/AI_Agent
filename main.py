# from agents.chat_agent import ChatAgent
# from tools.time_tool import *
# from tools.file_tool import *
# from tools.registry import ToolRegistry

# register = ToolRegistry()
# register.register_tool("read_file", read_file, "Reads the content of a file at the specified path.", {"type": "object", "properties": {"path": {"type": "string", "description": "The full path to the file."}}, "required": ["path"]}, requires_permission=True)
# register.register_tool("get_current_time", get_current_time, "Returns the current local time.", {"type": "object", "properties": {}}, requires_permission=False)
# agent = ChatAgent()

# while True:
#     user_input = input("User >> ")
#     if user_input.lower() in ["exit", "quit"]:
#         break
#     full_response = ""
#     gen = agent.run(user_input)
#     try:
#         chunk = next(gen)
#         while True:
#             if isinstance(chunk, str) and chunk.startswith("__ASK_PERMISSION__"):
#                 parts = chunk.split(":", 2)
#                 print(f"\n[Permission Required] Tool {parts[1]} with params {parts[2]}")
#                 choice = input("Allow? (y/n): ")
#                 chunk = gen.send(choice.lower() in ["y", "yes", ""])
#             else:
#                 if chunk is not None:
#                     full_response += chunk
#                     print(chunk, end="", flush=True)
#                 chunk = next(gen)
#     except StopIteration:
#         pass
#     print()
import difflib

with open('garden.txt', 'r') as f1, open('edited.txt', 'r') as f2:
    original = f1.readlines()
    edited = f2.readlines()

hd = difflib.HtmlDiff()
with open('diff.html', 'w') as f:
    f.write(hd.make_file(original, edited))