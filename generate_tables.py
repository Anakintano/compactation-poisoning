"""
Generate LaTeX Table I (full B-ISR breakdown) and Table II (per-summarizer
B-ISR) for the ISMC paper, using the same loading/CI logic as
generate_figures.py so the numbers in the paper match the figures exactly.
Outputs: paper/tables_generated.tex (both tables, ready to \\input{} or copy
into main.tex).
"""
import json
import numpy as np
from pathlib import Path

RESULTS = Path("E:/compactation-poisoning/results")
OUT = Path("E:/compactation-poisoning/paper/tables_generated.tex")

rows = []
for name in ["M1_anthropic", "M2_anthropic", "M3_anthropic", "M1_mem0"]:
    f = RESULTS / f"{name}.jsonl"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("behavioral_score") in (0, 1):
                    rows.append(r)

inj = [r for r in rows if r.get("framing") and r.get("position") and r.get("tool_category")]
# Table I/II match generate_figures.py / stats_summary.txt exactly: all pipelines
# pooled (n=994), since position/framing/tool-category are pipeline-agnostic
# structural variables and Mem0 contributes only 16/994 rows either way.
anthropic_inj = inj


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = (z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return max(0, centre - margin), min(1, centre + margin)


def cell(subset):
    n = len(subset)
    k = sum(1 for r in subset if r["behavioral_score"] == 1)
    p = (k / n * 100) if n else 0.0
    lo, hi = wilson_ci(k, n)
    return f"{p:.2f}", f"[{lo*100:.2f}, {hi*100:.2f}]", n, k


lines = []

# ── Table I ──────────────────────────────────────────────────────────────
lines.append(r"\begin{table}[t]")
lines.append(r"\centering")
lines.append(r"\caption{Behavioral Injection Survival Rate (B-ISR), overall and by experimental factor, with 95\% Wilson confidence intervals ($n=994$: 978 trials from the Anthropic-pattern pipeline pooled with 16 from the Mem0-pattern pipeline; see Section~III). Per-model sample sizes are unequal due to free-tier rate limits (Table~\ref{tab:bymodel}), so the pooled rate is an estimate over an unbalanced, partially censored design.}")
lines.append(r"\label{tab:bisr}")
lines.append(r"\begin{tabular}{lrrc}")
lines.append(r"\toprule")
lines.append(r"\textbf{Condition} & \textbf{B-ISR (\%)} & \textbf{95\% CI} & \textbf{$n$} \\")
lines.append(r"\midrule")

p, ci, n, k = cell(anthropic_inj)
lines.append(rf"Overall & {p} & {ci} & {n} \\")
lines.append(r"\midrule")
lines.append(r"\multicolumn{4}{l}{\textit{By position} ($\chi^2$=45.07, $df$=2, $p<0.0001$)} \\")
for pos, label in [("beginning", "Beginning"), ("middle", "Middle"), ("end", "End")]:
    sub = [r for r in anthropic_inj if r["position"] == pos]
    p, ci, n, k = cell(sub)
    lines.append(rf"\quad {label} & {p} & {ci} & {n} \\")
lines.append(r"\midrule")
lines.append(r"\multicolumn{4}{l}{\textit{By framing} ($\chi^2$=0.104, $df$=3, $p=0.991$, n.s.)} \\")
for fr in ["F1", "F2", "F3", "F4"]:
    sub = [r for r in anthropic_inj if r["framing"] == fr]
    p, ci, n, k = cell(sub)
    lines.append(rf"\quad {fr} & {p} & {ci} & {n} \\")
lines.append(r"\midrule")
lines.append(r"\multicolumn{4}{l}{\textit{By tool category} ($\chi^2$=47.08, $df$=3, $p<0.0001$)} \\")
cat_order = sorted(set(r["tool_category"] for r in anthropic_inj),
                    key=lambda c: -sum(1 for r in anthropic_inj if r["tool_category"] == c and r["behavioral_score"] == 1)
                    / max(1, sum(1 for r in anthropic_inj if r["tool_category"] == c)))
for cat in cat_order:
    sub = [r for r in anthropic_inj if r["tool_category"] == cat]
    p, ci, n, k = cell(sub)
    label = cat.replace("_", " ").title()
    lines.append(rf"\quad {label} & {p} & {ci} & {n} \\")
lines.append(r"\bottomrule")
lines.append(r"\end{tabular}")
lines.append(r"\end{table}")
lines.append("")

# ── Table II ─────────────────────────────────────────────────────────────
model_order = [
    ("llama-3.1-8b-instant", "Llama-3.1 8B"),
    ("meta-llama/llama-4-scout-17b-16e-instruct", "Llama-4 Scout 17B"),
    ("qwen/qwen3-32b", "Qwen3 32B"),
]
lines.append(r"\begin{table}[t]")
lines.append(r"\centering")
lines.append(r"\caption{B-ISR by summarizer model. Sample sizes are unequal across models due to free-tier rate-limit constraints; see Section~V.}")
lines.append(r"\label{tab:bymodel}")
lines.append(r"\begin{tabular}{lrrc}")
lines.append(r"\toprule")
lines.append(r"\textbf{Summarizer} & \textbf{B-ISR (\%)} & \textbf{95\% CI} & \textbf{$n$} \\")
lines.append(r"\midrule")
for model_id, label in model_order:
    sub = [r for r in anthropic_inj if r["summarizer_model"] == model_id]
    p, ci, n, k = cell(sub)
    lines.append(rf"{label} & {p} & {ci} & {n} \\")
lines.append(r"\bottomrule")
lines.append(r"\end{tabular}")
lines.append(r"\end{table}")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {OUT}")
print(f"anthropic_inj n = {len(anthropic_inj)}")
