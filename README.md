<img width="1000" height="422" alt="image" src="https://github.com/user-attachments/assets/6fbad0df-a4e6-4481-a290-34dba1375a88" />

# Injection Survivability Under Memory Compaction (ISMC)

Research code and data for **"Injection Survivability Under Memory Compaction: Structural
Position, Not Adversarial Framing, Governs Survival"** (IEEE UEMCON 2026).

We measure whether an indirect prompt injection buried earlier in a conversation survives
an LLM-driven **context compaction** step (the mechanism production agent platforms use to
summarize long conversation histories and discard the original turns), and whether it
retains behavioral force afterwards. Across 994 trials over three open-weight summarizer
models, survival is governed by *where* the injection sits in the conversation and *what
tool it targets* — not by how aggressively it is worded.

- **B-ISR** (Behavioral Injection Survival Rate): overall **7.65%**; beginning-of-conversation
  placement survives at **15.62%** vs. **3.46%** at the end (χ²=45.07, p<0.0001).
- **Framing has no measurable effect**: four adversarial framings (plain, urgency,
  system-impersonation, goal-chaining) all land within 7.29–7.94% (χ²=0.104, p=0.991).
- **S-ISR** (Semantic Injection Survival Rate): cosine similarity between the payload and
  the post-compaction context, reported as a continuous score.

## Repository Map

| Path | Contents |
|---|---|
| `harness/` | Experiment harness: two compaction pipelines (Anthropic-pattern, Mem0-pattern), the task-model evaluator, S-ISR measurement, and the run orchestrator. **See [`harness/README.md`](harness/README.md) for the full harness API reference** (manifest format, output schema, module-by-module description). |
| `scripts/build_dataset.py` | Builds the full factorial manifest (80 InjecAgent payloads × 4 framings × 3 positions × 4 tool categories) and the conversation scaffolds under `data/conversations/`. |
| `scripts/robustness_analysis.py` | Logistic regression robustness check (position/framing/category/summarizer jointly), drop-one-summarizer test, position×framing interaction test, payload-outlier check, power/MDE calculation. |
| `data/` | `dataset_manifest_660.json` (the manifest actually used for the reported runs), `dataset_manifest.json` (full design), `conversations/`, `controls/`. |
| `results/` | Raw per-trial output (`M1_anthropic.jsonl`, `M2_anthropic.jsonl`, `M3_anthropic.jsonl`, `M1_mem0.jsonl`), `stats_summary.txt`, and generated `figures/`. |
| `generate_tables.py` | Produces `paper/tables_generated.tex` (Table I/II) from `results/*.jsonl`. |
| `generate_figures.py` | Produces the position/category/framing/S-ISR figures used in the paper from `results/*.jsonl`. |
| `quick_analysis.py` | Fast sanity-check dump of B-ISR/S-ISR by framing, position, pipeline, and tool category. |
| `health_check.py` | Run-time monitor: row counts, garbage-row rate, and running B-ISR per batch, meant to be run periodically during a live experiment. |
| `make_subset_manifest.py` | Builds a reduced manifest (`dataset_manifest_660.json`) from the full design when free-tier rate limits make the full run infeasible in one pass. |
| `run_all.py` | Sequential orchestrator: runs every (pipeline, summarizer) batch in `BATCHES` against the harness, with resume support and per-batch logging. |
| `run_pair.py` | Runs a single (pipeline, summarizer) pair directly, without the full batch loop. |
| `launch_parallel.ps1` / `check_progress.ps1` | Windows PowerShell helpers to launch batches as background jobs and poll their progress. |
| `paper/` | `main.tex` (submission draft) and `main2.tex` (McEnerney-style rewrite), `refs.bib`, `worked_example.tex`, `tables_generated.tex` (generated, do not hand-edit), `figures/`. |
| `review/` | Reviewer feedback notes used to triage revisions. |
| `ASSESSMENT.md`, `Scoping.md` | Project scoping and design-decision notes from earlier planning stages. |

**Not included in this repo:** `InjecAgent/` — the payload/benchmark dependency this
project builds on. It's an external repo, clone it separately (see Setup below) rather
than vendoring a copy here.

## Setup

```bash
git clone https://github.com/uiuc-kang-lab/InjecAgent.git
pip install -r harness/requirements.txt
```

Set API keys (Groq is required; OpenRouter only if you use a Qwen/OpenRouter-routed model):

```bash
export GROQ_API_KEY="gsk_..."
export OPENROUTER_API_KEY="sk-or-..."   # optional
```

On Windows PowerShell:
```powershell
$env:GROQ_API_KEY = "gsk_..."
$env:OPENROUTER_API_KEY = "sk-or-..."
```

The sentence-transformer used for S-ISR (`all-mpnet-base-v2`) downloads automatically on
first use (~420 MB).

