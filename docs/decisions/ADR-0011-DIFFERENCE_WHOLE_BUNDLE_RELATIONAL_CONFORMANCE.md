# ADR-0011: One collision-safe union, one reference-edge authority, one binding authority

```text
DOC_TYPE=STRUCTURAL_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0011-DIFFERENCE-WHOLE-BUNDLE-RELATIONAL-CONFORMANCE
STATUS=ACCEPTED
DECIDED_AT=2026-09-01
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0010
SOURCE=INDEPENDENT_REVIEW_OF_3a30039
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

ADR-0009 and ADR-0010 gated records: a record crosses a typed boundary, satisfies its
canonical schema, and recomputes its identity. Four findings against `3a30039` are one
defect those gates cannot reach — **they decide records, never the relations between
them**. Insertion could silently replace a record; a reference could name nothing; an
Observation could be judged against a Scope it was never bound to; an event could name a
Closure Evaluation belonging to some other transition.

All four were reproduced against the reviewed head before anything was changed:

```text
1  two Objective bindings reusing one scope_id, each Scope valid alone
     Engine                                ACCEPTED
     emitted observation_scopes            ['OBS-SCOPE-0001/TP-0002']   <- one lost
     independent validator                 Difference projection mismatch: D-37BD36EB...
2  carried closure_evaluation naming an absent Difference
     Engine                                ACCEPTED
     independent validator                 evaluation references missing Difference
3  Scope-change re-observation of a recurring Fact
     Engine                                REJECTED (BoundaryViolationError)
     reason                                prior Observation bound to OBS-SCOPE-0001 was
                                           checked against OBS-SCOPE-0002
4  RETAINED event whose Evaluation proposes BLOCKED (both schema-valid)
     Engine                                ACCEPTED
     independent validator                 terminal evaluation binding mismatch
```

No Kernel contract text and no schema changed. No identity algorithm changed. Every
existing Difference and Observation identity is unchanged.

## 1. One collision-safe union

`conformance.merge_records` is now the only insertion path for every canonical section, on
every route — current derivation, the Observation context closure, predecessor context and
final bundle assembly. A new identity inserts, an identical duplicate is idempotent, and a
same-identity/different-payload pair fails closed **before** the target is mutated. Inputs
are never mutated: what is stored is a deep copy.

`engine._merge` is gone as a separate definition; the Engine imports the one function. The
direct assignments and read-only comprehensions that could drop a duplicate before anything
could detect it were removed:

```text
scopes[scope["scope_id"]] = ...                     -> merge_records   (finding 1)
methods[method["observation_method_id"]] = ...      -> merge_records
differences[prior["difference_id"]] = ...           -> merge_records
relations.append(...) / policies.append(...)        -> merge_records (were list appends
events.extend(...)                                     deduplicated only at the end)
objective_revisions = {objective[...]: ...}         -> merge_records
facts_by_id / bindings_by_id / observations_by_id    -> merge_records (read-only indexes
  and the evaluation index inside the closure           built by comprehension)
