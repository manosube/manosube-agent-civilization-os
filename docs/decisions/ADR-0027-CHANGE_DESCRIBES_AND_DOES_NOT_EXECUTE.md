# ADR-0027 — Change describes an authorized mutation, and does not perform one

**Status:** accepted
**Bounds:** KERNEL_CONSTITUTION 第24–26条, AUTHORITY_CONTRACT §7.2, APPROVAL_CONTRACT §2,
KERNEL_INVARIANTS A-002/A-003/B-002, ADR-0025 §4, ADR-0026 §1.
**Ratified interpretations:** Issue #31 comment `5519655293`.

## 0. What Phase 5 had to answer

Phase 4 ended with `AUTHORITY_CONTRACT.md` §7.2 holding an obligation it could not discharge:

```text
CHANGE EXECUTION MUST PRESENT
THE IDENTICAL OPERATION FINGERPRINT
THAT THE AUTHORITY DECISION BOUND
```

recorded as `CHANGE_ENGINE_IMPLEMENTED=false`. `AUTHORIZED` and `EXECUTED` were nameable but
not separable: nothing turned a decision into a record an executor could act on, and nothing
constrained what such a record could claim.

Five questions had no Human decision, and implementing any of them one way rather than another
would have fixed Change semantics by accident. They were put to Issue #31 and ratified before
implementation. This ADR records them and the reasoning that follows from each.

## 1. The five ratified interpretations

```text
CHANGE_INTENT_FINGERPRINT_REMAINS_BINDING=true
PREEXISTING_CHANGE_ID_REQUIRED=false
DERIVED_CHANGE_STATUS=AUTHORIZED
EXECUTION_RESULT_AT_DERIVATION=null
IDEMPOTENCY_KEY_DERIVED=true
STATE_BINDING_DERIVED_FROM_AUTHORITY=true
```

### 1.1 The approval's binding is not replaced

第22条 speaks of an approval binding a `change_id`. `APPROVAL_CONTRACT.md` §2 already resolved
this for Phase 4 by binding `change_intent_fingerprint(action, scope)` instead, because there
was no Change record to point at. Phase 5 creates one — and the tempting move is to now bind
approvals to `change_id`.

That move introduces a second binding for one question. Two bindings can disagree, and the
first time they do, one approval covers an operation the human did not approve. The derived
Change carries the *same* action and the *same* scope the decision bound, so the approval's
existing fingerprint still holds over it, and there is nothing to re-bind. The continuity is
proved by test rather than asserted.

### 1.2 Identity is derived, never supplied

A caller-supplied `change_id` is a label. A label that is believed rather than recomputed lets
one address name two different changes — the same discipline Phase 4 established as
`RECORD_IDENTITY_RECOMPUTED=true`. The Change request therefore has no entry for `change_id`,
and, the key set being closed, supplying one is refused rather than ignored.

The same argument covers `idempotency_key`. A caller who chooses the key can give two distinct
changes one key and have the second silently treated as a duplicate of the first. 第26条's
`DUPLICATE_CHANGE_IDEMPOTENT` is a property of what a change *is*, not of what a caller says
it is.

### 1.3 One status, out of seven

第25条 defines seven. The engine emits one.

```text
RUNNING / EXECUTED / FAILED → only an executor can report these
REJECTED / STALE            → refusals, raised rather than recorded
PROPOSED                    → pre-Authority, on the input side
```

Emitting a `REJECTED` or `STALE` Change record would be emitting a Change record for a
mutation that must not occur — a record whose existence is itself the hazard, because
downstream anything holding a Change record holds something that looks executable. Refusals
leave as exceptions and leave nothing behind.

Definition and emission are different claims. `SEVEN_STATUS_VALUES_EMITTED=false` is stated
explicitly so the first is not read as the second.

### 1.4 The vacuous guard that was removed

The schema first carried `if status == AUTHORIZED then execution_result is null`. With `status`
closed to a one-value enum and `execution_result` typed `null` directly, no input can reach
that conditional's false branch: it was a predicate that looks like a check and checks
nothing. Phase 4 had to declare "a guard constant no assertion reads" as an explicit non-claim;
this is the same shape, caught before it shipped.

Both fields are pinned directly instead. The conditional becomes necessary in the phase that
opens `status` to seven values — and it should be written *then*, by someone who needs it.

### 1.5 The State binding is taken, not supplied

`before_state_fingerprint` and `expected_state_revision` come out of the bound decision's
`evaluated_state_*`. Supplying them alongside the decision would create a pair that can
disagree, and a third authority would then be needed to say which is right. Taking them means
the disagreement cannot be expressed.

