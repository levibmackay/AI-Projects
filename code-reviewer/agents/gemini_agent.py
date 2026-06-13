from agents.base_agent import BaseAgent
from config.settings import GEMINI_API_KEY, GEMINI_MODEL


class GeminiAgent(BaseAgent):
    name = "Gemini 1.5 Flash"

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            self._model = genai.GenerativeModel(GEMINI_MODEL)
        return self._model

    def is_available(self) -> bool:
        return bool(GEMINI_API_KEY)

    def chat(self, messages: list[dict]) -> str:
        model = self._get_model()
        # Combine system + user into a single prompt for Gemini
        parts = []
        for m in messages:
            if m["role"] == "system":
                parts.append(f"[SYSTEM]\n{m['content']}\n")
            else:
                parts.append(m["content"])
        response = model.generate_content("\n".join(parts))
        return response.text
