<div align="center">

# SpecSaboteur

### Adversarial Specification Validation for Secure Program Synthesis

*Your spec passed verification. But is it actually correct?*

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Dafny](https://img.shields.io/badge/dafny-4.x-orange.svg)](https://github.com/dafny-lang/dafny)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Hackathon](https://img.shields.io/badge/Apart%20Research-Secure%20Program%20Synthesis-purple.svg)](https://www.apartresearch.com/)

[Why This Matters](#-why-this-matters) &bull; [How It Works](#-how-it-works) &bull; [Results](#-results) &bull; [Quick Start](#-quick-start) &bull; [Examples](#-examples) &bull; [Limitations](#-limitations)

---

</div>

## Why This Matters

The bottleneck in trustworthy software is no longer writing code — it's **specifying what the code should do and verifying it does it**. Formal verification proves implementations match specifications. But if the specification itself is incomplete, verified code can still be wrong.

This isn't hypothetical. A sorting spec that says *"output must be sorted"* without requiring element preservation lets an adversary **replace everything with zeros** — and Dafny says ✅ VERIFIED. An auth spec that says *"token required in header"* without defining validation lets an adversary **accept any string as a valid token**. The spec is satisfied. The system is compromised.

As AI-generated code scales, spec adequacy becomes the critical attack surface. **SpecSaboteur closes this gap.**

### The Insight

> *Instead of asking "does this implementation satisfy the spec?", ask "can a **wrong** implementation satisfy this spec?"*

This is the **dual of CEGIS** (counterexample-guided inductive synthesis). Where CEGIS uses counterexamples to refine implementations, SpecSaboteur uses adversarial implementations to refine specifications. It connects formal methods with [specification gaming](https://deepmind.google/discover/blog/specification-gaming-the-flip-side-of-ai-ingenuity/) from AI safety — applied to program specifications rather than reward functions.

## How It Works

SpecSaboteur generates **"malicious compliance" implementations** — programs that satisfy every formal constraint while violating the natural-language intent. Each verified adversarial implementation is a concrete, proven spec gap.

```
   NL Intent                    Formal Spec
       |                            |
       v                            v
  "Sort ascending,         ensures sorted order
   preserve elements"      // MISSING: permutation
                                    |
                    SpecSaboteur generates:
                    a[0]:=0; a[1]:=1; a[2]:=2; ...
                                    |
                           Dafny: ✅ VERIFIED
                           Intent: ❌ VIOLATED
                                    |
                           GAP CONFIRMED
                           Fix: ensures multiset(a[..]) == multiset(old(a[..]))
```

### Two Layers

**Layer 1 — Formal Verification (Dafny):** The rigorous core. Adversarial implementations are verified by the Dafny theorem prover backed by the Z3 SMT solver. If Dafny says it satisfies the spec, it provably does. No heuristics.

**Layer 2 — Software Spec Extension (LLM-as-Judge):** Extends the concept to real-world software specs — REST APIs, smart contracts, auth systems, database schemas. Uses LLM evaluation instead of formal verification, trading soundness for breadth across domains where formal specs don't exist.

### Three-Tier Benchmark

Each spec exists in three tiers to measure gap detection sensitivity:

| Tier | Design | Expected Result |
|------|--------|-----------------|
| **Weak** | Missing major constraints | Many gaps found |
| **Medium** | Closes obvious gap, leaves subtle one | Some gaps found |
| **Strong** | Fully constrained | No gaps found |

## Results

### Layer 1: Formal Verification (Dafny)

Adversarial implementations verified by the Dafny theorem prover — **mathematically proven** to satisfy the spec while violating intent.

#### Weak Specs (6 specs, 2 strategies each)

| Spec | Gaps | Strategy | Key Gap Found |
|------|:----:|----------|---------------|
| Sort | 2 | Trivial + Edge | Missing permutation preservation |
| Binary Search | 2 | Trivial + Edge | Missing "must find if exists" guarantee |
| Max | 1 | Trivial | Missing "greater than all elements" |
| Abs | 2 | Trivial + Edge | Missing negative input case |
| Sum | 1 | Trivial | Tautological postcondition (`s >= 0 || s < 0`) |
| FindFirst | 0 | *(rate limited)* | — |

> **8 adversarial implementations verified by Dafny. 100% gap detection on attacked specs.**

#### Medium Specs (6 specs, 2 strategies each)

| Spec | Gaps | Key Gap Found |
|------|:----:|---------------|
| Sort | 0 | Medium spec resisted attack |
| Binary Search | 0 | Medium spec resisted attack |
| Max | 0 | Attempted, couldn't verify |
| **Abs** | **2** | Returns 0 for negative inputs (missing `x < 0 ==> result == -x`) |
| **Sum** | **1** | Returns 0 for length ≥ 2 arrays (no constraint beyond base cases) |
| **FindFirst** | **1** | Returns LAST occurrence instead of first (missing minimality) |

> **4 gaps found on medium specs — subtle gaps detected where obvious ones were closed.**

#### Strong Specs (6 specs, 2 strategies each)

| Result | Details |
|--------|---------|
| **0 gaps found** | LLM could not generate any adversarial implementation that satisfies the strengthened specs |

> Strong specs resist adversarial attack — validating the three-tier benchmark design.

### Layer 2: Software Specs (LLM-as-Judge)

| Tier | Specs | Gaps Found | Details |
|------|:-----:|:----------:|---------|
| **Weak** | 4 | 1 | REST API: empty response satisfies "returns users array" |
| **Medium** | 4 | 2 | REST API + Solidity reentrancy gap |
| **Strong** | 4 | 2 | REST API + Solidity gaps persist (LLM judge less discriminating) |

### Combined Results Summary

| | Weak | Medium | Strong |
|---|:---:|:---:|:---:|
| **Layer 1 (Dafny)** | **8 gaps** (67%) | **4 gaps** (33%) | **0 gaps** (0%) |
| **Layer 2 (Software)** | 1 gap | 2 gaps | 2 gaps |

**Layer 1 monotonic gradient confirmed:** weaker specs produce more gaps, stronger specs resist attack. Layer 2 shows LLM-as-Judge limitations: strong-tier software specs still admit adversarial impls (REST API + Solidity). SpecSaboteur functions as both a **spec strength metric** and a **judge-quality diagnostic**.

### Iterative Refinement: Attack → Fix → Converge

The core demo: weak specs are iteratively strengthened through adversarial feedback until no gaps remain.

| Spec | Gap Trajectory | Iterations | Fix Applied |
|------|:--------------:|:----------:|-------------|
| Sort | 2 → 0 | 2 | `ensures multiset(a[..]) == old(multiset(a[..]))` |
| Binary Search | 1 → 0 | 2 | `ensures (exists k :: ...) ==> index >= 0` |
| Max | 2 → 0 | 2 | `ensures forall j :: 0 <= j < a.Length ==> a[j] <= m` |
| Abs | 2 → 0 | 2 | `ensures x < 0 ==> result == -x` |
| Sum | 1 → 0 | 2 | `ensures s == sum i :: 0 <= i < a.Length :: a[i]` |

> **100% convergence.** Every attacked weak spec was automatically strengthened to resist adversarial attack within 2 iterations. This is **CEGIS inverted** — counterexample-guided specification refinement.

### Gap Taxonomy

All 12 discovered gaps are automatically categorized into a structured taxonomy:

| Category | Count | Severity | Description |
|----------|:-----:|----------|-------------|
| Missing Preservation | 3 | Critical | Input elements not preserved in output |
| Missing Reentrancy Guard | 2 | Critical | No protection against reentrant state changes |
| Tautological Constraint | 1 | Critical | Postcondition constrains nothing |
| Missing Negative Case | 2 | Medium | Spec handles positive case but not negative |
| Missing Bound | 1 | Medium | Bound not tied to input domain |
| Uncategorized (API-specific) | 3 | Medium | Domain-specific gaps (REST API, auth) |

This taxonomy serves as training data for future spec-repair models (see [Future Work](#future-work)).

## Quick Start

### Prerequisites

- Python 3.12+
- [Dafny](https://github.com/dafny-lang/dafny) (`dotnet tool install -g dafny`)
- LLM provider (see below)

### Installation

```bash
git clone https://github.com/Raj-Taware/specsaboteur.git
cd specsaboteur
pip install -r requirements.txt
```

### LLM Setup

```bash
# Option A: Gemini (free tier)
export GEMINI_API_KEY="your-key-here"

# Option B: Local model via Ollama
ollama pull qwen2.5-coder:32b-instruct
```

### Run

```bash
# Attack all weak specs (both layers)
python run.py

# Layer 1 only (Dafny formal verification)
python run.py --layer 1

# Layer 2 only (software specs)
python run.py --layer 2 --software-specs specs/software_weak

# Use Ollama
python run.py --provider ollama --model qwen2.5-coder:32b-instruct

# Attack specific specs
python run.py specs/weak/01_sort.dfy specs/weak/03_max.dfy

# Iterative refinement: attack → fix → re-attack → converge
python run.py specs/weak/01_sort.dfy --refine --refine-iters 5

# Statistical sampling (N=5 trials per spec for Layer 2)
python run.py --sample --sample-trials 5 --software-specs specs/software_weak

# Extract gap taxonomy from existing results
python run.py --taxonomy

# Generate HTML report
python generate_report.py
```

## Architecture

```
specsaboteur/
├── src/
│   ├── pipeline.py              # Layer 1 orchestrator
│   ├── software_pipeline.py     # Layer 2 orchestrator
│   ├── adversarial_generator.py # Adversarial prompt engineering
│   ├── software_generator.py    # Software-domain adversarial prompts
│   ├── dafny_bridge.py          # Dafny CLI wrapper (verify/compile/run)
│   ├── spec_judge.py            # LLM-as-judge for Layer 2
│   ├── refinement.py            # Iterative spec refinement loop
│   ├── sampling.py              # Statistical sampling for Layer 2
│   ├── taxonomy.py              # Gap categorization + training data
│   ├── llm_client.py            # Multi-provider LLM abstraction
│   ├── software_spec.py         # YAML spec loader
│   └── report.py                # Unified HTML report generator
├── specs/
│   ├── weak/                    # Dafny specs with known gaps
│   ├── medium/                  # Dafny specs with subtle gaps
│   ├── strong/                  # Dafny specs fully constrained
│   ├── software_weak/           # Software specs (YAML) — weak tier
│   ├── software_medium/         # Software specs — medium tier
│   └── software_strong/         # Software specs — strong tier
├── reports/                     # Generated results (JSON + HTML)
├── run.py                       # CLI entry point
└── generate_report.py           # Standalone report generator
```

### Adversarial Strategies

| Strategy | What It Does | Targets |
|----------|-------------|---------|
| **Trivial Satisfaction** | Hardcode values satisfying postconditions | Missing input-output relationships |
| **Edge Case Exploitation** | Find boundaries where spec is silent | Missing boundary conditions |
| **Security Bypass** *(L2)* | Skip security measures spec doesn't require | Auth, crypto, rate limiting gaps |
| **Data Integrity Violation** *(L2)* | Satisfy schema, violate semantic constraints | Database, state consistency gaps |

### Supported Models

| Provider | Model | Setup |
|----------|-------|-------|
| **Gemini** | gemini-2.5-flash | `GEMINI_API_KEY` env var |
| **Ollama** | qwen2.5-coder:32b-instruct | `ollama pull` |
| **OpenAI-compatible** | Any model via vLLM/TGI | `--provider openai --base-url` |

## Examples

### Example 1: Sorting — Missing Permutation

```dafny
// Intent: Sort array ascending, PRESERVING all elements
method Sort(a: array<int>)
  modifies a
  ensures forall i :: 0 <= i < a.Length - 1 ==> a[i] <= a[i+1]
  // MISSING: ensures multiset(a[..]) == multiset(old(a[..]))
```

**Adversarial impl:** Replace all elements with `0, 1, 2, 3...` — sorted, but original elements destroyed.

**Dafny verdict:** ✅ VERIFIED. **Suggested fix:** `ensures multiset(a[..]) == multiset(old(a[..]))`

### Example 2: Binary Search — Vacuous Implication

```dafny
method BinarySearch(a: array<int>, target: int) returns (index: int)
  requires forall i :: 0 <= i < a.Length - 1 ==> a[i] <= a[i+1]
  ensures index >= 0 ==> 0 <= index < a.Length && a[index] == target
```

**Adversarial impl:** `index := -1` — always returns "not found."

**Why it verifies:** `index >= 0 ==> ...` is vacuously true when index is -1. The spec never requires the method to actually find existing targets.

### Example 3: Auth System — Token Forgery (Layer 2)

```yaml
Authentication:
  - Token must be present in Authorization header
```

**Adversarial impl:** Accept ANY string as valid token. `Bearer fakefakefake` grants full access.

**Gap:** No requirement for signature verification, expiry checking, or issuer validation.

## Theoretical Contribution

**Adversarial implementation synthesis** is a new validation technique connecting two fields:

- **Formal Methods:** The dual of [CEGIS](https://en.wikipedia.org/wiki/Counterexample-guided_abstraction_refinement) — adversarial implementations refine specifications, not implementations
- **AI Safety:** [Specification gaming](https://deepmind.google/discover/blog/specification-gaming-the-flip-side-of-ai-ingenuity/) applied to formal program specifications rather than reward functions

**The elegance of the duality:** The structural inversion is precise. In CEGIS, the spec is fixed and the implementation converges toward correctness. In CEGIS-Dual, the implementation is a disposable probe and the *specification* converges toward adequacy. The verifier serves the same role in both — as an oracle separating the search space — but the refinement target rotates 180°. The gap taxonomy is the spec-domain analogue of counterexample traces: same feedback structure, same convergence mechanism, applied to the dual problem. Our empirical convergence (≤2 iterations across all specs) suggests specifications have a finite attack surface that adversarial pressure can exhaust.

**Relation to Atlas Computing's work:** Atlas's [formal-specification-ide](https://github.com/atlas-computing-org/formal-specification-ide) helps write and annotate specs. SpecSaboteur validates them. Together they close the spec lifecycle: write → validate → strengthen → verify.

## Limitations

- **False negatives:** LLM may miss gaps. Finding gaps ≠ proving their absence.
- **Dafny-specific (Layer 1):** Concept generalizes to Lean, Coq, F* — current impl targets Dafny.
- **LLM-as-judge is not sound (Layer 2):** Useful for real-world software domains but lacks formal guarantees.
- **Adversarial creativity bounded** by LLM capability and prompt strategy.

## Future Work

### Spec Repair via Adversarial Feedback (Dataset Curation)

SpecSaboteur's gap taxonomy produces structured (spec, gap, fix) tuples — training data for **spec-repair models**. The vision:

1. **Curate dataset** from adversarial attacks across large spec corpora (DafnyBench, VERINA)
2. **Fine-tune** a model on (weak_spec, gap_description, strengthened_spec) examples
3. **Deploy as spec linter** — flag likely gaps at write-time using learned patterns

This inverts the current approach: instead of attacking specs post-hoc, prevent gaps during authoring. Not implemented due to compute constraints — the 12-entry taxonomy produced here is a proof of concept. Scaling to DafnyBench's 782 programs would produce a dataset sufficient for fine-tuning.

### Other Directions

- Integration with Atlas formal-specification-ide for write-time validation
- Support for Lean 4 and Coq specifications
- Behavioral test filter: compile adversarial impls, run against test cases for deterministic gap confirmation
- Overconstraining detection: generate correct impls to find specs that reject valid behavior

## License

MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

**SpecSaboteur** — *Apart Research × Atlas Computing · Secure Program Synthesis Hackathon 2026*

Specification Validation Track

</div>
