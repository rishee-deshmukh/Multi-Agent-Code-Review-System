"""The systems under comparison. Each takes one file and returns normalized predictions.

tools_only            static analysers alone, no LLM (floor: what the tools give you for free)
single_llm            one Gemini call, one generic prompt, no tools, no agents
multi_agent_no_tools  the full graph (3 specialists + synthesizer) with the static findings withheld
multi_agent           the full system: static findings ground the specialists

Comparing them separates the contribution of each idea: tools_only vs multi_agent is
the value of the LLMs; single_llm vs multi_agent_no_tools is the value of the agent
structure; multi_agent_no_tools vs multi_agent is the value of grounding.
Only security and performance predictions are scored: maintainability has no
objective ground truth.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))

from agents.graph import review_graph  # noqa: E402
from llm import LLMError, generate_json  # noqa: E402
from output_normalizer import _normalize_severity  # noqa: E402
from pipeline import analyze  # noqa: E402
from taxonomy import CATEGORY_OF, OTHER, classify, tool_rule_class  # noqa: E402
from tool_runner import TOOLS_BY_LANGUAGE, run_tools  # noqa: E402

SCORED_CATEGORIES = ("security", "performance")
SYSTEMS = ("tools_only", "single_llm", "multi_agent_no_tools", "multi_agent")

SINGLE_LLM_PROMPT = """
You are an expert code reviewer. Review the code for security vulnerabilities and
performance problems.

Return ONLY a JSON array. Each element must have exactly these fields:
  "issue_type": short name, e.g. "SQL Injection" or "N+1 Query"
  "category":   "security" or "performance"
  "severity":   "critical" | "high" | "medium" | "low"
  "line":       integer line number of the problem
  "evidence":   the offending code
  "llm_reasoning": why it is a problem
  "suggested_fix": how to fix it
  "confidence": float 0.0-1.0

Report only real problems. If there are none, return [].
"""


@dataclass
class Run:
    predictions: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    error: str | None = None   # set when the system could not produce a result at all


def _prediction(line, category, issue_type, severity, cls, agent="", confidence=None) -> dict:
    return {"line": int(line), "category": category, "issue_type": issue_type,
            "severity": severity, "class": cls, "agent": agent, "confidence": confidence}


def run_tools_only(code: str, filename: str, language: str) -> Run:
    report = run_tools(code, language, filename)
    run = Run(warnings=report.warnings)
    if all(tool in report.errors for tool in TOOLS_BY_LANGUAGE[language]):
        run.error = "all static tools failed: " + "; ".join(report.warnings)
        return run
    out = report.outputs

    for f in out["semgrep"]:
        meta = f.get("extra", {}).get("metadata") or {}
        cwe = meta.get("cwe")
        cwe = cwe[0] if isinstance(cwe, list) and cwe else cwe
        rule = f.get("check_id", "").rsplit(".rules.", 1)[-1]
        cls = tool_rule_class(rule, cwe)
        category = CATEGORY_OF.get(cls) or meta.get("category")
        if category in SCORED_CATEGORIES:
            run.predictions.append(_prediction(f["start"]["line"], category, rule,
                                               _normalize_severity(f["extra"].get("severity", "INFO")), cls, "semgrep"))

    for f in out["bandit"]:
        cls = tool_rule_class(f.get("test_id", ""), (f.get("issue_cwe") or {}).get("id"))
        run.predictions.append(_prediction(f["line_number"], CATEGORY_OF.get(cls, "security"), f.get("test_name", ""),
                                           _normalize_severity(f.get("issue_severity", "LOW")), cls, "bandit"))

    for f in out["ruff"]:
        if str(f.get("code") or "").startswith("PERF"):
            run.predictions.append(_prediction(f["location"]["row"], "performance", f["code"], "low", OTHER, "ruff"))

    for f in out["eslint"]:
        if f.get("ruleId") in ("no-await-in-loop", "no-loop-func"):
            cls = tool_rule_class(f["ruleId"])
            run.predictions.append(_prediction(f["line"], "performance", f["ruleId"],
                                               _normalize_severity(str(f.get("severity", 1))), cls, "eslint"))
    return run


def run_single_llm(code: str, filename: str, language: str) -> Run:
    user_message = f"FILENAME: {filename}\n\nSOURCE CODE:\n{code}\n\nReturn your findings as a JSON array."
    try:
        items = generate_json(SINGLE_LLM_PROMPT, user_message, list)
    except LLMError as e:
        return Run(error=str(e))

    run = Run()
    for item in items:
        try:
            category = str(item.get("category", "")).lower()
            if category not in SCORED_CATEGORIES:
                continue
            issue_type = str(item.get("issue_type", ""))
            run.predictions.append(_prediction(
                item.get("line", 1), category, issue_type, str(item.get("severity", "")).lower(),
                classify(issue_type, category), "single_llm", item.get("confidence")))
        except Exception:
            run.warnings.append(f"dropped malformed item: {item!r}"[:200])
    return run


def run_multi_agent(code: str, filename: str, language: str, grounded: bool = True) -> Run:
    _, state, warnings = analyze(code, filename, language)
    if not grounded:
        state["security_findings"] = state["performance_findings"] = state["maintainability_findings"] = []

    result = review_graph.invoke(state)
    run = Run(warnings=warnings + result.get("warnings", []))
    if result.get("failed_agents"):
        # a missing agent means missing findings: scoring the rest would understate recall
        run.error = "agent(s) failed: " + ", ".join(result["failed_agents"])
        return run

    for issue in result.get("final_issues", []):
        if issue.category in SCORED_CATEGORIES:
            run.predictions.append(_prediction(
                issue.line, issue.category, issue.issue_type, issue.severity,
                classify(issue.issue_type, issue.category), issue.agent, issue.confidence))
    return run


def run_system(name: str, code: str, filename: str, language: str) -> Run:
    if name == "tools_only":
        return run_tools_only(code, filename, language)
    if name == "single_llm":
        return run_single_llm(code, filename, language)
    if name == "multi_agent_no_tools":
        return run_multi_agent(code, filename, language, grounded=False)
    if name == "multi_agent":
        return run_multi_agent(code, filename, language, grounded=True)
    raise ValueError(f"unknown system {name!r}; choose from {SYSTEMS}")
