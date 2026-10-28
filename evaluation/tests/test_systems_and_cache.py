import json

import pytest

import llm
import systems
from agents.prompts import SYNTHESIZER_PROMPT
from llm_cache import CachedLLM

CODE = "import os\nos.system(input())\n"


def specialist_reply(system_prompt, user_message):
    if system_prompt == SYNTHESIZER_PROMPT:
        return json.dumps({"merged_issues": [], "new_issues": [], "summary": "s", "fixed_code": CODE})
    return json.dumps([{"issue_type": "OS Command Injection", "severity": "critical", "line": 2, "confidence": 0.9}])


def test_single_llm_maps_names_to_classes_and_drops_other_categories(fake_llm):
    fake_llm.respond = lambda s, u: json.dumps([
        {"issue_type": "SQL Injection", "category": "security", "severity": "Critical", "line": 4},
        {"issue_type": "Missing docstring", "category": "maintainability", "severity": "low", "line": 1},
        {"issue_type": "Await in loop", "category": "performance", "severity": "high", "line": 9},
    ])
    run = systems.run_single_llm(CODE, "d01.py", "python")
    assert [(p["class"], p["severity"]) for p in run.predictions] == [("sql_injection", "critical"), ("io_in_loop", "high")]


def test_single_llm_failure_is_an_error_not_an_empty_result(fake_llm):
    fake_llm.respond = lambda s, u: (_ for _ in ()).throw(RuntimeError("quota"))
    assert systems.run_single_llm(CODE, "d01.py", "python").error


def test_multi_agent_end_to_end(fake_llm):
    fake_llm.respond = specialist_reply
    run = systems.run_multi_agent(CODE, "d01.py", "python")
    assert run.error is None
    assert run.predictions and run.predictions[0]["class"] == "command_injection"


def test_multi_agent_without_tools_withholds_the_findings(fake_llm):
    seen = []
    fake_llm.respond = lambda s, u: (seen.append(u), specialist_reply(s, u))[1]
    systems.run_multi_agent(CODE, "d01.py", "python", grounded=False)
    assert seen and all("No static analysis findings available" in u for u in seen[:3])


def test_multi_agent_reports_total_failure(fake_llm):
    fake_llm.respond = lambda s, u: (_ for _ in ()).throw(RuntimeError("down"))
    assert "failed" in systems.run_multi_agent(CODE, "d01.py", "python").error


def test_unknown_system():
    with pytest.raises(ValueError):
        systems.run_system("nope", CODE, "x.py", "python")


# --- cache ---

@pytest.fixture
def cache(tmp_path, monkeypatch, fake_llm):
    monkeypatch.setattr(llm, "_generate_text", llm._generate_text)  # restore after install()
    monkeypatch.setattr(llm, "_client", llm._client)
    fake_llm.respond = lambda s, u: '["live"]'
    return lambda **kw: CachedLLM(tmp_path / "cache", **kw)


def test_second_call_is_a_cache_hit(cache, fake_llm):
    c = cache().install()
    assert llm.generate_json("sys", "user", list) == ["live"]
    assert llm.generate_json("sys", "user", list) == ["live"]
    assert fake_llm.calls == 1 and (c.calls, c.hits) == (2, 1)


def test_changing_the_prompt_invalidates_the_entry(cache, fake_llm):
    cache().install()
    llm.generate_json("sys v1", "user", list)
    llm.generate_json("sys v2", "user", list)
    assert fake_llm.calls == 2


def test_offline_mode_fails_on_a_miss_and_needs_no_credentials(cache, fake_llm):
    cache().install()
    llm.generate_json("sys", "user", list)

    cache(offline=True).install()
    assert llm.generate_json("sys", "user", list) == ["live"]
    with pytest.raises(llm.LLMError, match="offline"):
        llm.generate_json("never cached", "user", list)
