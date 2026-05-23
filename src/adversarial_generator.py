"""Adversarial implementation generator — the core of SpecSaboteur."""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Strategy(Enum):
    TRIVIAL_SATISFACTION = "trivial_satisfaction"
    EDGE_CASE_EXPLOITATION = "edge_case_exploitation"
    VACUOUS_SATISFACTION = "vacuous_satisfaction"
    STATE_ABUSE = "state_abuse"


@dataclass
class AdversarialImpl:
    code: str
    strategy: Strategy
    explanation: str  # Why this is adversarial
    exploited_gap: str  # What spec gap was exploited
    verified: Optional[bool] = None
    verification_output: str = ""
    is_adversarial: Optional[bool] = None  # Confirmed by behavioral test


STRATEGY_PROMPTS = {
    Strategy.TRIVIAL_SATISFACTION: """Your goal: Write a Dafny implementation that SATISFIES all the formal constraints
(requires/ensures/modifies/invariants) but does NOT do what the natural language intent describes.

Strategy: TRIVIAL SATISFACTION
- Return hardcoded values that satisfy the postconditions
- Ignore the input entirely if possible
- Use the simplest possible implementation that makes the verifier happy
- Do NOT implement the actual algorithm described in the intent

Think about what the postconditions literally require vs what the intent means.
The gap between literal formal requirements and intended behavior is what you exploit.""",

    Strategy.EDGE_CASE_EXPLOITATION: """Your goal: Write a Dafny implementation that SATISFIES all the formal constraints
(requires/ensures/modifies/invariants) but does NOT do what the natural language intent describes.

Strategy: EDGE CASE EXPLOITATION
- Find inputs or boundary conditions where the spec is silent
- Implement behavior that is correct for most inputs but wrong at boundaries
- Look for missing constraints about edge cases (empty arrays, zero values, overflow)
- Exploit any gap between what the spec says and what a correct implementation should do

Focus on what the specification DOESN'T say about edge cases.""",

    Strategy.VACUOUS_SATISFACTION: """Your goal: Write a Dafny implementation that SATISFIES all the formal constraints
(requires/ensures/modifies/invariants) but does NOT do what the natural language intent describes.

Strategy: VACUOUS SATISFACTION
- Look for preconditions (requires) that might be overly strong
- Find ways to make postconditions vacuously true
- If a postcondition is an implication (A ==> B), try to make A always false
- Exploit conditional ensures clauses by never triggering the condition

Focus on logical structure of the spec, not the algorithm.""",

    Strategy.STATE_ABUSE: """Your goal: Write a Dafny implementation that SATISFIES all the formal constraints
(requires/ensures/modifies/invariants) but does NOT do what the natural language intent describes.

Strategy: STATE ABUSE
- If the spec involves a class/object, satisfy per-method specs but violate the object's semantic purpose
- Implement a different data structure that happens to satisfy the same formal constraints
- Use internal state in ways the spec doesn't prevent but the intent wouldn't allow
- Satisfy size/count constraints without preserving the right data

Focus on what the spec says about state vs what the intent means for the object's purpose."""
}


def build_adversarial_prompt(intent: str, spec: str, strategy: Strategy) -> str:
    """Build the prompt for adversarial implementation generation."""
    return f"""You are a specification auditor. Your job is to find gaps in formal specifications
by generating implementations that technically satisfy the spec but violate the intended behavior.

{STRATEGY_PROMPTS[strategy]}

## Natural Language Intent
{intent}

## Dafny Specification
```dafny
{spec}
```

## Your Task
1. Analyze what the spec LITERALLY requires vs what the intent MEANS
2. Find a gap — something the intent requires but the spec doesn't enforce
3. Write a COMPLETE Dafny implementation that:
   - Passes the Dafny verifier (all requires/ensures satisfied)
   - Does NOT correctly implement the intent
4. Include all necessary loop invariants, decreases clauses, and assertions

## Output Format
Return ONLY a JSON object with these fields:
```json
{{
    "code": "// Complete Dafny file with method signature, spec, AND implementation body",
    "explanation": "Why this implementation is adversarial (what it does wrong)",
    "exploited_gap": "What specific constraint is missing from the spec"
}}
```

IMPORTANT: The code must be a COMPLETE Dafny file that compiles and verifies.
Include the full method signature with requires/ensures clauses AND the implementation body.
Do not use placeholder comments — write actual executable Dafny code."""


def build_retry_prompt(
    intent: str, spec: str, strategy: Strategy,
    previous_code: str, errors: list[str]
) -> str:
    """Build retry prompt with verification error feedback."""
    return f"""Your previous adversarial implementation failed Dafny verification.
Fix the errors while keeping the adversarial behavior.

## Natural Language Intent
{intent}

## Dafny Specification
```dafny
{spec}
```

## Previous Implementation (FAILED)
```dafny
{previous_code}
```

## Verification Errors
{chr(10).join(errors)}

## Fix Instructions
1. Fix ONLY the verification errors
2. Keep the adversarial behavior (the implementation should still NOT do what the intent says)
3. Add/fix loop invariants, decreases clauses, or assertions as needed
4. Make sure the code compiles AND verifies

Return ONLY a JSON object:
```json
{{
    "code": "// Fixed complete Dafny file",
    "explanation": "Why this implementation is adversarial",
    "exploited_gap": "What specific constraint is missing from the spec"
}}
```"""


def parse_llm_response(response_text: str) -> Optional[AdversarialImpl]:
    """Parse LLM response into AdversarialImpl."""
    # Try to extract JSON from response
    # Handle markdown code blocks
    json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try raw JSON
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            return None

    try:
        data = json.loads(json_str)
        # Extract code from potential markdown blocks within the JSON
        code = data.get("code", "")
        if "```dafny" in code:
            code_match = re.search(r"```dafny\s*(.*?)\s*```", code, re.DOTALL)
            if code_match:
                code = code_match.group(1)
        elif "```" in code:
            code_match = re.search(r"```\s*(.*?)\s*```", code, re.DOTALL)
            if code_match:
                code = code_match.group(1)

        return AdversarialImpl(
            code=code,
            strategy=Strategy.TRIVIAL_SATISFACTION,  # Will be set by caller
            explanation=data.get("explanation", ""),
            exploited_gap=data.get("exploited_gap", "")
        )
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[AdversarialGen] Failed to parse LLM response: {e}")
        # Try to extract code directly
        code_match = re.search(r"```dafny\s*(.*?)\s*```", response_text, re.DOTALL)
        if code_match:
            return AdversarialImpl(
                code=code_match.group(1),
                strategy=Strategy.TRIVIAL_SATISFACTION,
                explanation="(extracted from non-JSON response)",
                exploited_gap="(unknown)"
            )
        return None
