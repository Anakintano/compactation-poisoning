"""
Merge multiple JSONL result files, deduplicate by (condition_id, summarizer_model, pipeline),
and write a single merged output file. Prints a rich table of counts by model and pipeline.

Usage:
    python merge_results.py --input-dir results/ --output merged.jsonl
"""
import argparse
import json
import os
from pathlib import Path
from collections import defaultdict

from rich.console import Console
from rich.table import Table

console = Console()


def load_jsonl(path: str) -> list:
    """Load all JSON lines from a .jsonl file."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                console.print(f"[yellow]Warning: skipping malformed line {lineno} in {path}: {e}[/yellow]")
    return rows


def main():
    parser = argparse.ArgumentParser(description="Merge JSONL result files")
    parser.add_argument("--input-dir", required=True, help="Directory containing .jsonl files")
    parser.add_argument("--output", required=True, help="Path for merged output JSONL file")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    jsonl_files = sorted(input_dir.glob("*.jsonl"))

    if not jsonl_files:
        console.print(f"[red]No .jsonl files found in {input_dir}[/red]")
        return

    console.print(f"Found {len(jsonl_files)} JSONL file(s) in {input_dir}")

    # Load all rows and deduplicate
    seen: dict = {}   # key -> row (last-write-wins for duplicates)
    total_loaded = 0
    total_dupes = 0

    for fpath in jsonl_files:
        rows = load_jsonl(str(fpath))
        console.print(f"  Loaded {len(rows):>5} rows from {fpath.name}")
        for row in rows:
            total_loaded += 1
            key = (
                row.get("condition_id", ""),
                row.get("summarizer_model", ""),
                row.get("pipeline", ""),
            )
            if key in seen:
                total_dupes += 1
            seen[key] = row

    merged_rows = list(seen.values())
    console.print(
        f"\n[bold]Total loaded:[/bold] {total_loaded}  |  "
        f"[bold]Duplicates removed:[/bold] {total_dupes}  |  "
        f"[bold]Unique rows:[/bold] {len(merged_rows)}"
    )

    # Write merged output
    with open(args.output, "w", encoding="utf-8") as f:
        for row in merged_rows:
            f.write(json.dumps(row) + "\n")

    console.print(f"[green]Merged output written to:[/green] {args.output}")

    # Build count table by model and pipeline
    counts: dict = defaultdict(lambda: defaultdict(int))
    error_counts: dict = defaultdict(lambda: defaultdict(int))

    for row in merged_rows:
        model = row.get("summarizer_model", "unknown")
        pipeline = row.get("pipeline", "unknown")
        counts[model][pipeline] += 1
        if row.get("behavioral_score", 0) == -1:
            error_counts[model][pipeline] += 1

    # Collect all pipeline names
    all_pipelines = sorted({p for m_dict in counts.values() for p in m_dict})

    table = Table(title="Merged Results: Count by Model and Pipeline", show_header=True, header_style="bold magenta")
    table.add_column("summarizer_model", style="bold")
    for pl in all_pipelines:
        table.add_column(f"{pl} (rows)", justify="right")
        table.add_column(f"{pl} (errors)", justify="right")

    for model in sorted(counts):
        row_vals = [model]
        for pl in all_pipelines:
            n = counts[model].get(pl, 0)
            e = error_counts[model].get(pl, 0)
            row_vals.append(str(n))
            row_vals.append(str(e) if e > 0 else "0")
        table.add_row(*row_vals)

    console.print()
    console.print(table)


if __name__ == "__main__":
    main()
