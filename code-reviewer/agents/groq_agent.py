from agents.base_agent import BaseAgent
from config.settings import GROQ_API_KEY, GROQ_MODELS
import time


class GroqAgent(BaseAgent):
    name = "Groq (Llama 3.3 70B)"

    def __init__(self, model: str = "best"):
        self.model = GROQ_MODELS.get(model, GROQ_MODELS["best"])
        self._client = None

    def _get_client(self):
        if self._client is None:
            from groq import Groq
            self._client = Groq(api_key=GROQ_API_KEY)
        return self._client

    def is_available(self) -> bool:
        return bool(GROQ_API_KEY)

    def chat(self, messages: list[dict]) -> str:
        client = self._get_client()
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=4096,
                )
                return resp.choices[0].message.content
            except Exception as e:
                err = str(e).lower()
                if "rate_limit" in err and attempt < 2:
                    # Fall back to faster model on rate limit
                    self.model = GROQ_MODELS["fast"]
                    time.sleep(2)
                    continue
                raise
        raise RuntimeError("Groq failed after retries")
