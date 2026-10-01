# ADR-0029 — Eligible provider membership is not execution authority

**Status:** accepted
**Bounds:** `development_binding.policy`, `development_binding.executor_selection`,
`03_BINDING/CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md` §10, `03_BINDING/COPILOT_PARTICIPATION.md`.
**Ratified decision:** `HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0003` (Issue #102),
superseding `HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0002`.

## 0. What was requested

SHUKOU asked for a Kernel-compatible, interchangeable implementation executor: this
repository's Development Binding should admit GitHub Copilot alongside Claude Code, without
weakening anything ADR-0028 established. The Structural Advisor prepared the design
(`03_BINDING/COPILOT_PARTICIPATION.md`, PR #103); this ADR records the machine-policy
revision that implements it.

## 1. The capability does not change; the set of eligible names does

ADR-0028 bound the implementation executor capability to one name, `CLAUDE_CODE`, because an
unrecorded selection is an open slot. Admitting a second name the same way -- unrecorded, or
recorded as a bare role entry with no further gate -- would reopen exactly that slot one level
up: "eligible" would quietly become "selected" the moment two names could fill one capability
and nothing distinguished them.

```text
CAPABILITY DEFINED   ≠ IMPLEMENTER SELECTED        (ADR-0028)
IMPLEMENTER ELIGIBLE ≠ IMPLEMENTER SELECTED         (this decision)
```

So `GITHUB_COPILOT` is admitted into `development_binding.policy.EXECUTOR_PROVIDERS` with the
*identical* `may`/`must_not` sets and handoff transitions `CLAUDE_CODE` already had --
duplicated from one named constant, not independently authored, so the two cannot drift to
different permissions by someone editing one literal block and forgetting the other. The
capability is unchanged. Only the set of names eligible to hold it grows by one.

## 2. Eligibility is necessary, never sufficient

Being named in the ratified role map answers one question: is this name one the Binding
recognises at all. It does not answer a narrower, equally necessary question: is this name
the *selected* executor for *this* work unit, at *this* exact scope, right now.

`development_binding.executor_selection` answers the second question, mechanically, the same
way `development_binding.adoption_record` already answers the equivalent question for a
Human-adopted finding: a structured record, checked offline, bound field-by-field to a
SHUKOU-granted, read-back-verified comment, and refused whenever any one of its fields
disagrees with the current, exact scope it is being invoked for.

```text
ELIGIBLE  = named in policy.EXECUTOR_PROVIDERS
SELECTED  = ELIGIBLE, and bound by an ADMITTED executor-selection record to this exact
            repository, branch, base/head SHA and work unit
ELIGIBLE_PROVIDER_MEMBERSHIP_IS_NOT_EXECUTION_AUTHORITY=true
```

Six concrete failures this record format refuses, each a counterexample the design handoff
named explicitly: a missing record (refused by construction -- there is nothing to evaluate);
a forged or unposted grant (`COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT`, the same check
`adoption_record` already makes); a stale grant whose branch has since moved
(`HEAD_SHA_STALE`); an unknown provider name (`UNKNOWN_EXECUTOR_PROVIDER`); a scope mismatch
on repository, branch or base SHA (`*_SCOPE_MISMATCH`); a grant replayed against a different
work unit than the one it was issued for (`CROSS_WORK_UNIT_REPLAY`); and two providers
simultaneously claiming to be the active executor for one work unit
(`DUPLICATE_ACTIVE_EXECUTOR_FOR_WORK_UNIT`).

## 3. Backward compatibility is a property of the default, not an exception

`EXECUTOR_PROVIDER_DEFAULT = CLAUDE_CODE`. No executor-selection record is required for
Claude Code to keep operating -- every historical record, every existing transition, and
every future Claude Code work unit continues exactly as Decision 0002 left it. The gate in
§2 exists only for the *other* eligible name: before Copilot's output is treated as this
repository's authorized implementation for a given work unit, a record naming it must answer
`EXECUTOR_SELECTION_ADMITTED`.

This is why Decision 0003 is additive rather than a re-selection: it does not ask anyone to
re-prove that Claude Code is still the executor. It only adds a second name that must prove
itself, per work unit, before it is treated as one.

## 4. What stays exactly as ADR-0028 and Decision 0002 left it

Every boundary either ADR established is unchanged, and `GITHUB_COPILOT` inherits each one by
sharing `CLAUDE_CODE`'s own permission sets rather than by a separate assertion:

```text
STRUCTURAL_REVIEW                 still CHATGPT-only
MERGE_READINESS_RECOMMENDATION    still CHATGPT-only
FINAL_ACCEPTANCE_DECISION         still SHUKOU-only
MERGE_OPERATION                   still SHUKOU-only
ADOPT_EXTERNAL_FINDING            still SHUKOU-only
REQUEST_AUTOMATED_EXTERNAL_REVIEW still prohibited for every non-Human role
executor_terminal_state           still READY_FOR_STRUCTURAL_REVIEW, for every eligible provider
```

`prohibited_automated_review_triggers` is unchanged and still includes the Copilot
review-request trigger `.github/copilot-instructions.md` already warned against. A Copilot
self-acceptance, self-merge, or automated-review-request attempt is refused by `evaluate()`
through the same `ROLE_DRIFT`/`*_DRIFT` reason codes a Claude Code attempt would be -- proven,
not merely asserted, in `test_executor_selection_enforcement.py` and the extended
`test_development_binding_conformance.py`.

## 5. What this does not claim

```text
COPILOT_RUNTIME_WORK_UNIT_PROVEN=false
COPILOT_REVIEW_AUTO_ENABLED=false
ISSUE_102_CLOSE_ALLOWED=false
RUNTIME_ENFORCEMENT_IMPLEMENTED=false
```

This decision admits Copilot into the policy's eligible set and builds the selection gate a
real trial must pass. It does not itself run that trial. A concrete, reversible, bounded
Copilot work unit is prepared as part of this work unit's own evidence but deliberately not
executed under this code handoff, per its explicit scope. Observing one actual authorized
Copilot work unit, its independent structural review, and SHUKOU's disposition are the
remaining Difference Issue #102 stays open for.

## 6. Consequences

```text
CONSTRUCTION_BOUND_TO_TWO_NAMES_NOW
SELECTION_STILL_BOUND_TO_ONE_RECORD_PER_WORK_UNIT
ARTIFACT_NEUTRAL   (unchanged -- see ADR-0028 §7)
```
