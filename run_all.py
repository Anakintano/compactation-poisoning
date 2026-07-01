"""
Sequential orchestrator for all 10 experiment sub-batches.
Inherits GROQ_API_KEY and OPENROUTER_API_KEY from the parent environment.
Run directly: python run_all.py
"""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
HARNESS = BASE / "harness"
DATA = BASE / "data"
RESULTS = BASE / "results"
LOGS = BASE / "logs"

RESULTS.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

# llama-3.3-70b-versatile removed from Groq: free-tier cap is 100K tokens/day —
# not enough for even one batch of 1040 conditions (~1M tokens needed as summarizer).
# M2 is re-routed to OpenRouter alongside M5.
_NEEDS_OPENROUTER = {
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.3-70b-instruct",  # M2 via OpenRouter
}

# Revised model matrix — only models confirmed alive on Groq as of June 2026
# gemma2-9b-it, mixtral-8x7b-32768, deepseek, etc. all decommissioned
# OpenRouter free-tier models unavailable without paid credits
BATCHES = [
    ("anthropic", "llama-3.1-8b-instant",                         "M1_anthropic"),
    ("mem0",      "llama-3.1-8b-instant",                         "M1_mem0"),
    ("anthropic", "meta-llama/llama-4-scout-17b-16e-instruct",    "M2_anthropic"),
    ("mem0",      "meta-llama/llama-4-scout-17b-16e-instruct",    "M2_mem0"),
    ("anthropic", "allam-2-7b",                                   "M3_anthropic"),
    ("mem0",      "allam-2-7b",                                   "M3_mem0"),
    # M4/M5 slots reserved — add keys/models when available
]


def _log(msg: str, logfile):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    logfile.write(line + "\n")
    logfile.flush()


def _count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def main():
    log_path = LOGS / "run_log.txt"
    with open(log_path, "a", encoding="utf-8") as lf:
        _log(f"=== EXPERIMENT RUN STARTED (PID {os.getpid()}) ===", lf)
        _log(f"GROQ_API_KEY set: {bool(os.environ.get('GROQ_API_KEY', '').strip())}", lf)
        _log(f"OPENROUTER_API_KEY set: {bool(os.environ.get('OPENROUTER_API_KEY', '').strip())}", lf)

        total_start = datetime.now()

        has_openrouter = bool(os.environ.get("OPENROUTER_API_KEY", "").strip())
        if not has_openrouter:
            _log("OPENROUTER_API_KEY not set — M5 (Qwen) batches will be SKIPPED", lf)

        for i, (pipeline, model, tag) in enumerate(BATCHES, 1):
            batch_start = datetime.now()
            out_file = RESULTS / f"{tag}.jsonl"

            if model in _NEEDS_OPENROUTER and not has_openrouter:
                _log(f"[{i:02d}/{len(BATCHES)}] SKIP  {tag}  (OPENROUTER_API_KEY not set)", lf)
                continue

            # Count already-done rows (--resume skips them)
            prior_rows = _count_rows(out_file)
            _log(f"[{i:02d}/{len(BATCHES)}] START {tag}  model={model}  pipeline={pipeline}  prior_rows={prior_rows}", lf)

            cmd = [
                sys.executable,
                str(HARNESS / "run_experiment.py"),
                "--pipeline", pipeline,
                "--summarizer-model", model,
                "--manifest", str(DATA / "dataset_manifest_660.json"),
                "--output", str(out_file),
                "--resume",
            ]

            stdout_path = LOGS / f"{tag}.log"
            stderr_path = LOGS / f"{tag}.err"

            with (
                open(stdout_path, "a", encoding="utf-8") as so,
                open(stderr_path, "a", encoding="utf-8") as se,
            ):
                result = subprocess.run(
                    cmd,
                    cwd=str(HARNESS),
                    env=os.environ.copy(),
                    stdout=so,
                    stderr=se,
                )

            rows_after = _count_rows(out_file)
            new_rows = rows_after - prior_rows
            elapsed = (datetime.now() - batch_start).total_seconds() / 60

            _log(
                f"[{i:02d}/{len(BATCHES)}] DONE  {tag}  exit={result.returncode}  "
                f"rows={rows_after}/1040  new_this_run={new_rows}  elapsed={elapsed:.1f}min",
                lf,
            )

        total_elapsed = (datetime.now() - total_start).total_seconds() / 60
        _log(f"=== ALL BATCHES COMPLETE  total={total_elapsed:.1f}min ===", lf)


if __name__ == "__main__":
    main()
