#!/usr/bin/env python3
"""Quick test of Layer 2 — single software spec."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.llm_client import create_client
from src.software_spec import load_software_spec
from src.software_pipeline import SoftwareSaboteur, save_software_results

# Use the database spec (most likely to work — nearly succeeded last run)
spec = load_software_spec("specs/software/04_database_schema.yaml")
print(f"Loaded: {spec.name} ({spec.domain}/{spec.language})")
print(f"Intent: {spec.intent[:100]}...")

llm = create_client("gemini")
print(f"LLM: {llm.name}")

saboteur = SoftwareSaboteur(llm_client=llm)
result = saboteur.attack_spec(spec)

if result.gaps:
    print(f"\nSUCCESS! Found {len(result.gaps)} gaps!")
    for g in result.gaps:
        print(f"  Gap: {g.exploited_gap}")
else:
    print(f"\nNo gaps found (attacks: {result.attacks_attempted}, compliant: {result.attacks_compliant})")

save_software_results([result], "reports")
