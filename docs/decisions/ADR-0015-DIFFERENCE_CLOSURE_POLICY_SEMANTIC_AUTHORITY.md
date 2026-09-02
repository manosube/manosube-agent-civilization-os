# ADR-0015: A Closure Policy must recompute from its own content

```text
DOC_TYPE=STRUCTURAL_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0015-DIFFERENCE-CLOSURE-POLICY-SEMANTIC-AUTHORITY
STATUS=ACCEPTED
DECIDED_AT=2026-09-01
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0014
SOURCE=INDEPENDENT_REVIEW_OF_da3b0b1
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

Three findings against `da3b0b1`, all on the Closure Policy. Each was reproduced before
anything was changed:

```text
1  a carried Policy whose required Claim was rewritten
     stored policy_semantic_fingerprint   sha256:e1ae37bc...
     recomputed from its content          sha256:ed34d3c2...   <- differ
     Engine                               ACCEPTED and EMITTED
     independent validator                Policy required Claim identity mismatch

2  a reopen condition naming a predicate the Objective revision does not carry
     objective_revision_ref               OBJ-REV-0001          <- resolves
     OBJ-REV-0001 target predicates       ['TP-0001']
     condition id                         TP-NOT-IN-THE-OBJECTIVE
     Engine                               ACCEPTED and EMITTED
     independent validator                []                    <- silent too

3  a moving reference in a Closure Policy fragment of a satisfied derivation
     emitted policies                     0                     <- nothing to sweep
     Engine                               ACCEPTED
```

Finding 1 is the shape this review has found before, one layer further in. The Closure
Policy is the only carried record that stores a digest of *its own content*, and nothing
recomputed it: `_policy_identity` read `policy_semantic_fingerprint` off the record and
derived the Closure Policy ID from it, so the identity agreed with the stored digest and
with nothing else. The whole-bundle relational pass does recompute a Policy's semantics,
but only for a Policy some lifecycle Evaluation cites; a carried Policy that nothing cites
travelled untouched. The independent validator held the required-Claim rule and the Engine
did not, which is exactly the auditor-only rule this work is not allowed to keep.

Finding 2 is a rule the contract already states and the implementation had not reached.
`CLOSURE_POLICY.md` requires each reopen condition's ID, Objective revision *and*
fingerprint to resolve exactly. Reference closure, added in Round 15, proved only that the
Objective revision was present. Nothing looked inside it, so a condition could authorise a
reopen on a predicate that does not exist, under any fingerprint the caller chose. Neither
the Engine nor the validator objected: this one had no second line of defence at all.

Finding 3 is the Round 15 fragment scan, incomplete. That round scanned the Observation
Method fragment in the request and deliberately deferred the Closure Policy requirements
fragment to the emitted-bundle sweep, on the reasoning that completion materialises its
Claim descriptors and so the fragment's shape at those paths is not the record's. The
reasoning was wrong twice: the scan already skips any value that is not a reference with a
string `id`, so a descriptor is passed over rather than rejected; and a derivation whose
bound Target Predicates are all satisfied emits no Policy, so there was no output record to
sweep. A binding may also carry its own requirements fragment, so the same reference merely
had to be supplied one level down.

## 1. Decision

`difference/policy.py` is the single owner of Closure Policy semantic conformance. Two
rules live there, different in kind:

```text
closure_policy_semantic_errors        one record, from its own content
  policy_semantic_fingerprint            must recompute
  required_claims[].claim_semantic_...   must recompute
  required_claims[].id                   must recompute
  required_claims[] duplicate set member rejected
  required_claims[] two payloads/one id  rejected

reopen_condition_provenance_errors    relational, Policy x Objective revision
  condition id                           must name a predicate of that revision
  predicate_semantic_fingerprint         must recompute over that predicate
```

`MANOSUBE-TARGET-PREDICATE-SHA256-0.1` is implemented in `difference/identity.py` as
`target_predicate_fingerprint`, over the `INCLUDED_FIELDS` the contract fixes. It did not
exist before: `predicate_semantic_fingerprint` was carried and compared but never derived,
which is why nothing could tell a real fingerprint from a chosen one. A contract test reads
the profile block out of `CLOSURE_POLICY.md` and holds the implementation to it in both
directions.

`RecordType` gains a `semantics` authority beside its existing `identity` authority, and
`validate_typed_record` runs it *before* recomputing the identity: where a type stores a
digest of itself the identity is derived from that digest, so "identity does not recompute"
would report the consequence and hide the cause. `closure_policy` is the only type that
declares one, and `None` on every other type is the stated position that it carries no
self-derived semantics to recompute.

`_policy_identity` now recomputes the digest rather than reading it, so an altered Policy
changes its identity — which is what the identity gate is for.

The independent validator imports both rules and no longer restates either. Its
independent re-implementations of the *serializer* and of `_policy_fingerprint` are left
untouched: what is removed is a rule the auditor held alone, not the auditor's independence.

The Closure Policy requirements fragment is scanned in the request, on both routes it can
arrive by — `request.closure_policy_requirements` and
`request.bindings[i].closure_policy_requirements`. `_EMITTED_SWEEP_FRAGMENT_TYPES` is now
empty and kept rather than deleted, so the two-map fragment inventory still forces a
fragment added later to be classified before it can pass.

## 2. What this does not claim

Unchanged and still not implemented: Authority, Change, Evidence sufficiency, Reflow,
Closure Evaluation *execution*, adapters, CLI, runtime. No kernel contract file and no
schema changed. No identity algorithm changed: `target_predicate_fingerprint` is a digest
the contract already fixed and nothing had computed, not a new or altered one.

`reopen_condition_provenance_errors` does not restate reference closure. A condition whose
Objective revision is absent is reported by the closure gate and passed over here, so one
absent reference yields one error naming the reference, not two naming different things.

## 3. Cost

One new module and one new field on the record-type table. The alternative — recomputing
the Policy inside the conformance gate directly — would have put a Closure Policy rule in
the record-type table and left the validator's copy in place, which is the arrangement that
produced this finding.

A Round 15 test asserted that a reopen condition naming `TP-REOPEN-0001` with an arbitrary
fingerprint was accepted. It was written to prove the nested reference *resolved*, and it
recorded the gap as if it were the contract. It now names a predicate the Objective
revision really carries, and the two forgeries it used to permit are covered by their own
tests.
