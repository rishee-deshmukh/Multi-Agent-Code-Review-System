"""Scores results/<system>.json against ground_truth.json and writes results/RESULTS.md.

    python compute_metrics.py
    python compute_metrics.py --splits test --systems tools_only multi_agent

Reading the tables
- Precision/recall/F1 are micro-averaged over labels, security and performance only.
  Brackets are 95% bootstrap intervals from resampling *files* (2000 resamples, seed 0).
  With a few dozen files these are wide; a difference between two systems is only
  meaningful if the intervals clearly do not overlap.
- "clean-file false alarms": fraction of label-free files where the system reported
  at least one issue. This is the number a user feels as noise.
- A file the system errored on is excluded from the metrics and counted under "failed";
  it is never silently treated as "no issues".
- dev is the public benchmark (probably in the model's training data, and the split the
  static rules were developed against); test is the held-out split written afterwards.
  Quote test.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))

from records import degraded  # noqa: E402
from scoring import Label, Pred, bootstrap_ci, match_file, summarize  # noqa: E402
from taxonomy import OTHER  # noqa: E402

GROUND_TRUTH_FILE = EVAL_DIR / "ground_truth.json"
RESULTS_DIR = EVAL_DIR / "results"
SYSTEM_ORDER = ["tools_only", "single_llm", "multi_agent_no_tools", "multi_agent"]
SCORED = ("security", "performance")


def load_labels() -> dict:
    files = json.loads(GROUND_TRUTH_FILE.read_text(encoding="utf-8"))["files"]
    return {f["file"]: f for f in files}


def score_system(system: str, truth: dict, split: str):
    """Returns (list[FileResult], failed file names, raw per-file records) for one system on one split."""
    path = RESULTS_DIR / f"{system}.json"
    if not path.exists():
        return None
    records = json.loads(path.read_text(encoding="utf-8")).get("files", {})

    results, failed, used = [], [], {}
    for name, entry in truth.items():
        if split != "all" and entry["split"] != split:
            continue
        record = records.get(name)
        if record is None:
            continue
        if degraded(record):
            failed.append(name)
            continue
        labels = [Label(name, l["line"], l["class"], l["category"], l["severity"], l["ambiguous"]) for l in entry["labels"]]
        preds = [Pred(name, p["line"], p["class"], p["category"], p["severity"], p["issue_type"])
                 for p in record["predictions"] if p["category"] in SCORED]
        results.append(match_file(name, preds, labels))
        used[name] = record
    return results, failed, used


def pct(v) -> str:
    return "n/a" if v is None else f"{v:.2f}"


MIN_FOR_CI = 10   # below this many items behind a ratio, a bootstrap interval is false precision


def with_ci(results, category, metric) -> str:
    s = summarize(results, category)
    value = s[metric]
    if value is None:
        return "n/a"
    denominator = {"precision": s["tp"] + s["fp"], "recall": s["tp"] + s["fn"],
                   "f1": min(s["tp"] + s["fp"], s["tp"] + s["fn"])}[metric]
    if denominator < MIN_FOR_CI:
        return f"{value:.2f}†"
    ci = bootstrap_ci(results, category, metric)
    return f"{value:.2f}" + (f" [{ci[0]:.2f}–{ci[1]:.2f}]" if ci else "")


def rate(num: int, den: int) -> str:
    return "n/a" if not den else f"{num / den:.2f} ({num}/{den})"


def table(rows: list[list[str]]) -> str:
    header, *body = rows
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def latency_cell(used: dict) -> str:
    live = [r["seconds"] for r in used.values() if r.get("llm_calls") is not None and r["cache_hits"] == 0]
    if not live:
        return "n/a (cache replay)" if any(r.get("cache_hits") for r in used.values()) else "n/a"
    return f"{sum(live) / len(live):.1f}s"


def calls_cell(used: dict) -> str:
    calls = [r["llm_calls"] for r in used.values() if r.get("llm_calls") is not None]
    return f"{sum(calls) / len(calls):.1f}" if calls else "n/a"


def split_report(split: str, truth: dict, systems: list[str]):
    scored = {s: score_system(s, truth, split) for s in systems}
    scored = {s: v for s, v in scored.items() if v and v[0]}
    if not scored:
        return f"### {split}\n\nNo results yet. Run `python run_eval.py --split {split}`.\n", {}

    n_labels = sum(len([l for l in e["labels"] if not l["ambiguous"]]) for e in truth.values() if split in ("all", e["split"]))
    n_clean = sum(not e["labels"] for e in truth.values() if split in ("all", e["split"]))
    out = [f"### {split} split — {n_labels} labels in {sum(1 for e in truth.values() if split in ('all', e['split']))} files "
           f"({n_clean} clean)\n"]

    rows = [["system", "precision", "recall", "F1", "clean-file false alarms", "FP / clean file",
             "duplicate rate", "severity exact / ±1", "failed", "avg latency", "LLM calls / file"]]
    for system, (results, failed, used) in scored.items():
        s = summarize(results)
        rows.append([
            f"**{system}**" if system == "multi_agent" else system,
            with_ci(results, None, "precision"), with_ci(results, None, "recall"), with_ci(results, None, "f1"),
            rate(round((s["clean_false_alarm_rate"] or 0) * s["clean_files"]), s["clean_files"]),
            pct(s["fp_per_clean_file"]), pct(s["duplicate_rate"]),
            f"{pct(s['severity_exact'])} / {pct(s['severity_within_one'])}",
            str(len(failed)), latency_cell(used), calls_cell(used),
        ])
    out += [table(rows), "", f"† fewer than {MIN_FOR_CI} items behind the ratio: no interval is shown because it would be false precision.", ""]

    for category in SCORED:
        rows = [["system", "TP", "FP", "FN", "precision", "recall", "F1"]]
        for system, (results, _, _) in scored.items():
            s = summarize(results, category)
            if not s["tp"] + s["fn"]:
                continue
            rows.append([system, str(s["tp"]), str(s["fp"]), str(s["fn"]),
                         with_ci(results, category, "precision"), with_ci(results, category, "recall"),
                         with_ci(results, category, "f1")])
        if len(rows) > 1:
            out += [f"**{category}**\n", table(rows), ""]

    if "multi_agent" in scored:
        results, _, _ = scored["multi_agent"]
        per_class = defaultdict(lambda: [0, 0])
        for r in results:
            for _, g in r.tp:
                per_class[g.cls][0] += 1
                per_class[g.cls][1] += 1
            for g in r.fn:
                per_class[g.cls][1] += 1
        rows = [["class (multi_agent)", "found", "of", "recall"]] + [
            [cls, str(h), str(t), pct(h / t)] for cls, (h, t) in sorted(per_class.items(), key=lambda kv: (kv[1][0] / kv[1][1], kv[0]))]
        out += ["<details><summary>Recall by vulnerability class (multi_agent)</summary>\n", table(rows), "\n</details>\n"]

    unmapped = Counter()
    for system, (_, _, used) in scored.items():
        for record in used.values():
            for p in record["predictions"]:
                if p["class"] == OTHER and system not in ("tools_only",):
                    unmapped[(system, p["category"], p["issue_type"])] += 1
    if unmapped:
        out.append("<details><summary>Predictions whose issue name matched no class (count as false positives; extend taxonomy.py if they are legitimate names)</summary>\n")
        out += [f"- `{s}` / {c}: {t} ×{n}" for (s, c, t), n in unmapped.most_common(25)]
        out.append("\n</details>\n")
    return "\n".join(out), scored


def error_analysis(scored: dict, system: str) -> str:
    if system not in scored:
        return ""
    results, _, _ = scored[system]
    lines = [f"# Error analysis — {system}\n",
             "Every false positive and false negative, for manual adjudication. A listed false positive that is in fact a "
             "real, unlabelled issue means the *label set* is incomplete — fix `dataset/src`, not the scorer.\n"]
    for r in results:
        if not (r.fp or r.fn):
            continue
        lines.append(f"## {r.file}{' (clean)' if r.is_clean else ''}")
        lines += [f"- **FP** line {p.line}: {p.issue_type} → `{p.cls}` ({p.severity})" for p in r.fp]
        lines += [f"- **FN** line {g.line}: `{g.cls}` ({g.severity})" for g in r.fn]
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--splits", nargs="+", default=["test", "dev"], choices=["test", "dev", "all"])
    parser.add_argument("--systems", nargs="+", default=SYSTEM_ORDER)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    truth = load_labels()
    sections = ["# Evaluation results\n",
                "Generated by `compute_metrics.py` from `results/*.json`. See that file's docstring for how to read the tables.\n"]
    last_scored = {}
    for split in args.splits:
        text, scored = split_report(split, truth, args.systems)
        sections.append(text)
        if split == "test" or not last_scored:
            last_scored = scored

    report = "\n".join(sections)
    print(report)
    if not args.no_write:
        RESULTS_DIR.mkdir(exist_ok=True)
        (RESULTS_DIR / "RESULTS.md").write_text(report, encoding="utf-8")
        errors = error_analysis(last_scored, "multi_agent") or error_analysis(last_scored, next(iter(last_scored), ""))
        if errors:
            (RESULTS_DIR / "errors.md").write_text(errors, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