carried_observations / _facts / _bindings / _evaluations -> merge_records
materialized_status[difference_id] = ...            -> contradiction guard
```

A contract test asserts the Engine defines no second `_merge`, and a unit suite drives the
union over **every populated emitted section** of a real bundle: identical duplicate
idempotent, conflicting pair rejected in either insertion order and in a single call, the
target unmutated by the rejected write, and the caller's record unmutated by what the union
stores.

## 2. One typed reference-edge authority

`difference/graph.py` states what a reference *is* in the emitted graph, once:

```text
RESOLVABLE_KINDS   reference kind -> the emitted section it must resolve in   (20 kinds)
EXTERNAL_KINDS     kinds whose owner is outside this phase (enumerated non-claim)
REFERENCE_EDGES    record type -> its named reference fields and permitted kinds
IDENTITY_EDGES     record type -> its bare foreign keys and their target sections
```

Two passes run over every record of every section, not over the active Difference lineage:

* **Structural closure** finds every reference-shaped object wherever it is nested. A kind
  that is neither resolvable nor an enumerated non-claim fails closed, so a new reference
  kind cannot enter unreviewed. Completeness is by construction — no field list is
  consulted, so no field list can omit a field.
* **Typed edges** pin the kinds a named field may carry, which structural closure alone
  would not catch, and `IDENTITY_EDGES` covers the references that are *not* reference
  shaped: a Closure Evaluation names its subject Difference as a plain `difference_id`
  string, which is exactly how finding 2 escaped.

The independent contract validator **imports the same function object**; a contract test
asserts identity rather than parity, so two maps cannot drift. A contract test also asserts
`EMITTED_SECTIONS` values equal `REFERENCE_EDGES` keys equal `IDENTITY_EDGES` keys, in both
directions.

Where a kind is not resolved, the non-claim is enumerated rather than discovered:
`observation_method` resolves only where the lifecycle authority requires it (a Next
Observation Request); a Scope's or Observation's own declared method is the Observation
element's record and is not carried here. `target_predicate` is ambiguous *by contract* —
it names an Objective Target Predicate in some fields and a Closure Policy reopen condition
in others — so it is not resolved structurally, and the unambiguous case is decided by the
relational rules. Evidence, source snapshots, State revisions, kernel sources, authorities
and contract sources belong to elements this phase does not implement.

## 3. Every Observation against its own Scope

`_own_scope` is the single place that decides which Scope an Observation is verified
against. Both the append-only context closure and the final carried-Observation pass call
it, so the current derivation Scope can never be substituted for a historical Observation's
own Scope. A Scope the caller did not supply fails closed — reconstructing one would be
repairing the record rather than verifying it.

This is what makes a Scope-change re-observation possible at all. A recurring Fact keeps its
append-only evaluation chain across a Scope change, so the closure reaches the prior
Observation through its earlier binding; judging it against the new Scope rejected a valid
boundary-change derivation before it could supersede the prior Difference.

## 4. One Closure Evaluation binding authority

`lifecycle.closure_evaluation_binding_errors` is extracted from the independent validator
and imported back by it, so the producer and the auditor decide the binding one way. For
any event naming a Closure Evaluation it must resolve and belong to the same Difference;
for a `TRANSITION` into `CLOSED`, `BLOCKED` or `RETAINED` it must additionally match the
proposed terminal status, the preceding event head, the Closure Policy (identity, version
and recomputed semantic fingerprint), the evaluated State revision and fingerprint, the
Target Predicate and the Objective semantics; for a reopen it must be the very Evaluation
the `CLOSED` head named, satisfied and gated.

Two limits are stated rather than papered over. The Objective binding is on the **semantic
fingerprint**, not the revision identity — an editorial Objective revision carrying the same
semantics is a legitimate evaluation subject, and this repository's own conformance suite
caught the stricter rule rejecting it. And the `CLOSED` Reflow commitment window stays in
the independent validator under its own name (`closed reflow commitment mismatch`): Reflow
is a later element with no schema in v0.1 and this phase claims nothing about it.

**This caught two forgeries in this repository's own fixtures.** The helper bound a
REOPENED lineage's Closure Evaluation to the wrong event head, and carried a
CANDIDATE_CLOSURE Evaluation whose Evidence Sufficiency reference resolved to nothing.

## 5. The whole-bundle acceptance order

`_finalize` is the only return path, and it is crossed exactly once:

```text
collision-safe union of current + reached + predecessor records
  -> schema validation and identity recomputation      (validate_emitted_bundle)
  -> per-record cross-field/status validation          (_validate_carried_observations,
                                                        the predecessor boundary)
  -> all-record typed reference closure                (reference_closure_errors)
  -> cross-record relational validation                (relational_errors)
  -> return
```

A contract test reads the Engine source and asserts one assembly, one of each gate, one
`return bundle`, the gates in that order, and that `derive_differences` returns only through
`_finalize`.

**What "independent whole-bundle conformance" means here.** The Engine does not call
`scripts/difference_contract_validator.py`: doing so would make the auditor part of the
producer and destroy the independence the audit rests on. Instead the Engine runs the *same
authority objects* the auditor runs — `reference_closure_errors`,
`closure_evaluation_binding_errors`, `blocker_payload_errors`,
`next_observation_binding_errors` — and the contract suite runs the independent validator
over the bundles the Engine returns. Authority separation is preserved and no rule set is
duplicated. `ENGINE_EMBEDS_INDEPENDENT_AUDITOR=false` is recorded below as an explicit
non-claim.

## 6. Proofs added

```text
tests/contract/difference/test_reference_graph.py             32 cases
  - emitted record kinds == REFERENCE_EDGES keys == IDENTITY_EDGES keys, both directions
  - every resolvable kind and every identity edge names an emitted section
  - no kind is both resolvable and an enumerated non-claim
  - every declared edge kind is resolvable or enumerated; a resolve override never weakens
  - the Engine and the auditor hold the same edge-authority object
  - the whole-bundle gate is crossed exactly once, in order, on the only return path
  - the Engine holds no second union and no bare section assignment

