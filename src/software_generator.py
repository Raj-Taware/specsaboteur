"""Adversarial implementation generator for software specs (Layer 2)."""

import json
import re
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from .llm_client import LLMClient
from .software_spec import SoftwareSpec


@dataclass
class SoftwareAdversarialImpl:
    """An adversarial implementation for a software spec."""
    code: str
    language: str
    strategy: str
    explanation: str
    exploited_gap: str


SOFTWARE_ADVERSARIAL_PROMPT = """You are a specification auditor for software systems.
Your job is to find gaps in specifications by generating implementations that
technically satisfy every stated requirement but violate the intended behavior.

## Strategy: {strategy_desc}

## Natural Language Intent
{intent}

## Software Specification
{spec_text}

## Target Language
{language}

## Your Task
Write a COMPLETE, RUNNABLE implementation in {language} that:
1. Satisfies every requirement LITERALLY stated in the specification
2. Does NOT correctly implement the intended behavior
3. Would pass a compliance audit against the spec text
4. Would FAIL behavioral testing against the intent

Think about what the specification LITERALLY says vs what it MEANS.

## Output Format
Return ONLY a JSON object:
```json
{{
    "code": "// Complete runnable implementation in {language}",
    "explanation": "Why this implementation is adversarial (what it does wrong)",
    "exploited_gap": "What specific requirement is missing from the spec"
}}
```

IMPORTANT: The code must be complete and syntactically valid {language}.
Include imports, class definitions, function signatures — everything needed to run."""


STRATEGY_DESCRIPTIONS = {
    "trivial_satisfaction": """TRIVIAL SATISFACTION
- Return hardcoded/minimal values satisfying the spec's output format
- Ignore inputs, skip actual computation
- If spec says "returns a list" — return empty list
- If spec says "returns user object" — return minimal valid object""",

    "edge_case_exploitation": """EDGE CASE EXPLOITATION
- Find inputs where the spec is silent about expected behavior
- Implement behavior that works for common cases but fails at boundaries
- Exploit case sensitivity, null handling, type coercion
- Look for security-relevant gaps (auth bypass, injection, race conditions)""",

    "security_bypass": """SECURITY BYPASS
- Satisfy functional requirements but skip security measures
- Implement auth that accepts any token
- Skip input validation the spec doesn't explicitly require
- Ignore rate limiting, CSRF protection, encryption requirements
- Focus on what the spec says about security vs what a secure impl needs""",

    "data_integrity_violation": """DATA INTEGRITY VIOLATION
- Satisfy schema constraints but violate semantic data integrity
- Allow inconsistent state between related tables/objects
- Skip cascade operations the spec doesn't mention
- Violate invariants that aren't formally specified"""
}


def generate_software_adversarial(
    llm: LLMClient,
    spec: SoftwareSpec,
    strategy: str = "trivial_satisfaction"
) -> Optional[SoftwareAdversarialImpl]:
    """Generate adversarial implementation for a software spec."""
    strategy_desc = STRATEGY_DESCRIPTIONS.get(strategy, STRATEGY_DESCRIPTIONS["trivial_satisfaction"])

    prompt = SOFTWARE_ADVERSARIAL_PROMPT.format(
        strategy_desc=strategy_desc,
        intent=spec.intent,
        spec_text=spec.spec_text,
        language=spec.language
    )

    try:
        response = llm.generate(prompt, temperature=0.7)
        return _parse_response(response, spec.language, strategy)
    except Exception as e:
        print(f"  [SoftwareGen] Generation failed: {e}")
        return None


def _parse_response(
    response: str, language: str, strategy: str
) -> Optional[SoftwareAdversarialImpl]:
    """Parse LLM response into SoftwareAdversarialImpl."""
    # Try JSON extraction
    json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            return None

    try:
        data = json.loads(json_str)
        code = data.get("code", "")
        # Clean markdown code blocks from within JSON
        for lang_tag in [f"```{language}", "```python", "```solidity", "```sql", "```"]:
            if lang_tag in code:
                code_match = re.search(r"```\w*\s*(.*?)\s*```", code, re.DOTALL)
                if code_match:
                    code = code_match.group(1)
                    break

        return SoftwareAdversarialImpl(
            code=code,
            language=language,
            strategy=strategy,
            explanation=data.get("explanation", ""),
            exploited_gap=data.get("exploited_gap", "")
        )
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  [SoftwareGen] Parse failed: {e}")
        return None
