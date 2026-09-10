# Controlled Autonomous Change Executor Contract (Phase 18, Issue #73)

```text
DOC_TYPE=CHANGE_EXECUTOR_CONTRACT
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=CHANGE-EXECUTOR-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_EXECUTION_ADAPTER
CHANGE_EXECUTOR_OWNER_COUNT=1
PUBLIC_CHANGE_EXECUTOR_ENTRY_POINT_COUNT=2
SIGNED_KILL_SWITCH_CHAIN=true
KILL_SWITCH_CHECKPOINTS_PER_REQUEST=2
PREFLIGHT_BEFORE_EFFECT=true
IDEMPOTENCY_SLOT_MECHANISM=true
STRUCTURAL_REVIEW_ROUNDS_APPLIED=0
TEST_SUITE_PRESENT_WHEN_WRITTEN=false
TEST_SUITE_PRESENT_AT_DELIVERY=true
```

## 1. Position

This layer lets an already-authorized canonical Change be autonomously *executed*, only inside
an explicit, closed, low-risk Execution Boundary, producing one immutable
`change_execution_receipt` -- and then stops. It is **not** a ninth Kernel element (the Kernel is
fixed at eight: `KERNEL_ELEMENT_COUNT=8`, `ONE_KERNEL_ELEMENT_PER_PACKAGE=true`) -- an adapter
layer, exactly as Boot, CLI, Agent Runtime, Independent Verification, Projection, Runtime, and
URL Boot already are. It creates no Authority, updates no canonical State's semantic content
beyond its own three new record kinds (`execution_intent`, `execution_attempt`,
`change_execution_receipt`) and its own kill switch chain (`change_executor_kill_switch`), proves
no causality, establishes no sufficient Evidence, closes no Difference, and declares no
completion -- it hands off to the existing Evidence/Observation/Reflow owners
(`evidence_handoff.py`) rather than becoming a new owner of any of them.

```text
CHANGE_EXECUTOR_OWNER_COUNT=1
PUBLIC_CHANGE_EXECUTOR_ENTRY_POINT_COUNT=2
```

**On the state of proof at the time this document was first drafted, and since.** No test suite
existed anywhere under `tests/unit/change_executor/`, `tests/contract/change_executor/`, or
`tests/integration/change_executor/` at the moment this contract was first authored -- confirmed
absent by direct search immediately before writing, and re-checked once more before that draft was
finalized. That first draft's §12 therefore named each required proof layer (V1..V7, static
conformance) and stated, structurally, what the real shipped code in
`src/manosube_agent_civilization/change_executor/` did that would satisfy it, without citing a
test file or function name.

A full test suite (9 test files, 2 shared fixture modules, 161 tests) was written and verified
immediately afterward, in parallel with this document's own drafting, and is now present under
the three directories named above. §12 below has been revised to cite it by real file and test
name. One genuine defect the test suite itself found and demonstrated in an earlier draft of
`route.py` -- idempotency-slot resolution running *after* staleness rather than before, which
made an ordinary same-`claim_token` replay spuriously refuse as stale once any prior commit had
advanced `state_revision` -- was fixed in the shipped code before this delivery (see `route.py`'s
own module docstring, disclosed judgment call 5); every citation below is to the test suite as it
runs against the corrected code, not the defective draft it originally caught.

**Three further findings, from an automated review of PR #74, fixed after this document's first
draft.** An automated review identified three real defects against `route.py`, all since fixed
(disclosed judgment calls 6-8 below), and the test suite extended to 167 tests (same 9 files, same
2 fixture modules -- no new file) to prove each: (1) `worktree_root` was a request-facing
parameter with nothing tying it to the bound Boundary's own `repository`/`branch`, letting an
authorized Change be pointed at an unrelated checkout -- moved to composition time; (2) a crash
between the `execution_intent` commit and the following `execution_attempt` commit permanently
stranded the slot behind a spurious `StaleExecutionInputError`, with no path to reconciliation --
idempotency-slot resolution now also resolves an existing intent and skips staleness only when
this exact caller (identical `claim_token`) is resuming it; (3) two genuinely concurrent callers
could both pass idempotency-slot resolution before either committed anything and both call
`adapter.execute` -- `execution_attempt` now carries a fresh `attempt_nonce` per call, so the
Store's own existing conflict detection (not new machinery) correctly refuses the second one.
Every citation below, and every count in §12, is to the test suite as it runs against the code
with all three fixes applied.

## 2. Public signature

```python
from manosube_agent_civilization.change_executor import (
    ControlledFilesystemAdapter,
    compose_change_executor,
    commit_change_executor_kill_switch,
)

execute = compose_change_executor(
    store,
    project_id=project_id,
    project_binding_id=project_binding_id,
    execution_boundary={...},  # a closed Execution Boundary -- see §7
    adapter_identity={"kind": "controlled_filesystem_adapter", "version": "0.1"},
    adapter=ControlledFilesystemAdapter(executor_identity="controlled_filesystem_adapter", executor_version="0.1"),
    worktree_root="/path/to/an/admitted/disposable/worktree",  # bound once, here -- see §3 item 6
    kill_switch_trust_anchor_public_key_hex=configured_trust_anchor,
)

result = execute(
    change_id,
    claim_token="...",
    execution_instant="2026-09-10T00:00:01Z",
)
result["receipt"]         # the immutable change_execution_receipt
result["replay"]          # True only for an exact claim_token replay of an existing receipt
result["semantic_reuse"]  # True only when permit_semantic_reuse=True reused a receipt minted
                           # under a different claim_token

from manosube_agent_civilization.change_executor import route_change_execution_to_evidence

evidence = route_change_execution_to_evidence(store, result["receipt"], project_id, evidence_request)
```

`compose_change_executor` binds *store*, *project_id*, *project_binding_id*, a
canonicalized-and-frozen Execution Boundary, a canonicalized-and-frozen adapter identity, the
replaceable *adapter* itself, *worktree_root* (validated at composition to be a non-empty string
resolving to a real, existing directory -- §3 item 6), and the kill-switch trust anchor -- once,
before any request exists. The returned closure's own call signature carries only request-facing
data: there is no keyword, positional slot, or attribute on it through which a caller could
substitute a different Store, Boundary, adapter identity, adapter, worktree root, or trust anchor
after the fact.

**Disclosed judgment call: the return shape is a small envelope, not the bare receipt.** The
seeding task description asks for an idempotent replay to "return the existing receipt unchanged"
and a disclosed semantic reuse to return it "with a distinguishable field/flag" -- but
`execution_receipt.schema.json` is closed (`additionalProperties: false`), so no such flag can be
added to the immutable receipt record itself without becoming a second, undeclared schema. The
returned closure therefore always returns `{"receipt": <the exact, unmodified
change_execution_receipt>, "replay": bool, "semantic_reuse": bool}` -- a uniform envelope across
every code path (a genuinely first execution returns both flags `False`), so "unchanged" is
satisfied for the nested receipt itself in every case, and the distinguishing flag lives one
level out instead of inside the closed record.

## 3. Frozen semantic decisions

1. **`execution_started_at`/`execution_ended_at` both come from the one caller-supplied
   `execution_instant`.** The request-facing closure's own call shape carries exactly one
   instant, and this package reads no clock anywhere. Both receipt timestamp fields are
   therefore set to that one instant.
2. **A kill-switch refusal at checkpoint #2, and a Boundary-limit violation discovered while
   building the operation, both produce a terminal receipt rather than a raised exception.** By
   that point an `execution_attempt` is already durably committed; this package's own idempotency
   contract requires *some* terminal receipt to exist for a committed attempt (a bare exception
   here would leave the slot permanently stuck in "attempt exists, no receipt" --
   `ExecutionReconciliationRequiredError` forever, with no path to resolution). `KILL_SWITCH_
   STOPPED` and `BOUNDARY_VIOLATION` are both named, closed members of `EXECUTION_OUTCOMES` for
   exactly this reason -- and neither path ever calls `adapter.execute` at all.
