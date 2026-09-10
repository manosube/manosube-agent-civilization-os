# Multi-Model Replaceability Index (Phase 16, Issue #66)

```text
DOC_TYPE=MODEL_RUNTIME_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=MODEL-RUNTIME-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_MODEL_RUNTIME_ADAPTER
CANONICAL_KERNEL_COUNT=1
MODEL_RUNTIME_OWNER_COUNT=1
PUBLIC_MODEL_RUNTIME_ENTRY_POINT_COUNT=5
MODEL_EXECUTION_AUTHORIZATION_ENTRY_POINT_COUNT=1
SECOND_EXECUTION_CONTRACT=false
PROVIDER_SDK_DEPENDENCY_COUNT=0
STRUCTURAL_REVIEW_ROUNDS_APPLIED=0
```

---

## 0. What this document is

This is the one entry point for the **Multi-Model Replaceability and Phase 12 Execution
Continuity** contract set — the two documents under `11_MODEL_RUNTIME/` that define how an
Agent, a model, or a provider is replaced without losing Canonical State, Authority, Difference,
Boundary, Evidence requirements, or resumable work continuity.

```text
1. MODEL_RUNTIME_INDEX.md      (this document)
2. MODEL_RUNTIME_CONTRACT.md   the five public entry points, their frozen semantics, the
                                canonical route, the disclosed judgment calls, the required
                                proof layers, the explicit non-claims, and Gate 16
```

The human objective this Phase serves, in the adopting authority's own terms:

```text
Agent A starts from Canonical State
  → bounded work occurs under the Phase 12 execution contract
    → the session ends
      → Agent B starts from Canonical State
        → no conversation handoff
          → work continues under the same Authority and the same Difference
```

---

## 1. This is not a ninth Kernel element

The Kernel is fixed at eight (`KERNEL_ELEMENT_COUNT=8`,
`ONE_KERNEL_ELEMENT_PER_PACKAGE=true`), and this package declares
`KERNEL_ELEMENT=NONE_MODEL_RUNTIME_ADAPTER` — the same `none`-style convention Boot, the CLI,
Agent Runtime, Independent Verification, Projection and Runtime already use for their own
adapter layers.

What that means concretely: this layer validates no Project, restores no State, evaluates no
Change permission, judges no Evidence sufficiency, closes no Difference, and declares no
Objective completion. Each of those remains its existing owner's own, one-owner concern, and
this layer reaches every one of them only through that owner's own public surface.

---

## 2. This is not a second State, Difference, Authority, Evidence, Store, or Closure owner

| Existing owner | How this layer reaches it | What this layer never does |
|---|---|---|
| State / Store | `store.commit.commit_state_transition`, one call site | never calls `store.commit` directly, never writes a file, never builds a second persistence path |
| Boot | only through Phase 12's `start_temporary_agent`, one call site | never imports or calls `boot_project` |
| Agent Runtime (Phase 12) | takes a live `TemporaryAgent` as an argument | never defines a second execution contract, contract record, contract id, durable agent identity, session identity or resume token |
| Authority | `evaluate_model_execution_authorization`, one call site | never calls the Change evaluator `evaluate_authority`; never mints an Authority record itself |
| Difference | resolves and re-verifies a real, committed Difference | never derives, mutates or closes one |
| Evidence | `derive_evidence`, one call site, in the Change-free position | never judges sufficiency, never supplies its own accepting provenance |
| Reflow / Independent Verification | not at all | no module here imports either |

---

## 3. This is not a model client, an orchestrator, or a provider integration

```text
PROVIDER_SDK_DEPENDENCY_COUNT=0
LIVE_PROVIDER_CREDENTIAL_USE=false
REMOTE_COMMAND_EXECUTION=false
```

No shipped module in this package imports a provider SDK, a network surface, or a subprocess
surface — proved by AST walk, not asserted. No module reads the environment or any configuration
file. No canonical schema this delivery owns declares a provider, a model name, a prompt, a
transcript, model memory, a provider session id, or an API credential — proved by scanning every
property name at every depth of every schema, against a closed forbidden set.

