"""Matching predictions to labels, and the metrics derived from the matches. Pure functions, no I/O.

Matching rules
- A prediction matches a label only if file, category and class are identical and the
  lines are within LINE_TOLERANCE. Class identity is exact (see taxonomy.py); there is
  no substring or word-overlap matching.
- Matching is one-to-one, closest line first, so one label cannot absorb several predictions.
- A further prediction of an already-matched label is a *duplicate*: counted in the
  duplicate rate, not in precision.
- A label marked ``ambiguous`` is a judgement call. Matching it is neutral (neither TP
  nor FP) and missing it is not a FN.
- Files with no labels at all are *clean*. Any false positive there is a false alarm.
"""
import random
from dataclasses import dataclass, field

from taxonomy import OTHER, SEVERITIES

LINE_TOLERANCE = 3


@dataclass(frozen=True)
class Label:
    file: str
    line: int
    cls: str
    category: str
    severity: str
    ambiguous: bool = False


@dataclass(frozen=True)
class Pred:
    file: str
    line: int
    cls: str
    category: str
    severity: str
    issue_type: str = ""


@dataclass
class FileResult:
    file: str
    is_clean: bool
    tp: list = field(default_factory=list)          # [(Pred, Label)]
    fp: list = field(default_factory=list)          # [Pred]
    fn: list = field(default_factory=list)          # [Label]
    duplicates: list = field(default_factory=list)  # [Pred]
    ignored: list = field(default_factory=list)     # [Pred] matched an ambiguous label


def _compatible(p: Pred, g: Label, tol: int) -> bool:
    return p.cls != OTHER and p.cls == g.cls and p.category == g.category and abs(p.line - g.line) <= tol


def match_file(file: str, preds: list[Pred], labels: list[Label], tol: int = LINE_TOLERANCE) -> FileResult:
    result = FileResult(file=file, is_clean=not labels)
    firm = [g for g in labels if not g.ambiguous]
    soft = [g for g in labels if g.ambiguous]

    edges = sorted(
        (abs(p.line - g.line), pi, gi)
        for pi, p in enumerate(preds)
        for gi, g in enumerate(firm)
        if _compatible(p, g, tol)
    )
    used_preds, used_labels = set(), set()
    for _, pi, gi in edges:
        if pi in used_preds or gi in used_labels:
            continue
        used_preds.add(pi)
        used_labels.add(gi)
        result.tp.append((preds[pi], firm[gi]))

    matched_firm = [firm[gi] for gi in used_labels]
    for pi, p in enumerate(preds):
        if pi in used_preds:
            continue
        if any(_compatible(p, g, tol) for g in matched_firm):
            result.duplicates.append(p)
        elif any(_compatible(p, g, tol) for g in soft):
            result.ignored.append(p)
        else:
            result.fp.append(p)

    result.fn = [g for gi, g in enumerate(firm) if gi not in used_labels]
    return result


def _ratio(num: float, den: float):
    return num / den if den else None


def summarize(results: list[FileResult], category: str | None = None) -> dict:
    """Micro-averaged metrics over ``results``, optionally restricted to one category."""
    def keep(item):
        p = item[0] if isinstance(item, tuple) else item
        return category is None or p.category == category

    tp = [pair for r in results for pair in r.tp if keep(pair[1])]
    fp = [p for r in results for p in r.fp if keep(p)]
    fn = [g for r in results for g in r.fn if keep(g)]
    dup = [p for r in results for p in r.duplicates if keep(p)]
    ign = [p for r in results for p in r.ignored if keep(p)]

    precision = _ratio(len(tp), len(tp) + len(fp))
    recall = _ratio(len(tp), len(tp) + len(fn))
    if precision is None and recall is None:
        f1 = None
    elif not precision or not recall:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)

    def sev_gap(pair):
        p, g = pair
        return abs(SEVERITIES.index(p.severity) - SEVERITIES.index(g.severity)) if p.severity in SEVERITIES else 99

    clean = [r for r in results if r.is_clean]
    false_alarms = [r for r in clean if any(keep(p) for p in r.fp)]
    n_preds = len(tp) + len(fp) + len(dup) + len(ign)

    return {
        "files": len(results), "tp": len(tp), "fp": len(fp), "fn": len(fn),
        "duplicates": len(dup), "ignored": len(ign), "predictions": n_preds,
        "precision": precision, "recall": recall, "f1": f1,
        "severity_exact": _ratio(sum(sev_gap(x) == 0 for x in tp), len(tp)),
        "severity_within_one": _ratio(sum(sev_gap(x) <= 1 for x in tp), len(tp)),
        "duplicate_rate": _ratio(len(dup), n_preds),
        "clean_files": len(clean),
        "clean_false_alarm_rate": _ratio(len(false_alarms), len(clean)),
        "fp_per_clean_file": _ratio(sum(len([p for p in r.fp if keep(p)]) for r in clean), len(clean)),
    }


def bootstrap_ci(results: list[FileResult], category: str | None, metric: str,
                 n_boot: int = 2000, seed: int = 0, alpha: float = 0.05):
    """Percentile CI for ``metric`` obtained by resampling *files* (the unit that is actually independent)."""
    if not results:
        return None
    rng = random.Random(seed)
    values = []
    for _ in range(n_boot):
        sample = [results[rng.randrange(len(results))] for _ in results]
        value = summarize(sample, category)[metric]
        if value is not None:
            values.append(value)
    if len(values) < n_boot // 2:
        return None
    values.sort()
    lo = values[int(alpha / 2 * len(values))]
    hi = values[min(len(values) - 1, int((1 - alpha / 2) * len(values)))]
    return lo, hi
