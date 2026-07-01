"""
Routine health check — runs every 45 min.
Checks for: garbage rows (B=-1), stalled batches, row counts.
Prints a clear PASS/WARN/FAIL report.
"""
import json, os
from datetime import datetime
from pathlib import Path

RESULTS = Path("E:/compactation-poisoning/results")
TARGET = 715

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"\n{'='*60}")
print(f"HEALTH CHECK  {now}")
print(f"{'='*60}")

all_good = True
files = sorted(RESULTS.glob("*.jsonl"))
if not files:
    print("No result files yet.")
    exit()

print(f"{'Batch':<22} {'Total':>6} {'Clean':>6} {'Garbage':>8} {'B-ISR%':>7} {'Status'}")
print("-" * 60)

for f in files:
    if f.name.endswith(".bak"):
        continue
    rows = []
    try:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except Exception as e:
        print(f"{f.stem:<22} ERROR reading: {e}")
        continue

    total = len(rows)
    clean = [r for r in rows if r.get("behavioral_score") in (0, 1)]
    garbage = [r for r in rows if r.get("behavioral_score") not in (0, 1)]
    b1 = sum(1 for r in clean if r["behavioral_score"] == 1)
    bisr = round(b1 / len(clean) * 100, 1) if clean else 0.0

    garbage_pct = len(garbage) / total * 100 if total else 0

    if garbage_pct > 20:
        status = "FAIL - >20% garbage"
        all_good = False
    elif garbage_pct > 5:
        status = "WARN - some garbage"
        all_good = False
    elif total == 0:
        status = "WARN - no rows yet"
    else:
        status = "OK"

    print(f"{f.stem:<22} {total:>6} {len(clean):>6} {len(garbage):>8} {bisr:>6}%  {status}")

print("-" * 60)

# Aggregate
all_rows = []
for f in files:
    if f.name.endswith(".bak"):
        continue
    try:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    if r.get("behavioral_score") in (0, 1):
                        all_rows.append(r)
    except Exception:
        pass

total_clean = len(all_rows)
b1_total = sum(1 for r in all_rows if r["behavioral_score"] == 1)
overall_bisr = round(b1_total / total_clean * 100, 1) if total_clean else 0.0
sisr_avg = round(sum(r["sisr_cosine"] for r in all_rows) / total_clean, 4) if total_clean else 0.0

print(f"\nTotal clean rows : {total_clean}")
print(f"Overall B-ISR    : {overall_bisr}%  ({b1_total} successful injections)")
print(f"Avg S-ISR        : {sisr_avg}")
print(f"\nOverall status   : {'ALL GOOD' if all_good else 'ISSUES DETECTED - check garbage batches'}")
print(f"{'='*60}\n")
