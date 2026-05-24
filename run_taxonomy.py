#!/usr/bin/env python3
"""Extract gap taxonomy from all results."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.taxonomy import extract_taxonomy_from_results, build_taxonomy_report, save_taxonomy

output_dir = os.environ.get("OUTPUT", "reports/qwen")

# Collect L1 and L2 result files separately
layer1_paths = []
layer2_paths = []
for root, dirs, files in os.walk(output_dir):
    for f in files:
        full = os.path.join(root, f)
        if f == "results.json":
            layer1_paths.append(full)
        elif f == "software_results.json":
            layer2_paths.append(full)

print(f"Layer 1 files: {layer1_paths}")
print(f"Layer 2 files: {layer2_paths}")

patterns = extract_taxonomy_from_results(layer1_paths=layer1_paths, layer2_paths=layer2_paths)
print(f"Extracted {len(patterns)} gap patterns")

if patterns:
    report = build_taxonomy_report(patterns)
    save_taxonomy(report, output_dir)
else:
    print("No gaps found to categorize")
