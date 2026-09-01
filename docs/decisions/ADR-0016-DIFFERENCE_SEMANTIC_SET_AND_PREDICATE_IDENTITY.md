# ADR-0016: A duplicate is created by the projection, and an identity names one payload

```text
DOC_TYPE=STRUCTURAL_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0016-DIFFERENCE-SEMANTIC-SET-AND-PREDICATE-IDENTITY
STATUS=ACCEPTED
DECIDED_AT=2026-09-01
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0015
SOURCE=INDEPENDENT_REVIEW_OF_6043123
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

Three findings against `6043123`, each reproduced before anything was changed:

```text
1  two required_invariants differing only in an excluded commit_sha/blob_sha
     schema uniqueItems              satisfied (the whole objects differ)
     projected members               identical
     Engine                          ACCEPTED and EMITTED
     independent validator           []
   and two reopen conditions differing only in an excluded objective_revision_ref
     Engine                          ACCEPTED, 2 conditions emitted

2  a carried Objective revision with two Target Predicates under TP-0001
     first  fingerprint              sha256:2d3520f4...
     second fingerprint              sha256:50620235...
     Engine                          ACCEPTED, resolving against the LAST payload
     and, with nothing pointing at it, ACCEPTED with no rule reading it at all

3  a Target whose expected_value carries an UNORDERED_SET with a duplicate member
     operator exists   -> SATISFIED, no Difference, no record emitted
     operator equals   -> REJECTED  "normalized_target_state carries a duplicate ..."
```

Finding 1 is a rule that cannot be enforced before the projection it is about. `uniqueItems`
compares whole objects, and the duplicate does not exist in the whole objects — it is
*created* by the semantic projection, which drops `commit_sha`, `blob_sha` and
`objective_revision_ref`. `MANOSUBE-CLOSURE-POLICY-SHA256-0.1` names four unordered sets and
fixes `DUPLICATE_SET_MEMBER=REJECT`, and the Policy identity was made to depend on set
multiplicity, which a set does not have. The Round 15 duplicate check looked only inside
required Claims, which is the one place the projection changes nothing.

Finding 2 is the Round 16 correction reaching one layer short. `unique_target_predicates`
already owned "a Target Predicate identity names one predicate" and was applied to the
*requested* Objective revision only. Round 16 then indexed a carried revision by dict
comprehension — which silently keeps the last payload — so a reopen condition could resolve
against one reading of an ambiguous identity while the auditor's own lookups resolved the
other. The broader half is worse: a carried ambiguous revision that no condition points at
was accepted with no rule reading it at all.

Finding 3 is two canonicality rules enforced at different moments. Bare arrays were rejected
where each projection is produced; duplicate set members only while building an *unsatisfied*
Difference. A satisfied comparison returns before that — and satisfaction is the one outcome
that emits no record, so no later gate could catch it. The same Target was refused on one
route and reported satisfied on the other.

## 1. Decision

**One projection, read by the digest and by the duplicate rule.**
`identity.policy_semantic_projection` is extracted from `policy_semantic_fingerprint`, which
now digests it. `policy._duplicate_set_errors` reads that same projection and rejects a
repeated member in any of `POLICY_UNORDERED_SET_FIELDS`. A hand-copied second projection is
exactly how the check and the digest would drift, so there is not one. A contract test holds
`POLICY_UNORDERED_SET_FIELDS` and `DUPLICATE_SET_MEMBER=REJECT` to the profile block in
`CLOSURE_POLICY.md` in both directions.

**Target Predicate identity is decided by its owner, on every route.**
`RECORD_TYPES["objective_revision"]` declares `unique_target_predicates` as its `semantics`
authority, so the carried, input and emitted routes are covered by the one gate rather than
by whichever consumer happens to index first. `reopen_condition_provenance_errors` builds its
index through the same owner instead of by comprehension.

The `semantics` hook introduced in ADR-0015 now *raises* rather than returning errors, so
each rule keeps the exception type its own owner defines — an ambiguous predicate identity
stays an `IdentityCollisionError` and does not become a generic conformance failure. The
Closure Policy hook is a thin wrapper over `closure_policy_semantic_errors`, which the
independent validator still imports unchanged; a test asserts the message the gate raises is
the owner's own first error, verbatim.

**Both canonicality rules are stated together, at every projection.**
`engine._reject_noncanonical` rejects a bare array and a duplicate set member in one call,
and every projection site calls it — before the comparison, so satisfaction cannot be
reported over a non-canonical Target. The two later per-projection loops are replaced by the
same call; a test reads the derivation source and asserts no projection is checked by a bare
call to either underlying rule.

## 2. What this does not claim

Unchanged: Authority, Change, Evidence sufficiency, Reflow, Closure Evaluation *execution*,
adapters, CLI, runtime. No kernel contract file and no schema changed, and no digest changed
— `policy_semantic_fingerprint` computes exactly what it computed before, over a projection
that is now named rather than inlined.

The duplicate rule decides *set* members. It does not claim anything about ordering: the
profile fixes `SET_ORDER=CANONICAL_MEMBER_BYTES`, which the projection already applied and
which a contract test already covers.

## 3. Cost

`RecordType.semantics` changing from errors-returning to raising means a future rule must
choose its own exception type rather than inheriting one. That is the point — flattening an
identity collision into a generic conformance error is what would make a real defect read as
a schema nit — but it is a decision each new rule now has to make explicitly.
