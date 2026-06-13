from agents.base_agent import BaseAgent
from agents.router import get_agent, get_all_available
from reviewers.prompts import (
    SYSTEM, FULL_REVIEW, QUICK_REVIEW, SECURITY_REVIEW,
    PERFORMANCE_REVIEW, ROAST, MULTI_MODEL_MERGE,
)
from utils.language_detector import detect
from utils import history

PROMPT_MAP = {
    "full": FULL_REVIEW,
    "quick": QUICK_REVIEW,
    "security": SECURITY_REVIEW,
    "performance": PERFORMANCE_REVIEW,
    "roast": ROAST,
}


def review(
    code: str,
    mode: str = "full",
    language: str = None,
    agent_name: str = "auto",
    filepath: str = None,
    multi_model: bool = False,
) -> dict:
    language = language or detect(code, filepath)
    if language == "unknown":
        language = "code"

    if multi_model:
        return _multi_model_review(code, mode, language)

    agent = get_agent(agent_name)
    prompt_template = PROMPT_MAP.get(mode, FULL_REVIEW)
    prompt = prompt_template.format(code=code, language=language)

    result = agent.ask(SYSTEM, prompt)
    saved_path = history.save(code, language, mode, agent.name, result)

    return {
        "review": result,
        "language": language,
        "agent": agent.name,
        "mode": mode,
        "saved": saved_path,
    }


def _multi_model_review(code: str, mode: str, language: str) -> dict:
    agents = get_all_available()
    if not agents:
        raise RuntimeError("No agents available")

    if len(agents) == 1:
        return review(code, mode, language, multi_model=False)

    prompt_template = PROMPT_MAP.get(mode, FULL_REVIEW)
    prompt = prompt_template.format(code=code, language=language)

    individual_reviews = []
    for agent in agents:
        try:
            result = agent.ask(SYSTEM, prompt)
            individual_reviews.append(f"=== Review from {agent.name} ===\n\n{result}")
        except Exception as e:
            individual_reviews.append(f"=== {agent.name} failed: {e} ===")

    merge_prompt = MULTI_MODEL_MERGE.format(reviews="\n\n".join(individual_reviews))
    primary_agent = agents[0]
    merged = primary_agent.ask(SYSTEM, merge_prompt)

    saved_path = history.save(
        code, language, f"{mode}:multi",
        f"Multi-model ({', '.join(a.name for a in agents)})", merged
    )

    return {
        "review": merged,
        "language": language,
        "agent": f"Multi-model ({len(agents)} models)",
        "mode": mode,
        "saved": saved_path,
        "individual_reviews": individual_reviews,
    }


class ChatSession:
    def __init__(self, code: str, initial_review: str, language: str, agent_name: str = "auto"):
        self.code = code
        self.language = language
        self.agent = get_agent(agent_name)
        from reviewers.prompts import CHAT_SYSTEM
        self.messages = [
            {"role": "system", "content": CHAT_SYSTEM},
            {"role": "user", "content": f"Here is the code I want to discuss:\n\n```{language}\n{code}\n```"},
            {"role": "assistant", "content": f"Got it. Here is my initial review:\n\n{initial_review}"},
        ]

    def ask(self, question: str) -> str:
        self.messages.append({"role": "user", "content": question})
        response = self.agent.chat(self.messages)
        self.messages.append({"role": "assistant", "content": response})
        return response
