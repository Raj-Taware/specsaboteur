#!/usr/bin/env python3
"""Run iterative refinement on weak Dafny specs."""
import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.llm_client import LLMClient
from src.dafny_bridge import DafnyBridge
from src.refinement import IterativeRefiner, save_refinement_results

provider = os.environ.get("PROVIDER", "ollama")
model = os.environ.get("MODEL", "qwen2.5-coder:32b-instruct-q4_K_M")
output_dir = os.environ.get("OUTPUT", "reports/qwen/refinement")

llm = LLMClient(provider=provider, model=model)
dafny = DafnyBridge()

refiner = IterativeRefiner(llm_client=llm, dafny_bridge=dafny, max_iterations=5)

spec_files = sorted(glob.glob("specs/weak/*.dfy"))
if not spec_files:
    print("No spec files found in specs/weak/")
    sys.exit(1)

print(f"Refining {len(spec_files)} specs: {spec_files}")
results = []
for sf in spec_files:
    try:
        r = refiner.refine(sf)
        results.append(r)
    except Exception as e:
        print(f"[ERROR] Failed on {sf}: {e}")

save_refinement_results(results, output_dir)
