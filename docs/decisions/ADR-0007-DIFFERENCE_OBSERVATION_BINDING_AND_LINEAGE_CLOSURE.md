# ADR-0007: Observation binding integrity, lineage closure and one request per event

```text
DOC_TYPE=ENGINE_AND_VALIDATOR_CONFORMANCE_CORRECTION
DOCUMENT_ID=ADR-0007-DIFFERENCE-OBSERVATION-BINDING-AND-LINEAGE-CLOSURE
STATUS=ACCEPTED
DECIDED_AT=2026-08-31
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0006
SOURCE=INDEPENDENT_REVIEW_OF_f2b1d89
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

An independent review of head `f2b1d89` raised three P1 findings. All three were
conformance defects against contracts that already stated the rule, and each was
reproduced against the pre-change Engine before it was corrected.

No Kernel contract text and no schema changed. No identity algorithm changed. Every
existing Difference identity and every existing Observation identity is unchanged, so
ADR-0002's migration record still stands and no migration is required.

```text
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
EXISTING_DIFFERENCE_IDENTITIES_CHANGED=0
EXISTING_OBSERVATION_IDENTITIES_CHANGED=0
CANONICAL_RECORD_MIGRATION_REQUIRED=false
```

## 1. Finding 1 - the bound Observation's own identity was never recomputed

**Defect.** ADR-0005 and ADR-0006 recomputed Fact, binding and evaluation identities before
trusting them, and validated the whole upstream payload through the Observation owner's
verifier. The Observation record itself was exempt. A caller could retain `observation_id`
while altering `method_ref`, `time_boundary`, `source_snapshot_refs`,
`normalization_profile`, the State binding, the Target or the Scope reference: every
lookup still resolved, the canonical Observation schema still passed, and the Difference
bound a record that was not the one its identity names.

**Correction.** The Observation identity projection now lives once, owned by the
Observation element, and is read from the record rather than assembled from a request:

```text
src/manosube_agent_civilization/observation/identity.py
  OBSERVATION_SEMANTIC_FIELDS
  observation_semantic_projection()
  observation_identity()