3. **The best-effort rollback call is a second, distinct, explicitly policy-gated adapter call,
   not a violation of "call `adapter.execute(...)` exactly once."** That requirement governs
   dispatch of the one *primary*, requested operation; `rollback_policy ==
   "BEST_EFFORT_DELETE_WRITTEN_FILES"` is a Boundary-declared, closed, distinct recovery action,
   only ever reached after a partial or failed primary call, and only ever deletes exactly the
   paths the primary call's own raw facts say it wrote -- never a second attempt at the original
   operation.
4. **The mapping slot IS the shared record id for `execution_intent`, `execution_attempt`, and
   `change_execution_receipt`.** A full content address over `execution_intent`'s own semantic
   fields would vary with `claim_token`, so two different callers' intents for the identical
   `(change, Boundary, adapter)` would not collide at one Store `(kind, id)` slot -- exactly the
   collision the mapping-slot mechanism exists to produce. `execution_mapping_slot_key` is
   therefore a narrower projection (`change_id`, `execution_boundary_fingerprint`,
   `adapter_identity_fingerprint` alone, deliberately excluding `claim_token`), used verbatim as
   the Store id of all three related records for one slot. See §9.
5. **Where the current-kill-switch pointer lives.** `01_SCHEMA/state/semantic_state.schema.json`
   is an existing-owner schema this package may not touch; it is `additionalProperties: false`
   and fixed to exactly nine domains. This module stores its own current-pointer inside the
   existing **`"deployment"`** domain's `claims` map (a domain no other shipped package currently
   writes to, and deliberately not `"runtime"`, which is Runtime's own domain), under one fixed
   claim key, `CHANGE_EXECUTOR_KILL_SWITCH_CURRENT_ID` -- there is exactly one kill switch per
   project, never one per target, so no per-binding key map is needed. See §10.
6. **`worktree_root` is a composition-time parameter, not a request-facing one.** An automated
   review of PR #74 correctly identified that a request-facing `worktree_root` was a genuine
   Boundary-binding gap: every other trust-sensitive parameter this module uses is bound once at
   composition, but `worktree_root` alone was left request-facing, so nothing tied it to the
   bound Boundary's own fixed `repository`/`branch` -- a caller of one composed executor could
   point every write at an arbitrary existing directory unrelated to the Change it was authorized
   against (the adapter's own confinement is real defense *within* whatever root it is handed,
   never a defense against being handed the *wrong* root). Every Change executed through one
   composed executor already shares that one composed executor's own bound Boundary's fixed
   `repository`/`branch`, so binding `worktree_root` once at composition -- validated there to
   resolve to a real, existing directory -- is the correct model, not merely the fix.
7. **A caller resuming its own crash-interrupted intent skips the staleness check for that one
   call.** Every commit this route performs -- including the `execution_intent` commit alone --
   unconditionally advances `state_revision` by one (item 4/§9). A crash after that one commit
   succeeds but before the following `execution_attempt` commit ever runs leaves a slot with a
   durably committed intent, no attempt, no receipt; a bare retry previously raised
   `StaleExecutionInputError` permanently (an automated review identified this real crash-recovery
   gap), with zero adapter side effect ever having occurred and no path to reconciliation.
   Idempotency-slot resolution now additionally resolves any existing `execution_intent` for the
   slot; when one exists and its own declared `claim_token` equals this call's own, this call is
   that exact caller resuming its own interrupted attempt -- not a collision -- and only the
   staleness raise is skipped for it. A *different* `claim_token` against an existing intent is
   not a resume: it is left unflagged and correctly falls through to collide at the intent-commit
   step (`RecordConflictError` -> `ExecutionConcurrentClaimError`), unchanged.
8. **`execution_attempt` carries a fresh, per-call `attempt_nonce`.** Two callers invoking
   `execute()` truly concurrently with the identical `change_id`/`claim_token`/`execution_instant`
   could both pass idempotency-slot resolution before either had committed anything, then both
   build byte-identical `execution_attempt` records (deterministic from their identical inputs) --
   and the Store's own commit correctly treats a second, byte-identical attempt as an idempotent
   replay of the first rather than a conflict (the exact behavior legitimate sequential
   crash-retry depends on), so the second caller's attempt-commit would also succeed and call
   `adapter.execute` a second time (an automated review identified this real race). A fresh
   `secrets.token_hex(16)`, generated only immediately before building a genuinely new attempt
   (never caller-supplied, never derived from any other input), makes two independently-built
   attempts for the same slot genuinely different byte-for-byte, so the Store's own *existing*
   conflict detection -- not new Store-layer machinery -- correctly refuses the second one. It
   never participates in `execution_mapping_slot_key`/the record id itself (§9), only in the
   record body; `execution_intent`'s own body is deliberately untouched, since two racing
   intent-commits both succeeding is harmless by itself.

## 4. Canonical owner

```text
change_executor/route.py               the one public execution route (compose_change_executor);
                                        the one Boot call site; owns the entire canonical route
change_executor/evidence_handoff.py    the one Evidence hand-off (the one derive_evidence call)
change_executor/engine.py              pure record builders for the three request-scoped record
                                        kinds; no Store I/O, no clock
change_executor/identity.py            deterministic identities and the one mapping-slot key
change_executor/boundary.py            strict inert-data canonicalization, the closed low-risk
                                        action vocabulary, and Execution Boundary validation
change_executor/kill_switch.py         the human kill switch chain: resolve/verify/commit
change_executor/adapter.py             the one production adapter, ControlledFilesystemAdapter
change_executor/types.py               closed vocabularies, the ChangeExecutorAdapter Protocol
change_executor/errors.py              the typed refusal vocabulary
```

### 4.1 Canonical records

```text
execution_intent           EXECUTION_INTENT_SEMANTIC_FIELDS: project_id, change_ref,
                            execution_boundary_fingerprint, adapter_identity_fingerprint,
                            claim_token, requested_at
execution_attempt          EXECUTION_ATTEMPT_SEMANTIC_FIELDS: the above, plus
                            execution_intent_ref, attempt_nonce (a fresh per-call
                            secrets.token_hex(16) -- §3 item 8; never part of the record id)
change_execution_receipt   CHANGE_EXECUTION_RECEIPT_SEMANTIC_FIELDS: change_ref, idempotency_key,
                            authority_ref, project_id, project_binding_ref,
                            boot_state_fingerprint, execution_boundary_fingerprint,
                            executor_identity, executor_version, target, operation,
                            execution_started_at, execution_ended_at, outcome,
                            performed_result_fingerprint, performed_result_summary,
                            rollback_outcome, claim_token, reobservation_request
                            (excludes its own declared id/fingerprint and execution_request_id,
                            which is always exactly the declared id itself)
change_executor_kill_switch   KILL_SWITCH_SEMANTIC_FIELDS: project_id, status, generation,
                               predecessor_ref (excludes its own id/fingerprint/signature)
```

## 5. Canonical route

Every request-facing call performs the following, in this exact order (`route.py`'s own
`compose_change_executor.execute`):

