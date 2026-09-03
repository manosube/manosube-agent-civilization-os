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

## 1A. Exact Difference binding — the correction that changed the most

Structural review of `6640ffd` withheld the work unit on four findings, and the first was
the one that mattered most: **an Evidence record named no Difference at all.**

```text
Difference A's Evidence + Difference B's Closure Policy -> Difference B SUFFICIENT
```

That was reproducible in three lines. 第27条 puts Observation Evidence *behind* a
Difference — "before state と Difference を裏付ける証拠" — so a record that named none was
not a weaker binding, it was no binding.

The Difference is now derived, by its own producer, from the Observation this record is
about. The reproduced Observation bundle is **substituted into** the derivation request
rather than compared against a supplied one, for the reason substitution keeps beating
comparison: a request shape in which two things can disagree eventually meets a caller who
makes them.

Three things now name a Difference and all three arrive by derivation: the sufficiency
request, the Closure Policy's own subject, and every Evidence record. On the Change route a
fourth joins them — the Change's `difference_ref`, which comes from the Authority decision,
so two independent derivations are required to agree rather than two labels compared.

### 1A.1 What binding to a Difference costs, and why the cost is right

Evidence now inherits the Difference producer's admissibility. Five of the nine Observation
statuses reach an Evidence record; `FAILED` does not, because
`difference/engine.py` refuses to derive from an Observation it cannot read a State from.

第31条 wants failure reflowed as Evidence, so there is a real gap. It is reported, not
taken: widening a predecessor's admissibility is that phase's decision, and routing around
it here would reopen exactly the hole this correction closed. The gap is also narrower than
it looks — a FAILED *re-observation* is recordable, since the post-change Observation never
reaches the Difference producer — and both halves are pinned by test.

## 2. Q2-A — the vocabulary stays; the derivation stops at E1

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

The first implementation of this failed the review, and the way it failed is worth stating
plainly. It read the level from a **string on the Evidence request**:

```text
one identical Observation, three caller labels -> E1, E2, E3
one artifact reference to content nobody verified -> E0 becomes E1
```

That is not "E0–E3 from structural proof". It is a caller naming its own evidence strength
with a ceiling function on top, and the ceiling only made the label harder to see.

So the channel was removed rather than checked. There is no `observation_method_class` key,
no `evidence_level` key, and the request is closed, so writing one is refused rather than
ignored. The level is a function of one thing:

```text
E1  the Observation Engine certified its declared scope completely observed
    (status ∈ {COMPLETE, EMPTY}) over ≥1 content-addressed source snapshot
E0  otherwise
```

### 2.1 Why the derivation stops at E1 and not at E3

Applying "from structural proof, not from a caller label" to E2 and E3 gives the same answer
Q2-A gave for E4–E6, for the same reason. Deciding either requires knowing a *test executed*,
and the frozen tree records no such thing:

```text
observation_method.schema.json
  procedure_kind        {"const": "CANONICAL_OBSERVER"}
  normalization_profile {"const": "FIXTURE-0.1"}
```

Every canonical method is the same method. The only way to separate E1, E2 and E3 today is
to let a caller assert which one it was — the channel just removed.

`PHASE_6_DERIVABLE_LEVELS` therefore narrows from `E0..E3` to `E0..E1`. This is reported
rather than assumed: it is strictly **fail-closed** relative to the reviewed head, it narrows
only what may be *minted* and never the schema vocabulary, and it weakens no policy — a floor
of E2 through E6 is held `INSUFFICIENT` with a reason code and a sentence saying what would
have to exist. If a later phase defines a proof predicate for E2 or E3, `DERIVABLE_LEVELS`
widens and nothing else changes.

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

## 5A. The two smaller corrections

**Sub-second freshness (P1-C).** The age gate compared `int(delta.total_seconds())`, and
`int()` truncates toward zero, so both sub-second violations rounded to "no violation":

```text
int(0.5s in the future)    -> 0 -> not future-dated
int(0.5s old), max age 0   -> 0 -> not too old
```

This is the *same* fractional-second defect §6.2 records on the recording-instant guard,
surviving on the other side of the module — which says something about fixing a defect at
one site and calling it fixed. Comparison is now on exact `timedelta`s; the integer survives
only as a reported value.

**A reference that addressed nothing (P2-D).** `completion_semantics_ref` carried
`repository`, `commit_sha` and `blob_sha` and checked none of them, so a reference naming
commit `0000…` and blob `1111…` was accepted as a canonical content-addressed source:

```text
REFERENCE_SHAPE_VALID=true
REFERENCED_BLOB_VERIFIED=false
CONTENT_ADDRESS_BINDING_PROVEN=false
```

The unverifiable fields are gone — a pure function cannot check a repository or a commit, and
a blob address is commit-independent anyway — and the verifiable one is pinned in `levels.py`
with a repository test holding the pin to `git hash-object` of the live document. Every field
that remains is checked against something. Fields that carry a claim nothing verifies are
worse than absent fields, because absence does not assert.

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
| Phase 6 P1-A | "the Evidence backs this Difference" | a record naming no Difference at all |
| Phase 6 P1-B | "E0–E3 from structural proof" | a string the caller wrote |
| Phase 6 P1-C | "evidence older than the bound is stale" | a comparison that truncated first |
| Phase 6 P2-D | "a canonical content-addressed source" | three fields nothing checked |

The through-line holds across all twelve: **a claim is only as good as the thing that would
break if it were false.** The four review findings are four different ways of having nothing
there — no binding, a caller's word, a comparison that rounds the violation away, and fields
answerable to nothing.

Three rows were caught in-session by asking, of each check in the diff, *what input would
make this fail?* Four were caught by a reviewer asking it of checks that had already passed
their own tests. That the two sets do not overlap is the argument for the review step.

One correction removed a check rather than adding one. Binding the Change to the derived
Difference made the before-state comparison unreachable — Authority already refuses a
decision evaluated against another State — so it was deleted and replaced by a test that
holds the three owners to the guarantee. A fix that leaves a dead branch behind has traded
one silent claim for another.
