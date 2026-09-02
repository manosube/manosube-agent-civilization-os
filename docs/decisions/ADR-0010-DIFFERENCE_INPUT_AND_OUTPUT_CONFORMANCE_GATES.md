# ADR-0010: Input and output conformance gates, and status-bound request reasons

```text
DOC_TYPE=STRUCTURAL_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0010-DIFFERENCE-INPUT-AND-OUTPUT-CONFORMANCE-GATES
STATUS=ACCEPTED
DECIDED_AT=2026-08-31
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0009
SOURCE=INDEPENDENT_REVIEW_OF_2eae0b7
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

ADR-0009 closed the caller-supplied predecessor route with a typed boundary. The requested
Objective revision escaped anyway — because it arrives on the **current-derivation** route,
which had no such gate. That is the same defect one layer out, and the fix is the same
shape: a gate at every edge, driven by one table.

Both findings were reproduced against `2eae0b7` before correction.

```text
1  Objective revision missing a required field (recorded_at)
     consumed and returned                 yes
     returned Objective vs its own schema  FAILS
     independent Difference validator      []      <- nothing caught it
2  RETAINED event pointing at a REOPEN_REOBSERVATION request
     request content address recomputes    True
     event identity recomputes             True
     forged-reason request carried         yes
     independent Difference validator      []      <- nothing caught it
```

No Kernel contract text and no schema changed. No identity algorithm changed. Every
existing Difference and Observation identity is unchanged.

## 1. One record-type table, three gates

`src/manosube_agent_civilization/difference/conformance.py` states the canonical record
types once — schema, identity field, identity authority — and three maps read from it:

```text
RECORD_TYPES      22 canonical types
CARRIED_SECTIONS  predecessor-context section -> type   (the ADR-0009 boundary)
EMITTED_SECTIONS  returned-bundle section     -> type   (the output gate)
INPUT_KINDS       current-derivation input    -> type   (the input gate)
```

`difference/predecessor.py` no longer carries its own copy of the table or its own identity
helpers; a contract test asserts it holds the same objects and that the four duplicated
identity functions are gone.

**The output gate** runs in `_finalize`, immediately before the bundle is returned: unknown
sections rejected, every record schema-validated where a schema exists, every
content-addressed identity recomputed, duplicate and same-ID/different-payload records
rejected. A contract test reads the Engine's own `_finalize` literal — including the
conditional carried-dependency sections — and compares the emitted inventory against
`EMITTED_SECTIONS` **in both directions**, so a newly emitted section cannot bypass it and
the table cannot declare a section the Engine never emits.

**The input gate** validates each current-derivation input before any semantic field is
read. The audit of every input the review listed:

```text
input                     treatment
Objective revision        validated as a canonical record, before project/status/
                          fingerprint fields are read                    FIXED HERE
Observation Scope         validated as a canonical record (was already schema-validated;
                          now routed through the same gate)
Project State fingerprint validated against common/fingerprint.schema.json   ADDED HERE
Project State revision    non-negative integer check (no record type: the request carries
                          a revision and a fingerprint, not a State record)
Target Predicate          validated transitively as part of the Objective revision
Observation Method        arrives as a *fragment*; the record derived from it is
                          schema-validated by `_observation_method`
Closure Policy            arrives as a *requirements fragment*; the record derived from it
                          is schema-validated as `closure_policy.schema.json`
Observation bundle        validated by the Observation element's shared verifier
```

The two fragment inputs are deliberately absent from `INPUT_KINDS`: there is no canonical
schema for a fragment, and inventing one would be legislating a contract this Issue does
not own. Their conformance is decided on the records the Engine derives from them, which a
contract test pins.

## 2. Finding 1 — the requested Objective revision

The Engine checked only `schema_version`. `objective_revision.schema.json` composes its
required set across an `allOf`, and a record missing `recorded_at` was consumed, its
identity-bearing and semantic fields read, and the record copied into a returned bundle
that violates its own canonical schema — with the independent validator silent.

It is now validated through the shared registry before `project_id`, `status`, the semantic
fingerprint or the Target Predicates are read. Every required field removed one at a time
fails closed; so do identity-bearing and non-identity mutations, an undeclared field, and a
wrong schema version. A valid Objective is returned byte-identically.

## 3. Finding 2 — request reason bound to lifecycle status

The forward `next_observation_ref` is outside event identity, and the shared binding helper
compared everything about the request *except* its reason. A carried `RETAINED` event could
point at a `REOPEN_REOBSERVATION` request whose own content address recomputes perfectly.

The rule now lives in the single shared lifecycle authority the independent validator
already calls:

```python
if request is not None and event["to_status"] in NEXT_OBSERVATION_REASON:
    required = NEXT_OBSERVATION_REASON[event["to_status"]]
    if request["reason_code"] != required:
        errors.append("next observation reason does not match status: ...")
