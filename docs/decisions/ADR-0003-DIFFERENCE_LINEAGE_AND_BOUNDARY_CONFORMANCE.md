# ADR-0003: Difference lineage, boundary and evaluable-knowledge conformance

```text
DOC_TYPE=ENGINE_CONFORMANCE_AND_CONTRACT_CLARIFICATION
DOCUMENT_ID=ADR-0003-DIFFERENCE-LINEAGE-AND-BOUNDARY-CONFORMANCE
STATUS=ACCEPTED
DECIDED_AT=2026-08-31
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0002
SOURCE=INDEPENDENT_REVIEW_OF_49d52ab
SCHEMA_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

An independent review of head `49d52ab` raised four acceptance findings. Three were
**Engine conformance defects**: the Engine failed to enforce rules the contracts and the
cross-record validator already stated. One was an **evaluation-rule conformance defect**
present in both the Engine and the independent auditor, accompanied here by a contract
clarification that makes the already-stated rule unambiguous.

No schema changed. No identity algorithm changed. No canonical record shape changed.
Every existing Difference identity in the repository is unchanged by this ADR, so no
migration is required and `ADR-0002`'s migration record still stands as written.

```text
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
EXISTING_DIFFERENCE_IDENTITIES_CHANGED=0
CANONICAL_RECORD_MIGRATION_REQUIRED=false
```

## 1. Finding 1 - predecessor event identity was not recomputed

**Defect.** `_validate_predecessor` checked revision linkage and the bound Difference ID,
but never recomputed each `difference_event_id` from its payload. A caller could alter an
identity-bearing field - `reason_code`, `event_kind`, `from_status`, `to_status`,
`state_revision_evaluated`, `state_fingerprint_evaluated`, `observation_refs` or
`evidence_refs` - while retaining the old event ID. The forged event was then copied into
the returned append-only lineage and used as the predecessor of a new event.

**Correction.** Every event in the chain, not only its head, must satisfy

```text
event.difference_event_id == lifecycle_event_id(event)
```

before it is copied or appended. This uses the same single identity authority the Engine
uses to mint events; no parallel algorithm was introduced.

**Contract basis.** `DIFFERENCE_IDENTITY.md` section 7 already required
`SAME ID + DIFFERENT IMMUTABLE PAYLOAD -> REJECT OR QUARANTINE`, and section 6 already
required that a Supersession Relation resolve from both Differences and both Lifecycle
Events. The Engine simply did not enforce it for provenance events.

## 2. Finding 2 - equivalent re-observation dropped its predecessor context

**Defect.** `_absorb_predecessor_context` was called only on the material-change
supersession branch. On the equivalent re-observation branch the prior events were
retained but their supporting records were not, so the returned bundle contained a genesis
event referencing an Observation, Facts, bindings and evaluations that were absent from
the bundle. The lineage was append-only in shape but unresolvable in fact.

**Correction.** The equivalent re-observation branch now absorbs the predecessor context
through the same single context-absorption authority. The returned bundle carries both
Observations, both bindings, the full Fact evaluation chain, and the prior Scope, Policy
and Objective revision records.

**Contract basis.** `DIFFERENCE_CONTRACT.md` section 8 requires that re-observation append
a new Observation binding and Lifecycle Event to a preserved identity, and section 7
requires the materialized view be deterministically reconstructable from the lineage. A
lineage whose events cannot be resolved is not reconstructable.

### Related: Observation selection under an append-only lineage

Threading the real append-only Observation lineage exposed a second, latent defect.
`_select_observation` matched on Target and Scope alone, which is ambiguous once a bundle
carries more than one Observation. It now selects on the **exact requested Project State**
as well, and reports a stale binding when Observations exist for the Target and Scope but
none is bound to the requested State. This tightens, and never relaxes, the existing
`STATE_BINDING_MISMATCH -> INVALIDATED` rule.

## 3. Finding 3 - bounded proven absence could not satisfy `none`

**Defect.** Both the Engine projection and the independent auditor computed

```text
comparison = UNKNOWN if knowledge != KNOWN else ...
```

which forced every non-`KNOWN` status, including proven `ABSENT` and `EMPTY`, to
`UNKNOWN`. For a `none` Target over a complete scope with bounded Negative Evidence and no
candidates, the result was an incoherent `UNKNOWN` comparison paired with an `UNEXPECTED`
mismatch, instead of the required satisfied, empty Difference result.

**Correction.** Operator evaluation is reached by a closed set of evaluable statuses:

```text
EVALUABLE_KNOWLEDGE  = KNOWN | ABSENT | EMPTY
UNRESOLVED_KNOWLEDGE = UNKNOWN | UNOBSERVED | BLOCKED | INCOMPLETE
```

`ABSENT` and `EMPTY` are conclusions backed by bounded Negative Evidence and a complete
enumeration gate, not unresolved observations, so they are evaluable. Unresolved statuses
are still short-circuited to `UNKNOWN` before any operator runs, so `NO_RESULT` and
`UNOBSERVED` can never become proven absence or satisfaction. Positive operators over an
empty evaluated set still reach `MISSING`, so no vacuous truth is introduced.

```text
PROVEN_EMPTY + none  -> SATISFIED     -> no Difference
PROVEN_EMPTY + all   -> NOT_SATISFIED -> MISSING
UNRESOLVED   + none  -> UNKNOWN       -> UNKNOWN
```

The Engine's satisfied-route gate additionally accepts a completed `EMPTY` Observation
status alongside `COMPLETE`; `EMPTY` is a bounded complete enumeration, not an incomplete
scope. `scope_status` must still be `COMPLETE`.

**Contract basis.** `DIFFERENCE_IDENTITY.md` already stated that `none` alone may be
satisfied by an empty set given a complete Scope and bounded Negative Evidence, and listed
only `UNKNOWN`, `UNOBSERVED`, `BLOCKED`, `INCOMPLETE` and `CONFLICTED` as statuses that may
never be satisfied. This was therefore a conformance defect, not a rule change. The
contract text now names the evaluable and unresolved sets explicitly so the rule cannot be
read the other way again.

Both the Engine and the independent auditor were corrected together, and a contract test
now asserts the two derivations agree on every comparison route.

## 4. Finding 4 - the Negative Observation boundary was not validated

**Defect.** The Engine selected contributing Negative Observations by Observation ID,
Target identity and subject only. A schema-valid record from another project, Scope,
method, time window or source snapshot could therefore be interpreted as bounded
`ABSENT`/`EMPTY` proof, and its Evidence bound into the Difference, while the derived
boundary was taken from the positive Observation rather than verified against the negative
record. On the conflict route the cross-record validator does not require
`source_negatives_valid`, so the defect was reachable there as well.

**Correction.** Before any status or Evidence is interpreted, every contributing Negative
Observation must match the bound Observation exactly on:

```text
schema_version
project_id
target_identity            (selection)
subject                    (selection, and inside the resolved Scope)
observation_id             (selection)
scope_ref                  (and equal to the resolved Scope's scope_id)
method_ref                 (and equal to the Scope's declared method)
time_boundary
source_snapshot_refs
effective_boundary         (SOURCE_SNAPSHOT, declared identity, null start and end)
```

State binding is covered transitively: the Observation itself is validated against the
exact requested Project State, and the negative record must be bound to that Observation.
Only after these checks does the shared derived boundary legitimately apply.

**Contract basis.** `DIFFERENCE_CONTRACT.md` section 3 requires exact input binding and
`UNKNOWN_REFERENCE -> REJECT_OR_QUARANTINE`; `DIFFERENCE_IDENTITY.md` section 2 requires
the observed source to be selected under same project and State binding with an exact Scope
match. The cross-record validator already enforced these for the pure-negative route. The
Engine now enforces them on every route.

## 5. Proofs added

```text
tests/unit/difference/test_lineage_and_boundary.py            41 cases
  - 16 forged-identity mutations across 8 identity-bearing fields x genesis and head
  - forged identity in the middle of a longer chain
  - a valid multi-event chain is accepted and every event recomputes
  - equivalent re-observation returns a self-contained, resolvable lineage
  - bounded ABSENT/EMPTY satisfies none; NO_RESULT/UNOBSERVED never does
  - proven absence still MISSING for equals, all and exists
  - 7 Negative Observation boundary mutations, plus schema version, scope escape,
    conflict-route enforcement and the valid bounded-absence case

tests/contract/difference/test_difference_engine_conformance.py
  - Engine and independent auditor agree on every comparison route
  - both authorities agree that bounded absence satisfies none
  - both authorities agree that unresolved knowledge never does
  - equivalent re-observation bundle is cross-record valid and self-contained
  - every returned event identity recomputes

tests/integration/difference/test_state_observation_difference.py
  - real State -> Observation -> Difference for none over ABSENT, EMPTY,
    NO_RESULT and UNOBSERVED
  - real append-only re-observation lineage is self-contained

tests/contract/fixtures/difference/invalid/negative_cases.json
  - 9 added boundary mutations: cross project, cross scope, cross method,
    wrong time window, wrong source snapshot, effective boundary escape,
    unbounded effective window, cross target, stale Observation binding
```

## 6. Acceptance

```text
PREDECESSOR_EVENT_IDENTITY_RECOMPUTED=true
FULL_PREDECESSOR_CHAIN_VALIDATED=true
REOBSERVATION_LINEAGE_SELF_CONTAINED=true
OBSERVATION_SELECTED_BY_EXACT_STATE=true
PROVEN_ABSENCE_SATISFIES_NONE=true
UNRESOLVED_NEVER_SATISFIES=true
NO_RESULT_NE_PROVEN_ABSENCE=true
VACUOUS_TRUTH_PROHIBITED=true
NEGATIVE_BOUNDARY_FULLY_VALIDATED=true
ENGINE_AND_AUDITOR_AGREE=true

SCHEMA_CHANGED=false
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

```text
DIFFERENCE_RUNTIME_PROVEN=false
KERNEL_V0_1_COMPLETE=false
```
