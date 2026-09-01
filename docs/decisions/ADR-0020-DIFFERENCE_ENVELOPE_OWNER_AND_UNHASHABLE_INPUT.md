# ADR-0020: An Engine-only rule is the same defect as an auditor-only one

```text
DOC_TYPE=STRUCTURAL_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0020-DIFFERENCE-ENVELOPE-OWNER-AND-UNHASHABLE-INPUT
STATUS=ACCEPTED
DECIDED_AT=2026-09-01
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0019
SOURCE=INDEPENDENT_REVIEW_OF_f29e28a
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

Two findings against `f29e28a`, both in code ADR-0019 had just added.

```text
1  an emitted bundle whose satisfied_target_predicates names an open Difference's Target
     engine relational gate  ['Target Predicate is reported satisfied and open at once']
     independent validator   []                        <- silent

2  target_predicate_id supplied as [] / {} / ["TP-0001"]
     raised  TypeError: unhashable type: 'list'
```

Finding 1 falsifies a claim made in ADR-0019 §1 and repeated on the PR: that the
contradiction was "unemittable by any route". It was not. The rule was written directly
inside `graph.relational_errors`, which the Engine calls and the independent validator does
not -- that validator composes its own relational pass out of shared owners. So the producer
rejected the bundle and the auditor accepted it: an **Engine-only rule**, the exact mirror of
the auditor-only rule ADR-0015 removed, introduced one round after removing it.

Finding 2 is the totality rule of ADR-0018, missed inside the gate that exists to apply it.
A set membership test hashes its operand, so an unhashable identity raised before the
boundary could reject it.

**The sweep did not catch finding 2, and that is the more useful result.** It retyped every
location to a single scalar sentinel (`7`), which is hashable. Widening the substitutions to
`int`, `str`, `list`, `dict` and `null` raised the case count from 533 to 1597 and exposed
**ten** leaks, of which one was reported. A sweep is only as good as its substitution set,
and stating that here is worth more than the ten fixes.

## 1. Decision

**`difference/envelope.py` owns returned-bundle envelope invariants.** A bundle carries
records and envelope fields that summarise them; records are decided by schema, identity and
the relational gate, and an envelope field is decided by nothing unless something reconciles
it against the records. `satisfaction_reconciliation_errors` is read by
`graph.relational_errors` and by `validate_bundle`, so producer and auditor decide it
identically.

**The readability gate covers every mechanical type failure, not only container types.**
`observation_completeness_errors` now returns every `required` and every `type` violation.
Both are decidable without knowing what the record means: a missing property raises
`KeyError`, and a wrongly typed value raises `TypeError` when iterated or `unhashable type`
when used as an index key. Every other keyword -- `oneOf`, `enum`, `pattern`, `const` -- is
semantic, and stays with the cross-record pass. That line is what keeps a forged-but-readable
payload reporting as the defect it is; the five diagnosis tests that caught the over-wide
version in ADR-0018 all still pass, because the payload they forge is `oneOf`-invalid, not
type-invalid.

**A membership test needs the guard a subscript needs.** Both new instances were set
lookups over untrusted values -- `bound_targets` in the request gate, and the accepted-status
frozenset in selection. An `enum` is semantic, so the readability gate deliberately does not
decide it; the point of use does.

**The sweep substitutes five JSON types, not one.** Each is a well-formed JSON value, so what
is tested is the boundary rather than the parser.

## 2. What this does not claim

Unchanged: Authority, Change, Evidence sufficiency, Reflow, Closure Evaluation *execution*,
adapters, CLI, runtime. No kernel contract file and no schema changed; no digest changed and
no emitted identity moved.

ADR-0019 §2 stands: the envelope rule reconciles the satisfied set against emitted
Differences and does not claim that set is *complete*.

ADR-0018 §2 stands and is now better evidenced: the sweep is a measurement over one
representative bundle, not a theorem. This round is the proof of that -- the previous run
reported zero leaks over a substitution set that could not express the failure.

## 3. Cost

1597 parametrised cases add roughly twenty-five seconds to the suite, up from nine. The
alternative is discovering the eleventh substitution the hard way.