What remains checkable is that the Difference was observed against that same State, which is
exactly what 第26条's `STALE_CHANGE_BLOCKED` asks. The diagnostic names *which* binding failed:
a fingerprint mismatch at equal revisions must not read "revision 2 vs 2", because a caller
told only "no" cannot tell a human what to re-observe.

## 2. The error boundary, and the defect that proved it was needed

`CHANGE_CONTRACT.md` §9 claims every refusal leaves as a `ChangeError`. The first
implementation caught `DifferenceError` and `CanonicalizationError` and did not catch
`AuthorityError` — and `AuthorityError` is exactly what the reused admission path raises.

The reuse is deliberate and correct. `admit_difference` and `require_scope` are Authority's
owners; a second implementation of either would be a second answer to what a Difference or a
scope is, and the first time the two disagree the disagreement is silent. **Reusing the owner
is right; letting its vocabulary out of this boundary is not.** A caller of Change would
otherwise have to catch an *Authority* error to learn its own request was malformed.

Two integration tests failed on this before any reviewer saw it. The totality suite now
carries a standing control asserting that no delegated owner's error is a subclass of
`ChangeError`, so a regression fails rather than being scored as a canonical refusal.

## 3. What this phase does not claim

```text
CHANGE_EXECUTION_IMPLEMENTED=false
STATE_COMMIT_IMPLEMENTED=false
ATOMIC_STATE_COMMIT=false
PARTIAL_WRITE_NOT_CANONICAL=false
CRASH_RECOVERY_PROVEN=false
CHANGE_LIFECYCLE_TRANSITIONS_IMPLEMENTED=false
SEVEN_STATUS_VALUES_EMITTED=false
EVIDENCE_LINKED_FROM_CHANGE=false
DIFFERENCE_CLOSURE_IMPLEMENTED=false
ONE_FULL_NATURAL_CYCLE_PASS=false
```

Of 第26条's five Kernel requirements, Phase 5 satisfies the **derivation side** of two
(`STALE_CHANGE_BLOCKED`, `DUPLICATE_CHANGE_IDEMPOTENT`). The other three are an executor's,
and there is no executor. Each `false` records a missing owner, not a defect.

### 3.1 One gap found on Phase 4's surface, and deliberately not closed here

`authority.schema.json#/$defs/scope` accepts a path expression such as `src/**`; the
resolved-member check in `authority.scope` refuses it, and `derive_change` runs that check, so
no Change can carry one. The gap is schema-level, on Phase 4's surface, and pre-dates this
work.

It is not closed here. Widening a single-vertical PR into a predecessor's schema is how a
bounded change stops being reviewable, and the behaviour is already correct through the code
path — which this phase proves by test rather than assumes. The gap is reported on Issue #31
for its owning phase.

```text
AUTHORITY_SCOPE_SCHEMA_REJECTS_PATH_EXPRESSIONS=false
AUTHORITY_SCOPE_CODE_REJECTS_PATH_EXPRESSIONS=true
```

### 3.2 A second decision found, reported rather than taken

Three retained Difference tests failed on this work, all on one assertion: that
`01_SCHEMA/change/` is empty. Each was written as a *measurement* of the non-claim "no
canonical schema governs carried Change records" — and directory emptiness was the proxy they
measured it by.

Phase 5 falsifies the proxy. It does not falsify the claim. `change.schema.json` governs a
**derived** Change: thirteen fields, a `CHANGE-` content address, an Authority decision behind
it. The `changes` section of a Difference predecessor context carries **historical** Change
records of a different shape entirely — `{"change_id": "CHG-0001", "subject_ref": {...}}` —
which are gated by identity and reference closure and by nothing else.

Whether carried predecessor context should now be held to the canonical Change schema is a
real question, and it is a **Difference** semantic decision, not a Change one: answering it
"yes" would make every historical Change record uncarryable. It has a Human owner and is
reported on Issue #31 rather than taken here.

What this phase changed is only the three assertions, so that each measures the claim it
depends on — `RECORD_TYPES[...].schema is None` — instead of a proxy that Phase 5 made stale.
No behaviour changed, and `RECORD_TYPES["change"]` stays unschematized.

```text
CARRIED_CHANGE_CONTEXT_IS_SCHEMA_BACKED=false
DERIVED_CHANGE_IS_SCHEMA_BACKED=true
```

The general lesson is the session's recurring one in a new place: **a claim measured by a
proxy is a claim that drifts when the proxy does.** These three tests failed loudly rather
than silently, which is what made the distinction visible at all.

## 3.3 The P1: self-consistency read as provenance

Independent review found one blocker in the first implementation, and it was the important
kind — not a missing check, but a **claim in the contract that the code never made true**.

