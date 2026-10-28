from output_normalizer import normalize


def test_eslint_parse_error_does_not_crash():
    # regression: ruleId is null for parse errors and the old code called .lower() on it -> HTTP 500
    out = normalize({"eslint": [{"ruleId": None, "fatal": True, "severity": 2, "message": "Parsing error", "line": 1}]})
    finding = out["maintainability_findings"][0]
    assert finding["rule_id"] == "syntax-error" and finding["severity"] == "high"


def test_style_rules_are_not_performance():
    # regression: prefer-const / no-var used to be filed under performance
    out = normalize({"eslint": [
        {"ruleId": "prefer-const", "severity": 2, "message": "m", "line": 1},
        {"ruleId": "no-var", "severity": 2, "message": "m", "line": 2},
        {"ruleId": "no-await-in-loop", "severity": 2, "message": "m", "line": 3},
    ]})
    assert [f["rule_id"] for f in out["performance_findings"]] == ["no-await-in-loop"]
    assert len(out["maintainability_findings"]) == 2


def test_ruff_perf_rules_feed_the_performance_agent():
    out = normalize({"ruff": [
        {"code": "PERF401", "message": "m", "location": {"row": 4}},
        {"code": "F401", "message": "m", "location": {"row": 1}},
    ]})
    assert [f["rule_id"] for f in out["performance_findings"]] == ["PERF401"]
    assert [f["rule_id"] for f in out["maintainability_findings"]] == ["F401"]


def test_ruff_syntax_error_has_no_null_code_crash():
    out = normalize({"ruff": [{"code": None, "message": "m", "location": {"row": 1}}]})
    assert out["maintainability_findings"][0]["rule_id"] == "unknown"


def test_semgrep_category_comes_from_rule_metadata():
    def finding(category, check_id="some.path.rule"):
        return {"check_id": check_id, "start": {"line": 1},
                "extra": {"message": "m", "severity": "ERROR", "metadata": {"category": category}}}

    out = normalize({"semgrep": [finding("security"), finding("performance"), finding("best-practice")]})
    assert len(out["security_findings"]) == 1
    assert len(out["performance_findings"]) == 1
    assert len(out["maintainability_findings"]) == 1


def test_local_semgrep_rule_ids_do_not_leak_the_server_path():
    out = normalize({"semgrep": [{
        "check_id": "home.deploy.app.server.rules.js-exec-string-concat", "start": {"line": 1},
        "extra": {"message": "m", "severity": "ERROR", "metadata": {"category": "security"}},
    }]})
    assert out["security_findings"][0]["rule_id"] == "js-exec-string-concat"
