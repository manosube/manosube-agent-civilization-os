# ADR-0009: One typed validation boundary for carried predecessor context

```text
DOC_TYPE=STRUCTURAL_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0009-DIFFERENCE-PREDECESSOR-VALIDATION-BOUNDARY
STATUS=ACCEPTED
DECIDED_AT=2026-08-31
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0008
SOURCE=INDEPENDENT_REVIEW_OF_92d06a7
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

Three findings on head `92d06a7` are one structural defect, and the review named it
correctly: predecessor context was admitted by a **growing set of partial checks** rather
than by a boundary every carried record must cross. Each review round named the next
uncovered field; the fix is to stop fixing fields.

All three were reproduced against `92d06a7` before correction.

```text
1  malformed predecessor Difference payload
     difference_id recomputes            True
     malformed field carried             yes
     independent Difference validator    []          <- nothing caught it
2  forged BLOCKED blocker effective boundary, event id retained
     event id recomputes                 True
     forged boundary carried             yes
     independent Difference validator    ["blocker boundary mismatch: D-EVT-CCFD06..."]
3  forged Next Observation Request reason_code, request id retained
     forged request carried              yes
     independent Difference validator    ["next observation binding mismatch: D-EVT-CCFD06..."]
```

Findings 2 and 3 are producer/consumer drift: the Engine emitted bundles its own auditor
rejects. Finding 1 was caught by nothing.

No Kernel contract text and no schema changed. No identity algorithm changed. Every
existing Difference and Observation identity is unchanged.

## 1. The boundary

`src/manosube_agent_civilization/difference/predecessor.py` declares, once, every record
type the Engine is permitted to carry, and puts each through the same ordered gate:

```text
1. group every supplied record by its canonical type
2. reject an unknown section outright
3. schema-validate every record against its canonical schema
4. recompute every content-addressed identity with its existing single authority
5. enforce the type-specific cross-field and status invariants
6. reject same-identity/different-payload records inside the context itself
7. resolve every reference the carried records carry
8. only then is a record part of the returned bundle
```

Steps 1-6 need nothing but the context and run **before** any record is merged. Step 7 runs
on the merged set, because a reference may legitimately resolve to a record the current
derivation supplies rather than one the caller re-sent — the nuance ADR-0005 recorded.
Nothing is returned before both gates pass, and nothing is ever repaired.

A section absent from the table is **rejected**, so a new carried type cannot be introduced
without passing the boundary. A contract test reads the Engine's own absorption code and
asserts the declared table and the absorbed sections are the same set, in both directions.

## 2. Carried-type inventory and coverage matrix

```text
section                            schema  identity  cross-field   phase
observations                         yes     yes      Scope+boundary  OBSERVATION
normalized_facts                     yes     yes      shared verifier OBSERVATION
fact_observation_bindings            yes     yes      shared verifier OBSERVATION
fact_evaluations                     yes     yes      shared verifier OBSERVATION
negative_observations                yes     yes      shared verifier OBSERVATION
negative_observation_evaluations     yes     yes      shared verifier OBSERVATION
observation_scopes                   yes     n/a      resolved per Observation
objective_revisions                  yes     n/a      reference resolution
policies                             yes     yes      subject binding
next_observation_requests            yes     yes      event/Difference binding
observation_methods                  yes     yes      request binding
evaluations                          yes     n/a      NOT CLAIMED       LATER PHASE
reopen_condition_evaluations         yes     n/a      NOT CLAIMED       LATER PHASE
candidate_completion_records         yes     n/a      NOT CLAIMED       LATER PHASE
candidate_claim_evaluation_events    yes     n/a      NOT CLAIMED       LATER PHASE
invariant_evaluations                yes     n/a      NOT CLAIMED       LATER PHASE
evidence_sufficiency_results         yes     n/a      NOT CLAIMED       LATER PHASE
changes                              NONE    n/a      NOT CLAIMED       LATER PHASE
reflow_transitions                   NONE    n/a      NOT CLAIMED       LATER PHASE

difference        (predecessor key)  yes     yes      Closure Policy identity
events            (predecessor key)  yes     yes      shared lifecycle authority
```

`01_SCHEMA/change/` and `01_SCHEMA/reflow/` are **empty** in v0.1: those two types have no
canonical schema in this repository, so there is nothing to validate them against. They are
admitted only as carried provenance, remain subject to the identity-collision and
reference-resolution gates, and the non-claim is named in `NO_CANONICAL_SCHEMA_SECTIONS`
rather than implied. A contract test measures that emptiness against the repository.

The bundle's own envelope — `differences`, `events`, `supersession_relations`,
`materialized_status`, the profiles and `current_state_ref` — is accepted and ignored,
because handing a previous bundle back as context is the canonical usage. Ignoring is
fail-safe: a Difference, an event or a Supersession Relation enters the returned bundle
only through the predecessor's own keys or by being derived here.

## 3. Finding 1 — the carried Difference payload

Identity covers the closed semantic tuple only. Every carried Difference is now
schema-validated **before** it is read or copied, on both the retained same-ID route and
the material-change supersession route, and its Closure Policy identity is recomputed.
`risk_class`, `authority_required`, `observation_evidence_refs`, `observed_state_revision`
and `observation_scope` mutations all now fail closed.

**One honest limit.** `impact` is declared `{"type": "object"}` in
`01_SCHEMA/difference/difference.schema.json`, so *any* object is contract-conformant
there. The Engine cannot reject what the contract permits, and inventing a shape for it
would be legislating a schema this Issue does not own. Recorded as a remaining Difference:

```text
IMPACT_PROJECTION_UNCONSTRAINED=true
OWNER=schema authority, not this Issue
STATUS=REMAINING, recorded not resolved
```

## 4. Finding 2 — the carried lifecycle event payload

The blocker payload and the Next Observation Request binding sit **outside** event
identity, so a schema-valid event can retain its `difference_event_id` while either is
forged. Rather than write a second rule set, the rules were **extracted** from the
independent validator into the lifecycle authority the validator already imports:

```text
src/manosube_agent_civilization/difference/lifecycle.py
  BLOCKER_CONDITION_EXPECTED_STATE
  BLOCKER_PAYLOAD_FIELDS
  blocker_payload_errors()
  next_observation_binding_errors()
