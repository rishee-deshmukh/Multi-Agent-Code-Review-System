import json

import pytest

import llm
from models import Issue


def make_issue(agent="security", **overrides) -> Issue:
    fields = dict(
        agent=agent, category=agent, issue_type="SQL Injection", severity="high",
        file="app.py", line=10, evidence="e", llm_reasoning="r", suggested_fix="f",
        confidence=0.5, agent_agreement=[agent], cross_domain_notes=None,
    )
    fields.update(overrides)
    return Issue(**fields)


@pytest.fixture
def fake_llm(monkeypatch):
    """Replace the single network call in llm.py. Set ``fake_llm.respond`` to a callable
    ``(system_prompt, user_message) -> str`` (or raise) to script the model."""
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


def specialist_json(issue_type="SQL Injection", line=3):
    return json.dumps([{
        "issue_type": issue_type, "severity": "HIGH", "file": "app.py", "line": line,
        "evidence": "e", "llm_reasoning": "r", "suggested_fix": "f", "confidence": 0.9,
    }])
