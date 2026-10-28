import pytest

import llm


@pytest.fixture
def fake_llm(monkeypatch):
    """Script the model: set ``fake_llm.respond`` to ``(system_prompt, user_message) -> str``."""
    class Fake:
        respond = staticmethod(lambda system_prompt, user_message: "[]")
        calls = 0

    fake = Fake()

    def _generate_text(client, system_prompt, user_message):
        fake.calls += 1
        return fake.respond(system_prompt, user_message)

    monkeypatch.setattr(llm, "_client", lambda: object())
    monkeypatch.setattr(llm, "_generate_text", _generate_text)
    monkeypatch.setattr(llm, "RETRY_DELAYS", (0, 0, 0))
    return fake
