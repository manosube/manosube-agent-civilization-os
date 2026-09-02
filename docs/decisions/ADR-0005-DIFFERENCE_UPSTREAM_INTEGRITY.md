# ADR-0005: Fact boundary authority, upstream identity verification and predecessor context

```text
DOC_TYPE=CONTRACT_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0005-DIFFERENCE-UPSTREAM-INTEGRITY
STATUS=ACCEPTED
DECIDED_AT=2026-08-31
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0004
SOURCE=INDEPENDENT_REVIEW_OF_6d169d2
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

An independent review of head `6d169d2` raised three P1 findings. One was a
**cross-record validator defect** that made a contract-legal Observation shape
underivable; two were **Engine conformance defects** that let forged upstream input pass.

No Kernel contract text and no schema changed. No identity algorithm changed. Every
existing Difference identity is unchanged, so ADR-0002's migration record still stands and
no migration is required.

```text
EXISTING_DIFFERENCE_IDENTITIES_CHANGED=0
CANONICAL_RECORD_MIGRATION_REQUIRED=false
```

## 1. Finding 1 — only one Fact boundary kind could reach a Difference

**What the review said, and what was actually true.** The review stated that the
independent Difference validator "explicitly accepts both forms". That is only half
right, and the distinction matters:

- `_fact_boundary_observed()` in the validator does accept all three kinds — but it was
  used **only** in the closure/candidate section (`positive_facts_valid`);
- the **Difference projection** check (`source_projection_valid`) separately required
  `fact["effective_boundary"]["kind"] == "SOURCE_SNAPSHOT"`.

So the Engine's restriction matched the validator exactly. The defect was not that the
Engine disagreed with the auditor; it was that **both** agreed on a rule that contradicts
the Normalized Fact schema, which declares three legal kinds:

```text
01_SCHEMA/observation/normalized_fact.schema.json
effective_boundary.kind = TIME_INTERVAL | STATE_REVISION | SOURCE_SNAPSHOT
```

A canonical Observation carrying a `TIME_INTERVAL` or `STATE_REVISION` Fact — which the
Observation Engine produces and its own contract validator accepts — could never yield a
Difference at all. This is the same class of defect as ADR-0002's unreachable
pure-negative route: a contract-legal route with no conformant representation.

**Correction.** The matching rule now lives once, owned by the Observation element:

```text
src/manosube_agent_civilization/observation/boundary.py :: fact_boundary_observed
```

`observation/engine.py::_boundary_observed`, the validator's `_fact_boundary_observed`,
and the Difference Engine all delegate to it. Two byte-identical copies of the rule
previously existed; now there is one.

The Difference projection check was replaced with that authority, matched against an
Observation the Difference actually binds. The previous rule also required the Fact's
snapshot identity to appear in the Difference's `effective_boundary.source_snapshot_refs`;
for `SOURCE_SNAPSHOT` this is implied by the authority plus the already-enforced equality
between the Difference boundary's snapshot set and the Observation's, so nothing is
weakened — the change is strictly more representable and equally strict.

While applying this, a latent scoping bug in the validator was found and fixed: the
projection check would have read a leaked `observation` loop variable from an earlier
section rather than the Difference's own source Observation. The check now binds
explicitly to `source_observations`.

**Not relaxed.** A mismatched snapshot identity, a snapshot boundary carrying a window, a
wrong effective window, a wrong State revision and an unknown kind are all still rejected.

## 2. Finding 2 — upstream identities were trusted, not recomputed

**Defect.** The Engine resolved Normalized Facts, bindings and evaluations by reference
lookup and schema validity only. A caller could change an identity-bearing field of a Fact
— `value`, `subject`, `predicate`, `value_type`, `unit`, `project_id`,
`effective_boundary`, `normalization_profile` — while retaining the original `fact_id`.
Every lookup still resolved, the forged value was projected into the observed candidates,
and the altered Fact was copied into the returned bundle, even though the independent
validator reports `Normalized Fact identity mismatch`.

**Correction.** Before candidate projection, the Engine recomputes every identity-bearing
upstream record it is about to trust, using the **Observation element's own algorithms**
rather than a parallel implementation:

```text
fact_identity(fact)                  == fact["fact_id"]
binding_identity(binding)            == binding["binding_id"]
fact_evaluation_identity(evaluation) == evaluation["evaluation_id"]
```

To guarantee one algorithm rather than two, `observation/identity.py` now owns
`fact_semantic_projection()` and `normalize_fact()` was refactored to use it, so the
verifier and the producer share a single closed projection. A contract test asserts
`normalize_fact` holds those very objects, and another asserts the Engine's recomputation
equals the independent auditor's `_fact_id`.

Schema version is also verified per Fact, and every binding for the bound Observation must
reference a Fact present in the bundle.

## 3. Finding 3 — an incomplete predecessor context was accepted

**Defect.** `context` defaulted to `{}` and `_validate_predecessor()` validated only the
Difference and its events, never whether their references resolve. A predecessor carrying
just `difference` and `events` was accepted: the retained genesis event stayed in the
returned chain while its Observation, Facts, bindings and evaluations were absent. The
cross-record validator did not catch it either, because it does not check that a
non-blocked event's `observation_refs` resolve.

**Correction.** After the binding's own context is absorbed, every reference the retained
lineage carries must resolve inside the returned bundle:

```text
difference.observation_refs            -> observations
difference.objective_revision_ref      -> objective_revisions
difference.objective_scope_binding     -> observation_scopes
difference.closure_policy              -> policies
difference.genesis_event_ref           -> the returned event chain
event.observation_refs                 -> observations
event.next_observation_ref             -> next_observation_requests
event.closure_evaluation_ref           -> evaluations
event.reflow_transition_ref            -> reflow_transitions
event.change_refs                      -> changes
event.reopen_condition_evaluation_ref  -> reopen_condition_evaluations
blocker_resolution_condition.verification_request_ref -> next_observation_requests
blocker_scope.affected_subject_refs    -> this Difference only
observation.normalized_fact_refs       -> normalized_facts
fact_evaluation.binding_refs           -> fact_observation_bindings
```

This runs for **both** retained lineages: the same Difference on an equivalent
re-observation, and the superseded Difference on a material change.

A same-ID/different-payload context is also rejected. Where the carried context and the
canonical Observation bundle name the same record, the payloads must be byte-identical —
a contradicting context is a forgery, not provenance.

A section the current derivation legitimately re-supplies (the objective revision, scope
or policy of an equivalent re-observation) still resolves, and is correctly accepted: the
requirement is that every retained reference resolves in the returned bundle, not that the
caller duplicate records the derivation already provides.

## 4. Proofs added

```text
tests/unit/difference/test_upstream_integrity.py             32 cases
  - all three Fact boundary kinds derive a cross-record-valid Difference
  - Engine, Observation owner and auditor agree on each kind
  - 7 mismatched-boundary mutations rejected
  - 8 forged Fact identity inputs fail closed, plus binding and evaluation identities
  - the Engine's recomputation equals the auditor's _fact_id
  - predecessor with no context, empty context, or a missing referenced section rejected
  - forged same-ID context payload rejected
  - self-contained predecessor accepted, for re-observation and for supersession

