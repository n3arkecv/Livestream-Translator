import json
import os
from typing import Optional

class ContextManager:
    """
    Manages the scenario context for translation.
    """
    def __init__(self, max_tokens: int = 500):
        self.context = ""
        self.max_tokens = max_tokens

    def get_context(self) -> str:
        return self.context

    def update_context(self, new_context: str):
        """
        Updates the current context with the new summary from LLM2.
        """
        self.context = new_context

    def save_cache(self, path: str):
        """
        Saves the current context to a file.
        """
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({"context": self.context}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving context cache: {e}")

    def load_cache(self, path: str):
        """
        Loads context from a file.
        """
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.context = data.get("context", "")
        except Exception as e:
            print(f"Error loading context cache: {e}")