`CHANGE_CONTRACT.md` §8 listed four questions every supplied record crosses, the last being
"produced by the evaluator rather than asserted". The engine implemented the first three. For
the fourth it recomputed the decision's content address and treated agreement as evidence.

It is not evidence. `decision_id` and `decision_semantic_fingerprint` are **public pure
functions**, so the recomputation a caller must satisfy is a recomputation a caller can
perform. Reproduced at `035bdb7`: a caller that never invoked `evaluate_authority` assembled
an `AUTONOMOUS` decision for `MERGE` — a Human-only action — citing a rule that exists nowhere
in the repository, re-hashed it into perfect internal agreement, and obtained an `AUTHORIZED`
Change.

```text
INTERNAL CONSISTENCY = the record agrees with itself
PROVENANCE           = who wrote it
```

Hashes measure the first. Nothing about them measures the second, and the whole defect is one
sentence long: **self-consistency was read as provenance.**

### The repair, and why it is a reduction rather than a check

Adding a check would have been the wrong shape — a check is a thing that can be forgotten, and
this one *was* forgotten while the contract asserted it. The repair removes the possibility
instead.

The Change request now carries the **real Authority inputs** and the caller's **claim** about
what they yield. `derive_change` runs `evaluate_authority` on those inputs and requires the
claim to equal the result, whole-record, not by address alone — an address is a digest over a
projection, and a projection is by construction not the record.

Three consequences follow, and each is stronger than the check it replaced:

1. **The five exact-binding checks disappear.** Project, Difference, State, action and scope
   are read from the reproduced decision, and the request has no entry for supplying any of
   them beside it. Two values cannot disagree when there is only one. The disagreement is not
   refused; it is inexpressible.

2. **Staleness moves to its owner.** `evaluate_authority` already refuses a Difference
   observed against a State it did not evaluate, so Change stopped duplicating that. It keeps
   the *word*: 第26条 requires a stale Change to be blocked, and a caller told only "refused"
   cannot tell a human what to re-observe, so `StaleAuthorityInputError` is renamed
   `StaleChangeError` at the boundary and nothing else about it is restated.

3. **Order became load-bearing.** Evaluation runs *before* the claim is admitted. The first
   attempt admitted the claim first, which meant the shape of a caller-supplied value decided
   whether the canonical evaluation happened at all — the same defect as trusting the claim,
   wearing a different hat. Caught by the regression tests, not by review.

`ChangeBoundaryViolationError` had no remaining raiser and was replaced by
`AuthorityProvenanceError`, whose name states the property it defends.

### Is calling the evaluator a second Authority?

No, and the distinction is worth stating because it is the one thing that could make this
repair wrong. A second Authority is a module that *decides* — its own rule matching, its own
prohibition evaluation, its own approval resolution, its own reversibility floor. None of
those exists in `change/`, and a contract test reads the engine's source to keep it that way.
Calling the single owner is the opposite of duplicating it.

```text
SINGLE_AUTHORITY_OWNER_PRESERVED=true
CHANGE_REDECIDES_AUTHORITY=false
```

### What reproduction does not close

It does not close a caller forging the **inputs**. A decision citing a nonexistent rule is now
refused, but a caller who puts a fabricated rule into the supplied rules array gets a decision
the evaluator legitimately produced from it.

```text
NONEXISTENT_RULE_REFERENCE_REFUSED=true
SUPPLIED_RULE_PROVENANCE_RESOLVED=false
SUPPLIED_APPROVAL_PROVENANCE_RESOLVED=false
```

Rule and approval provenance belong to Authority and to the Binding owner, and v0.1 has no
registry to resolve them against. Change does not pretend to resolve what it cannot, and the
boundary is stated rather than left for the next reviewer to discover — which is the same
discipline whose absence produced this P1 in the first place.

### The general lesson

The recurring shape of this session, in its sharpest form yet. Rounds 3–10 were *a rule
asserted in one place and enforced in another*. This was worse: **a rule asserted in one place
and enforced nowhere**, with a computation standing in the enforcement's place and resembling
it closely enough that I wrote the sentence claiming it and did not notice.

The reviewer's finding is the reason the claim and the code are now the same thing.

## 4. Consequences

Change is a pure function from records to a record. It reads no clock, no filesystem, no
network, no environment, no GitHub and no conversation — and the evidence for that is the
absence of any API through which it could, not a sentence in a docstring.

`AUTHORITY_CONTRACT.md` §7.2's obligation is discharged structurally rather than by
comparison: the operation a Change presents **is** the operation the decision bound, the same
object read from the reproduced decision, because there is no other place it could come from.

```text
CAN_DO ≠ MAY_DO
AUTHORITY_REQUIRED ≠ AUTHORITY_GRANTED
AUTHORIZED ≠ EXECUTED
EXECUTED ≠ CLOSED
```
