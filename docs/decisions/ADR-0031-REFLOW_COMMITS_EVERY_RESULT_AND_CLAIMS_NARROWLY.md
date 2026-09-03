# ADR-0031 — Reflow commits every result, and claims narrowly against CLOSURE_POLICY.md

**Status:** accepted
**Bounds:** KERNEL_CONSTITUTION 第31–33条, KERNEL_INVARIANTS R-001–R-005,
`00_KERNEL/04_DIFFERENCE/CLOSURE_POLICY.md`, `00_KERNEL/04_DIFFERENCE/DIFFERENCE_LIFECYCLE.md`,
`00_KERNEL/08_REFLOW/REFLOW_CONTRACT.md`.
**Ratified basis:** Issue #39's own acceptance criteria and eight-step pre-implementation
protocol; the seven-point semantic inventory `REFLOW_CONTRACT.md` §§1–2 resolves entirely
from the frozen tree, with no point requiring escalation to a two-way constitutional fork.

## 0. What Reflow is, in one sentence found rather than chosen

`difference/lifecycle.py`'s own docstrings, written in Phase 4 before Reflow existed, name
the answer directly: *"A Closure Evaluation is provenance a later canonical owner
produces... Reflow is a later element with no schema in v0.1, and its own owner enforces
it."* Reflow is that owner, for exactly the questions that sentence leaves open — Closure
Evaluation production, the lifecycle transition it admits, the Atomic State commit, and
nothing `difference/lifecycle.py` already decides (lifecycle legality, event-to-Evaluation
binding, blocker-payload shape).

## 1. Provenance by reproduction, applied to G7–G17

`CLOSURE_POLICY.md` requires an after-state Observation independent of Change result and
requires the Target genuinely re-checked, scope-complete, conflict-free, unknown-free.
Rather than re-implement Difference's own normalization and comparison rules as a second
copy inside the evaluator, `reflow/closure.py` calls `derive_differences` again on the
caller's fresh re-observation and reads whether the Target Predicate lands in that
reproduction's own `satisfied_target_predicates`. That route only fires inside
`derive_differences` when knowledge is `KNOWN`, scope is `COMPLETE`, and the Observation is
`COMPLETE`/`EMPTY` — so G7, G9 (null case), G10, G13, and jointly G14–G17 are one real
reproduction of the actual canonical producer, not seven narrower diagnostics using the same
words. This is the same pattern this Kernel has used at every prior seam where a later phase
must prove something about an earlier phase's output rather than trust a restatement of it
(Phase 5's Authority-decision reproduction, Phase 6's Evidence-from-request derivation).

## 2. Four gaps, named rather than absorbed

`REFLOW_CONTRACT.md` §11 states each in full; this ADR records why each is a scope decision
rather than an interpretive fork, and therefore did not require escalation under Issue #39's
own rule that only a genuine two-way constitutional disagreement stops implementation.

```text
G9   required_observation_scope != null   NOT CLAIMED
G19  v0.1 mandatory invariant registry    NOT CLAIMED (checks Policy's declared set only)
G21  claim-series replay before promotion NOT CLAIMED (trusts the supplied binding's status)
G18  commit-time freshness recheck        NOT CLAIMED (evaluation-time only; RF6's obligation)
```

None of the four is ambiguous in the Policy text — each has an exact, unambiguous
specification. What makes each a legitimate scope decision rather than a fork is that each
is a **large, separable sub-system** whose omission is safely fail-closed rather than
silently permissive:

* **G9 non-null** fails the gate closed (`BLOCKED`) rather than being evaluated by a second,
  unbuilt scope-resolution mechanism. A caller cannot reach `SATISFIED` through it.
* **G19's registry auto-derivation** — parsing `KERNEL_INVARIANTS.md` §16's fenced block by
  exact Git blob provenance, deriving a versioned registry fingerprint, and re-deriving it
  again before every promotion — is a full vertical of comparable size to everything else in
  this Work Unit combined. What ships instead is a real, exact, non-vacuous check of the
  Policy's own declared `required_invariants`; the material gap is that an empty declared
  set reaches G19 `PASS` without the v0.1 mandatory union added. This is the one gap whose
  omission is not fail-closed against the Policy's literal text, and it is stated as such
  rather than downplayed.
