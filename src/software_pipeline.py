"""Layer 2 pipeline — adversarial spec validation for software specs."""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from .llm_client import LLMClient
from .software_spec import SoftwareSpec, load_all_software_specs
from .software_generator import generate_software_adversarial, SoftwareAdversarialImpl
from .spec_judge import SpecJudge, JudgeVerdict


@dataclass
class SoftwareGap:
    """A detected gap in a software spec."""
    spec_name: str
    domain: str
    strategy: str
    adversarial_code: str
    explanation: str
    exploited_gap: str
    judge_verdict: Optional[JudgeVerdict] = None
    suggested_fix: Optional[str] = None


@dataclass
class SoftwareResult:
    """Result from running Layer 2 on a software spec."""
    spec_name: str
    domain: str
    language: str
    intent: str
    gaps: list[SoftwareGap] = field(default_factory=list)
    attacks_attempted: int = 0
    attacks_compliant: int = 0     # Passed spec compliance check
    attacks_adversarial: int = 0   # Confirmed adversarial by judge
    duration_seconds: float = 0.0


# Strategies per domain
DOMAIN_STRATEGIES = {
    "rest_api": ["trivial_satisfaction", "security_bypass"],
    "smart_contract": ["edge_case_exploitation", "security_bypass"],
    "auth": ["security_bypass", "trivial_satisfaction"],
    "database": ["edge_case_exploitation", "data_integrity_violation"],
}

DEFAULT_STRATEGIES = ["trivial_satisfaction", "edge_case_exploitation"]


class SoftwareSaboteur:
    """Layer 2 pipeline for software spec adversarial validation."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.judge = SpecJudge(llm_client)

    def attack_spec(self, spec: SoftwareSpec) -> SoftwareResult:
        """Run adversarial attack on a software spec."""
        start = time.time()
        strategies = DOMAIN_STRATEGIES.get(spec.domain, DEFAULT_STRATEGIES)

        result = SoftwareResult(
            spec_name=spec.name,
            domain=spec.domain,
            language=spec.language,
            intent=spec.intent
        )

        print(f"\n{'='*60}")
        print(f"[SoftwareSaboteur] Attacking: {spec.name}")
        print(f"[SoftwareSaboteur] Domain: {spec.domain} | Language: {spec.language}")
        print(f"[SoftwareSaboteur] Strategies: {strategies}")
        print(f"{'='*60}")

        for strategy in strategies:
            print(f"\n--- Strategy: {strategy} ---")

            # Generate adversarial impl
            adv = generate_software_adversarial(self.llm, spec, strategy)
            if not adv:
                print(f"  [SKIP] Failed to generate adversarial impl")
                continue

            result.attacks_attempted += 1

            # Judge compliance + adversarial behavior
            verdict = self.judge.evaluate(
                spec.spec_text, spec.intent, adv.code, spec.language
            )

            print(f"  Compliant: {verdict.compliant} (confidence: {verdict.confidence:.1f})")
            print(f"  Adversarial: {verdict.adversarial}")

            if verdict.compliant and verdict.adversarial:
                result.attacks_compliant += 1
                result.attacks_adversarial += 1
                print(f"  [HIT!] Spec gap confirmed!")
                print(f"  Gap: {adv.exploited_gap}")

                # Suggest fix
                fix = self._suggest_fix(spec, adv, verdict)

                gap = SoftwareGap(
                    spec_name=spec.name,
                    domain=spec.domain,
                    strategy=strategy,
                    adversarial_code=adv.code,
                    explanation=adv.explanation,
                    exploited_gap=verdict.exploited_gap or adv.exploited_gap,
                    judge_verdict=verdict,
                    suggested_fix=fix
                )
                result.gaps.append(gap)

            elif verdict.compliant:
                result.attacks_compliant += 1
                print(f"  [PARTIAL] Compliant but not adversarial -- legit alternative")

            else:
                print(f"  [MISS] Spec caught attack")

        result.duration_seconds = time.time() - start
        self._print_summary(result)
        return result

    def _suggest_fix(
        self, spec: SoftwareSpec, adv: SoftwareAdversarialImpl, verdict: JudgeVerdict
    ) -> str:
        """Suggest spec additions to close the gap."""
        prompt = f"""A specification auditor found a gap in this software specification.

