# Human Wait-Time Transparency Contract (Issue #22)

```text
DOC_TYPE=WORK_TIME_TRANSPARENCY_CONTRACT
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=WORK-TIME-TRANSPARENCY-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
GOVERNING_ISSUE=#22
ADOPTION_ID=ADOPT_ISSUE_22_HUMAN_WAIT_TIME_TRANSPARENCY_VERTICAL
STRUCTURAL_REVIEW_ROUND_1_ADOPTION_ID=ADOPT_P84_R1_F1_F6_HUMAN_WAIT_TIME_TRANSPARENCY_CORRECTION
AUTHORIZED_BASE_MAIN_SHA=279572fb51775bd8a13665376aa751a63c1d0c35
NEW_SCHEMA_COUNT=3
SCHEMA_COUNT_BEFORE=86
SCHEMA_COUNT_AFTER=89
```

This document's §2, §3(5), §5, §6 (WTT-C2/C3), §9, §11, §13, and §14 below restate the vertical's
own **corrected** after-state, per Structural Review Round 1 (`ADOPT_P84_R1_F1_F6_HUMAN_WAIT_TIME_
TRANSPARENCY_CORRECTION`) -- the Round 1 findings this document now reflects are P84-R1-F1 (8-of-8
real adapter integration), P84-R1-F2 (resolve-and-verify lineage), P84-R1-F3 (derived, never
caller-supplied, `is_material_reestimate`/`heartbeat_deadline_breached`, plus the opening-deadline
rule), P84-R1-F4 (one injected clock, read only by `with_work_time_coordination`, plus the real
in-flight `ProgressReporter` channel), P84-R1-F5 (the resolve-and-verify boundary is a genuine
production guarantee, not only a test-side fingerprint recomputation), and P84-R1-F6 (caller-input
detachment as the literal first operation, plus `adapter_kind`/`work_unit_ref.kind` binding). A
disclosed deferral in this document's own first draft (wiring only Boot's real production
entrypoint, with the other 7 proved only through a representative callable) does not override this
corrected after-state.

---

## 1. Position

Issue #22's own design document, `00_KERNEL/HUMAN_AGENT_WORK_COMMUNICATION.md`, already states the
Objective, the Required Start Notice, the Progress Heartbeat rule, the Estimate Revision rule,
the Terminal Notice vocabulary, and the Kernel Placement requirement. This contract does not
restate that design; it is the **closed schema and deterministic evaluator realization** of it --
the concrete answer to "what record kinds exist, what are their exact fields, what is their
identity/idempotency discipline, and how does every execution-capable adapter compose with it."

```text
CANONICAL_DESIGN_DOCUMENT=00_KERNEL/HUMAN_AGENT_WORK_COMMUNICATION.md
THIS_DOCUMENT_ADDS=CLOSED_SCHEMAS + DETERMINISTIC_IDENTITY + COORDINATION_ENGINE + ADAPTER_COMPOSITION + PROOF
```

## 2. Public signature

```python
# manosube_agent_civilization.work_time_transparency

def open_work_time_coordination(
    store, *, project_id, project_binding_id, work_unit_ref, adapter_kind,
    estimated_duration_lower_minutes, estimated_duration_upper_minutes, estimate_confidence,
    major_steps, next_progress_update_due_minutes, variability_factors, opened_at,
) -> dict: ...

def record_work_time_progress_update(
    store, *, project_id, project_binding_id, open_ref, predecessor_ref, sequence_number,
    position_kind, current_position, material_result_or_blocker,
    remaining_duration_unknown, revised_remaining_duration_lower_minutes,
    revised_remaining_duration_upper_minutes, human_action_required,
    next_progress_update_due_minutes, recorded_at,
) -> dict: ...

def record_work_time_terminal_notice(
    store, *, project_id, project_binding_id, open_ref, predecessor_ref, terminal_outcome,
    explanation, recorded_at,
) -> dict: ...

def with_work_time_coordination(
    store, *, project_id, project_binding_id, adapter_kind, work_unit_ref,
    estimated_duration_lower_minutes, estimated_duration_upper_minutes, estimate_confidence,
    major_steps, next_progress_update_due_minutes, variability_factors,
    perform: Callable[[ProgressReporter], T],
    clock: Callable[[], str] = default_clock,
) -> tuple[dict, dict, T]: ...
```

**Structural Review Round 1 (P84-R1-F2/F3/F4) signature corrections**, restated here since §2
above is a public interface a caller reads first: `record_work_time_progress_update` no longer
accepts `is_material_reestimate` (derived server-side, WTT-C4) and gained
`next_progress_update_due_minutes` (every heartbeat re-declares its own next deadline, WTT-C2).
`record_work_time_terminal_notice` no longer accepts `actual_elapsed_minutes` (derived server-side
from the resolved open record's own `opened_at` and this call's own `recorded_at`, P84-R1-F4).
`with_work_time_coordination` no longer accepts `opened_at`/`completed_at` at all -- it reads
exactly one injected `clock` (defaulting to `clock.default_clock`, the package's *only* real
wall-clock read) twice, and `perform` now receives one `ProgressReporter` (§9).

Every one of the first three calls `boot_project(store, project_id=..., project_binding_id=...)`
itself, fresh, on every invocation -- never accepts a pre-resolved `BootContext`. This is the
identical TOCTOU-closure discipline `change_executor/route.py` and `runtime/route.py` already
keep: a cached `BootContext` from an earlier call could silently authorize against a stale
Project Binding if the bound project changed underneath a long-lived caller between a
coordination's own `open` and its later `update`/`terminal` calls. As of Structural Review Round 1
(P84-R1-F6), each of the first three also calls `_detach(...)` on every caller-owned mutable
argument as its own literal first operation, before `boot_project` or anything else -- see §6
below and `test_every_public_route_entry_point_detaches_caller_input_before_boot_project`.

## 3. Frozen semantic decisions

1. **Three record kinds, not one.** `work_time_coordination_open` (the start estimate),
   `work_time_coordination_update` (heartbeat / re-estimate / external wait / blocker, unified
   under one kind discriminated by `position_kind`), `work_time_coordination_terminal` (the one
   terminal outcome). Unifying heartbeat/re-estimate/external-wait into one kind, rather than
   three, mirrors Issue #22's own text treating them as one evolving "Progress Heartbeat"
   concept with an optional re-estimate/wait payload, not three independent facts.
2. **Narrow, deterministic identity, not full content-addressing.** See §7.
3. **No `human_authority_ref`, no signature, on any of the 3 schemas.** A Work Coordination
   record is a first-class immutable Store record (so it gets the Store's own durability,
   replay, and conflict guarantees for free) but is deliberately never shaped like an Authority
   declaration (`change_executor_kill_switch`, `human_grant_declaration`) -- see §12.
