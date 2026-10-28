import json
import re

import pytest

import build_dataset
from build_dataset import DatasetError, parse_source
from taxonomy import CATEGORY_OF


def test_committed_dataset_is_in_sync_with_dataset_src():
    outputs, ground_truth = build_dataset.build()
    assert build_dataset.stale_files(outputs, ground_truth) == [], "run `python build_dataset.py` and commit the result"


@pytest.fixture(scope="module")
def truth():
    return json.loads(build_dataset.GROUND_TRUTH_FILE.read_text())["files"]


def test_every_label_sits_on_a_real_line_of_code(truth):
    for entry in truth:
        lines = (build_dataset.SAMPLES_DIR / entry["file"]).read_text().split("\n")
        for label in entry["labels"]:
            assert 1 <= label["line"] <= len(lines), entry["file"]
            assert lines[label["line"] - 1].strip(), f"{entry['file']}:{label['line']} is blank"


def test_published_samples_contain_no_markers_and_keep_line_numbers(truth):
    for entry in truth:
        published = (build_dataset.SAMPLES_DIR / entry["file"]).read_text()
        assert "@label" not in published and "@note" not in published
        source = (build_dataset.EVAL_DIR / entry["origin"]).read_text()
        assert len(published.split("\n")) == len(source.split("\n"))


def test_published_names_do_not_leak_the_answer(truth):
    for entry in truth:
        assert re.fullmatch(r"(dev|test)/[dt]\d\d\.(py|js)", entry["file"]), entry["file"]


def test_category_is_consistent_with_class(truth):
    for entry in truth:
        for label in entry["labels"]:
            assert CATEGORY_OF[label["class"]] == label["category"]


def test_dataset_has_clean_files_and_both_languages_in_the_held_out_split(truth):
    test = [e for e in truth if e["split"] == "test"]
    assert sum(not e["labels"] for e in test) >= 8
    assert {e["language"] for e in test} == {"python", "javascript"}
    assert {l["category"] for e in test for l in e["labels"]} == {"security", "performance"}


def test_parse_source_strips_markers_and_keeps_lines(tmp_path):
    src = tmp_path / "a.py"
    src.write_text("import os\nos.system(x)  # @label command_injection critical -- why\n# @note hello\n")
    code, labels, notes = parse_source(src)
    assert code == "import os\nos.system(x)\n\n"
    assert labels == [{"line": 2, "class": "command_injection", "category": "security", "severity": "critical",
                       "cwe": "CWE-77", "ambiguous": False, "note": "why"}]
    assert notes == ["hello"]


def test_ambiguous_marker(tmp_path):
    src = tmp_path / "a.js"
    src.write_text("run(x) // @label? ssrf high\n")
    assert parse_source(src)[1][0]["ambiguous"] is True


@pytest.mark.parametrize("line,message", [
    ("x = 1  # @label not_a_class high", "unknown class"),
    ("x = 1  # @label xss urgent", "unknown severity"),
    ("x = 1  # @label xss", "expected"),
    ("# @label xss high", "blank line"),
])
def test_bad_markers_fail_loudly(tmp_path, line, message):
    src = tmp_path / "a.py"
    src.write_text(line + "\n")
    with pytest.raises(DatasetError, match=message):
        parse_source(src)
