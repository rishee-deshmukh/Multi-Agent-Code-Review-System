"""Steps shared by the HTTP API and the offline evaluation harness."""
import logging

from language_detector import detect_language
from models import Language
from output_normalizer import normalize
from tool_runner import run_tools

logger = logging.getLogger(__name__)


def analyze(code: str, filename: str | None = None, language: Language | None = None) -> tuple[Language, dict, list[str]]:
    """Detect the language and run the static tools.

    Returns (language, initial LangGraph state, warnings about tools that did not run).
    """
    language = language or detect_language(code, filename)
    report = run_tools(code, language, filename)
    normalized = normalize(report.outputs, filename)

    logger.info(
        "Language %s — findings: security %d, performance %d, maintainability %d",
        language,
        len(normalized["security_findings"]),
        len(normalized["performance_findings"]),
        len(normalized["maintainability_findings"]),
    )

    state = {
        "code":                     code,
        "language":                 language,
        "filename":                 filename,
        "tool_outputs":             report.outputs,
        "security_findings":        normalized["security_findings"],
        "performance_findings":     normalized["performance_findings"],
        "maintainability_findings": normalized["maintainability_findings"],
        "security_issues":          [],
        "performance_issues":       [],
        "maintainability_issues":   [],
        "failed_agents":            [],
        "warnings":                 [],
        "final_issues":             [],
        "summary":                  "",
        "fixed_code":               "",
    }
    return language, state, report.warnings
