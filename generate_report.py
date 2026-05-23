#!/usr/bin/env python3
"""Generate unified HTML report from existing results."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.report import generate_unified_report

layer1 = "reports/results.json" if os.path.exists("reports/results.json") else None
layer2 = "reports/software_results.json" if os.path.exists("reports/software_results.json") else None

if not layer1 and not layer2:
    print("No results found! Run the pipeline first.")
    sys.exit(1)

print(f"Layer 1 results: {'YES' if layer1 else 'NO'}")
print(f"Layer 2 results: {'YES' if layer2 else 'NO'}")

generate_unified_report(layer1, layer2, "reports/report.html")
print("Done! Open reports/report.html in browser.")
