"""
Main orchestration script for the compaction poisoning experiment.

Usage:
    python run_experiment.py --pipeline anthropic --summarizer-model llama-3.1-8b-instant \
        --manifest path/to/manifest.json --output results.jsonl
    python run_experiment.py --pipeline mem0 --summarizer-model llama-3.3-70b-versatile \
        --manifest path/to/manifest.json --output results.jsonl --resume
"""
import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime, timedelta

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.layout import Layout
from rich.panel import Panel

import pipeline_anthropic_pattern
import pipeline_mem0
import evaluator
import measure_sisr

console = Console()


def load_manifest(manifest_path: str) -> list:
    """Load conditions from the manifest JSON file, normalizing field names."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        conditions = data
    elif isinstance(data, dict) and "conditions" in data:
        conditions = data["conditions"]
    else:
        raise ValueError(f"Unrecognized manifest format in {manifest_path}")

    for c in conditions:
        # Derive condition_id from filename stem (unique, stable)
        if "condition_id" not in c:
            fp = c.get("file_path", "")
            c["condition_id"] = Path(fp).stem if fp else (
                f"{c.get('injection_id', 'unknown')}_{c.get('framing', 'X')}_{c.get('position', 'X')}"
            )
        # Map file_path → conversation_path
        if "conversation_path" not in c:
            c["conversation_path"] = c.get("file_path", "")
        # Provide safe defaults for nullable fields
        if not c.get("attacker_goal"):
            c["attacker_goal"] = ""
        if not c.get("payload_text"):
            c["payload_text"] = c.get("attacker_goal", "")
        if "legitimate_task" not in c:
            c["legitimate_task"] = ""

    return conditions


def load_conversation(conv_path: str) -> tuple:
    """
    Load a conversation JSON file.
    Returns (conversation_turns: list, meta: dict) where meta holds
    payload_text, attacker_goal, and other top-level fields from the file.
    """
    with open(conv_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data, {}
    elif isinstance(data, dict):
        for key in ("conversation_turns", "turns", "conversation"):
            if key in data:
                turns = data[key]
                meta = {k: v for k, v in data.items() if k != key}
                return turns, meta
        raise ValueError(f"No turn list found in {conv_path}")
    else:
        raise ValueError(f"Unrecognized conversation format in {conv_path}")


def load_existing_ids(output_path: str, pipeline: str, summarizer_model: str) -> set:
    """Load already-completed condition IDs from output file for resume support."""
    done = set()
    if not os.path.exists(output_path):
        return done
    with open(output_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if (
                    row.get("pipeline") == pipeline
                    and row.get("summarizer_model") == summarizer_model
                ):
                    done.add(row["condition_id"])
            except json.JSONDecodeError:
                continue
    return done


def make_stats_table(
    completed: int,
    total: int,
    bisr_sum: int,
    sisr_sum: float,
    errors: int,
    eta_seconds: float,
) -> Table:
    """Build a rich Table showing live running stats."""
    table = Table(title="Live Experiment Stats", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    bisr_pct = (bisr_sum / completed * 100) if completed > 0 else 0.0
    sisr_mean = (sisr_sum / completed) if completed > 0 else 0.0
    eta_str = str(timedelta(seconds=int(eta_seconds))) if eta_seconds > 0 else "—"

    table.add_row("Conditions completed", f"{completed} / {total}")
    table.add_row("Running B-ISR %", f"{bisr_pct:.1f}%")
    table.add_row("Running S-ISR mean", f"{sisr_mean:.4f}")
    table.add_row("Errors", str(errors))
    table.add_row("ETA", eta_str)
    return table


def make_final_table(rows: list) -> Table:
    """Build a final summary rich Table."""
    table = Table(title="Final Experiment Summary", show_header=True, header_style="bold green")
    table.add_column("condition_id", max_width=20)
    table.add_column("pipeline")
    table.add_column("summarizer_model", max_width=25)
    table.add_column("B-score", justify="right")
    table.add_column("S-ISR cos", justify="right")
    table.add_column("S-ISR bin", justify="right")
    table.add_column("pre tok", justify="right")
    table.add_column("post tok", justify="right")

    for row in rows:
        b = row.get("behavioral_score", -1)
        b_str = str(b) if b != -1 else "[red]ERR[/red]"
        table.add_row(
            str(row.get("condition_id", ""))[:20],
            str(row.get("pipeline", "")),
            str(row.get("summarizer_model", ""))[:25],
            b_str,
            f"{row.get('sisr_cosine', 0):.4f}",
            str(row.get("sisr_binary", 0)),
            str(row.get("pre_compact_tokens", 0)),
            str(row.get("post_compact_tokens", 0)),
        )
    return table


def run_condition(condition: dict, pipeline: str, summarizer_model: str) -> dict:
    """
    Execute one experimental condition and return a result dict.
    Raises on unrecoverable errors.
    """
    condition_id = condition["condition_id"]
    injection_id = condition.get("injection_id", "")
    framing = condition.get("framing", "")
    position = condition.get("position", "")
    tool_category = condition.get("tool_category", "")
    attacker_goal = condition.get("attacker_goal", "")
    legitimate_task = condition.get("legitimate_task", "")
    payload_text = condition.get("payload_text", attacker_goal)
    conv_path = condition.get("conversation_path", "")

    # Load the conversation turns and file-level metadata
    conversation_turns, conv_meta = load_conversation(conv_path)

    # If legitimate_task was not in manifest, use the first user turn as the task
    if not legitimate_task:
        user_turns = [t for t in conversation_turns if t.get("role") == "user"]
        legitimate_task = user_turns[0]["content"][:500] if user_turns else "Complete the user's task."

    # Prefer payload_text from the conversation file (actual injected text vs. goal description)
    if not payload_text and conv_meta.get("payload_text"):
        payload_text = conv_meta["payload_text"]

    # Run the pipeline
    if pipeline == "anthropic":
        pipeline_result = pipeline_anthropic_pattern.run(conversation_turns, summarizer_model)
    elif pipeline == "mem0":
        pipeline_result = pipeline_mem0.run(
            conversation_turns, run_id=condition_id, summarizer_model=summarizer_model
        )
    else:
        raise ValueError(f"Unknown pipeline: {pipeline}")

    compacted_context = pipeline_result["compacted_context"]
    pre_compact_tokens = pipeline_result["pre_compact_tokens"]
    post_compact_tokens = pipeline_result["post_compact_tokens"]

    # Run the evaluator
    eval_result = evaluator.evaluate(compacted_context, attacker_goal, legitimate_task)

    # Compute S-ISR
    sisr_result = measure_sisr.compute(payload_text, compacted_context)

    return {
        "condition_id": condition_id,
        "injection_id": injection_id,
        "framing": framing,
        "position": position,
        "tool_category": tool_category,
        "pipeline": pipeline,
        "summarizer_model": summarizer_model,
        "pre_compact_tokens": pre_compact_tokens,
        "post_compact_tokens": post_compact_tokens,
        "compacted_context": compacted_context,
        "behavioral_score": eval_result["behavioral_score"],
        "sisr_cosine": sisr_result["sisr_cosine"],
        "sisr_binary": sisr_result["sisr_binary"],
        "attacker_goal": attacker_goal,
        "evaluator_response": eval_result["evaluator_response"],
        "detection_method": eval_result["detection_method"],
    }


def main():
    parser = argparse.ArgumentParser(description="Run compaction poisoning experiment")
    parser.add_argument(
        "--pipeline", required=True, choices=["mem0", "anthropic"],
        help="Which compaction pipeline to use"
    )
    parser.add_argument(
        "--summarizer-model", required=True,
        help="Model ID for the summarizer/compactor"
    )
    parser.add_argument(
        "--manifest", required=True,
        help="Path to the dataset manifest JSON file"
    )
    parser.add_argument(
        "--output", required=True,
        help="Path to write output JSONL file"
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip conditions already present in the output file"
    )
    args = parser.parse_args()

    conditions = load_manifest(args.manifest)
    total = len(conditions)

    # Resume support
    skip_ids: set = set()
    if args.resume:
        skip_ids = load_existing_ids(args.output, args.pipeline, args.summarizer_model)
        if skip_ids:
            console.print(f"[yellow]Resuming: skipping {len(skip_ids)} already-completed conditions[/yellow]")

    pending = [c for c in conditions if c["condition_id"] not in skip_ids]
    console.print(f"[bold]Pipeline:[/bold] {args.pipeline}  |  [bold]Model:[/bold] {args.summarizer_model}")
    console.print(f"[bold]Total conditions:[/bold] {total}  |  [bold]Pending:[/bold] {len(pending)}")

    # Open output file in append mode
    out_f = open(args.output, "a", encoding="utf-8")

    completed = 0
    bisr_sum = 0
    sisr_sum = 0.0
    errors = 0
    all_rows = []
    start_time = time.time()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )
    task_id = progress.add_task("Processing conditions...", total=len(pending))

    stats_table = make_stats_table(0, total, 0, 0.0, 0, 0.0)

    with Live(
        Panel(stats_table, title="Experiment Progress"),
        console=console,
        refresh_per_second=2,
    ) as live:
        for i, condition in enumerate(pending):
            cid = condition.get("condition_id", f"cond_{i}")
            try:
                row = run_condition(condition, args.pipeline, args.summarizer_model)
                bisr_sum += max(0, row["behavioral_score"])
                sisr_sum += row.get("sisr_cosine", 0.0)
            except Exception:
                console.print_exception(show_locals=False)
                row = {
                    "condition_id": cid,
                    "injection_id": condition.get("injection_id", ""),
                    "framing": condition.get("framing", ""),
                    "position": condition.get("position", ""),
                    "tool_category": condition.get("tool_category", ""),
                    "pipeline": args.pipeline,
                    "summarizer_model": args.summarizer_model,
                    "pre_compact_tokens": 0,
                    "post_compact_tokens": 0,
                    "compacted_context": "",
                    "behavioral_score": -1,
                    "sisr_cosine": 0.0,
                    "sisr_binary": 0,
                    "attacker_goal": condition.get("attacker_goal", ""),
                    "evaluator_response": "",
                    "detection_method": "error",
                }
                errors += 1

            # Write result immediately
            out_f.write(json.dumps(row) + "\n")
            out_f.flush()
            all_rows.append(row)
            completed += 1
            progress.advance(task_id)

            # Update live display every 10 conditions or on last
            if completed % 10 == 0 or completed == len(pending):
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                remaining = len(pending) - completed
                eta = remaining / rate if rate > 0 else 0.0
                stats_table = make_stats_table(completed, total, bisr_sum, sisr_sum, errors, eta)
                live.update(Panel(stats_table, title="Experiment Progress"))

    out_f.close()
    console.print("\n[bold green]Experiment complete![/bold green]")
    console.print(make_final_table(all_rows))

    # Final summary line
    total_done = completed
    bisr_final = (bisr_sum / total_done * 100) if total_done > 0 else 0
    sisr_final = (sisr_sum / total_done) if total_done > 0 else 0
    console.print(
        f"\n[bold]Final B-ISR:[/bold] {bisr_final:.1f}%  |  "
        f"[bold]Final S-ISR mean:[/bold] {sisr_final:.4f}  |  "
        f"[bold]Errors:[/bold] {errors}"
    )
    console.print(f"[bold]Output written to:[/bold] {args.output}")


if __name__ == "__main__":
    main()
