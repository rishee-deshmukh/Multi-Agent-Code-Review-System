import pytest

from scoring import Label, Pred, bootstrap_ci, match_file, summarize


def label(line=10, cls="sql_injection", category="security", severity="critical", ambiguous=False, file="f.py"):
    return Label(file, line, cls, category, severity, ambiguous)


def pred(line=10, cls="sql_injection", category="security", severity="critical", file="f.py"):
    return Pred(file, line, cls, category, severity)


def test_exact_match_is_a_true_positive():
    r = match_file("f.py", [pred()], [label()])
    assert (len(r.tp), len(r.fp), len(r.fn)) == (1, 0, 0)


def test_wrong_class_is_both_a_false_positive_and_a_false_negative():
    # the old fuzzy matcher could credit this; the class must be identical
    r = match_file("f.py", [pred(cls="xss")], [label(cls="sql_injection")])
    assert (len(r.tp), len(r.fp), len(r.fn)) == (0, 1, 1)


def test_other_never_matches():
    r = match_file("f.py", [pred(cls="other")], [label(cls="other")])
    assert len(r.tp) == 0 and len(r.fp) == 1


def test_category_must_match():
    r = match_file("f.py", [pred(category="performance")], [label(category="security")])
    assert len(r.tp) == 0


@pytest.mark.parametrize("offset,hit", [(0, True), (3, True), (-3, True), (4, False), (-4, False)])
def test_line_tolerance(offset, hit):
    r = match_file("f.py", [pred(line=10 + offset)], [label(line=10)])
    assert bool(r.tp) is hit


def test_one_label_absorbs_one_prediction_the_rest_are_duplicates():
    r = match_file("f.py", [pred(line=10), pred(line=11), pred(line=9)], [label(line=10)])
    assert len(r.tp) == 1 and len(r.duplicates) == 2 and not r.fp


def test_closest_prediction_wins_when_labels_compete():
    labels = [label(line=10), label(line=14)]
    r = match_file("f.py", [pred(line=12), pred(line=14)], labels)
    matched = {(p.line, g.line) for p, g in r.tp}
    assert matched == {(14, 14), (12, 10)}


def test_an_ambiguous_label_is_neutral_both_ways():
    hit = match_file("f.py", [pred()], [label(ambiguous=True)])
    assert (len(hit.tp), len(hit.fp), len(hit.ignored)) == (0, 0, 1)
    miss = match_file("f.py", [], [label(ambiguous=True)])
    assert len(miss.fn) == 0


def test_unlabelled_file_makes_every_prediction_a_false_alarm():
    r = match_file("c.py", [pred(file="c.py")], [])
    assert r.is_clean and len(r.fp) == 1
    s = summarize([r])
    assert s["clean_false_alarm_rate"] == 1.0 and s["fp_per_clean_file"] == 1.0


def test_metrics():
    results = [
        match_file("a", [pred(file="a")], [label(file="a")]),                       # TP
        match_file("b", [pred(file="b", cls="xss")], [label(file="b")]),            # FP + FN
        match_file("c", [], [label(file="c")]),                                      # FN
    ]
    s = summarize(results)
    assert (s["tp"], s["fp"], s["fn"]) == (1, 1, 2)
    assert s["precision"] == 0.5 and s["recall"] == pytest.approx(1 / 3)
    assert s["f1"] == pytest.approx(0.4)


def test_no_predictions_is_undefined_precision_and_zero_f1():
    s = summarize([match_file("a", [], [label(file="a")])])
    assert s["precision"] is None and s["recall"] == 0.0 and s["f1"] == 0.0


def test_severity_accuracy():
    results = [match_file("a", [pred(file="a", severity="high")], [label(file="a", severity="critical")])]
    s = summarize(results)
    assert s["severity_exact"] == 0.0 and s["severity_within_one"] == 1.0


def test_category_filter():
    results = [match_file("a", [pred(file="a"), pred(file="a", cls="quadratic", category="performance", line=30)],
                          [label(file="a")])]
    assert summarize(results, "security")["tp"] == 1
    assert summarize(results, "performance")["fp"] == 1


def test_bootstrap_is_deterministic_and_brackets_the_estimate():
    results = [match_file(str(i), [pred(file=str(i))] if i % 3 else [], [label(file=str(i))]) for i in range(30)]
    first = bootstrap_ci(results, None, "recall")
    assert first == bootstrap_ci(results, None, "recall")
    assert first[0] <= summarize(results)["recall"] <= first[1]


def test_bootstrap_on_nothing():
    assert bootstrap_ci([], None, "recall") is None
