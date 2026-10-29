# Error analysis — multi_agent

Every false positive and false negative, for manual adjudication. A listed false positive that is in fact a real, unlabelled issue means the *label set* is incomplete — fix `dataset/src`, not the scorer.

## test/t01.js (clean)
- **FP** line 14: Database Query Optimization and Error Handling → `other` (high)
- **FP** line 12: Missing Rate Limiting → `other` (medium)

## test/t02.js (clean)
- **FP** line 11: Performance Bottleneck in Git Log Execution → `other` (high)
- **FP** line 26: Path Traversal → `path_traversal` (high)
- **FP** line 13: Command Injection → `command_injection` (medium)
- **FP** line 8: Missing Rate Limiting → `other` (medium)

## test/t03.js (clean)
- **FP** line 12: N+1 Query Pattern and SQL Injection → `io_in_loop` (critical)
- **FP** line 11: Missing Input Validation → `missing_validation` (high)

## test/t04.js (clean)
- **FP** line 5: Synchronous I/O and Unsafe Configuration Loading → `sync_blocking` (high)
- **FP** line 15: Open Redirect → `open_redirect` (medium)
- **FP** line 7: Missing Rate Limiting → `other` (medium)

## test/t05.js
- **FP** line 1: Potential Data Leakage / Missing Validation → `missing_validation` (medium)

## test/t06.js
- **FP** line 2: Inefficient O(n*m) complexity and lack of input validation → `other` (high)
- **FP** line 6: Input validation missing for totalRevenue → `missing_validation` (medium)
- **FP** line 6: Insecure Arithmetic / Type Confusion → `other` (low)
- **FN** line 2: `quadratic` (high)

## test/t07.js
- **FP** line 4: Inefficient RegExp instantiation in loop → `other` (high)
- **FP** line 4: ReDoS (Regular Expression Denial of Service) → `other` (medium)
- **FP** line 1: ReDoS (Regular Expression Denial of Service) → `other` (medium)
- **FN** line 4: `repeated_work` (medium)

## test/t08.js
- **FP** line 7: Sensitive Data Exposure → `other` (medium)
- **FP** line 5: Missing Rate Limiting → `other` (medium)

## test/t09.js
- **FP** line 5: Inefficient O(n*m*k) complexity → `other` (high)
- **FN** line 5: `quadratic` (high)

## test/t10.js
- **FP** line 8: Missing Input Validation → `missing_validation` (medium)

## test/t11.js
- **FP** line 5: Missing Rate Limiting → `other` (medium)

## test/t12.js
- **FP** line 10: Inefficient File I/O → `other` (medium)
- **FP** line 8: Missing Rate Limiting → `other` (medium)

## test/t13.js
- **FP** line 1: Missing Rate Limiting → `other` (medium)

## test/t14.js
- **FP** line 5: Information Disclosure → `other` (low)

## test/t15.js
- **FP** line 7: Missing Input Sanitization → `other` (medium)

## test/t16.js
- **FP** line 5: Synchronous Cryptographic Operation → `other` (high)
- **FP** line 9: Missing Error Handling → `other` (medium)

## test/t17.js
- **FP** line 3: Missing Security Headers → `other` (low)

## test/t18.js
- **FP** line 6: Memory Leak / Unbounded Cache → `other` (critical)
- **FP** line 3: Missing Input Validation → `missing_validation` (medium)

## test/t19.js
- **FP** line 8: Timing Attack Vulnerability and Buffer Mismatch → `other` (high)

## test/t20.py (clean)
- **FP** line 17: Inefficient LIKE query → `other` (high)
- **FP** line 18: SQL Injection (Potential) → `sql_injection` (high)
- **FP** line 16: Input Validation and Error Handling → `missing_validation` (medium)
- **FP** line 15: Configuration and Connection Management → `other` (medium)

## test/t21.py (clean)
- **FP** line 12: Command Injection and Process Management → `command_injection` (high)
- **FP** line 5: Path Traversal → `path_traversal` (medium)
- **FP** line 5: Process spawning overhead → `other` (medium)
- **FP** line 4: Missing Error Handling for Subprocess → `command_injection` (medium)

