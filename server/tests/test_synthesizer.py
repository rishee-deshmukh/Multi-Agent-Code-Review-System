import json

from agents.synthesizer_agent import synthesizer_agent
from tests.conftest import make_issue


def state(*issues):
    return {
        "code": "orig", "filename": "app.py",
        "security_issues": [i for i in issues if i.agent == "security"],
        "performance_issues": [i for i in issues if i.agent == "performance"],
        "maintainability_issues": [i for i in issues if i.agent == "maintainability"],
    }


def reply(**fields):
    base = {"merged_issues": [], "new_issues": [], "summary": "s", "fixed_code": "fixed"}
    return lambda s, u: json.dumps({**base, **fields})


def test_issues_the_llm_did_not_group_are_kept(fake_llm):
    # regression: the old code only emitted issues that appeared in merged_issues
    a, b, c = make_issue(line=1), make_issue("performance", line=2), make_issue("maintainability", line=3)
    fake_llm.respond = reply(merged_issues=[{"indices": [0, 1]}])
    result = synthesizer_agent(state(a, b, c))
    assert len(result["final_issues"]) == 2
    assert sorted(i.line for i in result["final_issues"]) == [1, 3]


def test_no_groups_at_all_still_returns_every_issue(fake_llm):
    fake_llm.respond = reply()
    issues = [make_issue(line=n) for n in (1, 2, 3)]
    assert len(synthesizer_agent(state(*issues))["final_issues"]) == 3


def test_an_index_listed_in_two_groups_is_not_duplicated(fake_llm):
    fake_llm.respond = reply(merged_issues=[{"indices": [0, 1]}, {"indices": [1, 2]}])
    issues = [make_issue(line=n) for n in (1, 2, 3)]
    assert len(synthesizer_agent(state(*issues))["final_issues"]) == 2


def test_bad_indices_are_ignored(fake_llm):
    fake_llm.respond = reply(merged_issues=[{"indices": [99, -1, "x", True, None]}, "junk"])
    assert len(synthesizer_agent(state(make_issue()))["final_issues"]) == 1


def test_confidence_reflects_agent_agreement(fake_llm):
    fake_llm.respond = reply(merged_issues=[{"indices": [0, 1, 2]}])
    issues = [make_issue("security"), make_issue("performance"), make_issue("maintainability")]
    merged = synthesizer_agent(state(*issues))["final_issues"][0]
    assert merged.confidence == 1.0
    assert merged.agent_agreement == ["security", "performance", "maintainability"]


def test_invalid_relabelling_keeps_the_issue(fake_llm):
    fake_llm.respond = reply(merged_issues=[{"indices": [0], "severity": "catastrophic"}])
    assert len(synthesizer_agent(state(make_issue()))["final_issues"]) == 1


def test_unparseable_answer_is_retried_then_falls_back_with_warning(fake_llm):
    fake_llm.respond = lambda s, u: "no json here"
    result = synthesizer_agent(state(make_issue(line=1), make_issue(line=2)))
    assert fake_llm.calls == 3
    assert len(result["final_issues"]) == 2
    assert result["fixed_code"] == "orig"
    assert "synthesizer failed" in result["warnings"][0]


def test_empty_fixed_code_falls_back_to_original(fake_llm):
    fake_llm.respond = reply(fixed_code="")
    assert synthesizer_agent(state(make_issue()))["fixed_code"] == "orig"


def test_new_issues_are_added(fake_llm):
    fake_llm.respond = reply(new_issues=[{
        "category": "security", "issue_type": "IDOR", "severity": "high", "line": 4,
    }])
    result = synthesizer_agent(state(make_issue()))
    assert {i.issue_type for i in result["final_issues"]} == {"SQL Injection", "IDOR"}
