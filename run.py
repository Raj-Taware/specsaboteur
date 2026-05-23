#!/usr/bin/env python3
"""SpecSaboteur CLI -- run adversarial spec validation."""

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
    specs_dir = args.software_specs or "specs/software_weak"
    results = saboteur.attack_all(specs_dir)

    if results:
        save_software_results(results, args.output)

    return results


def run_refine(args, llm):
    """Iterative refinement: attack -> fix -> re-attack -> converge."""
    from src.refinement import IterativeRefiner, save_refinement_results

    if not args.specs:
        spec_files = sorted(glob.glob("specs/weak/*.dfy"))
    else:
        spec_files = args.specs

    if not spec_files:
        print("No spec files to refine. Provide paths as arguments.")
        return

    print(f"\n{'='*60}")
    print(f"ITERATIVE REFINEMENT")
    print(f"{'='*60}")
    print(f"Specs: {len(spec_files)}")
    print(f"Max iterations: {args.refine_iters}")

    try:
        dafny = DafnyBridge(dafny_path=args.dafny_path, timeout=args.dafny_timeout)
    except RuntimeError as e:
        print(f"Dafny error: {e}")
        return

    strategies = [Strategy(s) for s in args.strategies]
    refiner = IterativeRefiner(
        llm_client=llm,
        dafny_bridge=dafny,
        max_iterations=args.refine_iters,
        strategies=strategies,
        max_retries=args.max_retries,
    )

    results = []
    for spec_file in spec_files:
        try:
            result = refiner.refine(spec_file)
            results.append(result)
        except Exception as e:
            print(f"[ERROR] Refinement failed for {spec_file}: {e}")
            import traceback
            traceback.print_exc()

    if results:
        save_refinement_results(results, args.output)

    return results


def run_sampling(args, llm):
    """Statistical sampling for Layer 2."""
    from src.sampling import StatisticalSampler, save_sampling_results

    specs_dir = args.software_specs or "specs/software_weak"
    tier = "weak"
    if "medium" in specs_dir:
        tier = "medium"
    elif "strong" in specs_dir:
        tier = "strong"

    print(f"\n{'='*60}")
    print(f"STATISTICAL SAMPLING -- {tier} tier")
    print(f"{'='*60}")
    print(f"Trials per spec: {args.sample_trials}")
    print(f"Specs dir: {specs_dir}")

    sampler = StatisticalSampler(llm_client=llm, num_trials=args.sample_trials)
    report = sampler.sample_all(specs_dir, tier=tier)

    if report.specs:
        save_sampling_results(report, args.output)

    return report


def run_taxonomy(args):
    """Extract gap taxonomy from existing results."""
    from src.taxonomy import extract_taxonomy_from_results, build_taxonomy_report, save_taxonomy

    print(f"\n{'='*60}")
    print(f"GAP TAXONOMY EXTRACTION")
    print(f"{'='*60}")

    # Find all result files
    layer1_paths = []
    layer2_paths = []
    reports_dir = args.output

    for root, dirs, files in os.walk(reports_dir):
        for f in files:
            path = os.path.join(root, f)
            if f == "results.json":
                layer1_paths.append(path)
            elif f.startswith("software_results") and f.endswith(".json"):
                layer2_paths.append(path)

    print(f"Layer 1 result files: {len(layer1_paths)}")
    print(f"Layer 2 result files: {len(layer2_paths)}")

    patterns = extract_taxonomy_from_results(layer1_paths, layer2_paths)
    report = build_taxonomy_report(patterns)
    save_taxonomy(report, reports_dir)


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
        "--refine", action="store_true",
        help="Run iterative refinement loop (attack -> fix -> re-attack -> converge)"
    )
    parser.add_argument(
        "--refine-iters", type=int, default=5,
        help="Max refinement iterations (default: 5)"
    )
    parser.add_argument(
        "--sample", action="store_true",
        help="Run statistical sampling for Layer 2 (N trials per spec)"
    )
    parser.add_argument(
        "--sample-trials", type=int, default=5,
        help="Number of sampling trials per spec (default: 5)"
    )
    parser.add_argument(
        "--taxonomy", action="store_true",
        help="Extract gap taxonomy from existing results"
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

    print(f"SpecSaboteur -- Adversarial Specification Validation")
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

    # Special modes
    if args.taxonomy:
        run_taxonomy(args)
        return

    if args.refine:
        run_refine(args, llm)
        return

    if args.sample:
        run_sampling(args, llm)
        return

    # Run selected layers
    if args.layer in ("1", "both"):
        run_layer1(args, llm)

    if args.layer in ("2", "both"):
        run_layer2(args, llm)


if __name__ == "__main__":
    main()
