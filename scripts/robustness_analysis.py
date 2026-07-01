"""
Robustness analyses for main2-copy.tex.
Outputs: numbers for logistic regression table, drop-one table,
interaction test, payload outlier check, power statement,
and threshold sensitivity data.
"""

import json, math, pathlib, collections
import numpy as np
from scipy import stats
from scipy.stats import chi2_contingency

# ── Load data ────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).parent.parent / "results"
FILES = ["M1_anthropic.jsonl", "M2_anthropic.jsonl", "M3_anthropic.jsonl"]

rows = []
for f in FILES:
    p = ROOT / f
    if not p.exists():
        continue
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

# Keep only injection rows with full metadata
rows = [r for r in rows if "framing" in r and "position" in r and "tool_category" in r]
print(f"Loaded {len(rows)} rows\n")

# ── Helper: Wilson CI ─────────────────────────────────────────────────────────
def wilson_ci(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2*n)) / denom
    margin = (z * math.sqrt(p*(1-p)/n + z**2/(4*n**2))) / denom
    return round(p*100,2), round((centre-margin)*100,2), round((centre+margin)*100,2)

# ── A. Logistic regression ────────────────────────────────────────────────────
print("=" * 60)
print("A. LOGISTIC REGRESSION")
print("=" * 60)
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import LabelEncoder
    import pandas as pd

    df = pd.DataFrame(rows)
    df["y"] = df["behavioral_score"].astype(int)

    # Encode categoricals
    for col in ["position", "framing", "tool_category", "summarizer_model"]:
        if col not in df.columns:
            df[col] = "unknown"
    df = pd.get_dummies(df, columns=["position","framing","tool_category","summarizer_model"],
                        drop_first=True)

    feature_cols = [c for c in df.columns if any(
        c.startswith(p) for p in ["position_","framing_","tool_category_","summarizer_model_"])]
    X = df[feature_cols].values
    y = df["y"].values

    from sklearn.linear_model import LogisticRegression
    from scipy.special import expit

    lr = LogisticRegression(max_iter=500, solver="lbfgs")
    lr.fit(X, y)

    # Approximate SEs via Hessian
    p_hat = expit(lr.decision_function(X))
    W = np.diag(p_hat * (1 - p_hat))
    XX = np.column_stack([np.ones(len(X)), X])
    try:
        cov = np.linalg.inv(XX.T @ W @ XX)
        ses = np.sqrt(np.diag(cov))[1:]  # skip intercept
    except np.linalg.LinAlgError:
        ses = np.full(len(feature_cols), np.nan)

    print(f"{'Feature':<40} {'OR':>8} {'95% CI':>20} {'z':>8} {'p':>8}")
    for name, coef, se in zip(feature_cols, lr.coef_[0], ses):
        OR = math.exp(coef)
        lo = math.exp(coef - 1.96*se)
        hi = math.exp(coef + 1.96*se)
        z = coef / se if se > 0 else float("nan")
        p = 2*(1 - stats.norm.cdf(abs(z))) if not math.isnan(z) else float("nan")
        print(f"{name:<40} {OR:8.3f}  [{lo:.3f}, {hi:.3f}]  {z:8.3f}  {p:8.4f}")

except ImportError:
    print("sklearn not available; skipping logistic regression")

# ── C. Drop-one-summarizer table ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("C. DROP-ONE-SUMMARIZER: Beginning vs End B-ISR gap")
print("=" * 60)

models = list(set(r.get("summarizer_model","") for r in rows))

def bisr_pos(subset, pos):
    n = [r for r in subset if r["position"] == pos]
    k = sum(r["behavioral_score"] for r in n)
    return len(n), k