## test/t22.py (clean)
- **FP** line 14: File Serving Optimization and Security → `other` (medium)
- **FP** line 9: Missing Rate Limiting → `other` (medium)

## test/t23.py (clean)
- **FP** line 10: Path Traversal and Unbounded File Access → `path_traversal` (high)
- **FP** line 19: Insecure and Unbounded YAML Parsing → `other` (high)
- **FP** line 27: Missing Rate Limiting → `other` (medium)

## test/t24.py (clean)
- **FP** line 22: Inefficient and unsafe CSV generation → `other` (medium)
- **FP** line 23: CSV Injection → `other` (medium)
- **FP** line 6: Potential KeyError → `other` (medium)

## test/t25.py (clean)
- **FP** line 18: Unsafe and Blocking External Request Handling → `other` (critical)
- **FP** line 15: Missing Request Timeout/Validation → `other` (medium)

## test/t26.py (clean)
- **FP** line 11: Insecure Randomness → `insecure_random` (low)

## test/t27.py
- **FP** line 12: Potential KeyError / Type Error → `other` (medium)
- **FP** line 12: Missing Input Validation → `missing_validation` (low)

## test/t28.py
- **FP** line 4: Unbounded Input → `other` (medium)

## test/t29.py
- **FP** line 4: CSV Injection → `other` (medium)
- **FP** line 11: Inefficient list creation in loop → `other` (medium)
- **FP** line 1: CSV Injection via Header → `other` (medium)

## test/t30.py
- **FP** line 4: Inefficient Algorithm / KeyError Risk → `other` (critical)
- **FP** line 5: IndexError / Denial of Service → `other` (medium)
- **FN** line 4: `repeated_work` (medium)

## test/t31.py
- **FP** line 9: Redundant external API calls → `other` (high)
- **FP** line 10: Improper Input Validation → `missing_validation` (medium)
- **FP** line 8: Missing Rate Limiting → `other` (medium)

## test/t33.py
- **FP** line 16: Resource Management → `other` (medium)
- **FP** line 15: Missing Input Validation → `missing_validation` (medium)

## test/t34.py
- **FP** line 7: Missing Rate Limiting → `other` (medium)

## test/t35.py
- **FP** line 16: Blocking I/O in synchronous route → `sync_blocking` (medium)
- **FP** line 8: Missing Rate Limiting → `other` (medium)

## test/t36.py
- **FP** line 8: Missing Rate Limiting → `other` (medium)

## test/t37.py
- **FP** line 11: Unsafe and Blocking External Request → `other` (critical)
- **FP** line 7: Missing Rate Limiting → `other` (medium)
- **FN** line 12: `ssrf` (high)

## test/t38.py
- **FP** line 11: Missing Request Size Limit → `other` (high)

## test/t39.py
- **FP** line 12: Missing Cookie Integrity Protection → `other` (high)

## test/t40.py
- **FP** line 10: Connection Management → `other` (critical)
- **FP** line 14: SQL Injection Risk → `sql_injection` (medium)

## test/t41.py
- **FP** line 6: Insecure Password Hashing → `other` (critical)
- **FP** line 5: Unbounded Input Length → `other` (medium)
- **FN** line 6: `weak_crypto` (medium)

## test/t42.py
- **FP** line 13: Security/Performance: Unsafe and blocking logging → `other` (medium)
- **FP** line 12: Missing Rate Limiting → `other` (medium)

## test/t44.py
- **FP** line 11: Insecure and Inefficient Network Request → `other` (high)
- **FP** line 10: Missing Input Validation → `missing_validation` (medium)
- **FN** line 11: `tls_verification` (high)

## test/t45.py
- **FP** line 8: Missing Input Sanitization → `other` (high)

## test/t46.py
- **FP** line 12: Insecure and Non-Production Server Configuration → `other` (critical)
- **FP** line 3: Missing Security Headers → `other` (medium)
- **FN** line 12: `debug_enabled` (medium)

## test/t47.py
- **FP** line 13: Insecure Token Storage and Memory Management → `other` (high)
- **FP** line 10: Missing Rate Limiting → `other` (high)

## test/t48.py
- **FP** line 21: Path Traversal → `path_traversal` (high)

