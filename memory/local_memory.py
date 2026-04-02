import json
import os
from .base_memory import BaseMemory

class LocalMemory(BaseMemory):
    def __init__(self, storage_path="history.json"):
        super().__init__()
        self.storage_path = storage_path
        self.load()

    def add_message(self, role, content):
        super().add_message(role, content)
        self.save()

    def save(self):
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    self.history = json.load(f)
            except Exception as e:
                print(f"Error loading history: {e}")
                self.history = []
