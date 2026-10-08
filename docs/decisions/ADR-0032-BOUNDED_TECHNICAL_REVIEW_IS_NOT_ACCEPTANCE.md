# ADR-0032 — A bounded reviewer is still not an acceptor

**Status:** accepted
**Bounds:** `03_BINDING/CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md`, `03_BINDING/
DEVELOPMENT_BINDING_POLICY.json`, `development_binding.evaluation`, `KERNEL_VERTICAL_
WORK_UNIT_DELIVERY.md` §6.
**Ratified decision:** `HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0004` (Issue
#109), superseding `HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0003`.
**Supersedes no prior finding.** ADR-0028 (Issue #34) remains the record of what actually
went wrong the first time an automated reviewer reached this repository's critical path; this
ADR records why reopening a narrow, mechanically bounded route for Codex does not reopen that
same failure.

## 0. The question this decision had to answer honestly

ADR-0028 is unambiguous: an unselected capability is an open slot, and an automated reviewer
that reaches a critical path without an explicit, bounded admission route becomes
self-sustaining. `03_BINDING/DEVELOPMENT_BINDING_POLICY.json` has accordingly kept
`automated_review_trigger_allowed=false` since Decision 0002, and `evaluation.evaluate`
enforces it as a real refusal, not a described intention.

Issue #109 asked a narrower question than "should Codex review this repository" — it asked
whether a *specific*, *mechanically bounded*, *non-default-active* route could exist for one
capability (`BOUNDED_TECHNICAL_REVIEWER`) without reopening the exact failure mode ADR-0028
already named. The honest answer required building the admission chain first and then asking
whether it actually closes the gap, rather than asserting that a new boolean flag or a new
role name would.

## 1. Eligibility is still not authority, extended to a disjoint role

Decision 0003 (ADR unnamed, Issue #102) already drew this line once, for `GITHUB_COPILOT`:
being named in the ratified role map is eligibility, never the authority to act for one
specific work unit. `development_binding.executor_selection` is the separate, narrower gate
that authority requires.

Decision 0004 draws the identical line for a role that is not even in the same capability
family:

```text
ELIGIBLE  = CODEX names the bounded technical reviewer capability in the ratified policy
ADMITTED  = ELIGIBLE, and this exact request is bound by review_selection to its exact
            scope, freshness, environment and provenance
```

`CODEX` is never added to `EXECUTOR_PROVIDERS`. It holds one capability
(`BOUNDED_TECHNICAL_REVIEWER`) and one action (`BOUNDED_TECHNICAL_REVIEW`), and its own
`must_not` set is the union of every implementation-executor action and every structural/
Human-authority action: `CODE_AUTHORSHIP`, `IMPLEMENTATION`, `TEST_EXECUTION`,
`EXECUTOR_SELF_REVIEW`, `PR_PREPARATION`, `STRUCTURAL_AUTHORITY`, `STRUCTURAL_REVIEW`,
`MERGE_READINESS_RECOMMENDATION`, `FINAL_ACCEPTANCE_DECISION`, `MERGE_OPERATION`,
`ADOPT_EXTERNAL_FINDING`, `REQUEST_AUTOMATED_EXTERNAL_REVIEW`. A reviewer that could also
implement, self-review, or adopt its own finding would not be a bounded reviewer; it would be
an unbounded one wearing a narrower name.

`BOUNDED_TECHNICAL_REVIEW` is deliberately **not** the same action
`automated_review_trigger_allowed` gates. That boolean, and the `prohibited_automated_review_
triggers` list it guards, still prohibit every *unconditional* native/bot trigger exactly as
Decision 0002 left them — Decision 0004 neither widens that boolean nor removes an entry from
that list. The one new route is a second, narrower, independently-admitted gate
(`development_binding.review_selection`), structurally identical to `executor_selection`'s own
non-default-provider gate, layered *beside* the unconditional-trigger prohibition rather than
through it.

## 2. Three owners, one admission route, no second canonical state

`review_selection` answers one offline question: is this exact Bounded Review Grant internally
consistent, unexpired, unrevoked, and scoped to the exact repository/PR/base/head/requirement/
environment it claims. It holds no state across calls and makes no network call or process
launch, the identical limit `executor_selection` already states for itself.

`review_control` is the one stateful owner: a durable, file-locked ledger recording every
claim this repository has ever admitted, so "one launch per identity, forever" and "one
concurrent review per repository" are real properties of a persisted ledger, not promises a
caller could forget between invocations. It is explicitly *not* a second canonical State
owner — the handoff's own words, preserved here: "it remains execution-control metadata, not
a second canonical State owner." Nothing in `review_control` touches the Store, Boot,
Authority, or Evidence owners this repository already has.

`review_adapter` is the one place any of this decision's own code may launch a process, build
a restricted environment, or send a signal. Everything upstream of it is pure or
ledger-bound; everything downstream of admission is this one, explicitly external-effect
module.

`scripts/bounded_technical_review.py` composes these three and introduces no fourth,
competing admission route. Its own `dispatch` subcommand validates a grant, attempts a claim,
and evaluates the activation gate — and stops there, in this delivery, every time.

## 3. Why this delivery still launches nothing

`03_BINDING/DEVELOPMENT_BINDING_POLICY.json`'s own `bounded_review_activation_default` is
`false`, pinned by `development_binding.policy.load_policy` the identical way every other
ratified boolean in this file is pinned — not merely described as `false` in prose while a
caller could flip it in practice.

`review_control.evaluate_activation_gate` requires eight affirmatively-confirmed fields
(authentication, exact CLI/model match, confirmed allowance, confirmed-disabled auto-recharge,
a resolved native-GitHub-dedup disposition, an admitted live grant, and the activation switch
itself) before it will ever answer `ACTIVATION_GATE_ACTIVATED`; an absent, unknown, or merely
unverified field is a refusal, never a default pass. `scripts/bounded_technical_review.py`
hardcodes `activation_enabled=False` on every evidence mapping it assembles — there is no
flag, environment variable, or file this script reads that can set it to `True`. Reaching a
real external launch requires code this delivery does not contain.

This is why Issue #109's own handoff could state, truthfully, before a single line of this
decision's implementation existed: `REAL_CODEX_MODEL_REQUEST_ALLOWED=false`. This ADR records
that the implementation kept that promise rather than merely repeating it.

## 4. What remains open, honestly

```text
REAL_CODEX_MODEL_REQUEST_ALLOWED=false
LIVE_REVIEW_CONTROLLER_START_ALLOWED=false
AUTOMATED_EXTERNAL_REVIEW_REQUEST_PERFORMED=false
SHUKOU_ACCOUNT_AUTO_RECHARGE_DISPOSITION_VERIFIED=false
NATIVE_GITHUB_AUTOMATIC_REVIEW_SETTING_VERIFIED=false
CODEX_CLI_FLAG_SET_INDEPENDENTLY_VALIDATED_AGAINST_REAL_CLI=false
BOUNDED_TECHNICAL_REVIEW_IS_NOT_A_TRIGGER_EXEMPTION=true
ELIGIBLE_PROVIDER_MEMBERSHIP_IS_NOT_EXECUTION_AUTHORITY=true
```

This decision implements and tests the control plane. It does not implement a live
connection, does not mint a live grant, and does not claim any of the unverified real-world
preconditions its own activation gate would require are satisfied. A later, separately
authorized work unit answers whether a genuine Codex launch, under a genuine grant, actually
behaves the way this delivery's fake-executable proofs predict — the identical separation
Decision 0003 already drew between admitting Copilot as eligible and proving one real Copilot
work unit end to end.
