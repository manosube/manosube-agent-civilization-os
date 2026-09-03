# ADR-0030 — A failed observation is still an observation

**Status:** accepted
**Bounds:** KERNEL_CONSTITUTION 第27条/第31条/第33条,
00_KERNEL/04_DIFFERENCE/DIFFERENCE_CONTRACT.md §4,
00_KERNEL/07_EVIDENCE/EVIDENCE_CONTRACT.md §1A/§12,
`difference/engine.py:_ACCEPTED_OBSERVATION_STATUS`,
`difference/projection.py:_NEGATIVE_STATUS_MAP`.
**Ratified decision:** Human Authority, Issue #37 / PR #38 — recommended by the Structural
Advisor, decided by SHUKOU.

```text
ACCEPT_FAILED_OBSERVATION_IN_DIFFERENCE
FAILED_PROJECTION=UNKNOWN
FAILED_ATTEMPT_AND_FAILURE_CLASS_PRESERVED=true
INVALID_OBSERVATION_REMAINS_REFUSED=true
EVIDENCE_MUST_NOT_BYPASS_DIFFERENCE=true
THIRD_EVIDENCE_POSITION_CREATED=false
```

## 0. How the contradiction was made rather than found

ADR-0029 §1A bound Evidence to a Difference, because an Evidence record that named no
Difference was no binding at all. That fix was right and is kept. It also had a consequence
nobody had asked about: Evidence inherited the Difference producer's admissibility, and that
producer refused two Observation statuses outright.

```text
INITIAL FAILED OBSERVATION -> Difference producer refuses -> no Observation Evidence anywhere
```

第31条 requires failure, EMPTY, BLOCKED, STALE and non-arrival to reflow as formal Evidence.
So closing one hole opened a contradiction with the constitution — and the executor found it
while writing the tests for the fix, not while designing it.

That is worth naming. A correction that satisfies its own review can still break something
the review was not looking at, and the only reason this surfaced is that the status route was
exercised end to end rather than asserted.

## 1. What Phase 6 did with it, and did not

Phase 6 **held** the contradiction. 第33条 says a contradiction is preserved, not deleted,
overwritten or averaged, so it was recorded in `EVIDENCE_CONTRACT.md`, pinned from both sides
by test, and returned to the Human Authority with the three ways it could be closed:

1. widen the Difference producer's admissibility — a Phase 3 amendment;
2. let Evidence bypass the Difference for these statuses — reopens ADR-0029 §1A;
3. add a third position to 第27条 — a constitutional amendment.

Each belongs to somebody else. The executor did not choose, and — when the Structural
Advisor recommended (1) — did not implement on the strength of a recommendation either. A
recommendation is not an authorization, and treating it as one would have broken the exact
boundary the escalation existed to protect.

What the executor did do while waiting was verify the recommendation's premise, because a
decision resting on a false premise is worse than a decision deferred.

## 2. The premise held, and was stronger than stated

The recommendation's argument was that the Difference layer already defines
`FAILED -> UNKNOWN`. It does — and so does the Difference *contract document*:

```text
DIFFERENCE_CONTRACT.md §4   "NO_RESULT、FAILED、UNKNOWN、UNOBSERVED はproven absenceへ
                             昇格せず UNKNOWN knowledge のまま保持する"
projection._NEGATIVE_STATUS_MAP   FAILED  -> UNKNOWN
                                  INVALID -> REJECT_OR_QUARANTINE
engine._ACCEPTED_OBSERVATION_STATUS   refused FAILED before either was consulted
```

So this is not an amendment to the Difference contract's semantics. **It is a repair of an
engine that disagreed with its own contract.** The asymmetry the recommendation asked for —
admit FAILED, keep refusing INVALID — was already written in the map, by whoever wrote it.

One thing the executor reported before ratification because it changes what is being decided:
the map applies to a Negative Observation's *evaluation status*, while the gate reads the
Observation record's *own* status. The mapping existed; the gate refused before reaching it.
That distinction makes the change smaller than "add a semantics", not larger.

## 3. Why UNKNOWN is a safe projection

Not because it sounds cautious. Because of where it sits:

```text
UNKNOWN in UNRESOLVED_KNOWLEDGE   True
UNKNOWN in EVALUABLE_KNOWLEDGE    False
UNKNOWN in PROVEN_ABSENCE         False
```

A failure passing through cannot become satisfaction, proven absence or completion, and that
is a property of those sets rather than a promise in a comment. `EVALUABLE_KNOWLEDGE` is what
Target Satisfaction reads; `PROVEN_ABSENCE` is what `EMPTY` and `ABSENT` require.

## 4. The projection does not overwrite the failure

```text
Difference   knowledge_status = UNKNOWN
Observation  status = FAILED, attempts = [(FAILED, SOURCE_ERROR)]
Negative     negative_status = FAILED
Evidence     status = FAILED, level = E0, attempt_outcomes = [FAILED]
```

