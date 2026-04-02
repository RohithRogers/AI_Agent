class BaseAgent:
    def __init__(self, model="deepseek-coder", system_prompt=""):
        self.model = model
        self.system_prompt = system_prompt
        self.messages = [{"role": "system", "content": system_prompt}]

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})

    def get_messages(self):
        return self.messages

    def run(self, user_input):
        raise NotImplementedError("Subclasses must implement the run method.")
