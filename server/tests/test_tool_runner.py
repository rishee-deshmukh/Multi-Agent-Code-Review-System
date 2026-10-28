import shutil

import pytest

import tool_runner
from output_normalizer import normalize
from tool_runner import run_tools

JS_VULN = """
const express = require("express");
const { exec } = require("child_process");
const app = express();
app.get("/ping", (req, res) => {
    exec("ping -c 1 " + req.query.host, (err, out) => res.send(out));
});
"""
PY_VULN = "import os\nuser = input()\nos.system(user)\n"


def needs(*tools):
    return pytest.mark.skipif(any(shutil.which(t) is None for t in tools), reason=f"{tools} not installed")


@pytest.mark.integration
@needs("semgrep")
def test_semgrep_uses_javascript_rules_for_javascript():
    # regression: the language was never passed, so JS was scanned with the Python ruleset
    report = run_tools(JS_VULN, "javascript")
    assert not report.errors
    assert report.outputs["semgrep"], "expected the JS command-injection rules to fire"
    assert all("py-" not in f["check_id"] for f in report.outputs["semgrep"])


@pytest.mark.integration
@needs("semgrep", "bandit", "ruff")
def test_python_tools_find_command_injection():
    report = run_tools(PY_VULN, "python")
    assert not report.errors
    assert report.outputs["semgrep"] and report.outputs["bandit"]


@pytest.mark.integration
@needs("eslint")
def test_eslint_runs_with_flat_config():
    # regression: --no-eslintrc was removed in ESLint 9 so every invocation failed
    report = run_tools("var x = 1;\n", "javascript")
    assert "eslint" not in report.errors
    assert any(f["ruleId"] == "no-var" for f in report.outputs["eslint"])


@pytest.mark.integration
@needs("eslint", "semgrep")
def test_js_syntax_error_flows_through_normalizer():
    report = run_tools("const x = ;", "javascript")
    findings = normalize(report.outputs)["maintainability_findings"]
    assert any(f["rule_id"] == "syntax-error" for f in findings)


@pytest.mark.integration
@needs("ruff")
def test_ruff_performance_rules_are_enabled():
    code = "def f(xs):\n    out = []\n    for x in xs:\n        out.append(x * 2)\n    return out\n"
    report = run_tools(code, "python")
    assert any(f["code"].startswith("PERF") for f in report.outputs["ruff"])


def test_missing_tool_is_reported_not_swallowed(monkeypatch):
    monkeypatch.setenv("PATH", "")
    report = run_tools("x = 1", "python")
    assert set(report.errors) == {"semgrep", "bandit", "ruff"}
    assert "not installed" in report.errors["bandit"]
    assert len(report.warnings) == 3


def test_timeout_is_reported(monkeypatch):
    import subprocess

    def slow(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ruff", timeout=1)

    monkeypatch.setattr(tool_runner.subprocess, "run", slow)
    report = run_tools("x = 1", "python")
    assert "timed out" in report.errors["ruff"]


def test_missing_rule_file_is_reported(monkeypatch, tmp_path):
    monkeypatch.setattr(tool_runner, "RULES_DIR", tmp_path)
    report = run_tools("x = 1", "python")
    assert "rule file" in report.errors["semgrep"]
