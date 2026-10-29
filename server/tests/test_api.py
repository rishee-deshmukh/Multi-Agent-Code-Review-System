import json

import pytest
from fastapi.testclient import TestClient

import main
import pipeline
from limits import RequestGuard
from agents.prompts import SYNTHESIZER_PROMPT
from tests.conftest import specialist_json
from tool_runner import ToolReport

client = TestClient(main.app)
BODY = {"code": "import os\nos.system(input())", "filename": "t.py"}


@pytest.fixture(autouse=True)
def no_real_tools(monkeypatch):
    monkeypatch.setattr(pipeline, "run_tools", lambda code, language, filename=None: ToolReport())


@pytest.fixture(autouse=True)
def open_guard(monkeypatch):
    monkeypatch.setattr(main, "guard", RequestGuard(max_code_chars=0, per_minute=0, daily_budget=0, max_concurrent=0))


def healthy_model(system_prompt, user_message):
    if system_prompt == SYNTHESIZER_PROMPT:
        return json.dumps({"merged_issues": [], "new_issues": [], "summary": "ok", "fixed_code": "fixed"})
    return specialist_json()


def sse_events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_review_happy_path(fake_llm):
    fake_llm.respond = healthy_model
    body = client.post("/review", json=BODY).json()
    assert body["total_issues"] == 3  # one per specialist, none dropped by the synthesizer
    assert body["fixed_code"] == "fixed"
    assert body["warnings"] == []


def test_review_returns_502_when_every_agent_fails(fake_llm):
    # regression: this used to be HTTP 200 with zero issues, indistinguishable from clean code
    fake_llm.respond = lambda s, u: (_ for _ in ()).throw(RuntimeError("API key not valid"))
    response = client.post("/review", json=BODY)
    assert response.status_code == 502
    assert "unavailable or misconfigured" in response.json()["detail"]


def test_review_surfaces_partial_failure_as_warning(fake_llm):
    def flaky(system_prompt, user_message):
        if "performance" in system_prompt.lower()[:200]:
            raise RuntimeError("quota")
        return healthy_model(system_prompt, user_message)

    fake_llm.respond = flaky
    response = client.post("/review", json=BODY)
    assert response.status_code == 200
    assert any("performance agent failed" in w for w in response.json()["warnings"])


def test_tool_failures_are_returned_as_warnings(fake_llm, monkeypatch):
    fake_llm.respond = healthy_model
    monkeypatch.setattr(pipeline, "run_tools", lambda *a, **k: ToolReport(errors={"semgrep": "timed out after 60s"}))
    warnings = client.post("/review", json=BODY).json()["warnings"]
    assert any("semgrep did not run" in w for w in warnings)


def test_stream_event_order(fake_llm):
    fake_llm.respond = healthy_model
    events = sse_events(client.post("/stream", json=BODY))
    names = [e["event"] for e in events]
    assert names[:2] == ["language", "tools_done"]
    assert set(names[2:5]) == {"security_done", "performance_done", "maintainability_done"}
    assert names[5:] == ["synthesis_done", "done"]


def test_stream_emits_error_event_when_every_agent_fails(fake_llm):
    fake_llm.respond = lambda s, u: (_ for _ in ()).throw(RuntimeError("down"))
    events = sse_events(client.post("/stream", json=BODY))
    assert events[-1]["event"] == "error"
    assert "done" not in [e["event"] for e in events]


def test_empty_code_is_rejected():
    assert client.post("/review", json={"code": ""}).status_code == 422


def test_oversized_code_gets_413_before_any_work_is_done(fake_llm, monkeypatch):
    monkeypatch.setattr(main, "guard", RequestGuard(max_code_chars=10, per_minute=0, daily_budget=0, max_concurrent=0))
    for path in ("/review", "/stream"):
        response = client.post(path, json=BODY)
        assert response.status_code == 413
        assert "limit" in response.json()["detail"]
    assert fake_llm.calls == 0


def test_rate_limit_applies_to_both_endpoints_and_spares_health(fake_llm, monkeypatch):
    fake_llm.respond = healthy_model
    monkeypatch.setattr(main, "guard", RequestGuard(max_code_chars=0, per_minute=2, daily_budget=0, max_concurrent=0))
    assert client.post("/review", json=BODY).status_code == 200
    assert client.post("/stream", json=BODY).status_code == 200
    for path in ("/review", "/stream"):
        response = client.post(path, json=BODY)
        assert response.status_code == 429
        assert "Retry-After" in response.headers
    assert client.get("/health").status_code == 200


def test_concurrency_slot_is_freed_after_a_stream_finishes_and_after_a_failed_review(fake_llm, monkeypatch):
    fake_llm.respond = healthy_model
    monkeypatch.setattr(main, "guard", RequestGuard(max_code_chars=0, per_minute=0, daily_budget=0, max_concurrent=1))
    for _ in range(3):
        assert client.post("/stream", json=BODY).status_code == 200
        assert client.post("/review", json=BODY).status_code == 200
    fake_llm.respond = lambda s, u: (_ for _ in ()).throw(RuntimeError("down"))
    assert client.post("/review", json=BODY).status_code == 502
    fake_llm.respond = healthy_model
    assert main.guard._active == 0
    assert client.post("/review", json=BODY).status_code == 200


def test_cors_origins_come_from_the_environment(monkeypatch):
    import importlib
    monkeypatch.setenv("CORS_ORIGINS", "https://demo.example.com, https://other.example.com")
    reloaded = importlib.reload(main)
    try:
        response = TestClient(reloaded.app).options(
            "/review", headers={"Origin": "https://demo.example.com", "Access-Control-Request-Method": "POST"})
        assert response.headers.get("access-control-allow-origin") == "https://demo.example.com"
        refused = TestClient(reloaded.app).options(
            "/review", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
        assert "access-control-allow-origin" not in refused.headers
    finally:
        monkeypatch.undo()
        importlib.reload(main)