* **G21's mandatory X-003 claim**, by contrast, *is* claimed in full: its identity is a
  closed-form Policy-text constant, not a derivation, so `MANDATORY_X003_CLAIM_REF` is always
  in the expected set regardless of what the Policy declares. Only the append-only event
  series replay immediately before promotion — proving a supplied binding is still current —
  is deferred; a caller cannot omit the mandatory claim, only misreport whether it is
  current.
* **G18's second freshness check** is deferred to RF6 (the Atomic State commit), which is
  where `CLOSURE_POLICY.md` §8 actually places it ("Atomic Reflowはcommit clockを...再検証
  する"). Evaluation-time freshness is checked in full; nothing about this gap weakens what
  G18 checks at the evaluation itself.

## 3. Every Closure Evaluation result commits a State transition, not only SATISFIED

`KERNEL_INVARIANTS.md` R-005 (`FAILED_AND_BLOCKED_RESULTS_REFLOWED`) is why
`reflow/route.py::reflow` runs the full commit path — mint the lifecycle event, mutate
bookkeeping, commit through `FileStateStore` — for `BLOCKED`/`RETAINED`/`NOT_SATISFIED`
outcomes exactly as it does for `SATISFIED`. The schema itself enforces the one detail this
depends on getting right: `difference_lifecycle_event.schema.json` requires a non-null
`reflow_transition_ref` only when `to_status == "CLOSED"`, so only the closing route needs
the commit to have already produced a real transaction identity before the event can be
minted; every other route mints and commits with `reflow_transition_ref: null`, which the
schema permits.

## 4. `open_differences` has exactly one writer

No producer anywhere in this Kernel writes to `semantic_state.open_differences` before this
Work Unit — not Difference, not Evidence, not Authority. `reflow/bookkeeping.py` is
therefore not competing with an existing owner; it is the field's first and only writer, and
the rule it applies is the simplest one consistent with the field's name: a Difference's
reference is a member exactly while its current lifecycle status is non-terminal. `CLOSED`
joins `difference/lifecycle.py`'s own `TERMINAL_STATUSES` for this one purpose (removal from
the list), even though `TERMINAL_STATUSES` itself correctly excludes `CLOSED` for lifecycle
legality — a closed Difference can still be reopened, but it has stopped needing attention,
which is what the list tracks.

## 5. Reopen re-references; it does not re-evaluate

`reflow/reopen.py::decide_reopen` does not call `evaluate_closure`. `REFLOW_CONTRACT.md` §8
("Reopen preserves old Closure Evaluation/Evidence") and `difference/lifecycle.py`'s own
`REQUIRES_CLOSURE_EVALUATION` — which deliberately excludes `REOPENED` — already say this:
Reopen's `closure_evaluation_ref` names the Evaluation being contradicted, not a fresh one.
Two of `CLOSURE_POLICY.md` §9's five reopen triggers are implemented,
`OBSERVATION_CONTRADICTION` and `MATERIAL_CONTRADICTION` (the schema this Work Unit's RF1
added); the other three are refused rather than silently accepted, each for a concrete
missing dependency named in `reopen.py`'s own module docstring (an Evidence-revocation
producer, and a Target Predicate re-evaluator Reflow does not own).

## 6. Verified rather than assumed

Every claim above is proven by a real injected violation, not a diagnostic that happens to
share its name with the property: a forged `difference_id` fails G1 through the schema-
validated output, not a unit test of the recomputation function in isolation; a stale
`before_project_state` is rejected by the real `FileStateStore`, not a mock; the mandatory
X-003 claim's absence fails G21 through the full `evaluate_closure` call, not a check of the
constant in isolation; and the crash-recovery proof (RF9) injects a `SimulatedCrash` at
every one of the Store's own seven commit stages and recovers through the Store's own
`recover()`, then replays the identical transaction and asserts the two committed States are
equal.