```

`scripts/difference_contract_validator.py` now calls them and states none of those rules
itself — a contract test asserts the rule strings no longer appear in its source and that
both consumers hold the same objects. `BLOCKER_CONDITION_EXPECTED_STATE` is pinned to the
`blocker_resolution_condition` enum in the canonical event schema.

## 5. Finding 3 — the carried Next Observation Request

A request's content address covers its whole payload, so recomputing it is what makes a
retained `observation_request_id` over an altered `reason_code`, Scope, method, State
binding or event binding fail closed. Requests supplied directly and requests reached from
an event's `next_observation_ref` or a blocker's `verification_request_ref` go through the
same authority.

## 6. What the boundary found in this repository's own tests

Turning the boundary on immediately rejected fixtures that had been supplied for eight
rounds: `retained_status_predecessor` was carrying **schema-invalid Closure Evaluation
records** for `OPEN`, `ACTIVE`, `VERIFYING`, `RETAINED`, `CLOSED` and `REOPENED` — the
canonical schema binds `evaluation_mode`, `proposed_terminal_status` and `result` together,
and the helper set the last two to the target status. Nothing had ever validated them.

The helper now supplies conformant later-phase provenance: `TERMINAL_POLICY_ONLY` for
`BLOCKED` and `RETAINED`, and a `CANDIDATE_CLOSURE` evaluation with an after-state
candidate for `CLOSED` and `REOPENED`. Statuses needing no Closure Evaluation carry none.

**This narrowed a standing non-claim.** With a conformant evaluation, a `RETAINED` retained
re-observation is now `validate_bundle(...) == []` end to end:

```text
RETAINED_CROSS_RECORD_PROVEN=true    (was unproven)
REOPENED_CROSS_RECORD_PROVEN=false   (Evidence sufficiency, candidate claim and candidate
                                      invariant bindings a CANDIDATE_CLOSURE evaluation
                                      must satisfy are later-phase machinery)
```

The REOPENED test pins what remains: every message must name that Closure Evaluation or an
upstream lifecycle event, and none may concern a Next Observation Request.

## 7. Proofs added

```text
tests/contract/difference/test_predecessor_boundary.py        12 cases
  - every absorbed section is a declared carried type, and every declared type is
    absorbed -- read out of the Engine's own source, in both directions
  - an unknown section is rejected; the bundle envelope is accepted and carries nothing
  - the predecessor accepts exactly difference / events / context
  - every named schema exists on disk; the no-schema non-claim is measured
  - the later-phase and caller-assigned-identity sets are exhaustive and consistent
  - one lifecycle payload authority: the validator states none of the rules itself
  - BLOCKER_CONDITION_EXPECTED_STATE equals the canonical schema enum

tests/unit/difference/test_predecessor_mutations.py           48 cases, 10 skipped
  - 6 identity-bearing mutations at the boundary and end to end
  - 9 schema-invalid payload mutations across the carried types
  - a smuggled undeclared field rejected for every schema-backed populated type
  - 5 malformed predecessor Difference payload fields
  - 3 forged blocker resolution conditions and a forged blocker effective boundary,
    each asserting the event identity still recomputes first
  - a non-BLOCKED event carrying blocker payload
  - same-ID/different-payload rejected; an identical duplicate accepted
  - a valid multi-event predecessor accepted byte for byte
  - equivalent re-observation and material supersession both cross-record valid
  - the skipped cases name why: no canonical schema, or not populated by the fixture
```

## 8. Acceptance

```text
PREDECESSOR_VALIDATION_BOUNDARY_COUNT=1
CARRIED_TYPE_INVENTORY_CLOSED=true
UNKNOWN_SECTION_REJECTED=true
EVERY_ABSORBED_SECTION_TYPED=true
CARRIED_DIFFERENCE_SCHEMA_VALIDATED=true
CARRIED_EVENT_PAYLOAD_VALIDATED=true
CARRIED_REQUEST_IDENTITY_RECOMPUTED=true
LIFECYCLE_PAYLOAD_AUTHORITY_COUNT=1
PREDECESSOR_RECORDS_NEVER_REPAIRED=true
VALID_PREDECESSOR_BYTE_IDENTICAL=true
RETAINED_CROSS_RECORD_PROVEN=true

KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
CLOSURE_EVALUATION_IMPLEMENTED=false
REFLOW_IMPLEMENTED=false
```

```text
REOPENED_CROSS_RECORD_PROVEN=false
LATER_PHASE_SEMANTICS_CLAIMED=false
CHANGE_AND_REFLOW_SCHEMA_AVAILABLE=false
IMPACT_PROJECTION_UNCONSTRAINED=true
DIFFERENCE_RUNTIME_PROVEN=false
KERNEL_V0_1_COMPLETE=false
```