```

`observation/engine.py` was refactored to **mint** through it: the identity-bearing half of
the record is built first, the identity is derived from that projection, and the full
record is assembled from the same object. A contract test asserts the Engine contains no
`deterministic_id("OBS"` call of its own, so producer and verifier cannot drift. Every
existing Observation identity is bit-for-bit unchanged, which the conformance fixtures
prove.

The shared Observation verifier (`observation_record_errors`) now recomputes the identity
of every Observation in a bundle, so the Observation Engine and the Difference Engine
inherit the check from one place. While adding it, a latent robustness gap in that
verifier was closed: identity recomputation over a schema-invalid record would raise
`KeyError` instead of returning a verdict. Recomputation now runs only on records that
already passed their canonical schema; a malformed record is still reported, by the schema
rule that owns it.

**Boundary, not only identity.** A self-consistent identity is not admissibility. The
Difference Engine additionally verifies each Observation it consumes against the
**resolved canonical Scope** — project, Scope reference, declared method, exact source
snapshot set, and time-boundary containment — before any Fact, binding, evaluation or
Evidence reference it carries is read. The containment rule was extracted from
`observation/engine.py` into `observation/boundary.py::time_boundary_within_scope`, so the
Observation Engine that reports completeness and the consumer that verifies the binding
hold one rule.

An Observation produced by the real Observation Engine against a *different* Scope is
internally consistent and passes its own auditor, yet is correctly rejected here: its
source snapshots are not the ones the resolved Scope declares.

## 2. Finding 2 - a fresh derivation emitted a partial lineage

**Defect.** For a first Difference over an append-only Observation bundle — no Difference
predecessor — a recurring Fact already carries evaluations from the earlier and the current
Observation. The Engine carried the whole evaluation chain, because append-only semantics
forbid dropping a revision and the chain must stay contiguous to be read at all, but
carried only the *current* Observation's bindings. Every earlier evaluation's
`binding_refs` therefore dangled, and the earlier Observation and its Facts were absent.

Reproduced against the pre-change Engine: one binding carried where two were referenced,
one Observation where two were needed — and `validate_bundle` returned `[]`, so the
independent auditor did not catch it either.

**Correction — Engine.** Context absorption now computes the transitive closure to a
fixpoint over `Observation -> Fact -> evaluation -> binding -> Observation`. Nothing
required by append-only semantics is discarded, and every Observation the closure reaches
is verified against the resolved Scope before it is carried, so the closure can never
widen the Difference's boundary. A record the closure needs but the bundle does not hold
fails closed; the union rejects same-ID/different-payload records as before.

**Correction — independent auditor.** The Difference cross-record validator now requires,
for the bundle as a whole and not only for the records one Difference cites:

```text
fact_evaluation.fact_id        -> normalized_facts
fact_evaluation.binding_refs   -> fact_observation_bindings, of that same Fact
binding.observation_id         -> observations
binding.fact_id                -> normalized_facts
observation.normalized_fact_refs -> normalized_facts
```

This is the rule that would have caught the defect independently, and it is the auditor's
own to state: a carried record whose references do not resolve cannot be read back.

## 3. Finding 3 - two Next Observation Requests for one appended event

**Defect.** An equivalent re-observation of an unresolved or conflicted Difference already
at `BLOCKED`, `RETAINED` or `REOPENED` took two request-derivation paths: the
retained-status branch minted the status-specific request and set the event's reference,
then the unresolved-mismatch branch minted a second request for the *same* event and
overwrote that reference with a generic `BLOCKER_REOBSERVATION` one.

Reproduced against the pre-change Engine:

```text
BLOCKED   2 requests, both BLOCKER_REOBSERVATION  -> identical content address,
                                                     "duplicate canonical record"
RETAINED  2 requests, BLOCKER_REOBSERVATION + RETAINED_REOBSERVATION
          the event referenced the generic one; RETAINED_REOBSERVATION was orphaned
REOPENED  2 requests, BLOCKER_REOBSERVATION + REOPEN_REOBSERVATION, same outcome
```

**Contract basis.** `DIFFERENCE_LIFECYCLE.md` section 5 gives `next_observation_ref` as one
typed reference or null, and section 4 requires a blocker's `verification_request_ref` to
be **identical** to the event's `next_observation_ref`. Two requests for one event cannot
satisfy either. This was a conformance defect, not a rule gap.

**Correction.** There is now exactly one request-derivation path, and it is the only call
site of `_next_observation_request` inside `derive_differences` — a contract test asserts
that count. It runs once per appended event, after the chain is settled:

```text
reason = the retained status's own reason, when the appended event retains
         BLOCKED, RETAINED or REOPENED
       = BLOCKER_REOBSERVATION, when an unresolved or conflicted mismatch needs a
         further bounded observation on any other status
       = none otherwise
```

The retained status wins when both apply, because the status is what the next observation
must resolve. Deriving a request for an event that already carries one fails closed rather
than overwriting, and the request set became a keyed collection so a
same-ID/different-payload request is rejected at insertion instead of at later validation.
Predecessor-context requests now merge through the same fail-closed rule.

## 4. Proofs added

```text
tests/unit/difference/test_observation_binding_integrity.py   19 cases
  - all 9 Observation identity inputs forged while the id is retained, each asserting
    the payload really changed and the identity really broke
  - a self-consistent Observation built by the real Observation Engine against another
    Scope is rejected on its source snapshots
  - a window outside the Scope, and a method outside the Scope, both rejected even
    after the identity is recomputed to match
  - a forged *earlier* Observation in the lineage fails closed
  - nothing outside the projection is an identity input
  - the shared authority rejects what the canonical schema accepts
  - the bundle is not mutated and the route stays byte-deterministic

tests/unit/difference/test_lineage_closure.py                 10 cases
  - a fresh derivation with no predecessor over a two-Observation lineage carries every
    binding its evaluations reference, both Observations and all their Facts
  - the evaluation chain stays contiguous and complete
  - cross-record valid and deterministic
  - a missing binding, Observation or Fact fails closed
  - a contradicting duplicate in the union fails closed
  - the closure never widens the boundary

tests/unit/difference/test_next_observation_requests.py       21 cases
  - unresolved and conflicted routes x BLOCKED, RETAINED, REOPENED: exactly one request
    per appended event, with its own reason code, referenced by that event
  - no request id repeats and no event carries two
  - the BLOCKED route is cross-record valid, and its blocker condition and its event
    name the same single request
  - OPEN unresolved, OPEN retained, and resolved routes unaffected
  - a missing Observation Method projection still fails closed

tests/contract/difference/test_lifecycle_authority.py
  - one Observation identity authority, held by both engines and the shared verifier
  - the Observation Engine mints through it and defines no OBS identity input of its own
  - one time-boundary containment authority
  - exactly one Next Observation Request derivation path

tests/integration/difference/test_state_observation_difference.py
  - real State -> Observation -> Difference over a two-Observation lineage with no
    predecessor: no dangling reference, every Observation identity recomputes
  - a real Observation whose method was altered afterwards fails closed
```

## 5. Stated limit, unchanged

Full cross-record validity is proven end to end for a `BLOCKED` retained re-observation.
For `RETAINED` and `REOPENED` the appended event, its single request, its reason code and
its schema conformance are proven; what remains unvalidated concerns only the
caller-supplied Closure Evaluation and the upstream lifecycle events that reach those
statuses — records owned by later phases, which this Engine deliberately does not create.
The tests assert that every remaining message names such a record and none concerns a
Next Observation Request.

```text
RETAINED_AND_REOPENED_CROSS_RECORD_PROVEN=false
```

## 6. Acceptance

```text
OBSERVATION_IDENTITY_AUTHORITY_COUNT=1
OBSERVATION_IDENTITY_RECOMPUTED=true
OBSERVATION_MINTED_THROUGH_SHARED_PROJECTION=true
OBSERVATION_SCOPE_BOUNDARY_VERIFIED=true
TIME_BOUNDARY_AUTHORITY_COUNT=1
OUT_OF_SCOPE_SOURCE_REJECTED=true
EVERY_CONSUMED_OBSERVATION_VERIFIED=true

LINEAGE_CLOSURE_TRANSITIVE=true
CARRIED_EVALUATION_BINDINGS_RESOLVE=true
CARRIED_BINDING_REFERENCES_RESOLVE=true
PARTIAL_LINEAGE_NEVER_EMITTED=true
APPEND_ONLY_CHAIN_NEVER_TRUNCATED=true
AUDITOR_DETECTS_DANGLING_REFERENCES=true

NEXT_OBSERVATION_REQUEST_PATH_COUNT=1
ONE_REQUEST_PER_APPENDED_EVENT=true
STATUS_SPECIFIC_REASON_PRESERVED=true
DUPLICATE_REQUEST_FAILS_CLOSED=true
OPEN_UNRESOLVED_ROUTE_UNAFFECTED=true

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
DIFFERENCE_RUNTIME_PROVEN=false
KERNEL_V0_1_COMPLETE=false
```
