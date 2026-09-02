# ADR-0026 — One Authority evaluator, and no channel for prose

**Status:** accepted
**Bounds:** SECURITY.md §3–§5, KERNEL_CONSTITUTION 第4条/第21–23条, KERNEL_INVARIANTS A-002/A-003/B-002, ADR-0025 §4.

## 0. What Phase 4 had to answer

Phase 3 left `authority_required` on every Difference — a list of references the Difference
Contract explicitly calls *a requirement for later evaluation, not a permission* (§9). Nothing
answered it. `CAN_DO` and `MAY_DO` were mechanically indistinguishable, which is the precise
condition under which "the tool could, so the agent did" becomes a system property.

The inventory at `d7bc607c` found no partial answer to reduce: `00_KERNEL/05_AUTHORITY/` and
`01_SCHEMA/authority/` held only `.gitkeep`, no `authority` package existed, and every
`authority` occurrence in `src/` was a reference or a requirement. So this is the rare case of
building rather than reducing — and the risk shifts accordingly, from duplication to **making
up semantics that the contracts already fix**.

## 1. Three values, and why not four

```text
AUTONOMOUS
HUMAN_APPROVAL_REQUIRED
PROHIBITED
```

The pressure to add a fourth — "allowed with warning", "allowed if careful" — is the pressure
to record an unresolved question as a resolved one. Every input that cannot be decided lands
on `HUMAN_APPROVAL_REQUIRED`, never on `AUTONOMOUS`. **Silence is not permission**, and the
absence of a rule is silence: a request no rule governs is approval-required by construction,
not by a default that could be configured away.

Two floors cannot be lowered by any rule: Human-only action kinds, and irreversibility. A rule
declaring `AUTONOMOUS` over `MERGE` does not lower `MERGE`; it is simply outranked.

## 2. Prohibition is evaluated before rules, and that ordering is the substance

A prohibition is a **found refusal**. A missing rule is an **absent permission**. Collapsing
them loses the difference between "ask a human" and "do not ask".

Evaluating prohibitions first is not tidiness. If rules resolved first, a successful lookup
becomes a path that never reaches the refusal — the same shape as ADR-0022's D1/D3, where a
value was read before the gate that establishes it could be. Ordering is the fix, again.

The two scope operators are deliberately asymmetric:

```text
PERMISSION   requested ⊆ granted        narrow
PROHIBITION  requested ∩ forbidden ≠ ∅  wide
```

A request touching one forbidden path is refused whole. It is not trimmed to its permitted
remainder, because "execute the allowed part" is how a boundary becomes negotiable.

## 3. The approval binds a change intent, because Change does not exist yet

`KERNEL_CONSTITUTION` 第22条 and `SECURITY.md` §4 bind an approval to `change_id`. Phase 4
must not implement Change, so no such identity exists to bind. Issue #28 §3 words the same
requirement as *"exact objective/difference/change intent"*, and that is what is implemented:

```text
REQUIRED  change_intent_fingerprint   a digest over exactly this action and this scope
OPTIONAL  change_ref                  filled only when a Change record later exists
```

This keeps what `change_id` *meant* — which change was approved — without inventing a Change
identity to hold it. It does not loosen anything: the fingerprint moves when the action or the
scope moves, and an approval whose fingerprint has moved is not an approval.

Recorded as an interpretation rather than made silently. If Human Authority reads 第22条 as
requiring a literal `change_id`, this is the choice to revisit.

## 4. The strongest form of "untrusted input is not Authority" is an absent parameter

`SECURITY.md` §3 lists what may never escalate authority: prompts, READMEs, Issues, Pull
Requests, review comments, CI results, credentials, tool discovery, session memory. The
obvious implementation is a filter. This is not that.

The evaluator's request key set is **closed**, and there is no key through which prose could
arrive. Supplying one is **refused**, not ignored:

```text
authority request carries unknown keys: ['pull_request_body']
```

That difference matters. An ignored key is still a key a caller can believe was weighed; the
absence of an effect is indistinguishable from a subtle one. A refusal says plainly that this
evaluator has no input of that kind.

The closed key set was not there when the first integration test ran. `test_untrusted_text_
has_no_route_into_an_authority_decision` failed, because extra keys were being silently
dropped — a real route, found by writing the test that assumes there is none.

## 5. Delegation, and where a boundary must not delegate

"Can this be read" already had one owner (ADR-0025). Authority asks it rather than answering
it again; the dependency runs with the Kernel order, DIFFERENCE before AUTHORITY, and a
contract test holds the owner objects by identity.

But the input-totality generators then found the cost of that. Measured over the 1624
generated cases:

```text
decided                      231
AuthorityError              1022
DifferenceError escapes      371   <- a Difference error crossing the Authority boundary
other raw exceptions           0
```

A caller of Authority was having to catch a *Difference* error to learn that its own request
was malformed. The decision is rightly delegated; the boundary's error vocabulary is not.
`evaluate_authority` translates at the seam, and the 371 became `AuthorityError`.

Both halves matter. Re-implementing readability would have been a second owner; leaking the
first owner's vocabulary would have been a leaky boundary. Delegating the decision and owning
the vocabulary is neither.

## 5.1 Seven findings were one boundary

The exact-head review of `b0bc7ce` returned seven findings — five P1. They looked like seven
bugs across five files. They were one missing stage.

