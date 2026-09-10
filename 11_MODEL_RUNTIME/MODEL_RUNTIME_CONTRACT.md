# Multi-Model Replaceability and Phase 12 Execution Continuity Contract (Phase 16, Issue #66)

```text
DOC_TYPE=MODEL_RUNTIME_CONTRACT
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=MODEL-RUNTIME-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_MODEL_RUNTIME_ADAPTER
MODEL_RUNTIME_OWNER_COUNT=1
PUBLIC_MODEL_RUNTIME_ENTRY_POINT_COUNT=5
SECOND_EXECUTION_CONTRACT=false
PROVIDER_SDK_DEPENDENCY_COUNT=0
LIVE_PROVIDER_CREDENTIAL_USE=false
REMOTE_COMMAND_EXECUTION=false
STRUCTURAL_REVIEW_ROUNDS_APPLIED=0
```

## 1. Position

This layer proves exactly one thing: **an Agent, a model, or a provider can be replaced without
losing Canonical State, Authority, Difference, Boundary, Evidence requirements, or resumable
work continuity.**

```text
Agent A starts from Canonical State
  → bounded work occurs under the Phase 12 execution contract
    → the session ends
      → Agent B starts from Canonical State
        → no conversation handoff
          → work continues under the same Authority and the same Difference
```

It is **not** a ninth Kernel element (the Kernel is fixed at eight:
`KERNEL_ELEMENT_COUNT=8`, `ONE_KERNEL_ELEMENT_PER_PACKAGE=true`). It is an adapter layer,
exactly as Boot, CLI, Agent Runtime, Independent Verification, Projection and Runtime already
are. The model and the provider are never a State, Authority, Difference, Evidence, Change,
Reflow, Binding, Boot, Runtime, or Closure owner here.

```text
MODEL_RUNTIME_OWNER_COUNT=1
PUBLIC_MODEL_RUNTIME_ENTRY_POINT_COUNT=5
```

## 2. Public signature

```python
opened = open_model_work_unit(
    store,
    agent,  # a live Phase 12 TemporaryAgent -- the execution contract
    project_id=project_id,
    project_binding_id=project_binding_id,
    difference_ref={"kind": "difference", "id": difference_id},
    required_capability="PROPOSE_EVIDENCE_CANDIDATE",
    boundary_ref={"kind": "model_execution_boundary", "id": boundary_id},
    model_execution_grant_refs=[{"kind": "model_execution_grant", "id": grant_id}],
    opened_at="2026-01-01T00:00:00Z",
)
opened["model_work_unit"]  # the canonical, committed, immutable Work Unit
opened["model_work_unit_ref"]  # what every later call resolves by
opened["model_execution_decision"]  # the Authority Decision, committed in the same transition

result = execute_model_work_unit(
    store,
    agent,
    project_id=project_id,
    project_binding_id=project_binding_id,
    model_work_unit_ref=opened["model_work_unit_ref"],
    adapter=my_model_adapter,  # the one replaceable boundary
    executed_at="2026-01-01T00:01:00Z",
)
result["envelope"]  # the canonical, committed Model Execution Envelope
result["receipt"]  # ModelExecutionReceipt (ephemeral, never committed)

recovered = recover_model_execution_session(
    store,
    agent_b,
    project_id=project_id,
    project_binding_id=project_binding_id,
    model_work_unit_ref=opened["model_work_unit_ref"],
    recovered_at="2026-01-01T00:02:00Z",
)
recovered["session_recovery_receipt"]  # the committed proof of recovery
recovered["model_work_unit"]  # every one of these was resolved by content address,
recovered["difference"]  # schema-validated, identity-recomputed,
recovered["model_execution_boundary"]  # project-bound, Binding-bound and Authority-bound
recovered["model_execution_decision"]  # inside this one call

swap = record_model_swap(
    store,
    agent_b,
    project_id=project_id,
    project_binding_id=project_binding_id,
    model_work_unit_ref=opened["model_work_unit_ref"],
    predecessor_execution_ref={"kind": "model_execution_envelope", "id": first_envelope_id},
    successor_execution_ref={"kind": "model_execution_envelope", "id": second_envelope_id},
    recorded_at="2026-01-01T00:04:00Z",
)
swap["model_swap_receipt"]

evidence = route_model_execution_to_evidence(store, result["receipt"], project_id, request)
```

The Authority extension this delivery adds lives in the **existing** `authority` package, not
here:

