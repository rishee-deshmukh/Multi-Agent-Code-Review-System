"""Closed vocabulary of issue classes used by labels and by scoring.

The old evaluation compared free-text issue names with substring and word-overlap
heuristics, which can credit a prediction for the wrong vulnerability. Here every
label has exactly one class from CLASSES, and a prediction is mapped to a class by
an explicit, ordered keyword table. A prediction that cannot be mapped becomes
"other" and can never match a label; such names are reported so the table can be
extended in the open instead of silently loosening the match.
"""
import re

# class id -> (category, CWE numbers, default severity)
# Severity rubric (applied when labelling):
#   critical  remote code execution or direct data-store compromise (command/code injection, SQLi, deserialization)
#   high      exploitable disclosure or client compromise (XSS, path traversal, SSRF, LDAP injection, hardcoded or exposed secrets, disabled TLS checks)
#   medium    needs extra conditions or limited impact (open redirect, XML entity expansion, weak hashing, debug mode); performance that scales badly with input
#   low       hygiene (non-cryptographic RNG for tokens, small constant-factor waste)
CLASSES: dict[str, tuple[str, tuple[int, ...], str]] = {
    # security
    "sql_injection":        ("security", (89,),            "critical"),
    "command_injection":    ("security", (77, 78),         "critical"),
    "code_injection":       ("security", (94, 95, 96),     "critical"),
    "deserialization":      ("security", (502,),           "critical"),
    "path_traversal":       ("security", (22, 23, 36, 73), "high"),
    "xss":                  ("security", (79, 80),         "high"),
    "ssrf":                 ("security", (918,),           "high"),
    "ldap_injection":       ("security", (90,),            "high"),
    "hardcoded_credentials": ("security", (259, 321, 798), "high"),
    "tls_verification":     ("security", (295,),           "high"),
    "open_redirect":        ("security", (601,),           "medium"),
    "xml_parsing":          ("security", (611, 776, 827),  "medium"),
    "weak_crypto":          ("security", (326, 327, 328, 916), "medium"),
    "debug_enabled":        ("security", (215, 489),       "medium"),
    "insecure_random":      ("security", (330, 338),       "low"),
    "missing_validation":   ("security", (20,),            "medium"),
    # performance
    "io_in_loop":           ("performance", (), "high"),    # await / HTTP / DB query per iteration (N+1)
    "quadratic":            ("performance", (), "high"),    # nested loops, or a linear scan per iteration
    "repeated_work":        ("performance", (), "medium"),  # sort / regex compile / recompute inside a loop
    "sync_blocking":        ("performance", (), "medium"),  # synchronous I/O on a hot or request path
    "string_concat_loop":   ("performance", (), "low"),
}

CATEGORY_OF = {cls: spec[0] for cls, spec in CLASSES.items()}
SEVERITIES = ("low", "medium", "high", "critical")
OTHER = "other"

