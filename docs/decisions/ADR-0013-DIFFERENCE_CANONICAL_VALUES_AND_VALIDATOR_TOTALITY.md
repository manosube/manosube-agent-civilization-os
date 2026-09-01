# ADR-0013: A canonical value is payload, and a validator returns errors

```text
DOC_TYPE=STRUCTURAL_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0013-DIFFERENCE-CANONICAL-VALUES-AND-VALIDATOR-TOTALITY
STATUS=ACCEPTED
DECIDED_AT=2026-09-01
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0012
SOURCE=INDEPENDENT_REVIEW_OF_41ef65f
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
UNSCHEMATIZED_REFERENCE_POLICY=STRUCTURAL_CLOSURE_REQUIRED
```

## 0. Position

Five findings. Three share one cause — **a canonical value was treated as something other
than payload** — and two are the cost of last round's corrections not being carried all the
way through. All five were reproduced against `41ef65f` before anything changed:

```text
1  Target {"value_type":"STRUCTURED","value":{"a":1}} vs Fact value {"a":1}
     Engine   satisfied: ['TP-0001']  differences: 0     <- the Difference was suppressed
5  Fact value {"kind":"widget","id":"HEAD"} (value_type STRUCTURED)
     Engine   SecurityRejectionError: moving reference 'HEAD' at
              request.bindings[0].observation_bundle.facts[0].value
2  predecessor context carrying a change naming an absent Difference
     Engine   ACCEPTED           auditor  0 errors      <- neither gate looked
3  historical Scope claiming TP-9999 while its Observation targets TP-0001
     Engine   ACCEPTED           auditor  0 errors
4  Negative Evaluation with evidence_refs removed
     raised   builtins.KeyError: 'evidence_refs'         <- not a validation error at all
```

No Kernel contract text and no schema changed. No identity algorithm changed.

## 1. Only the contract's typed scalar wrappers are unwrapped

`DIFFERENCE_IDENTITY.md` states the `expected_value_type` derivation as one closed table. A
`{"value_type": ..., "value": ...}` wrapper appears in it exactly four times — `DECIMAL`,
`TIMESTAMP`, `DURATION`, `IDENTITY_REFERENCE` — for the types JSON's own shape cannot
express. *Ordinary JSON object → STRUCTURED* is in the same table, and the two collection
types are written with a `collection_kind` wrapper, not a `value_type` one.

`RESERVED_VALUE_TYPES` had contained all seven. Including `STRUCTURED` was a category error
with a real consequence: a Target whose literal business value happened to be wrapper-shaped
had its outer object discarded, so a Fact carrying only the inner object satisfied the Target
and the required Difference was never derived. The constant is now
`TYPED_SCALAR_WRAPPER_TYPES`, and a contract test **reads the rule out of the Kernel
document** and asserts equality in both directions, so the code cannot drift from the
contract. The independent validator's own copy was corrected with it, and a parity test
compares fourteen shapes through both.

## 2. Reference scanning follows declared locations, everywhere

ADR-0012 stopped the *relational graph gate* inferring references from shape. It left
`walk_references()` — the moving-reference security scan — traversing the whole request by
that same unsound heuristic, so a schema-valid `STRUCTURED` Fact value of
`{"kind": "widget", "id": "HEAD"}` was rejected as a moving reference.

Both consumers now read one iterator, `graph.iter_declared_references`, so a second
reference registry cannot exist: the graph gate uses it to decide resolution, the security
scan uses it to decide identity immutability, and a contract test asserts both call it and
that the Engine holds the scan object rather than a traversal of its own.
`_iter_request_records` maps every record-bearing request location to the type it is scanned
as — the requested Objective, each binding's Scope, its historical Scopes, its Observation
bundle sections, and the predecessor's Difference, events and context.

Secret material is still scanned everywhere, unchanged: that is a property of *values*, and
the finding was about references.

## 3. Unschematized records: policy chosen and recorded

