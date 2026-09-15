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

## 10. Cross-package extension: `pinned_execution_snapshot` (Phase 19, Issue #77, Structural
Review Round 3, P19-R3-F1)

`execute_model_work_unit` takes one additional optional keyword parameter, added for Phase 19's
own Multi-Agent Dynamic Execution package (`multi_agent`) and never reimplemented there:

```python
result = execute_model_work_unit(
    store,
    agent,
    project_id=project_id,
    project_binding_id=project_binding_id,
    model_work_unit_ref=opened["model_work_unit_ref"],
    adapter=my_model_adapter,
    executed_at="2026-01-01T00:01:00Z",
    pinned_execution_snapshot=None,  # optional; default preserves every existing caller unchanged
)
```

When omitted (every caller that predates this extension, unchanged), this route's own request
and committed Envelope continue to declare the true live State a fresh reboot observes at this
exact call -- identical behaviour to before this parameter existed. When supplied, it must be a
mapping with exactly `state_revision` (a non-negative `int`, never from the Store's own future --
a revision ahead of the fresh reboot's own is refused with `ModelRuntimeStaleStateError` before
the adapter is reached) and `semantic_fingerprint` (the matching fingerprint shape); those two
values are what the adapter's own real request and the committed Envelope declare *instead of*
the freshly-rebooted live values, while every other freshness/staleness/Authority check in this
route still runs against the true live Boot underneath, completely unchanged. `project_binding_ref`
and `human_authority_ref` are never overridable this way -- they always come from the true live
Boot, regardless.

This exists because `multi_agent`'s own plans open one shared Model Work Unit that every one of
1-3 slots' own independent Temporary Agent then executes against in sequence; each slot's own
real committed Envelope legitimately advances the Store's own live State before the next slot's
own adapter call, so an unpinned request would let each slot's own request observe a different,
order-dependent `state_revision`/`semantic_fingerprint` pair -- Structural Review Round 3's own
P19-R3-F1 finding. Pinning every slot's own real request to the plan's own immutable, genesis-once
snapshot closes that drift at the one place a real adapter request is ever constructed
(`_canonical_request`), rather than in `multi_agent`'s own bookkeeping alone. No second Authority
evaluator, execution route, or Model Runtime owner is introduced by this extension; it is a single
additive parameter on the one existing route this repository's every caller already shares.

## 11. Structural Review Round 4 corrections (Phase 19, Issue #77, P19-R4-F1/F3/F4)

Three further, purely additive changes to `execute_model_work_unit` and its own
`_require_valid_pinned_execution_snapshot` helper, adopted the same way as §10 above: every
existing caller that supplies none of these is entirely unaffected.

