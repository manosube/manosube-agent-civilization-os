# ADR-0014: A status that asserts no conflict may not name one, and fragments are scanned

```text
DOC_TYPE=STRUCTURAL_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0014-DIFFERENCE-CONFLICT-POSITION-AND-FRAGMENT-SCANNING
STATUS=ACCEPTED
DECIDED_AT=2026-09-01
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0013
SOURCE=INDEPENDENT_REVIEW_OF_5d67ce2
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

Two findings, both a rule that was enforced in one direction only. Both were reproduced
against `5d67ce2` first, and neither had been incidentally corrected in the previous round:

```text
1  a SUPPORTED Fact Evaluation carrying a conflict reference
     identity recomputes         True
     observation_record_errors   []            <- the shared verifier was silent
     Engine                      ACCEPTED
     independent validator       0 errors
2  request.observation_method with procedure_ref.id = "HEAD"
     Engine                      ACCEPTED
     emitted procedure_ref ids   ['OBS-PROCEDURE-0001', 'HEAD']
                                 <- copied into a content-addressed Method
```

No Kernel contract text and no schema changed. No identity algorithm changed.

## 1. The conflict position is stated in both directions

`NORMALIZED_FACT.md` makes the latest contiguous evaluation the record of the *current*
support and conflict position, and `NEGATIVE_OBSERVATION.md` requires the Fact side and the
Negative side to reference the same conflict pair. Both were enforced. The converse was not:
nothing required a status asserting *no* conflict to carry no conflict references.

Every gate that should have caught it was answering a different question. The canonical
schema constrains only the `CONFLICTED` direction (`if CONFLICTED then anyOf minItems 1`).
The identity is derived from subject and revision alone, so an evaluation appended to move a
Fact off `CONFLICTED` recomputes perfectly while keeping the references of the revision it
replaced. And the symmetry rule had nothing to object to, because both sides were left
mutually consistent. The result was a Difference derived from an observed state that
simultaneously claimed support and conflict.

`observation/verification.conflict_position_errors` states the rule once, for **both**
evaluation kinds — there is no second status table and no auditor-only rule, because every
consumer reaches it through `observation_record_errors`:

```text
CONFLICTED           requires at least one conflict reference
every other status   forbids any conflict reference
```

The status list and the reference fields are read from the canonical schema in the test, not
restated, so a new status cannot be added without deciding which side it falls on. The rule
applies per revision rather than only to the latest: an append-only chain records the
position *at* each revision, and a historical revision that contradicted itself was never
admissible either.

## 2. Raw fragments are scanned before they become records

ADR-0013 moved the moving-reference scan onto declared reference locations and mapped every
canonical record the request carries. It missed the raw **fragments** — the shapes the Engine
completes into records — so a declared field of the Observation Method fragment could carry a
mutable identity into a content-addressed record, after which the output gate saw only the
derived, stable identity.

Two routes cover the two fragments, and the split is declared rather than incidental:

```text
_REQUEST_FRAGMENT_TYPES        observation_method -> observation_method
                               scanned as that type, before derivation: a Method fragment is
                               the record minus schema_version, record_kind and its content
                               address, so its declared reference locations are identical
_EMITTED_SWEEP_FRAGMENT_TYPES  closure_policy_requirements -> closure_policy
                               swept as the *derived* record in _finalize: completion
                               materialises required_claims descriptors into Completion Claim
                               records, so the fragment's shape at those declared paths is not
                               the record's, and scanning it as closure_policy would reject
                               valid input
```

The `_finalize` sweep is the general closure, not a patch for one fragment: it reads every
emitted record through the same declared paths, so any record the Engine *derives* is
covered, whatever it was derived from. A contract test proves the two maps together equal the
fragments the derivation actually reads — parsed out of `derive_differences` — in both
directions, and that they do not overlap. `_SCANNED_BINDING_KEYS` does the same for the
record-bearing binding keys, with the remainder asserted to carry an identifier, a fragment or
a risk class rather than records.

Arbitrary shape traversal is not restored anywhere. A test carries a `STRUCTURED` Fact value
of `{"kind": "widget", "id": "HEAD"}` through a request that also supplies a Method fragment,
and it stays literal in the emitted observed state.

## 3. Proofs added

```text
tests/unit/difference/test_conflict_position.py               25 cases
  - the status list and reference fields are read from the canonical schema
  - 5 non-conflicted statuses x 2 reference lists, with the identity recomputed so no
    identity rule can be what rejects them
  - each non-conflicted status with empty lists accepted; CONFLICTED with none rejected
  - a Negative Evaluation held to the same rule
  - the real CONFLICTED lineage the Observation Engine produces is unaffected
  - the rule is total over four hostile payloads, and reached through one verifier

tests/unit/difference/test_request_fragment_scanning.py       21 cases
  - fragment inventory == the fragments derive_differences reads, both directions,
    non-overlapping, each becoming a declared emitted type
  - every record-bearing binding key is scanned, and the unscanned remainder is named
  - one moving-reference mutation per declared Observation Method reference location
  - six moving identity forms; a stable reference accepted; the error names the fragment
  - a moving reference in a Closure Policy requirement caught by the emitted sweep
  - a STRUCTURED {kind,id} value stays literal; a malformed fragment leaks no raw exception
```

## 4. Acceptance

```text
CONFLICT_POSITION_AUTHORITY_COUNT=1
CONFLICT_RULE_STATED_IN_BOTH_DIRECTIONS=true
CONFLICT_RULE_COVERS_BOTH_EVALUATION_KINDS=true
FACT_EVALUATION_STATUSES_COVERED=6
SECOND_STATUS_TABLE=absent
REQUEST_FRAGMENT_INVENTORY_MATCHES_DERIVATION=true
FRAGMENT_SCAN_USES_DECLARED_PATHS=true
EMITTED_MOVING_REFERENCE_SWEEP=true
ARBITRARY_SHAPE_TRAVERSAL=absent
RAW_EXCEPTION_ESCAPES=0

KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
CANONICAL_OWNER_COUNT=1
```

Every non-claim recorded in ADR-0011 through ADR-0013 stands unchanged; this round adds
none and removes none.