tests/contract/difference/test_lifecycle_authority.py
  - exactly one Fact boundary authority; Observation engine and validator both hold it
  - the authority covers exactly the kinds the Normalized Fact schema declares
  - normalize_fact and the identity verifier share one semantic projection

tests/integration/difference/test_state_observation_difference.py
  - real State -> Observation -> Difference for each boundary kind
  - a real Observation whose Fact payload was altered afterwards fails closed
```

## 5. Acceptance

```text
EVERY_FACT_BOUNDARY_KIND_DERIVABLE=true
FACT_BOUNDARY_AUTHORITY_COUNT=1
MISMATCHED_BOUNDARY_REJECTED=true
UPSTREAM_FACT_IDENTITY_RECOMPUTED=true
UPSTREAM_BINDING_IDENTITY_RECOMPUTED=true
UPSTREAM_EVALUATION_IDENTITY_RECOMPUTED=true
FACT_IDENTITY_AUTHORITY_COUNT=1
PREDECESSOR_CONTEXT_REQUIRED=true
RETAINED_REFERENCES_RESOLVE=true
FORGED_CONTEXT_PAYLOAD_REJECTED=true

KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

```text
DIFFERENCE_RUNTIME_PROVEN=false
KERNEL_V0_1_COMPLETE=false
```
