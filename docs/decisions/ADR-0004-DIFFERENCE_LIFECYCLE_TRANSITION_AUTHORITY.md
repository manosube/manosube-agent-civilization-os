# ADR-0004: Single lifecycle transition authority and retained-status provenance

```text
DOC_TYPE=ENGINE_CONFORMANCE_AND_OWNERSHIP_CORRECTION
DOCUMENT_ID=ADR-0004-DIFFERENCE-LIFECYCLE-TRANSITION-AUTHORITY
STATUS=ACCEPTED
DECIDED_AT=2026-08-31
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0003
SOURCE=INDEPENDENT_REVIEW_OF_9004df7
CONTRACT_CHANGED=false
SCHEMA_CHANGED=false
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

An independent review of head `9004df7` raised three lifecycle findings. All three were
Engine conformance defects against `DIFFERENCE_LIFECYCLE.md`, plus one cross-record
validator defect that made a contract-legal record shape unrepresentable.

**No Kernel contract text, no schema and no identity algorithm changed.** Every existing
Difference identity is unchanged, so ADR-0002's migration record still stands and no
migration is required.

```text
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
EXISTING_DIFFERENCE_IDENTITIES_CHANGED=0
CANONICAL_RECORD_MIGRATION_REQUIRED=false
```

One conformance fixture was regenerated so its lifecycle event identities recompute under
the canonical algorithm; its Difference identity is unchanged, because event identities
are not Difference identity inputs.

## 1. The single lifecycle transition authority

`LEGAL_TRANSITIONS` previously existed only inside `scripts/difference_contract_validator.py`,
where the Engine could not reach it. Rather than transcribe a second table, the executable
projection of `DIFFERENCE_LIFECYCLE.md` section 3 now lives once in

```text
src/manosube_agent_civilization/difference/lifecycle.py
```

and the independent validator imports it. That validator already depended on the package
for canonical serialization and fingerprinting, so this introduces no new coupling
direction and creates no parallel owner.

```text
LEGAL_TRANSITION_TABLE_COUNT=1
```

A contract test parses the section 3 table out of `DIFFERENCE_LIFECYCLE.md` and asserts it
equals the executable set, and a second test asserts the validator holds the identical
object and no longer defines a table of its own. The code therefore cannot drift from the
contract, in either direction.

The module also names the derived facts the contract already implies, so no consumer
re-derives them by hand: `TERMINAL_STATUSES` (`SUPERSEDED`, `INVALIDATED` — `CLOSED` is
deliberately absent, because it can be reopened), `OBSERVATION_BOUND_FORBIDDEN`,
`REQUIRES_NEXT_OBSERVATION` and `NEXT_OBSERVATION_REASON`.

## 2. Finding 1 - illegal predecessor transitions were accepted

**Defect.** `_validate_predecessor` checked revision linkage, Difference binding and event
identity, but never status continuity or transition legality. A caller could supply an
identity-valid chain containing, for example, `DETECTED -> VERIFYING`, recompute that
event's identity, and pass every check. The chain was then copied into the returned
lineage even though the independent validator reports `illegal lifecycle transition`.

**Correction.** Every predecessor event is now additionally validated for

```text
schema conformance (difference_lifecycle_event.schema.json)
status continuity          from_status == previous.to_status
TRANSITION legality        (from_status, to_status) in LEGAL_TRANSITIONS
OBSERVATION_BOUND rules    from_status == to_status, and not on CLOSED/SUPERSEDED/INVALIDATED
```

`CLOSED` is no longer treated as terminal for predecessor acceptance, because the contract
does not treat it as terminal; only `SUPERSEDED` and `INVALIDATED` are.

## 3. Finding 2 - supersession was hard-coded to OPEN

**Defect.** `_supersede` rejected any predecessor whose head was not `OPEN`. The contract
gives `ACTIVE`, `VERIFYING`, `BLOCKED`, `RETAINED`, `CLOSED` and `REOPENED` legal
transitions to `SUPERSEDED` as well, so a material identity change arriving after the
Difference had progressed could not produce its canonical successor at all.

**Correction.** Legality is derived from the single authority:

```python
if not is_legal_transition(head["to_status"], "SUPERSEDED"):
    raise DifferenceError(...)
