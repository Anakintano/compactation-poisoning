import json, os

results_dir = 'E:/compactation-poisoning/results'
files = sorted(f for f in os.listdir(results_dir) if f.endswith('.jsonl') and not f.endswith('.bak'))

all_rows = []
print(f"{'Batch':<22} {'Good':>6} {'B=1':>5} {'B=0':>5} {'B-ISR%':>7} {'S-ISR avg':>10}")
print('-' * 57)

for fname in files:
    rows = []
    with open(os.path.join(results_dir, fname)) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get('behavioral_score') in (0, 1):
                rows.append(r)
    tag = fname.replace('.jsonl', '')
    if not rows:
        print(f"{tag:<22} {'0':>6}")
        continue
    b1 = sum(1 for r in rows if r['behavioral_score'] == 1)
    b0 = len(rows) - b1
    bisr = round(b1 / len(rows) * 100, 1)
    sisr = round(sum(r['sisr_cosine'] for r in rows) / len(rows), 4)
    print(f"{tag:<22} {len(rows):>6} {b1:>5} {b0:>5} {bisr:>6}% {sisr:>10}")
    all_rows.extend(rows)

print('-' * 57)
print(f"{'TOTAL':<22} {len(all_rows):>6}")

if not all_rows:
    print("\nNo clean rows yet.")
    exit()

print("\n=== PRELIMINARY RESULTS ===\n")

print("B-ISR by framing (injection framing type):")
for f in ['F1', 'F2', 'F3', 'F4']:
    label = {'F1':'F1 plain','F2':'F2 urgency','F3':'F3 sys-impersonation','F4':'F4 goal-chaining'}[f]
    rf = [r for r in all_rows if r.get('framing') == f]
    if rf:
        b1 = sum(1 for r in rf if r['behavioral_score'] == 1)
        sisr = round(sum(r['sisr_cosine'] for r in rf) / len(rf), 4)
        print(f"  {label:<26} {b1:>3}/{len(rf):<5} = {round(b1/len(rf)*100,1):>5}% B-ISR  S-ISR={sisr}")

print("\nB-ISR by position (where injection sat in the conversation):")
for pos in ['beginning', 'middle', 'end']:
    rp = [r for r in all_rows if r.get('position') == pos]
    if rp:
        b1 = sum(1 for r in rp if r['behavioral_score'] == 1)
        sisr = round(sum(r['sisr_cosine'] for r in rp) / len(rp), 4)
        print(f"  {pos:<12} {b1:>3}/{len(rp):<5} = {round(b1/len(rp)*100,1):>5}% B-ISR  S-ISR={sisr}")

print("\nB-ISR by pipeline (compaction type):")
for pipe in ['anthropic', 'mem0']:
    rp = [r for r in all_rows if r.get('pipeline') == pipe]
    if rp:
        b1 = sum(1 for r in rp if r['behavioral_score'] == 1)
        sisr = round(sum(r['sisr_cosine'] for r in rp) / len(rp), 4)
        print(f"  {pipe:<12} {b1:>3}/{len(rp):<5} = {round(b1/len(rp)*100,1):>5}% B-ISR  S-ISR={sisr}")

print("\nB-ISR by tool category:")
for cat in ['email', 'calendar', 'file_system', 'web_search']:
    rc = [r for r in all_rows if r.get('tool_category') == cat]
    if rc:
        b1 = sum(1 for r in rc if r['behavioral_score'] == 1)
        print(f"  {cat:<14} {b1:>3}/{len(rc):<5} = {round(b1/len(rc)*100,1):>5}% B-ISR")
