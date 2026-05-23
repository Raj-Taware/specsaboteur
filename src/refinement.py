"""Iterative Spec Refinement — attack → fix → re-attack → converge.

The core demo: shows specs getting stronger through adversarial feedback
until no more gaps can be found. This is CEGIS inverted —
counterexample-guided specification refinement.
"""

import json
import os
import re
import time
import copy
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

from .llm_client import LLMClient
from .dafny_bridge import DafnyBridge, extract_spec_from_file
from .adversarial_generator import Strategy
from .pipeline import SpecSaboteur, SaboteurResult


@dataclass
class RefinementStep:
    """One iteration of the refinement loop."""
    iteration: int
    spec_text: str
    gaps_found: int
    gaps_details: list[dict] = field(default_factory=list)
    fix_applied: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class RefinementResult:
    """Full result of iterative refinement on one spec."""
    spec_file: str
    intent: str
    original_spec: str
    final_spec: str
    iterations: list[RefinementStep] = field(default_factory=list)
    converged: bool = False
    total_gaps_found: int = 0
    total_gaps_closed: int = 0
    total_duration_seconds: float = 0.0


class IterativeRefiner:
    """Attack → Fix → Re-attack → Converge loop."""

    def __init__(
        self,
        llm_client: LLMClient,
        dafny_bridge: DafnyBridge,
        max_iterations: int = 5,
        strategies: Optional[list[Strategy]] = None,
        max_retries: int = 3,
    ):
        self.llm = llm_client
        self.dafny = dafny_bridge
        self.max_iterations = max_iterations
        self.strategies = strategies or [
            Strategy.TRIVIAL_SATISFACTION,
            Strategy.EDGE_CASE_EXPLOITATION,
        ]
        self.max_retries = max_retries

    def refine(self, spec_file: str) -> RefinementResult:
        """Run iterative refinement on a spec file."""
        start = time.time()
        spec_info = extract_spec_from_file(spec_file)
        intent = spec_info["intent"]
        # Use full file content so we have the brace and body for splicing
        with open(spec_file) as f:
            current_spec = f.read()

        result = RefinementResult(
            spec_file=spec_file,
            intent=intent,
            original_spec=current_spec,
            final_spec=current_spec,
        )

        print(f"\n{'='*70}")
        print(f"[REFINEMENT] Starting iterative refinement: {spec_file}")
        print(f"[REFINEMENT] Intent: {intent}")
        print(f"[REFINEMENT] Max iterations: {self.max_iterations}")
        print(f"{'='*70}")

        for iteration in range(1, self.max_iterations + 1):
            iter_start = time.time()
            print(f"\n{'-'*50}")
            print(f"  ITERATION {iteration}/{self.max_iterations}")
            print(f"{'-'*50}")

            # Write current spec to temp file for attack
            temp_file = self._write_temp_spec(spec_file, current_spec, iteration)

            # Attack current spec
            saboteur = SpecSaboteur(
                llm_client=self.llm,
                dafny_bridge=self.dafny,
                max_retries=self.max_retries,
                strategies=self.strategies,
            )

            try:
                attack_result = saboteur.attack_spec(temp_file)
            except Exception as e:
                print(f"  [ERROR] Attack failed: {e}")
                break
            finally:
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            gaps_this_round = attack_result.attacks_confirmed_adversarial

            step = RefinementStep(
                iteration=iteration,
                spec_text=current_spec,
                gaps_found=gaps_this_round,
                gaps_details=[
                    {
                        "strategy": g.strategy.value,
                        "gap": g.exploited_gap,
                        "fix": g.suggested_fix,
                    }
                    for g in attack_result.gaps_found
                ],
                duration_seconds=time.time() - iter_start,
            )
            result.iterations.append(step)
            result.total_gaps_found += gaps_this_round

            if gaps_this_round == 0:
                print(f"\n  [OK] NO GAPS FOUND -- spec converged!")
                result.converged = True
                break

            # Apply fix from first gap found
            gap = attack_result.gaps_found[0]
            fix = gap.suggested_fix
            if not fix or fix.startswith("(Fix generation failed"):
                # Try to generate fix separately
                fix = self._generate_fix(intent, current_spec, gap.exploited_gap, gap.adversarial_code)

            if fix:
                new_spec = self._apply_fix(current_spec, fix, intent)
                if new_spec and new_spec != current_spec:
                    print(f"\n  [FIX] Applying fix to spec...")
                    print(f"  Fix: {fix[:200]}...")
                    step.fix_applied = fix
                    current_spec = new_spec
                    result.final_spec = current_spec
                    result.total_gaps_closed += 1
                else:
                    print(f"  [WARN] Could not apply fix -- stopping refinement")
                    break
            else:
                print(f"  [WARN] No fix generated -- stopping refinement")
                break

        result.total_duration_seconds = time.time() - start
        self._print_refinement_summary(result)
        return result

    def _write_temp_spec(self, original_file: str, spec_text: str, iteration: int) -> str:
        """Write current spec to a temp file for Dafny verification."""
        base = Path(original_file)
        temp_path = base.parent / f"_temp_refine_{base.stem}_iter{iteration}{base.suffix}"
        with open(temp_path, "w") as f:
            f.write(spec_text)
        return str(temp_path)

    def _generate_fix(self, intent: str, spec: str, gap: str, adversarial_code: str) -> Optional[str]:
        """Generate a spec fix for a found gap."""
        prompt = f"""A specification auditor found a gap in this Dafny specification.

## Natural Language Intent
{intent}

## Current Specification
```dafny
{spec}
```

## Adversarial Implementation (satisfies spec but violates intent)
```dafny
{adversarial_code}
```

## Gap Found
{gap}

## Your Task
Write the COMPLETE updated Dafny specification (method signature + all ensures/requires clauses)
that closes this gap. Include ALL existing clauses plus the new one(s).

Return ONLY the complete method signature with all clauses, no implementation body.
End with a single open brace on its own line.

Example format:
method Sort(a: array<int>)
  modifies a
  ensures forall i :: 0 <= i < a.Length - 1 ==> a[i] <= a[i+1]
  ensures multiset(a[..]) == multiset(old(a[..]))
{{"""

        try:
            response = self.llm.generate(prompt, temperature=0.3)
            return response
        except Exception as e:
            print(f"  [ERROR] Fix generation failed: {e}")
            return None

    def _apply_fix(self, current_spec: str, fix_response: str, intent: str) -> Optional[str]:
        """Apply LLM-generated fix to produce new spec text."""
        # Strip markdown code fences from LLM response
        cleaned = fix_response.strip()
        cleaned = re.sub(r"```\w*\n?", "", cleaned).strip()
        cleaned = cleaned.replace("```", "").strip()

        print(f"  [REFINE] Fix response (cleaned): {cleaned[:300]}")

        # Strategy 1: Full method signature in response
        method_match = re.search(
            r"(method\s+\w+\s*\(.*?\)(?:\s+returns\s*\(.*?\))?\s*(?:(?:requires|ensures|modifies|decreases|reads)\s+[^\n]+\n)*)",
            cleaned,
            re.DOTALL
        )

        if method_match:
            new_spec_body = method_match.group(0).strip()
            intent_comment = f"// Intent: {intent}\n"
            full_spec = f"{intent_comment}\n{new_spec_body}\n{{\n  // Implementation intentionally left empty for adversarial generation\n}}\n"
            print(f"  [REFINE] Applied fix via full method match")
            return full_spec

        # Strategy 2: Extract ensures/requires clauses and splice into current spec
        ensures_matches = re.findall(r"(ensures\s+[^\n]+)", cleaned)
        requires_matches = re.findall(r"(requires\s+[^\n]+)", cleaned)
        print(f"  [REFINE] Strategy 2: ensures={len(ensures_matches)}, requires={len(requires_matches)}")

        if ensures_matches or requires_matches:
            # Deduplicate: skip clauses already in current spec
            existing = current_spec.replace(" ", "")
            new_clauses = []
            for clause in requires_matches + ensures_matches:
                if clause.replace(" ", "") not in existing:
                    new_clauses.append(f"  {clause.strip()}")

            if not new_clauses:
                print(f"  [REFINE] All suggested clauses already in spec")
                return None

            clause_text = "\n".join(new_clauses)
            # Insert before opening brace
            brace_pos = current_spec.rfind("{")
            if brace_pos > 0:
                new_spec = current_spec[:brace_pos] + clause_text + "\n" + current_spec[brace_pos:]
                print(f"  [REFINE] Applied fix via clause insertion: {clause_text}")
                return new_spec

        # Strategy 3: LLM returned prose with embedded Dafny — extract any line with ensures/requires
        lines = cleaned.split("\n")
        clause_lines = [l.strip() for l in lines if re.match(r"\s*(ensures|requires)\s+", l)]
        if clause_lines:
            existing = current_spec.replace(" ", "")
            new_clauses = [f"  {c}" for c in clause_lines if c.replace(" ", "") not in existing]
            if new_clauses:
                clause_text = "\n".join(new_clauses)
                brace_pos = current_spec.rfind("{")
                if brace_pos > 0:
                    new_spec = current_spec[:brace_pos] + clause_text + "\n" + current_spec[brace_pos:]
                    print(f"  [REFINE] Applied fix via line extraction: {clause_text}")
                    return new_spec

        print(f"  [REFINE] Could not extract any clauses from fix response")
        return None

    def _print_refinement_summary(self, result: RefinementResult):
        """Print refinement summary."""
        print(f"\n{'='*70}")
        print(f"[REFINEMENT COMPLETE] {result.spec_file}")
        print(f"{'='*70}")
        print(f"  Iterations: {len(result.iterations)}")
        print(f"  Converged: {'[OK] YES' if result.converged else '[FAIL] NO'}")
        print(f"  Total gaps found: {result.total_gaps_found}")
        print(f"  Gaps closed: {result.total_gaps_closed}")
        print(f"  Duration: {result.total_duration_seconds:.1f}s")
        print()
        print(f"  Gap trajectory: {' -> '.join(str(s.gaps_found) for s in result.iterations)}")
        print()
        if result.converged:
            print(f"  Original spec had {result.total_gaps_found} exploitable gaps.")
            print(f"  After {len(result.iterations)} iterations, spec resists adversarial attack.")
        print(f"{'='*70}")


def save_refinement_results(results: list[RefinementResult], output_dir: str):
    """Save refinement results to JSON."""
    os.makedirs(output_dir, exist_ok=True)
    output = []
    for r in results:
        entry = {
            "spec_file": r.spec_file,
            "intent": r.intent,
            "original_spec": r.original_spec,
            "final_spec": r.final_spec,
            "converged": r.converged,
            "total_gaps_found": r.total_gaps_found,
            "total_gaps_closed": r.total_gaps_closed,
            "total_duration_seconds": r.total_duration_seconds,
            "gap_trajectory": [s.gaps_found for s in r.iterations],
            "iterations": [
                {
                    "iteration": s.iteration,
                    "spec_text": s.spec_text,
                    "gaps_found": s.gaps_found,
                    "gaps_details": s.gaps_details,
                    "fix_applied": s.fix_applied,
                    "duration_seconds": s.duration_seconds,
                }
                for s in r.iterations
            ],
        }
        output.append(entry)

    filepath = os.path.join(output_dir, "refinement_results.json")
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n[Refinement results saved to {filepath}]")
    return filepath
