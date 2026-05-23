"""SpecSaboteur main pipeline — orchestrates adversarial spec validation."""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from .dafny_bridge import DafnyBridge, extract_spec_from_file, VerifyResult
from .adversarial_generator import (
    Strategy, AdversarialImpl, build_adversarial_prompt,
    build_retry_prompt, parse_llm_response
)
from .llm_client import LLMClient


@dataclass
class SpecGap:
    """A confirmed specification gap."""
    spec_file: str
    strategy: Strategy
    adversarial_code: str
    explanation: str
    exploited_gap: str
    verification_output: str
    behavioral_test_result: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class SaboteurResult:
    """Full result from running SpecSaboteur on a spec."""
    spec_file: str
    intent: str
    gaps_found: list[SpecGap] = field(default_factory=list)
    attacks_attempted: int = 0
    attacks_verified: int = 0
    attacks_confirmed_adversarial: int = 0
    attacks_filtered: int = 0  # Legitimate alternatives
    duration_seconds: float = 0.0


class SpecSaboteur:
    """Main pipeline: attack specs, find gaps, suggest fixes."""

    def __init__(
        self,
        llm_client: LLMClient,
        dafny_bridge: Optional[DafnyBridge] = None,
        max_retries: int = 3,
        strategies: Optional[list[Strategy]] = None
    ):
        self.llm = llm_client
        self.dafny = dafny_bridge or DafnyBridge()
        self.max_retries = max_retries
        self.strategies = strategies or [
            Strategy.TRIVIAL_SATISFACTION,
            Strategy.EDGE_CASE_EXPLOITATION
        ]

    def attack_spec(self, spec_file: str) -> SaboteurResult:
        """Run full adversarial attack pipeline on a spec file."""
        start = time.time()
        spec_info = extract_spec_from_file(spec_file)
        result = SaboteurResult(
            spec_file=spec_file,
            intent=spec_info["intent"]
        )

        print(f"\n{'='*60}")
        print(f"[SpecSaboteur] Attacking: {spec_file}")
        print(f"[SpecSaboteur] Intent: {spec_info['intent']}")
        print(f"[SpecSaboteur] Strategies: {[s.value for s in self.strategies]}")
        print(f"{'='*60}")

        for strategy in self.strategies:
            print(f"\n--- Strategy: {strategy.value} ---")
            adv_impl = self._generate_adversarial(
                spec_info["intent"], spec_info["spec"], strategy
            )
            if not adv_impl:
                print(f"  [SKIP] LLM failed to generate implementation")
                continue

            result.attacks_attempted += 1
            adv_impl.strategy = strategy

            # Try to verify
            verified = self._verify_with_retries(
                adv_impl, spec_info["intent"], spec_info["spec"], strategy
            )
            if not verified:
                print(f"  [MISS] Could not produce verifying adversarial impl")
                continue

            result.attacks_verified += 1
            print(f"  [HIT!] Adversarial impl VERIFIED by Dafny!")
            print(f"  Explanation: {adv_impl.explanation}")
            print(f"  Gap: {adv_impl.exploited_gap}")

            # Generate suggested fix
            fix = self._suggest_fix(
                spec_info["intent"], spec_info["spec"], adv_impl
            )

            gap = SpecGap(
                spec_file=spec_file,
                strategy=strategy,
                adversarial_code=adv_impl.code,
                explanation=adv_impl.explanation,
                exploited_gap=adv_impl.exploited_gap,
                verification_output=adv_impl.verification_output,
                suggested_fix=fix
            )
            result.gaps_found.append(gap)
            result.attacks_confirmed_adversarial += 1

        result.duration_seconds = time.time() - start
        self._print_summary(result)
        return result

    def _generate_adversarial(
        self, intent: str, spec: str, strategy: Strategy
    ) -> Optional[AdversarialImpl]:
        """Generate an adversarial implementation using LLM."""
        prompt = build_adversarial_prompt(intent, spec, strategy)
        try:
            response = self.llm.generate(prompt, temperature=0.7)
            impl = parse_llm_response(response)
            if impl:
                impl.strategy = strategy
            return impl
        except Exception as e:
            print(f"  [ERROR] LLM generation failed: {e}")
            return None

    def _verify_with_retries(
        self, impl: AdversarialImpl, intent: str, spec: str, strategy: Strategy
    ) -> bool:
        """Try to verify adversarial impl, retrying with error feedback."""
        for attempt in range(self.max_retries):
            print(f"  Verify attempt {attempt + 1}/{self.max_retries}...")
            result = self.dafny.verify(impl.code)
            impl.verification_output = result.output

            if result.success:
                impl.verified = True
                return True

            if attempt < self.max_retries - 1:
                print(f"  Verification failed, retrying with error feedback...")
                retry_prompt = build_retry_prompt(
                    intent, spec, strategy, impl.code, result.errors
                )
                try:
                    response = self.llm.generate(retry_prompt, temperature=0.5)
                    new_impl = parse_llm_response(response)
                    if new_impl:
                        impl.code = new_impl.code
                        impl.explanation = new_impl.explanation
                        impl.exploited_gap = new_impl.exploited_gap
                except Exception as e:
                    print(f"  [ERROR] Retry failed: {e}")

        impl.verified = False
        return False

    def _suggest_fix(
        self, intent: str, spec: str, adv_impl: AdversarialImpl
    ) -> str:
        """Ask LLM to suggest a spec fix based on the gap found."""
        prompt = f"""A specification auditor found that this Dafny specification has a gap.

## Natural Language Intent
{intent}

## Current Specification
```dafny
{spec}
```

## Adversarial Implementation (satisfies spec but violates intent)
```dafny
{adv_impl.code}
```

## Gap Found
{adv_impl.exploited_gap}

## Your Task
Suggest the MINIMAL additional Dafny specification clause(s) (ensures/requires/invariant)
that would close this gap and prevent this adversarial implementation from verifying.

Return ONLY the additional clause(s) as Dafny code, one per line. Example:
ensures forall i :: 0 <= i < a.Length ==> a[i] >= 0
ensures |result| == |input|

Do not return the full method signature — only the NEW clauses to add."""

        try:
            return self.llm.generate(prompt, temperature=0.3)
        except Exception as e:
            return f"(Fix generation failed: {e})"

    def _print_summary(self, result: SaboteurResult):
        """Print summary of attack results."""
        print(f"\n{'='*60}")
        print(f"[SUMMARY] {result.spec_file}")
        print(f"  Intent: {result.intent}")
        print(f"  Attacks attempted: {result.attacks_attempted}")
        print(f"  Attacks verified: {result.attacks_verified}")
        print(f"  Gaps confirmed: {result.attacks_confirmed_adversarial}")
        print(f"  Filtered (legit alternatives): {result.attacks_filtered}")
        print(f"  Duration: {result.duration_seconds:.1f}s")

        if result.gaps_found:
            print(f"\n  GAPS FOUND:")
            for i, gap in enumerate(result.gaps_found, 1):
                print(f"  [{i}] Strategy: {gap.strategy.value}")
                print(f"      Gap: {gap.exploited_gap}")
                print(f"      Explanation: {gap.explanation}")
                if gap.suggested_fix:
                    print(f"      Suggested fix: {gap.suggested_fix[:200]}...")
        else:
            print(f"\n  NO GAPS FOUND — spec appears adequate!")
        print(f"{'='*60}")


def save_results(results: list[SaboteurResult], output_dir: str):
    """Save results to JSON for reporting."""
    os.makedirs(output_dir, exist_ok=True)
    output = []
    for r in results:
        entry = {
            "spec_file": r.spec_file,
            "intent": r.intent,
            "attacks_attempted": r.attacks_attempted,
            "attacks_verified": r.attacks_verified,
            "gaps_confirmed": r.attacks_confirmed_adversarial,
            "duration_seconds": r.duration_seconds,
            "gaps": [
                {
                    "strategy": g.strategy.value,
                    "exploited_gap": g.exploited_gap,
                    "explanation": g.explanation,
                    "adversarial_code": g.adversarial_code,
                    "suggested_fix": g.suggested_fix
                }
                for g in r.gaps_found
            ]
        }
        output.append(entry)

    filepath = os.path.join(output_dir, "results.json")
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n[Results saved to {filepath}]")
    return filepath
