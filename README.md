<div align="center">

# SpecSaboteur

### Adversarial Specification Validation for Secure Program Synthesis

*Your spec passed verification. But is it actually correct?*

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Dafny](https://img.shields.io/badge/dafny-4.x-orange.svg)](https://github.com/dafny-lang/dafny)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Hackathon](https://img.shields.io/badge/Apart%20Research-Hackathon%202026-purple.svg)](https://www.apartresearch.com/)

[Overview](#-overview) &bull; [How It Works](#-how-it-works) &bull; [Quick Start](#-quick-start) &bull; [Results](#-results) &bull; [Architecture](#-architecture) &bull; [Examples](#-examples) &bull; [FAQ](#-faq)

---

</div>

## The Problem

Formal verification proves that an implementation matches its specification. But **who verifies the specification itself?**

A sorting function spec that says *"output must be sorted"* — without requiring elements are preserved — lets an adversarial implementation **replace everything with zeros** and still pass verification. The spec is formally satisfied. The code is formally verified. **And the program is completely wrong.**

This gap between what specs *say* and what they *mean* is the specification adequacy problem. In an era of AI-generated code, it's the critical bottleneck for secure program synthesis.

## Overview

**SpecSaboteur** finds gaps in formal specifications by generating *adversarial implementations* — programs that formally satisfy every constraint but violate the intended behavior. Each verified adversarial implementation is a **concrete, proven specification gap**.

```
   "Sort array ascending,        method Sort(a: array<int>)
    preserving elements"           modifies a
                                   ensures forall i :: 0 <= i < a.Length - 1
         NL Intent          +              ==> a[i] <= a[i+1]
                                   // MISSING: multiset(a[..]) == multiset(old(a[..]))

                                          Formal Spec
                                              |
                    +-------------------------+
                    |
                    v
        SpecSaboteur generates:
        
        a[0] := 0; a[1] := 1; a[2] := 2; ...
        
        Replaces all elements with 0,1,2,3...
        Array is sorted. Spec is satisfied.
        ✅ Dafny says: VERIFIED
        ❌ Original elements are gone
        
        GAP FOUND: Missing permutation preservation
        FIX: ensures multiset(a[..]) == multiset(old(a[..]))
```

> **The dual of correctness checking:** instead of asking *"does this implementation satisfy the spec?"*, we ask *"can a **wrong** implementation satisfy this spec?"*

## How It Works

SpecSaboteur operates in two layers:

### Layer 1: Formal Verification (Dafny)

The rigorous core. Adversarial implementations are verified by the Dafny theorem prover — if Dafny says it satisfies the spec, it provably does. No heuristics, no approximations.

```
NL Intent + Formal Spec
        |
        v
[Adversarial Impl Generator]  ──→  [Dafny Verifier]
        (LLM)                            |
                               ┌─────────┴─────────┐
                               │                    │
                          VERIFIED              REJECTED
                       (Spec gap!)          (Spec caught it)
                               │
                               v
                    [Gap Reporter + Fix Suggester]
```

### Layer 2: Software Spec Extension (LLM-as-Judge)

Extends the concept to real-world software specifications — REST APIs, smart contracts, auth systems, database schemas. Uses LLM evaluation instead of formal verification, trading soundness for breadth.

| Domain | Example Gap Found |
|--------|-------------------|
| **REST API** | Spec says "returns user list" — empty array satisfies it |
| **Smart Contract** | Spec says "balances change" — no reentrancy guard required |
| **Auth/RBAC** | Spec says "token required" — any string accepted as valid |
| **Database** | Spec says "email UNIQUE" — case-sensitive allows duplicates |

## Quick Start

### Prerequisites

- Python 3.12+
- [Dafny](https://github.com/dafny-lang/dafny) (`dotnet tool install -g dafny`)
- Gemini API key (free tier) or local model via Ollama/vLLM

### Installation

```bash
git clone https://github.com/Raj-Taware/specsaboteur.git
cd specsaboteur
pip install -r requirements.txt
```

### Set up your LLM

```bash
# Option A: Gemini (free tier)
export GEMINI_API_KEY="your-key-here"

# Option B: Local model via Ollama
ollama pull qwen2.5-coder:32b

# Option C: Qwen on H100 via vLLM
# python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-Coder-32B-Instruct
```

### Run

```bash
# Attack all weak specs (Layer 1 + Layer 2)
python run.py

# Layer 1 only (Dafny formal verification)
python run.py --layer 1

# Layer 2 only (software specs)
python run.py --layer 2

# Use a specific LLM provider
python run.py --provider ollama --model qwen2.5-coder:32b
python run.py --provider openai --base-url http://localhost:8000/v1 --model Qwen/Qwen2.5-Coder-32B-Instruct

# Attack specific spec files
python run.py specs/weak/01_sort.dfy specs/weak/03_max.dfy

# Generate HTML report from existing results
python generate_report.py
```

## Results

### Layer 1: Formal Verification

| Spec | Gaps Found | Strategy | Key Gap |
|------|:----------:|----------|---------|
| **Sort** | 2 | Trivial + Edge | Missing permutation preservation |
| **Binary Search** | 2 | Trivial + Edge | Missing "must find if exists" |
| **Max** | 1 | Trivial | Missing "greater than all" |
| **Abs** | 2 | Trivial + Edge | Missing negative case |
| **Sum** | 1 | Trivial | Tautological postcondition |
| **FindFirst** | — | *(rate limited)* | — |

> **8/8 attacks verified by Dafny. 100% gap detection rate on weak specs.**

### Layer 2: Software Specs

| Domain | Spec | Gaps | Security Impact |
|--------|------|:----:|-----------------|
| REST API | GET /users | 2 | Empty response + token bypass |
| Solidity | ERC-20 transfer | 1 | Reentrancy vulnerability |
| Auth/RBAC | Login + RBAC | 2 | Token forgery + brute force |
| Database | User schema | 2 | Case-insensitive bypass + plaintext passwords |

## Architecture

```
specsaboteur/
├── src/
│   ├── pipeline.py              # Layer 1 orchestrator
│   ├── software_pipeline.py     # Layer 2 orchestrator
│   ├── adversarial_generator.py # Adversarial prompt engineering
│   ├── software_generator.py    # Software-specific adversarial prompts
│   ├── dafny_bridge.py          # Dafny CLI wrapper (verify/compile/run)
│   ├── spec_judge.py            # LLM-as-judge for Layer 2
│   ├── llm_client.py            # Multi-provider LLM abstraction
│   ├── software_spec.py         # YAML spec loader
│   └── report.py                # Unified HTML report generator
├── specs/
│   ├── weak/                    # Dafny specs with known gaps (test targets)
│   ├── strong/                  # Dafny specs with gaps closed (false positive test)
│   └── software/                # Software specs in YAML (Layer 2)
├── reports/                     # Generated HTML reports + JSON results
├── run.py                       # CLI entry point
└── generate_report.py           # Standalone report generator
```

### Adversarial Strategies

| Strategy | What It Does | Best For |
|----------|-------------|----------|
| **Trivial Satisfaction** | Hardcode values satisfying postconditions | Missing input-output relationships |
| **Edge Case Exploitation** | Find boundaries where spec is silent | Missing boundary conditions |
| **Vacuous Satisfaction** | Make implications vacuously true | Overly conditional specs |
| **State Abuse** | Satisfy per-method specs, violate object purpose | Missing object invariants |
| **Security Bypass** *(Layer 2)* | Skip security measures spec doesn't require | Auth, crypto, rate limiting gaps |
| **Data Integrity Violation** *(Layer 2)* | Satisfy schema, violate semantic integrity | Database, state consistency gaps |

### Supported LLM Providers

| Provider | Model | Cost | Setup |
|----------|-------|------|-------|
| **Gemini** | gemini-2.5-flash | Free | `GEMINI_API_KEY` env var |
| **OpenAI-compatible** | Qwen2.5-Coder-32B | Free (H100) | vLLM on GPU server |
| **Ollama** | qwen2.5-coder:32b | Free (local) | `ollama pull` |

## Examples

### Example 1: Sorting — Missing Permutation

```dafny
// Intent: Sort array ascending, PRESERVING all elements
method Sort(a: array<int>)
  modifies a
  ensures forall i :: 0 <= i < a.Length - 1 ==> a[i] <= a[i+1]
  // MISSING: ensures multiset(a[..]) == multiset(old(a[..]))
```

**Adversarial implementation:** Replace all elements with `0, 1, 2, 3...` — sorted, but original elements are destroyed.

**Dafny verdict:** ✅ VERIFIED — the spec is formally satisfied.

**Suggested fix:** `ensures multiset(a[..]) == multiset(old(a[..]))`

### Example 2: Binary Search — Vacuous Implication

```dafny
// Intent: Find target in sorted array, return index or -1
method BinarySearch(a: array<int>, target: int) returns (index: int)
  requires forall i :: 0 <= i < a.Length - 1 ==> a[i] <= a[i+1]
  ensures index >= 0 ==> 0 <= index < a.Length && a[index] == target
  // MISSING: ensures (exists i :: ... a[i] == target) ==> index >= 0
```

**Adversarial implementation:** `index := -1` — always returns "not found."

**Why it verifies:** The ensures clause is `index >= 0 ==> ...` — when index is -1, the premise is false, making the implication vacuously true.

### Example 3: Auth System — Token Forgery (Layer 2)

```yaml
# Spec says "Bearer token required" but doesn't define validation
Authentication:
  - Token must be present in Authorization header
```

**Adversarial implementation:** Accept ANY string as a valid token. `Bearer fakefakefake` grants full access.

**Gap:** No requirement for cryptographic signature verification, expiry checking, or issuer validation.

## Theoretical Contribution

SpecSaboteur introduces **adversarial implementation synthesis** — a new approach that connects two fields:

- **Formal Methods:** The dual of [CEGIS](https://en.wikipedia.org/wiki/Counterexample-guided_abstraction_refinement) — instead of using counterexamples to refine *implementations*, we use adversarial implementations to refine *specifications*
- **AI Safety:** Applies the concept of [specification gaming](https://deepmind.google/discover/blog/specification-gaming-the-flip-side-of-ai-ingenuity/) to formal program specifications

> *"An unspecified program can't be incorrect, only surprising."* — SpecSaboteur automates finding those surprises.

## Limitations

We believe in honest science. Here's what SpecSaboteur can't do:

- **False negatives:** LLM may miss spec gaps. Finding gaps ≠ proving absence of gaps.
- **Dafny-specific (Layer 1):** Concept generalizes to any spec language with a verifier (Lean, Coq, F*), but current implementation targets Dafny.
- **LLM-as-judge is weaker (Layer 2):** Not formally sound. Behavioral tests are the ground truth.
- **Adversarial creativity is bounded** by LLM capability and prompt strategy.
- **Rate limits:** Free-tier Gemini constrains throughput (~10-15 RPM).

## Acknowledgments

- **[Apart Research](https://www.apartresearch.com/)** & **[Atlas Computing](https://atlascomputing.org/)** — Hackathon organizers
- **[Atlas formal-specification-ide](https://github.com/atlas-computing-org/formal-specification-ide)** — Complementary spec writing tool
- **[Dafny](https://github.com/dafny-lang/dafny)** — Verification language and theorem prover
- **[Google Gemini](https://ai.google.dev/)** — Free-tier LLM for adversarial generation

## License

MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

**SpecSaboteur** — *Apart Research Hackathon 2026 | Secure Program Synthesis Track*

Built with adversarial intent (for good).

</div>
