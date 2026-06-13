from agents.base_agent import BaseAgent
from agents.groq_agent import GroqAgent
from agents.gemini_agent import GeminiAgent
from agents.ollama_agent import OllamaAgent


def get_agent(preferred: str = "auto") -> BaseAgent:
    """Return the best available agent."""
    candidates = {
        "groq": GroqAgent,
        "gemini": GeminiAgent,
        "ollama": OllamaAgent,
    }

    if preferred != "auto" and preferred in candidates:
        agent = candidates[preferred]()
        if agent.is_available():
            return agent

    for cls in [GroqAgent, GeminiAgent, OllamaAgent]:
        agent = cls()
        if agent.is_available():
            return agent

    raise RuntimeError(
        "No AI provider available. Add a GROQ_API_KEY or GEMINI_API_KEY to your .env file, "
        "or install Ollama at https://ollama.com"
    )


def get_all_available() -> list[BaseAgent]:
    agents = []
    for cls in [GroqAgent, GeminiAgent, OllamaAgent]:
        try:
            a = cls()
            if a.is_available():
                agents.append(a)
        except Exception:
            pass
    return agents
