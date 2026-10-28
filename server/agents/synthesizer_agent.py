import json
import logging
from agents.state import AgentState
from agents.prompts import SYNTHESIZER_PROMPT
from llm import LLMError, generate_json
from models import Issue

logger = logging.getLogger(__name__)

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
AGENT_ORDER = ["security", "performance", "maintainability"]


def synthesizer_agent(state: AgentState) -> dict:
    code = state["code"]
    filename = state.get("filename") or "submitted_code"

    all_issues = (
        state.get("security_issues", []) +
        state.get("performance_issues", []) +
        state.get("maintainability_issues", [])
    )

    user_message = _build_user_message(code, filename, all_issues)

    try:
        result = _call_llm(user_message, filename)
    except LLMError as e:
        logger.warning("Synthesizer failed — falling back to raw agent outputs: %s", e)
        return {
            "final_issues": sorted(all_issues, key=lambda i: SEVERITY_RANK[i.severity]),
            "summary": "Synthesis failed. Showing raw agent findings.",
            "fixed_code": code,
            "warnings": [f"synthesizer failed, results are not merged or deduplicated: {e}"],
        }

    final_issues = _reconstruct_issues(result["merged_issues"], all_issues)
    final_issues += result["new_issues"]
    final_issues.sort(key=lambda i: SEVERITY_RANK[i.severity])

    return {
        "final_issues": final_issues,
        "summary": result["summary"],
        # an empty string would blank the "fixed code" panel; keep the original instead
        "fixed_code": result["fixed_code"] or code,
    }


def _build_user_message(code: str, filename: str, all_issues: list) -> str:
    # send stripped fields only — the synthesizer doesn't need evidence/llm_reasoning to merge
    indexed = [
        {
            "index": i,
            "agent": issue.agent,
            "category": issue.category,
            "issue_type": issue.issue_type,
            "severity": issue.severity,
            "file": issue.file,
            "line": issue.line,
            "suggested_fix": issue.suggested_fix,
        }
        for i, issue in enumerate(all_issues)
    ]

    return f"""
FILENAME: {filename}

AGENT ISSUES ({len(all_issues)} total):
{json.dumps(indexed, indent=2)}

ORIGINAL SOURCE CODE:
{code}

Perform synthesis following all 3 steps. Return JSON object.
"""


def _reconstruct_issues(merged_issues: list, all_issues: list[Issue]) -> list[Issue]:
    """Build final issues from the LLM's index groups.

    Every specialist issue ends up in exactly one group. Indices the LLM
    left out are kept as single-issue groups, and an index it listed twice
    is only honoured in the first group, so the synthesizer can merge issues
    but can never silently drop or duplicate them.
    """
    groups: list[tuple[list[int], dict]] = []
    claimed: set[int] = set()

    for group in merged_issues:
        if not isinstance(group, dict):
            continue
        indices = [
            i for i in dict.fromkeys(group.get("indices", []))
            if isinstance(i, int) and not isinstance(i, bool)
            and 0 <= i < len(all_issues) and i not in claimed
        ]
        if not indices:
            continue
        claimed.update(indices)
        groups.append((indices, group))

    for i in range(len(all_issues)):
        if i not in claimed:
            groups.append(([i], {}))

    result = []
    for indices, group in groups:
        # representative: prefer security, then performance, then maintainability
        def agent_priority(idx):
            agent = all_issues[idx].agent
            return AGENT_ORDER.index(agent) if agent in AGENT_ORDER else 99

        base = all_issues[min(indices, key=agent_priority)]
        agent_agreement = sorted({all_issues[i].agent for i in indices}, key=AGENT_ORDER.index)

        # confidence based on how many agents agree
        n = len(agent_agreement)
        confidence = 1.0 if n >= 3 else 0.67 if n == 2 else 0.33

        try:
            result.append(Issue(
                agent="synthesizer",
                category=group.get("category", base.category),
                issue_type=group.get("issue_type", base.issue_type),
                severity=group.get("severity", base.severity),
                file=base.file,
                line=base.line,
                evidence=base.evidence,
                llm_reasoning=base.llm_reasoning,
                suggested_fix=base.suggested_fix,
                confidence=confidence,
                agent_agreement=agent_agreement,
                cross_domain_notes=group.get("cross_domain_notes", None),
            ))
        except Exception as e:
            # the LLM's relabelling was invalid — keep the specialist's own values rather than lose the issue
            logger.warning("Invalid merge metadata (%s) — keeping original issue", e)
            result.append(base.model_copy(update={
                "agent": "synthesizer",
                "confidence": confidence,
                "agent_agreement": agent_agreement,
            }))

    return result


def _parse_new_issues(items: list, filename: str) -> list[Issue]:
    issues = []
    for item in items:
        try:
            issues.append(Issue(
                agent="synthesizer",
                category=item.get("category", "security"),
                issue_type=item.get("issue_type", "Unknown"),
                severity=item.get("severity", "low"),
                file=item.get("file", filename),
                line=max(1, int(item.get("line", 1))),
                evidence=item.get("evidence", ""),
                llm_reasoning=item.get("llm_reasoning", ""),
                suggested_fix=item.get("suggested_fix", ""),
                confidence=0.4,
                agent_agreement=["synthesizer"],
                cross_domain_notes=None,
            ))
        except Exception as e:
            logger.warning("Skipping malformed new issue from synthesizer: %s", e)
    return issues


def _call_llm(user_message: str, filename: str) -> dict:
    parsed = generate_json(SYNTHESIZER_PROMPT, user_message, dict)

    merged = parsed.get("merged_issues", [])
    new_issues = parsed.get("new_issues", [])

    return {
        "merged_issues": merged if isinstance(merged, list) else [],
        "new_issues": _parse_new_issues(new_issues if isinstance(new_issues, list) else [], filename),
        "summary": str(parsed.get("summary", "")),
        "fixed_code": str(parsed.get("fixed_code", "")),
    }
