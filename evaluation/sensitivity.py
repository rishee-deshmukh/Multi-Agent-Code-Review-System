"""How much of each system's false-positive count is findings the closed taxonomy cannot classify?

    python sensitivity.py [--split test]

The headline tables in results/RESULTS.md count every prediction whose issue name maps to no class
(for example "Missing Rate Limiting") as a false positive, because the dataset only labels specific,
verifiable bugs. That is a strict reading: some of those are advisory remarks, not mistakes. This script
reports the most generous alternative, in which every unclassifiable prediction is simply discarded,
applied identically to all systems. It is a diagnostic, not a replacement for the headline metric: it
cannot change which predictions match a label, only how many unmatched ones count against precision.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compute_metrics import SYSTEM_ORDER, load_labels, score_system  # noqa: E402
from taxonomy import OTHER  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="test", choices=["dev", "test"])
    args = parser.parse_args()
    truth = load_labels()

    print(f"{args.split} split; unclassifiable = predictions whose issue name maps to no class\n")
    print("| system | TP | FP | of which unclassifiable | precision (strict) | precision (unclassifiable dropped) | clean files alarmed (strict) | (unclassifiable dropped) |")
    print("|---|---|---|---|---|---|---|---|")
    for system in SYSTEM_ORDER:
        scored = score_system(system, truth, args.split)
        if scored is None:
            continue
        results, _, _ = scored
        tp = sum(len(r.tp) for r in results)
        fp = sum(len(r.fp) for r in results)
        other = sum(1 for r in results for p in r.fp if p.cls == OTHER)
        clean = [r for r in results if r.is_clean]
        alarmed = sum(1 for r in clean if r.fp)
        alarmed_known = sum(1 for r in clean if any(p.cls != OTHER for p in r.fp))
        strict = tp / (tp + fp) if tp + fp else float("nan")
        generous = tp / (tp + fp - other) if tp + fp - other else float("nan")
        print(f"| {system} | {tp} | {fp} | {other} | {strict:.2f} | {generous:.2f} | {alarmed}/{len(clean)} | {alarmed_known}/{len(clean)} |")


if __name__ == "__main__":
    main()
