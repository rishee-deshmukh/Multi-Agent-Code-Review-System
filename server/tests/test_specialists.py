from agents.security_agent import security_agent
from agents.performance_agent import performance_agent
from tests.conftest import specialist_json


def state(**extra):
    return {"code": "x = 1", "filename": "app.py", "security_findings": [], "performance_findings": [], **extra}


def test_llm_failure_is_reported_not_reported_as_clean(fake_llm):
    fake_llm.respond = lambda s, u: (_ for _ in ()).throw(RuntimeError("API key not valid"))
    update = security_agent(state())
    assert update["security_issues"] == []
    assert update["failed_agents"] == ["security"]
    assert "API key not valid" in update["warnings"][0]


def test_unparseable_answer_is_reported(fake_llm):
    fake_llm.respond = lambda s, u: "I refuse"
    assert performance_agent(state())["failed_agents"] == ["performance"]


def test_empty_array_is_a_legitimate_clean_result(fake_llm):
    fake_llm.respond = lambda s, u: "[]"
    update = security_agent(state())
    assert update == {"security_issues": []}


def test_issue_fields_are_normalised(fake_llm):
    fake_llm.respond = lambda s, u: specialist_json()  # severity "HIGH" upper-case
    issue = security_agent(state())["security_issues"][0]
    assert issue.severity == "high"
    assert issue.agent == "security" and issue.agent_agreement == ["security"]


def test_malformed_items_are_dropped_with_a_warning(fake_llm):
    fake_llm.respond = lambda s, u: '[{"issue_type": "A", "line": "not-a-number"}, "garbage", ' + specialist_json()[1:]
    update = security_agent(state())
    assert len(update["security_issues"]) == 1
    assert "2 malformed" in update["warnings"][0]
