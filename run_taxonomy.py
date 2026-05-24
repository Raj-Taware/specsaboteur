#!/usr/bin/env python3
"""Extract gap taxonomy from all results."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.taxonomy import extract_taxonomy_from_results, GapPattern

output_dir = os.environ.get("OUTPUT", "reports/qwen")

# Collect all result files
result_files = []
for root, dirs, files in os.walk(output_dir):
    for f in files:
        if f in ("results.json", "software_results.json", "refinement_results.json"):
            result_files.append(os.path.join(root, f))

print(f"Found {len(result_files)} result files: {result_files}")

all_patterns = []
for rf in result_files:
    try:
        patterns = extract_taxonomy_from_results(rf)
        all_patterns.extend(patterns)
        print(f"  {rf}: {len(patterns)} patterns")
    except Exception as e:
        print(f"  [ERROR] {rf}: {e}")

# Save taxonomy
taxonomy = {}
for p in all_patterns:
    cat = p.category
    if cat not in taxonomy:
        taxonomy[cat] = []
    taxonomy[cat].append({
        "subcategory": p.subcategory,
        "description": p.description,
        "spec_file": p.spec_file,
        "domain": p.domain,
        "strategy": p.strategy,
        "severity": p.severity,
    })

out_path = os.path.join(output_dir, "gap_taxonomy.json")
with open(out_path, "w") as f:
    json.dump(taxonomy, f, indent=2)
print(f"\n[Taxonomy saved to {out_path}] — {len(all_patterns)} patterns in {len(taxonomy)} categories")
