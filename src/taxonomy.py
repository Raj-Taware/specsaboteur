"""Gap Taxonomy — categorize and catalog all discovered spec gaps.

Extracts structured gap patterns from results for:
1. Spec linting (pattern-match new specs against known gaps)
2. Future training data for spec repair models
3. Research contribution (gap classification)
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict


@dataclass
class GapPattern:
    """A categorized specification gap pattern."""
    category: str           # e.g., "missing_permutation", "vacuous_implication"
    subcategory: str         # e.g., "no_element_preservation", "false_antecedent"
    description: str         # Human-readable description
    spec_file: str           # Which spec it was found in
    domain: str              # "dafny" or software domain
    strategy: str            # Which adversarial strategy found it
    exploited_gap: str       # Raw gap description
    suggested_fix: str       # Suggested fix
    severity: str            # "critical", "high", "medium", "low"
    adversarial_code: str    # The adversarial implementation


# Gap category definitions with detection heuristics
GAP_CATEGORIES = {
    "missing_preservation": {
        "keywords": ["permutation", "multiset", "preserv", "element", "lost", "replaced", "destroyed"],
        "description": "Spec doesn't ensure input elements are preserved in output",
        "severity": "critical",
    },
    "vacuous_implication": {
        "keywords": ["vacuous", "implication", "false premise", "antecedent", "always -1", "always returns"],
        "description": "Postcondition is an implication that can be made vacuously true",
        "severity": "high",
    },
    "missing_completeness": {
        "keywords": ["must find", "exists", "completeness", "not found", "miss", "skip"],
        "description": "Spec doesn't require the method to produce a result when one exists",
        "severity": "high",
    },
    "missing_bound": {
        "keywords": ["greater than", "upper bound", "lower bound", "maximum", "minimum", "not in array"],
        "description": "Spec requires a bound property but not that result comes from the input",
        "severity": "medium",
    },
    "missing_negative_case": {
        "keywords": ["negative", "x < 0", "negative input", "absolute"],
        "description": "Spec handles positive case but not negative",
        "severity": "medium",
    },
    "tautological_constraint": {
        "keywords": ["tautolog", "always true", "s >= 0 || s < 0", "vacuously true", "any integer"],
        "description": "Postcondition is a tautology that constrains nothing",
        "severity": "critical",
    },
    "missing_ordering": {
        "keywords": ["first", "last", "order", "minimum index", "earliest", "latest"],
        "description": "Spec doesn't enforce ordering among valid results",
        "severity": "medium",
    },
    "missing_base_case": {
        "keywords": ["empty", "length 0", "length 1", "base case", "length 2"],
        "description": "Spec only constrains base cases, not the general case",
        "severity": "high",
    },
    "token_bypass": {
        "keywords": ["token", "any string", "bearer", "authentication", "validate", "forgery"],
        "description": "Auth spec accepts any token without validation",
        "severity": "critical",
    },
    "empty_response": {
        "keywords": ["empty array", "empty list", "empty response", "no users", "no data"],
        "description": "Response satisfies structural spec with no actual data",
        "severity": "high",
    },
    "case_sensitivity": {
        "keywords": ["case-sensitive", "case-insensitive", "upper", "lower", "duplicate"],
        "description": "Uniqueness constraint is case-sensitive when intent requires case-insensitive",
        "severity": "medium",
    },
    "missing_reentrancy_guard": {
        "keywords": ["reentrancy", "reentrant", "external call", "check-effect", "order of operations"],
        "description": "No reentrancy protection in state-modifying operation",
        "severity": "critical",
    },
    "plaintext_storage": {
        "keywords": ["plaintext", "not hashed", "password", "cleartext", "unencrypted"],
        "description": "Sensitive data stored without encryption/hashing",
        "severity": "critical",
    },
}


def categorize_gap(exploited_gap: str, strategy: str) -> tuple[str, str]:
    """Categorize a gap based on its description.

    Returns (category, severity).
    """
    gap_lower = exploited_gap.lower()

    best_category = "uncategorized"
    best_score = 0

    for cat_name, cat_info in GAP_CATEGORIES.items():
        score = sum(1 for kw in cat_info["keywords"] if kw.lower() in gap_lower)
        if score > best_score:
            best_score = score
            best_category = cat_name

    severity = GAP_CATEGORIES.get(best_category, {}).get("severity", "medium")
    return best_category, severity


def extract_taxonomy_from_results(
    layer1_paths: list[str] = None,
    layer2_paths: list[str] = None,
) -> list[GapPattern]:
    """Extract gap taxonomy from all result files."""
    patterns = []

    # Process Layer 1 (Dafny) results
    for path in (layer1_paths or []):
        if not os.path.exists(path):
            continue
        with open(path) as f:
            data = json.load(f)
        for spec in data:
            for gap in spec.get("gaps", []):
                category, severity = categorize_gap(
                    gap.get("exploited_gap", ""),
                    gap.get("strategy", ""),
                )
                pattern = GapPattern(
                    category=category,
                    subcategory=gap.get("strategy", ""),
                    description=GAP_CATEGORIES.get(category, {}).get("description", "Unknown gap type"),
                    spec_file=spec.get("spec_file", ""),
                    domain="dafny",
                    strategy=gap.get("strategy", ""),
                    exploited_gap=gap.get("exploited_gap", ""),
                    suggested_fix=gap.get("suggested_fix", ""),
                    severity=severity,
                    adversarial_code=gap.get("adversarial_code", ""),
                )
                patterns.append(pattern)

    # Process Layer 2 (Software) results
    for path in (layer2_paths or []):
        if not os.path.exists(path):
            continue
        with open(path) as f:
            data = json.load(f)
        for spec in data:
            for gap in spec.get("gaps", []):
                category, severity = categorize_gap(
                    gap.get("exploited_gap", ""),
                    gap.get("strategy", ""),
                )
                pattern = GapPattern(
                    category=category,
                    subcategory=gap.get("strategy", ""),
                    description=GAP_CATEGORIES.get(category, {}).get("description", "Unknown gap type"),
                    spec_file=spec.get("spec_name", ""),
                    domain=spec.get("domain", "software"),
                    strategy=gap.get("strategy", ""),
                    exploited_gap=gap.get("exploited_gap", ""),
                    suggested_fix=gap.get("suggested_fix", ""),
                    severity=severity,
                    adversarial_code=gap.get("adversarial_code", ""),
                )
                patterns.append(pattern)

    return patterns


def build_taxonomy_report(patterns: list[GapPattern]) -> dict:
    """Build structured taxonomy report from gap patterns."""
    # Group by category
    by_category = defaultdict(list)
    for p in patterns:
        by_category[p.category].append(p)

    # Group by severity
    by_severity = defaultdict(list)
    for p in patterns:
        by_severity[p.severity].append(p)

    # Group by domain
    by_domain = defaultdict(list)
    for p in patterns:
        by_domain[p.domain].append(p)

    # Build report
    report = {
        "total_gaps": len(patterns),
        "categories": {
            cat: {
                "count": len(gaps),
                "description": GAP_CATEGORIES.get(cat, {}).get("description", "Unknown"),
                "severity": GAP_CATEGORIES.get(cat, {}).get("severity", "medium"),
                "specs_affected": list(set(g.spec_file for g in gaps)),
                "strategies_used": list(set(g.strategy for g in gaps)),
            }
            for cat, gaps in sorted(by_category.items(), key=lambda x: -len(x[1]))
        },
        "severity_distribution": {
            sev: len(gaps)
            for sev, gaps in sorted(by_severity.items())
        },
        "domain_distribution": {
            dom: len(gaps)
            for dom, gaps in sorted(by_domain.items())
        },
        "training_data": [
            {
                "category": p.category,
                "severity": p.severity,
                "domain": p.domain,
                "spec_file": p.spec_file,
                "exploited_gap": p.exploited_gap,
                "suggested_fix": p.suggested_fix,
                "adversarial_code": p.adversarial_code,
                "strategy": p.strategy,
            }
            for p in patterns
        ],
    }

    return report


def save_taxonomy(report: dict, output_dir: str):
    """Save taxonomy report to JSON."""
    os.makedirs(output_dir, exist_ok=True)

    filepath = os.path.join(output_dir, "gap_taxonomy.json")
    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[Gap taxonomy saved to {filepath}]")

    # Print summary
    print(f"\n{'='*60}")
    print(f"GAP TAXONOMY SUMMARY")
    print(f"{'='*60}")
    print(f"Total gaps cataloged: {report['total_gaps']}")
    print(f"\nBy category:")
    for cat, info in report["categories"].items():
        print(f"  {cat}: {info['count']} gaps [{info['severity']}]")
        print(f"    {info['description']}")
    print(f"\nBy severity:")
    for sev, count in report["severity_distribution"].items():
        print(f"  {sev}: {count}")
    print(f"\nTraining data entries: {len(report['training_data'])}")
    print(f"  -> Ready for future spec-repair model fine-tuning")
    print(f"{'='*60}")

    return filepath
