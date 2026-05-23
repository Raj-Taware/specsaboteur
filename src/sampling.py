"""Statistical sampling for Layer 2 — run N trials to prove results aren't flukes.

LLM-as-judge is probabilistic. Single run could be lucky/unlucky.
Running N times and reporting mean +/- std proves signal is robust.
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict

from .llm_client import LLMClient
from .software_spec import SoftwareSpec, load_all_software_specs
from .software_pipeline import SoftwareSaboteur, SoftwareResult


@dataclass
class SamplingTrialResult:
    """Result from one trial of a spec."""
    trial: int
    gaps_found: int
    gap_strategies: list[str]
    duration_seconds: float


@dataclass
class SamplingResult:
    """Aggregated sampling results for one spec."""
    spec_name: str
    domain: str
    num_trials: int
    trials: list[SamplingTrialResult] = field(default_factory=list)
    mean_gaps: float = 0.0
    std_gaps: float = 0.0
    detection_rate: float = 0.0  # fraction of trials that found >= 1 gap
    strategy_frequency: dict = field(default_factory=dict)  # strategy -> count


@dataclass
class SamplingReport:
    """Full sampling report across all specs."""
    tier: str  # weak/medium/strong
    num_trials: int
    specs: list[SamplingResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0


class StatisticalSampler:
    """Run Layer 2 pipeline N times for statistical robustness."""

    def __init__(self, llm_client: LLMClient, num_trials: int = 5):
        self.llm = llm_client
        self.num_trials = num_trials

    def sample_spec(self, spec: SoftwareSpec) -> SamplingResult:
        """Run N trials on a single spec."""
        result = SamplingResult(
            spec_name=spec.name,
            domain=spec.domain,
            num_trials=self.num_trials,
        )

        print(f"\n{'='*60}")
        print(f"[SAMPLING] {spec.name} -- {self.num_trials} trials")
        print(f"{'='*60}")

        strategy_counts = defaultdict(int)

        for trial in range(1, self.num_trials + 1):
            print(f"\n  --- Trial {trial}/{self.num_trials} ---")
            start = time.time()

            saboteur = SoftwareSaboteur(llm_client=self.llm)
            try:
                attack_result = saboteur.attack_spec(spec)
                gaps = len(attack_result.gaps)
                strategies = [g.strategy for g in attack_result.gaps]
                for s in strategies:
                    strategy_counts[s] += 1
            except Exception as e:
                print(f"  [ERROR] Trial {trial} failed: {e}")
                gaps = 0
                strategies = []

            trial_result = SamplingTrialResult(
                trial=trial,
                gaps_found=gaps,
                gap_strategies=strategies,
                duration_seconds=time.time() - start,
            )
            result.trials.append(trial_result)
            print(f"  Trial {trial}: {gaps} gaps found")

        # Compute statistics
        gap_counts = [t.gaps_found for t in result.trials]
        result.mean_gaps = sum(gap_counts) / len(gap_counts) if gap_counts else 0
        result.std_gaps = (
            (sum((x - result.mean_gaps) ** 2 for x in gap_counts) / len(gap_counts)) ** 0.5
            if gap_counts else 0
        )
        result.detection_rate = sum(1 for g in gap_counts if g > 0) / len(gap_counts) if gap_counts else 0
        result.strategy_frequency = dict(strategy_counts)

        print(f"\n  [STATS] {spec.name}: mean={result.mean_gaps:.1f} +/- {result.std_gaps:.2f}")
        print(f"     Detection rate: {result.detection_rate:.0%} ({sum(1 for g in gap_counts if g > 0)}/{len(gap_counts)} trials)")

        return result

    def sample_all(self, specs_dir: str, tier: str = "unknown") -> SamplingReport:
        """Run sampling on all specs in a directory."""
        start = time.time()
        specs = load_all_software_specs(specs_dir)
        if not specs:
            print("[SAMPLING] No specs found!")
            return SamplingReport(tier=tier, num_trials=self.num_trials)

        report = SamplingReport(
            tier=tier,
            num_trials=self.num_trials,
        )

        for spec in specs:
            try:
                result = self.sample_spec(spec)
                report.specs.append(result)
            except Exception as e:
                print(f"[ERROR] Sampling failed for {spec.name}: {e}")

        report.total_duration_seconds = time.time() - start
        self._print_summary(report)
        return report

    def _print_summary(self, report: SamplingReport):
        print(f"\n{'='*60}")
        print(f"SAMPLING SUMMARY -- {report.tier} tier ({report.num_trials} trials each)")
        print(f"{'='*60}")
        print(f"{'Spec':<25} {'Mean Gaps':>10} {'Std':>8} {'Detection':>10}")
        print(f"{'-'*55}")
        for s in report.specs:
            print(f"{s.spec_name:<25} {s.mean_gaps:>10.1f} {s.std_gaps:>8.2f} {s.detection_rate:>9.0%}")
        print(f"{'='*60}")


def save_sampling_results(report: SamplingReport, output_dir: str):
    """Save sampling results to JSON."""
    os.makedirs(output_dir, exist_ok=True)
    output = {
        "tier": report.tier,
        "num_trials": report.num_trials,
        "total_duration_seconds": report.total_duration_seconds,
        "specs": [
            {
                "spec_name": s.spec_name,
                "domain": s.domain,
                "num_trials": s.num_trials,
                "mean_gaps": s.mean_gaps,
                "std_gaps": s.std_gaps,
                "detection_rate": s.detection_rate,
                "strategy_frequency": s.strategy_frequency,
                "trials": [
                    {
                        "trial": t.trial,
                        "gaps_found": t.gaps_found,
                        "gap_strategies": t.gap_strategies,
                        "duration_seconds": t.duration_seconds,
                    }
                    for t in s.trials
                ],
            }
            for s in report.specs
        ],
    }

    filepath = os.path.join(output_dir, f"sampling_{report.tier}.json")
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n[Sampling results saved to {filepath}]")
    return filepath
