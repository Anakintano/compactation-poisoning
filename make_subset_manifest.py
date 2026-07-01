"""
Create a 660-condition subset manifest from the full 1040-entry manifest.
Selection: first 55 injection payloads (injecagent_001 to injecagent_055)
  × 4 framings × 3 positions = 660 injection conditions.
Controls: first 55 control entries (proportional).
Total: 660 + 55 = 715 entries.
"""
import json
from pathlib import Path

src = Path("E:/compactation-poisoning/data/dataset_manifest.json")
dst = Path("E:/compactation-poisoning/data/dataset_manifest_660.json")

full = json.loads(src.read_text())

# Separate injections and controls
injections = [e for e in full if not e.get("is_control", False)]
controls   = [e for e in full if e.get("is_control", False)]

# Pick 55 payloads proportionally across all 4 tool categories
# (14 from 3 categories, 13 from 1 = 55 total × 4 framings × 3 positions = 660)
from collections import defaultdict

by_cat = defaultdict(list)
seen = set()
for e in injections:
    iid = e["injection_id"]
    if iid not in seen:
        seen.add(iid)
        by_cat[e["tool_category"]].append(iid)

cats = sorted(by_cat.keys())          # consistent ordering
per_cat = {c: 14 for c in cats}       # 14 × 4 cats = 56; adjust one down
sorted_cats = sorted(cats, key=lambda c: len(by_cat[c]))
per_cat[sorted_cats[0]] -= 1          # subtract 1 from smallest category → 55 total

selected_ids = set()
for cat in cats:
    selected_ids.update(by_cat[cat][:per_cat[cat]])

kept_inj = [e for e in injections if e["injection_id"] in selected_ids]
kept_ctrl = controls[:55]

subset = kept_inj + kept_ctrl
dst.write_text(json.dumps(subset, indent=2))

# Summary
by_framing  = {}
by_position = {}
by_category = {}
for e in kept_inj:
    by_framing[e["framing"]]       = by_framing.get(e["framing"], 0) + 1
    by_position[e["position"]]     = by_position.get(e["position"], 0) + 1
    by_category[e["tool_category"]]= by_category.get(e["tool_category"], 0) + 1

print(f"Injection conditions : {len(kept_inj)}  (target 660)")
print(f"Control conditions   : {len(kept_ctrl)}")
print(f"Total in subset      : {len(subset)}")
print(f"Framings  : {by_framing}")
print(f"Positions : {by_position}")
print(f"Categories: {by_category}")
print(f"Saved to  : {dst}")