`UNSCHEMATIZED_REFERENCE_POLICY = "STRUCTURAL_CLOSURE_REQUIRED"`.

`01_SCHEMA/change/` and `01_SCHEMA/reflow/` are empty in v0.1, so those two types declare no
reference locations — and removing shape-based traversal left them with **no closure check
at all**. A Change naming an absent Difference passed the Engine and the auditor.

The instruction offered a fail-closed alternative: refuse to carry them. That was weighed and
rejected, because a `CLOSED` lineage's Reflow transaction *is* one of these records and its
retained chain cannot resolve without it — refusing would remove a route the contract
requires and this PR already supports. Instead a conservative structural traversal applies
**to these two types only**. Inside a record with no schema nothing can distinguish a
reference from a business value, and the safer reading of an ambiguous `{"kind", "id"}` field
is that it is a reference which must resolve; an unrecognised kind fails closed.

The cost is stated rather than hidden: a Change or Reflow record whose *payload* is shaped
like a reference is rejected here. That cost is removable only by the Kernel defining these
schemas, which is exactly `CHANGE_AND_REFLOW_SCHEMA_AVAILABLE=false`. The set is measured
from `RECORD_TYPES[...].schema is None`, so a type that gains a schema leaves the structural
set automatically and moves under the declared-path registry, with a contract test proving
the two stay in step and the schema directories really are empty.

## 4. Every Observation is admissible under the Scope it names

`_validate_observation_boundary` compared project, Scope id, method, snapshots and time —
never the Target. A supplied historical Scope could therefore claim `TP-9999` while the
Observation bound to it targeted `TP-0001`, and that impossible provenance was accepted by
the Engine, the returned bundle and the shared auditor alike.

The relationship between an Observation and its Scope belongs to the Observation element, so
`observation.scope.validate_scope` decides it — the same authority the Observation Engine
uses — rather than being restated here. It applies through the single `_own_scope` resolver,
so the current binding, the reached historical Observations, predecessor-only provenance and
the no-predecessor route all cross it. The derivation-request project rule keeps its own
message and runs first, so the more specific diagnosis is not lost.

## 5. A validator returns errors; it never leaks an implementation exception

A Negative Evaluation missing its schema-required `evidence_refs` was reported by the schema
pass and then handed, unfiltered, to a relational helper that indexed the missing field. The
Difference API raised `KeyError` instead of its canonical validation error.

Three changes, because any one alone is incomplete:

* **Rules that cannot be decided without a well-formed record run over the schema-valid
  subset** — the Evidence-channel binding, and the identity projections in
  `_verify_upstream_records`, which are now skipped for a record whose projection fields are
  absent rather than raising over it.
* **Reads are total.** Every list access goes through `_records`, and each loop guards the
  fields it needs with `_complete`, so a malformed record is still *examined* by the rules it
  can satisfy and its specific diagnosis is not lost.
* **The cross-record pass is wrapped** so that a record which trips a read it should never
  have reached cannot replace the canonical validation failure. That wrapper engages **only
  when a schema error was already recorded**: a schema-clean bundle is not shielded, so a
  genuine defect there still raises loudly instead of being reported as the caller's fault.

The audit went beyond `evidence_refs`, as required. Writing the totality matrix found further
raw indexes in the shared verifier — the Fact and Binding identity loops, the Fact and
Negative evaluation chain sorts, the revision-zero comparison — and in
`graph.relational_errors`. All are fixed.

## 6. Proofs added

