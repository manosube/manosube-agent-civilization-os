# ADR-0021: A gate that runs second is not a gate, and an unmeasured surface is not a clean one

```text
DOC_TYPE=STRUCTURAL_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0021-DIFFERENCE-GATE-ORDERING-AND-A-MEASURED-GAP
STATUS=ACCEPTED
DECIDED_AT=2026-09-01
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0020
SOURCE=INDEPENDENT_REVIEW_OF_542f3d7
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
OPEN_MEASURED_GAP=true
```

## 0. Position

Four findings against `542f3d7`. Two were pre-existing; two were in code the previous round
added.

```text
1  closure_policy_requirements.required_claims = null / 7 / [None] / ['x'] / [{}]
     TypeError while iterating, or TypeError/KeyError inside completion_claim_id
2  a binding whose predecessor is a list or a string
     AttributeError from the first .get() of the context reader
3  derive_differences(None / [] / "x" / 7)
     AttributeError from require_schema_version -- which runs BEFORE the shape gate
4  satisfied_target_predicates carrying [[]] or [{}], audited
     TypeError: unhashable type, from intersection
```

Finding 3 is the sharpest. `_require_request_shape` already contained the correct rejection
for a non-object root. It was placed *after* `require_schema_version`, which calls `.get()`,
so the guard was unreachable for exactly the inputs it was written for. **A gate that runs
second is not a gate**, and this is the second consecutive round where ordering rather than
absence was the defect.

Finding 4 is the unhashable-membership rule for the third time. ADR-0020 §1 states it --
"a membership test needs the guard a subscript needs" -- and the same round then wrote a new
`intersection` over an untrusted envelope. Writing a rule down is not the same as applying
it, and this ADR records that as a fact about the process rather than a resolved problem.

## 1. Decision

The four are corrected: the Claim descriptor collection and each member are validated before
materialisation; a predecessor must be an object or absent; the shape gate runs first, before
the schema-version read; and the envelope helper filters members to strings before the set
operation.

**The sweep's blind spots are the substantive finding, and two of three are closed.**
ADR-0018's harness mutated *inside* a valid request, so it never passed a non-object root --
finding 3 was unreachable by it. Non-object roots are now a parametrised case.

## 2. The open, measured gap

The sweep's fixture carried **no predecessor**, so that entire subtree was unreachable and
finding 2 was found by a reviewer rather than here. A predecessor fixture was written and
run. It produced **78 failures**, concentrated in `predecessor.events[].event_revision`.

Those 78 are **not corrected in this round**, and the fixture is deliberately **not**
committed into the sweep:

* committing it would leave the suite red and the branch unmergeable;
* omitting it silently would let `INPUT_TOTALITY_SWEEP_LEAKS=0` continue to mean less than
  it appears to.

So it is recorded here instead, as a measured, quantified, open gap, and the sweep's own
docstring names the omission. `ALL_DERIVATION_INPUT_TOTAL` remains
`measured_over_the_sweep`, and the sweep is now known to exclude the predecessor route.

A third blind spot remains unmeasured: the sweep exercises the Engine only. No equivalent
enumeration is run over `validate_bundle` against mutated emitted bundles, and finding 4 --
an auditor-side leak -- was therefore also found by a reviewer. That is stated as unmeasured
rather than clean.

## 3. Cost

This ADR records an open defect set rather than closing one. That is the point: the previous
two rounds each reported a clean sweep that a wider substitution set or a wider fixture then
falsified. Reporting 78 known failures is worth more than a third clean number of unknown
scope.
