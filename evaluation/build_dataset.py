"""Builds samples/ and ground_truth.json from the annotated sources in dataset/src/.

Labels live next to the code they describe, as trailing comments:

    cursor.execute("..." % name)      # @label sql_injection critical
    do_thing(token)                   # @label? hardcoded_credentials high   (? = ambiguous, scored neutrally)
    # @note free text explaining a judgement call (anywhere in the file)

Markers are removed from the published samples without moving any line, so the line
number of a label is the line number in the file the system under test receives.
Published files get neutral names (d01.py, t07.js): descriptive names such as
``sql_injection_login.py`` or ``..._CWE-089_...`` would hand the answer to the model
through the FILENAME field of the prompt.

    python build_dataset.py            # regenerate
    python build_dataset.py --check    # exit 1 if the committed output is stale
"""
import argparse
import json
import re
import sys
from pathlib import Path

from taxonomy import CATEGORY_OF, CLASSES, SEVERITIES

EVAL_DIR = Path(__file__).resolve().parent
SRC_DIR = EVAL_DIR / "dataset" / "src"
SAMPLES_DIR = EVAL_DIR / "samples"
GROUND_TRUTH_FILE = EVAL_DIR / "ground_truth.json"

SPLITS = {"dev": "d", "test": "t"}
LANGUAGES = {".py": "python", ".js": "javascript"}
MARKER = re.compile(r"[ \t]*(?:#|//)[ \t]*@(?P<kind>label\?|label|note)(?=\s|$)(?P<body>.*)$")

# a representative CWE per class, recorded in ground_truth.json for readers
CWE_OF = {cls: f"CWE-{spec[1][0]}" for cls, spec in CLASSES.items() if spec[1]}


class DatasetError(ValueError):
    pass


def parse_source(path: Path) -> tuple[str, list[dict], list[str]]:
    """Return (code with markers removed, labels, notes). Line numbers are unchanged."""
    clean_lines, labels, notes = [], [], []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
        match = MARKER.search(line)
        if not match:
            clean_lines.append(line)
            continue

        clean_lines.append(line[:match.start()])
        body = match.group("body").strip()
        if match.group("kind") == "note":
            notes.append(body)
            continue

        parts = body.split("--", 1)
        fields = parts[0].split()
        if len(fields) != 2:
            raise DatasetError(f"{path}:{lineno}: expected '@label <class> <severity>', got {body!r}")
        cls, severity = fields
        if cls not in CLASSES:
            raise DatasetError(f"{path}:{lineno}: unknown class {cls!r}")
        if severity not in SEVERITIES:
            raise DatasetError(f"{path}:{lineno}: unknown severity {severity!r}")
        if not clean_lines[-1].strip():
            raise DatasetError(f"{path}:{lineno}: a label must sit on a line of code, not on a blank line")

        labels.append({
            "line": lineno,
            "class": cls,
            "category": CATEGORY_OF[cls],
            "severity": severity,
            "cwe": CWE_OF.get(cls),
            "ambiguous": match.group("kind") == "label?",
            "note": parts[1].strip() if len(parts) > 1 else "",
        })
    return "\n".join(clean_lines), labels, notes


def build() -> tuple[dict[Path, str], dict]:
    """Return ({output path: content}, ground_truth dict) without touching the disk."""
    outputs: dict[Path, str] = {}
    files = []

    for split, prefix in SPLITS.items():
        sources = sorted(p for p in (SRC_DIR / split).glob("*") if p.suffix in LANGUAGES)
        if not sources:
            raise DatasetError(f"no sources in {SRC_DIR / split}")

        for n, src in enumerate(sources, start=1):
            code, labels, notes = parse_source(src)
            name = f"{prefix}{n:02d}{src.suffix}"
            outputs[SAMPLES_DIR / split / name] = code
            files.append({
                "file": f"{split}/{name}",
                "split": split,
                "language": LANGUAGES[src.suffix],
                "origin": src.relative_to(EVAL_DIR).as_posix(),
                "labels": labels,
                "notes": notes,
            })

    return outputs, {"version": 2, "line_tolerance": 3, "files": files}


def render_ground_truth(ground_truth: dict) -> str:
    return json.dumps(ground_truth, indent=2) + "\n"


def stale_files(outputs: dict[Path, str], ground_truth: dict) -> list[Path]:
    stale = [p for p, content in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != content]
    if not GROUND_TRUTH_FILE.exists() or GROUND_TRUTH_FILE.read_text(encoding="utf-8") != render_ground_truth(ground_truth):
        stale.append(GROUND_TRUTH_FILE)
    on_disk = {p for p in SAMPLES_DIR.rglob("*") if p.is_file()}
    stale += sorted(on_disk - set(outputs))  # leftovers from an older layout
    return stale


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files differ from the committed ones")
    args = parser.parse_args()

    outputs, ground_truth = build()

    if args.check:
        stale = stale_files(outputs, ground_truth)
        for path in stale:
            print(f"stale: {path.relative_to(EVAL_DIR)}")
        return 1 if stale else 0

    for leftover in SAMPLES_DIR.rglob("*"):
        if leftover.is_file():
            leftover.unlink()
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    GROUND_TRUTH_FILE.write_text(render_ground_truth(ground_truth), encoding="utf-8")

    total = sum(len(f["labels"]) for f in ground_truth["files"])
    clean = sum(not f["labels"] for f in ground_truth["files"])
    print(f"{len(outputs)} samples, {total} labels, {clean} clean files -> {GROUND_TRUTH_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