# Ordered: the first matching pattern wins, and only classes of the prediction's own category are tried.
_NAME_PATTERNS: list[tuple[str, str]] = [
    # security
    ("code_injection",        r"code injection|\beval\b|arbitrary code|remote code execution|\brce\b|template injection|\bssti\b|cwe-?(94|95)\b"),
    ("command_injection",     r"command|\bcmd\b|shell injection|os\.system|subprocess|cwe-?78\b"),
    ("sql_injection",         r"\bsql|sqli|cwe-?89\b"),
    ("ldap_injection",        r"ldap|cwe-?90\b"),
    ("deserialization",       r"deserializ|unpickl|pickle|yaml\.load|unsafe yaml|marshal|cwe-?502\b"),
    ("path_traversal",        r"path traversal|directory traversal|zip ?slip|tar ?slip|arbitrary file|file inclusion|\blfi\b|cwe-?(22|23)\b"),
    ("ssrf",                  r"ssrf|server.?side request|cwe-?918\b"),
    ("open_redirect",         r"redirect|cwe-?601\b"),
    ("xss",                   r"\bxss\b|cross.?site scripting|html injection|cwe-?79\b"),
    ("xml_parsing",           r"xxe|xml external|entity expansion|billion laughs|xml (bomb|parsing|parser|injection)|cwe-?(611|776)\b"),
    ("hardcoded_credentials", r"hard.?coded|embedded (key|password|credential)|credential|secret|api.?key|password in|cwe-?798\b"),
    ("tls_verification",      r"\btls\b|\bssl\b|certificate|verify ?= ?false|cwe-?295\b"),
    ("weak_crypto",           r"weak (hash|crypto|cipher|algorithm)|\bmd5\b|sha-?1\b|broken (hash|crypto)|insecure (hash|cipher)|cryptograph|cwe-?(327|328)\b"),
    ("insecure_random",       r"random|cwe-?330\b"),
    ("debug_enabled",         r"debug|cwe-?489\b"),
    ("missing_validation",    r"input validation|missing validation|unvalidated|improper validation|insufficient validation|cwe-?20\b"),
    # performance
    ("io_in_loop",            r"await|n\+1|\b(query|queries|requests?|calls?|fetch(es|ing)?|network|api|io|i/o|database|db|http)\b.{0,30}\b(in|inside|within|per|for each)\b.{0,15}\b(loop|iteration|item)|\b(sequential|serial)\b.{0,20}\b(requests?|calls?|fetch|await|io|network)\b"),
    ("quadratic",             r"nested loop|o\(n\^?2\)|o\(n²\)|quadratic|\b(scan|search|filter|lookup|includes|indexof|find|membership)\b.{0,30}\b(in|inside|within|per|for each)\b.{0,15}\b(loop|iteration)|repeated.{0,15}(scan|search|filter|lookup)|linear (search|scan|lookup)|brute.?force"),
    ("string_concat_loop",    r"string concat|concatenat|string building|\+= ?on string"),
    ("repeated_work",         r"(repeated|redundant|multiple|unnecessary|duplicate).{0,15}(sort|comput|calculat|regex|work|evaluation|parsing)|sort.{0,20}(loop|iteration)|regex compil|recomput|loop.?invariant"),
    ("sync_blocking",         r"sync(hronous)? (i/?o|file|fs|read|write)|blocking|readfilesync|writefilesync|event loop"),
]
_COMPILED = [(cls, re.compile(pat, re.IGNORECASE)) for cls, pat in _NAME_PATTERNS]


def classify(issue_type: str, category: str) -> str:
    """Map a free-text issue name to a class id, or OTHER. Only classes of ``category`` are considered."""
    for cls, pattern in _COMPILED:
        if CATEGORY_OF[cls] == category and pattern.search(issue_type or ""):
            return cls
    return OTHER


# --- mapping raw static-tool output to classes (for the tools-only baseline) ---

_CWE_TO_CLASS = {cwe: cls for cls, (_, cwes, _) in CLASSES.items() for cwe in cwes}

_TOOL_RULE_CLASS = {
    # local semgrep performance rules carry no CWE
    "py-string-concat-in-loop": "string_concat_loop",
    "py-query-in-loop": "io_in_loop",
    "js-array-scan-in-loop": "quadratic",
    "js-sort-in-loop": "repeated_work",
    "js-string-concat-in-loop": "string_concat_loop",
    "no-await-in-loop": "io_in_loop",
}


def cwe_to_class(cwe) -> str:
    """Accepts 89, "89", "CWE-89" or "CWE-89: Improper Neutralization..."; returns a class id or OTHER."""
    match = re.search(r"(\d+)", str(cwe))
    return _CWE_TO_CLASS.get(int(match.group(1)), OTHER) if match else OTHER


def tool_rule_class(rule_id: str, cwe=None) -> str:
    if rule_id in _TOOL_RULE_CLASS:
        return _TOOL_RULE_CLASS[rule_id]
    return cwe_to_class(cwe) if cwe is not None else OTHER