def gap_row(label, subset):
    nb, kb = bisr_pos(subset, "beginning")
    ne, ke = bisr_pos(subset, "end")
    pb, lb, ub = wilson_ci(kb, nb)
    pe, le, ue = wilson_ci(ke, ne)
    gap = round(pb - pe, 2)
    # chi2 for position effect in this subset
    nm, km = bisr_pos(subset, "middle")
    ct = np.array([[kb, nb-kb],[km, nm-km],[ke, ne-ke]])
    chi2, p, *_ = chi2_contingency(ct)
    print(f"{label:<30} Beg={pb}% [{lb},{ub}]  End={pe}% [{le},{ue}]  "
          f"Gap={gap}pp  chi2={chi2:.2f}  p={p:.4f}  n={len(subset)}")

gap_row("Full pooled sample", rows)
for m in sorted(models):
    drop = [r for r in rows if r.get("summarizer_model","") != m]
    gap_row(f"Drop {m[:30]}", drop)

# ── D. Position x Framing interaction ────────────────────────────────────────
print("\n" + "=" * 60)
print("D. POSITION x FRAMING INTERACTION (chi-square)")
print("=" * 60)

rows = [r for r in rows if r.get("framing") and r.get("position")]
framings = sorted(set(r["framing"] for r in rows))
positions = sorted(set(r["position"] for r in rows))
ct = np.zeros((len(framings), len(positions)), dtype=int)
for r in rows:
    fi = framings.index(r["framing"])
    pi = positions.index(r["position"])
    ct[fi, pi] += r["behavioral_score"]

# contingency on counts (successes) requires full table including failures
ct_full = np.zeros((len(framings), len(positions), 2), dtype=int)
for r in rows:
    fi = framings.index(r["framing"])
    pi = positions.index(r["position"])
    ct_full[fi, pi, r["behavioral_score"]] += 1

# collapse to successes/failures 2D
ct2 = np.zeros((len(framings)*len(positions), 2), dtype=int)
labels = []
for fi, fr in enumerate(framings):
    for pi, po in enumerate(positions):
        idx = fi*len(positions)+pi
        ct2[idx, 1] = ct_full[fi,pi,1]
        ct2[idx, 0] = ct_full[fi,pi,0]
        labels.append(f"{fr}_{po}")

# Test interaction: compare full model chi2 with marginal
# Simple: run chi2 on framing x position success counts
success_ct = np.array([[ct_full[fi,pi,1] for pi in range(len(positions))]
                        for fi in range(len(framings))])
chi2_int, p_int, dof_int, _ = chi2_contingency(success_ct)
print(f"Interaction chi2={chi2_int:.3f}  df={dof_int}  p={p_int:.4f}")
print(f"Framings: {framings}")
print(f"Positions: {positions}")
print("Success counts (framing x position):")
print(success_ct)

# ── E. Payload-level outlier check ───────────────────────────────────────────
print("\n" + "=" * 60)
print("E. PAYLOAD-LEVEL OUTLIER CHECK")
print("=" * 60)

payload_bisr = collections.defaultdict(list)
for r in rows:
    payload_bisr[r["injection_id"]].append(r["behavioral_score"])

payload_rates = {pid: (sum(vs), len(vs), sum(vs)/len(vs))
                 for pid, vs in payload_bisr.items()}

sorted_payloads = sorted(payload_rates.items(), key=lambda x: x[1][2], reverse=True)
print("Top 10 payloads by B-ISR:")
for pid, (k, n, rate) in sorted_payloads[:10]:
    print(f"  {pid:<30} k={k}  n={n}  B-ISR={rate*100:.1f}%")

# Drop top 5 and recompute position effect
top5_ids = {pid for pid, _ in sorted_payloads[:5]}
trimmed = [r for r in rows if r["injection_id"] not in top5_ids]
print(f"\nAfter dropping top-5 payloads: n={len(trimmed)}")
nb, kb = bisr_pos(trimmed, "beginning")
nm, km = bisr_pos(trimmed, "middle")
ne, ke = bisr_pos(trimmed, "end")
ct_trim = np.array([[kb, nb-kb],[km, nm-km],[ke, ne-ke]])
chi2_trim, p_trim, *_ = chi2_contingency(ct_trim)
pb, lb, ub = wilson_ci(kb, nb)
pe, le, ue = wilson_ci(ke, ne)
print(f"  Beg={pb}% [{lb},{ub}]  End={pe}% [{le},{ue}]  "
      f"chi2={chi2_trim:.2f}  p={p_trim:.4f}")

