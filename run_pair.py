"""
Run the anthropic + mem0 pair for a single summarizer model.
Usage: python run_pair.py --model MODEL_ID --tag-prefix TAG --groq-key KEY

This lets us run 3 model families in parallel, each with its own Groq key.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
HARNESS = BASE / "harness"
DATA = BASE / "data"
RESULTS = BASE / "results"
LOGS = BASE / "logs"

RESULTS.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)


def _log(msg, lf):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    lf.write(line + "\n")
    lf.flush()


def _count(path):
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as f:
        return sum(1 for ln in f if ln.strip())


def run_batch(pipeline, model, tag, env, lf):
    out_file = RESULTS / f"{tag}.jsonl"
    prior = _count(out_file)
    _log(f"START {tag}  model={model}  pipeline={pipeline}  prior_rows={prior}", lf)

    cmd = [
        sys.executable,
        str(HARNESS / "run_experiment.py"),
        "--pipeline", pipeline,
        "--summarizer-model", model,
        "--manifest", str(DATA / "dataset_manifest_660.json"),
        "--output", str(out_file),
        "--resume",
    ]

    with (
        open(LOGS / f"{tag}.log", "a", encoding="utf-8") as so,
        open(LOGS / f"{tag}.err", "a", encoding="utf-8") as se,
    ):
        result = subprocess.run(cmd, cwd=str(HARNESS), env=env, stdout=so, stderr=se)

    after = _count(out_file)
    _log(f"DONE  {tag}  exit={result.returncode}  rows={after}  new={after - prior}", lf)
    return result.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="Groq model ID")
    ap.add_argument("--tag-prefix", required=True, help="e.g. M1, M2, M3")
    ap.add_argument("--groq-key", required=True, help="Groq API key for this worker")
    args = ap.parse_args()

    env = os.environ.copy()
    env["GROQ_API_KEY"] = args.groq_key  # override key for this worker

    log_path = LOGS / f"pair_{args.tag_prefix}.log"
    with open(log_path, "a", encoding="utf-8") as lf:
        _log(f"=== PAIR WORKER STARTED  model={args.model}  prefix={args.tag_prefix}  PID={os.getpid()} ===", lf)

        t0 = datetime.now()
        for pipeline in ("anthropic", "mem0"):
            tag = f"{args.tag_prefix}_{pipeline}"
            run_batch(pipeline, args.model, tag, env, lf)

        elapsed = (datetime.now() - t0).total_seconds() / 60
        _log(f"=== PAIR COMPLETE  elapsed={elapsed:.1f}min ===", lf)


if __name__ == "__main__":
    main()
