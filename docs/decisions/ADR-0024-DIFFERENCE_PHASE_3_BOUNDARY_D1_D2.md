# ADR-0024 — The Phase 3 boundary: retain D1, defer D2

**Status:** accepted
**Bounds:** ADR-0022, ADR-0023. **Supersedes nothing.**

## 1. Why a boundary decision rather than another correction

Three consecutive rounds ended the same way: an authority introduced to close a defect class
was itself incomplete on its first outing, and a review found the gap.

```text
ADR-0020   envelope rule            written Engine-only; the auditor never read it
ADR-0023   emitted readability gate narrower than the rule it stood in for
this round _canonical_time          accepted a value that is not canonical
```

The reflex is a fourth correction. The measurement says something else.

## 2. What the evidence actually showed

**64 of 65 review findings are producer-located.** 44 in `engine.py`, 17 in other
`difference/` owners, 3 in `observation/`, and **one** in the independent auditor — the
still-open `_canonical_time` P2. The last twelve findings are eleven producer, one auditor.
So the correction loop's source was never Independent Verification arriving early; it was
producer defects surfacing one review at a time.

**The auditor already exists on `main`** — 2461 lines, importing only `state.*`, with `main`
carrying no `difference/` package at all. It independently reimplements lifecycle
transitions, conflict position, boundary matching, policy semantics, the Objective chain and
selection. This branch's `+425/-349` is not new auditor functionality: it is the rewiring
that made the auditor **delegate to the shared owners** instead.

Those two facts reject a wholesale `A+B+C / D` split. Reverting the auditor would restore
the duplicated rulesets ADR-0015 and ADR-0020 removed, in exchange for removing one finding.

## 3. The boundary

```text
RETAIN  A   core deterministic derivation
        B   predecessor / lifecycle absorption
        C   whole-bundle producer conformance
        D1  auditor shared-owner delegation      <- producer-correctness infrastructure

DEFER   D2  auditor adversarial totality         <- Independent Verification's obligation
```

`52592db` is where Phase 3 acquired D2. Before it, D was only the rewiring. After it, this
branch asserted *adversarial totality of the auditor over arbitrary mutated bundles* — an
obligation of a later element, and the one this phase has now failed to close three times.

**Deferred artifacts** (three additive files plus the D2-only validator hunks):

```text
tests/unit/difference/test_auditor_totality_sweep.py                       390 lines
tests/contract/fixtures/difference/frozen/auditor_bundle_baseline.json  11 865 lines
tests/contract/difference/test_unschematized_provenance.py                 152 lines
scripts/difference_contract_validator.py:  _canonical_time, _snapshot_time,
   the attempt-window timestamp guards, the unresolved-reference guard
```

`_canonical_time` is removed rather than fixed. It was introduced only to satisfy the D2
enumeration, and a partial authority retained because later tests reference it is exactly
the failure mode of the last three rounds.

**Retained in the validator**, because neither depends on D2:

* delegation to the shared canonical owners, and the deletion of the auditor-only rules it
  replaced — this *is* the single-ownership property, not verification;
* the removal of the undocumented Reflow semantic reads (ADR-0023 §3). That was a phase
  **ownership** correction: the auditor was reading fields no schema declares. It is
  required whether or not D2 exists.

## 4. What is no longer claimed

```text
AUDITOR_ADVERSARIAL_TOTALITY_CLAIMED=false
AUDITOR_BOUNDED_EMPTY_ROUTE_TOTALITY_PROVEN=false
DEFERRED_KNOWN_FINDING=naive_timestamp_in_independent_auditor
FUTURE_OWNER=INDEPENDENT_VERIFICATION_PACKAGE_IV_1
```

**The deferred finding is not fixed and is not claimed fixed.** The defective authority is
absent from the Phase-3 diff; the underlying obligation — that an independent verifier is
total over arbitrary later-phase bundles — moves to its owner. The deleted artifacts stay
recoverable from branch history.

## 5. What Phase 3 still owes, and still proves

A Difference producer must reject the malformed inputs **it actually consumes**, and must
not emit internally inconsistent records. Both remain proven:

```text
Engine input totality   7770 cases, 0 harness faults, 0 raw exceptions   (retained)
State -> Observation -> Difference natural integration                   PASS
whole-bundle producer conformance                                        retained
predecessor / lifecycle routes the Engine emits                          retained
canonical identities                                                     unchanged
```

Identity change is impossible by construction: `git diff` against the pre-split head shows
**no change under `src/`** at all.

## 6. The caution this ADR does not resolve

This boundary makes Phase 3 closable by removing an obligation it cannot meet. It does not
explain why 64 producer findings arrived one review at a time, and a smaller PR does not fix
that by itself. What the last three rounds argue is narrower and more specific: **a new
authority needs adversarial coverage authored with it**, rather than coverage inherited from
whichever fixtures happened to exist. That is a process obligation, and it survives this
split.