# ── F. Power statement ────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("F. STATISTICAL POWER")
print("=" * 60)

# Observed: beginning vs end
n1, k1 = bisr_pos(rows, "beginning")
n2, k2 = bisr_pos(rows, "end")
p1 = k1/n1; p2 = k2/n2
p_pool = (k1+k2)/(n1+n2)
z_obs = (p1-p2) / math.sqrt(p_pool*(1-p_pool)*(1/n1+1/n2))
print(f"Observed: p_beg={p1*100:.2f}%  p_end={p2*100:.2f}%  z={z_obs:.3f}  "
      f"n_beg={n1}  n_end={n2}")

# Power at observed effect size
from scipy.stats import norm
alpha = 0.05
z_alpha = norm.ppf(1 - alpha/2)
se_alt = math.sqrt(p1*(1-p1)/n1 + p2*(1-p2)/n2)
ncp = (p1 - p2) / se_alt
power = 1 - norm.cdf(z_alpha - abs(ncp)) + norm.cdf(-z_alpha - abs(ncp))
print(f"Achieved power (two-sided, alpha=0.05) = {power*100:.1f}%")

# MDE: smallest detectable difference at 80% power, same n
z_beta = norm.ppf(0.80)
# MDE formula for proportions using pooled p (approximate)
p_base = p2  # use end as baseline
for mde_step in np.arange(0.001, 0.20, 0.001):
    p_alt = p_base + mde_step
    p_p = (p_base*n2 + p_alt*n1) / (n1+n2)
    z_stat = (p_alt - p_base) / math.sqrt(p_p*(1-p_p)*(1/n1+1/n2))
    pwr = 1 - norm.cdf(z_alpha - z_stat) + norm.cdf(-z_alpha - z_stat)
    if pwr >= 0.80:
        print(f"MDE at 80% power (n_beg={n1}, n_end={n2}) = {mde_step*100:.1f}pp")
        print(f"Observed effect = {(p1-p2)*100:.1f}pp  ({(p1-p2)/mde_step:.1f}x MDE)")
        break

# ── B. S-ISR threshold sensitivity (data for figure) ─────────────────────────
print("\n" + "=" * 60)
print("B. S-ISR THRESHOLD SENSITIVITY (using sisr_cosine for threshold sweep)")
print("=" * 60)

# The paper uses keyword overlap for B-ISR; for threshold sensitivity we re-derive
# B-ISR at different keyword thresholds IF keyword_score field exists,
# otherwise we use sisr_cosine threshold as a proxy for binary S-ISR
has_kscore = "keyword_score" in rows[0] if rows else False
if has_kscore:
    print("keyword_score field found; sweeping threshold")
    for thresh in [0.30, 0.40, 0.50, 0.60, 0.70]:
        for pos in positions:
            sub = [r for r in rows if r["position"] == pos]
            k = sum(1 for r in sub if r.get("keyword_score",0) >= thresh)
            n = len(sub)
            print(f"  thresh={thresh}  pos={pos}  B-ISR={k/n*100:.1f}% (n={n})")
else:
    print("No keyword_score field in data; threshold sweep requires raw keyword scores.")
    print("S-ISR cosine distribution by position (for reference):")
    for pos in positions:
        sub = [r["sisr_cosine"] for r in rows if r["position"] == pos and "sisr_cosine" in r]
        if sub:
            print(f"  pos={pos}  mean={np.mean(sub):.3f}  median={np.median(sub):.3f}  n={len(sub)}")

print("\nDone.")