4. **Minute-integer durations, never floating point.** The canonical serializer
   (`state.canonicalize._canonical_tree`) raises `UnsupportedValueError` on any Python `float`
   repository-wide; every duration/elapsed-time field in this vertical's 3 schemas is
   schema-typed `"type": "integer"`, and every Python builder/adapter type hint is `int`, not
   `float`. `adapters._elapsed_minutes` rounds a caller-supplied `(opened_at, completed_at)` pair
   to the nearest whole minute rather than reading a clock or emitting a fraction.
5. **Exactly one real wall-clock read in this whole package** (Structural Review Round 1,
   P84-R1-F4, correcting this decision's own original "this package reads no clock" claim, which
   was true only of `route.py`/`engine.py` themselves). `clock.default_clock` is the one function
   in the package that ever calls `datetime.now(UTC)`, and it is used only as
   `with_work_time_coordination`'s own default `clock=` argument -- always overridable by an
   injected deterministic clock, as every test in this vertical does. `route.py`/`engine.py`
   still never call `default_clock` themselves; they only ever convert an already-observed
   timestamp (e.g. deriving `actual_elapsed_minutes` from two already-observed timestamps, never
   reading a third).
6. **Composition over modification for adapter conformance.** See §11.

## 4. Canonical owner

### 4.1 Canonical records

| Kind | Id | Semantic fingerprint fields |
|---|---|---|
| `work_time_coordination_open` | `f(project_id, work_unit_ref)` | all 11 body fields (`OPEN_SEMANTIC_FIELDS`) |
| `work_time_coordination_update` | `f(open_id, sequence_number)` | all 14 body fields (`UPDATE_SEMANTIC_FIELDS`) |
| `work_time_coordination_terminal` | `f(open_id)` alone | all 8 body fields (`TERMINAL_SEMANTIC_FIELDS`) |

Every id is computed by `hashlib.sha256(canonical_json_bytes(payload)).hexdigest()`, using the
one canonical serializer (`state.canonicalize.canonical_json_bytes`) every other kernel package
already uses for its own identity -- never a bespoke hashing scheme.

### 4.2 The closed vocabularies

```text
ADAPTER_KINDS (8, index-matched to WORK_UNIT_REF_KINDS)
  CLI                        <-> cli_invocation
  BOOT                       <-> boot_session
  TEMPORARY_AGENT            <-> temporary_agent_session
  MODEL_RUNTIME              <-> model_runtime_work_unit
  MULTI_AGENT                <-> multi_agent_execution_plan
  CHANGE_EXECUTOR            <-> change_executor_execution
  INDEPENDENT_VERIFICATION   <-> independent_verification_run
  GITHUB_PROJECTION          <-> github_projection_attempt

ESTIMATE_CONFIDENCE_LEVELS   HIGH, MEDIUM, LOW
POSITION_KINDS                WORK_RUNNING, EXTERNAL_REVIEW_WAIT, BLOCKED, ERROR
TERMINAL_OUTCOMES             COMPLETED, BLOCKED_HUMAN_ACTION_REQUIRED, FAILED_RETRYABLE,
                               FAILED_TERMINAL, PAUSED_BY_HUMAN
```

`ADAPTER_KIND_TO_WORK_UNIT_REF_KIND` is built via `zip(ADAPTER_KINDS, WORK_UNIT_REF_KINDS,
strict=True)`, so the two tuples can never silently drift out of index-alignment -- a length
mismatch raises at import time, not at some later call site.

## 5. Canonical route

```text
open_work_time_coordination(...)
  -> _detach(work_unit_ref), _detach(major_steps)          (literal first operation, P84-R1-F6)
  -> validate adapter_kind against ADAPTER_KIND_TO_WORK_UNIT_REF_KIND[adapter_kind] == work_unit_ref.kind
  -> boot_project (fresh)
  -> build_work_time_coordination_open (pure builder, schema-validates)
  -> store.commit_coordination_record (Structural Review Round 2, P84-R2-F1/F4 -- the Store's
     own orthogonal coordination ledger, never commit_state_transition)
  -> return the committed record

record_work_time_progress_update(...)
  -> _detach(open_ref), _detach(predecessor_ref)           (literal first operation, P84-R1-F6)
  -> boot_project (fresh)
  -> _commit_tip_dependent (run once -- no Compare-And-Swap retry loop is needed under the
     orthogonal ledger; see Structural Review Round 2 below):
       resolve_open -> verify_binding_congruity -> refuse if a terminal already exists
       -> resolve_predecessor_at_sequence -> verify_predecessor_matches
       -> verify_monotonic_continuation
       -> derive is_material_reestimate, heartbeat_deadline_breached (never caller-supplied)
       -> build_work_time_coordination_update (pure builder, schema-validates,
          cross-validates remaining_duration_unknown against the two revised_remaining_duration_*
          fields)
       -> store.commit_coordination_record
  -> return the committed record

record_work_time_terminal_notice(...)
  -> _detach(open_ref), _detach(predecessor_ref)           (literal first operation, P84-R1-F6)
  -> boot_project (fresh)
  -> _commit_tip_dependent (run once -- see Structural Review Round 2 below):
       resolve_open -> verify_binding_congruity -> resolve_tip -> verify_predecessor_matches
       -> verify_monotonic_continuation
       -> derive actual_elapsed_minutes, heartbeat_deadline_breached (never caller-supplied)
       -> build_work_time_coordination_terminal (pure builder, schema-validates)
       -> store.commit_coordination_record
  -> return the committed record
```

**Structural Review Round 2 (P84-R2-F1/F4, `ADOPT_P84_PROJECT_STATE_ORTHOGONAL_COORDINATION_
REBIND`): persistence moved off `commit_state_transition` onto the Store's own orthogonal
coordination ledger.** Every commit above goes through
`FileStateStore.commit_coordination_record` -- a second, independent append-only lane living
entirely under this project's own `coordination/` directory (`coordination/ledger.jsonl` as the
authoritative, full-body append-only log; `coordination/records/<kind>/<id>.json` as a
materialized, resolve-time-convenient cache always reproducible from the ledger alone) -- never
through `commit_state_transition`/`store.commit`, which this package no longer calls at all. No
code path here ever reads or advances `state_revision`, `semantic_fingerprint`, or
`lineage_head_ref`, and no coordination commit ever stages, reads, or writes anything under
`state/`, `events/`, or Project State's own `records/`: this is structural, not conventional,
proven by `tests/integration/store/test_coordination_ledger.py`'s own
`test_no_coordination_commit_ever_touches_project_state` and by every adapter integration test's
own "no mutation beyond `coordination/`" proof. Because the ledger's own conflict check is keyed
purely on each record's own `(kind, id)` identity -- never on a Project-State revision unrelated
activity elsewhere could advance -- no Compare-And-Swap retry loop is needed for
`record_work_time_progress_update`/`record_work_time_terminal_notice` any more: a resolve-verify-
build-commit pass runs exactly once, and a genuine concurrent writer racing on the identical
coordination still fails closed immediately (`RecordConflictError`) rather than being silently
retried against a moving tip. The ledger reuses this project's own single exclusive Store lock
(the same lock `commit()` itself holds), so a coordination write can never interleave with a
concurrent Project State commit, nor with a concurrent coordination write from another process --
giving every committed coordination record exactly one, unambiguous place in the ledger's own
single, total, append order. The ledger is crash-safe and replay-safe: same-body replay is
idempotent (no new ledger line, the already-committed body is simply returned), a same-identity/
different-body replay fails closed (`RecordConflictError`), a hand-edited ledger entry whose own
embedded fingerprint no longer matches its own embedded body is refused (`CorruptStoreError`,
never silently trusted), and a crash strictly between the ledger append and a record's own
permanent-file materialization heals itself on the next resolve or commit of that identical id
(or via the explicit `FileStateStore.recover_coordination_ledger`).

