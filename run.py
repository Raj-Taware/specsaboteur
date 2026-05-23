#!/usr/bin/env python3
"""SpecSaboteur CLI — run adversarial spec validation."""

import argparse
import glob
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.llm_client import create_client
from src.pipeline import SpecSaboteur, save_results
from src.dafny_bridge import DafnyBridge
from src.adversarial_generator import Strategy


def run_layer1(args, llm):
    """Layer 1: Dafny formal verification pipeline."""
    # Resolve spec files
    if args.specs:
        spec_files = args.specs
    else:
        spec_files = sorted(glob.glob("specs/weak/*.dfy"))
        if not spec_files:
            print("No spec files found in specs/weak/. Provide paths as arguments.")
            return

    print(f"\n{'='*60}")
    print(f"LAYER 1: Formal Verification (Dafny)")
    print(f"{'='*60}")
    print(f"Specs to attack: {len(spec_files)}")
    print(f"Strategies: {args.strategies}")

    # Create Dafny bridge
    try:
        dafny = DafnyBridge(
            dafny_path=args.dafny_path,
            timeout=args.dafny_timeout
        )
    except RuntimeError as e:
        print(f"Dafny error: {e}")
        print("Install Dafny: dotnet tool install -g dafny")
        return

    # Create pipeline
    strategies = [Strategy(s) for s in args.strategies]
    saboteur = SpecSaboteur(
        llm_client=llm,
        dafny_bridge=dafny,
        max_retries=args.max_retries,
        strategies=strategies
    )

    # Attack all specs
    results = []
    for spec_file in spec_files:
        try:
            result = saboteur.attack_spec(spec_file)
            results.append(result)
        except Exception as e:
            print(f"[ERROR] Failed to attack {spec_file}: {e}")
            import traceback
            traceback.print_exc()

    # Save results
    if results:
        save_results(results, args.output)

    # Print summary
    print(f"\n{'='*60}")
    print(f"LAYER 1 SUMMARY")
    print(f"{'='*60}")
    total_gaps = sum(r.attacks_confirmed_adversarial for r in results)
    total_attempted = sum(r.attacks_attempted for r in results)
    total_verified = sum(r.attacks_verified for r in results)
    print(f"Specs attacked: {len(results)}")
    print(f"Total attacks: {total_attempted}")
    print(f"Verified adversarial: {total_verified}")
    print(f"Gaps confirmed: {total_gaps}")
    if total_attempted > 0:
        print(f"Success rate: {total_verified/total_attempted*100:.1f}%")

    return results


def run_layer2(args, llm):
    """Layer 2: Software spec validation (LLM-as-judge)."""
    from src.software_pipeline import SoftwareSaboteur, save_software_results

    print(f"\n{'='*60}")
    print(f"LAYER 2: Software Spec Validation (LLM-as-Judge)")
    print(f"{'='*60}")

    saboteur = SoftwareSaboteur(llm_client=llm)
    specs_dir = args.software_specs or "specs/software"
    results = saboteur.attack_all(specs_dir)

    if results:
        save_software_results(results, args.output)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="SpecSaboteur: Find gaps in formal specifications via adversarial implementation synthesis"
    )
    parser.add_argument(
        "specs", nargs="*", default=None,
        help="Dafny spec files to attack (default: specs/weak/*.dfy)"
    )
    parser.add_argument(
        "--layer", choices=["1", "2", "both"], default="both",
        help="Which layer to run: 1=Dafny formal, 2=software specs, both=all (default: both)"
    )
    parser.add_argument(
        "--software-specs", default=None,
        help="Directory for software specs (default: specs/software)"
    )
    parser.add_argument(
        "--provider", default="gemini",
        choices=["gemini", "openai", "ollama"],
        help="LLM provider (default: gemini)"
    )
    parser.add_argument(
        "--model", default=None,
        help="Model name (default: provider-specific)"
    )
    parser.add_argument(
        "--base-url", default="http://localhost:8000/v1",
        help="Base URL for OpenAI-compatible API (default: localhost:8000)"
    )
    parser.add_argument(
        "--strategies", nargs="+",
        default=["trivial_satisfaction", "edge_case_exploitation"],
        choices=[s.value for s in Strategy],
        help="Adversarial strategies for Layer 1 (default: trivial_satisfaction edge_case_exploitation)"
    )
    parser.add_argument(
        "--max-retries", type=int, default=3,
        help="Max verification retries per strategy (default: 3)"
    )
    parser.add_argument(
        "--output", default="reports",
        help="Output directory for results (default: reports)"
    )
    parser.add_argument(
        "--dafny-path", default="dafny",
        help="Path to Dafny executable"
    )
    parser.add_argument(
        "--dafny-timeout", type=int, default=30,
        help="Dafny verification timeout in seconds"
    )

    args = parser.parse_args()

    print(f"SpecSaboteur — Adversarial Specification Validation")
    print(f"{'='*50}")
    print(f"Provider: {args.provider}")
    print(f"Layer: {args.layer}")

    # Create LLM client
    client_kwargs = {}
    if args.model:
        client_kwargs["model"] = args.model
    if args.provider == "openai":
        client_kwargs["base_url"] = args.base_url

    try:
        llm = create_client(args.provider, **client_kwargs)
        print(f"LLM client: {llm.name}")
    except Exception as e:
        print(f"Failed to create LLM client: {e}")
        sys.exit(1)

    # Run selected layers
    if args.layer in ("1", "both"):
        run_layer1(args, llm)

    if args.layer in ("2", "both"):
        run_layer2(args, llm)


if __name__ == "__main__":
    main()
