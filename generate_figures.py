"""
Publication-quality figure generation for the ISMC paper.
Outputs to results/figures/
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from collections import defaultdict
from scipy import stats

# ── paths ────────────────────────────────────────────────────────────────────
RESULTS = Path("E:/compactation-poisoning/results")
FIG_DIR = RESULTS / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# ── load data ─────────────────────────────────────────────────────────────────
rows = []
for name in ["M1_anthropic", "M2_anthropic", "M3_anthropic", "M1_mem0"]:
    f = RESULTS / f"{name}.jsonl"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("behavioral_score") in (0, 1):
                    rows.append(r)

# injection rows only (exclude controls and rows with missing keys)
inj = [r for r in rows if r.get("framing") and r.get("position") and r.get("tool_category")]

print(f"Total rows: {len(rows)}  |  Injection rows with full metadata: {len(inj)}")

# ── helpers ───────────────────────────────────────────────────────────────────
def wilson_ci(k, n, z=1.96):
    """95% Wilson score confidence interval for a proportion."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = (z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return max(0, centre - margin), min(1, centre + margin)

def bisr_stats(subset):
    n = len(subset)
    k = sum(1 for r in subset if r["behavioral_score"] == 1)
    p = k / n if n else 0
    lo, hi = wilson_ci(k, n)
    return p * 100, (p - lo) * 100, (hi - p) * 100, n

# ── style ─────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.alpha": 0.3,
    "figure.dpi": 150,
})

BLUE   = "#2563EB"
ORANGE = "#EA580C"
GREEN  = "#16A34A"
GRAY   = "#6B7280"
COLORS = [BLUE, ORANGE, GREEN, "#7C3AED", GRAY]

# ═══════════════════════════════════════════════════════════════════════════════
# FIG 1 — B-ISR by injection position
# ═══════════════════════════════════════════════════════════════════════════════
positions = ["beginning", "middle", "end"]
pos_labels = ["Beginning\n(Turn 1)", "Middle\n(Turn 5–6)", "End\n(Turn 10)"]

vals, lo_errs, hi_errs, ns = [], [], [], []
for pos in positions:
    sub = [r for r in inj if r["position"] == pos]
    p, lo, hi, n = bisr_stats(sub)
    vals.append(p); lo_errs.append(lo); hi_errs.append(hi); ns.append(n)

fig, ax = plt.subplots(figsize=(6, 4))
bars = ax.bar(pos_labels, vals, color=[BLUE, ORANGE, GREEN],
              width=0.5, edgecolor="white", linewidth=0.8)
ax.errorbar(range(len(positions)), vals,
            yerr=[lo_errs, hi_errs], fmt="none", color="black",
            capsize=5, capthick=1.5, linewidth=1.5)
for i, (v, n) in enumerate(zip(vals, ns)):
    ax.text(i, v + hi_errs[i] + 0.4, f"{v:.1f}%\n(n={n})",
            ha="center", va="bottom", fontsize=9)

ax.set_ylabel("Behavioral Injection Survival Rate (%)")
ax.set_title("Fig. 1 — B-ISR by Injection Position\n(95% Wilson CI)", fontsize=11)
ax.set_ylim(0, max(vals) * 1.5)
plt.tight_layout()
plt.savefig(FIG_DIR / "fig1_bisr_position.pdf", bbox_inches="tight")
plt.savefig(FIG_DIR / "fig1_bisr_position.png", bbox_inches="tight")
plt.close()
print("Fig 1 saved.")

# ═══════════════════════════════════════════════════════════════════════════════
# FIG 2 — B-ISR by tool category
# ═══════════════════════════════════════════════════════════════════════════════
categories = ["file_system", "web_search", "calendar", "email"]
cat_labels  = ["File System", "Web Search", "Calendar", "Email"]

vals2, lo2, hi2, ns2 = [], [], [], []
for cat in categories:
    sub = [r for r in inj if r["tool_category"] == cat]
    p, lo, hi, n = bisr_stats(sub)
    vals2.append(p); lo2.append(lo); hi2.append(hi); ns2.append(n)

# sort descending
order = sorted(range(len(categories)), key=lambda i: -vals2[i])
cat_labels_s = [cat_labels[i] for i in order]
vals2_s = [vals2[i] for i in order]
lo2_s   = [lo2[i]   for i in order]
hi2_s   = [hi2[i]   for i in order]
ns2_s   = [ns2[i]   for i in order]

