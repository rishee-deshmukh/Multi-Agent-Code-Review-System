"""Shared judgement about whether a saved per-file result may be scored."""


def degraded(record: dict) -> bool:
    """True if the run errored, or if any agent failed and the predictions are therefore incomplete.

    Older result files stored such runs as ordinary results with only a warning attached, so the
    warnings are checked as well as the error field.
    """
    if record.get("error"):
        return True
    return any(" agent failed" in w or w.startswith("synthesizer failed") for w in record.get("warnings", []))


def hit_daily_quota(record: dict) -> bool:
    text = " ".join([record.get("error") or "", *record.get("warnings", [])])
    return "daily API quota exhausted" in text
