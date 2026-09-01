# ADR-0019: A Target Predicate is bound once, and cannot be satisfied and open at once

```text
DOC_TYPE=STRUCTURAL_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0019-DIFFERENCE-ONE-BINDING-PER-TARGET
STATUS=ACCEPTED
DECIDED_AT=2026-09-01
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0018
SOURCE=INDEPENDENT_REVIEW_OF_274a64d
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

One finding. It was reviewed against `274a64d`, which `9d632dc` had already superseded, so
the first thing done was to establish whether it still applied. It did, unchanged:

```text
two bindings, both individually valid, both naming TP-0001
  one bundle observes READY      -> satisfied route, returns before emitting anything
  one bundle observes NOT-READY  -> emits a Difference

ACCEPTED.
satisfied_target_predicates: ['TP-0001']
differences: [('D-8C63714C1D1CAB53', 'TP-0001')]
SAME TARGET BOTH SATISFIED AND OPEN: ['TP-0001']
AUDITOR: []
```

The returned bundle asserts both answers to one question, and the independent validator is
silent. This is not the input-totality class of ADR-0018; it is a semantic contradiction the
gates could not see, because the two answers are produced on routes that never meet: the
satisfied route returns before emitting a record, and every whole-bundle gate reads records.

## 1. Decision

Two rules, at two levels, because either alone leaves the other open.

**One binding per Target Predicate**, rejected in `_require_request_shape` before any
binding is processed. That removes the cause. It rejects nothing legitimate: a Target's
additional Scopes travel as `historical_observation_scopes` (ADR-0012), not as a second
binding, and the rule fires on duplicate identity rather than on disagreement -- two bindings
that happen to agree are equally rejected, because the defect is the duplicate binding, not
the contradiction it sometimes produces.

**A Target may not be satisfied and open at once**, checked in the whole-bundle relational
gate over `satisfied_target_predicates` against the emitted Differences. That makes the
contradiction unemittable by any route, including one that does not exist yet. It is total
over an untrusted envelope: a non-list `satisfied_target_predicates` is passed over rather
than raised on, per ADR-0018.

The envelope rule is what the reviewer's last sentence asks for -- "the final conformance
gates do not reconcile that envelope field" -- and it is the half that survives a future
route this round cannot anticipate.

## 2. What this does not claim

Unchanged: Authority, Change, Evidence sufficiency, Reflow, Closure Evaluation *execution*,
adapters, CLI, runtime. No kernel contract file and no schema changed; no digest changed and
no emitted identity moved.

The envelope rule reconciles `satisfied_target_predicates` against emitted Differences. It
does not claim that the satisfied set is *complete* -- a Target the request never bound is
neither satisfied nor open here, and this phase says nothing about it. Objective Completion
has a later canonical owner, and `PROVEN_ABSENCE_SATISFIES_NONE` remains a Difference-level
statement rather than a Completion claim.

## 3. Cost

A caller that legitimately wanted two Observation bundles for one Target must now supply the
second through `historical_observation_scopes`, which is the declared route for it. That is
a narrowing of the input interface, and it is recorded rather than silent.
