# from agents.chat_agent import ChatAgent
# from tools.time_tool import *
# from tools.file_tool import *
from tools.registry import ToolRegistry

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


# import difflib

# with open('garden.txt', 'r') as f1, open('edited.txt', 'r') as f2:
#     original = f1.readlines()
#     edited = f2.readlines()

# hd = difflib.HtmlDiff()
# with open('diff.html', 'w') as f:
#     f.write(hd.make_file(original, edited))

# from google import genai
# from config import CLOUD_MODE

# client = genai.Client(api_key=CLOUD_MODE)

# # Test gemma 4 for tool calling

# tool_prompt = '''You are an AI assistant. And you have access to tools like checking time. Return a JSON object with the tool name and parameters.
#                 JSON type:
#                 {
#                     "tool_name": "<tool_name>",
#                     "parameters": {
#                         "<parameter_name>": "<parameter_value>"
#                     }
#                 }
# '''
# try:
#     response = client.models.generate_content_stream(
#         model="gemma-4-31b-it",
#         contents=tool_prompt + "tell me a joke"
#     )
#     for chunk in response:
#         print(chunk.text, end="", flush=True)
# except Exception as e:
#      print(e)

# import subprocess
# subprocess.Popen("cmd", creationflags=subprocess.CREATE_NEW_CONSOLE)

from google import genai
from google.genai import types
from PIL import Image
from config import CLOUD_MODE

client = genai.Client(api_key=CLOUD_MODE)

# prompt = ("Create a picture of a nano banana dish in a fancy restaurant with a Gemini theme")
# response = client.models.generate_content(
#     model="gemini-3-flash-image-preview",
#     contents=[prompt],
# )

models = client.models.list()
for model in models:
    print(model.name)

# for part in response.parts:
#     if part.text is not None:
#         print(part.text)
#     elif part.inline_data is not None:
#         image = part.as_image()
#         image.save("generated_image.png")