**Structural Review Round 1 (P84-R1-F2/F5): resolve-and-verify lineage, not a trusted caller-
supplied record body.** `open_ref`/`predecessor_ref` are bare `{"kind": ..., "id": ...}` pairs;
every continuation resolves them from this project's own Store through
`work_time_transparency.verify`'s own canonical boundary (`resolve_open`,
`resolve_predecessor_at_sequence`, `resolve_tip`, `verify_predecessor_matches`,
`verify_monotonic_continuation`, `verify_binding_congruity`) before any record is built or any
commit is attempted -- a nonexistent open, a cross-project/cross-coordination predecessor, a
skipped/reordered/forked sequence position, a terminal-before-open, an update-after-terminal, or a
non-monotonic continuation is refused *here*, so every refusal leaves the coordination ledger
untouched (nothing was ever committed) and never touches `state_revision` at all (Structural
Review Round 2: no path here reaches Project State). An Update's own predecessor must be whatever
record genuinely sits at `sequence_number - 1` (`resolve_predecessor_at_sequence` -- correct for
both a new sequence position and an exact replay, since the tip has moved on by the time of a
replay but the replay's own original predecessor never changes); a Terminal Notice's own
predecessor must always be the coordination's current live tip (`resolve_tip` -- unaffected by
that distinction, since nothing after a terminal can ever move the tip further).

`_commit_tip_dependent` (Structural Review Round 2) runs this whole resolve-verify-derive-build
sequence exactly once, then commits the result through `store.commit_coordination_record`. No
Compare-And-Swap retry loop is needed (unlike the pre-Round-2 `commit_state_transition`-based
design this replaced): the ledger's own conflict check is keyed purely on the record's own
`(kind, id)` identity, never on a Project-State revision unrelated activity elsewhere could
advance, so nothing about this project's own coordination ledger ever goes stale out from under a
single pass. A genuine concurrent writer racing on the identical coordination is still caught, and
still fails closed rather than silently retried, by `commit_coordination_record`'s own same-id/
different-body `RecordConflictError` -- a real identity/content conflict or a genuine lineage/
validation refusal always propagates to the caller immediately.

## 6. WTT-C1 through WTT-C6

### WTT-C1 -- Closed start-estimate schema

`work_time_coordination_open` requires `estimated_duration_lower_minutes` /
`estimated_duration_upper_minutes` (non-negative integers, upper >= lower, enforced in
`build_work_time_coordination_open`), `estimate_confidence` (closed 3-value enum),
`major_steps` (non-empty array, 1-64 items), and `next_progress_update_due_minutes` -- Issue
#22's own "Required Start Notice" fields, verbatim.

### WTT-C2 -- Unified heartbeat / re-estimate / external-wait record

