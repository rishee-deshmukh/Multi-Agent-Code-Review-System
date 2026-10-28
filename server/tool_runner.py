"""Runs the static analysers on a snippet and records which ones actually ran.

A tool that is missing, times out or crashes is reported in ``ToolReport.errors``
rather than silently becoming an empty findings list, so the API can tell the
caller that the LLM agents were running without grounding.
"""
import json
import logging
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from models import Language

logger = logging.getLogger(__name__)

RULES_DIR = Path(__file__).resolve().parent / "rules"

SEMGREP_TIMEOUT = 60
TOOL_TIMEOUT = 30

TOOLS_BY_LANGUAGE = {
    "python": ("semgrep", "bandit", "ruff"),
    "javascript": ("semgrep", "eslint"),
}

# ESLint >= 9 only understands flat config, so the rules live in a config file
# written next to the code. No plugins or parsers are imported: it works with
# any bare ESLint install.
ESLINT_CONFIG = """
export default [{
  files: ["**/*.js"],
  languageOptions: { ecmaVersion: 2022, sourceType: "module" },
  rules: {
    "no-var": "error",
    "no-unused-vars": "error",
    "no-eval": "error",
    "no-implied-eval": "error",
    "no-new-func": "error",
    "no-await-in-loop": "error",
    "no-loop-func": "error",
    "no-constant-condition": "error",
    "no-unreachable": "error",
    "no-duplicate-case": "error",
    "no-empty": "error",
    "eqeqeq": "error",
    "curly": "error",
    "no-throw-literal": "error",
    "prefer-const": "error",
    "no-console": "warn",
    "no-process-exit": "warn",
    "complexity": ["warn", 10],
    "max-depth": ["warn", 4],
    "max-params": ["warn", 5],
  },
}];
"""

# E/F: pycodestyle + pyflakes defaults; B: bugbear; C90: complexity; PERF: perflint; SIM: simplifications
RUFF_SELECT = "E,F,B,C90,PERF,SIM"


class ToolError(Exception):
    """A tool could not produce usable output."""


@dataclass
class ToolReport:
    outputs: dict = field(default_factory=lambda: {"semgrep": [], "bandit": [], "ruff": [], "eslint": []})
    errors: dict = field(default_factory=dict)  # tool name -> why it produced nothing

    @property
    def warnings(self) -> list[str]:
        return [f"{tool} did not run, so its findings are missing: {err}" for tool, err in self.errors.items()]


def run_tools(code: str, language: Language, filename: str | None = None) -> ToolReport:
    suffix = ".py" if language == "python" else ".js"
    report = ToolReport()

    with tempfile.TemporaryDirectory(prefix="review-") as workdir:
        path = os.path.join(workdir, f"code{suffix}")
        Path(path).write_text(code, encoding="utf-8")

        runners = {
            "semgrep": lambda: _run_semgrep(path, language, workdir),
            "bandit":  lambda: _run_bandit(path, workdir),
            "ruff":    lambda: _run_ruff(path, workdir),
            "eslint":  lambda: _run_eslint(path, workdir),
        }
        tools = TOOLS_BY_LANGUAGE[language]

        with ThreadPoolExecutor(max_workers=len(tools)) as executor:
            futures = {name: executor.submit(runners[name]) for name in tools}
            for name, future in futures.items():
                try:
                    report.outputs[name] = future.result()
                except ToolError as e:
                    logger.warning("%s failed: %s", name, e)
                    report.errors[name] = str(e)
                except Exception as e:
                    logger.exception("%s crashed", name)
                    report.errors[name] = f"unexpected error: {e}"

    return report


def _exec(cmd: list[str], cwd: str, timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except FileNotFoundError:
        raise ToolError(f"'{cmd[0]}' is not installed") from None
    except subprocess.TimeoutExpired:
        raise ToolError(f"timed out after {timeout}s") from None


def _load_json(proc: subprocess.CompletedProcess):
    if not proc.stdout.strip():
        raise ToolError(f"no output (exit {proc.returncode}): {proc.stderr.strip()[-300:]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise ToolError(f"invalid JSON output: {e}") from None


def _semgrep_configs(language: str) -> list[str]:
    """Local rules always; registry packs only if SEMGREP_EXTRA_CONFIGS is set (needs network)."""
    local = RULES_DIR / f"{language}.yml"
    if not local.exists():
        raise ToolError(f"rule file {local} is missing")
    extra = [c.strip() for c in os.getenv("SEMGREP_EXTRA_CONFIGS", "").split(",") if c.strip()]
    return [str(local), *extra]


def _run_semgrep(path: str, language: str, cwd: str) -> list:
    cmd = ["semgrep", "scan", "--json", "--quiet", "--metrics=off", "--disable-version-check", "--no-git-ignore"]
    for config in _semgrep_configs(language):
        cmd += ["--config", config]
    proc = _exec(cmd + [path], cwd, SEMGREP_TIMEOUT)

    data = _load_json(proc)
    results = data.get("results", [])
    errors = [e for e in data.get("errors", []) if e.get("level") == "error"]
    if errors and not results:
        raise ToolError(errors[0].get("message", "semgrep reported an error")[:300])
    return results


def _run_bandit(path: str, cwd: str) -> list:
    # bandit exits 1 when it finds issues, so the exit code says nothing about failure
    data = _load_json(_exec(["bandit", "-f", "json", "-q", path], cwd, TOOL_TIMEOUT))
    return data.get("results", [])


def _run_ruff(path: str, cwd: str) -> list:
    # --isolated: ignore any pyproject/ruff.toml the host happens to have
    cmd = ["ruff", "check", "--isolated", "--no-cache", "--output-format=json",
           f"--select={RUFF_SELECT}", "--config", "lint.mccabe.max-complexity = 10", path]
    return _load_json(_exec(cmd, cwd, TOOL_TIMEOUT))


def _run_eslint(path: str, cwd: str) -> list:
    Path(cwd, "eslint.config.mjs").write_text(ESLINT_CONFIG, encoding="utf-8")
    proc = _exec(["eslint", "--format=json", path], cwd, TOOL_TIMEOUT)

    data = _load_json(proc)
    messages = []
    for file_result in data:
        messages.extend(file_result.get("messages", []))
    return messages
