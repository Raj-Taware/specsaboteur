#!/usr/bin/env python3
"""Run statistical sampling (N trials) on Layer 2 software specs."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.llm_client import create_client
from src.software_spec import load_all_software_specs
from src.software_pipeline import SoftwareSaboteur

provider = os.environ.get("PROVIDER", "ollama")
model = os.environ.get("MODEL", "qwen2.5-coder:32b-instruct-q4_K_M")
output_dir = os.environ.get("OUTPUT", "reports/qwen/sampling")
n_trials = int(os.environ.get("TRIALS", "5"))
specs_dir = os.environ.get("SPECS", "specs/software_weak")

os.makedirs(output_dir, exist_ok=True)

llm = create_client(provider=provider, model=model)
specs = load_all_software_specs(specs_dir)
print(f"Sampling {len(specs)} specs x {n_trials} trials")

all_results = []
for spec in specs:
    spec_trials = []
    for trial in range(1, n_trials + 1):
        print(f"\n--- {spec.name} trial {trial}/{n_trials} ---")
        start = time.time()
        saboteur = SoftwareSaboteur(llm_client=llm)
        try:
            result = saboteur.attack_spec(spec)
            spec_trials.append({
                "trial": trial,
                "gaps_found": result.gaps_confirmed,
                "strategies": [g.strategy for g in result.gaps],
                "duration": round(time.time() - start, 1),
            })
        except Exception as e:
            print(f"  [ERROR] Trial {trial}: {e}")
            spec_trials.append({"trial": trial, "gaps_found": 0, "error": str(e)})

    gaps_per_trial = [t["gaps_found"] for t in spec_trials]
    mean = sum(gaps_per_trial) / len(gaps_per_trial) if gaps_per_trial else 0
    all_results.append({
        "spec": spec.name,
        "trials": spec_trials,
        "mean_gaps": round(mean, 2),
        "min_gaps": min(gaps_per_trial) if gaps_per_trial else 0,
        "max_gaps": max(gaps_per_trial) if gaps_per_trial else 0,
    })

out_path = os.path.join(output_dir, "sampling_results.json")
with open(out_path, "w") as f:
    json.dump(all_results, f, indent=2)
print(f"\n[Sampling results saved to {out_path}]")
