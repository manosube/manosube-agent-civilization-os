# ADR-0006: Difference Record immutability and upstream payload validation

```text
DOC_TYPE=ENGINE_CONFORMANCE_AND_CONTRACT_CLARIFICATION
DOCUMENT_ID=ADR-0006-DIFFERENCE-IMMUTABLE-RECORD-AND-UPSTREAM-PAYLOAD
STATUS=ACCEPTED
DECIDED_AT=2026-08-31
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0005
SOURCE=INDEPENDENT_REVIEW_OF_9bfb176
KERNEL_CONTRACT_FILES_CHANGED=1
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

An independent review of head `9bfb176` raised two P1 findings. Both were **Engine
conformance defects**: the contracts already required the behaviour, and the Engine did
not enforce it. Correcting the first exposed a third defect, present in both the Engine
and the independent auditor, which made an immutable record un-revalidatable across its
own lineage.

No schema changed and no identity algorithm changed. Every existing Difference identity is
unchanged, so ADR-0002's migration record still stands and no migration is required.

```text
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
EXISTING_DIFFERENCE_IDENTITIES_CHANGED=0
CANONICAL_RECORD_MIGRATION_REQUIRED=false
```

One Kernel contract file gained two clarifying paragraphs. Both state rules the contract
already implied and both **narrow** what is acceptable; neither adds, removes or relaxes
an enum, a required field, an identity input or a Completion gate.

## 1. Finding 1 - an equivalent re-observation rewrote the record it preserved

**Defect.** On the equivalent re-observation route the Engine kept the predecessor's
identity and its event chain, but returned the **newly constructed** Difference under that
identity. Every field outside the identity tuple was silently replaced:
`observed_state_revision`, `observed_state_fingerprint`, `observation_refs`,
`observation_evidence_refs`, `normalized_observed_state`, `objective_revision_ref` and
`genesis_event_ref`. The record's own genesis binding was overwritten with the newest
Observation while the retained genesis event still claimed the original one.

The collision guard did not catch it, because `DIFFERENCE_IDENTITY.md` section 7 compares
only the immutable semantic identity input, and re-observation provenance is deliberately
excluded from that comparison. Excluding provenance from *identity* was never permission
to *overwrite* it.

**Contract basis.** `DIFFERENCE_IDENTITY.md` section 5 already fixed the route as

```text
REOBSERVATION -> SAME DIFFERENCE ID -> APPEND OBSERVATION BINDING
              -> APPEND OBSERVATION_BOUND EVENT
