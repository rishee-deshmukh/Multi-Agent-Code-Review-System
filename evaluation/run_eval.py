"""Runs one or more systems over the dataset and writes results/<system>.json.

Runs in-process (no server needed) through the same code path the API uses.

    python run_eval.py --system tools_only                      # no API key needed
    python run_eval.py --system multi_agent --split test        # needs GEMINI_API_KEY the first time
    python run_eval.py --system all --offline                   # replay committed cache, no key, no network
    python run_eval.py --system multi_agent --limit 3           # smoke test

Every Gemini response is cached in llm_cache/ (see llm_cache.py), so re-runs are free
and the committed cache reproduces the published numbers. Use --resume to continue an
interrupted run, and --min-interval to stay under a free-tier rate limit.
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))
sys.path.insert(0, str(EVAL_DIR.parent / "server"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(EVAL_DIR.parent / ".env")
load_dotenv(EVAL_DIR.parent / "server" / ".env")

import llm  # noqa: E402
from llm_cache import CachedLLM  # noqa: E402
from systems import SYSTEMS, run_system  # noqa: E402

SAMPLES_DIR = EVAL_DIR / "samples"
GROUND_TRUTH_FILE = EVAL_DIR / "ground_truth.json"
RESULTS_DIR = EVAL_DIR / "results"
CACHE_DIR = EVAL_DIR / "llm_cache"


def load_files(split: str, limit: int | None, only: list[str] | None) -> list[dict]:
    files = json.loads(GROUND_TRUTH_FILE.read_text(encoding="utf-8"))["files"]
    if split != "all":
        files = [f for f in files if f["split"] == split]
    if only:
        files = [f for f in files if f["file"] in only]
    return files[:limit] if limit else files


def evaluate_file(system: str, entry: dict, cache: CachedLLM, track_calls: bool) -> dict:
    code = (SAMPLES_DIR / entry["file"]).read_text(encoding="utf-8")
    name = Path(entry["file"]).name   # neutral name: the model must not see the vulnerability class
    calls_before, hits_before = cache.calls, cache.hits

    started = time.monotonic()
    try:
        run = run_system(system, code, name, entry["language"])
        predictions, warnings, error = run.predictions, run.warnings, run.error
    except Exception as e:  # a crash on one file must not lose the rest of the run
        predictions, warnings, error = [], [], f"{type(e).__name__}: {e}"
    seconds = time.monotonic() - started

    return {
        "predictions": predictions,
        "warnings": warnings,
        "error": error,
        "seconds": round(seconds, 2),
        # per-file call counts are only meaningful when files run one at a time
        "llm_calls": cache.calls - calls_before if track_calls else None,
        "cache_hits": cache.hits - hits_before if track_calls else None,
    }


def save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--system", default="all", help=f"one of {', '.join(SYSTEMS)}, or 'all'")
    parser.add_argument("--split", default="all", choices=["dev", "test", "all"])
    parser.add_argument("--limit", type=int, help="only the first N files (smoke test)")
    parser.add_argument("--file", action="append", help="only this sample, e.g. test/t07.js (repeatable)")
    parser.add_argument("--workers", type=int, default=1, help="parallel files; >1 makes per-file latency/call counts unreliable")
    parser.add_argument("--offline", action="store_true", help="never call the API; fail on a cache miss")
    parser.add_argument("--min-interval", type=float, default=0.0, help="seconds between live API calls")
    parser.add_argument("--resume", action="store_true", help="keep results already saved without an error")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--cache-dir", type=Path, default=CACHE_DIR)
    args = parser.parse_args()

    systems = SYSTEMS if args.system == "all" else (args.system,)
    for s in systems:
        if s not in SYSTEMS:
            parser.error(f"unknown system {s!r}")

    files = load_files(args.split, args.limit, args.file)
    if not files:
        parser.error("no files selected")

    cache = CachedLLM(args.cache_dir, offline=args.offline, min_interval=args.min_interval).install()
    exit_code = 0

    for system in systems:
        path = args.results_dir / f"{system}.json"
        payload = {"system": system, "model": llm.model_name(), "files": {}}
        if args.resume and path.exists():
            previous = json.loads(path.read_text(encoding="utf-8"))
            payload["files"] = {k: v for k, v in previous.get("files", {}).items() if not v.get("error")}
        elif path.exists() and (args.split != "all" or args.limit or args.file):
            # a partial run must not wipe the results of files it did not touch
            payload["files"] = json.loads(path.read_text(encoding="utf-8")).get("files", {})

        todo = [f for f in files if f["file"] not in payload["files"] or not args.resume]
        print(f"\n== {system}: {len(todo)} file(s)  (model {llm.model_name()}{', offline' if args.offline else ''})")

        def work(entry):
            return entry["file"], evaluate_file(system, entry, cache, track_calls=args.workers == 1)

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for i, (name, result) in enumerate(pool.map(work, todo), start=1):
                payload["files"][name] = result
                payload["created"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                save(path, payload)
                status = f"ERROR {result['error']}" if result["error"] else f"{len(result['predictions'])} predictions"
                print(f"  [{i}/{len(todo)}] {name:12s} {status}  ({result['seconds']}s)")
                exit_code |= bool(result["error"])

    print(f"\nlive API calls: {cache.calls - cache.hits}   cache hits: {cache.hits}")
    if exit_code:
        print("Some files failed; they are excluded from the metrics and reported as failures.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
