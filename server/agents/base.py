"""Shared implementation of the three specialist agents.

Security, Performance and Maintainability differ only in their prompt, the
static-analysis findings they receive and the label on the issues they emit.
"""
import json
import logging
from dataclasses import dataclass

from agents.state import AgentState
from llm import LLMError, generate_json
from models import Issue

logger = logging.getLogger(__name__)

VALID_SEVERITIES = {"critical", "high", "medium", "low"}


@dataclass(frozen=True)
class SpecialistSpec:
    name: str          # "security" | "performance" | "maintainability"
    prompt: str        # system prompt
    tools_label: str   # which static tools feed this agent, shown to the LLM


def build_user_message(code: str, filename: str, findings: list, tools_label: str) -> str:
    if findings:
        findings_text = json.dumps(findings, indent=2)
    else:
        findings_text = "No static analysis findings available. Analyze the code directly."

    # no backtick fences around code — avoids breaking if user code contains backticks
    return f"""
FILENAME: {filename}

STATIC ANALYSIS FINDINGS ({tools_label}):
{findings_text}

SOURCE CODE:
{code}

Review the code and findings above. Return your findings as a JSON array.
"""


def parse_issues(items: list, spec: SpecialistSpec, filename: str) -> tuple[list[Issue], int]:
    """Convert raw LLM dicts to Issues. Returns (issues, number skipped as malformed)."""
    issues, skipped = [], 0
    for item in items:
        try:
            severity = str(item.get("severity", "medium")).lower()
            if severity not in VALID_SEVERITIES:
                severity = "medium"
            issues.append(Issue(
                agent=spec.name,
                category=spec.name,
                issue_type=item.get("issue_type") or "Unknown",
                severity=severity,
                file=item.get("file") or filename,
                line=max(1, int(item.get("line", 1))),
                evidence=str(item.get("evidence", "")),
                llm_reasoning=str(item.get("llm_reasoning", "")),
                suggested_fix=str(item.get("suggested_fix", "")),
                confidence=min(1.0, max(0.0, float(item.get("confidence", 0.5)))),
                agent_agreement=[spec.name],
                cross_domain_notes=None,
            ))
        except Exception as e:
            # one bad issue shouldn't lose the whole response
            skipped += 1
            logger.warning("Skipping malformed issue from %s agent: %s", spec.name, e)
    return issues, skipped


def run_specialist(spec: SpecialistSpec, state: AgentState) -> dict:
    filename = state.get("filename") or "submitted_code"
    findings = state.get(f"{spec.name}_findings", [])
    user_message = build_user_message(state["code"], filename, findings, spec.tools_label)

    try:
        items = generate_json(spec.prompt, user_message, list)
    except LLMError as e:
        logger.error("%s agent failed: %s", spec.name, e)
        return {
            f"{spec.name}_issues": [],
            "failed_agents": [spec.name],
            "warnings": [f"{spec.name} agent failed and its findings are missing: {e}"],
        }

    issues, skipped = parse_issues([i for i in items if isinstance(i, dict)], spec, filename)
    skipped += len(items) - len([i for i in items if isinstance(i, dict)])

    update: dict = {f"{spec.name}_issues": issues}
    if skipped:
        update["warnings"] = [f"{spec.name} agent: {skipped} malformed issue(s) were dropped"]
    return update