fig, ax = plt.subplots(figsize=(6, 4))
bars = ax.bar(cat_labels_s, vals2_s, color=COLORS[:len(categories)],
              width=0.5, edgecolor="white", linewidth=0.8)
ax.errorbar(range(len(categories)), vals2_s,
            yerr=[lo2_s, hi2_s], fmt="none", color="black",
            capsize=5, capthick=1.5, linewidth=1.5)
for i, (v, n) in enumerate(zip(vals2_s, ns2_s)):
    ax.text(i, v + hi2_s[i] + 0.3, f"{v:.1f}%\n(n={n})",
            ha="center", va="bottom", fontsize=9)

ax.set_ylabel("Behavioral Injection Survival Rate (%)")
ax.set_title("Fig. 2 — B-ISR by Tool Category\n(95% Wilson CI)", fontsize=11)
ax.set_ylim(0, max(vals2_s) * 1.6)
plt.tight_layout()
plt.savefig(FIG_DIR / "fig2_bisr_category.pdf", bbox_inches="tight")
plt.savefig(FIG_DIR / "fig2_bisr_category.png", bbox_inches="tight")
plt.close()
print("Fig 2 saved.")

# ═══════════════════════════════════════════════════════════════════════════════
# FIG 3 — B-ISR by framing type
# ═══════════════════════════════════════════════════════════════════════════════
framings = ["F1", "F2", "F3", "F4"]
framing_labels = ["F1\nPlain", "F2\nUrgency", "F3\nSys-Impersonation", "F4\nGoal-Chaining"]

vals3, lo3, hi3, ns3 = [], [], [], []
for f in framings:
    sub = [r for r in inj if r["framing"] == f]
    p, lo, hi, n = bisr_stats(sub)
    vals3.append(p); lo3.append(lo); hi3.append(hi); ns3.append(n)

fig, ax = plt.subplots(figsize=(7, 4))
bars = ax.bar(framing_labels, vals3, color=COLORS[:4],
              width=0.5, edgecolor="white", linewidth=0.8)
ax.errorbar(range(len(framings)), vals3,
            yerr=[lo3, hi3], fmt="none", color="black",
            capsize=5, capthick=1.5, linewidth=1.5)
# overall mean line
mean_bisr = np.mean(vals3)
ax.axhline(mean_bisr, color="black", linestyle="--", linewidth=1, alpha=0.6,
           label=f"Mean {mean_bisr:.1f}%")
ax.legend(fontsize=9)
for i, (v, n) in enumerate(zip(vals3, ns3)):
    ax.text(i, v + hi3[i] + 0.3, f"{v:.1f}%\n(n={n})",
            ha="center", va="bottom", fontsize=9)

ax.set_ylabel("Behavioral Injection Survival Rate (%)")
ax.set_title("Fig. 3 — B-ISR by Injection Framing Type\n(95% Wilson CI)", fontsize=11)
ax.set_ylim(0, max(vals3) * 1.7)
plt.tight_layout()
plt.savefig(FIG_DIR / "fig3_bisr_framing.pdf", bbox_inches="tight")
plt.savefig(FIG_DIR / "fig3_bisr_framing.png", bbox_inches="tight")
plt.close()
print("Fig 3 saved.")

# ═══════════════════════════════════════════════════════════════════════════════
# FIG 4 — S-ISR heatmap: framing × position
# ═══════════════════════════════════════════════════════════════════════════════
heat_data = np.zeros((4, 3))
annot_data = []
for fi, frm in enumerate(framings):
    row_annot = []
    for pi, pos in enumerate(positions):
        sub = [r for r in inj if r["framing"] == frm and r["position"] == pos]
        sisr_vals = [r["sisr_cosine"] for r in sub if r.get("sisr_cosine") is not None]
        mean_s = np.mean(sisr_vals) if sisr_vals else 0
        heat_data[fi, pi] = mean_s
        row_annot.append(f"{mean_s:.3f}\n(n={len(sub)})")
    annot_data.append(row_annot)

fig, ax = plt.subplots(figsize=(6, 4.5))
im = ax.imshow(heat_data, cmap="YlOrRd", aspect="auto",
               vmin=0.25, vmax=0.35)
