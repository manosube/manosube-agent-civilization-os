# ADR-0018: The same defect four rounds running is a class, not a sequence

```text
DOC_TYPE=STRUCTURAL_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0018-DIFFERENCE-INPUT-TOTALITY-SWEEP
STATUS=ACCEPTED
DECIDED_AT=2026-09-01
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0017
SOURCE=INDEPENDENT_REVIEW_OF_274a64d
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

Three findings against `274a64d`, all the same shape as the four before them:

```text
1  historical_observation_scopes = 7      TypeError from the hostile-input scan
2  a facts / bindings member that is an object without its identity field
                                          KeyError from the index comprehension
3  a binding that is an object without target_predicate_id
                                          KeyError from the sort key
```

Rounds 17 to 20 each corrected this defect where it was reported, and each next round found
it one layer further in: the section list, then its members, then their fields. Correcting
the reported line is what guaranteed the next round would find the next line. So this round
enumerated the surface instead.

A harness walks every reachable location of a valid derivation request, deletes and retypes
each, and records anything that is not a `DifferenceError`. **It found 19, of which 3 were
reported.** The other 16 were the same class, unreported and undetected by every prior
round.

The harness itself was wrong on its first run and reported 4. Its path parser produced an
empty key after a list index, `apply` raised, and a bare `except: continue` swallowed it --
so every nested location was silently skipped and the run looked clean. That is worth
recording because it is the same defect the harness was written to find: a container walked
and its members not, and a total-looking guard hiding the miss. The parser was fixed and a
failed mutation is now reported as a harness fault rather than skipped.

## 1. Decision

**One request-shape gate, first.** `_require_request_shape` declares the top-level keys and
the per-binding keys the derivation reads, and runs before anything reads them, so no absent
key is discovered by the code that needed it.

**One readability gate over the Observation bundle**, decided by the Observation element's
own authority. `observation.verification.observation_completeness_errors` returns *only* the
schema violations that make a record impossible to read: a required property absent, or a
container of the wrong JSON type.

That narrowing is the whole design, and it was arrived at by getting it wrong first.
Returning every schema error pre-empted the cross-record pass for a record that is *both*
incomplete and wrong: a forged `CONFLICTED` payload was reported as a schema failure instead
of by the rule written to catch it, and five existing tests said so. Completeness and
admissibility are distinct obligations (ADR-0013); this gate answers only the first, and a
record that is complete but wrong stays silent here and keeps its own diagnosis.

**Scans that precede a gate are total.** The hostile-input scan runs before both gates, so it
passes over a non-list rather than iterating it, and the owner of that rule reports it with
its own message -- `_historical_scopes` still owns "historical Observation Scopes must be a
list", and this round removed a duplicate of that rule that had been added to the request
gate.

**The sweep is now a test.** `tests/unit/difference/test_input_totality_sweep.py` runs the
same enumeration on every suite run: 533 cases, each asserting the derivation either derives
or raises `DifferenceError`, never a raw exception. Success is a legitimate outcome for many
of them -- an optional key with a default, a retyped Target value that is a valid `INTEGER` --
so what is asserted is the property the boundary documents, not that every mutation is
rejected. A location added to the request later is covered without being remembered.

## 2. What this does not claim

Unchanged: Authority, Change, Evidence sufficiency, Reflow, Closure Evaluation *execution*,
adapters, CLI, runtime. No kernel contract file and no schema changed; no digest changed and
no emitted identity moved.

The sweep covers the *derivation request*, at every location reachable within a bounded
depth of a representative bundle -- one binding, one Fact, one Negative Observation, one
predecessor-free route. It is not a proof of totality over every possible request shape, and
it is not a fuzzer: it enumerates a fixed structure deterministically. A shape this fixture
does not exhibit is not covered, and `ALL_DERIVATION_INPUT_TOTAL` is therefore claimed as
`measured_over_the_sweep`, not as a theorem.

## 3. Cost

533 parametrised cases add roughly nine seconds to the suite. That is the price of the class
being closed by measurement rather than by the next reviewer finding the next layer, and it
is worth paying: four rounds of one-at-a-time correction cost more than nine seconds each.
