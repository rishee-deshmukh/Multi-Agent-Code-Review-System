# Error analysis — tools_only

Every false positive and false negative, for manual adjudication. A listed false positive that is in fact a real, unlabelled issue means the *label set* is incomplete — fix `dataset/src`, not the scorer.

## test/t02.js (clean)
- **FP** line 26: js-taint-path-traversal → `path_traversal` (high)

## test/t04.js (clean)
- **FP** line 15: js-taint-open-redirect → `open_redirect` (medium)

## test/t06.js
- **FN** line 2: `quadratic` (high)

## test/t07.js
- **FN** line 4: `repeated_work` (medium)

## test/t08.js
- **FN** line 7: `sync_blocking` (medium)

## test/t09.js
- **FN** line 5: `quadratic` (high)

## test/t21.py (clean)
- **FP** line 1: blacklist → `command_injection` (low)
- **FP** line 5: start_process_with_partial_path → `command_injection` (low)
- **FP** line 5: subprocess_without_shell_equals_true → `command_injection` (low)
- **FP** line 12: start_process_with_partial_path → `command_injection` (low)
- **FP** line 12: subprocess_without_shell_equals_true → `command_injection` (low)

## test/t26.py (clean)
- **FP** line 11: py-insecure-random → `insecure_random` (low)
- **FP** line 11: blacklist → `insecure_random` (low)

## test/t27.py
- **FN** line 5: `quadratic` (high)

## test/t29.py
- **FN** line 4: `string_concat_loop` (low)

## test/t30.py
- **FN** line 4: `repeated_work` (medium)

## test/t31.py
- **FN** line 10: `sync_blocking` (medium)

## test/t32.py
- **FN** line 4: `quadratic` (high)

## test/t34.py
- **FP** line 1: blacklist → `command_injection` (low)

## test/t36.py
- **FN** line 17: `xss` (high)

## test/t37.py
- **FN** line 12: `ssrf` (high)

## test/t38.py
- **FP** line 8: yaml_load → `missing_validation` (medium)

## test/t39.py
- **FP** line 2: blacklist → `deserialization` (low)

## test/t40.py
- **FP** line 9: py-hardcoded-secret-kwarg → `hardcoded_credentials` (medium)

## test/t45.py
- **FP** line 11: blacklist → `command_injection` (medium)

## test/t46.py
- **FP** line 12: flask_debug_true → `code_injection` (high)

## test/t48.py
- **FP** line 2: blacklist → `command_injection` (low)
- **FP** line 22: hardcoded_tmp_directory → `other` (medium)
