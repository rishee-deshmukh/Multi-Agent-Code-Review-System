# Evaluation

Does the multi-agent pipeline find real problems better than the simpler things you
could do instead? This directory answers that with four systems, two datasets, a
strict scorer, and confidence intervals. Results are generated into
[`results/RESULTS.md`](results/RESULTS.md); error-by-error detail is in
[`results/errors.md`](results/errors.md).

## What is compared

| system | what it is | what the comparison isolates |
|---|---|---|
| `tools_only` | Semgrep + Bandit + Ruff + ESLint, no LLM | the floor: what static analysis gives you for free |
| `single_llm` | one Gemini call, one generic prompt, no tools | the cheap alternative to this whole project |
| `multi_agent_no_tools` | full graph, static findings withheld | value of the agent structure |
| `multi_agent` | full system: tools ground the agents | value of grounding in static analysis |

`tools_only` vs `multi_agent` is the value of the LLMs; `single_llm` vs
`multi_agent_no_tools` is the value of splitting the work across agents;
`multi_agent_no_tools` vs `multi_agent` is the value of grounding. Only **security
and performance** are scored; maintainability has no objective ground truth.

## Datasets

| split | files | provenance | how to use it |
|---|---|---|---|
| `dev` | 30 | 20 Python snippets from the public [SecurityEval](https://huggingface.co/datasets/s2e-lab/SecurityEval) benchmark + 10 small JS files that shipped with the project | look at failures, debug, tune |
| `test` | 49 | written for this project after the static rules were frozen; 38 vulnerable, 11 clean | **quote these numbers.** Do not tune against them |

The test split deliberately includes *clean* files and hard negatives (parameterized
SQL, `execFile` with an argument list, `yaml.safe_load`, `random.choice` for a UI
tip, `Promise.all` instead of `await` in a loop) so precision means something, plus
files with several issues so recall is measured within a file.

### Labels live in the source

`dataset/src/{dev,test}/` holds annotated code. A marker on the vulnerable line
declares the label; `build_dataset.py` strips the markers (without moving any line)
and writes `samples/` and `ground_truth.json`:

```python
rows = conn.execute(sql).fetchall()   # @label sql_injection critical -- optional justification
conn = connect(user="", passwd="")    # @label? hardcoded_credentials high   (? = ambiguous: matching it is neutral)
# @note free text about a judgement call
```

A file with no `@label` is clean. Published files get neutral names (`d07.py`,
`t31.py`): the previous version of this evaluation sent names like
`018_CWE-089_codeql_1_py.py` to the model as `FILENAME:`, which tells it the answer.

To add a sample: put it in `dataset/src/test/`, add markers, run
`python build_dataset.py`, commit the generated files. A test fails if you forget.

**Severity rubric.** critical = code execution or direct data-store compromise
(command/code injection, SQLi, deserialization); high = exploitable disclosure or client
compromise (XSS, path traversal, SSRF, LDAP injection, hardcoded secrets, disabled TLS
checks); medium = needs extra conditions (open redirect, XML entity expansion, weak hash,
debug mode) or performance that scales badly; low = hygiene. Severity is the weakest
signal in the set; read it as "roughly right", not as a measurement.

## Scoring

Defined in [`scoring.py`](scoring.py), with tests.

- A prediction matches a label only if **file, category and class are identical** and the
  lines are within ±3. Classes are a closed vocabulary ([`taxonomy.py`](taxonomy.py));
  a prediction's free-text name is mapped to a class by an explicit keyword table. A name
  that maps to nothing becomes `other` and can never match; those names are listed in the
  report so the table can be extended openly. (The old scorer used substring and
  two-word-overlap matching and rewrote "XXE" and "YAML deserialization" to "improper
  input validation", which could credit the wrong vulnerability.)
- Matching is one-to-one, closest line first. Extra predictions of an already-matched
  label are *duplicates*: reported as a duplicate rate, not counted against precision.
- A system that errors on a file (API down, bad key) is **excluded and counted as
  failed**, never scored as "found nothing".
- Intervals are 95% bootstrap percentile intervals, resampling files, 2000 resamples,
  seed 0. Ratios resting on fewer than 10 items are shown without an interval (`†`).

## Reproduce

```bash
pip install -r ../requirements-dev.txt   # plus: npm i -g eslint
python build_dataset.py --check          # generated files match dataset/src
pytest                                   # scorer, taxonomy, dataset, systems and cache tests (offline)

python run_eval.py --system tools_only   # no API key needed
python run_eval.py --system all --offline   # replay the committed llm_cache/, no key, no network
python compute_metrics.py                # -> results/RESULTS.md, results/errors.md
```

First live run (needs `GEMINI_API_KEY`): `python run_eval.py --system all --min-interval 4`.
Every response is cached in `llm_cache/` keyed by (model, prompt, input), so re-runs are
free and identical; **commit that directory** and anyone can regenerate the published
numbers without a key. Changing a prompt, the model, or a sample invalidates just the
affected entries. `--resume` continues an interrupted run. Run with `--workers 1`
(the default) if you want per-file latency; cached replays report no latency.

## Threats to validity — read before quoting a number

1. **One labeler.** There is no second annotator and no inter-annotator agreement. The
   `test` files and labels were written with AI assistance by the same hands that wrote
   the static rules, so the rules and the labels share blind spots. A `tools_only`
   recall that looks high is partly a property of that, not proof that Semgrep rules
   generalize.
2. **Dev is contaminated.** SecurityEval is public and almost certainly in the training
   data of the model being evaluated, and the static rules were written knowing its
   CWE classes. Use it for debugging, not for claims.
3. **Small n.** 49 held-out files. The intervals show how little that supports; two
   systems whose intervals overlap are not shown to differ.
4. **Synthetic code.** The test files are short, single-purpose, and clean of real-world
   noise. Real repositories will score lower; this does not measure that.
5. **Unlabelled real issues count as false positives.** `results/errors.md` lists every
   false positive for manual adjudication; one that is a genuine issue means the *label
   set* is incomplete, and the fix is in `dataset/src`, followed by re-scoring all
   systems.
6. **The class table can mis-credit.** An LLM that names a bug in an unexpected way scores
   a miss. Check the "matched no class" list in the report before concluding a system is
   worse.
7. **One run per system.** Temperature is 0, but Gemini is not guaranteed
   deterministic; the cache pins the published run, it does not prove stability.
8. **Do not tune on `test`.** If you change prompts or rules after looking at `test`
   results, that split is spent: say so and write a fresh held-out set.