| # | Reported as | Actually |
| --- | --- | --- |
| 1 | payload absent from the approval fingerprint | the binding did not name the operation |
| 2 | forged / Agent-declared rule grants `AUTONOMOUS` | no admission for a supplied rule |
| 3 | non-canonical Human approval usable | no admission for a supplied approval |
| 4 | globs pass as resolved scope | no admission for a supplied scope member |
| 5 | timestamps compared as strings | no admission for a supplied instant |
| 6 | provenance absent from decision identity | the address ignored part of its record |
| 7 | equivalent approvals selected by input order | resolution was not deterministic |

1–5 are the same absence: **a record supplied by a caller reached a decision without being
established as canonical.** Each site had a hand-written key check that covered a little less
than the schema it stood in for, and each covered a *different* little less — which is why
one gate looked like five independent oversights.

The fix is one admission path (`authority/conformance.py`) asking four questions of every
supplied record: readable, schema-valid at a supported version with no unknown property,
**content address recomputed**, and declared by a Human Authority. The third is the one a
per-record gate always omits, and the only one that sees forgery: every other check passes on
a record whose fields were edited after it was addressed.

6 and 7 are the other half of the same sentence. Once inputs are canonical, the *output* must
be too: the decision address now includes which rule permitted, which approval was used and
which prohibitions matched, and equivalent approvals are selected by identity rather than by
arrival. Without both, two different payloads shared one identity — the same-identity /
different-payload collision the Kernel forbids everywhere else.

Fixing only the reported fingerprint would have left four of the five P1s open behind a
correction that read as complete.

## 5.2 What the operation payload is, and is not

`action.operation` is an **opaque canonical payload**. Authority binds it into the approval
identity and never interprets or executes it; its digest is derived from canonical bytes
rather than taken from the caller, so a declared digest is a label that must match, not a
binding that is trusted.

This is not a Change semantics change. `KERNEL_CONSTITUTION` 第22条 already binds an approval
to an `approved_action_fingerprint`; an action fingerprint that cannot distinguish two
operations is simply not fingerprinting the action. What Phase 4 records, and does not
implement, is the obligation that follows: **execution must present the identical operation
fingerprint the decision bound.**

## 5.3 One non-claim, stated rather than approximated

Deciding whether an enumerated path resolves outside a Boundary requires reading a
filesystem, and a deterministic evaluator does not read one. So Authority refuses every path
*expression* — glob, traversal, absolute root, trailing separator — and compares only
enumerated members. `AUTHORITY_RESOLVES_SYMLINKS=false`, and refusing expressions is what
keeps that gap bounded instead of open.

## 6. What is measured

```text
CANONICAL_AUTHORITY_OWNER_COUNT=1     one evaluator; a source scan forbids the three
                                      decision values anywhere outside the package
PARALLEL_AUTHORITY_COUNT=0
ONE_CANONICAL_INPUT_ADMISSION_PATH=1  rules, approvals and prohibitions cross the same gate
HUMAN_ONLY_ACTION_KINDS               13, held to AUTHORITY_LEVELS.md §4 in both directions
AUTHORITY_SCHEMA_COUNT=4              22 committed fixtures, 18 of them adversarial, 0 escapes
RAW_EXCEPTION_COUNT=0                 over a location sweep plus declaration-driven generation
COMPLETE_OPERATION_BOUND=true         two payloads under one action/scope cannot share an
                                      approval or an intent identity
RECORD_IDENTITY_RECOMPUTED=true       a record edited after addressing is refused
PATH_EXPRESSION_REJECTED=true         on the request, the rule and the prohibition alike
CHRONOLOGICAL_VALIDITY_COMPARISON=true
DECISION_IDENTITY_INCLUDES_PROVENANCE=true
APPROVAL_SELECTION_CANONICAL=true     permutation invariant
```

The declaration generator exists because ADR-0025 §1 established that a fixture-path sweep is
blind to what a fixture omits. Authority can generate from its declarations where the
Difference request could not, for one reason: **every key set here is closed.** An unknown key
is refused, so the declared set is the whole set, and generating from it is generating from
the grammar rather than from an example of it.

## 7. What is not claimed

```text
AUTHORITY_CONTRACTS_DEFINED=true
AUTHORITY_SCHEMAS_IMPLEMENTED=true
AUTHORITY_ENGINE_IMPLEMENTED=true
DIFFERENCE_TO_AUTHORITY_INTEGRATION=true

CHANGE_ENGINE_IMPLEMENTED=false     nothing here executes anything
EVIDENCE_ENGINE_IMPLEMENTED=false
REFLOW_ENGINE_IMPLEMENTED=false
ONE_FULL_NATURAL_CYCLE_PASS=false
KERNEL_V0_1_COMPLETE=false
```

`AUTONOMOUS` means an action may proceed. It does not mean it will succeed, that a Difference
closes, or that anything is finished. Authority decides permission and stops — and the
evidence for that claim is not an assertion but the absence of any API through which this
package could do more.

Two limits worth stating rather than implying. The eight worlds are worlds, not a proof of
totality over rule combinations; and the action-kind vocabulary is an open pattern, so a
misspelled kind is not a permitted kind — it simply matches no rule and lands on
approval-required, which is fail-closed but is not the same as being validated.