## test/t49.py
- **FP** line 13: Sensitive Data Exposure in Logs → `other` (medium)

## test/t50.js (clean)
- **FP** line 16: Command Injection and Resource Exhaustion → `command_injection` (critical)
- **FP** line 24: Unsafe File Uploads → `other` (high)
- **FP** line 12: Missing Rate Limiting → `other` (medium)

## test/t51.js
- **FP** line 6: Missing Rate Limiting → `other` (medium)

## test/t52.js
- **FP** line 10: Missing Error Handling → `other` (medium)

## test/t53.js
- **FP** line 2: Inefficient array accumulation → `other` (high)
- **FN** line 2: `quadratic` (high)

## test/t54.js
- **FP** line 10: Unsafe JSON Parsing and Error Handling → `other` (high)
- **FP** line 9: Inefficient string concatenation → `string_concat_loop` (medium)
- **FP** line 6: Missing Request Timeout → `other` (medium)

## test/t55.js
- **FP** line 7: Missing Authentication/Authorization → `other` (critical)
- **FP** line 13: Unrestricted File Upload → `other` (high)
- **FP** line 11: Blocking I/O / Lack of Stream Backpressure → `sync_blocking` (medium)

## test/t56.py
- **FP** line 5: Inefficient queue operation → `other` (high)
- **FP** line 10: Inefficient path construction → `other` (medium)
- **FP** line 10: Memory inefficiency in path storage → `other` (medium)
- **FN** line 5: `quadratic` (medium)

## test/t57.py (clean)
- **FP** line 26: N+1 Query / Unbounded Query → `io_in_loop` (high)
- **FP** line 10: Missing Authorization → `other` (high)
- **FP** line 13: Potential N+1 Query and Code Style → `io_in_loop` (medium)
- **FP** line 19: Inefficient Raw SQL Usage → `other` (medium)
- **FP** line 10: Missing Authorization → `other` (medium)
- **FP** line 23: Information Exposure → `other` (low)

## test/t58.py (clean)
- **FP** line 28: Zip Slip / Arbitrary File Write → `path_traversal` (critical)
- **FP** line 18: Blocking I/O and Memory Exhaustion → `sync_blocking` (high)
- **FP** line 14: Insecure File Upload Configuration → `other` (medium)
- **FP** line 11: Missing Rate Limiting → `other` (medium)

## test/t59.py
- **FP** line 4: Missing Authorization → `other` (high)
- **FP** line 7: Inefficient List Construction → `other` (low)

## test/t60.py
- **FP** line 9: Missing Input Validation → `missing_validation` (medium)

## test/t61.py
- **FP** line 12: Blocking I/O and Memory Exhaustion → `sync_blocking` (critical)
- **FP** line 15: Unrestricted File Upload → `other` (medium)
- **FP** line 12: Missing File Extension Validation → `other` (medium)

## test/t62.py
- **FP** line 6: I/O inside loop → `io_in_loop` (critical)
- **FP** line 6: Path Traversal / File Access → `path_traversal` (medium)
- **FP** line 8: KeyError Vulnerability → `other` (low)
- **FN** line 7: `repeated_work` (medium)

## test/t63.py
- **FP** line 17: Blocking I/O in synchronous loop → `io_in_loop` (critical)
- **FP** line 18: Improper Input Validation → `missing_validation` (medium)
- **FP** line 12: Missing Error Handling for Network Operations → `other` (medium)

## test/t64.py
- **FP** line 12: Connection pooling anti-pattern → `other` (high)
- **FP** line 12: Missing Error Handling for Network Requests → `other` (medium)

## test/t65.py
- **FP** line 14: Connection overhead per request → `other` (high)
- **FP** line 17: Insecure SMTP Configuration → `other` (medium)
- **FP** line 13: Missing Input Validation → `missing_validation` (medium)

## test/t66.py
- **FP** line 14: Improper Input Validation → `missing_validation` (medium)
- **FP** line 13: Missing Input Sanitization/Length Limit → `other` (medium)
- **FN** line 17: `code_injection` (critical)

## test/t67.py
- **FP** line 7: Resource Exhaustion (Zip Bomb) → `other` (high)
- **FP** line 8: Inefficient Archive Processing → `other` (medium)