```text
canonicalize + freeze execution_boundary / adapter_identity, and bind worktree_root
                                                                            (composition, once)
→ execution_instant falls within the bound Boundary's own validity_window  (zero-call refusal)
→ kill switch check #1 -- fresh resolve, ACTIVE required, signature re-verified
→ idempotency-slot resolution: an existing receipt (replay/reuse/mismatch), an existing attempt
  with no receipt (reconciliation required), an existing intent under this exact caller's own
  claim_token with neither (resuming a crash-interrupted attempt -- §3 item 7), or none of the
  three (proceed) -- deliberately *before* Boot and staleness (§3 item 4/§9 explain why)
→ fresh Boot (boot_project)                                 (a genuinely new or resumed slot only)
→ resolve the Change, recompute-and-compare its own identity/fingerprint, require AUTHORIZED
→ resolve the Authority Decision the Change names, recompute-and-compare, require AUTONOMOUS
→ require action_kind in the bound Boundary's own permitted_action_kinds, and not Human-only
→ require scope.repository/branch/paths are entirely admitted by the bound Boundary
→ staleness: before_state_fingerprint / expected_state_revision must equal the fresh Boot's own
  -- skipped only when resuming a prior, crash-interrupted intent under this exact claim_token
→ commit execution_intent                                    (RecordConflictError -> concurrent
                                                                claim)
→ commit execution_attempt, carrying a fresh attempt_nonce    (RecordConflictError -> concurrent
                                                                claim -- §3 item 8)
→ kill switch check #2 -- fresh resolve again, immediately before the one adapter call; a
  refusal here still produces a terminal receipt (KILL_SWITCH_STOPPED), never a bare exception,
  because an execution_attempt is already committed and idempotency requires a terminal outcome
→ build + validate the closed operation against the bound Boundary's own file-count/byte/path
  limits; a violation here likewise produces a terminal receipt (BOUNDARY_VIOLATION), never a
  bare exception, for the identical reason
→ call adapter.execute(...) exactly once for the primary requested operation, against the one
  worktree_root bound at composition (a distinct, policy-gated best-effort rollback call may
  follow, only when the primary call partially mutated and rollback_policy ==
  BEST_EFFORT_DELETE_WRITTEN_FILES)
→ classify the adapter's raw reported facts into one EXECUTION_OUTCOMES member -- never trusted
  from the adapter as an assertion
→ build + commit the terminal change_execution_receipt (with the embedded reobservation_request)
→ return {"receipt": ..., "replay": bool, "semantic_reuse": bool}
```

A terminal replay/semantic-reuse return, and a refusal detected at idempotency-slot resolution
itself, both leave here with zero Boot, zero Store commit, and zero adapter calls. Every
exception path from idempotency-slot resolution through staleness likewise raises before any
Store commit and before the adapter is ever constructed a call to (P18-C4). `route.py`'s own
docstring states this ordering as the canonical route; the numbered comments inline in
`compose_change_executor.execute` mirror it exactly (step 4 now also resolves an existing
`execution_intent`, per §3 item 7, without a new step number).

## 6. P18-C1 through P18-C10

### P18-C1 -- Exact executable Change admission

*Requirement:* the executor route accepts only one canonical `AUTHORIZED` Change whose Authority
provenance is reproduced through the existing Authority owner, binding the identical project,
before-State fingerprint, expected State revision, action, operation, scope, and idempotency key.
Caller-asserted "approved," hash-consistent fabricated decisions, model recommendations, URL
content, and adapter claims are not Authority.

*Code:* `route._resolve_change` resolves the Change by `store.resolve_record`, requires
`change.get("project_id") == project_id`, recomputes `change_id`/`change_semantic_fingerprint`
via `change.identity` and requires them to equal the Store-lookup key and the record's own
declared values, and requires `status == "AUTHORIZED"`. `route._resolve_authority_decision`
performs the identical three-way check on the `authority_decision` the Change names, then
`compose_change_executor.execute` requires `decision["decision"] == AUTONOMOUS`. `route.py`
imports `authority.identity.decision_id`/`decision_semantic_fingerprint` and `change.identity.
change_id`/`change_semantic_fingerprint` -- never `authority.evaluate_authority` or
`change.engine.derive_change` -- so this package only ever reproduces an already-minted Decision
and an already-derived Change, never evaluates or derives one itself. The Change's own
`before_state_fingerprint`/`expected_state_revision`, `action.action_kind`, `scope`, and
`idempotency_key` are each independently checked or carried through, never trusted as a caller's
bare claim (steps 5-10 of §5).

*Proof layer:* V2 (Authority/Change continuity) and V6 (tamper/substitution matrix).

### P18-C2 -- Closed low-risk execution Boundary

*Requirement:* one deterministic, identity-bearing Boundary enumerating at least: admitted
action/operation kinds; repository/worktree identity and root; branch/target identity; admitted
paths; mutation limits; symlink/traversal/path-escape policy; network/subprocess/environment/
credential policy; timeout; rollback policy; executor identity/version; kill-switch state;
validity window. Unknown fields, wildcard authority, and free-form command strings are refused.
Boundary identity must participate in the execution-request and receipt identities.

*Code:* `boundary.validate_execution_boundary` + `REQUIRED_BOUNDARY_KEYS` (§7 below) enforce
every field the requirement names, field-by-field, and additionally schema-validate against
`execution_boundary.schema.json` (`additionalProperties: false`) so an unknown key is refused
twice, independently. `execution_boundary_fingerprint` is embedded in
`execution_mapping_slot_key` (so it participates in every one of the three request-scoped record
ids) and directly in `change_execution_receipt.execution_boundary_fingerprint`. **One field the
requirement names is deliberately not a Boundary key:** kill-switch state is not declared inside
the frozen, content-addressed Boundary payload at all -- it is checked live, twice per request,
against `kill_switch.py`'s own separately chained, separately signed
`change_executor_kill_switch` record (§10), because kill-switch state is a dynamic fact that can
change between two calls sharing the identical Boundary, and a content-addressed Boundary is, by
construction, immutable once fingerprinted.

*Proof layer:* V1 (deterministic identity and schema proof) and V5 (prohibited-scope/kill-switch
matrix).

### P18-C3 -- Replaceable controlled executor adapter

*Requirement:* one replaceable executor adapter protocol and one controlled filesystem/worktree
adapter for the disposable vertical proof. The adapter receives a prevalidated closed operation,
not raw prose, prompts, URLs, model output, or arbitrary commands. It cannot evaluate Authority,
broaden scope, write State/Evidence, close Difference, or declare completion.