```python
decision = evaluate_model_execution_authorization(
    {
        "schema_version": "0.1",
        "project_id": project_id,
        "difference_ref": {...},
        "required_capability": "PROPOSE_EVIDENCE_CANDIDATE",
        "boundary_ref": {...},
        "human_authority_ref": {...},
        "human_authority_signing_key": {...},
        "grants": [...],
    }
)
decision["decision"]  # MODEL_EXECUTION_AUTHORIZED | MODEL_EXECUTION_REFUSED
```

## 3. Frozen semantic decisions

1. **Phase 12 is the execution contract, unchanged.** Every route takes a live
   `TemporaryAgent` and reads its own `boot_context`, which is what makes the handle's liveness a
   *checked* fact rather than an assumption: a released Agent raises `AgentReleasedError` from
   that very property. This package defines no execution-contract record, no contract id field,
   no schema for one, no durable agent identity, no session identity, no resume token, and no
   second Boot wrapper. `SECOND_EXECUTION_CONTRACT=false`.
2. **Boot is reached only through Phase 12.** `boot_project` is never imported here. There is
   exactly one literal `start_temporary_agent` call site in this package
   (`route._fresh_execution_contract`), and the Agent it starts is released immediately: it
   exists to take one honest snapshot and nothing else.
3. **A Work Unit is genesis-only and immutable.** It is opened once, is never mutated, has no
   current pointer and no transition chain, and is resolved by content address for the whole
   lifetime of the work. Two Agents "resuming the same Work Unit" resolve the identical address
   and independently re-verify the identical body — so "the same Work Unit" is a re-proved fact
   about content, never a shared variable.
4. **Every reference is resolved, schema-validated, identity-recomputed and re-bound on every
   call.** Nothing is cached across a session boundary. A Store-resolved record is never trusted
   on shape alone, and never trusted at all until its own recomputed identity and semantic
   fingerprint equal its own declared values.
5. **Model output is an untrusted candidate.** The accepting classification
   `CANDIDATE_ACCEPTED` does not exist in the vocabulary an adapter may report. Only the route
   computes it, and only after independently projecting the candidate down to the Boundary's own
   `permitted_candidate_fields` and independently re-fingerprinting that projection.
6. **The route reads exactly three keys out of an adapter's result**, through
   `MODEL_ADAPTER_RESULT_KEYS` by index rather than through string literals. An adapter's
   attempt to mint Authority, produce Evidence, declare a Difference closed, commit a Change or
   widen its own Boundary therefore has *no call shape at all*.
7. **No provider surface exists.** No shipped module in this package imports a provider SDK, a
   network surface, or a subprocess surface. `PROVIDER_SDK_DEPENDENCY_COUNT=0`,
   `LIVE_PROVIDER_CREDENTIAL_USE=false`, `REMOTE_COMMAND_EXECUTION=false`.
8. **One sanctioned committer, one Authority evaluator, one Evidence deriver.**
   `commit_state_transition`, `evaluate_model_execution_authorization` and `derive_evidence`
   each have exactly one call site, in exactly one module. This layer never calls the Change
   evaluator `evaluate_authority` at all.
9. **Every failure is typed, and none collapses into another.** Seven canonical outcomes, six of
   them non-accepting, each mapping to its own receipt status. No failure is ever converted into
   success, closure, or an authoritative absence of a result.
10. **This route reads no clock.** Every instant is a required, caller-supplied, canonically
    validated timestamp — the identical discipline every other route in this repository keeps.

## 4. Canonical owner

```text
model_runtime/route.py             the four public routes, the one Phase 12 call site, the one
                                    sanctioned commit, the one Authority evaluation
model_runtime/evidence_handoff.py  the one Evidence hand-off (the one derive_evidence call)
model_runtime/engine.py            pure derivation and schema validation; no I/O of any kind
model_runtime/identity.py          five content-addressed identities + the request identity
model_runtime/types.py             closed vocabularies, the ModelAdapter Protocol, the receipt
model_runtime/adapter.py           the two controlled adapters; imports no first-party owner
model_runtime/errors.py            the typed refusal vocabulary
```

The Authority half is owned by the existing Authority element:

```text
authority/model_execution_authorization.py   evaluate_model_execution_authorization
authority/identity.py                        the grant's signing payload / id, the decision's
                                              own semantic fields / id / fingerprint
authority/conformance.py                     the model_execution_grant admission entry
```

### 4.1 Canonical records