The two adapters this delivery ships are both **controlled and in-memory**. Their whole purpose
is to prove the architecture, which is exactly what P16-C7 permits before any real model
execution: live credentials, real-provider calls, remote command execution and autonomous change
remain outside this proposal unless separately adopted.

---

## 4. Canonical owner

### 4.1 The five public entry points

```text
open_model_work_unit              open one immutable, State-bound Work Unit (genesis, once)
execute_model_work_unit           one bounded, provider-neutral model execution against it
record_model_swap                 prove Adapter/Agent A stopped and B resumed the same Work Unit
recover_model_execution_session   prove a totally lost session was recovered from Store alone
route_model_execution_to_evidence hand the normalized candidate to the existing Evidence owner
```

### 4.2 The seven canonical records

```text
model_execution_boundary     Human-declared. What the model's output may be used for.
model_work_unit              The State-bound Work Unit. Immutable, opened once, never mutated.
model_execution_envelope     The committed model result.
model_swap_receipt           The committed proof a different Adapter resumed this Work Unit.
session_recovery_receipt     The committed proof a lost session was recovered from Store.
model_execution_grant        (Authority-owned) The Human-Authority-signed capability grant.
model_execution_decision     (Authority-owned) The content-addressed decision.
```

`model_execution_boundary` and `model_execution_grant` are Human-declared **inputs**: shipped
code here only ever resolves and verifies them.

### 4.3 The six identities

```text
model_execution_boundary_id / _semantic_fingerprint     what the output may be used for
model_work_unit_id / _semantic_fingerprint              the State-bound anchor
model_execution_request_identity                        the provider-neutral execution binding
model_execution_envelope_id / _semantic_fingerprint     the model result
model_swap_receipt_id / _semantic_fingerprint           the model-swap receipt
session_recovery_receipt_id / _semantic_fingerprint     the recovery receipt
```

Every projection is the complete record minus its own two digest fields, so every
authority-bearing field, every reference field, every State-binding field and every outcome
field participates in both digests. There is no field a record can carry that its own identity
does not see.

### 4.4 The closed vocabularies

```text
MODEL_EXECUTION_CAPABILITIES   PROPOSE_EVIDENCE_CANDIDATE
MODEL_CANDIDATE_KINDS          OBSERVATION_CANDIDATE
MODEL_ADAPTER_OUTCOMES         CANDIDATE, UNAVAILABLE, REFUSED, MALFORMED, TIMEOUT, CANCELLED,
                               INCOMPLETE_EVIDENCE
MODEL_EXECUTION_OUTCOMES       CANDIDATE_ACCEPTED, UNAVAILABLE, REFUSED, MALFORMED, TIMEOUT,
                               CANCELLED, INCOMPLETE_EVIDENCE
```

The two outcome vocabularies differ by exactly one member, and that difference is the whole of
"model output is never self-authenticating": there is no token an adapter can return that means
*accepted*.

---

## 5. Explicit non-claims

Restated here so the index and the contract cannot drift; `MODEL_RUNTIME_CONTRACT.md` §8 is the
full list.

- No real model or provider was called. Both adapters are controlled and in-memory.
- No model was selected as better than another. Best-model selection is an explicit non-target.
- Model memory is not State, and there is no field in which it could be.
- No autonomous change is authorized; this layer commits no Change.
- No remote command execution is authorized.
- Phase 17 URL boot does not exist.
- Phase 12 is not cryptographically sandboxed; its own docstring already disclaims that. What is
  proved is that every ordinary caller cannot obtain an execution contract except through a real
  Boot, and that a contract not matching the Store is refused before any adapter exists.
- A normalized candidate is an Evidence *candidate*, never Evidence. The existing Evidence
  owner's own Change-free position decides, unchanged.

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_16_COMPLETE=false
PHASE_17_ALLOWED=false
```