```

and the terminal event records the real `from_status` rather than a hard-coded `OPEN`.
Prohibited and terminal sources are still rejected. Event revision, predecessor linkage,
identity recomputation, the bidirectional Supersession Relation and full predecessor
context carry-forward are unchanged.

```text
LEGAL_SUPERSESSION_SOURCES = ACTIVE | BLOCKED | CLOSED | OPEN | REOPENED | RETAINED | VERIFYING
```

## 4. Finding 3 - status-preserving appends dropped required payload

**Defect.** `_observation_bound_event` set `from_status` and `to_status` to the retained
status but left every other field at its empty default. For a predecessor at `BLOCKED`
that emitted null blocker fields and no next-observation reference; for `RETAINED` and
`REOPENED` it omitted their required next-observation reference. Schema validation then
raised instead of appending the contractually allowed status-preserving event.

**Correction.** The append now carries whatever its retained status requires:

- `BLOCKED` re-derives the blocker kind, scope and resolution condition from the
  predecessor's own payload, **replacing** the effective boundary with the current
  Difference's boundary and the verification request with a freshly minted one;
- `BLOCKED`, `RETAINED` and `REOPENED` each receive a **new** Next Observation Request,
  derived from this event, with the reason code their status requires
  (`BLOCKER_REOBSERVATION`, `RETAINED_REOBSERVATION`, `REOPEN_REOBSERVATION`).

No forward reference is ever copied: the predecessor's own request is carried forward as
provenance, while the retained event points only at the request derived from itself. Both
resolve inside the returned self-contained bundle. The event identity input still excludes
the forward-looking `next_observation_ref` and the blocker payload, so no identity cycle
exists.

Predecessor context absorption was extended to every dependency section a retained event
may reference — Closure Evaluations, Reflow transitions, Changes, reopen condition
evaluations, candidate records, invariant evaluations and evidence sufficiency results, as
well as Next Observation Requests and Observation Methods. **The Engine creates none of
them**; it only preserves what the caller supplied, so a retained event's own references
still resolve.

## 5. Validator correction: provenance appends are not terminal transitions

The cross-record validator required a Closure Evaluation for **any** event whose
`to_status` is `CLOSED`, `BLOCKED` or `RETAINED`, including a status-preserving
`OBSERVATION_BOUND` append. `DIFFERENCE_LIFECYCLE.md` section 5 states that an
`OBSERVATION_BOUND` event is a provenance append and does not produce a status change, so
it does not re-enter the terminal status and cannot owe a fresh Evaluation — the
`TRANSITION` that entered the status owns it.

The branch is now gated on `event_kind == "TRANSITION"`. This removes an impossible
obligation; it does not relax any check on an actual transition, and it does not implement
Closure Evaluation, which remains a later owner's responsibility.

## 6. Proofs added

```text
tests/contract/difference/test_lifecycle_authority.py         8 cases
  - the executable table equals the parsed section 3 contract table
  - the validator imports it and defines no table of its own
  - terminal statuses have no outgoing transition; CLOSED is not terminal
  - the derived sets are consistent with the table

tests/unit/difference/test_retained_status_lineage.py        25 cases
  - 6 illegal predecessor transitions rejected; status-continuity break rejected
  - a predecessor OBSERVATION_BOUND event may not mutate status
  - material supersession from all 7 legal source states
  - supersession rejected from every prohibited source state
  - retained BLOCKED re-observation is cross-record valid, with re-derived blocker
    payload, a fresh request, and the predecessor's records carried forward
  - RETAINED and REOPENED appends carry their required request and reason code
  - OPEN needs no next-observation reference
  - missing blocker payload fails closed
  - a stale blocker boundary is re-derived, not copied
  - a stale forward reference is never reused

tests/integration/difference/test_state_observation_difference.py
  - real State -> Observation -> Difference retained BLOCKED re-observation
```

Full cross-record validity is proven end to end for a `BLOCKED` predecessor. For
`RETAINED` and `REOPENED` the emitted event, its payload, its schema conformance and its
freshly derived request are proven; complete cross-record validity of those two
predecessors additionally requires Closure Evaluation modes (`CANDIDATE_TERMINAL`) and
Reflow records owned by later phases, which this Engine deliberately does not create.
Recording that boundary is preferable to fabricating an upstream owner's records.

## 7. Acceptance

```text
LEGAL_TRANSITION_TABLE_COUNT=1
EXECUTABLE_TABLE_EQUALS_CONTRACT=true
ILLEGAL_PREDECESSOR_TRANSITION_REJECTED=true
PREDECESSOR_STATUS_CONTINUITY_ENFORCED=true
PREDECESSOR_SCHEMA_VALIDATED=true
SUPERSESSION_FROM_EVERY_LEGAL_SOURCE=true
SUPERSESSION_FROM_PROHIBITED_SOURCE_REJECTED=true
RETAINED_STATUS_PAYLOAD_PRESERVED=true
RETAINED_NEXT_OBSERVATION_REDERIVED=true
STALE_FORWARD_REFERENCE_NEVER_COPIED=true
PROVENANCE_APPEND_OWES_NO_CLOSURE_EVALUATION=true

CONTRACT_CHANGED=false
SCHEMA_CHANGED=false
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
CLOSURE_EVALUATION_IMPLEMENTED=false
REFLOW_IMPLEMENTED=false
```

```text
DIFFERENCE_RUNTIME_PROVEN=false
KERNEL_V0_1_COMPLETE=false
```
