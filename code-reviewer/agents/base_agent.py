from abc import ABC, abstractmethod


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def chat(self, messages: list[dict]) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    def ask(self, system: str, user: str) -> str:
        return self.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])