*Code:* `types.ChangeExecutorAdapter` is a `Protocol` with exactly one executable method,
`execute(self, operation: Any, *, worktree_root: str) -> dict[str, Any]`. `adapter.
ControlledFilesystemAdapter` is the one shipped production implementation: its constructor takes
no Store, Boundary, or Project identity -- only self-identification strings -- and its `execute`
performs mechanical filesystem writes/deletes strictly beneath a caller-supplied `worktree_root`,
with real traversal/symlink-escape enforcement (rejects absolute/`.`/`..` paths outright, walks
every intermediate ancestor refusing any that is itself a symlink, refuses a target that already
exists as a symlink, and independently re-resolves the final path with `Path.resolve()` to
require it begins with `worktree_root`'s own resolved parts). `route._operation_violation_reason`
builds and bounds the closed `ExecutionOperation` (`operation_kind`, `file_writes`,
`file_deletes` -- each write/delete path checked against `admitted_paths` and the byte/file-count
limits) before `adapter.execute` is ever called; the adapter never sees the Change's raw
`action.operation` payload directly, only this prevalidated projection.

*Proof layer:* V3 (real vertical proof) and static conformance (no network/subprocess/credential
import anywhere in this package -- verified directly against every module's own import list).

### P18-C4 -- Preflight-before-effect and fail-closed staleness

*Requirement:* all facts knowable before mutation are checked before the first side effect;
stale, substituted, tampered, ambiguous, expired, or unverifiable input refuses with zero
executor calls and zero mutation.

*Code:* §5's canonical route is exactly this ordering: time window, kill switch #1, fresh Boot,
Change/Authority resolve-and-recompute, action-kind/scope admission, and staleness (`change[
"before_state_fingerprint"] != current_fingerprint or change["expected_state_revision"] !=
boot_context.current_state["state_revision"]` raises `StaleExecutionInputError`) all run, and can
all raise, before `_commit_records` is ever called for `execution_intent` -- i.e. before any
Store commit of any kind and before `adapter.execute` is ever reached. `route.py`'s own docstring
states this explicitly: "Every exception path up through staleness raises before any Store commit
and before the adapter is ever constructed a call to."

*Proof layer:* V2 (decisive zero-call controls) and V6 (tamper/substitution matrix).

### P18-C5 -- Idempotency, replay, and crash semantics

*Requirement:* the contract must distinguish first execution, exact replay, conflicting
reuse/substitution, started-but-unknown, partial failure, and terminal success/failure/refusal. A
retry must never silently convert `UNKNOWN` or partial execution into success. Concurrent
duplicate attempts must not perform the mutation twice.

*Code:* see §9 for the full state machine. In outline: `execution_mapping_slot_key` (§3 item 4,
§9) defines execution identity from `(change_id, execution_boundary_fingerprint,
adapter_identity_fingerprint)`. A resolved terminal receipt under the identical `claim_token`
returns `{"replay": True}` with the unmodified receipt, never re-executing. A resolved terminal
receipt under a *different* `claim_token` either raises `ExecutionTerminalClaimMismatchError` or,
only with explicit `permit_semantic_reuse=True`, returns `{"semantic_reuse": True}` -- also
without re-executing. A resolved `execution_attempt` with no terminal receipt raises
`ExecutionReconciliationRequiredError` -- "the true outcome of a prior attempt (which may already
have called the adapter) is genuinely unknown," refused rather than guessed or silently retried.
A `RecordConflictError` committing either `execution_intent` or `execution_attempt` (a genuinely
concurrent claim already holding the slot) raises `ExecutionConcurrentClaimError`, never silently
retried into an attempt or an adapter call. A crash between the `execution_intent` commit and the
following `execution_attempt` commit leaves the identical, non-conflicting caller (matching
`claim_token`) able to resume rather than be permanently stranded by staleness (§3 item 7/§9), and
a fresh per-attempt `attempt_nonce` (§3 item 8) ensures two genuinely concurrent callers racing
for the same slot never both reach `adapter.execute` -- the second one's attempt-commit is a real
`RecordConflictError` -> `ExecutionConcurrentClaimError`, not an idempotent replay. **Disclosed
structural fact:** if `adapter.execute`
itself raises (rather than returning an error fact), `route.py` converts that into a raised
`ExecutionAdapterError` rather than committing an `UNKNOWN`-outcome receipt -- by that point
`execution_attempt` is already durably committed, so the *next* call for that identical slot
correctly refuses as reconciliation-required, "rather than retry blindly" (`route.py`'s own
inline comment at that call site). The `UNKNOWN` member of `EXECUTION_OUTCOMES` therefore remains
part of the closed contract vocabulary without this package's own route ever being the site that
commits a receipt carrying it.

*Proof layer:* V4 (idempotency/concurrency/crash matrix).

### P18-C6 -- Immutable authorized execution receipt

*Requirement:* a deterministic, content-addressed receipt binding execution/request identity,
Change identity and idempotency key, Authority Decision reference, Project/Binding/Boot context,
before-State revision/fingerprint, Boundary identity, executor identity, target and admitted
operation, start/end instants, typed outcome, performed-result fingerprint and bounded summary,
rollback outcome, and after-state re-observation request identity.

*Code:* `engine.build_change_execution_receipt` builds exactly this record and schema-validates
it against `execution_receipt.schema.json` (`additionalProperties: false`) before returning it;
every field the requirement names has a corresponding required schema field (§8/§4.1 above list
them). `change_execution_receipt_id` is always exactly `execution_request_id`, the shared
mapping-slot key (§9). The record is never mutated after commit -- every later resolution
(`route._resolve_slot_record`, `evidence_handoff.resolve_and_verify_committed_receipt`)
independently recomputes its identity and semantic fingerprint and refuses to trust it otherwise.

*Proof layer:* V1 (deterministic identity/schema proof).

### P18-C7 -- Re-observation and existing-owner continuity

*Requirement:* every attempted execution, including failed, blocked, partial, and unknown
outcomes, must emit or preserve a typed request for independent after-state Observation.
Post-execution facts must flow through the existing Observation, Difference, Evidence,
Independent Verification, and Reflow contracts; no second owner may be introduced.

*Code:* `reobservation_request` (`{"kind": "change_execution_reobservation_request", "target":
{...}, "reason_codes": ["AUTONOMOUS_CHANGE_EXECUTION_ATTEMPTED"], "requested_at": ...}`) is built
once, immediately after `execution_attempt` is committed, and passed identically into every one
of `_commit_terminal_receipt`'s call sites -- the `KILL_SWITCH_STOPPED` path, the
`BOUNDARY_VIOLATION` path, and the final adapter-outcome path all carry the identical
`reobservation_request` shape. **Precise scope of "every attempted execution":** a request that
is refused *before* `execution_attempt` is ever committed (staleness, unresolvable Change/
Authority, Boundary/scope mismatch, kill switch check #1) never produces any receipt at all, by
the preflight-before-effect discipline P18-C4 itself requires -- nothing was yet "attempted" in
the sense a receipt exists for. Every outcome reached *after* `execution_attempt` exists commits
a terminal receipt carrying `reobservation_request`, with no exception. `evidence_handoff.
route_change_execution_to_evidence` hands the receipt to `evidence.derive_evidence`, the one
existing Evidence owner, in the Change-Free Verification Evidence position (`evidence_request.
verification_observation_request` required non-`None`; `change_request` and
`post_change_observation_request` both required `None`) -- never a second Evidence, Observation,
Difference, Independent Verification, or Reflow owner. This package imports none of `reflow`.

*Proof layer:* V3 (real vertical proof, including the hand-off) and V7 (Kernel continuity).

### P18-C8 -- Human kill switch and non-self-closure

*Requirement:* a Human-controlled kill switch checked immediately before the first side effect
and at every safe continuation boundary. The executing Agent and adapter cannot enable/bypass the
switch, approve their own Change, accept their own receipt as sufficient Evidence, mutate
completion semantics, close the Difference/Issue/PR, or authorize a retry after an unknown/
partial outcome. The proof must include a deterministic pre-start stop and an interruption at a
safe mid-execution boundary.

*Code:* see §10 for the full chain mechanism. `route._require_active_kill_switch_verified` is
called twice per request: checkpoint #1 before any Store commit or Boot (`stage="before Boot"`),
checkpoint #2 immediately before the one `adapter.execute` call
(`stage="immediately before the adapter call"`) -- this package's own execution is single-step
(one primary adapter call, at most one policy-gated rollback call), so this one checkpoint is
exactly the "safe continuation boundary" the requirement names. Both checkpoints independently
resolve the current kill switch fresh (never cached across the two checks) and independently
re-verify its Ed25519 signature against the caller-supplied `kill_switch_trust_anchor_public_key_
hex` -- "defense in depth beyond what commit-time verification alone already establishes,
appropriate to a control whose entire purpose is to be trusted at the exact moment it is checked"
(`route.py`'s own inline docstring). A checkpoint-#1 refusal raises `ExecutionKillSwitchError`
with zero Store commits and zero adapter calls -- the deterministic pre-start stop. A
checkpoint-#2 refusal commits a `KILL_SWITCH_STOPPED` terminal receipt without ever calling
`adapter.execute` -- the interruption at the one safe mid-execution boundary this package's own
single-step execution has. **Non-self-closure, structurally:** nothing in `route.py`, `engine.
py`, or any adapter can construct a valid signed `change_executor_kill_switch` record or flip its
own status -- only `kill_switch.commit_change_executor_kill_switch`, called with an externally
supplied private key's matching public counterpart, can (`kill_switch.py` "holds no private key
and mints no signature of its own -- it only ever verifies"). This package never imports an
Authority evaluator (so it cannot approve its own Change), and `evidence_handoff.py` constructs
`verification_result_provenance` but never itself decides sufficiency -- that decision belongs
entirely to `derive_evidence`, the existing owner.

*Proof layer:* V5 (prohibited-scope and kill-switch matrix).

### P18-C9 -- Typed failure and no silent rollback claim

*Requirement:* refusal, validation failure, boundary violation, stale authority, target drift,
kill-switch stop, timeout, adapter failure, partial mutation, rollback success, rollback failure,
and unknown outcome remain distinguishable. "Rollback requested" is not "rollback succeeded";
neither may erase the execution attempt or its receipt.

*Code:* `EXECUTION_OUTCOMES` (§8) is the closed, twelve-member vocabulary naming exactly these.
`route._classify_outcome` classifies the adapter's raw reported facts (never an adapter
assertion) into `SUCCEEDED`, `PARTIAL_MUTATION`, or `ADAPTER_FAILURE`; a subsequent rollback
attempt (`route._attempt_rollback`, gated on `rollback_policy ==
"BEST_EFFORT_DELETE_WRITTEN_FILES"`) reports its own distinct `rollback_outcome`
(`ROLLBACK_OUTCOMES`: `NOT_ATTEMPTED`, `ROLLBACK_SUCCEEDED`, `ROLLBACK_FAILED`) as a *separate*
receipt field, never folded silently into `outcome` without also being visible in
`rollback_outcome` -- when a rollback is attempted and succeeds, `outcome` itself is set to
`"ROLLBACK_SUCCEEDED"` and `rollback_outcome` is independently set to `"ROLLBACK_SUCCEEDED"` too,
so a reader never has to infer rollback state from `outcome` alone. When `rollback_policy ==
"NONE"`, `rollback_outcome` is explicitly `"NOT_ATTEMPTED"` -- "rollback requested" (a Boundary
that permits it) is never conflated with "rollback succeeded" (a receipt that actually reports
it). No commit path ever deletes or replaces a prior `execution_attempt` or `change_execution_
receipt`; every terminal outcome, including a violation or a kill-switch stop, is itself a new,
immutable, committed receipt.

*Proof layer:* V4 (idempotency/concurrency/crash matrix) and V1 (schema proof that every listed
outcome is a real, distinct enum member).

### P18-C10 -- Model, URL, and Agent boundary continuity

*Requirement:* Model Runtime output, URL Boot content, and temporary Agent output remain
candidate/untrusted inputs; they cannot enter the executor as executable authority-bearing
instructions. Phase 18 must not implement Phase 19 multi-Agent orchestration.

*Code:* this package imports none of `model_runtime`, `url_boot`, or `agent_runtime` anywhere
(confirmed against every module's own import list). The one replaceable adapter's `execute`
method receives only a closed `ExecutionOperation` TypedDict (`operation_kind`, `file_writes`:
`{path, content_utf8}`, `file_deletes`: `{path}`) -- never a URL, a prompt, or a raw model
response -- and that operation is itself derived from the Change's own already-authorized
`action.operation` payload, prevalidated and bounded by `route._operation_violation_reason`
before the adapter is ever reached. No orchestration of multiple Agents, of multiple Changes in
one call, or of any Phase-19-shaped coordination exists anywhere in this package.

*Proof layer:* static conformance (import-surface proof) and V7 (Kernel continuity).

## 7. The closed Execution Boundary schema

`01_SCHEMA/change_executor/execution_boundary.schema.json`, `additionalProperties: false`,
`REQUIRED_BOUNDARY_KEYS` (17 keys, every one required, no others admitted):

| Field | Constraint |
|---|---|
| `permitted_action_kinds` | non-empty, unique list, every member in `PERMITTED_ACTION_KINDS` (§8) |
| `repository` | non-empty string |
| `branch` | non-empty string |
| `admitted_paths` | non-empty, unique list of genuinely relative POSIX-style paths (no leading `/`, no empty/`.`/`..` segment) |
| `max_files_changed` | positive integer |
| `max_bytes_changed` | positive integer |
| `max_file_bytes` | positive integer |
| `permit_symlinks` | schema-fixed `false` |
| `permit_path_traversal` | schema-fixed `false` |
| `permit_network` | schema-fixed `false` |
| `permit_subprocess` | schema-fixed `false` |
| `permit_environment_mutation` | schema-fixed `false` |
| `permit_credential_access` | schema-fixed `false` |
| `timeout_seconds` | positive integer |
| `rollback_policy` | one of `ROLLBACK_POLICIES` (§8) |
| `executor_identity` | non-empty string |
| `executor_version` | non-empty string |
| `validity_window` | `{issued_at, expires_at}`, both RFC3339 UTC instants, genuinely ordered (`issued_at < expires_at`) |

The six `permit_*` fields marked schema-fixed `false` above are, in `boundary.py`, additionally
checked at the Python level (`_FIXED_FALSE_KEYS`) to be exactly the Python value `False` -- a
Boundary supplying `True` for any of them is refused outright, never silently downgraded.
`execution_boundary_fingerprint(boundary)` is `"sha256:" + sha256(canonical_json_bytes(dict(
boundary)))` over the *entire* boundary mapping (a Boundary carries no identity field of its own
to exclude, unlike a record).

`PERMITTED_ACTION_KINDS` (Issue #73's own `INITIAL_AUTONOMOUS_SCOPE`) is checked, at module
import time, to be disjoint from `authority.levels.HUMAN_ONLY_ACTION_KINDS` -- a defense-in-depth
assertion, not merely a runtime check, so this package's own Boundary refuses a Human-only action
kind on its own terms, never relying solely on the fact that Authority would already have refused
it upstream.

## 8. The closed outcome vocabularies

```python
EXECUTION_OUTCOMES = frozenset({
    "SUCCEEDED", "REFUSED", "BOUNDARY_VIOLATION", "STALE_AUTHORITY", "TARGET_DRIFT",
    "KILL_SWITCH_STOPPED", "TIMEOUT", "ADAPTER_FAILURE", "PARTIAL_MUTATION",
    "ROLLBACK_SUCCEEDED", "ROLLBACK_FAILED", "UNKNOWN",
})

ROLLBACK_OUTCOMES = frozenset({"NOT_ATTEMPTED", "ROLLBACK_SUCCEEDED", "ROLLBACK_FAILED"})

PERMITTED_ACTION_KINDS = frozenset({
    "WRITE_DOCUMENTATION_FILE", "WRITE_TEST_FILE", "WRITE_ISOLATED_SOURCE_FILE",
    "WRITE_LOW_RISK_CONFIGURATION_FILE", "DELETE_DOCUMENTATION_FILE", "DELETE_TEST_FILE",
    "DELETE_ISOLATED_SOURCE_FILE",
})

ROLLBACK_POLICIES = frozenset({"NONE", "BEST_EFFORT_DELETE_WRITTEN_FILES"})
```

`types.py`'s own docstring states the vocabulary is "closed and complete for the *contract*, not
a claim that one route implementation exercises every member": `route.py`'s own route never
itself commits a `REFUSED`-outcome receipt (a refusal at that stage is a raised, typed exception
with zero Store I/O, per the preflight discipline of P18-C4) or a `TARGET_DRIFT`/`TIMEOUT`-outcome
receipt (this package reads no ambient clock and its adapter's own worktree confinement makes a
genuine drift-after-admission a distinct future concern this delivery's own single, synchronous,
local `ControlledFilesystemAdapter` does not itself produce a path to). `REFUSED` and
`BOUNDARY_VIOLATION` are deliberately distinct: `REFUSED` is named in the contract vocabulary for
a well-formed-but-inadmissible request refused before any commit; `BOUNDARY_VIOLATION` is the
narrower case this package's own route does produce -- a well-typed operation exceeding the bound
Boundary's own limits, discovered *after* `execution_attempt` is already committed, and therefore
recorded as a genuine terminal receipt.

Note `PERMITTED_ACTION_KINDS` carries no `DELETE_LOW_RISK_CONFIGURATION_FILE` member -- the
vocabulary admits writing a low-risk configuration file but not deleting one; this is the literal
shipped vocabulary, transcribed exactly, not a narrowing this document introduces.

## 9. The idempotency/mapping-slot state machine

Every execution request is identified by one deterministic value, independent of `claim_token`
and of any instant:

```python
execution_mapping_slot_key(change_id, execution_boundary_fingerprint, adapter_identity_fingerprint)
  = "EXEC-SLOT-" + sha256(canonical_json_bytes({
        "change_id": change_id,
        "execution_boundary_fingerprint": execution_boundary_fingerprint,
        "adapter_identity_fingerprint": adapter_identity_fingerprint,
    })).hexdigest().upper()
```

This one value is used, verbatim, as the Store `(kind, id)` identity of `execution_intent`,
`execution_attempt`, and `change_execution_receipt` for that slot -- so two distinct callers
proposing the identical `(change, Boundary, adapter)` triple always collide at the identical
slot, and only a genuinely distinct triple ever produces a distinct one. Each kind's own broader
content (including `claim_token` and `requested_at`) is still fully tamper-checked, separately,
through that kind's own `*_semantic_fingerprint` function -- the coarser slot key is only the
record *id*, never a substitute for full content tamper-detection.

Per-request resolution, in order (`route.py` step 4):

```text
resolve change_execution_receipt at slot_key
  found, claim_token matches       -> {"receipt": <unmodified>, "replay": True,
                                        "semantic_reuse": False}   (no re-execution)
  found, claim_token differs,
    permit_semantic_reuse=True     -> {"receipt": <unmodified>, "replay": False,
                                        "semantic_reuse": True}    (no re-execution)
  found, claim_token differs,
    permit_semantic_reuse=False    -> ExecutionTerminalClaimMismatchError
  not found -> resolve execution_attempt at slot_key
    found (no receipt yet)         -> ExecutionReconciliationRequiredError
                                       ("the true outcome of a prior attempt ... is genuinely
                                        unknown; refusing rather than risk a duplicate real
                                        mutation")
    not found -> resolve execution_intent at slot_key
      found, claim_token matches   -> resuming_from_existing_intent=True: proceed exactly as
                                       "not found" below, except the staleness check (§6 P18-C4)
                                       is skipped for this one call -- a crash between the intent
                                       commit and the attempt commit, this exact caller retrying
                                       (§3 item 7)
      found, claim_token differs   -> not a resume; proceed as "not found" below unchanged --
                                       correctly collides at the intent-commit step
                                       (RecordConflictError -> ExecutionConcurrentClaimError)
      not found                    -> proceed: commit execution_intent, then execution_attempt
                                       (carrying a fresh attempt_nonce -- §3 item 8; either
                                       commit's RecordConflictError ->
                                       ExecutionConcurrentClaimError -- a genuinely concurrent
                                       claim, never silently retried)
```

Every record resolved from the Store at any point in this state machine
(`route._resolve_slot_record` + `route._verify_slot_record`) is independently recomputed and
compared -- Store lookup key, declared id, and recomputed id must all agree, and the declared
semantic fingerprint must equal the recomputed one -- before any of its fields are trusted,
including `claim_token` itself.

## 10. The human kill switch: ACTIVE/REVOKED monotonic chain, Ed25519 signing/verification split

`change_executor_kill_switch` (`kill_switch.py`) mirrors -- deliberately without importing --
`runtime.admission_registry`'s own shape: a signed, content-addressed, monotonically chained
record, and one sanctioned committer.

**Identity and chain shape.** `KILL_SWITCH_SEMANTIC_FIELDS = (project_id, status, generation,
predecessor_ref)`. `kill_switch_id`/`kill_switch_semantic_fingerprint` hash exactly this
projection (excluding the record's own declared id/fingerprint and its `signature` block, which
cannot cover its own value). `status` is one of `KILL_SWITCH_STATUSES = {ACTIVE, REVOKED}`.
`_require_legal_transition` enforces the identical genesis/successor/terminality discipline
`runtime.transition_chain` establishes for its own chains, self-contained here for a single,
project-scoped pointer (exactly one kill switch per project, so no per-target chain-key map is
needed):

```text
no current record            -> only generation=0, predecessor_ref=null, status=ACTIVE admitted
current record REVOKED       -> terminal: no successor and no ancestor replay ever admitted again
current record ACTIVE        -> proposed.predecessor_ref.id must equal the current record's own id
                                 proposed.generation must equal current.generation + 1
```

**Signing/verification split.** `kill_switch.py` holds no private key and mints no signature of
its own -- it only ever verifies, via `binding.signature.verify_ed25519_signature`, the identical
separation `runtime.admission_registry`/`runtime.root_admission` already keep between minting and
verifying. `commit_change_executor_kill_switch(store, project_id, kill_switch, *,
trust_anchor_public_key_hex, committed_at)` requires: a non-empty `trust_anchor_public_key_hex`
supplied by the deployment/composition boundary itself (never read from the Store being admitted,
never derived from anything on the request path); the proposed record's own recomputed identity/
fingerprint to equal its declared values; a `signature` block whose `algorithm ==
SUPPORTED_SIGNATURE_ALGORITHM` and whose `value` verifies, via `verify_ed25519_signature`, against
`trust_anchor_public_key_hex` over `kill_switch_signing_payload` (the identical bytes the id and
fingerprint themselves hash); and a legal chain transition from whatever is currently pointed to.
Only then does it commit the record **and** move the current-kill-switch pointer, atomically, in
one `commit_state_transition` call, inside a bounded (8-retry) Compare-And-Swap loop.

**Where the current pointer lives.** `semantic_state.deployment.claims
["CHANGE_EXECUTOR_KILL_SWITCH_CURRENT_ID"]` -- see §3 item 5 for why.

**Read paths.** `resolve_current_kill_switch` uses the Store's own read-only, quiescence-checked
`read_current_consistent` surface (appropriate for a check `route.py` performs twice per request,
including once before any Store commit has happened at all) and independently re-verifies the
resolved record's own identity/fingerprint before returning it. `require_active_kill_switch`
(exported for direct callers) and `route._require_active_kill_switch_verified` (used by
`route.py` itself, which additionally re-verifies the Ed25519 signature against the bound trust
anchor at every call, not merely at the record's own original commit time) both require the
resolved record to exist and be `ACTIVE`, refusing closed with zero adapter calls otherwise.

```text
KILL_SWITCH_STATUSES=ACTIVE,REVOKED
KILL_SWITCH_TRANSITION_MONOTONIC=true
KILL_SWITCH_REVOCATION_IS_TERMINAL=true
KILL_SWITCH_SIGNING_KEY_HELD_BY_THIS_PACKAGE=false
KILL_SWITCH_VERIFIED_AGAINST_AN_EXTERNALLY_SUPPLIED_ANCHOR=true
KILL_SWITCH_CHECKPOINTS_PER_REQUEST=2
KILL_SWITCH_SIGNATURE_REVERIFIED_AT_EVERY_ROUTE_CHECKPOINT=true
```

## 11. Disclosed judgment calls

Transcribed faithfully from the shipped module docstrings; every one below is stated, in full, in
the real code this document was written from.

1. **The return shape is a small envelope, not the bare receipt** (`route.py`, §2/§3 item 1
   above).
2. **`execution_started_at`/`execution_ended_at` both come from the one caller-supplied
   `execution_instant`** (`route.py`, §3 item 2).
3. **A kill-switch refusal at checkpoint #2, and a Boundary-limit violation discovered while
   building the operation, both produce a terminal receipt rather than a raised exception**
   (`route.py`, §3 item 2/§6 P18-C5).
4. **The best-effort rollback call is a second, distinct, explicitly policy-gated adapter call**
   (`route.py`, §3 item 3).
5. **The mapping slot IS the shared record id for all three request-scoped record kinds**
   (`identity.py`, §3 item 4/§9).
6. **Where the current-kill-switch pointer lives** -- the `"deployment"` domain's `claims` map,
   not a new top-level `semantic_state` domain this delivery is not permitted to add
   (`kill_switch.py`, §3 item 5/§10).
7. **Which Store read surface backs which call site** -- `read_current_consistent` for the
   twice-per-request resolve, `load_current` inside the Compare-And-Swap retry loop for the
   commit path itself, mirroring every other committer in this repository (`kill_switch.py`).
8. **A genuinely impure adapter is deliberately absent -- `ControlledFilesystemAdapter` performs
   real, ordinary filesystem I/O, never a network or subprocess call**, and the
   traversal/symlink-escape enforcement it performs is real, not decorative: absolute/`.`/`..`
   rejection before any filesystem touch, ancestor-symlink walking, existing-symlink-target
   refusal, and independent `Path.resolve()` containment as defense in depth (`adapter.py`).
9. **`worktree_root` is bound once at composition, never carried on the per-request
   `execute(...)` call** -- an automated review of PR #74 identified that a request-facing
   `worktree_root` was a genuine Boundary-binding gap, since every other trust-sensitive
   parameter this module uses was already bound once at composition (`route.py`, §3 item 6).
10. **A caller resuming its own crash-interrupted intent skips the staleness check for that one
    call** -- closes a real crash-recovery gap an automated review identified: a crash between
    the `execution_intent` commit and the following `execution_attempt` commit previously
    stranded the slot behind a spurious, permanent `StaleExecutionInputError` (`route.py`, §3
    item 7/§9).
11. **`execution_attempt` carries a fresh, per-call `attempt_nonce`** -- closes a genuine race an
    automated review identified, where two truly concurrent callers could both pass
    idempotency-slot resolution before either committed anything and both reach
    `adapter.execute`; the fix reuses the Store's own existing conflict detection rather than
    adding new Store-layer machinery, and deliberately leaves `execution_intent`'s own body
    untouched (`route.py`/`engine.py`/`identity.py`, §3 item 8).

## 12. Required proof layers

```text
V1                    deterministic identity and schema proof
V2                    Authority/Change continuity
V3                    non-skipped disposable worktree vertical
V4                    idempotency/concurrency/crash matrix
V5                    prohibited-scope and kill-switch matrix
V6                    tamper/substitution matrix
V7                    Kernel continuity
STATIC_CONFORMANCE    import-surface and side-effect-confinement proof
```

A full test suite now exists (§1): `tests/unit/change_executor/test_change_executor_identity.py`;
`tests/contract/change_executor/test_change_executor_static_conformance.py`;
`tests/integration/change_executor/test_change_executor_authority_continuity.py` (V2),
`test_change_executor_vertical_proof.py` (V3), `test_change_executor_idempotency_crash_matrix.py`
(V4), `test_change_executor_prohibited_scope_kill_switch.py` (V5),
`test_change_executor_tamper_substitution_matrix.py` (V6), and
`test_change_executor_kernel_continuity.py` (V7); plus two shared fixture modules,
`tests/fixtures/change_executor_world.py` and `tests/fixtures/change_executor_kill_switch_issuer.py`
(the latter a mint-only Ed25519 issuer, deliberately separate from `kill_switch.py`'s own
verify-only committer -- the identical issuer/verifier split Phase 17 Round 5 established). Final
run, with all three automated-review findings' own regression tests included (§1): **167
passed, 0 skipped, 0 failed** (`pytest tests/unit/change_executor/
tests/contract/change_executor/ tests/integration/change_executor/ -q`).

- **V1** (`test_change_executor_identity.py`, 65 tests) requires every identity this delivery
  mints -- `execution_intent_id`, `execution_attempt_id`, `change_execution_receipt_id`,
  `execution_boundary_fingerprint`, `kill_switch_id` -- to be deterministic and collision-sensitive
  to every one of its own semantic fields (parametrized field-by-field over every
  `*_SEMANTIC_FIELDS` tuple in §4.1, now including `execution_attempt`'s own `attempt_nonce` --
  §3 item 8), `execution_mapping_slot_key` to depend on exactly `(change_id,
  execution_boundary_fingerprint, adapter_identity_fingerprint)` and nothing else
  (`claim_token`/`requested_at`/`attempt_nonce` proven *not* to move it), and every record kind to
  schema-validate.
- **V2** (`test_change_executor_authority_continuity.py`, 21 tests) requires canonical
  Authority/Change evaluator reproduction (never a hand-forged decision -- built through the real
  `evaluate_authority`/`derive_change` route, `tests/change_helpers.route`/`tests/
  authority_helpers`), exact Change binding, and stale State/Authority refusal with decisive
  zero-call controls: a tampered Authority Decision, a tampered Change, a cross-project `change_id`,
  an out-of-Boundary `action_kind`, and every Human-only action kind are each refused with the
  bound counting adapter proven called exactly zero times.
- **V3** (`test_change_executor_vertical_proof.py`, 1 test, non-skipped) requires one authorized
  low-risk change performed on a real disposable worktree, independently re-observed, routed to
  existing Evidence/Reflow, and unable to self-close: a real `ControlledFilesystemAdapter` writes a
  real file to a real `tmp_path`, the returned receipt round-trips unchanged through
  `store.resolve_record`, `evidence_handoff.route_change_execution_to_evidence` genuinely derives
  an Evidence record from it with no mocking of the Evidence layer, and no `difference_event`/
  `closure_evaluation` record exists anywhere in the project's own Store.
- **V4** (`test_change_executor_idempotency_crash_matrix.py`, 11 tests) requires the exact-replay/
  conflicting-replay/concurrent-duplicate/crash/partial-failure/retry-refusal matrix §9 describes
  in full: exact replay returns the byte-identical receipt with the adapter called exactly once
  total across both calls; a mismatched `claim_token` against a terminal slot raises
  `ExecutionTerminalClaimMismatchError` unless `permit_semantic_reuse=True`; a directly-planted
  competing `execution_intent` raises `ExecutionConcurrentClaimError`; a directly-planted
  `execution_attempt` with no receipt raises `ExecutionReconciliationRequiredError`; a partial-
  failure adapter produces a terminal `PARTIAL_MUTATION`/`ROLLBACK_SUCCEEDED`/`ROLLBACK_FAILED`
  outcome that a second call then replays cleanly, adapter never called twice for the same slot.
  Two further tests prove the automated-review fixes directly (§3 items 7-8):
  `test_crash_between_intent_commit_and_attempt_commit_is_recoverable_via_resumed_retry` plants a
  bare `execution_intent` (no compensating headroom) and proves the identical retry resumes to a
  genuine `SUCCEEDED` receipt with the adapter called exactly once total, never
  `StaleExecutionInputError`; `test_two_racing_callers_for_the_identical_slot_call_the_adapter_at_
  most_once` drives a second, independent `execute()` call to full completion from inside the
  first caller's own idempotency-slot resolution (a real Store proxy, the identical technique
  V5's own `_RevokeOnFirstLoadCurrent` establishes), and proves exactly one of the two callers
  reaches a terminal `SUCCEEDED` receipt, the other raises `ExecutionConcurrentClaimError`, and
  one shared adapter instance's own `call_count` is exactly 1.
- **V5** (`test_change_executor_prohibited_scope_kill_switch.py`, 41 tests) requires the
  prohibited-scope and kill-switch matrix in full, including the two proof obligations P18-C8
  itself names explicitly: `test_pre_start_kill_switch_revocation_refuses_with_zero_adapter_calls`
  (a deterministic pre-start stop) and
  `test_mid_execution_kill_switch_revocation_produces_a_terminal_kill_switch_stopped_receipt` (an
  interruption at a safe mid-execution boundary, terminal `KILL_SWITCH_STOPPED` receipt, not a
  bare exception). Also: all thirteen `HUMAN_ONLY_ACTION_KINDS` parametrized against both
  `validate_execution_boundary` and `compose_change_executor` directly; the sibling-path-collision
  case (`docs` must not admit `docs-private/x.md`); a hand-built traversal path refused by
  `route.py`'s own admission check before the adapter is ever called; a real planted filesystem
  symlink refused by `ControlledFilesystemAdapter` directly (called with no `route.py` involved at
  all); all six fixed-`False` Boundary fields parametrized as refused when supplied `True`; no
  kill switch ever committed, a `REVOKED` kill switch, and a wrong-key-signed kill switch each
  refused (the last one refused by `commit_change_executor_kill_switch` itself, before it can ever
  become current).
- **V6** (`test_change_executor_tamper_substitution_matrix.py`, 7 tests) requires the
  tamper/substitution matrix: cross-project execution refused; two separate `FileStateStore`
  instances under the same `tmp_path` proven not to cross-resolve a Change/receipt; a mismatched
  `project_binding_id` refused by `boot_project` itself; a State transition that advances
  `state_revision` between Change derivation and `execute()` refused via
  `StaleExecutionInputError`; two closures composed with two different Boundaries against the
  identical project proven to admit different Changes; a mutated receipt copy refused by
  `evidence_handoff.route_change_execution_to_evidence`; two closures composed with two different
  `adapter_identity` values proven to produce two distinct mapping slots for the identical Change.
- **V7** (`test_change_executor_kernel_continuity.py`, 8 tests) requires that existing State,
  Authority, Change, Evidence, Boot, Binding, and Reflow owners remain singular, and that Phase 17
  (URL Boot) and Model/Agent Runtime remain untouched: an AST walk over every shipped module in
  `change_executor/` proves zero imports of `url_boot`, `model_runtime`, or `agent_runtime`; an AST
  walk proves `store.commit` is never called directly anywhere in this package (only through
  `commit_state_transition`); a full real vertical execution followed by a second, unrelated
  Change execution against the same project proves `state_revision` advances by exactly the number
  of State-mutating commits this package made, with every existing resolve-recompute-compare
  contract still holding for both.
- **Static conformance** (`test_change_executor_static_conformance.py`, 13 tests) requires
  side-effect imports and filesystem mutation confined to the adapter owner, with no arbitrary
  shell/remote-command surface, credential source, GitHub push/merge, deployment, direct
  State/Evidence write, dynamic tool dispatch, or self-approval route: no module in this package
  imports `socket`, `subprocess`, `urllib`, or `requests`, or mutates `os.environ`; the composed
  `execute` closure's own real parameter set (via `inspect.signature`, not AST) is exactly
  `{change_id, claim_token, execution_instant, permit_semantic_reuse}`, carrying no
  `store`/`project_id`/`project_binding_id`/Boundary/adapter/`worktree_root` parameter of any kind
  (§3 item 6); two further tests prove `worktree_root` moved to composition genuinely, not merely
  in the two static-shape checks above --
  `test_compose_change_executor_requires_worktree_root_to_be_an_existing_directory` proves
  composition itself refuses a non-existent directory, and
  `test_composed_execute_closure_rejects_a_worktree_root_keyword_argument` proves passing
  `worktree_root=` to the returned closure raises a genuine `TypeError`; no function
  anywhere in the shipped package accepts a parameter named `classify_resolved_address`,
  `perform_resolution`, `perform_connection`, `classify`, or any other generic policy-callable
  name; `route.py`'s own `__all__` is pinned to exactly `["compose_change_executor"]`; and
  `kill_switch.resolve_current_kill_switch` is confirmed to call `read_current_consistent`, never
  `load_current`, while its own committer and `route.py`'s own `_commit_records` correctly do call
  `load_current`, inside their own commit retry loops only.

## 13. Explicit non-claims

This delivery does **not** claim, and this document asserts none of the following as proven by a
passing test this delivery itself observed (§1):

- that a caller-supplied Execution Boundary is safe merely because it validates -- validation
  enforces the closed shape and the fixed-`False` policy fields; it does not itself reason about
  whether the *paths* a caller admits are wise ones for that caller's own repository.
- that this package defends against a TOCTOU filesystem race beyond the ordinary symlink and
  traversal checks `ControlledFilesystemAdapter` actually performs (§6 P18-C3/§11 item 8): a
  symlink swapped into place between the adapter's own ancestor-walk check and its own write, on
  a filesystem an adversary with local write access to the identical worktree controls
  concurrently, is not a scenario this adapter's synchronous, single-process checks are designed
  to close. What is proved is the ordinary, real defense every check performs at the moment it
  runs -- absolute/`.`/`..` rejection, ancestor-symlink refusal, existing-symlink-target refusal,
  and independent resolved-path containment -- not immunity to a concurrent, privileged local
  attacker racing the *same* worktree's own filesystem underneath it mid-execution. `worktree_root`
  now being bound once at composition (§3 item 6/§11 item 9) closes a different, genuine gap --
  a caller of one composed executor can no longer substitute an arbitrary *different* root per
  request, since every Change executed through it already shares that one composed executor's
  own bound Boundary's fixed `repository`/`branch` -- but this non-claim about a concurrent local
  attacker on the one bound root itself is unchanged and still holds in full.
- that this package's kill-switch mechanism is resistant to a compromised trust-anchor private
  key. `kill_switch.py` verifies a presented Ed25519 signature against whatever public key its
  own caller supplies as `trust_anchor_public_key_hex`; if that private key itself is
  compromised, a forged kill switch record becomes genuinely, correctly verifiable. This package
  makes no cryptographic-capability-security claim beyond what a correct Ed25519 verification
  against a caller-supplied public key can ever prove -- the identical limit every other signed
  chain in this repository (Runtime's own root-admission and declaration chains, in
  `10_RUNTIME/RUNTIME_CONTRACT.md`) already discloses for its own trust anchor.
- that a `change_execution_receipt` is itself sufficient Evidence, or that this package decides
  sufficiency at all -- `evidence_handoff.py` constructs `verification_result_provenance` and
  calls the existing `derive_evidence` owner; sufficiency, if any, is that owner's own decision,
  never this package's.
- that this package proves causality between the executed operation and any later observed
  effect, or that it establishes anything about the *correctness* of the Change it executes
  beyond faithfully performing the exact, prevalidated, bounded operation the Change's own
  `action.operation` names.
- that a rollback, when attempted, undoes every effect of a partial mutation -- `_attempt_
  rollback` deletes exactly the paths the primary call's own raw facts say it wrote; it performs
  no compensating action for anything else a partially-completed write might have changed (a
  directory it created along the way, for instance) beyond the specific files named.
- that this delivery's own test suite (167 tests, §12) constitutes Structural Review: every
  citation above is to a test this delivery itself wrote and observed passing against the real
  shipped code -- including the regression tests an automated PR review's three findings
  prompted (§1/§3 items 6-8/§11 items 9-11) -- but none of it is independent review by the
  adopting Structural Advisor, which `STRUCTURAL_REVIEW_ROUNDS_APPLIED=0` (document header)
  already discloses.

## 14. Gate 18

```text
GATE_18_CONTROLLED_AUTONOMOUS_CHANGE
  AUTONOMY_BOUNDARY_EXPLICIT=true
  AUTHORITY_CHECK_BEFORE_EXECUTION=true
  PROHIBITED_SCOPE_BLOCKED=true
  STALE_AUTHORITY_BLOCKED=true
  EXECUTION_IDEMPOTENCY_DEFINED=true
  AGENT_CANNOT_SELF_CLOSE=true
  REOBSERVATION_REQUIRED=true
  HUMAN_KILL_SWITCH_PROVEN=true
  MERGE_ALLOWED=false
  ISSUE_CLOSE_ALLOWED=false
  PHASE_18_COMPLETE=false
  PHASE_19_ALLOWED=false
```

Every item above is now marked `true` on the strength of both the real shipped code and a real,
observed, passing test suite (§12), cited by module/function and test name throughout this
document: the Boundary is explicit and closed (§7), the Authority/Change check runs before any
Store commit or adapter call (§6 P18-C1/P18-C4), the prohibited-scope fields are schema-fixed and
asserted disjoint from Human-only action kinds (§7), staleness is checked and fails closed with
zero mutation (§6 P18-C4), the idempotency/mapping-slot state machine is fully defined and
mechanically enforced (§9), the executing code path can construct no Authority Decision, no
sufficient-Evidence verdict, and no closure of anything (§2 of `CHANGE_EXECUTOR_INDEX.md`, §6
P18-C8), and every committed outcome carries an embedded re-observation request routed to the
existing Evidence owner (§6 P18-C7).

**`HUMAN_KILL_SWITCH_PROVEN` is now marked `true`.** An earlier draft of this document marked it
`false`, honestly, because Issue #73 phrases this specific item as a *proof* obligation --
explicitly, "a deterministic pre-start stop **and** an interruption at a safe mid-execution
boundary" (P18-C8) -- and no test suite existed yet to cite as having demonstrated either. Both
now exist and pass:
`test_pre_start_kill_switch_revocation_refuses_with_zero_adapter_calls` and
`test_mid_execution_kill_switch_revocation_produces_a_terminal_kill_switch_stopped_receipt`, both
in `tests/integration/change_executor/test_change_executor_prohibited_scope_kill_switch.py` (§12).
`MERGE_ALLOWED`/`ISSUE_CLOSE_ALLOWED`/`PHASE_18_COMPLETE`/`PHASE_19_ALLOWED` remain `false`
regardless -- Gate 18 alone does not authorize any of the four; those remain SHUKOU's own
Structural-Review-gated decisions.