```text
model_execution_boundary     Human-declared. What the model's output may be used for.
model_work_unit              The State-bound Work Unit. Immutable, opened once.
model_execution_envelope     The committed model result.
model_swap_receipt           The committed proof that a different Adapter resumed this Work Unit.
session_recovery_receipt     The committed proof that a lost session was recovered from Store.
model_execution_grant        (Authority) The Human-Authority-signed capability grant.
model_execution_decision     (Authority) The content-addressed decision the evaluator mints.
```

`model_execution_boundary` and `model_execution_grant` are **Human-declared inputs**: shipped
Model Runtime code only ever resolves and verifies them, exactly as Runtime only ever verifies a
`runtime_deployment_declaration` it did not itself author.

## 5. Canonical route

```text
live Phase 12 Temporary Agent Execution Contract (its own boot_context, read not assumed)
→ fresh Boot through the same Phase 12 owner -- stale-State refusal, zero adapter calls
→ Store-resolved, schema-valid, identity-recomputed Difference
→ Store-resolved, schema-valid, identity-recomputed, Binding-bound, Authority-bound
  Model Execution Boundary
→ real Human-Authority-signed grant(s) → ONE evaluate_model_execution_authorization call
→ canonical, State-bound Model Work Unit (immutable, opened once, content-addressed) and its
  own Authority Decision, committed in ONE State transition
→ deterministic provider-neutral model_execution_request_identity (no adapter reached yet)
→ authority-freshness re-check -- refuses before the adapter
→ replaceable Model Adapter -- one bounded call, handed deep-frozen structures it cannot mutate
→ independent Boundary projection and typed reclassification (CANDIDATE_ACCEPTED computed here,
  never accepted from the adapter's own report)
→ canonical Model Execution Envelope
→ authority-freshness re-check on every commit attempt
→ existing canonical persistence boundary (commit_state_transition)
→ bounded Model Execution Receipt → existing Evidence / Independent Verification owners
```

### 5.1 The provider-neutral execution binding (P16-C1)

One request/response boundary binds every model invocation to exactly:

```text
state_revision + semantic_fingerprint     the exact State revision and semantic fingerprint
model_work_unit_ref                       the State-bound Work Unit identity
difference_ref                            the same Difference reference
required_capability                       the required capability
authority_ref + authority_decision        an explicit Authority reference AND decision
boundary_ref + boundary                   the applicable Boundary reference and resolved body
evidence_requirements                     the Evidence requirements
execution_contract                        the Phase 12 Temporary Agent Execution Contract identity
```

Provider-specific payloads, chat transcripts, hidden model memory and provider session IDs are
not canonical inputs, and there is **no key here through which one could arrive**.

### 5.2 The two freshness gates

```text
STALE STATE          checked once per call, before any resolution is trusted and before any
                     adapter exists
AUTHORITY FRESHNESS  checked before the adapter, and again on EVERY commit attempt
```

## 6. Disclosed judgment calls

Every one of these was left open by the adopted text and is decided here, in the open.

### 6.1 Authority integration: a new evaluator, not `evaluate_authority`

The adopted text offered two paths. Path (b) was taken: one narrowly-scoped new function,
`evaluate_model_execution_authorization`, added to the **existing** `authority` package.

`evaluate_authority` is the one *Change-permission* evaluator: "may this action occur, against
this exact State?" Its closed request shape is built for that question — a full `difference`
record, a `requested_action` carrying an `action_kind`, a `reversibility` and an opaque
operation payload with its own recomputed fingerprint, a `requested_scope`, `authority_rules` /
`prohibitions` / `approvals`, and a `current_state_revision` / `current_state_fingerprint` pair
— and it answers `AUTONOMOUS` / `HUMAN_APPROVAL_REQUIRED` / `PROHIBITED`.

The question Phase 16 must ask is a *capability-grant* question: "did this Project Binding's
Human Authority grant this specific `required_capability`, for this Difference, inside this
Boundary?" It has no requested action, no reversibility, no scope containment and no
rule/approval precedence in it at all. Forcing it through the Change evaluator would have meant
inventing an `action_kind` for it — and an unrecognized-but-well-formed kind fails closed to
`HUMAN_APPROVAL_REQUIRED`, not to a capability decision. That is the identical reasoning
P13-R3-F1 recorded for `evaluate_verifier_selection` and P14-R1-F1 recorded for
`evaluate_projection_authorization`; this is the third instance of the same shape, and it is an
extension of the one Authority owner rather than a second owner.

