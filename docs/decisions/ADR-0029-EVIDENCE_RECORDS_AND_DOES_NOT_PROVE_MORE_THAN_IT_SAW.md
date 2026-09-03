# ADR-0029 — Evidence records what was observed, and never more than that

**Status:** accepted
**Bounds:** KERNEL_CONSTITUTION 第27–30条, KERNEL_INVARIANTS E-001–E-005,
COMPLETION_SEMANTICS ch.3, 00_KERNEL/04_DIFFERENCE/CLOSURE_POLICY.md §4–§8,
00_KERNEL/07_EVIDENCE/*.
**Ratified decisions:** Issue #37 構造参謀判断 — `Q1-A + Q1-ii`, `Q2-A`, `Q3-A`,
and the ownership boundary (`EVIDENCE_OWNS_SUFFICIENCY_PRODUCTION=true`,
`EVIDENCE_OWNS_DIFFERENCE_CLOSURE=false`).

## 0. Why the executor stopped before writing any of it

Five semantic questions were put to the Human Authority before implementation rather than
after. Two were answerable from the frozen tree and were reported as answered; three were
not, and every one of the three would have shaped the whole vertical:

```text
Q1  第28条's before_state / after_state have no definition anywhere in the Kernel
Q2  E4–E6 have labels and a prohibition, and no proof predicate
Q3  Change Result Evidence with no executor to produce a result
```

Choosing one reading and building on it would have produced a working engine resting on a
semantics nobody ratified. That is the cheapest kind of correctness to fake and the most
expensive to unwind, because by then every schema, fixture and test agrees with the guess.

The two that were already decided are recorded here as *found*, not as *chosen*:

```text
sufficiency ownership   ADR-0009 line 96: NOT CLAIMED — LATER PHASE.
                        Difference carries the results; no producer existed.
independence            CLOSURE_POLICY.md §4: v0.1 admits only false, and
                        verification_independence_ref is always null.
```

## 1. Q1-A + Q1-ii — every field present, state bound and never embedded

第27条 requires Observation Evidence to be storable in a Change-free cycle. 第28条 makes all
fourteen fields the minimum. The two read together leave one question: what does an
Observation Evidence record do with `after_state`, `change_identity` and `authority_used`?

Ratified: **all fourteen present on every record; `null` where inapplicable.**

```text
ALL_MINIMUM_FIELDS_PRESENT=true
NOT_APPLICABLE=null
STATE_BINDING=revision + semantic_fingerprint
STATE_BODY_EMBEDDED=false
```

The alternative that looks most reasonable and is wrong is Q1-C: `after_state = before_state`
on an Observation Evidence record, because nothing changed. It was rejected, and the reason
generalises past this field:

```text
"NOTHING CHANGED" IS A CLAIM ABOUT A SECOND POINT IN TIME
A SECOND POINT IN TIME REQUIRES A SECOND OBSERVATION
```

An Observation Evidence record has one observation. Copying the before-state across asserts an
unobserved absence of change — `NO_RESULT != PROVEN_ABSENCE` with the sign flipped.

`null` rather than omission matters for a different reason. Omission makes "this Evidence
carries no Change" and "this Evidence forgot to say" the same bytes. One is a fact, the other
a defect, and a record that cannot separate them is not evidence of anything.

## 2. Q2-A — the vocabulary stays; the derivation stops at E3

```text
SCHEMA_VOCABULARY=E0..E6
PHASE_6_DERIVABLE_LEVELS=E0..E3
CALLER_CLAIMED_E4_E5_E6=REFUSED
POLICY_REQUIRING_E4_E5_E6=INSUFFICIENT
```

The frozen tree gives E4–E6 three labels, a completion-level mapping, and `E-005`, which
forbids overstating a level and defines no positive criterion for any. v0.1 has no Runtime,
and §1's independence finding makes E6's "独立" unobservable by construction.

So Phase 6 refuses them. Two things about the shape of that refusal:

**The vocabulary is not narrowed.** `evidence_level` admits E0..E6 in the schema. Narrowing
it would be a phase editing the constitution to fit what it can currently do.

**A policy demanding one is held, not lowered.** `minimum_evidence_level ∈ {E4,E5,E6}` returns
`INSUFFICIENT` with `EVIDENCE_LEVEL_UNREACHABLE_IN_PHASE_6`, and the Difference stays open.
The reason code exists so a reviewer can tell "the evidence is too weak" from "this Kernel
cannot yet produce evidence that strong" — two situations with entirely different remedies,
which the four-valued result cannot distinguish on its own.

### 2.1 The ceiling, and why it only ever lowers

The method class states a *claim*. What the record contains sets a *ceiling*.

```text
≥1 completed attempt   → ceiling E3
artifacts only         → ceiling E1
neither                → ceiling E0

evidence_level = min(claim, ceiling)
```

This is `E-005` as a computation. A record whose method class says INTEGRATION_TEST but which
carries no completed attempt did not run an integration test, whatever it calls itself. There
is no rule that raises a level, because a rule that raised one would be a rule for making
claims larger than their evidence.

E2 and E3 share a ceiling because the Kernel separates them by *what was exercised* and
Evidence has no way to observe that. The honest move is to let the claim decide between them
downward, not to invent an observable difference.

## 3. Q3-A — no executor, no Change Result Evidence

```text
UNGROUNDED_CHANGE_RESULT_EVIDENCE=REFUSED
UNKNOWN_OBSERVATION_EVIDENCE=ALLOWED
AUTHORIZED_CHANGE_NE_EXECUTED=true
CAUSALITY_NOT_CLAIMED=true
```

`CLOSURE_POLICY.md` §4 gives the chain, and v0.1 is missing its first link:

```text
CHANGE EXECUTION RESULT → RE-OBSERVATION REQUEST → NORMALIZED AFTER FACTS
                        → CHANGE RESULT EVIDENCE
```

`change.schema.json` pins `execution_result` to null; `E-002` names execution return codes,
agent success reports and file existence as the three things that are *not* an after-state.
There is nothing to convert.

The refusal is not a dead end, and that is load-bearing. UNKNOWN, BLOCKED and INCOMPLETE are
recordable as **Observation** Evidence, so a caller facing this situation has a truthful
record available. A route that only refused would push callers toward mislabelling — which is
precisely the substitution `E-002` forbids, arrived at by making the honest path unavailable.

Where a post-change Observation does exist, what the record proves is exactly one thing:

```text
POST_CHANGE_OBSERVATION != EXECUTION_RECEIPT != CAUSALITY_PROOF != E4_PROOF
```

`causality_claimed` and `execution_receipt_present` are schema-pinned `false`. The
non-claims are structural; no record can carry the opposite.

Note what is *not* required: that the after-state differ from the before-state. Requiring a
difference would be asserting that the Change changed something, which is the causal claim
being disowned two paragraphs up.

## 4. Ownership — a producer, not a second Difference

```text
DIFFERENCE_OWNS_CLOSURE_POLICY_SCHEMA=true
DIFFERENCE_OWNS_SUFFICIENCY_RESULT_SCHEMA=true
EVIDENCE_OWNS_SUFFICIENCY_PRODUCTION=true
EVIDENCE_OWNS_DIFFERENCE_CLOSURE=false
```

Difference's four-valued result schema is used unchanged. The distinctions it cannot carry —
which of nine statuses, absence versus emptiness, too-weak versus unreachable — live in
`reason_codes` beside it, and `not_evaluated_here` names the six policy fields sufficiency
does not decide. `SUFFICIENT != CLOSED`, stated in the return value rather than in a comment.

### 4.1 The half the owner does not check

Difference's `closure_policy_semantic_errors` recomputes `policy_semantic_fingerprint` and
refuses a rewritten requirement. It does not recompute the `CP-` address. Sufficiency
recomputes the address and **does not** re-compare the fingerprint.

The omission is the point. A second fingerprint comparison could never fail, because the
owner already refused that case one line earlier.

```text
A CHECK THAT CANNOT FAIL READS AS PROTECTION AND PROVIDES NONE
```

This repository has shipped two of those (ADR-0027 §3.5, §3.6). The division of labour is
asserted by a test that calls `closure_policy_semantic_errors` on the bad-ID policy and
proves it returns `[]`, so if the owner ever grows an ID check, the redundancy becomes
visible instead of accumulating.

## 5. Provenance, inherited rather than restated

The Phase 5 P1 defect — a self-consistent record read as a produced one — has the same shape
one phase later, and a worse blast radius: Evidence is a record *about* other records, so a
forged predecessor yields a false claim wearing a true fingerprint.

The engine does not take predecessor **records**. It takes predecessor **requests** and runs
the canonical owners:

```text
observation_request              → observe()
post_change_observation_request  → observe()
change_request                   → derive_change()   → which reproduces the Authority decision
```

A forged predecessor is not refused. It is inexpressible — there is no parameter to put one
in. `test_the_engine_takes_a_request_and_not_a_record` asserts that handing the engine a real
minted Observation record fails, which is the property stated from the outside.

## 6. Four findings from this work unit, recorded with how each was found

### 6.1 Found by the totality sweep

Both are the same class as Decision 0002's D3:

**`derive_level` on an unhashable method class.** `dict.get` raises `TypeError` on a list.
A `TypeError` crossing the Evidence boundary is a caller learning about Evidence's internals
instead of about its own request. Fixed at the owner, with a type check before the lookup.

**`observe` reading its request keys directly.** An absent key surfaced as `KeyError` through
Evidence's boundary. The Observation request has no declared envelope grammar — the gap
`difference/admissibility.py` was written to close for its own envelope. Evidence translates
`KeyError`/`TypeError`/`IndexError` **at the delegation call site only**, and reports the
predecessor-side gap rather than taking it: declaring that grammar belongs to the phase that
owns the request. A wider `except` would eventually swallow a real defect in this module,
which is what a broad `except TypeError` always does.

### 6.2 Found by re-reading the diff adversarially, before it shipped

**A comparison that orders bytes where it claims to order instants.**
`_require_recorded_after` compared the recording instant to the Observation's end
lexicographically, and its own docstring asserted that this was exact for the canonical
timestamp form. It is not: `common/timestamp.schema.json` admits optional fractional
seconds, and `...00.5Z` sorts before `...00Z` on `'.' < 'Z'` while being half a second
later. The guard would have rejected a correctly-ordered record and passed no test, because
no fixture used a fractional second. It now goes through `observation.boundary.instant`, the
repository's canonical parser, and the fractional case is a regression test in both
directions.

The docstring is the part worth keeping in view. It did not merely fail to notice the flaw;
it *asserted the flaw away*. A confident sentence about why a check is exact is the easiest
place in a diff for a wrong check to hide.

**A branch no input could reach.** `_minted_observation` raised
`EvidenceProvenanceError("produced no Observation")` when `observe` returned an empty bundle.
`observe` always appends the Observation it mints, so the branch could never run. Removed;
the extraction now happens inside the delegation guard, so if that postcondition ever changes
the result is a clean `EvidenceError` rather than an `IndexError` — which is what the
unreachable branch was reaching for, achieved by a route that works.

Removing it left `EvidenceProvenanceError` exported and never raised. That was also deleted.
An error class named for a check is a claim that the check exists; here provenance is
structural (§5), and a reader who goes looking for the guard should find the explanation of
why there is nothing to guard, not a class that never fires.

## 7. The through-line, eighth instance

Every guard added here has a control that shows it reporting a violation written into a real
copy of the real package, and a control that shows an untouched copy sweeping clean with the
same module count. The live assertions and the injection controls call **the same functions**
(`tests/evidence_guards.py`), because a control exercising something the live guard does not
is the seventh instance wearing a third hat.

```text
LIVE_ASSERTION_AND_INJECTION_CONTROL_SHARE_ONE_SWEEP=true
```

The list, unchanged in shape since ADR-0027 §3.6:

| | the claim | what stood in its place |
|---|---|---|
| Phase 5 P1 | "produced by the evaluator" | a digest anyone can recompute |
| Decision 0002 | "these are the ratified permissions" | a check that they are *strings* |
| Binding round 1 | "the guard evaluates records" | a path existing only in a checkout |
| `307e5ea` | "the protocols state the route" | four copies compared to nothing |
| `922ccd0` | "every copy is checked" | one syntactic form of four |
| `bdf6588` | "normalization has one owner" | an assertion that could not fail |
| `6b44098` | "the suite contains this control" | a shell command run once |
| Phase 6 §4.1 | "the policy address is verified" | *would have been* a second fingerprint compare |
| Phase 6 §6.2 | "this comparison is exact" | *would have been* a lexicographic compare |
| Phase 6 §6.2 | "no Observation was produced" | *would have been* a branch with no input |

The last three were caught before they shipped, by one question asked of each check in the
diff: **what input would make this fail?** Three times the answer was "none", and each time
the check read, until that question, exactly like the ones that work.