```text
tests/contract/difference/test_value_type_contract.py         12 cases
  - the wrapper set equals the Kernel document's table, both directions
  - STRUCTURED is reached by shape, never by a wrapper; collections use collection_kind
  - each declared wrapper unwraps; an ordinary object, an unknown type and a wrapper with
    extra fields all stay literal
  - Engine and auditor normalize fourteen shapes identically

tests/unit/difference/test_structured_values.py               25 cases
  - a Fact carrying only the inner object does not satisfy a structured Target
  - the exact full object does; nested wrapper-shaped business objects stay intact
  - six ordinary value shapes still derive a Difference; four declared wrappers unwrap
    end to end; the projection is deterministic
  - a reference-shaped value, and six moving identities, are ordinary payload
  - a real moving reference is still rejected in the Objective, a carried Observation and
    the requested Scope

tests/unit/difference/test_unschematized_closure.py           13 cases
  - four dangling reference kinds, an unknown kind, a nested dangling reference
  - a resolving reference and an external kind are accepted
  - Reflow gated the same way; a schema-backed value never reinterpreted
  - the policy is recorded, measured from schema absence, and the directories are empty

tests/unit/difference/test_observation_scope_binding.py        8 cases
  - a historical Scope claiming another Target fails closed, naming that Observation
  - the valid Scope-change route passes cross-record validation, each Observation matched
    to its own Scope's Target and project
  - foreign project, carried predecessor Scope, and the authority-reuse source check

tests/unit/difference/test_validation_totality.py             33 cases
  - every required field removed, and every non-nullable field nulled, one at a time
  - wrong types, a malformed owner, several simultaneous schema errors, stable ordering
  - no raw exception escapes for any single removal
  - a valid Evidence-channel mutation still reaches semantic rejection
  - every shared helper total over hostile input, and the guard proven not to shield a
    schema-clean bundle
```

## 7. Acceptance

```text
TYPED_SCALAR_WRAPPER_COUNT=4
WRAPPER_SET_EQUALS_CONTRACT=true
STRUCTURED_TARGET_COMPARED_WHOLE=true
CANONICAL_VALUE_NEVER_TRAVERSED=true
REFERENCE_PATH_AUTHORITY_COUNT=1
MOVING_REFERENCE_SCAN_USES_DECLARED_PATHS=true
SECOND_REFERENCE_REGISTRY=absent
UNSCHEMATIZED_REFERENCE_POLICY=STRUCTURAL_CLOSURE_REQUIRED
UNSCHEMATIZED_TYPES_MEASURED_FROM_SCHEMA_ABSENCE=true
OBSERVATION_SCOPE_AUTHORITY_COUNT=1
OBSERVATION_TARGET_BOUND_TO_ITS_OWN_SCOPE=true
VALIDATION_ERRORS_ARE_TOTAL=true
RAW_EXCEPTION_ESCAPES=0
SCHEMA_CLEAN_BUNDLE_IS_NOT_SHIELDED=true

KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
CANONICAL_OWNER_COUNT=1
```

```text
CHANGE_AND_REFLOW_SCHEMA_AVAILABLE=false   # the cost of the structural policy in section 3
UNSCHEMATIZED_PAYLOAD_MAY_NOT_BE_REFERENCE_SHAPED=true
DERIVATION_INPUT_INTERFACE_EXTENDED=true
ENGINE_EMBEDS_INDEPENDENT_AUDITOR=false
CLOSURE_EVALUATION_EXECUTION_IMPLEMENTED=false
REFLOW_COMMITMENT_CLAIMED=false
OBJECTIVE_EDITORIAL_CHAIN_CLAIMED=false
OBSERVATION_METHOD_CLOSURE=partial
TARGET_PREDICATE_RESOLVED_STRUCTURALLY=false
REOPENED_CROSS_RECORD_PROVEN=false
LATER_PHASE_SEMANTICS_CLAIMED=false
IMPACT_PROJECTION_UNCONSTRAINED=true
DIFFERENCE_RUNTIME_PROVEN=false
KERNEL_V0_1_COMPLETE=false
```

`UNSCHEMATIZED_PAYLOAD_MAY_NOT_BE_REFERENCE_SHAPED` is the new, explicit cost of section 3's
policy, recorded so it is reviewable rather than discovered: inside a Change or Reflow record
this phase reads every `{"kind", "id"}` field as a reference, because no schema exists to say
otherwise.