`UNKNOWN` is what the Difference *projects*. `FAILED` is what the record *says*, and it still
says why. Replacing the second with the first would break `NO_RESULT != PROVEN_ABSENCE` from
the other direction — not a failure promoted to a result, but a failure erased into a shrug.

## 5. Failure does not become sufficiency

FAILED is in `_DETERMINATE_INSUFFICIENT_STATUSES`, so a FAILED Evidence record evaluates
`INSUFFICIENT` at every floor including E0, carrying `EVIDENCE_STATUS_FAILED`. A test asserts
this across all seven floors, with a control proving the same route can reach `SUFFICIENT` on
a complete observation — without which "never sufficient" would also hold for a route that
never works at all.

## 6. INVALID, refused twice and neither redundant

```text
gate        _ACCEPTED_OBSERVATION_STATUS excludes INVALID  -- reads the Observation's status
projection  _NEGATIVE_STATUS_MAP -> REJECT_OR_QUARANTINE   -- reads the Negative evaluation
```

Two different questions about two different records. An INVALID Observation is not a
trustworthy canonical record; a FAILED one is a schema-valid record of an attempt that did not
reach its subject. That is the whole distinction the decision rests on.

## 7. What the amendment is *not*

Each was asserted rather than assumed, because an amendment quietly wider than its decision
is the same defect family as a claim wider than its check:

* **Not wider than one status.** A test pins `_ACCEPTED_OBSERVATION_STATUS` to exactly the
  eight, and separately pins that the only excluded status is `INVALID`.
* **Not a bypass.** The FAILED Evidence record's `difference_ref` is the Difference its own
  producer derived from that failed Observation.
* **Not a third position.** 第27条 still has two, and a failure is recorded in the first.
* **Not a Phase 7 excursion.** Nothing here touches Reflow, Lineage or State transition.

## 8. What was proven, and by what

Two files, and the difference between them is the point.

`test_failed_observation_route.py` calls the Difference owner's own gates —
`validate_emitted_bundle` and `reference_closure_errors` — over the real bundle
`derive_differences` emitted for the failed Observation, carrying the sufficiency result
Phase 6 produced, against that Difference's own emitted Closure Policy.

`test_public_failed_round_trip.py` runs the **route**:

```text
observe() → derive_differences() → derive_evidence() → evaluate_sufficiency()
         → a real predecessor context → derive_differences()
```

The first was written when this ADR was drafted, and the reasoning offered for stopping there
was that `difference_round_trip_request` cannot produce a failed predecessor, so the gates
were run directly instead. That reasoning was true about the *helper* and wrong about the
*conclusion*. A real predecessor for the failed Difference did not need that helper at all: the
first derivation's own output — its Difference, its events, its bundle as context — is one.

Structural review named the gap exactly: **running a gate is not running the route.** Both
files are kept, because they prove different things. The gates show each check accepts these
records; the route shows a real predecessor carrying a real sufficiency result survives a real
re-derivation. Neither substitutes for the other, and the second is the one Issue #37 requires,
since a demonstration run once outside the repository is not Repository Evidence.

The route test also pins two things that had been left to inference:

```text
materialized status          = OPEN
CLOSED lifecycle event count = 0
candidate_completion_records = []
evaluations                  = []
```

They do follow from "UNKNOWN is not evaluable knowledge" and "FAILED Evidence is never
SUFFICIENT". An inference is not a regression test, and the thing a regression would break is
the conclusion.

And it closes a reporting overstatement worth recording. The round-4 report said the failure
lineage was asserted "in three places — Observation, Negative and Evidence". The tests checked
`result`/`failure_class` on the Observation and `attempt_outcomes` on the Evidence, separately;
nothing showed the Negative Observation was about *that* attempt, so a Negative Observation
citing a different one would have passed. The route test resolves `ATTEMPT-0001` across all
four records. The claim was slightly wider than the check — the eighth instance of the same
habit, caught by a reviewer reading the tests rather than the report.

The negative control runs through `derive_differences` rather than through
`reference_closure_errors` directly, because the claim being controlled is about the route. It
is paired with an assertion that the forgery and the honest record differ in nothing but that
one tag, so the refusal cannot be caused by something else the forgery changed.

## 9. The through-line, fourteenth instance

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
| Phase 6 round 2 | "the sufficiency result is consumable" | two tests that never touched a gate |
| ADR-0030 §8 | "the failure lineage is asserted in three places" | two of the three, and not the joining one |
| **ADR-0030** | **"the engine implements this contract"** | **a gate refusing what the contract admits** |

The last row is a different shape from the rest, and worth keeping separate. Every earlier
row is a claim with nothing behind it. This one is a *contract* with an engine behind it that
said something else — the document was right, the map was right, and the gate in between
disagreed with both. Nothing was overstated; two things that should have been one had drifted.

The check that would have caught it does not exist anywhere yet: no test asserts that
`_ACCEPTED_OBSERVATION_STATUS` agrees with what `DIFFERENCE_CONTRACT.md` §4 says a Difference
may be derived from. That is stated here rather than built, because it is a Phase 3 guard over
a Phase 3 surface.
