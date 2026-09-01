# ADR-0022 — Measure the whole surface, freeze what it finds, then correct once

**Status:** accepted
**Supersedes nothing. Bounds:** ADR-0018 §2, ADR-0020 §1, ADR-0021 §2.

## 0. Why the method changed

Rounds 17–24 each corrected the defect where it was reported and each next round found
the same defect one layer further out. ADR-0018 responded by enumerating the surface
instead of naming cases, and that was right — but the enumeration was then trusted more
than it had earned. `INPUT_TOTALITY_SWEEP_LEAKS=0` was falsified three times, every time
by *widening the measurement* rather than by a code change revealing a regression.

So this round inverts the order: **measure everything, freeze the failures as committed
data, and only then correct.** The frozen manifests are written before any production
change exists, which is what makes "the fix closed exactly these and introduced none"
checkable rather than asserted.

## 1. The measurement was wrong about itself, again — three times

Before it found anything about the Engine, the harness found three faults in itself.
Each is recorded rather than quietly fixed, because each is the same class the harness
exists to detect.

**The depth bound was truncating the inventory.** `_MAX_DEPTH` was 8. The request
fixture nests to 9 and the predecessor fixture to 15, while this file's own docstring
claimed every location was "well within" the bound. **49 predecessor locations — 294
cases — were clipped out of every count this branch has published**, including the ones
quoted back to it in the authorising decision. The bound is now asserted against the
measured nesting depth, so a deeper fixture fails the measurement instead of shrinking
it. Re-measuring at the un-truncated depth added 294 cases and **no new defects**: the
same 78 at the same five sites.

**The auditor had never been enumerated at all.** Its entire negative coverage was 55
hand-authored invalid-fixture cases. That is exactly why an Engine-only rule reached the
branch in ADR-0020 — the producer rejected a bundle, the auditor accepted it, and no
measurement in the repository could have said so. Enumerating it measured **1317 raw
exceptions across 198 raise sites**.

**A measurement that cannot fail reports zero.** Mutation-application failures, paths the
parser cannot round-trip, and a shrunken inventory now each fail the measurement rather
than shrinking it, and positive controls point every classifier at a known raw raiser, a
known canonical rejection and a known good call, and assert it tells them apart.

## 2. The frozen set

Committed at `52592db`, before any correction existed:

```text
tests/contract/fixtures/difference/frozen/engine_input_baseline.json
tests/contract/fixtures/difference/frozen/auditor_bundle_baseline.json

Engine    7770 cases   0 harness faults    78 raw-exception cases   26 paths    5 sites
auditor   7248 cases   0 harness faults  1317 raw-exception cases  356 paths  198 sites
          4184 reported, 1747 accepted
```

## 3. 1395 cases, seven defects, one shape

Every frozen case is a value read before anything establishes it can be read.

| # | Where | Cases | The defect |
| --- | --- | --- | --- |
| D1 | `engine.py` lineage agreement | 40 | ran three lines *before* the typed boundary, then used each carried record's identity key as a mapping key |
| D2 | `engine.py` request record scan | 16 | `or []` passes any truthy non-iterable to `enumerate` |
| D3 | `engine.py` predecessor chain | 20 | sorted on `event_revision` before the gate that validates events |
| D4 | `engine.py` events scan | 1 | the same `or []` shape |
| D5 | `engine.py` predecessor sections | 1 | a closed key set is two rules; only "reject unknown" was stated |
| — | `predecessor.py` context | 2 | read the context's own key set before it was known to be a mapping |
| A1 | `validate_bundle` entry | 1297 | the auditor read an emitted bundle with nothing establishing it was readable |

**None was corrected where it was reported.** D1, D3 and A1 are orderings; D5 and the
context are the missing half of an existing rule; D2 and D4 apply a rule the same scan
already applied to Observation bundle sections. No new ruleset, no new owner, no
path-specific guards.

## 4. The narrow gate, and getting it wrong first

`validate_bundle` **returns** violations. A raw `KeyError` out of it is therefore not a
rejection — it is the auditor failing to answer, and an auditor that cannot answer cannot
be the independent half of anything.

The first attempt made the entry gate call `validate_emitted_bundle`, which also
recomputes identities. It converted 1317 cases and **broke four existing tests**, because
it pre-empted the cross-record diagnosis for a bundle that was both unreadable and
cross-record-invalid: a supersession cycle reported as a schema failure. That is the
ADR-0013 line — completeness and admissibility are distinct obligations — and the
enumeration would never have caught it, because the enumeration only asks whether the
auditor raises. **The existing focused tests caught it.** Both kinds of coverage were
needed and neither would have done alone.

What counts as unreadable is now one declaration, shared with the Observation side:

- `required` and `type` — the direct cases;
- `enum`/`const` **only** when the instance is a list or dict, which no enum member ever
  is, so a *string* not in the enum stays semantic and keeps its own diagnosis;
- `oneOf` **only** when every branch objected mechanically, applied recursively, so a
  reference naming the wrong `kind` stays semantic;
- **never** anything reached through `if`/`then`/`else`/`not`, which states what a value
  must be *given another field's value* — a consistency rule between fields, not a read
  failure.

## 5. Three test fixtures were incomplete and had never been checked

Two supersession relations omitted `schema_version`, `reason_codes` and `evidence_refs`;
an After State Candidate stub carried two of its eight required properties. They passed
only because nothing settled readability first. They are completed, not exempted, so each
proves the rule it was written for.

## 6. Result

```text
Engine   7770 cases    78 -> 0 raw   0 new outside the frozen set
auditor  7248 cases  1317 -> 0 raw   0 new outside the frozen set
         reported 4184 -> 6697   accepted 1747 -> 551
```

Reported rises and never falls: the gate answers where it used to raise, and masks
nothing.

## 7. What is still not claimed

`INPUT_TOTALITY_PROVEN` stays **false**. This is a measurement over four fixtures — two
requests and two emitted bundles — with one substitution set, and its scope has now been
wrong four times. Two fixtures are still single-binding, so no enumeration here can reach
a defect that needs two bindings to express, which is precisely the shape of the ADR-0019
finding. The auditor enumeration covers emitted bundles only; `validate_fixture_suite` and
the Observation validator are not enumerated. Change and Reflow have no schema in v0.1, so
there is no oracle to enumerate against.

The honest summary is that the input space is closed **over what is measured**, the
measured surface is now stated as data rather than as a claim, and the remaining gaps are
listed above rather than implied by a number.