```

`NEXT_OBSERVATION_REASON` was already the transcribed contract mapping, so no new rule was
invented. Two further obligations were added from the same contract: a terminal status
(`SUPERSEDED`, `INVALIDATED`) must not carry a request at all, and `BLOCKED`'s own
requirement stays where it belongs — in the blocker payload rule, which pins the resolution
condition's verification request to the same reference.

**This caught the identical forgery in this repository's own fixtures.**
`retained_status_predecessor` defaulted every status to `BLOCKER_REOBSERVATION`, so
`RETAINED` and `REOPENED` predecessors had been pointing at blocker-reason requests for
rounds. The helper now derives the reason from the status.

## 4. Proofs added

```text
tests/contract/difference/test_output_conformance.py          13 cases
  - emitted inventory == final-gate inventory, in both directions, read from the source
  - envelope keys are exactly the non-record keys
  - the gate runs before the bundle is returned
  - an unknown emitted section, a schema-invalid record, a duplicate identity and a
    same-ID/different-payload pair are all rejected
  - every declared input is validated before its semantic fields are read
  - the fragment inputs are validated on the records they produce
  - one record-type table, with the four duplicated identity helpers gone
  - every named schema exists; the unschematized set is measured against the repository

tests/unit/difference/test_input_conformance.py               46 cases
  - every required Objective field removed one at a time (read from the composed schema)
  - 10 identity-bearing and non-identity Objective mutations
  - undeclared field, wrong schema version
  - a valid Objective accepted and returned byte-identically, and the returned Objective
    passes its own schema and the cross-record validator
  - 5 Observation Scope mutations, a missing required field, an undeclared field
  - 3 State fingerprint mutations and a missing required field

tests/unit/difference/test_request_reason_binding.py          23 cases
  - every status that requires a request x every reason (9 combinations), with both the
    request's content address and the event's identity recomputed, so neither identity
    rule can be what rejects them
  - RETAINED with REOPEN, REOPENED with RETAINED or blocker, BLOCKED with non-blocker
  - a terminal status carrying a request
  - OPEN retained and OPEN ordinary unresolved routes unaffected
  - the Engine and the auditor call the same rule object
  - valid status-specific requests remain cross-record valid
```

## 5. Acceptance

```text
OUTPUT_CONFORMANCE_GATE_COUNT=1
EMITTED_INVENTORY_MATCHES_GATE=true
UNKNOWN_EMITTED_SECTION_REJECTED=true
DUPLICATE_EMITTED_IDENTITY_REJECTED=true
INPUT_CONFORMANCE_GATE_COUNT=1
OBJECTIVE_REVISION_SCHEMA_VALIDATED=true
OBSERVATION_SCOPE_SCHEMA_VALIDATED=true
STATE_FINGERPRINT_SCHEMA_VALIDATED=true
FRAGMENT_INPUTS_VALIDATED_ON_DERIVED_RECORDS=true
RECORD_TYPE_TABLE_COUNT=1
REQUEST_REASON_BOUND_TO_STATUS=true
TERMINAL_STATUS_REQUESTS_FORBIDDEN=true
LIFECYCLE_PAYLOAD_AUTHORITY_COUNT=1

KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

```text
ALL_OUTPUT_SCHEMA_VALID=true   # qualified by UNSCHEMATIZED_SECTIONS below
UNSCHEMATIZED_SECTIONS=changes, reflow_transitions
CHANGE_AND_REFLOW_SCHEMA_AVAILABLE=false
LATER_PHASE_SEMANTICS_CLAIMED=false
REOPENED_CROSS_RECORD_PROVEN=false
IMPACT_PROJECTION_UNCONSTRAINED=true
DIFFERENCE_RUNTIME_PROVEN=false
KERNEL_V0_1_COMPLETE=false
```

`ALL_OUTPUT_SCHEMA_VALID` is true for every emitted section **except** `changes` and
`reflow_transitions`, for which `01_SCHEMA/change/` and `01_SCHEMA/reflow/` are empty in
v0.1. Those records are gated on identity collision and reference resolution only, and no
schema or semantic conformance is claimed for them. A contract test measures that emptiness
against the repository rather than asserting it.
