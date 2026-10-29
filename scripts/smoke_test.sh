#!/usr/bin/env bash
# Checks a built image without any API key: every static analyser is present and runs, the UI is served,
# and the API refuses to report "no issues" when the LLM is unavailable.
#   scripts/smoke_test.sh [image]      (default: code-review)
set -euo pipefail
IMAGE="${1:-code-review}"
NAME="smoke-$$"
trap 'docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT

echo "== static analysers inside the image"
docker run --rm -i --entrypoint python "$IMAGE" - <<'PY'
from tool_runner import run_tools

py = run_tools("import os\nos.system(input())\nx = eval(input())\n", "python")
js = run_tools("var x = eval(prompt());\n", "javascript")
for label, report in (("python", py), ("javascript", js)):
    assert not report.errors, f"{label}: {report.errors}"
    print(label, {tool: len(findings) for tool, findings in report.outputs.items() if findings or tool in report.outputs})
assert py.outputs["semgrep"] and py.outputs["bandit"], "python tools found nothing in code with os.system(input())"
assert js.outputs["semgrep"] and js.outputs["eslint"], "javascript tools found nothing in code with eval(prompt())"
PY

echo "== server"
docker run -d --name "$NAME" -p 127.0.0.1:0:8000 -e RATE_LIMIT_PER_MINUTE=0 -e MAX_CODE_CHARS=2000 "$IMAGE" >/dev/null
PORT=$(docker port "$NAME" 8000/tcp | head -1 | sed 's/.*://')
BASE="http://127.0.0.1:$PORT"

for _ in $(seq 1 30); do curl -fs "$BASE/health" >/dev/null 2>&1 && break; sleep 1; done
curl -fs "$BASE/health" | grep -q '"ok"' || { echo "health check failed"; docker logs "$NAME"; exit 1; }
curl -fs "$BASE/" | grep -q 'id="root"' || { echo "UI is not served at /"; exit 1; }

code=$(curl -s -o /tmp/smoke-review.json -w '%{http_code}' -X POST "$BASE/review" \
    -H 'Content-Type: application/json' -d '{"code":"print(1)","filename":"a.py"}')
[ "$code" = 502 ] || { echo "expected 502 without an API key, got $code: $(cat /tmp/smoke-review.json)"; exit 1; }

code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/review" \
    -H 'Content-Type: application/json' -d "{\"code\":\"$(head -c 2500 /dev/zero | tr '\0' x)\"}")
[ "$code" = 413 ] || { echo "expected 413 for oversized code, got $code"; exit 1; }

echo "smoke test passed"
