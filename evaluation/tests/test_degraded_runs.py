import json
import sys

import pytest

import run_eval
from agents.prompts import SYNTHESIZER_PROMPT, SECURITY_PROMPT
from records import degraded, hit_daily_quota
from systems import run_multi_agent

CODE = "import os\nos.system(input())\n"
DAILY = "429 RESOURCE_EXHAUSTED quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier"


def healthy(system_prompt, user_message):
    if system_prompt == SYNTHESIZER_PROMPT:
        return json.dumps({"merged_issues": [], "new_issues": [], "summary": "s", "fixed_code": CODE})
    return json.dumps([{"issue_type": "OS Command Injection", "severity": "critical", "line": 2}])


@pytest.mark.parametrize("record,expected", [
    ({"error": None, "warnings": []}, False),
    ({"error": "boom", "warnings": []}, True),
    ({"error": None, "warnings": ["security agent failed and its findings are missing: 429"]}, True),
    ({"error": None, "warnings": ["synthesizer failed, results are not merged or deduplicated: x"]}, True),
    ({"error": None, "warnings": ["semgrep did not run, so its findings are missing: timed out"]}, False),
    ({"error": None, "warnings": ["security agent: 2 malformed issue(s) were dropped"]}, False),
])
def test_degraded(record, expected):
    assert degraded(record) is expected


def test_one_failed_specialist_makes_the_file_an_error_not_a_partial_result(fake_llm):
    # previously this was scored as a normal result with a warning, silently understating recall
    def respond(system_prompt, user_message):
        if system_prompt == SECURITY_PROMPT:
            raise RuntimeError("503 unavailable")
        return healthy(system_prompt, user_message)

    fake_llm.respond = respond
    run = run_multi_agent(CODE, "d01.py", "python")
    assert run.error == "agent(s) failed: security"


def test_a_failed_synthesizer_makes_the_file_an_error(fake_llm):
    fake_llm.respond = lambda s, u: "not json" if s == SYNTHESIZER_PROMPT else healthy(s, u)
    assert "synthesizer" in run_multi_agent(CODE, "d01.py", "python").error


def test_daily_quota_is_detected_from_warnings_and_errors():
    assert hit_daily_quota({"error": None, "warnings": ["security agent failed ...: daily API quota exhausted; re-run"]})
    assert hit_daily_quota({"error": "daily API quota exhausted; re-run", "warnings": []})
    assert not hit_daily_quota({"error": "503", "warnings": []})


def test_run_stops_at_the_first_daily_quota_error_and_keeps_what_it_has(fake_llm, tmp_path, monkeypatch, capsys):
    fake_llm.respond = lambda s, u: (_ for _ in ()).throw(RuntimeError(DAILY))
    monkeypatch.setattr(sys, "argv", ["run_eval", "--system", "single_llm", "--limit", "5",
                                      "--results-dir", str(tmp_path / "r"), "--cache-dir", str(tmp_path / "c")])
    assert run_eval.main() == 2
    out = capsys.readouterr().out
    assert "daily quota is exhausted" in out and "[2/5]" not in out
    assert fake_llm.calls == 1   # did not burn the quota (or the afternoon) on the other four files


def test_resume_reruns_degraded_results_and_keeps_good_ones(fake_llm, tmp_path, monkeypatch):
    results = tmp_path / "r"
    results.mkdir()
    good = {"predictions": [], "warnings": [], "error": None, "seconds": 1, "llm_calls": 0, "cache_hits": 0}
    bad = {**good, "warnings": ["security agent failed and its findings are missing: 429"]}
    (results / "multi_agent.json").write_text(json.dumps({"system": "multi_agent", "files": {"dev/d01.py": good, "dev/d02.py": bad}}))

    fake_llm.respond = healthy
    monkeypatch.setattr(sys, "argv", ["run_eval", "--system", "multi_agent", "--limit", "2", "--resume",
                                      "--results-dir", str(results), "--cache-dir", str(tmp_path / "c")])
    run_eval.main()
    saved = json.loads((results / "multi_agent.json").read_text())["files"]
    assert saved["dev/d01.py"] == good                      # untouched
    assert not degraded(saved["dev/d02.py"])                # re-run and now healthy