```

and section 7 already stated that a later payload must not overwrite an earlier one. This
was therefore a conformance defect, not a rule change.

**Correction.** The equivalent route now returns `deepcopy(prior_difference)` byte for
byte. The new State revision, State fingerprint, Observation binding and Evidence binding
are represented only by the appended `OBSERVATION_BOUND` event and the records that event
references, all of which travel in the returned bundle.

Three guards were added so that returning the predecessor cannot itself become a hole:

```text
closure_policy.id            must recompute from its own fingerprint and this identity
closure_policy fingerprint   must equal the fingerprint this derivation re-derived
genesis_event_ref            must name the retained chain's own genesis, never rewritten
```

The Closure Policy record is now built from the record actually returned, and the retained
projections are re-checked for duplicate unordered-set members. The identity-collision
guard on same-ID/different-identity-payload is unchanged and still fires.

The contract text now says plainly that the record is immutable under its identity, so the
"do not duplicate" rule cannot be read as permitting an in-place replacement instead.

## 2. Related: an immutable record must survive its own lineage

Returning the predecessor made a latent defect reachable, in the Engine and in the
independent auditor alike.

**Defect.** Both selected the **globally latest** Fact Evaluation for a Normalized Fact and
then required it to be bound to the Difference's own Observation. Under an append-only
Observation lineage a re-observation appends a further evaluation bound to the **next**
Observation, so the moment a subject is re-observed, every earlier Difference Record fails
`source_facts_valid` -- `Difference projection mismatch`. An immutable record cannot be
revalidated after the lineage moves past it.

**Correction.** Selection is scoped to the Observation the record binds:

```text
the applicable Fact Evaluation = the highest-revision evaluation bound to THIS Observation
```

Selection happens **before** any status is read, so a later re-evaluation of the *same*
Observation still governs and still fails closed; only an evaluation belonging to a
*different* Observation is excluded, and that evaluation is evidence about that other
Observation, which owns its own Difference. The accepted set therefore widens by exactly
the canonical append-only re-observation case and by nothing else.

The Engine and the auditor were corrected together and a contract test asserts the two
selections agree, for every Observation in a real two-Observation lineage. A second test
proves a superseding `INVALID` re-evaluation of the same Observation is still selected and
still rejected.

`DIFFERENCE_IDENTITY.md` section 2 already fixed the derivation order at "State-bound
observed input selection"; the added paragraph names which evaluation that selection
resolves to, because two independent implementations read it the other way.

## 3. Finding 2 - upstream Fact-evaluation payload was never validated

**Defect.** `fact_evaluation_identity()` is derived from `fact_id` and
`evaluation_revision` only. A caller could keep an evaluation's identity, flip
`evaluation_status` from `SUPPORTED` to `CONFLICTED` with empty
`conflict_fact_refs` and `conflict_negative_observation_refs`, and pass every check the
Engine made: the identity recomputed, the reference resolved, and a `CONFLICT` Difference
was derived from a payload the canonical Fact Evaluation schema forbids. The
schema-violating record was then copied into the returned bundle.

Identity recomputation and payload validation are **distinct obligations**, and the Engine
performed only the first. Recomputing an identity proves that the identity-bearing
projection is unchanged; it says nothing about the fields outside it.

**Correction.** The rules that decide payload admissibility already existed, once, inside
the Observation Engine's `_validate_records`, where no other consumer could reach them.
They are now owned by the Observation element and shared:

```text
src/manosube_agent_civilization/observation/verification.py :: observation_record_errors
src/manosube_agent_civilization/observation/schemas.py      :: the canonical registry
```

`observation/engine.py::_validate_records` is now one delegating call, and the Difference
Engine calls the same function before any status, value, conflict reference or Evidence
reference is trusted. **The Difference Engine states no evaluation rule of its own**: it
does not name `conflict_fact_refs`, and it does not validate an upstream evaluation
against any schema itself.

```text
OBSERVATION_RECORD_VERIFICATION_AUTHORITY_COUNT=1
```

The shared authority covers exactly the six canonical Observation record schemas, each
record's schema conformance, Fact and Binding identity recomputation, canonical payload
form, contiguous evaluation lineage with correct predecessor linkage, binding references
belonging to their own Fact, Negative revision-zero status and conflict agreement, and
mutual Fact/Negative conflict declaration. Identity recomputation is retained, runs first
so it keeps its precise diagnosis, and is **not** described as payload validation.

Three existing fail-closed tests now fail closed one step earlier, at the shared authority
rather than at the Difference Engine's own defence-in-depth rule. Each was rewritten to
state which authority rejects it, and one was strengthened: the `INVALID` Negative
Observation case now mutates the record and its evaluation together, so the bundle stays
cross-record valid upstream and the rejection provably comes from the Difference Engine.

## 4. Proofs added

```text
tests/unit/difference/test_immutable_predecessor.py           23 cases
  - the predecessor record is returned byte for byte
  - the caller's predecessor object is never mutated
  - 8 fields outside the identity tuple keep the predecessor's value
  - the appended event really does carry a new State, Observation and Evidence binding
  - genesis resolves its original Observation; the append binds the new one
  - the retained chain is contiguous, append-only and verbatim
  - the returned bundle is cross-record valid and the route is deterministic
  - 4 forged identity fields, a forged Closure Policy id, a redirected genesis
    reference and an unresolvable Observation binding all fail closed

tests/unit/difference/test_upstream_payload.py                18 cases
  - the exact forgery: retained identity, status flipped to CONFLICTED, empty
    conflict lists -- the identity still recomputes, the bundle is still rejected
  - a spy proves no candidate is projected from the forgery, and proves the
    valid route does reach projection
  - 8 independent conflict, reference, lineage and status mutations
  - 4 non-supporting evaluation statuses cannot project a candidate
  - a one-sided conflict declaration is rejected
  - the valid route still derives and validates
  - the shared verifier and the independent Observation auditor agree
  - the shared verifier does not mutate the bundle

tests/contract/difference/test_lifecycle_authority.py
  - exactly one Observation record-verification authority, held by both engines
  - the Observation Engine keeps no ruleset of its own
  - the Difference Engine names no evaluation rule and no evaluation schema
  - the authority covers exactly the six canonical Observation record schemas
  - payload validation and identity recomputation both precede projection

tests/contract/difference/test_difference_engine_conformance.py
  - Engine and auditor agree on Observation-scoped evaluation selection
  - a later re-evaluation of the same Observation still governs and still fails closed

tests/integration/difference/test_state_observation_difference.py
  - real State -> Observation -> Difference equivalent re-observation leaves the
    record unchanged while the appended event carries the new binding
```

## 5. Acceptance

```text
PREDECESSOR_RECORD_IMMUTABLE=true
PREDECESSOR_RETURNED_BYTE_IDENTICAL=true
NEW_BINDING_ONLY_VIA_APPENDED_EVENT=true
SAME_ID_DIFFERENT_PAYLOAD_STILL_REJECTED=true
RETAINED_LINEAGE_SELF_CONTAINED=true
IMMUTABLE_RECORD_REVALIDATABLE_ACROSS_LINEAGE=true
OBSERVATION_SCOPED_EVALUATION_SELECTION=true
SAME_OBSERVATION_REEVALUATION_STILL_GOVERNS=true
UPSTREAM_EVALUATION_PAYLOAD_VALIDATED=true
OBSERVATION_RECORD_VERIFICATION_AUTHORITY_COUNT=1
DIFFERENCE_ENGINE_STATES_NO_EVALUATION_RULE=true
IDENTITY_RECOMPUTATION_STILL_REQUIRED=true

KERNEL_CONTRACT_FILES_CHANGED=1
SCHEMA_FILES_CHANGED=0
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