Verify the harness end-to-end before a real run:
```bash
cd harness
python smoke_test.py
```
Exit code 0 means all checks passed. Without `GROQ_API_KEY` set, only the local S-ISR path
is exercised (no API calls).

## Running an Experiment

### 1. Build (or reuse) the manifest

The manifest used for the reported results is already in `data/dataset_manifest_660.json`.
To regenerate it (or the full design) from scratch:

```bash
python scripts/build_dataset.py
python make_subset_manifest.py   # only if you need the reduced 660-condition subset
```

### 2. Run a batch through the Anthropic-pattern harness

```bash
python harness/run_experiment.py \
  --pipeline anthropic \
  --summarizer-model llama-3.1-8b-instant \
  --manifest data/dataset_manifest_660.json \
  --output results/M1_anthropic.jsonl \
  --resume
```

`--resume` skips conditions already present in the output file, so a batch can be safely
killed and restarted.

### 3. Run a batch through the Mem0-pattern harness

```bash
python harness/run_experiment.py \
  --pipeline mem0 \
  --summarizer-model llama-3.1-8b-instant \
  --manifest data/dataset_manifest_660.json \
  --output results/M1_mem0.jsonl \
  --resume
```

### 4. Or run every configured batch sequentially

`run_all.py` drives the full model/pipeline matrix defined in its `BATCHES` list (edit
that list to add/remove models), writing one log file per batch under `logs/`:

```bash
python run_all.py
```

On Windows, `launch_parallel.ps1` launches the batches as background jobs instead of
running them sequentially; `check_progress.ps1` polls their row counts and exit status.

## What to Monitor During a Run

Long free-tier runs (rate-limited to ~15–24 requests/minute) take hours, so check on them
periodically rather than watching continuously:

- **`python health_check.py`** — the primary monitor. Prints per-batch row counts, the
  fraction of "garbage" rows (`behavioral_score` not in `{0, 1}`, usually a stuck API call
  or a parsing failure), and the running B-ISR/S-ISR. Flags `WARN` above 5% garbage rows
  and `FAIL` above 20% — a `FAIL` batch usually means the summarizer or evaluator is
  erroring out and should be stopped and inspected rather than left running.
- **`logs/<tag>.err`** — stderr for a given batch; check this first if `health_check.py`
  reports garbage rows or a batch stalls.
- **`logs/<tag>.log`** — full stdout for a batch (verbose; only needed when debugging a
  specific condition).
- **Rate limiting** — `harness/config.py` sets `SLEEP_BETWEEN_CALLS` and backoff
  parameters. If you see repeated 429s in a `.err` file, increase
  `SLEEP_BETWEEN_CALLS` before restarting rather than reducing `MAX_RETRIES`.

## Analysis

Once the batches you care about have finished (or partially finished — these scripts
tolerate incomplete files):

```bash
python quick_analysis.py            # fast B-ISR/S-ISR breakdown by framing/position/category
python generate_tables.py           # regenerates paper/tables_generated.tex
python generate_figures.py          # regenerates paper/figures/*
python scripts/robustness_analysis.py   # logistic regression + interaction + power checks
```

All four scripts read directly from `results/*.jsonl` and require no API keys — they only
need the result files to exist.

## Output Schema

Each line of `results/*.jsonl` is one trial:

| Field | Type | Description |
|---|---|---|
| `condition_id` | str | Unique condition identifier |
| `injection_id` | str | Injection payload identifier (from InjecAgent) |
| `framing` | str | F1 (plain) / F2 (urgency) / F3 (system-impersonation) / F4 (goal-chaining) |
| `position` | str | `beginning` / `middle` / `end` — where the payload sits in the conversation |
| `tool_category` | str | `email` / `file_system` / `web_search` / `calendar` |
| `pipeline` | str | `anthropic` or `mem0` — which compaction pattern was used |
| `summarizer_model` | str | Model used to perform the compaction |
| `compacted_context` | str | Full compacted/summarized context handed to the evaluator |
| `behavioral_score` | int | 1 = attacker goal executed, 0 = not executed, -1 = evaluation error |
| `sisr_cosine` | float | Cosine similarity between payload and compacted context |
| `evaluator_response` | str | Task model's response to the legitimate follow-up task |

See [`harness/README.md`](harness/README.md) for the complete field list and the manifest
input format.

## Notes on the Data

- The headline `n=994` pools 978 Anthropic-pattern trials with 16 Mem0-pattern trials
  (`M1_mem0.jsonl`); position/framing/tool-category are pipeline-agnostic structural
  variables, so both pipelines are combined for the position/framing/category breakdowns.
  Per-summarizer numbers in Table II use the Anthropic-pattern trials only.
- Per-model and per-category sample sizes are unequal — a consequence of free-tier rate
  limits truncating some batches before completion, not a sampling design choice. See the
  Limitations section of the paper for the full disclosure of which comparisons this
  affects.