**P19-R4-F1 -- `cancellation_check`.** An optional `Callable[[], bool]` keyword. When supplied,
it is called exactly once, immediately before this route would otherwise commit the Envelope --
after the real adapter call has already returned, and after that Envelope's own recomputed
semantic fingerprint has already been checked against its own declared value. If it returns
`True`, this call raises `ModelRuntimeExecutionCancelledError` instead of committing anything.
This exists because a caller that bounds this call's own real duration on its own side (a
worker-thread timeout, since a blocked Python thread cannot be forcibly killed) may already have
recorded its own typed timeout outcome and moved on by the time a late adapter call finally
returns; without this check, that late, no-longer-awaited result could still silently become a
committed success. `multi_agent`'s own per-slot `ThreadPoolExecutor` bound (`execute_
dynamic_execution_plan`, Structural Review Round 3's own P19-R3-F4) sets a `threading.Event()`
the instant it gives up on a slot's own attempt, and passes that Event's own `is_set` as this
parameter -- the one, real, runtime-enforced signal this route itself checks before ever
committing, rather than a second, parallel cancellation mechanism `multi_agent` would otherwise
have had to build and maintain on its own.

**P19-R4-F3 -- `additional_records_factory`.** An optional
`Callable[[Mapping[str, Any]], list[tuple[str, str, Mapping[str, Any]]]]` keyword, called once
with the fully-derived, self-verified Envelope -- after `cancellation_check`, so a cancelled
attempt never reaches it -- and expected to return zero or more `(kind, id, body)` record tuples.
Those records are committed in the *exact same* atomic `_commit` transaction as the Envelope
itself, never a separate follow-up commit. This exists because `multi_agent`'s own per-slot
attempt-envelope claim (Structural Review Round 3's own P19-R3-F3) previously committed in a
second, separate transaction immediately after this route's own Envelope commit returned --
leaving a real, if narrow, crash window in which a real, already-committed Envelope existed with
no claim naming it, a state `multi_agent`'s own recovery path had no way to reach. Folding the
caller's own record into this route's one existing commit call closes that window entirely:
either both the Envelope and the caller's own record land, or neither does. This route never
inspects, validates, or interprets the caller's own record kind or body -- it only extends the
one commit call's own record list, so no second commit primitive, Store owner, or transaction
authority is introduced.

**P19-R4-F4 -- `pinned_execution_snapshot` is now verified against the resolved Work Unit's own
genesis snapshot, not merely shape- and future-checked.** §10 above already required a supplied
`pinned_execution_snapshot` to be well-shaped and never claim a State revision from the Store's
own future; that alone left an arbitrary, caller-minted `(state_revision, semantic_fingerprint)`
pair otherwise unchecked, which a `pinned_execution_snapshot` originating outside the one
legitimate caller could exploit to have the Envelope declare a State pair that was never actually
resolved from anywhere real. `_require_valid_pinned_execution_snapshot` now additionally requires
the supplied pair to equal, exactly, the resolved Work Unit's own already schema-valid, identity-
recomputed `opened_state_revision`/`opened_semantic_fingerprint` fields -- the real, committed,
canonical fact of the State this Work Unit was genuinely opened against, verified by
`_resolve_work_unit` before this check is ever reached. A supplied pair that does not equal it is
refused with `ModelRuntimeRequirementError` before the adapter is ever reached and with nothing
committed, regardless of how the pair was obtained. `multi_agent`'s own plan-boot snapshot and
the shared Work Unit's own opened fields are both derived from the identical live State read
inside the same `open_dynamic_execution_plan` call, so this new requirement changes nothing for
that one legitimate caller.

No second Authority evaluator, execution route, Store owner, or Model Runtime owner is introduced
by any of these three changes; each is a single additive parameter, or a strengthened check on an
existing one, on the one route this repository's every caller already shares.

## 12. Structural Review Round 5 correction (Phase 19, Issue #77, P19-R5-F2)

Adopted as `ADOPT_P19_R5_ATOMIC_TIMEOUT_AND_BOUNDED_ADDITIONAL_RECORDS` against reviewed
head/authorized target `d762ccb7f88a0e3fbfd1c8478955da5abe501adf` (PR #78). One finding lands on
this route (P19-R5-F1 is entirely a `multi_agent`-side fix over the unchanged
`cancellation_check` contract from §11 above; it introduces no change here).

**P19-R5-F2 -- `additional_records_factory` is replaced by
`slot_attempt_envelope_claim_factory`, a closed, caller-immune single-record surface.** §11's
own P19-R4-F3 fix accepted a caller-supplied `Callable[[Mapping[str, Any]], list[tuple[str, str,
Mapping[str, Any]]]]` -- a generic record-injection surface with no restriction on the returned
`kind`. Exact-head reproduction against that surface successfully persisted a forged
`kind="authority_decision"` record, `id="FORGED-BY-MODEL-RUNTIME-CALLER"`, atomically alongside a
real Envelope: nothing about the parameter's own shape stopped a caller (or a bug, or an
attacker with the caller's own access) from choosing any kind at all. The fix replaces that
parameter with `slot_attempt_envelope_claim_factory: Callable[[Mapping[str, Any]], Mapping[str,
Any]] | None`, called once, in the identical position (after `cancellation_check`, so a
cancelled attempt never reaches it), and returning exactly one record *body* -- never a kind, an
id, or a list. The kind this route ever commits alongside that body is a single, hardcoded module
constant, `_SLOT_ATTEMPT_ENVELOPE_CLAIM_RECORD_KIND = "multi_agent_slot_attempt_envelope_claim"`;
no parameter, argument, or caller-controlled value can ever select a different one, so the class
of forgery the reproduction demonstrated is now structurally inexpressible rather than merely
checked and refused. Before committing, this route additionally requires the returned body's own
`model_execution_envelope_ref` field to be present and to name *this exact, newly-derived*
Envelope (its `kind` equal to `ENVELOPE_RECORD_KIND` and its `id` equal to this call's own
`envelope["model_execution_envelope_id"]`), and its own
`multi_agent_slot_attempt_envelope_claim_id` field to be a non-empty string; either check failing
raises `ModelRuntimeRequirementError` with nothing committed. This route does not itself recompute
that id or the claim's own semantic fingerprint -- it has no legitimate way to, since that hash
function belongs to `multi_agent`, never duplicated here (the one-way package layering this
repository already establishes: `multi_agent` depends on `model_runtime`, never the reverse). The
caller's own factory is therefore expected to self-verify its own construction (recomputing and
comparing its own identity and semantic fingerprint) before ever returning the body to this route,
and every subsequent read of the committed record independently re-verifies both again, exactly as
every other canonical record's own resolver in this repository already does — a corrupted claim is
caught at construction time and at every later read, never silently trusted at any single point.
Either the Envelope and this one claim commit together, or neither does — the identical atomicity
§11 established, now bounded to one caller-immune kind. Proved at the Model Runtime level by four
tests in `test_model_runtime_failure_tamper_matrix.py`: the rewritten P19-R4-F3 crash-window proof
(now against the new parameter shape), a proof that the old `additional_records_factory` keyword
no longer exists (`TypeError`, zero adapter calls), a proof that a claim body whose
`model_execution_envelope_ref` names a different, fabricated Envelope id is refused with zero
writes and an unchanged State revision, and a proof that a claim body missing its own declared id
is refused the same way.

`PUBLIC_GENERIC_ADDITIONAL_RECORD_FACTORY_PRESENT=false`: no parameter on this route's public
signature accepts a caller-selected record kind, id, or list of records. No second Authority
evaluator, execution route, Store owner, or Model Runtime owner is introduced by this change.

## 13. Structural Review Round 6 correction (Phase 19, Issue #77, P19-R6-F2)

Adopted as `ADOPT_P19_R6_POST_COMMIT_RECOVERY_AND_CLAIM_INTEGRITY` against reviewed head/
authorized target `b9df7f8179db7e3ab3d67d411cc59b50d69924f1` (PR #78). One finding lands on this
route (P19-R6-F1 is entirely a `multi_agent`-side fix over this route's own unchanged commit and
return-value contract; it introduces no change here).

**P19-R6-F2 -- this route closes the `slot_attempt_envelope_claim_factory` surface §12 opened
against caller-selected identity, cross-attempt binding, forged semantic fingerprint, and
schema-unbounded shape.** §12's own fix required only a non-empty declared id and a correct
`model_execution_envelope_ref`; it could not independently recompute that id or the claim's own
semantic fingerprint, since that hash formula lived in `multi_agent.identity`, and this route may
never import `multi_agent` (that package depends on this one, never the reverse). Exact-head
reproduction showed the gap that left open: a caller-selected non-empty claim id unrelated to its
own content, a wrong `project_id`/`plan_ref`/`slot_index`/`attempt_ordinal`, a missing or forged
semantic fingerprint, and an additional unregistered field all passed this route's own shallow
checks.

The fix is relocation, not duplication: a new module, `model_runtime.claim_identity`, is now the
single owner of this one closed kind's own identity, semantic fingerprint, and schema --
`multi_agent_slot_attempt_envelope_claim_id` and `multi_agent_slot_attempt_envelope_claim_
semantic_fingerprint` moved here verbatim (identical formula, identical field-list constants) from
`multi_agent.identity`, which now imports them from here instead of maintaining its own copy. This
is deliberately not a general dependency on `multi_agent`: no name from that package is read here,
and both functions are generic -- the identical `sha256(canonical_json_bytes(projection))` recipe
every other canonical kind in this repository already uses. `require_schema_valid_slot_attempt_
envelope_claim` performs the identical generic, package-neutral schema lookup `binding.validation.
validate_against_schema_id` already establishes as the sanctioned pattern for a record a domain
accepts but does not own the schema of: it loads this kind's own registered `$id` from `01_SCHEMA/`
via `jsonschema.Draft202012Validator` + `referencing.Registry`/`Resource`, generically, exactly as
that existing precedent does.

`execute_model_work_unit` gained a new required parameter, `slot_attempt_envelope_claim_binding:
Mapping[str, Any] | None = None`, required whenever `slot_attempt_envelope_claim_factory` is
supplied and carrying `{"plan_ref": ..., "slot_index": ..., "attempt_ordinal": ...}` -- this call's
own caller's declared expectation for what this exact attempt's claim must bind to, never the
untrusted factory's own self-selected values. The commit-tail validation sequence is now: (1)
schema-validate the returned body against its own registered canonical schema (closing the
additional-field gap a field-projection recompute alone cannot, since `additionalProperties:
false` is the only check that reads outside each projection's own named field set); (2) require its
declared `model_execution_envelope_ref` to name this exact, newly-derived Envelope (unchanged from
§12); (3) require its declared `project_id`/`plan_ref`/`slot_index`/`attempt_ordinal` to equal this
call's own `project_id` parameter and `slot_attempt_envelope_claim_binding`'s own declared values
exactly; (4) independently recompute the claim's own narrow id and require it to equal its own
declared value; (5) independently recompute the claim's own full semantic fingerprint and require
it to equal its own declared value. Any failure raises `ModelRuntimeRequirementError` with nothing
committed. `multi_agent` itself now imports these same two functions from
`model_runtime.claim_identity` rather than defining its own copy, so its own construction-time
self-verification and its own read-time resolver both follow this same single owner -- exactly the
"ownership remains singular and every existing consumer follows that same owner" constraint the
adoption required.

Proved at the Model Runtime level in `test_model_runtime_failure_tamper_matrix.py`: the three
existing §12 negative-control tests, rewritten to supply the new required binding parameter and a
schema-valid, self-consistent claim body while still isolating each test's own original condition
(crash-before-commit; wrong Envelope binding; missing declared id), plus eight new required
negative controls -- a caller-selected, self-inconsistent claim id; a wrong `project_id`, `plan_
ref`, `slot_index`, and `attempt_ordinal` binding (four separate tests, each isolating one field);
a forged semantic fingerprint; a missing semantic fingerprint; and an additional, unregistered
field -- each proving `FORGED_OR_MALFORMED_CLAIM_WRITE_COUNT=0` (the adapter is called exactly
once, since this route's own commit-tail validation runs strictly after the real adapter call, but
the Store's own State revision is unchanged and nothing is committed).

`CALLER_SELECTED_CLAIM_ID_ACCEPTED=false`, `CLAIM_SCHEMA_VALIDATED_BEFORE_COMMIT=true`,
`CLAIM_NATURAL_KEY_ID_RECOMPUTED=true`, `CLAIM_FULL_SEMANTIC_FINGERPRINT_VERIFIED=true`,
`CLAIM_PROJECT_BINDING_EXACT=true`, `CLAIM_PLAN_BINDING_EXACT=true`,
`CLAIM_SLOT_BINDING_EXACT=true`, `CLAIM_ENVELOPE_BINDING_EXACT=true`,
`UNKNOWN_FIELD_ACCEPTED=false`. No import of `multi_agent` was added to this package; no second
Store/State/Authority owner was introduced; ownership of this one closed kind's identity, semantic
fingerprint, and schema remains singular.

## 14. Structural Review Round 7 correction (Phase 19, Issue #77, P19-R7-F1)

Adopted as `ADOPT_P19_R7_CANONICAL_CLAIM_ORIGIN_BINDING` against reviewed head/authorized target
`976a7ef28c4b98a0312f033e36ae5df6c75c87be` (PR #78).

**P19-R7-F1 -- this route now independently resolves and verifies the canonical Phase 19 plan
behind a claim, rather than merely comparing two caller-supplied values to each other.** §13's own
fix verified that the factory-produced claim body's own declared `plan_ref`/`slot_index`/`attempt_
ordinal` equalled `slot_attempt_envelope_claim_binding`'s own declared values -- but the identical
single public caller supplies both the factory and the binding, so their mutual agreement never
proved a genuinely committed plan stood behind either one. Exact-head reproduction showed a wholly
caller-invented `plan_ref`/`slot_index`/`attempt_ordinal` triple -- self-consistent, schema-valid,
with a genuinely recomputed id and semantic fingerprint -- passing every §13 check unnoticed, for a
plan that was never committed to the Store at all.

The fix is the identical relocation discipline §13 already established, extended to the plan kind:
`multi_agent_dynamic_execution_plan_id`, `multi_agent_dynamic_execution_plan_semantic_fingerprint`,
and a new `require_schema_valid_multi_agent_dynamic_execution_plan` now live in this route's own
`model_runtime.claim_identity` module (relocated, not duplicated, from `multi_agent.identity`,
which now imports the two identity functions from here). Before the adapter is ever reached --
immediately after this call's own Work Unit is resolved, alongside every other pre-adapter
admission check -- a new private helper, `_resolve_and_verify_canonical_plan`, is called whenever
`slot_attempt_envelope_claim_factory` is supplied: it resolves the plan
`slot_attempt_envelope_claim_binding`'s own `plan_ref` names from the Store itself (via the
Store's own generic, kind-agnostic `resolve_record`, exactly as `_SLOT_ATTEMPT_ENVELOPE_CLAIM_
RECORD_KIND` has been resolved and committed by name since Round 5), schema-validates it,
independently recomputes its own narrow id and requires it to equal both its own declared value
*and* the Store lookup key used to find it, independently recomputes its own full semantic
fingerprint and requires it to equal its own declared value, requires its own declared `project_
id` to equal this call's own, requires its own declared `model_work_unit_ref` (kind and id) to
name this exact Work Unit, requires the caller-declared `slot_index` to exist in its own `slots`
with a `capability` equal to this call's own already-resolved Work Unit's own `required_
capability`, and requires the caller-declared `attempt_ordinal` to equal the fixed literal `1` --
this system's own single-attempt-per-slot design (no retry loop exists; `multi_agent.route`'s own
`_call_execute_model_work_unit` already always hardcodes `attempt_ordinal=1`) means this field is a
route-derived invariant, never a free caller-selected value trusted from any "expected" parameter.
Any failure raises `ModelRuntimeRequirementError` or `ModelRecordIntegrityError`, with the adapter
never reached and nothing committed -- unlike every §12/§13 claim-body check, which necessarily
runs after the one real adapter call this route's own commit-tail follows, this is a genuine
pre-adapter admission check, the identical class as the pre-existing Difference/Boundary/Authority
resolution above it.

This closes the collusion gap without any of the prohibited approaches the adoption named: no
second caller-provided "expected" comparator was added (the canonical plan is resolved from the
Store itself, never merely asserted by any parameter); the check is not limited to body-versus-
binding equality (it independently re-derives the plan's own identity and fingerprint from its own
resolved content); no hidden equivalent public hook exists (the one existing
`slot_attempt_envelope_claim_factory`/`slot_attempt_envelope_claim_binding` pair is where this
verification now lives); `model_runtime` still does not import `multi_agent` (the plan kind's
identity/fingerprint/schema functions were relocated here, the identical precedent as the claim
kind); no second implementation of the plan's own identity/fingerprint formula exists (`multi_
agent.identity` now imports these two functions from here rather than defining its own copy); and
no second Store/State/Authority owner was introduced (the existing Store's own generic `resolve_
record` is the only new call, exactly as the pre-existing Difference/Boundary resolvers already
use it).

Proved in `test_model_runtime_failure_tamper_matrix.py`: a new required decisive negative control,
using the adoption's own exact literal values (`plan_ref={"id": "CALLER-SELECTED-PLAN"}`, `slot_
index=2`, `attempt_ordinal=999`, a self-consistent, schema-valid claim body and binding, and no
such plan ever committed to the Store) -- proving `ADAPTER_CALL_COUNT=0` (unlike every §12/§13
negative control, which all show exactly one adapter call), `ENVELOPE_WRITE_COUNT=0`, `CLAIM_
WRITE_COUNT=0`, and `STATE_REVISION_ADVANCE=0`; and a new required positive control, using a
genuine, Store-resolved plan (this test file's own new `_commit_canonical_plan` helper) naming
this exact Work Unit and slot, proving the fix does not narrow the honest route -- the Envelope
and the claim still commit atomically, in the same one transaction, exactly as every Round 4-6
proof already established. The pre-existing Round 5/6 claim-factory tests (all eleven of them)
were updated to call this same helper before their own `execute_model_work_unit` call, so the
canonical plan their own `slot_attempt_envelope_claim_binding` names now genuinely resolves --
each test's own original point (a caller-selected id, a wrong project/plan/slot/attempt binding, a
forged or missing semantic fingerprint, an additional unregistered field, a crash immediately
before commit) is otherwise unchanged and still isolated at the identical post-adapter commit-tail
layer it always was. The Round 6 F1 post-commit acknowledgement-loss recovery test (`multi_agent`'s
own `test_p19_r6_f1_a_post_commit_acknowledgement_loss_never_publishes_a_false_unavailable`, which
runs through the full `multi_agent` stack and therefore already commits a genuine plan via `open_
dynamic_execution_plan`/`resolve_and_verify_committed_plan` before ever reaching this route)
continues to pass unmodified, and its own `REPLAY_DUPLICATE_ADAPTER_CALL_COUNT=0` proof already
covers this fix's own zero-duplicate-adapter-call replay requirement over a real, Store-resolved
plan.

`CALLER_SUPPLIED_BODY_AND_BINDING_DEFINE_CANONICAL_ORIGIN=false`, `PLAN_REF_RESOLVED_FROM_
STORE=true`, `PLAN_SCHEMA_IDENTITY_AND_SEMANTIC_FINGERPRINT_VERIFIED=true`, `PLAN_PROJECT_
BINDING_MATCH=true`, `PLAN_MODEL_WORK_UNIT_BINDING_MATCH=true`, `SLOT_INDEX_EXISTS_IN_RESOLVED_
PLAN=true`, `SLOT_CAPABILITY_MATCHES_RESOLVED_PLAN=true`, `ATTEMPT_ORDINAL_ROUTE_DERIVED=true`,
`SELF_CONSISTENT_COLLUDING_BODY_AND_BINDING_WRITE_COUNT=0`, `GENUINE_PHASE19_CLAIM_ATOMIC_WITH_
ENVELOPE=true`. No import of `multi_agent` was added to this package; no second caller-provided
comparator, hidden equivalent hook, duplicated identity/schema implementation, or second
Store/State/Authority owner was introduced; ownership of the plan kind's identity, semantic
fingerprint, and schema is now singular in this route's own package, exactly as the claim kind's
already is.

## 15. Structural Review Round 8 correction (Phase 19, Issue #77, P19-R8-F1)

Adopted as `ADOPT_P19_R8_VERIFIED_BINDING_CONTINUITY` against reviewed head/authorized target
`dcf5c23c5dc58e9ee1811a7599dd0543d5d4c78c` (PR #78).

**P19-R8-F1 -- the canonical plan verified before the adapter and the plan the post-adapter claim
comparison checks against are now the identical retained value, never two independent reads of
`slot_attempt_envelope_claim_binding`.** §14 above resolved and verified the canonical plan
*before* the adapter was ever reached, but the post-adapter commit-tail (§12/§13) then built its
own comparator by taking `dict(slot_attempt_envelope_claim_binding)` a second time -- reading the
identical caller-owned Mapping again, after `adapter.execute()` had already returned. Because the
same public caller supplies the adapter, the binding, and the claim factory, the adapter could
mutate that Mapping in place -- including its own nested `plan_ref` -- from a genuinely resolved
and verified Plan A to an uncommitted Plan B between those two reads, and the factory (invoked
after the adapter, over the by-then-mutated Mapping) could follow that same mutation to build a
self-consistent Plan-B claim the post-adapter re-read would have agreed with, even though only
Plan A was ever resolved and independently verified against the Store.

`slot_attempt_envelope_claim_binding` is now validated and normalized exactly once, before the
adapter is ever reached, into a value wholly detached from the caller's own Mapping object
(`_detach_slot_attempt_envelope_claim_binding`): it reads `plan_ref.kind`, `plan_ref.id`, `slot_
index`, and `attempt_ordinal` once, and returns a freshly built dict -- including a freshly built
`plan_ref` dict of its own -- sharing no nested container with the caller's own Mapping. A shallow
`dict(binding)` alone would not have sufficed, since its own `plan_ref` entry could still be the
identical nested Mapping object the caller (or an adapter it controls) continues to hold and
mutate. This one retained value, and never another read of the parameter itself, is what both the
pre-adapter canonical-plan resolution (§14) and the post-adapter claim comparison (§12/§13) use.

Proved in `test_model_runtime_failure_tamper_matrix.py`: a new required decisive adversarial
regression in which a genuine Plan A is committed and resolved/verified before the adapter, a
custom `FakeModelAdapter` subclass mutates the original caller-owned binding Mapping in place --
including its own nested `plan_ref` -- to a wholly uncommitted Plan B inside its own `execute()`,
and the claim factory (called after the adapter, reading only the by-then-mutated Mapping) follows
Plan B. `PLAN_A_RESOLVED_AND_VERIFIED=true`, `ADAPTER_MUTATES_ORIGINAL_CALLER_BINDING_TO_PLAN_
B=true`, `FACTORY_FOLLOWS_MUTATED_PLAN_B=true`, `PLAN_B_CANONICAL_RESOLUTION=false` (Plan B is
never committed to the test's own Store at all), `ADAPTER_CALL_COUNT=1` (Plan A's own pre-adapter
check genuinely passes, so the adapter really is reached -- unlike §14's own pre-adapter collusion
control), `PLAN_B_CLAIM_WRITE_COUNT=0`, `ENVELOPE_WRITE_COUNT=0`, `STATE_REVISION_ADVANCE=0`; and a
new required positive control proving the fix does not narrow the honest route -- when nothing
mutates the original binding at all, the retained, caller-detached value is exactly what the caller
declared, and the Envelope plus its companion claim still commit atomically in the same one
transaction, the identical Round 4-7 invariant, preserved. The Round 6 acknowledgement-loss
recovery test, every Round 7 control, and the Round 5/6 claim-factory suite all continue to pass
unmodified.

## 16. Structural Review Round 10 correction (Phase 19, Issue #77, P19-R10-F1)

Adopted as `ADOPT_P19_R10_CANONICAL_WORK_UNIT_AND_ATTEMPT_IDENTITY` against reviewed head/
authorized target `cd6ea7e7a07092ad8fe30d18b28c26ac1881e5a7` (PR #78). Only `P19-R10-F1` touches
this module; `P19-R10-F2` is addressed entirely inside `multi_agent/route.py` and requires no
change here.

**P19-R10-F1 -- a caller outside this module can now resolve and verify a committed Model Work
Unit's own canonical, Store-recomputed lineage directly, rather than either trust an in-memory
copy of it or duplicate this module's own identity/schema verification a second time.** Round 9's
`multi_agent/route.py` treated `model_work_unit_ref` equality alone as sufficient transitive proof
that an Envelope genuinely binds to the plan's own Model Work Unit's `boundary_ref` and
`evidence_requirements` -- reasoning that a Work Unit is one immutable, content-addressed record
whose consistency with any Envelope committed against it is already enforced by
`execute_model_work_unit`'s own commit-time check. That reasoning holds only for an Envelope
genuinely produced through the real `execute_model_work_unit` route; it does not hold for a
schema/id/fingerprint-valid Envelope that some other, non-canonical path constructed and committed
directly, naming the same `model_work_unit_ref` while declaring a different, equally genuine
Boundary the Work Unit never actually authorized. Closing that gap requires resolving the
canonical Work Unit itself, not merely trusting the equality of a reference to it.

New public `resolve_and_verify_committed_work_unit(store, project_id, model_work_unit_id_value)`
is a thin wrapper around the existing private `_resolve_work_unit`, which already performs this
module's own full three-way canonical admission for a Work Unit: schema-valid, same-project, and
its own identity and semantic fingerprint independently recomputed from its own content, equal to
its own declared values and to the Store lookup key itself. No Work Unit identity or schema logic
is duplicated in `multi_agent`; the caller receives the identical canonical record this module's
own execution route itself would resolve. Deliberately not added to `__all__`, matching the
existing convention that `resolve_and_verify_committed_envelope` is public but excluded from
`__all__` -- direct imports continue to work regardless of `__all__` membership. This is a
genesis-once, immutable record; resolving it here never re-derives or re-evaluates Authority, and
never introduces a second Work Unit owner.

Proved in `test_multi_agent_substitution_and_continuity.py`
(`test_p19_r10_f1_an_envelope_with_the_plans_own_work_unit_but_a_different_genuine_boundary_is_
refused`): a second, genuinely committed Boundary is opened alongside the plan's own; a genuine
claim/Envelope pair is reached via the Round 1/3 crash-before-terminal-commit technique; a new,
genuinely committed forged Envelope is built by copying the genuine one with `boundary_ref`
swapped and its own `model_execution_envelope_id`/semantic fingerprint honestly recomputed from
that changed content (this module's own `ENVELOPE_SEMANTIC_FIELDS` include `boundary_ref`, so an
in-place, same-key tamper is impossible here -- a genuinely new record, committed through a real
Store transaction, is the only way to construct this control); the existing claim is redirected to
name it. `FORGED_ENVELOPE_SELF_CONSISTENT=true`, `FORGED_ENVELOPE_DIFFERENT_ID_FROM_GENUINE=true`,
`WORK_UNIT_BOUNDARY_CROSS_CHECK=refused`, `ADAPTER_CALL_COUNT=0` (redirection is caught purely by
the lineage check, before any new adapter execution), `SLOT_OUTPUT_WRITE_COUNT=0`,
`STATE_REVISION_ADVANCE=0`. Every Round 1-9 proof in this module continues to pass unmodified.

## 17. Structural Review Round 11 correction (Phase 19, Issue #77, P19-R11-F1)

Adopted as `ADOPT_P19_R11_AUTHORITY_AND_ADAPTER_IDENTITY_CONTINUITY` against reviewed head/
authorized target `6c4f69af886b57223d2b3af8dafa6383eb9fa592` (PR #78). Only `P19-R11-F1` touches
this module; `P19-R11-F2` is addressed entirely inside `multi_agent/route.py` and requires no
change here, since it reuses this module's own existing `model_execution_request_identity`
unchanged.

**P19-R11-F1 -- a caller outside this module can now resolve and verify a committed Model
Execution Decision's own canonical, Store-recomputed lineage directly, without re-evaluating
whatever Human Authority happens to be live right now.** `multi_agent`'s own Round 10 fix
resolved the canonical Work Unit and compared an Envelope's `boundary_ref`/
`evidence_requirements` against it, but left the Envelope's own `project_binding_ref` and
`human_authority_ref` unchecked against any canonical owner. `project_binding_ref` is
straightforward -- the Work Unit already carries the identical field -- but `human_authority_ref`
is not: neither the Work Unit nor the Plan records it, since the genuine route
(`_canonical_request`) always sets it from whichever Human Authority is live at *execution* time,
never at Work Unit or Plan genesis. The one immutable, canonical fact that already existed the
moment this Work Unit's Authority was granted, and that every genuine Envelope produced under it
is unconditionally required to agree with (`_resolve_authority_decision`'s own
`selection_authority_ref` == fresh Human Authority check, run on **every** execution against this
Work Unit, not merely at genesis), is the committed Model Execution Decision's own
`selection_authority_ref`.

The existing `_resolve_authority_decision` bundled two concerns that this correction now
separates: (1) the static, time-invariant admission of the decision record itself --
schema-valid, same project, its own identity and semantic fingerprint independently recomputed
and equal to its own declared values -- and (2) the live-freshness re-binding against whatever
Human Authority a fresh Boot reports *right now*. Only (1) is safe to reuse for a later, post-hoc
terminal-graph check that may run long after the original execution: re-running (2) against a
current live Boot would be wrong for exactly the reason (1) is right -- a legitimate Human
Authority rotation after this Work Unit's own lifetime must never make an honest historical
Envelope look forged. New private `_resolve_decision` extracts exactly (1), and both
`_resolve_authority_decision` (unchanged behavior, still applying (2) on top) and new public
`resolve_and_verify_committed_authority_decision(store, project_id, authority_ref)` (a thin
wrapper exposing only (1)) now call it -- no duplicated identity/schema/fingerprint logic exists
in two places.

Proved in `test_multi_agent_substitution_and_continuity.py`
(`test_p19_r11_f1_an_envelope_with_a_different_project_binding_and_human_authority_is_refused`):
a genuine claim/Envelope pair is reached via the Round 1/3/9/10 crash-before-terminal-commit
technique; a new, genuinely committed forged Envelope -- copied from the genuine one with both
`project_binding_ref` and `human_authority_ref` swapped for different, equally well-formed
references, and its own id/fingerprint honestly recomputed -- is named by the redirected claim;
replay refuses with zero new adapter calls, zero terminal writes, zero State advance. Every
Round 1-10 proof in this module continues to pass unmodified.

`BINDING_NORMALIZED_ONCE_BEFORE_ADAPTER=true`, `NORMALIZED_BINDING_DETACHED_FROM_ALL_CALLER_
ALIASES=true`, `CANONICAL_PLAN_VERIFIED_AGAINST_RETAINED_BINDING=true`, `POST_ADAPTER_CLAIM_
COMPARED_TO_SAME_RETAINED_BINDING=true`, `CALLER_BINDING_RE_READ_AFTER_ADAPTER=false`, `VERIFIED_
PLAN_A_TO_UNVERIFIED_PLAN_B_SWITCH_ACCEPTED=false`. `multi_agent.route`'s own `_call_execute_
model_work_unit` required zero code changes: its own `slot_attempt_envelope_claim_binding` is
already a freshly built dict literal at each call (with its own `plan_ref` a fresh `dict(plan_
ref)` copy), never handed to the adapter it constructs, so nothing in that package could ever
mutate it. No import of `multi_agent` was added to this package; no second caller-provided
comparator, hidden equivalent hook, or second Store/State/Authority owner was introduced.

## 18. Structural Review Round 2 Work Coordination wrap (Issue #22, `ADOPT_P84_PROJECT_STATE_
ORTHOGONAL_COORDINATION_REBIND`, PR #84)

`open_model_work_unit` and `execute_model_work_unit` are now each composed inside the Human
Wait-Time Transparency vertical's own `with_work_time_coordination` (`work_time_transparency.
adapters`), below their own eager, pure-shape identity checks and above everything that was
their prior body -- renamed `_open_model_work_unit_body`/`_execute_model_work_unit_body`,
otherwise byte-identical. Every normal invocation reaching this module's own Store/Authority/
Boot admission sequence, or any refusal beyond the eager checks, now durably commits a Work
Coordination `open`/`terminal` record pair through the Store's own orthogonal `coordination/`
ledger (`FileStateStore.commit_coordination_record`) -- a second, independent append-only lane
this module's own State/Authority/Evidence surface never reads or writes, so nothing here can
ever be authorized or mutated by a Work Coordination commit. `work_unit_ref` is content-
addressed from this project's own id, the resolved Difference/Work Unit id, and one real clock
reading taken before the coordination opens -- never reused across two distinct attempts. Both
entrypoints gained seven optional `estimated_duration_*`/`estimate_confidence`/`major_steps`/
`next_progress_update_due_minutes`/`variability_factors`/`work_time_coordination_clock` keyword
parameters, each defaulting to this module's own canonical estimate, so every existing caller's
call syntax remains valid unchanged (`multi_agent.route`'s own call sites required no changes).
`MODEL_RUNTIME_EXACT_STATE_WEAKENING_ALLOWED=false` holds unmodified: the wrap never touches
`_live_contract(require_exact_state=True)`, only wraps around the two public entrypoints that
already called it. See `16_WORK_TIME_TRANSPARENCY/WORK_TIME_TRANSPARENCY_CONTRACT.md` §5 and
`tests/integration/store/test_coordination_ledger.py` for the ledger's own proof.

## 19. Structural Review Round 3 Work Coordination hardening (P84-R3-F1/F2/F3/F4,
`ADOPT_P84_R3_COORDINATION_LEDGER_CLOSURE`)

`commit_coordination_record` is replaced by the Store's own atomically tip-guarded
`commit_coordination_record_at_tip` (see `16_WORK_TIME_TRANSPARENCY/
WORK_TIME_TRANSPARENCY_CONTRACT.md` §15) -- `work_time_transparency/route.py`'s own callers,
this module included, require no call-site changes.

`open_model_work_unit` gains one new optional parameter, `joined_coordination:
work_time_transparency.adapters.ProgressReporter | None = None`. `None` (the default) is every
existing caller's own behavior, unchanged: an independent Work Coordination root is opened and
closed exactly as before. When `multi_agent.open_dynamic_execution_plan`'s own nested call
supplies its own bound `ProgressReporter` as `joined_coordination`, this entrypoint opens **no**
coordination root of its own at all -- it composes straight into its own body with the caller's
already-open reporter, so real production nesting has one root, never two (P84-R3-F4; see
`16_WORK_TIME_TRANSPARENCY/WORK_TIME_TRANSPARENCY_CONTRACT.md` §15 for the full rationale).

## 20. Structural Review Round 4 correction (P84-R4-F1, `ADOPT_P84_R4_WTT_JOIN_AND_LEDGER_
RECOVERY_CLOSURE`)

§19's own `joined_coordination` public parameter is retracted: the Structural Advisor identified
that an ordinary public keyword argument, checked only for `is not None`, is a caller-forgeable
suppression of `open_model_work_unit`'s own mandatory Work Coordination -- satisfiable by a
duck-typed object, or by a genuine reporter resolved against a different project, binding, or
coordination entirely. `open_model_work_unit`'s public signature no longer accepts any join
capability at all: every call always opens its own independent coordination root, unconditionally.

The one legitimate nested join (Multi-Agent's own already-open `MULTI_AGENT` coordination) is now
reached exclusively through a new internal function this module does not export,
`_open_model_work_unit_joined(store, agent, *, project_id, project_binding_id, difference_ref,
required_capability, boundary_ref, model_execution_grant_refs, opened_at, joined_coordination)` --
only `multi_agent.route`'s own internal composition imports and calls it. The passed
`joined_coordination` is still fully re-verified there, never merely trusted because of who is
presumed to have called it: see `16_WORK_TIME_TRANSPARENCY/WORK_TIME_TRANSPARENCY_CONTRACT.md`
§16 for the full `verify_joined_coordination` boundary this now requires (genuine `ProgressReporter`
instance, same Store/project/binding, correct `adapter_kind`, not yet terminal).

## 21. Structural Review Round 5 correction (P84-R5-F1, `ADOPT_P84_R5_F1_EXACT_OUTER_WORK_
UNIT_JOIN_BINDING`)

§20's own checks alone admitted a live reporter genuinely naming some *other*, simultaneously
open `MULTI_AGENT` coordination in the identical Store/project/binding -- everything Round 4
checked was individually true of it, since nothing there compared the resolved coordination's own
`work_unit_ref` against the specific outer work unit the joining call actually opened for.
`_open_model_work_unit_joined` gains a required `expected_outer_work_unit_ref` parameter, threaded
into `verify_joined_coordination` as its own new `expected_work_unit_ref` argument (see
`16_WORK_TIME_TRANSPARENCY/WORK_TIME_TRANSPARENCY_CONTRACT.md` §17 for the full boundary). The
public `open_model_work_unit` signature remains exactly as §20 left it -- no join or suppression
parameter of any kind. `expected_outer_work_unit_ref` is never derived inside this module: it is
`multi_agent.route.open_dynamic_execution_plan`'s own already-computed outer identity, carried
unchanged through the nested call (see `14_MULTI_AGENT/MULTI_AGENT_CONTRACT.md` §24 for the
caller-side derivation).
