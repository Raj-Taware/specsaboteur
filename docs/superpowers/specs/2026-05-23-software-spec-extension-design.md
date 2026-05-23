# SpecSaboteur v2: Software Spec Extension Design

## Problem
SpecSaboteur finds spec gaps via adversarial impls verified by Dafny. Works great for algorithm specs. Real software (APIs, auth, databases) doesn't use Dafny. How to extend?

## Decision: Hybrid Architecture

### Layer 1: Formal Core (existing)
- Dafny specs -> adversarial impl -> Dafny verifier -> confirmed gap
- Keeps formal soundness (key differentiator)
- Algorithm domain: sort, search, max, stack, bank, findFirst

### Layer 2: Software Spec Demo (new)
- Software specs (OpenAPI, Solidity, access control, SQL) as structured text
- LLM generates adversarial impl in target language (Python/JS/Solidity)
- LLM-as-judge evaluates: "does this impl satisfy the spec literally?"
- Behavioral test confirms adversarial behavior (deterministic ground truth)
- **Explicitly labeled as concept extension — honest about weaker guarantees**

### Why Hybrid
- Formal core → Execution Quality score (sound methodology)
- Demo layer → Impact/Innovation score (broader applicability vision)
- Honest framing → Presentation/Clarity score (acknowledges limitations)

## Layer 2 Pipeline

```
Software Spec (text) + NL Intent
    |
    v
[Adversarial Impl Generator]  → generates Python/JS/Solidity code
    |
    v
[LLM Judge]  → "does this impl satisfy the spec text literally?"
    |
    +--> YES → [Behavioral Test] → FAIL = confirmed gap
    |                            → PASS = legit alternative
    +--> NO → spec caught attack
```

## Demo Domains (4)

### 1. REST API Contracts
- Spec: OpenAPI-style endpoint description
- Example: "GET /users returns paginated list, 401 on bad auth"
- Adversarial: returns empty array always (satisfies "returns list")
- Gap: missing "returns ALL matching users" constraint

### 2. Smart Contracts (Solidity)
- Spec: ERC-20 transfer function constraints
- Example: "transfer decreases sender balance by amount"
- Adversarial: allows reentrancy, no mutex
- Gap: missing reentrancy guard requirement

### 3. Auth/Access Control
- Spec: RBAC policy text
- Example: "admin can delete users, regular users can view"
- Adversarial: checks role but doesn't validate token expiry
- Gap: missing authentication freshness requirement

### 4. Database Schema
- Spec: Schema constraints + migration description
- Example: "email must be unique, users table"
- Adversarial: adds unique index but allows NULL emails (NULL != NULL in SQL)
- Gap: missing NOT NULL constraint specification

## New Components

### `src/software_spec.py`
- `SoftwareSpec` dataclass: intent, spec_text, language, domain, test_cases
- `load_software_specs()`: reads from `specs/software/` directory
- Spec file format: YAML with intent, spec, language, expected_behavior fields

### `src/software_generator.py`
- Adapts adversarial prompts for non-Dafny languages
- Same strategies (trivial satisfaction, edge case exploitation)
- Output: executable code in target language

### `src/spec_judge.py`
- LLM evaluates: "Given this spec, does this implementation comply?"
- Structured prompt returning YES/NO + reasoning
- Two-pass: first LLM judges compliance, second LLM (or same) judges adversarial behavior

### `src/software_pipeline.py`
- Orchestrates Layer 2: generate → judge → test → report
- Reuses existing report infrastructure

### Spec file format (YAML)
```yaml
domain: rest_api
language: python
intent: "GET /users endpoint returns paginated list of all users, requires valid auth token"
spec: |
  Endpoint: GET /users
  Auth: Bearer token required
  Response 200: JSON array of user objects
  Response 401: Invalid or missing token
  Pagination: offset/limit query params
test_cases:
  - input: "valid token, 10 users in DB"
    expected: "returns all 10 users"
  - input: "no token"
    expected: "returns 401"
known_gap: "Spec doesn't require returning ALL users, empty array satisfies 'JSON array'"
```

## Qwen Integration
- Qwen2.5-Coder-32B on H100 via vLLM (OpenAI-compatible API)
- Use existing `OpenAICompatibleClient` with H100 base_url
- CLI: `--provider openai --base-url http://<H100_IP>:8000/v1 --model Qwen/Qwen2.5-Coder-32B-Instruct`

## Implementation Order
1. Software spec examples (YAML files) — 4 domains
2. `spec_judge.py` — LLM compliance judge
3. `software_generator.py` — adapted adversarial prompts
4. `software_pipeline.py` — Layer 2 orchestrator
5. Unified report — both layers in one HTML
6. Test run with Gemini

## Limitations (state explicitly in presentation)
- Layer 2 loses formal soundness (LLM judge != Dafny verifier)
- LLM judge can be wrong — both false positives and negatives
- Behavioral tests are the ground truth, not the judge
- This is a research direction, not a production tool