### 6.2 The grant carries its own signature, rather than a separate declaration record

`github_projection_grant` carries no signature; a separate, signed
`github_projection_grant_declaration` anchors it. `model_execution_grant` carries its own
Ed25519 signature directly, following `runtime_deployment_declaration`'s precedent instead: one
canonical projection is simultaneously the content address and the signed message, so "what this
record granted" can never mean two different things. One signed record closes the same gap two
records closed there, with strictly less surface. The Ed25519 primitive is not reimplemented —
Binding's own shared, fail-closed-as-a-value verifier is imported lazily and only the four-line
composition lives in Authority.

A consequence worth stating: because `signature` is outside the address projection (a signature
cannot cover its own value), a grant re-signed with an attacker's key has the **identical**
content address, and the Store refuses to hold two different bodies at one address. That is a
control in its own right, and the V4 suite asserts it directly.

### 6.3 The Boundary shape

There is no single general "Boundary" owner in this repository — Product Binding's Boundary
bounds repository source paths, Difference's `effective_boundary` bounds an Observation Scope,
and Runtime's Observation Boundary bounds live HTTP targets. None of the three is about *what a
model's output may be used for*, and force-fitting one would have meant declaring repo paths or
network targets this Phase neither reads nor honours.

So Phase 16 defines its own minimal Boundary, as its own canonical, Store-committed,
Human-declared record (`boundary_ref` names a real resolved record, never a free-form string):

```text
permitted_capability         which capability the output may serve
permitted_candidate_kinds    which kinds of candidate it may propose
permitted_candidate_fields   which fields may survive normalization at all
```

Nothing about repository paths, network targets, credentials or commands appears in it, because
none of those is what this Phase bounds.

### 6.4 The second Model Adapter is in-memory, not local-HTTP

Phase 15's second adapter opened a real bounded HTTP GET, because its domain genuinely *is*
HTTP. This domain is not. A local HTTP server here would be a *simulated provider endpoint*: it
would add a real network surface to a package the adopted proposal requires to have none, drift
the delivery toward the shape of a live provider call
(`LIVE_PROVIDER_CREDENTIAL_USE=false` is adopted), and prove nothing P16-C2 actually asks for.

`RequestDerivedModelAdapter` is instead structurally different in the way that matters: it holds
**no world at all**, deriving every candidate field purely from the canonical request it was
handed, while `FakeModelAdapter` holds a seeded world. They share no base class, no helper, no
module-level state and no notion of where a candidate comes from. The static suite proves the
negative directly: no module in this package imports a provider SDK, a network surface or a
subprocess surface.

### 6.5 What "stale State" means, exactly

Stale **cannot** mean "the Work Unit's `opened_state_revision` is behind the current revision":
committing the Work Unit itself advances the revision, so that reading would make every Work
Unit unusable the instant it existed and resumption after any unrelated commit impossible — the
exact opposite of what P16-C4 asks to prove. What must be current is the *execution contract the
caller is acting under*. Three rules therefore apply:

```text
NOT FROM THE FUTURE     a contract claiming a State revision this Store has never reached is not
                        a view of this Store at all
NOT A DIFFERENT WORLD   a contract claiming the Store's own current revision must carry the
                        Store's own current semantic fingerprint -- this is what refuses a
                        contract genuinely established against a different, internally
                        self-consistent Store at the same revision number
NOT OLDER THAN THE WORK an Agent whose own contract predates the revision the Work Unit was
                        opened against is operating on a view of the world in which this Work
                        Unit does not exist
```

Genesis additionally requires a **fully current** contract, because opening a Work Unit binds it
to an exact State snapshot. A Work Unit declaring an `opened_state_revision` greater than the
current one is refused as material that was never opened against any State this Store had.

### 6.6 The one route-level downgrade

An adapter reporting `CANDIDATE` whose bounded projection retains **no** permitted field at all
has not produced a candidate this Boundary can carry, and is recorded as `INCOMPLETE_EVIDENCE`
rather than as an accepted candidate over an empty object. That direction is the only one taken
anywhere: no failure is ever converted into success, and no outcome into an authoritative
absence.

### 6.7 No re-execution at hand-off

