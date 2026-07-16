import pytest

from agents import router


class _FakeAvailable:
    def is_available(self):
        return True


class _FakeUnavailable:
    def is_available(self):
        return False


class _FakeError:
    def __init__(self):
        raise RuntimeError("boom")


def test_get_agent_respects_preferred_available(monkeypatch):
    monkeypatch.setattr(router, "GroqAgent", _FakeUnavailable)
    monkeypatch.setattr(router, "GeminiAgent", _FakeAvailable)
    monkeypatch.setattr(router, "OllamaAgent", _FakeUnavailable)

    agent = router.get_agent("gemini")

    assert isinstance(agent, _FakeAvailable)


def test_get_agent_raises_when_none_available(monkeypatch):
    monkeypatch.setattr(router, "GroqAgent", _FakeUnavailable)
    monkeypatch.setattr(router, "GeminiAgent", _FakeUnavailable)
    monkeypatch.setattr(router, "OllamaAgent", _FakeUnavailable)

    with pytest.raises(RuntimeError, match="No AI provider available"):
        router.get_agent("auto")


def test_get_all_available_skips_failing_constructors(monkeypatch):
    monkeypatch.setattr(router, "GroqAgent", _FakeError)
    monkeypatch.setattr(router, "GeminiAgent", _FakeAvailable)
    monkeypatch.setattr(router, "OllamaAgent", _FakeUnavailable)

    available = router.get_all_available()

    assert len(available) == 1
    assert isinstance(available[0], _FakeAvailable)
