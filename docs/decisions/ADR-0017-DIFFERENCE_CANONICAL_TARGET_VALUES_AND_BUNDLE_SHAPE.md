# ADR-0017: A declared type is a promise about the value, and an envelope is input too

```text
DOC_TYPE=STRUCTURAL_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0017-DIFFERENCE-CANONICAL-TARGET-VALUES-AND-BUNDLE-SHAPE
STATUS=ACCEPTED
DECIDED_AT=2026-09-01
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0016
SOURCE=INDEPENDENT_REVIEW_OF_c2ef01e
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

Two findings against `c2ef01e`, plus one this round's own tests found.

```text
1  a typed Target wrapper whose inner value is not canonical
     {"value_type":"TIMESTAMP","value":"2026-08-30T09:00:00+01:00"}
     operator equals  -> REJECTED, by the emitted difference.schema.json pattern
     operator exists  -> ACCEPTED, SATISFIED, no record emitted
   and the same for a malformed DECIMAL, DURATION and IDENTITY_REFERENCE

2  an observation_bundle omitting facts / bindings / fact_evaluations /
   negative_observations / negative_evaluations
     raised  KeyError: '<section>'   <- not the documented DifferenceError

3  (found by this round's own test) a bundle section present but not a list
     raised  TypeError: 'int' object is not iterable, from the hostile-input scan
```

**The reported mechanism for finding 1 is not the one that occurs, and reproducing it first
is what showed that.** The review describes the Engine emitting a false `VALUE_MISMATCH`.
It does not: `difference.schema.json` constrains the emitted `expected_value` for all three
string wrappers, so under an operator that consults the value the derivation is *rejected* —
late, and with a generated-schema message, but rejected. What escapes is the satisfied
route, under an operator such as `exists` that never consults `expected_value`: no record is
emitted, so the schema that would have caught it is never reached. That is exactly the class
ADR-0016 §2b closed for duplicate set members and did not close for typed wrappers. The
finding is real and its severity stands; the route is different, and the fix follows the
route rather than the description.

Findings 2 and 3 are ADR-0016 §2d one layer out. That round made the *record* scan total and
left the *envelope* untrusted: `_selectable` guarded `observations` and nothing guarded the
five sections the derivation indexes next.

## 1. Decision

**One definition of a canonical value, in the element that owns it.**
`observation.normalization.canonical_value` is extracted from `normalize_fact`, which now
calls it. It was inlined there, so the Observation element canonicalised the values it
minted and every other consumer of a declared type had only a shape check.

`projection.reject_noncanonical_typed_value` reads that authority and rejects a Target whose
declared wrapper is not already canonical. It **compares**; it does not substitute. The
Target is a Human Objective's declared value and an identity input: canonicalising it would
silently change what the Objective says and move every Difference identity derived from it.
`DIFFERENCE_IDENTITY.md` supports the stricter reading — it declares the inner value as a
*canonical* decimal, UTC timestamp or duration, and says the value is **projected**.

**The envelope is validated before its sections are indexed.**
`_REQUIRED_BUNDLE_SECTIONS` declares the six sections the derivation reads, and
`_require_bundle_shape` rejects any that is absent or not a list, before selection. A
contract test compares the tuple against the sections the derivation actually reads, in both
directions, so a section added to the derivation without being declared fails.

**And the scan that runs before that guard is itself total.** `_iter_request_records` walks
the bundle's sections during the hostile-input pass, which precedes the shape guard, so a
section that is not a list is passed over there and rejected by the guard with its own
message. This one was not reported: the parametrised test for finding 2 found it.

## 2. What this does not claim

Unchanged: Authority, Change, Evidence sufficiency, Reflow, Closure Evaluation *execution*,
adapters, CLI, runtime. No kernel contract file and no schema changed, and no digest changed:
`canonical_value` computes exactly what `normalize_fact` computed before, named rather than
inlined, and the Target is never rewritten by it.

The rule covers the four contract-declared typed scalar wrappers. It claims nothing about a
literal value of the same shape — a plain string that looks like a timestamp is a `STRING`,
per ADR-0013, and is compared whole.

## 3. Cost

A Human Objective must now declare its typed values in canonical form: a Target of
`2026-08-30T09:00:00+01:00` is rejected rather than accepted and compared. That is the
intended reading of the contract, and the alternative — normalising it — would make the
Objective's declared text and the identity derived from it disagree. The rejection names the
type and says the value is not canonical, so the author is told what to write.