Projection's own hand-off re-observes the live external artifact. This one does not, for the
reason Runtime's own hand-off states and one more of its own: a model invocation is not
idempotent, so "re-running the model to check the receipt" would compare two genuinely different
candidates and would silently redefine "this receipt is genuine" into "the model would say the
same thing again" — which is neither what Issue #66 asks Evidence to attest to nor something a
replaceable adapter could guarantee. Corroboration means Store resolution and exact field
equality against the real, committed fact.

### 6.8 The Evidence position, and the target it attests about

The already-ratified `CHANGE_FREE_VERIFICATION_EVIDENCE` position, reached through the one
existing `derive_evidence` owner. Unlike a Runtime Observation, a model execution genuinely has
a canonical Difference subject, so `target_refs`/`input_refs` name the real Difference **and**
the State-bound Work Unit, rather than the Project Binding at large.

## 7. Required proof layers

```text
V1  deterministic identities        tests/unit/model_runtime/test_model_runtime_identity.py
V2  controlled adapter contract     tests/contract/model_runtime/test_model_adapter_contract.py
V3  model-swap vertical proof       tests/integration/model_runtime/
                                      test_model_swap_vertical_proof.py
V4  failure / tamper matrix         tests/integration/model_runtime/
                                      test_model_runtime_failure_tamper_matrix.py
V5  Phase 12 continuity + static    tests/contract/model_runtime/
                                      test_model_runtime_static_conformance.py
```

- **V1** proves every identity this delivery mints — the provider-neutral request, the model
  result, the model-swap receipt and the recovery receipt V1 names literally, plus the Work Unit
  they all hang from and the Boundary a Work Unit references. Every field of every closed
  semantic projection is tampered independently and both digests must move. A harness test pins
  each projection to the real record body, so a field added without being added to its own
  projection fails rather than escaping every tamper proof.
- **V2** proves two structurally distinct adapters execute a byte-identical canonical request
  and return normalized results in the identical shape, that they share no implementation, and
  that the accepting classification is absent from the adapter vocabulary entirely.
- **V3** proves the whole A-stops/B-resumes vertical over a real Store, with the session
  genuinely ended (the handle is released *and* asserted unusable, and every name bound to
  anything A produced is deleted) so that only the Work Unit's content address crosses.
- **V4** proves every scenario the adopted text names, each test's docstring stating whether it
  is a zero-adapter-call refusal, a typed outcome, or an adapter defect.
- **V5** pins Phase 12's exact public surface, the absence of any second execution contract
  anywhere in shipped code or the schema registry, and this package's own static conformance.

## 8. Explicit non-claims

This delivery does **not** claim, and no test here asserts:

- that any real model or provider was ever called. Both shipped adapters are controlled and
  in-memory; `LIVE_PROVIDER_CREDENTIAL_USE=false`.
- that one model is better than another, or that any selection was made. Best-model selection is
  an explicit non-target.
- that model memory is State. It is not, and there is no field anywhere in which it could be.
- that autonomous change is authorized. This layer commits no Change and evaluates no Change
  permission.
- that remote command execution is authorized. No module here imports a subprocess or network
  surface.
- that Phase 17 URL boot exists. It does not.
- that Phase 12 is cryptographically sandboxed. `TemporaryAgent` is a public `abc.ABC` and its
  own docstring already disclaims that; what is proved here is that every ordinary caller going
  through the documented surface cannot obtain an execution contract except through a real Boot,
  and that a contract not matching the Store is refused before any adapter exists.
- that a normalized candidate is Evidence. It is an Evidence *candidate*; whether it becomes
  Evidence is answered by the existing Evidence owner's own Change-free position, unchanged.

## 9. Gate 16

```text
GATE_16_MULTI_MODEL_REPLACEABILITY
  V1_DETERMINISTIC_IDENTITIES=PASS
  V2_CONTROLLED_ADAPTER_CONTRACT=PASS
  V3_MODEL_SWAP_VERTICAL_PROOF=PASS
  V4_FAILURE_TAMPER_MATRIX=PASS
  V5_PHASE_12_CONTINUITY=PASS
  STATIC_CONFORMANCE=PASS
  SCHEMA_VALIDATION=PASS
  MERGE_ALLOWED=false
  ISSUE_CLOSE_ALLOWED=false
  PHASE_16_COMPLETE=false
  PHASE_17_ALLOWED=false
```

`MERGE_ALLOWED`, `ISSUE_CLOSE_ALLOWED`, `PHASE_16_COMPLETE` and `PHASE_17_ALLOWED` are fixed at
`false` by the adopting authority and are not this document's to change.
