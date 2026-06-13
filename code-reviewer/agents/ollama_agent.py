from agents.base_agent import BaseAgent
from config.settings import OLLAMA_MODEL


class OllamaAgent(BaseAgent):
    name = f"Ollama (local)"

    def __init__(self, model: str = None):
        self.model = model or OLLAMA_MODEL
        self.name = f"Ollama ({self.model})"

    def is_available(self) -> bool:
        try:
            import ollama
            ollama.list()
            return True
        except Exception:
            return False

    def chat(self, messages: list[dict]) -> str:
        import ollama
        resp = ollama.chat(model=self.model, messages=messages, options={"num_predict": 2048})
        # Support both dict-style and object-style responses across ollama versions
        if hasattr(resp, "message"):
            return resp.message.content
        return resp["message"]["content"]