ax.set_xticks(range(3)); ax.set_xticklabels(["Beginning", "Middle", "End"])
ax.set_yticks(range(4)); ax.set_yticklabels(["F1 Plain", "F2 Urgency", "F3 Sys-Imp.", "F4 Goal-Chain"])
for fi in range(4):
    for pi in range(3):
        ax.text(pi, fi, annot_data[fi][pi], ha="center", va="center",
                fontsize=8, color="black")
plt.colorbar(im, ax=ax, label="Mean S-ISR (cosine similarity)")
ax.set_title("Fig. 4 — Semantic ISR Heatmap\nFraming × Position", fontsize=11)
plt.tight_layout()
plt.savefig(FIG_DIR / "fig4_sisr_heatmap.pdf", bbox_inches="tight")
plt.savefig(FIG_DIR / "fig4_sisr_heatmap.png", bbox_inches="tight")
plt.close()
print("Fig 4 saved.")

# ═══════════════════════════════════════════════════════════════════════════════
# FIG 5 — B-ISR by summarizer model
# ═══════════════════════════════════════════════════════════════════════════════
model_map = {
    "llama-3.1-8b-instant":                       "Llama-3.1\n8B",
    "meta-llama/llama-4-scout-17b-16e-instruct":   "Llama-4\nScout 17B",
    "qwen/qwen3-32b":                              "Qwen3\n32B",
}
model_colors = [BLUE, ORANGE, GREEN]

vals5, lo5, hi5, ns5, mlabels = [], [], [], [], []
for model, label in model_map.items():
    sub = [r for r in inj if r.get("summarizer_model") == model]
    if not sub:
        continue
    p, lo, hi, n = bisr_stats(sub)
    vals5.append(p); lo5.append(lo); hi5.append(hi); ns5.append(n)
    mlabels.append(label)

fig, ax = plt.subplots(figsize=(6, 4))
bars = ax.bar(mlabels, vals5, color=model_colors[:len(mlabels)],
              width=0.5, edgecolor="white", linewidth=0.8)
ax.errorbar(range(len(mlabels)), vals5,
            yerr=[lo5, hi5], fmt="none", color="black",
            capsize=5, capthick=1.5, linewidth=1.5)
for i, (v, n) in enumerate(zip(vals5, ns5)):
    ax.text(i, v + hi5[i] + 0.3, f"{v:.1f}%\n(n={n})",
            ha="center", va="bottom", fontsize=9)

ax.set_ylabel("Behavioral Injection Survival Rate (%)")
ax.set_title("Fig. 5 — B-ISR by Summarizer Model\n(95% Wilson CI)", fontsize=11)
ax.set_ylim(0, max(vals5) * 1.7)
plt.tight_layout()
plt.savefig(FIG_DIR / "fig5_bisr_model.pdf", bbox_inches="tight")
plt.savefig(FIG_DIR / "fig5_bisr_model.png", bbox_inches="tight")
plt.close()
print("Fig 5 saved.")

# ═══════════════════════════════════════════════════════════════════════════════
# FIG 6 — Combined: position × model grouped bar
# ═══════════════════════════════════════════════════════════════════════════════
model_ids  = list(model_map.keys())
model_lbls = list(model_map.values())
x = np.arange(len(positions))
width = 0.25

fig, ax = plt.subplots(figsize=(8, 4.5))
for mi, (mid, mlbl) in enumerate(zip(model_ids, model_lbls)):
    vals_m, lo_m, hi_m = [], [], []
    for pos in positions:
        sub = [r for r in inj if r.get("summarizer_model") == mid and r["position"] == pos]
        p, lo, hi, n = bisr_stats(sub)
        vals_m.append(p); lo_m.append(lo); hi_m.append(hi)
    offset = (mi - 1) * width
    bars = ax.bar(x + offset, vals_m, width, label=mlbl.replace("\n", " "),
                  color=model_colors[mi], edgecolor="white", linewidth=0.6)
    ax.errorbar(x + offset, vals_m, yerr=[lo_m, hi_m],
                fmt="none", color="black", capsize=3, capthick=1, linewidth=1)

ax.set_xticks(x)
ax.set_xticklabels(["Beginning", "Middle", "End"])
ax.set_ylabel("B-ISR (%)")
ax.set_title("Fig. 6 — B-ISR by Position × Summarizer Model\n(95% Wilson CI)", fontsize=11)
ax.legend(title="Model", fontsize=9)
ax.set_ylim(0, 30)
plt.tight_layout()
plt.savefig(FIG_DIR / "fig6_position_by_model.pdf", bbox_inches="tight")
plt.savefig(FIG_DIR / "fig6_position_by_model.png", bbox_inches="tight")
plt.close()
print("Fig 6 saved.")

