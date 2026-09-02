# ADR-0023 — One readability owner, and Change/Reflow as opaque structural provenance

**Status:** accepted
**Bounds:** ADR-0013 §completeness-vs-admissibility, ADR-0022 §3.
**Supersedes nothing.**

## 1. What the `a11d7c7` review found, and what it actually was

A P2 said the emitted-bundle readability gate skipped every record of a type with no
canonical schema, so a carried Change or Reflow record whose declared identity was absent or
unhashable passed the gate and the auditor then indexed it — `KeyError`, `unhashable type`.

Reproduced 5/5. But the finding was not a missed case. `validate_typed_record` **already**
checked the declared identity key for every type, schema-backed or not, and the gate added
beside it one round earlier implemented a *narrower* version of the same rule. A second,
weaker answer to a question already answered correctly one module away — inside the gate
written so producer and auditor could not disagree. That is the ADR-0015 auditor-only /
ADR-0020 Engine-only failure a third time, committed while correcting the second.

## 2. One owner

`difference/readability.py` is now the only module that decides whether a canonical record
can be read. Four partial restatements are deleted; `validate_typed_record`,
`validate_typed_section`, `merge_records`, the emitted-bundle gate, the predecessor boundary
and the independent validator all delegate.

Diagnostic order is preserved exactly: a non-object still raises before the schema pass and
an unusable identity after it, so for a schema-backed type the schema still reports an absent
key first and the identity message stays reachable only for unschematized types.

Two things are deliberately **not** in the owner, and a contract test asserts it never calls
`validate_record`, `require_schema_version` or `canonical_bytes`:

* **semantic admissibility** — a record that is readable and *wrong* keeps its own
  diagnosis. Folding this in reported a supersession cycle as a schema failure once already.
* **identity recomputation** — whether an identity *recomputes* is about payload meaning.
  Whether it can be used as a mapping key is not.

Ownership is pinned **in both directions**: every gate holds the same owner object, and
`conformance.py` / `predecessor.py` are parsed for any re-introduced readability decision.
That second direction caught four restatements on its first run that no call-site assertion
would have found.

## 3. The blocker, and the ownership error underneath it

Populating Change and Reflow — required because an empty section had been counting as
coverage — exposed 15 further raw exceptions no previous fixture could reach. Closing the
`reflow_transitions[*].committed_at` cases appeared to require declaring what a Reflow record
must contain, which this phase does not own. Work stopped and reported.

**The correct resolution was not to author the contract. It was to stop reading.**

The auditor was reading `committed_at`, `event_type`, `project_id`, `after_state`,
`from_revision`, `to_revision`, `before_fingerprint`, `after_fingerprint`, `lineage_head_ref`
and `evidence_refs` off a Reflow record, and parsing two timestamps out of it. No canonical
schema declares any of them. That was **a Reflow field contract authored here by
assumption** — an undeclared rule that could not be satisfied, argued with, or versioned,
because nothing stated it. Reading it was also unsound in the ordinary way: the first fixture
to populate the section reached `fromisoformat` on a field nothing had validated.

```text
REFLOW_SCHEMA_AVAILABLE=false
REFLOW_FIELD_SEMANTICS_OWNED_BY_DIFFERENCE=false
REFLOW_SEMANTIC_VALIDATION_IN_PHASE_3=false
REFLOW_RECORD_TREATMENT_IN_PHASE_3=OPAQUE_STRUCTURAL_PROVENANCE
```

**This is a phase-bounded non-claim, not a permanent rejection of a Reflow contract.** The
Reflow phase owns those fields and must state them as a canonical schema with its own
validation. Until it does, Phase 3 must not become their owner by default — which is exactly
what happens when a reader is added and nobody notices it implied a contract.

What survives is what this phase genuinely owns: the *reference* on the Difference-owned
lifecycle event and Closure Evaluation, its declared kind, and whether it resolves.

## 4. Opaque is not unchecked

Still enforced for an unschematized record, because all of it is owned structurally and
needs no Reflow contract to state it: the section is a canonical collection; each record is
an object; the declared caller-assigned identity exists and is usable as a mapping key; one
identity cannot name two payloads; reference-shaped provenance follows the existing bounded
policy.

## 5. Measured

```text
                             15 cases
  -7  removed the unowned Reflow semantic read        ->  8 remaining
  -8  totalized contract-owned reads                  ->  0 remaining
```

The 7 were not assumed — the count was remeasured after step one, as it was not the 14 a
subtraction would have predicted. The remaining 8 were schema-backed Observation reads,
closed under two rules with existing owners and no new registry:

* `PARSE_ONLY_AFTER_VALIDATION` — every `fromisoformat` in the validator now goes through
  one `_canonical_time`, which returns `None` rather than raising. A malformed schema-backed
  timestamp is reported by the schema pass that owns it; the predicate's job is to answer.
* `RESOLVE_ONLY_AFTER_REFERENCE_RESOLUTION` — `after_observations` already records an
  unresolved or wrong-kind reference as `None`; reading that result before indexing was the
  whole fix.

## 6. An empty section is not coverage

`changes` and `reflow_transitions` are populated by real Engine output, and a
`supersession_relations` fixture was added rather than declared a non-claim, because that
section is Difference-owned. Five sections remain unpopulated and are stated with reasons —
all schema-backed, all produced by a later canonical owner, so what is missing is
*enumerated* coverage rather than any check. The P2 was the opposite: an unschematized type
where an empty section meant no check ran at all.

One fixture choice is worth recording. The first `unschematized` fixture used the REOPENED
route, which also populates `reflow_transitions` — and which the independent validator
rejects with nine Closure Evaluation *execution* provenance violations, the standing
`REOPENED_CROSS_RECORD_PROVEN=false` non-claim, present with or without a carried Change. A
fixture that is already red cannot be the positive control for "a clean bundle stays
accepted", so both records ride a RETAINED lineage that audits clean.

## 7. Result

Measured when this ADR was written. **The auditor sweep was deferred out of Phase 3 by
ADR-0024**, so the second line is a historical record of what was measured, not a standing
Phase-3 claim; `AUDITOR_ADVERSARIAL_TOTALITY_CLAIMED=false` now.

```text
Engine sweep     7770 cases   0 harness faults   0 raw exceptions   (retained)
auditor sweep   16044 cases   0 harness faults   0 raw exceptions   (deferred, ADR-0024)
suite           25242 passed, 10 skipped                            (pre-split)
mypy            138 / 12  -- one FEWER than the 139 baseline: removing the unowned
                             Reflow reads deleted a pre-existing error
```

## 8. The obligation this creates

The Reflow phase must replace this non-claim with a canonical schema and its own semantic
validation. `REFLOW_FIELD_SEMANTICS_CLAIMED=false` is asserted at source level, so a reader
re-added anywhere in the Difference auditor fails the suite — whether or not whoever adds it
notices it implies a contract.
