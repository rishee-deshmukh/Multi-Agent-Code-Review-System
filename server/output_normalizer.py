import logging

logger = logging.getLogger(__name__)

NormalizedFinding = dict

# ESLint rules that point at runtime cost; everything else it reports is style/maintainability
ESLINT_PERFORMANCE_RULES = {"no-await-in-loop", "no-loop-func"}
RUFF_PERFORMANCE_PREFIXES = ("PERF",)

# ids of semgrep rules written without a category in their metadata
SECURITY_RULE_MARKERS = ("python.security", "javascript.security", "generic.secrets", "injection", "xss", "sqli")


def normalize(tool_outputs: dict, filename: str | None = None) -> dict:
    display_name = filename or "submitted_code"

    security        = []
    performance     = []
    maintainability = []
    buckets = {"security": security, "performance": performance, "maintainability": maintainability}

    for finding in tool_outputs.get("semgrep", []):
        normalized = _normalize_semgrep(finding, display_name)
        if normalized:
            buckets[_semgrep_category(finding, normalized["rule_id"])].append(normalized)

    for finding in tool_outputs.get("bandit", []):
        normalized = _normalize_bandit(finding, display_name)
        if normalized:
            security.append(normalized)

    for finding in tool_outputs.get("ruff", []):
        normalized = _normalize_ruff(finding, display_name)
        if normalized:
            is_perf = normalized["rule_id"].startswith(RUFF_PERFORMANCE_PREFIXES)
            (performance if is_perf else maintainability).append(normalized)

    for finding in tool_outputs.get("eslint", []):
        normalized = _normalize_eslint(finding, display_name)
        if normalized:
            is_perf = normalized["rule_id"] in ESLINT_PERFORMANCE_RULES
            (performance if is_perf else maintainability).append(normalized)

    return {
        "security_findings":        security,
        "performance_findings":     performance,
        "maintainability_findings": maintainability,
    }


def _semgrep_category(finding: dict, rule_id: str) -> str:
    declared = (finding.get("extra", {}).get("metadata") or {}).get("category")
    if declared in ("security", "performance", "maintainability"):
        return declared
    if any(marker in rule_id.lower() for marker in SECURITY_RULE_MARKERS):
        return "security"
    return "maintainability"


def _semgrep_rule_id(check_id: str | None) -> str:
    # semgrep prefixes local rules with their on-disk path (home.user.app.server.rules.<id>); keep only <id>
    return (check_id or "unknown").rsplit(".rules.", 1)[-1]


def _normalize_semgrep(finding: dict, filename: str) -> NormalizedFinding | None:
    try:
        return {
            "tool":     "semgrep",
            "rule_id":  _semgrep_rule_id(finding.get("check_id")),
            "message":  finding.get("extra", {}).get("message", ""),
            "file":     filename,
            "line":     finding.get("start", {}).get("line", 1),
            "severity": _normalize_severity(finding.get("extra", {}).get("severity", "INFO")),
        }
    except Exception as e:
        logger.warning(f"Failed to normalize semgrep finding: {e}")
        return None


def _normalize_bandit(finding: dict, filename: str) -> NormalizedFinding | None:
    try:
        return {
            "tool":     "bandit",
            "rule_id":  finding.get("test_id") or "unknown",
            "message":  finding.get("issue_text", ""),
            "file":     filename,
            "line":     finding.get("line_number", 1),
            "severity": _normalize_severity(finding.get("issue_severity", "LOW")),
        }
    except Exception as e:
        logger.warning(f"Failed to normalize bandit finding: {e}")
        return None


def _normalize_ruff(finding: dict, filename: str) -> NormalizedFinding | None:
    try:
        code = finding.get("code") or "unknown"
        return {
            "tool":     "ruff",
            "rule_id":  code,
            "message":  finding.get("message", ""),
            "file":     filename,
            "line":     finding.get("location", {}).get("row", 1),
            "severity": "high" if code == "invalid-syntax" else "low",
        }
    except Exception as e:
        logger.warning(f"Failed to normalize ruff finding: {e}")
        return None


def _normalize_eslint(finding: dict, filename: str) -> NormalizedFinding | None:
    try:
        # parse errors have ruleId == null and fatal == true
        rule_id = finding.get("ruleId") or ("syntax-error" if finding.get("fatal") else "unknown")
        return {
            "tool":     "eslint",
            "rule_id":  rule_id,
            "message":  finding.get("message", ""),
            "file":     filename,
            "line":     finding.get("line", 1),
            "severity": "high" if finding.get("fatal") else _normalize_severity(str(finding.get("severity", 1))),
        }
    except Exception as e:
        logger.warning(f"Failed to normalize eslint finding: {e}")
        return None


def _normalize_severity(raw: str) -> str:
    mapping = {
        "error":    "high",
        "warning":  "medium",
        "info":     "low",
        "high":     "high",
        "medium":   "medium",
        "low":      "low",
        "critical": "critical",
        "2":        "high",
        "1":        "medium",
    }
    return mapping.get(raw.lower(), "low")