# ═══════════════════════════════════════════════════════════════════════════════
# STATS SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
stats_path = RESULTS / "stats_summary.txt"
with open(stats_path, "w", encoding="utf-8") as sf:
    sf.write("ISMC PAPER — STATISTICAL SUMMARY\n")
    sf.write(f"Total clean rows: {len(rows)}\n")
    sf.write(f"Injection rows (full metadata): {len(inj)}\n\n")

    total_b1 = sum(1 for r in inj if r["behavioral_score"] == 1)
    sf.write(f"Overall B-ISR: {total_b1}/{len(inj)} = {total_b1/len(inj)*100:.2f}%\n\n")

    sf.write("--- BY POSITION ---\n")
    for pos in positions:
        sub = [r for r in inj if r["position"] == pos]
        p, lo, hi, n = bisr_stats(sub)
        sf.write(f"  {pos:<12} {p:.2f}%  95%CI [{p-lo:.2f}%, {p+hi:.2f}%]  n={n}\n")

    sf.write("\n--- BY FRAMING ---\n")
    for frm in framings:
        sub = [r for r in inj if r["framing"] == frm]
        p, lo, hi, n = bisr_stats(sub)
        sf.write(f"  {frm}  {p:.2f}%  95%CI [{p-lo:.2f}%, {p+hi:.2f}%]  n={n}\n")

    sf.write("\n--- BY TOOL CATEGORY ---\n")
    for cat in categories:
        sub = [r for r in inj if r["tool_category"] == cat]
        p, lo, hi, n = bisr_stats(sub)
        sf.write(f"  {cat:<14} {p:.2f}%  95%CI [{p-lo:.2f}%, {p+hi:.2f}%]  n={n}\n")

    sf.write("\n--- BY MODEL ---\n")
    for mid, mlbl in model_map.items():
        sub = [r for r in inj if r.get("summarizer_model") == mid]
        if not sub: continue
        p, lo, hi, n = bisr_stats(sub)
        sf.write(f"  {mlbl.replace(chr(10),' '):<30} {p:.2f}%  95%CI [{p-lo:.2f}%, {p+hi:.2f}%]  n={n}\n")

    # Chi-squared: position effect
    sf.write("\n--- CHI-SQUARED: POSITION EFFECT ---\n")
    contingency = []
    for pos in positions:
        sub = [r for r in inj if r["position"] == pos]
        k = sum(1 for r in sub if r["behavioral_score"] == 1)
        contingency.append([k, len(sub) - k])
    chi2, p_val, dof, expected = stats.chi2_contingency(contingency)
    sf.write(f"  chi2={chi2:.3f}  df={dof}  p={p_val:.4f}  {'SIGNIFICANT (p<0.05)' if p_val < 0.05 else 'not significant'}\n")

    # Chi-squared: tool category effect
    sf.write("\n--- CHI-SQUARED: TOOL CATEGORY EFFECT ---\n")
    contingency2 = []
    for cat in categories:
        sub = [r for r in inj if r["tool_category"] == cat]
        k = sum(1 for r in sub if r["behavioral_score"] == 1)
        contingency2.append([k, len(sub) - k])
    chi2b, p_val2, dof2, _ = stats.chi2_contingency(contingency2)
    sf.write(f"  chi2={chi2b:.3f}  df={dof2}  p={p_val2:.4f}  {'SIGNIFICANT (p<0.05)' if p_val2 < 0.05 else 'not significant'}\n")

    # Chi-squared: framing (expect not significant)
    sf.write("\n--- CHI-SQUARED: FRAMING EFFECT ---\n")
    contingency3 = []
    for frm in framings:
        sub = [r for r in inj if r["framing"] == frm]
        k = sum(1 for r in sub if r["behavioral_score"] == 1)
        contingency3.append([k, len(sub) - k])
    chi2c, p_val3, dof3, _ = stats.chi2_contingency(contingency3)
    sf.write(f"  chi2={chi2c:.3f}  df={dof3}  p={p_val3:.4f}  {'SIGNIFICANT (p<0.05)' if p_val3 < 0.05 else 'not significant'}\n")

print(f"\nStats summary saved to {stats_path}")
print("\nAll figures generated in:", FIG_DIR)