`work_time_coordination_update` carries `position_kind` (the 4-value closed enum distinguishing
ordinary progress from an external wait, a blocker, or an error), `current_position`,
`material_result_or_blocker`, `is_material_reestimate` (Structural Review Round 1, P84-R1-F3:
derived server-side in `route.py` from the resolved canonical predecessor, never a raw caller-
supplied boolean -- see WTT-C4), `remaining_duration_unknown` plus the two nullable
`revised_remaining_duration_*_minutes` fields (schema `oneOf null/integer`, and
`build_work_time_coordination_update` refuses a body where `remaining_duration_unknown` doesn't
agree with whether both bounds are null), `human_action_required`,
`next_progress_update_due_minutes` (every heartbeat re-declares its own next deadline; `route.py`
refuses one more than 10 minutes past this update's own elapsed-since-open time, restating Issue
#22's own opening-deadline rule at every subsequent heartbeat, P84-R1-F3), and
`heartbeat_deadline_breached` (also derived server-side -- see WTT-C5).

### WTT-C3 -- Exactly-one-terminal-outcome enforcement by construction

`work_time_coordination_terminal_id` is `f(open_id)` alone (§7). A second, differently-bodied
terminal notice for the identical coordination collides at the identical Store `(kind, id)` slot
and is refused by `RecordConflictError` -- "exactly one observable outcome" (Issue #22's own
phrase) is a structural property of the identity scheme, not a runtime check this package writes
itself. `terminal_outcome` is the closed 5-value vocabulary from Issue #22's own "Terminal
Notice" section, verbatim.

### WTT-C4 -- Material re-estimate rule, restated verbatim, derived not asserted

`is_material_reestimate` restates Issue #22's own "Estimate Revision" section exactly: a
remaining-range change of >= 5 minutes on either bound, OR the upper bound expanding by >= 50
percent, OR a new blocking dependency appearing. A transition into or out of "unknown remaining
duration" (`None` bounds) is always treated as material -- genuinely losing or regaining the
ability to bound remaining work is exactly the kind of change the rule exists to surface, even
though it isn't literally describable as a numeric range delta. Structural Review Round 1
(P84-R1-F3): `route.py` calls this function itself, against the resolved canonical predecessor's
own state, immediately before embedding the result in the built record -- a caller can no longer
simply assert `is_material_reestimate=True/False` and have it trusted.

### WTT-C5 -- Heartbeat-overdue detection, never enforcement, derived not asserted

`is_heartbeat_overdue(opened_at_minutes, next_progress_update_due_minutes, now_minutes,
has_update)` is a pure, read-side, non-blocking observation: has the coordination's own deadline
passed with no update recorded yet? Detectable, never enforced -- Issue #22's own doctrine is
that silence must never be trusted as a health signal, not that silence must block anything this
package owns (§13 "no health claim"). `route.py` itself never refuses a late update or a
terminal notice on account of this function's result -- proved by
`test_a_late_heartbeat_past_its_own_due_deadline_is_still_accepted_and_recorded_but_marked_
breached`. Structural Review Round 1 (P84-R1-F3): every committed `work_time_coordination_update`
and `work_time_coordination_terminal` now carries its own `heartbeat_deadline_breached` boolean,
always server-derived, never caller-supplied -- durably observable per record, not only
computable on demand from two timestamps. The Terminal path uses `is_heartbeat_overdue` itself
(its "has any update arrived" read-side semantics fit a terminal observation); the Update path
uses a direct write-time comparison instead (`elapsed_since_open > previous_due_minutes`), since
`is_heartbeat_overdue` would vacuously return `False` for the very update that is itself arriving.

### WTT-C6 -- Adapter composition, not adapter modification

See §11.

### WTT-C7 -- Caller-input detachment and adapter/work-unit-kind binding

Structural Review Round 1 (P84-R1-F6). Every caller-owned mutable argument (`work_unit_ref`,
`major_steps`, `open_ref`, `predecessor_ref`) is deep-copied by `_detach(...)` as the *literal
first operation* of every one of the three public route entrypoints, before `boot_project` or
anything else -- proven structurally by an AST-based static-conformance test comparing the
string-index position of `_detach(` against `boot_project(` inside each function's own source
(`test_every_public_route_entry_point_detaches_caller_input_before_boot_project`), and behaviorally
by mutating a caller's own `work_unit_ref`/`major_steps` objects from inside a monkeypatched
`boot_project` and proving the committed record reflects only the pre-mutation values
(`test_mutating_caller_owned_inputs_while_boot_project_runs_never_reaches_the_committed_record`).
`open_work_time_coordination` additionally refuses an `adapter_kind` whose declared
`work_unit_ref.kind` (via `ADAPTER_KIND_TO_WORK_UNIT_REF_KIND`) does not match the caller-supplied
`work_unit_ref["kind"]` -- an adapter cannot open a coordination under a foreign work-unit kind,
even one that is itself a real, closed `WORK_UNIT_REF_KINDS` member
(`test_an_adapter_kind_bound_to_the_wrong_work_unit_ref_kind_is_refused`).

## 7. Deterministic narrow-key identity (the idempotency/replay/conflict mechanism)

Each kind's id is a pure function of **only the fields that identify "which coordination, at
which chain position"** a record is -- never its full body:

```text
work_time_coordination_open_id      = sha256(canonical_json({project_id, work_unit_ref}))
work_time_coordination_update_id    = sha256(canonical_json({open_id, sequence_number}))
work_time_coordination_terminal_id  = sha256(canonical_json({open_id}))
```

This is the identical mapping-slot-key technique `change_executor/identity.py`'s own module
docstring describes for its own `execution_intent`/`execution_attempt` ids. Because the id is
narrow, the Store's own **pre-existing** same-id-same-body replay tolerance and same-id-
different-body `RecordConflictError` refusal (`store/errors.py`) give this package, for free,
without any new mechanism:

- **idempotent replay** -- retrying the identical logical call (same estimate for the same work
  unit; the same heartbeat at the same sequence number; the same terminal outcome) returns the
  identical committed record;
- **conflict detection** -- a second, differently-bodied call at the identical identity slot
  (a different estimate for the same work unit; a conflicting update at the same sequence
  number; a second terminal outcome) is refused, never silently admitted as a coexisting second
  fact;
- **exactly-one-terminal enforcement** -- because the terminal id has no sequence number at all,
  there is structurally only one slot a terminal notice for a given coordination can ever
  occupy.

Each kind's own broader content (every field beyond the narrow identity key) is still fully
tamper-checked through that kind's own `*_semantic_fingerprint` function, embedded in the
committed record itself -- a hand-edited record no longer matches its own stored fingerprint
(`test_post_commit_tampering_a_hand_edited_record_no_longer_matches_its_own_stored_fingerprint`).

## 8. The closed schemas

Full field lists are in §6 above and in the schema files themselves
(`01_SCHEMA/work_time_transparency/*.schema.json`). All three set `additionalProperties: false`
and require `schema_version` (const `"0.1"`) plus their own id/fingerprint field. `open_ref`,
`predecessor_ref`, and `project_binding_ref` are all typed against the shared
`../common/reference.schema.json` with a `kind` constraint, not free-form strings --
`predecessor_ref` on both `update` and `terminal` accepts either `work_time_coordination_open`
or `work_time_coordination_update` as its kind, forming the chain each coordination's own
sequence of updates and final terminal notice link back through.

## 9. Adapter composition primitive

```python
def with_work_time_coordination(
    store, *, project_id, project_binding_id, adapter_kind, work_unit_ref,
    estimated_duration_lower_minutes, estimated_duration_upper_minutes, estimate_confidence,
    major_steps, next_progress_update_due_minutes, variability_factors,
    perform: Callable[[ProgressReporter], T],
    clock: Callable[[], str] = default_clock,
) -> tuple[open_record, terminal_record, T]:
```

Opens a Work Coordination, calls the caller-supplied `perform` (wrapping one real adapter
entrypoint call, unmodified, and receiving one `ProgressReporter` bound to the open coordination),
and closes the coordination: `COMPLETED` if `perform` returns, `FAILED_TERMINAL` if it raises --
the original exception is always re-raised unchanged after the terminal notice is durably
committed, never swallowed. This is the one shared composition point every adapter's own
`route.py` (or, in this delivery, this package's own conformance tests calling each adapter's real
production entrypoint directly) wraps a call through to get identical canonical timing semantics,
without this package importing or modifying that adapter's own code at all.

**Structural Review Round 1 (P84-R1-F4): one injected clock, read exactly twice by this function
itself.** `clock` (defaulting to `clock.default_clock`, this package's one real wall-clock read)
is called once to open (`opened_at`) and once immediately after `perform` returns or raises (the
terminal notice's own `recorded_at`); a terminal observation that is not at or after `opened_at`
raises `WorkTimeTransparencyClockError` rather than silently clamping a negative duration to zero.
`opened_at`/`completed_at` are no longer caller-supplied arguments at all.

**Structural Review Round 1 (P84-R1-F4): a real in-flight progress channel.** `ProgressReporter`
is bound to the open coordination (`store`/`project_id`/`project_binding_id`/`open_ref`/`clock`)
and tracks its own live tip; a real, possibly long-running adapter call receives one as `perform`'s
own argument and may call `.report(...)` zero or more times *while it is still running*, each call
posting one genuine, immediately-committed `work_time_coordination_update` through the identical,
fully-verified `record_work_time_progress_update` boundary -- so a coordination is no longer
limited to only an open and a terminal notice around one opaque, silent call. Proved against two
real adapters (Change Executor, Independent Verification), each posting one real in-flight
heartbeat mid-call and the resulting terminal notice's own `predecessor_ref` resolving to that
heartbeat (§11).

## 10. Kernel Placement continuity

Issue #22's own "Kernel Placement" section requires this contract to be "referenced by the
canonical execution entrypoint and by every adapter that can start work," with "the same fields
and timing rules" preserved regardless of adapter-specific UI formatting.
`test_every_declared_adapter_kind_composes_uniformly_through_the_shared_primitive` (parametrized
over all 8 `ADAPTER_KINDS`) proves the one shared primitive produces identical field shapes and
identical `COMPLETED`/`FAILED_TERMINAL` semantics regardless of which adapter kind is composing
through it.

## 11. Composition, not modification -- all 8 real adapters proved (Structural Review Round 1, P84-R1-F1)

`adapters.py` deliberately does not import CLI/Temporary Agent/Model Runtime/Multi-Agent/Change
Executor/Independent Verification/GitHub Projection and does not wrap their public entrypoints
itself, and never will. Doing so would make `work_time_transparency` a new upstream dependency of
7 unrelated, already-accepted, already-reviewed verticals' own `route.py` modules -- or force this
module to duplicate each one's own complex Authority/Boundary/Grant precondition chain -- which is
exactly the "second owner" duplication the adoption's own mandatory pre-design inventory instructs
against. What Structural Review Round 1 (P84-R1-F1) corrected was not this design decision, but
this document's own prior disclosure that only Boot's real production entrypoint was proved this
way, with the remaining 7 stood in only by an arbitrary representative callable.

**As of this correction, every one of the 8 `ADAPTER_KINDS` is proved through its own real,
completely unmodified production entrypoint**, called at its real entry boundary, over a real
`FileStateStore`, with that adapter's own real accepted precondition chain (a real bound Project,
a real committed Difference/Boundary/Grant, a real signed Human declaration, a real git worktree,
a real Ed25519 kill switch, a real `FakeGitHubAdapter`) -- never a dummy stand-in callable --
`tests/integration/work_time_transparency/test_work_time_transparency_adapter_conformance.py`:

1. **Boot** -- `boot_project`, wrapped end to end (success and a real `boot_project` failure
   producing a `FAILED_TERMINAL` notice with the original exception still propagating).
2. **CLI** -- the real `cli.main.run(["boot", ...])` entrypoint, over the identical fixture world
   `tests/integration/cli/test_cli_boot_command.py` itself proves against.
3. **Temporary Agent** -- `agent_runtime.start_temporary_agent`, returning a real `TemporaryAgent`
   whose own `boot_context` is asserted against the coordination's own `project_id`.
4. **Model Runtime** -- `model_runtime.open_model_work_unit`, against
   `tests/fixtures/model_runtime_world.py`'s own `authorized_world`/`open_kwargs` (a real
   Difference, Boundary, and genuinely Ed25519-signed Model Execution Grant), with the real
   `TemporaryAgent` started *inside* `perform` -- after the coordination's own open record has
   already committed -- so the Agent's own Boot-observed State exactly matches what
   `open_model_work_unit`'s own live-contract check requires.
5. **Multi-Agent** -- `multi_agent.open_dynamic_execution_plan`, against
   `tests/fixtures/multi_agent_world.py`'s own `authorized_world`/`open_plan_kwargs`, the identical
   just-in-time-Agent pattern as Model Runtime.
6. **Change Executor** -- `change_executor.compose_change_executor(...)(...)`, against a real git
   worktree (`tests/fixtures/change_executor_world.py`'s own `git_worktree`), a real committed and
   AUTONOMOUS Change (`build_committed_change`, built *inside* `perform` immediately before
   `execute()`, after a real in-flight `ProgressReporter.report()` heartbeat -- Change Executor's
   own preflight staleness check requires the Change to be authorized against the State exactly as
   it stands right before `execute()` runs), and a real, genuinely Ed25519-signed kill switch
   (`commit_active_kill_switch` + `tests/fixtures/change_executor_kill_switch_issuer.py`).
7. **Independent Verification** -- `independent_verification.run_independent_verification`,
   against a real committed `verifier_selection_grant` and a real, genuinely Ed25519-signed
   `human_grant_declaration` (via the real `binding.declare_human_grant` route), built using plain
   helper functions cross-imported directly from
   `tests/integration/independent_verification/test_run_independent_verification.py` (this
   vertical carries no dedicated `tests/fixtures/*_world.py` module of its own) -- also posting a
   real in-flight `ProgressReporter.report()` heartbeat mid-call.
8. **GitHub Projection** -- `projection.project_to_github`, against a real committed
   `observation_evidence` record (via the real `evidence.derive_evidence`), a real committed
   `github_projection_grant`, and a real, genuinely Ed25519-signed
   `github_projection_grant_declaration` (via the real `binding.declare_github_projection_grant`
   route), using the shipped `FakeGitHubAdapter` (never `RealGitHubAdapter`, whose network-write
   authority is explicitly withheld repository-wide) and plain helper functions cross-imported
   directly from `tests/integration/projection/test_project_to_github.py` (this vertical also
   carries no dedicated fixture-world module of its own).

Cross-importing a sibling test module's own plain (non-`pytest.fixture`-decorated) helper
functions, for exactly the two adapters with no dedicated `tests/fixtures/*_world.py` module, is a
disclosed departure from this repository's more common "promote to `tests/fixtures/` or duplicate"
convention -- justified because both precondition chains involve intricate, multi-step,
Ed25519-signed grant-and-declaration construction that would otherwise require ~100-150 lines of
near-duplicated fixture logic per adapter, for a UX/coordination-only concern that does not
warrant promoting either vertical's own test-internal helpers to a shared fixture module.

The uniform-composition proof
(`test_every_declared_adapter_kind_composes_uniformly_through_the_shared_primitive`, parametrized
over all 8 `ADAPTER_KINDS` with a representative callable) is retained alongside the 8 real-adapter
proofs above -- it proves the *shared primitive itself* behaves identically field-for-field across
every declared adapter kind, a distinct, still-useful property from "this adapter's own real
entrypoint composes correctly."

```text
REAL_ADAPTER_INTEGRATION_TESTS_REQUIRED=8_OF_8
FULLY_REAL_PRODUCTION_ENTRYPOINT_PROOFS=8_OF_8
UNIFORM_COMPOSITION_PROOFS=8_OF_8                (ALL ADAPTER_KINDS, shared-primitive proof, retained)
IN_FLIGHT_PROGRESS_CHANNEL_PROVEN_AGAINST_REAL_ADAPTERS=2   (CHANGE_EXECUTOR, INDEPENDENT_VERIFICATION)
```

## 12. Non-Authority / non-Evidence / non-Difference-closure boundary -- structural proof

Proved against the real production engines, not merely asserted in prose
(`tests/contract/work_time_transparency/test_work_time_transparency_non_authority_boundary.py`):

1. **No Authority shape.** None of the 3 schemas carry a `human_authority_ref` or signature
   field (`test_no_schema_carries_a_human_authority_ref_or_signature_field`, an
   `additionalProperties: false` schema check, not a convention).
2. **No Reflow/Difference reachability.** None of the 3 kinds are members of
   `reflow.reference_registry.STORE_OWNED_REFERENCE_KINDS`
   (`test_no_work_time_transparency_kind_is_a_store_owned_reference_target_for_reflow`). The
   real `reference_edges()` function fail-closed refuses (before any Store resolution) a real
   `closure_evaluation` or `difference_event` body that names a `work_time_coordination_*`
   reference in a field whose closed kind set does not include it
   (`test_reference_edges_refuses_a_closure_evaluation_pointing_change_result_evidence_at_a_terminal_notice`,
   `test_reference_edges_refuses_a_difference_event_pointing_evidence_refs_at_a_heartbeat_update`).
3. **No Evidence substitution path.** `evidence.engine.EVIDENCE_REFERENCE_KIND` is a fixed
   module constant, always `"observation_evidence"` -- there is no parameter through which a
   caller could substitute a `work_time_coordination_*` kind
   (`test_evidence_reference_kind_is_a_fixed_constant_never_a_work_time_transparency_kind`).
4. **No import path at all.** An AST-level static-conformance test proves every one of this
   package's own modules never imports `reflow`, `evidence`, `authority`, or `difference.graph`
   at all (`test_no_work_time_transparency_module_imports_reflow_evidence_authority_or_difference_graph`)
   -- a real closure over the package's own source, not only a naming convention.

```text
TIMING_RECORD_NE_PROJECT_EVIDENCE=true   (proven, item 3)
ESTIMATE_NE_AUTHORITY=true               (proven, item 1)
TIMING_EVENT_CANNOT_CLOSE_DIFFERENCE=true (proven, items 2 and 4)
TIMING_EVENT_CANNOT_CLOSE_ISSUE=true      (this package has no GitHub-facing surface at all)
TIMING_EVENT_CANNOT_AUTHORIZE_MERGE=true  (this package has no GitHub-facing surface at all)
CANONICAL_TIMING_OWNER_COUNT=1
PARALLEL_TIMING_AUTHORITY_COUNT=0
```

## 13. Required proof layers

```text
tests/unit/work_time_transparency/test_work_time_transparency_engine.py                68 tests
tests/contract/work_time_transparency/test_work_time_transparency_static_conformance.py 10 tests
tests/contract/work_time_transparency/test_work_time_transparency_non_authority_boundary.py 7 tests
tests/integration/work_time_transparency/test_work_time_transparency_natural_route.py   2 tests
tests/integration/work_time_transparency/test_work_time_transparency_negative_and_replay_matrix.py 23 tests
tests/integration/work_time_transparency/test_work_time_transparency_adapter_conformance.py 17 tests
tests/fixtures/work_time_transparency_world.py                                          1 fixture module
                                                                                TOTAL: 127 tests
```

- **Unit (68)** -- identity purity (same inputs -> same id, different inputs -> different id),
  schema round-trip validity for every kind (now including `next_progress_update_due_minutes`/
  `heartbeat_deadline_breached` on the Update schema and `heartbeat_deadline_breached` on the
  Terminal schema), per-field semantic-fingerprint sensitivity (parametrized: mutating any one
  semantic field changes the fingerprint), invalid-input refusal (bad enum values, upper < lower,
  `major_steps` empty, `remaining_duration_unknown` disagreeing with the nullable bound pair, an
  opening deadline more than 10 minutes past `opened_at` when the upper estimate exceeds 10
  minutes -- P84-R1-F3), the full 9-case `is_material_reestimate` matrix, `is_heartbeat_overdue`.
- **Contract / static conformance (10)** -- module inventory matches the shipped directory
  exactly (now including `clock.py`/`verify.py`); no network/subprocess/filesystem-I/O import;
  only `route.py` calls `commit_state_transition`; no module ever calls the raw `store.commit()`
  method; exactly 3 public route entrypoints; `__init__.py` re-exports exactly the public surface
  (now including `ProgressReporter`); every route function calls `boot_project` itself and accepts
  no `boot_context` parameter; every public route entrypoint calls `_detach(...)` before
  `boot_project(...)`, by source position (P84-R1-F6); both continuation entry points resolve and
  verify lineage through `verify.py`'s own canonical boundary, by source position (P84-R1-F2/F5);
  no schema carries `human_authority_ref`/signature.
- **Contract / non-Authority boundary (7)** -- §12 above.
- **Integration / natural route (2)** -- the full open -> heartbeat -> material-reestimate ->
  terminal chain against a real `FileStateStore`, proving each record resolves back out of the
  Store byte-identical to what was returned, that `state_revision` advances by exactly one per
  commit, and that `is_material_reestimate`/`actual_elapsed_minutes` are correctly derived rather
  than caller-supplied; a short-work zero-heartbeat direct open -> terminal path.
- **Integration / negative and replay matrix (23)** -- replaying an identical open/update/
  terminal call is idempotent; a differently-bodied retry at each of the three identity levels
  (open, update-at-sequence-N, terminal) is refused with `RecordConflictError`; two distinct
  work units produce two genuinely distinct coordinations; cross-project/cross-coordination
  predecessor substitution, a skipped sequence number, a forked predecessor off a stale tip,
  terminal-before-open, update-after-terminal, and a non-monotonic update/terminal time are all
  refused with `WorkTimeTransparencyLineageError` through the real public route boundary
  (P84-R1-F2/F5); a wrong-kind predecessor ref and a tampered predecessor ref id substituted for a
  real foreign record are refused; a late heartbeat past its own due deadline is still accepted
  and recorded, but marked `heartbeat_deadline_breached`; a terminal notice never requires any
  update to have been recorded first (the missing-heartbeat control); post-commit tampering is
  detectable via the semantic fingerprint; an adapter kind bound to the wrong `work_unit_ref.kind`
  is refused, and `state_revision` is proven unchanged; mutating a caller-owned
  `work_unit_ref`/`major_steps` while `boot_project` runs never reaches the committed record
  (P84-R1-F6).
- **Integration / adapter conformance (17)** -- §11 above (2 Boot tests, 1 uniform-composition
  test parametrized over all 8 `ADAPTER_KINDS`, and 7 new real-production-entrypoint tests for
  CLI/Temporary Agent/Model Runtime/Multi-Agent/Change Executor/Independent Verification/GitHub
  Projection).

## 14. Explicit non-claims

```text
SCHEDULER_IMPLEMENTED=false
PROGRESS_UI_IMPLEMENTED=false
NINTH_EXECUTION_ADAPTER_IMPLEMENTED=false
CLOCK_READ_BY_THIS_PACKAGE=1_FUNCTION_ONLY   (clock.default_clock; see §3 item 5, corrected P84-R1-F4)
WORK_TIME_TRANSPARENCY_IS_A_SECOND_STATE_OWNER=false
WORK_TIME_TRANSPARENCY_IS_A_SECOND_AUTHORITY_OWNER=false
WORK_TIME_TRANSPARENCY_IS_A_SECOND_EVIDENCE_OWNER=false
WORK_TIME_TRANSPARENCY_IS_A_SECOND_REFLOW_OWNER=false
WORK_TIME_TRANSPARENCY_IS_A_SECOND_BOOT_OWNER=false
WORK_TIME_TRANSPARENCY_DECLARES_COMPLETION=false
REAL_ADAPTER_INTEGRATION_TESTS_REQUIRED=8_OF_8
FULLY_REAL_PRODUCTION_ENTRYPOINT_PROOFS=8_OF_8_ADAPTERS   (corrected P84-R1-F1; see §11)
REMAINING_ADAPTER_ROUTE_PY_WIRING=NONE   (composition primitive, still never wired into another vertical's own route.py by design; see §11)
IS_MATERIAL_REESTIMATE_CALLER_SUPPLIED=false   (derived server-side; see WTT-C4, corrected P84-R1-F3)
HEARTBEAT_DEADLINE_BREACHED_CALLER_SUPPLIED=false   (derived server-side; see WTT-C5, corrected P84-R1-F3)
ACTUAL_ELAPSED_MINUTES_CALLER_SUPPLIED=false   (derived server-side from resolved open + recorded_at; corrected P84-R1-F4)
LINEAGE_TRUSTED_FROM_CALLER_BODY=false   (resolved and verified through verify.py; see §5, corrected P84-R1-F2/F5)
HEARTBEAT_LATENESS_ENFORCED=false   (detected via is_heartbeat_overdue, never blocked; see WTT-C5)
```

No test suite existed for this vertical at the moment this document pair's first draft was
written -- confirmed absent by direct search immediately before writing. A full suite (6 test
files plus 1 fixture module, 101 tests, 0 skipped, 0 failed) was written and independently
verified at that first draft; Structural Review Round 1 (`ADOPT_P84_R1_F1_F6_HUMAN_WAIT_TIME_
TRANSPARENCY_CORRECTION`) required the corrections this document now reflects, growing the suite
to 127 tests (§13 above cites the current state by real file and test name).

## 15. Structural Review Round 3 -- coordination ledger closure (`ADOPT_P84_R3_COORDINATION_
LEDGER_CLOSURE`)

Structural Review Round 2's own orthogonal coordination ledger (§5) left four closure gaps the
Structural Advisor identified against the live head this vertical's own Round 2 delivery reached
(`cf3f6c079d66a92f95b3fedd0268891f41fb3502`): a caller-side resolve-then-commit sequence could
race a concurrent writer between its own outside-lock predecessor resolve and its own commit
(P84-R3-F1); a resolved coordination record's own materialized cache file was trusted directly,
without re-verification against the ledger's own authoritative fact, on every resolve after the
first (P84-R3-F2); a crash strictly mid-append could leave the ledger unreadable rather than
recoverable (P84-R3-F3); and the real production nested call from
`multi_agent.open_dynamic_execution_plan` into `model_runtime.open_model_work_unit` opened a
second, independent coordination root with no defined ownership relation to the outer one
(P84-R3-F4).

**P84-R3-F1 (atomic coordination-tip admission).** `FileStateStore.commit_coordination_record`
is replaced by `commit_coordination_record_at_tip(project_id, chain_id, kind, record_id, body, *,
expected_predecessor)`: under the project's own single exclusive lock, it re-derives *chain_id*'s
own actual current tip (the last ledger entry, by the ledger's own single append order, carrying
that `chain_id`) and requires it to equal *expected_predecessor* before admitting the new entry --
in the same atomic pass the entry is appended and materialized. A stale predecessor, resolved
correctly before another writer's commit but no longer current by the time this call runs, is
refused with the new `CoordinationTipConflictError`, regardless of whether the racing writes share
the same `(kind, record_id)` -- closing the update-vs-terminal race a same-id-only conflict check
could never see (their record ids differ by construction: `update_id` depends on
`sequence_number`, `terminal_id` does not). `route.py`'s three public entrypoints now thread
`open_id` as `chain_id` and their own already-resolved-and-verified `predecessor_ref` as
`expected_predecessor` for every commit, open included (`expected_predecessor=None` for a chain's
first entry).

**P84-R3-F2 (authoritative-ledger read verification).** `resolve_coordination_record` no longer
returns an on-disk cache file directly: every resolve re-derives this id's own unique
authoritative ledger fact, refuses (`CorruptStoreError`) a duplicate divergent ledger entry for
the identical `(kind, record_id)`, refuses an orphaned cache file with no ledger entry backing it
at all, and requires the materialized cache's own bytes to equal the ledger fact's own canonical
bytes exactly before returning it -- catching a schema-valid, internally self-consistent
substituted cache body the pre-Round-3 design's own direct-return fast path could never detect.

**P84-R3-F3 (interrupted-append recovery boundary).** The ledger append protocol assumes only
the file's own final line can ever be a torn write (append-only, `"ab"` mode never rewrites
earlier bytes): `_coordination_ledger_entries` silently excludes a trailing line with no
terminating `b"\n"` rather than raising `CorruptStoreError` for the whole file, while any
*earlier* malformed line is still genuine corruption and still refused. `_heal_coordination_
ledger_tail` physically truncates that incomplete trailing fragment -- called as the first step
of every coordination commit and of `recover_coordination_ledger` -- so a subsequent append can
never silently concatenate its own new content onto a torn write.

**P84-R3-F4 (nested coordination ownership).** `model_runtime.open_model_work_unit` gains one new
optional parameter, `joined_coordination: ProgressReporter | None = None`. Every existing
standalone caller (`joined_coordination=None`, the default) is unaffected -- it keeps opening and
closing its own independent coordination root exactly as before. `multi_agent.
open_dynamic_execution_plan`'s own nested call now passes its own bound `ProgressReporter` as
`joined_coordination`: `open_model_work_unit` then opens **no** coordination root of its own at
all, calling straight into its own body with the caller's already-open reporter. There is
therefore only ever the one coordination root a real nested invocation actually has -- no second
root, so no cycle between two roots and no orphan-parent substitution can ever arise, because no
second root is ever created to reason about.

**Required decisive tests (Structural Review Round 3).** `tests/integration/store/
test_coordination_ledger.py` (22 tests): the full Round 2 suite adapted to the new atomic
tip-guarded API, plus new coverage for a stale-predecessor refusal, a second-open-on-a-non-empty-
chain refusal, a barrier-controlled concurrent update-vs-terminal race admitting exactly one
winner (P84-R3-F1); a schema-valid substituted materialized cache refusal, a duplicate-divergent-
ledger-entry refusal, a tolerated duplicate-identical-entry, an orphaned-cache refusal (P84-R3-F2);
a torn trailing write excluded rather than treated as whole-file corruption, the next commit
healing that torn tail before appending its own new entry, `recover_coordination_ledger` healing
a torn tail directly, and a genuinely malformed *non*-trailing line still refused as corruption
(P84-R3-F3). `tests/integration/work_time_transparency/
test_work_time_transparency_adapter_conformance.py` gains one new real-production-nested-call
topology test (P84-R3-F4) that reads this project's own coordination ledger directly and asserts
the exact expected topology -- exactly one `work_time_coordination_open` record with
`adapter_kind == "MULTI_AGENT"`, zero with `adapter_kind == "MODEL_RUNTIME"` -- not merely that
the nested call succeeds.

```text
MERGE_ALLOWED=false
ISSUE_22_CLOSE_ALLOWED=false
PHASE_20_IMPLEMENTATION_ALLOWED=false
```

## 16. Structural Review Round 4 -- WTT join and ledger-recovery closure (`ADOPT_P84_R4_
WTT_JOIN_AND_LEDGER_RECOVERY_CLOSURE`)

Structural Review Round 3's own two designs -- the nested-join parameter (P84-R3-F4) and the
duplicate-tolerant ledger read (part of P84-R3-F2) -- each left a gap the Structural Advisor
identified against the live head Round 3 reached (`8df493b7d2f51923a05e516ea8d2eaea3231024b`):
`open_model_work_unit`'s own `joined_coordination` parameter was an ordinary public keyword
argument, checked only for `is not None`, reachable by any direct caller and satisfiable by a
duck-typed object or a genuine-but-unrelated reporter (P84-R4-F1); the coordination ledger
tolerated a byte-identical duplicate physical entry for the same `(kind, id)` as harmless, when
an authoritative append-only ledger must permit at most one publication fact per identity
(P84-R4-F2); and the required persistence-stage fault-injection matrix for the ledger itself had
not yet been built at all (P84-R4-F3).

**P84-R4-F1 (close the public nested-join bypass).** `open_model_work_unit`'s public signature no
longer accepts `joined_coordination` at all -- every call through the public entrypoint always
opens (and later closes) its own independent coordination root, unconditionally. The one
legitimate nested join (Multi-Agent's own already-open `MULTI_AGENT` coordination, joined by its
own nested Model Runtime call) is now reached exclusively through a new internal function,
`model_runtime.route._open_model_work_unit_joined`, which no public route parameter exposes a
path to. Even there, the passed reporter is never merely trusted: new
`work_time_transparency.adapters.verify_joined_coordination(store, reporter, *, project_id,
project_binding_id, expected_adapter_kind)` requires it to be a genuine `ProgressReporter`
instance (never a duck-typed substitute -- Python's `isinstance` cannot be satisfied by attribute
shape alone), bound to the identical `store` object, `project_id`, and `project_binding_id`, whose
own `open_ref` resolves (through this package's own canonical `resolve_open`/
`verify_binding_congruity` boundary) to a real, schema-valid, binding-congruent
`work_time_coordination_open` record carrying the expected `adapter_kind`, and whose coordination
has no terminal notice yet (`resolve_terminal_if_exists`). `ProgressReporter` gains three new
read-only properties -- `store`, `project_id`, `project_binding_id` -- alongside the existing
`open_ref`, so this verification never has to reach into the class's own private attributes from
outside the module.

**P84-R4-F2 (one authoritative publication per identity).** New `FileStateStore.
_coordination_ledger_match(kind, record_id, entries)` is the one shared boundary every duplicate-
detecting caller now goes through: it refuses (`CorruptStoreError`) as soon as more than one
physical ledger entry claims the identical `(kind, record_id)`, divergent or byte-identical alike
-- retracting Round 3's own "an identical duplicate is harmless" position. `commit_coordination_
record_at_tip`'s same-body-replay/conflict check, `resolve_coordination_record`, and `recover_
coordination_ledger`'s own pre-healing duplicate scan all resolve through this identical helper,
so a corrupted duplicate is refused consistently across every read and write path, never silently
resolved through in one direction while refused in another.

**P84-R4-F3 (complete persistence-stage fault injection).** `commit_coordination_record_at_tip`
gains an optional `fault: FaultInjector | None = None` parameter -- the identical mechanism
`FileStateStore.commit` already exercises against its own `STAGES` -- threaded through a new
`COORDINATION_STAGES` tuple of seven named boundaries: `BEFORE_APPEND`, `DURING_PARTIAL_APPEND`,
`AFTER_COMPLETE_LINE_BEFORE_FILE_FSYNC`, `AFTER_FILE_FSYNC_BEFORE_DIRECTORY_FSYNC`,
`AFTER_DURABLE_LEDGER_PUBLICATION` (all inside `_commit_coordination_ledger_line`, which now
writes each line in two physical `write` calls specifically so `DURING_PARTIAL_APPEND` names a
real boundary between genuinely separate on-disk byte states, not a hook around one atomic call),
and `DURING_MATERIALIZATION`/`AFTER_MATERIALIZATION` (inside `_materialize_coordination_record`,
fired only when a new cache file is actually about to be written).

**Required decisive tests (Structural Review Round 4).** `tests/integration/store/
test_coordination_ledger.py` gains: a duplicate-identical-entry refusal on resolve (replacing
Round 3's own tolerance test), the identical refusal on `recover_coordination_ledger`, on a
subsequent same-body commit, and on a subsequent conflicting commit (P84-R4-F2); and one
`pytest.mark.parametrize`d test iterating all seven `COORDINATION_STAGES`, each injecting a real
`SimulatedCrash` through the actual commit path, then restarting through a fresh `FileStateStore`
instance to prove: the previously committed prefix remains readable, the attempted record is
deterministically either absent or committed per the declared commit point, `recover_
coordination_ledger` never raises and never changes that verdict, Project State remains
byte-identical throughout, and a retry never duplicates the ledger publication (P84-R4-F3).
`tests/integration/work_time_transparency/test_work_time_transparency_adapter_conformance.py`
gains six negative controls against `_open_model_work_unit_joined`: a fake duck-typed reporter, a
cross-project reporter, an unrelated genuine reporter (opened under a different `adapter_kind`), a
terminal coordination, a replayed reporter captured from an earlier, finished invocation -- each
refused with `WorkTimeTransparencyLineageError` -- and one proving the public
`open_model_work_unit` raises `TypeError` for a `joined_coordination` keyword argument it no
longer accepts at all (P84-R4-F1).

```text
MERGE_ALLOWED=false
ISSUE_22_CLOSE_ALLOWED=false
PHASE_20_IMPLEMENTATION_ALLOWED=false
```