tests/unit/difference/test_section_union.py                   48 cases
  - every populated emitted section: insert, idempotent duplicate, conflicting pair in
    either order and in one call, target unmutated on rejection, inputs unmutated
  - two bindings reusing one scope_id fail closed and leave the request unmodified
  - two distinct Scopes still derive and stay cross-record valid

tests/unit/difference/test_reference_closure.py               38 cases
  - one dangling-edge mutation per resolvable reference kind (20)
  - one dangling-key mutation per declared bare foreign key (11)
  - unresolvable foreign key, unresolvable reference, wrong kind, undeclared kind,
    ambiguous target
  - the unmutated lineage passes both the Engine gate and the independent validator

tests/unit/difference/test_scope_change_reobservation.py       7 cases
  - the lineage really carries one recurring Fact across two Scope ids
  - the boundary-change re-observation supersedes the prior Difference and stays
    cross-record valid
  - deleting, renaming or re-describing the historical Scope fails closed
  - a same-ID/different-payload Scope crossing two routes fails closed

tests/unit/difference/test_closure_evaluation_binding.py      24 cases
  - proposed terminal status, subject Difference, event head, Closure Policy, evaluated
    State revision and fingerprint, Target Predicate, Objective semantics, terminal gate
  - a reopen naming another closure
  - the Engine and the auditor call the same rule object
  - REOPENED: every binding rule holds and the residual non-claim is enumerated exactly
```

## 7. Acceptance

```text
CANONICAL_SECTION_UNION_COUNT=1
BARE_SECTION_ASSIGNMENT_COUNT=0
SECTIONS_COVERED_BY_UNION_TESTS=15
REFERENCE_EDGE_AUTHORITY_COUNT=1
EMITTED_KINDS_EQUAL_EDGE_REGISTRY_KINDS=true
RESOLVABLE_REFERENCE_KIND_COUNT=20
DECLARED_FOREIGN_KEY_COUNT=11
OBSERVATION_RESOLVED_AGAINST_OWN_SCOPE=true
OWN_SCOPE_RESOLVER_COUNT=1
CLOSURE_EVALUATION_BINDING_AUTHORITY_COUNT=1
WHOLE_BUNDLE_GATE_CROSSED_EXACTLY_ONCE=true
ENGINE_RETURN_PATH_COUNT=1

KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
CANONICAL_OWNER_COUNT=1
```

```text
ENGINE_EMBEDS_INDEPENDENT_AUDITOR=false
CLOSURE_EVALUATION_EXECUTION_IMPLEMENTED=false
REFLOW_COMMITMENT_CLAIMED=false
OBSERVATION_METHOD_CLOSURE=partial
TARGET_PREDICATE_RESOLVED_STRUCTURALLY=false
ALL_OUTPUT_SCHEMA_VALID=true   # qualified by UNSCHEMATIZED_SECTIONS
UNSCHEMATIZED_SECTIONS=changes, reflow_transitions
CHANGE_AND_REFLOW_SCHEMA_AVAILABLE=false
LATER_PHASE_SEMANTICS_CLAIMED=false
REOPENED_CROSS_RECORD_PROVEN=false   # binding rules proven; execution provenance is not
IMPACT_PROJECTION_UNCONSTRAINED=true
DIFFERENCE_RUNTIME_PROVEN=false
KERNEL_V0_1_COMPLETE=false
```

`REOPENED_CROSS_RECORD_PROVEN` stays false, and this ADR narrows exactly what it covers.
Every binding rule this phase owns now holds for a REOPENED lineage, and the reference
graph of that bundle is closed — a unit test asserts both. What the independent validator
still reports is *Closure Evaluation execution* provenance: candidate claim and invariant
bindings, Evidence sufficiency, mandatory gate outcomes, the Reflow commitment and the
VERIFYING minimum gate. Those belong to later elements this phase does not implement, and
fabricating them would be implementing Closure Evaluation execution rather than validating
caller-supplied provenance. The residual set is enumerated in the test, so a *new* kind of
error — or any binding error — fails it.