## Current Specification
{spec.spec_text}

## Natural Language Intent
{spec.intent}

## Adversarial Implementation (satisfies spec but violates intent)
```{spec.language}
{adv.code}
```

## Gap Exploited
{verdict.exploited_gap or adv.exploited_gap}

## Your Task
Suggest MINIMAL additions to the specification that would close this gap.
Write concrete, testable requirements that would prevent this adversarial implementation.

Format: numbered list of new requirements to add to the spec."""

        try:
            return self.llm.generate(prompt, temperature=0.3)
        except Exception as e:
            return f"(Fix generation failed: {e})"

    def _print_summary(self, result: SoftwareResult):
        print(f"\n{'='*60}")
        print(f"[SUMMARY] {result.spec_name} ({result.domain})")
        print(f"  Attacks: {result.attacks_attempted}")
        print(f"  Compliant: {result.attacks_compliant}")
        print(f"  Adversarial: {result.attacks_adversarial}")
        print(f"  Gaps: {len(result.gaps)}")
        print(f"  Duration: {result.duration_seconds:.1f}s")
        if result.gaps:
            for i, g in enumerate(result.gaps, 1):
                print(f"  [{i}] {g.strategy}: {g.exploited_gap}")
        print(f"{'='*60}")

    def attack_all(self, specs_dir: str = "specs/software") -> list[SoftwareResult]:
        """Attack all software specs in directory."""
        specs = load_all_software_specs(specs_dir)
        if not specs:
            print("[SoftwareSaboteur] No specs found!")
            return []

        results = []
        for spec in specs:
            try:
                result = self.attack_spec(spec)
                results.append(result)
            except Exception as e:
                print(f"[ERROR] Failed on {spec.name}: {e}")
                import traceback
                traceback.print_exc()

        self._print_final_summary(results)
        return results

    def _print_final_summary(self, results: list[SoftwareResult]):
        print(f"\n{'='*60}")
        print(f"LAYER 2 FINAL SUMMARY")
        print(f"{'='*60}")
        total_gaps = sum(len(r.gaps) for r in results)
        total_attacks = sum(r.attacks_attempted for r in results)
        print(f"Specs attacked: {len(results)}")
        print(f"Total attacks: {total_attacks}")
        print(f"Gaps found: {total_gaps}")
        for r in results:
            status = "GAPS FOUND" if r.gaps else "ADEQUATE"
            print(f"  {r.spec_name} ({r.domain}): {status} ({len(r.gaps)} gaps)")


def save_software_results(results: list[SoftwareResult], output_dir: str):
    """Save Layer 2 results to JSON."""
    os.makedirs(output_dir, exist_ok=True)
    output = []
    for r in results:
        entry = {
            "spec_name": r.spec_name,
            "domain": r.domain,
            "language": r.language,
            "intent": r.intent,
            "attacks_attempted": r.attacks_attempted,
            "attacks_compliant": r.attacks_compliant,
            "attacks_adversarial": r.attacks_adversarial,
            "duration_seconds": r.duration_seconds,
            "gaps": [
                {
                    "strategy": g.strategy,
                    "exploited_gap": g.exploited_gap,
                    "explanation": g.explanation,
                    "adversarial_code": g.adversarial_code,
                    "suggested_fix": g.suggested_fix,
                    "judge_compliant": g.judge_verdict.compliant if g.judge_verdict else None,
                    "judge_confidence": g.judge_verdict.confidence if g.judge_verdict else None,
                }
                for g in r.gaps
            ]
        }
        output.append(entry)

    filepath = os.path.join(output_dir, "software_results.json")
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n[Results saved to {filepath}]")
    return filepath
