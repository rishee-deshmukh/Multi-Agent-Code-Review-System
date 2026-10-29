import pytest

from taxonomy import CLASSES, OTHER, classify, cwe_to_class, tool_rule_class


@pytest.mark.parametrize("name,category,expected", [
    ("SQL Injection", "security", "sql_injection"),
    ("SQL Injection (CWE-89)", "security", "sql_injection"),
    ("OS Command Injection", "security", "command_injection"),
    ("Command Injection via subprocess shell=True", "security", "command_injection"),
    ("Remote Code Execution via eval", "security", "code_injection"),
    ("Server-Side Template Injection (SSTI)", "security", "code_injection"),
    ("SSTI in render_template_string", "security", "code_injection"),
    ("Path Traversal", "security", "path_traversal"),
    ("Directory Traversal / Arbitrary File Read", "security", "path_traversal"),
    ("Reflected Cross-Site Scripting (XSS)", "security", "xss"),
    ("DOM-based XSS", "security", "xss"),
    ("LDAP Injection", "security", "ldap_injection"),
    ("Server-Side Request Forgery (SSRF)", "security", "ssrf"),
    ("Open Redirect", "security", "open_redirect"),
    ("Unsafe Deserialization of pickle data", "security", "deserialization"),
    ("Unsafe yaml.load", "security", "deserialization"),
    ("XML External Entity (XXE) Injection", "security", "xml_parsing"),
    ("Hardcoded Credentials", "security", "hardcoded_credentials"),
    ("Hard-coded API Key", "security", "hardcoded_credentials"),
    ("TLS Certificate Verification Disabled", "security", "tls_verification"),
    ("Weak Hashing Algorithm (MD5)", "security", "weak_crypto"),
    ("Insecure Random Number Generation", "security", "insecure_random"),
    ("Flask Debug Mode Enabled", "security", "debug_enabled"),
    ("Improper Input Validation", "security", "missing_validation"),
    ("Await Inside Loop", "performance", "io_in_loop"),
    ("N+1 Query Problem", "performance", "io_in_loop"),
    ("Sequential network requests in loop", "performance", "io_in_loop"),
    ("O(n²) Nested Loop", "performance", "quadratic"),
    ("Repeated Full-Array Scan in Loop", "performance", "quadratic"),
    ("Linear search inside loop", "performance", "quadratic"),
    ("Inefficient String Concatenation in Loop", "performance", "string_concat_loop"),
    ("Redundant Repeated Sorting", "performance", "repeated_work"),
    ("Regex compiled inside loop", "performance", "repeated_work"),
    ("Blocking synchronous file read", "performance", "sync_blocking"),
])
def test_realistic_names_map_to_the_intended_class(name, category, expected):
    assert classify(name, category) == expected


def test_unrecognised_names_are_other_not_a_guess():
    assert classify("Missing Docstring", "security") == OTHER
    assert classify("Use of assert detected", "security") == OTHER


def test_classes_are_restricted_to_the_predictions_category():
    # "Injection ... in loop" style names must not leak a security name into a performance class
    assert classify("SQL Injection", "performance") == OTHER


def test_xxe_is_no_longer_folded_into_input_validation():
    # the old synonym map rewrote XXE and YAML deserialization to "improper input validation"
    assert classify("XML External Entity Injection", "security") != classify("Improper Input Validation", "security")


@pytest.mark.parametrize("cwe,expected", [(89, "sql_injection"), ("CWE-78", "command_injection"), ("CWE-22: Path Traversal", "path_traversal"),
                                          ("79", "xss"), ("CWE-9999", OTHER), (None, OTHER), ("n/a", OTHER)])
def test_cwe_mapping(cwe, expected):
    assert cwe_to_class(cwe) == expected


def test_tool_rule_class_prefers_rule_id_over_cwe():
    assert tool_rule_class("js-array-scan-in-loop") == "quadratic"
    assert tool_rule_class("py-taint-sql-injection", "CWE-89") == "sql_injection"
    assert tool_rule_class("no-await-in-loop") == "io_in_loop"


def test_every_class_is_reachable_by_name():
    reachable = {classify(name, CLASSES[cls][0]) for cls, name in {
        "sql_injection": "sql injection", "command_injection": "command injection", "code_injection": "eval",
        "deserialization": "deserialization", "path_traversal": "path traversal", "xss": "xss", "ssrf": "ssrf",
        "ldap_injection": "ldap injection", "hardcoded_credentials": "hardcoded password", "tls_verification": "tls",
        "open_redirect": "open redirect", "xml_parsing": "xxe", "weak_crypto": "weak hash md5", "debug_enabled": "debug mode",
        "insecure_random": "insecure random", "missing_validation": "input validation", "io_in_loop": "await in loop",
        "quadratic": "nested loop", "repeated_work": "repeated sorting", "sync_blocking": "blocking io",
        "string_concat_loop": "string concatenation in loop"}.items()}
    assert reachable == set(CLASSES)
