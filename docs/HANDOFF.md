# Handoff: making the Multi-Agent Code Review System portfolio-ready

Written for another engineer or AI assistant continuing this work with local access to the repo.
Read it top to bottom once; sections 7 and 8 are the parts you will act on.

- Branch with all work so far: `claude/festive-knuth-rvz4h5` (forked from `main` at `1ca0f6f`, "Initial project import").
- This file is session documentation. Delete it, or do not merge it, once it is no longer useful.

## 1. The goal, and the working relationship

The repo owner wants this project to be **portfolio-ready**: something a recruiter or interviewer can run,
inspect, and believe. The owner asked for **blunt, evidence-based advice, with no flattery**. The standing
instruction was to challenge weak reasoning, name what is being avoided, and rank work by what actually
moves the outcome. Keep doing that. In particular:

- A portfolio project is judged on *evidence that it works*, not on feature count. The architecture
  (3 parallel LLM specialists + synthesizer over LangGraph, grounded in static analysis) is a common pattern.
  What can distinguish this repo is an evaluation that holds up under questioning.
- Do not add features (more languages, auth, UI polish) before the evaluation is credible and the project
  can be run by a stranger in minutes.
- Be ready to publish a **negative or null result** (for example "the agents add little over Semgrep plus one
  prompt"). That is more credible than an inflated claim, and the harness exists to produce either.
- The code originated in a friend's repository. The git history is one import commit. The owner should be
  able to say precisely what they built; do not obscure authorship.

## 2. What the project is

Automated code review for Python and JavaScript. `POST /review` (JSON) and `POST /stream` (SSE):

```
code -> language_detector -> tool_runner (Semgrep / Bandit / Ruff / ESLint) -> output_normalizer
     -> LangGraph fan-out: security | performance | maintainability agents (Gemini, parallel)
     -> fan-in: synthesizer (merge, rank, cross-domain notes, fixed_code)
     -> ReviewResponse
```

FastAPI backend in `server/`, React + Vite + TypeScript + Tailwind frontend in `client/`, evaluation in
`evaluation/`. The runtime LLM is `gemini-3.1-flash-lite` (override with env `GEMINI_MODEL`).

## 3. Status snapshot

| Step | Scope | State |
|---|---|---|
| 1 | Correctness bugs and silent failures | **Done**, pushed, tested |
| 2 | Evaluation rebuild (dataset, scorer, baselines, harness) | **Done**, pushed, tested |
| 2b | Run the LLM systems and publish numbers | **Pending**: blocked by the free-tier daily API quota, see section 7 |
| 3 | Packaging: Docker, hosting, CI, rate limiting, CORS | **Done except**: no `LICENSE` (owner's choice), nothing deployed to a host yet, CI workflow not yet run on GitHub. Image build and `scripts/smoke_test.sh` verified locally |
| 4 | README that leads with results and a demo | **Not started** (the README is partly stale, see section 9) |
| 5 | Optional features | Deliberately deferred |

Commits on the branch, oldest first:

| hash | summary |
|---|---|
| `f79db9d` | Fix silent failures and wrong results in the review pipeline |
| `740bb7f` | Rebuild the evaluation: verifiable labels, strict scoring, baselines |
| `2fa4e82` | Add 18 harder held-out test files |
| `d1c04f5` | Wait out API rate limits instead of retrying inside the blocked window |
| `9a46c33` | Never score a run in which an agent failed; stop cleanly at the daily quota |

Test counts at the last commit: **52 server tests, 97 evaluation tests**, all passing offline (the LLM is faked).

## 4. Step 1: bugs found and fixed (all with regression tests)

| # | Bug | Where | Fix |
|---|---|---|---|
| 1 | Language never passed to Semgrep: JS was scanned with the Python ruleset | `server/tool_runner.py` | Language-specific local rules |
| 2 | Semgrep fetched rules from the registry on every request; an unreachable registry silently disabled it | `tool_runner.py` | Rules ship in `server/rules/{python,javascript}.yml`; registry packs are opt-in via env `SEMGREP_EXTRA_CONFIGS` |
| 3 | ESLint invoked with `--no-eslintrc` (removed in ESLint 9), so it failed on every call, silently | `tool_runner.py` | Flat config written next to the code; works on ESLint 9 and 10 |
| 4 | Every tool/agent failure returned HTTP 200 with zero issues, indistinguishable from clean code | `main.py`, `agents/base.py`, `tool_runner.py` | `ToolReport.errors`; agents report `failed_agents`/`warnings`; `ReviewResponse.warnings`; `/review` returns **502** if all specialists fail; `/stream` emits an `error` event |
| 5 | Synthesizer dropped every issue the LLM did not place in a merged group | `agents/synthesizer_agent.py` | Unclaimed indices become single-issue groups; an index is honoured in one group only |
| 6 | Unparseable synthesizer output bypassed the retry loop | synthesizer, `llm.py` | One `generate_json` with retry for all agents |
| 7 | `normalize()` crashed (HTTP 500) on any JS syntax error (`ruleId` is null) | `output_normalizer.py` | None-safe |
| 8 | `prefer-const`/`no-var` classed as performance; Python performance had no static tool | `output_normalizer.py`, `tool_runner.py` | Ruff `PERF` rules feed the performance agent |
| 9 | `/stream` blocked the event loop on subprocesses and handled only the first node of each graph chunk | `main.py` | `asyncio.to_thread`; iterate all chunk keys |
| 10 | Three copy-pasted specialist agents | `agents/*` | One implementation in `agents/base.py` |
| 11 | Truncated model output could be "repaired" into a half-finished `fixed_code` | `llm.py` | Truncated JSON is rejected and retried |

New shared modules: `server/llm.py` (all Gemini I/O: retry, JSON extraction, `temperature=0`, JSON mime
type), `server/pipeline.py` (`analyze()`, used by the API and by the evaluation so both run identical code),
`server/agents/base.py`.

Rate limits (`d1c04f5`): a 429 sleeps for the delay the API requests (+1 s, capped at 90 s) and does not consume
one of the 3 attempts. A per-day quota raises `DailyQuotaExhausted` (a subclass of `LLMUnrecoverableError`) immediately.

## 5. Step 2: the evaluation, and why it was rebuilt

The original evaluation could not support any claim:

- Labels were generated from the CWE in each *filename* plus a regex guess at the line, but described as hand-labeled. Some were wrong.
- Filenames like `018_CWE-089_codeql_1_py.py` were sent to the LLM as `FILENAME:`, leaking the answer.
- One label per file and no clean files, so precision and false-alarm rate were unmeasurable.
- Fuzzy matching (substring, 2-word overlap) plus a synonym map that folded XXE and YAML deserialization into "input validation".
- No baselines, so "multi-agent" was an assumption. The only data was a public benchmark (probably in training data).

**Design now** (full protocol and threats to validity: `evaluation/README.md`):

- **Labels live in the source.** `evaluation/dataset/src/{dev,test}/` holds annotated code. A trailing comment
  `# @label <class> <severity>` (or `//` in JS; `@label?` = ambiguous, scored neutrally; `# @note ...` free text) marks the
  vulnerable line. `build_dataset.py` strips markers without moving any line and writes `samples/` and
  `ground_truth.json`. Published files get neutral names (`d07.py`, `t31.js`). **Never edit `samples/` or
  `ground_truth.json` by hand.** Edit `dataset/src/` and run `python build_dataset.py`; a test fails if you forget.
- **Closed vocabulary** of 21 classes in `taxonomy.py` (16 security, 5 performance). A prediction matches a label only on
  identical file, category and class, within +/-3 lines, one to one. Unmappable names become `other` and never match.
- **Splits.** `dev` = 30 files (20 public SecurityEval Python snippets + 10 JS files that shipped with the project),
  relabeled by hand, probably contaminated. `test` = 67 held-out files (53 vulnerable incl. multi-issue files, 14 clean/hard-negative),
  written for this project after the static rules were frozen. Totals: 97 files, 88 labels, 15 clean files. **Quote `test` numbers only.**
- **Four systems** (`systems.py`): `tools_only`, `single_llm`, `multi_agent_no_tools`, `multi_agent`. They isolate the value
  of the LLMs, of the agent structure, and of grounding.
- **Scoring** (`scoring.py`): micro P/R/F1; duplicates reported separately (not counted against precision); ambiguous
  labels neutral; clean-file false-alarm rate; severity exact and within one level; 95% bootstrap CIs resampling *files*
  (2000 resamples, seed 0); ratios resting on fewer than 10 items are marked `†` with no interval.
- **Failed files are excluded and counted as failed, never scored as "found nothing"** (`records.degraded`). A file where any agent
  failed is treated the same way, including old result files saved before this rule existed.
- **LLM response cache** (`llm_cache.py`, directory `evaluation/llm_cache/`, keyed by model + prompt + input). Re-runs are free
  and reproducible. The intent is to **commit the cache** so anyone can regenerate the published numbers with `--offline` and no key.

Static rules: 20 Python and 18 JS Semgrep rules (6 taint-mode rules each for the injection-style classes, with `focus-metavariable` sinks; the rest are pattern rules, including a few performance rules). They
were written from general CWE patterns but with knowledge of the dev set's CWE classes. Do not tune them against `test`.

## 6. Results so far

Only `tools_only` has been run (needs no API key). On the 67-file `test` split:

- precision 0.68 [0.53-0.84], recall 0.68 [0.55-0.81], F1 0.68 [0.56-0.78]
- 4 of 14 clean files produced a false alarm
- performance recall is poor (the tools find few of the labelled performance problems)

Recall on the first 49 test files was 0.73; it fell to 0.68 on the harder second batch, which says the first batch was easier
for the rules. **No LLM system has been scored on the final dataset.** A partial earlier run exists on the owner's machine
(see section 7); do not rely on it.

## 7. Immediate next actions (this is where work resumes)

The owner ran the LLM systems on their machine with a Gemini **free-tier** key. Constraints discovered:

- 15 requests/minute and **500 requests/day** per model. A full pass is roughly 700 calls, so it spans two days.
- The earlier run was on an older checkout (79 files, not 97) and ended at the daily quota partway through `multi_agent`.
  Some files there had failed agents and were saved as normal results; the current code now treats those as failed.

To finish (run on the owner's machine, with `GEMINI_API_KEY` exported, Python 3.10+, `pip install -r requirements-dev.txt`, `npm i -g eslint`):

```bash
git pull
cd evaluation
python run_eval.py --system all --min-interval 5 --resume    # stops cleanly (exit 2) at the daily quota; re-run next day
python compute_metrics.py                                      # writes results/RESULTS.md and results/errors.md
```

Do not trust the headline table until you have checked, in this order:

1. `failed` column: should be 0 for every system. Anything else means missing data, not zero findings.
2. The "matched no class" list in `results/RESULTS.md`. If a system names real bugs in ways `taxonomy.py` does not recognise, its score is
   understated. Extending the keyword table in the open is legitimate **only if it is done for all systems and noted**; do it before quoting numbers.
3. `results/errors.md`: every false positive. A false positive that is a genuine unlabelled issue means the **label set** is incomplete.
   Fix it in `dataset/src/`, rebuild, and re-score all systems. Do not special-case the scorer.
4. Only then read precision/recall. Compare intervals, not point estimates. With 53 vulnerable files, overlapping intervals mean "not shown to differ".

Then commit `evaluation/llm_cache/` and `evaluation/results/` (see section 10 about not committing secrets; the cache holds only prompts and model text).

If the free quota proves too slow, enabling billing on the Google AI project costs very little for ~900 calls, but it is not required.

## 8. Remaining plan

### Step 3: packaging (not started)

Acceptance: a stranger can clone, run one command, and get a working app; CI is green; a public demo cannot drain the API key.

- **Dockerfile** for the backend with Python, Semgrep/Bandit/Ruff and Node + ESLint (>= 9). Bake nothing secret in. Provide `docker-compose.yml` for backend + frontend.
- **Hosting.** `vercel.json` is **broken and should be removed or replaced**: Semgrep + Bandit + Ruff + Node cannot run in a Vercel Python function, and the `client/$1` route looks wrong.
  The owner chose "Docker + a free container host" (Render, Fly.io or Hugging Face Spaces); frontend can stay on static hosting. Note the client calls **relative** URLs (`/stream`, `/review`; Vite proxies to :8000 in dev), so production needs a same-origin reverse proxy or a configurable API base URL.
- **Rate limiting and input caps.** None exist. A public deploy lets strangers spend the Gemini quota. Add per-IP rate limits, a maximum code size, and a global daily budget guard.
- **CORS** is hard-coded to `http://localhost:5173`; make it an env var.
- `.env.example`, `LICENSE`, pinned/locked dependencies (currently unpinned `requirements.txt`; `ruff --config "lint.mccabe.max-complexity = 10"` needs a recent Ruff), a root `Makefile` or scripts (`make test`, `make eval`).
- **GitHub Actions CI:** server tests, evaluation tests, `python evaluation/build_dataset.py --check`, client `tsc -b && vite build`. The integration tests need the real binaries (`pytest -m integration`); install them in CI.
- A smoke test of the container with the LLM faked, so CI needs no secret.

### Step 4: README (not started)

Lead with: a 15-second demo GIF, the results table (with baselines and intervals), an architecture diagram, one-command run, and an honest
**Limitations** section (synthetic held-out set, single labeler, TypeScript unsupported, free-tier model, maintainability unscored). Link
`evaluation/README.md`. Remove anything the README claims that the code does not do (see section 9).

### Step 5: only after the above

Additional languages, auth, saved reviews, UI polish, a GitHub-PR integration. Each is optional; none helps if the evaluation is weak.

## 9. Known stale or unverified things

- **Root `README.md` is a spec written for AI assistants and is partly wrong now.** It still describes Semgrep run with `--config=p/python` (now local rules), ESLint with `--no-eslintrc`,
  `cache_control` prompt caching (an Anthropic feature; this uses Gemini), "Sonnet" in the synthesizer section, the old 3-agent file layout, the `/review` response without `warnings`, and the stream events
  without `tools_done.warnings` / `synthesis_done.warnings` / `error`. Only its "Evaluation" section and the evaluation part of its file tree were updated.
- **Specialist prompts** (`server/agents/prompts.py`) still say the performance agent receives only "ESLint performance rules" although Ruff `PERF` findings now feed it. This was left
  unchanged on purpose: any prompt edit invalidates the LLM cache and, once `test` results have been seen, counts as tuning. If prompts are changed, do it before the final evaluation run, say so in the write-up, and re-run everything.
- **`gemini-3.1-flash-lite`** is confirmed to exist for the owner's key (the API error names it), but quota is the free tier's.
- TypeScript (`.ts`/`.tsx`) is routed to the JavaScript path, but the ESLint config parses plain JS only, so TS files will produce parse errors.
- The synthesizer returns `fixed_code` in the same call as the merge; very large inputs can hit the output-token limit (truncated output is now retried, not repaired).
- Maintainability is generated but **not scored** (no objective ground truth).
- Semgrep `--validate` requires network access to the registry; validate rules by scanning instead.

## 10. Guardrails: please do not

1. **Tune anything against `test`** (rules, prompts, taxonomy keywords, scorer) after seeing LLM results on it. If that is unavoidable, state it and write a fresh held-out set.
2. **Edit generated files by hand** (`evaluation/samples/`, `evaluation/ground_truth.json`, `evaluation/results/*.md`). Regenerate.
3. **Weaken the failure-visibility behaviour** (warnings, 502, `degraded`). A failure must never look like "no issues".
4. **Commit secrets.** `GEMINI_API_KEY` belongs in the shell or an ignored `.env`. Beware of realistic-looking fake keys in test data: GitHub push protection can block the push (the sample secrets here are deliberately not in known formats).
5. **Score partial runs**, or silently drop failed files from the denominators.
6. **Run `--system all` repeatedly to retry.** Use `--resume`.
7. Add features before sections 7 and 8 (steps 3 and 4) are done.

## 11. How to verify everything

```bash
python3 -m venv .venv && source .venv/bin/activate        # Python 3.10+ required (uses `X | None`)
pip install -r requirements-dev.txt && npm install -g eslint   # ESLint >= 9

(cd server && python -m pytest -q)                          # 52 tests; add -m integration to run only real-binary tests
(cd evaluation && python -m pytest -q)                      # 97 tests
(cd evaluation && python build_dataset.py --check)          # generated files match dataset/src
(cd client && npm ci && npx tsc -b && npx vite build)

cd server && uvicorn main:app --reload                      # API on :8000; client: cd client && npm run dev (:5173)
```

## 12. Merging with local changes

The owner has been editing locally while this branch advanced. Before changing anything:

```bash
git fetch origin && git status
git log --oneline origin/claude/festive-knuth-rvz4h5 -8
```

Likely conflict areas: `server/tool_runner.py`, `server/main.py`, `server/agents/*` (rewritten), `evaluation/*` (rewritten), root `README.md`. Prefer merging the branch
in over rebasing shared history, resolve in favour of the failure-visibility behaviour, and re-run section 11 after merging. Commits on this branch end with a
`Co-Authored-By` trailer and a `Claude-Session` URL; keep that convention or drop it consistently.

## 13. Environment gotchas already hit

- The cloud sandbox used for most of the work blocked `semgrep.dev` (a reason the rules had to be local) and had no Gemini key; environment changes reach only *new* sessions.
- Python < 3.10 fails on type-annotation syntax; the macOS system Python is often 3.9.
- A missing dependency shows up as `ModuleNotFoundError` at the first import (for example `dotenv`); run the install in section 11 first.
- `ThreadPoolExecutor.map` keeps running queued work after an early return; the harness now submits cancellable futures with a shared stop flag.
