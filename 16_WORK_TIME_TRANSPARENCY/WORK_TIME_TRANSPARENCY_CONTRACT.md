# Human Wait-Time Transparency Contract (Issue #22)

```text
DOC_TYPE=WORK_TIME_TRANSPARENCY_CONTRACT
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=WORK-TIME-TRANSPARENCY-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
GOVERNING_ISSUE=#22
ADOPTION_ID=ADOPT_ISSUE_22_HUMAN_WAIT_TIME_TRANSPARENCY_VERTICAL
AUTHORIZED_BASE_MAIN_SHA=279572fb51775bd8a13665376aa751a63c1d0c35
NEW_SCHEMA_COUNT=3
SCHEMA_COUNT_BEFORE=86
SCHEMA_COUNT_AFTER=89
```

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
    position_kind, current_position, material_result_or_blocker, is_material_reestimate,
    remaining_duration_unknown, revised_remaining_duration_lower_minutes,
    revised_remaining_duration_upper_minutes, human_action_required, recorded_at,
) -> dict: ...

def record_work_time_terminal_notice(
    store, *, project_id, project_binding_id, open_ref, predecessor_ref, terminal_outcome,
    actual_elapsed_minutes, explanation, recorded_at,
) -> dict: ...

def with_work_time_coordination(
    store, *, project_id, project_binding_id, adapter_kind, work_unit_ref,
    estimated_duration_lower_minutes, estimated_duration_upper_minutes, estimate_confidence,
    major_steps, next_progress_update_due_minutes, variability_factors, opened_at, completed_at,
    perform: Callable[[], T],
) -> tuple[dict, dict, T]: ...
```

Every one of the first three calls `boot_project(store, project_id=..., project_binding_id=...)`
itself, fresh, on every invocation -- never accepts a pre-resolved `BootContext`. This is the
identical TOCTOU-closure discipline `change_executor/route.py` and `runtime/route.py` already
keep: a cached `BootContext` from an earlier call could silently authorize against a stale
Project Binding if the bound project changed underneath a long-lived caller between a
coordination's own `open` and its later `update`/`terminal` calls.

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
5. **This package reads no clock.** Every timestamp (`opened_at`, `recorded_at`, `completed_at`)
   is caller-supplied -- the identical discipline `change_executor/engine.py`'s own module
   docstring states for its own builders, and what makes every test in this vertical
   deterministic.
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
  -> boot_project (fresh)
  -> build_work_time_coordination_open (pure builder, schema-validates)
  -> _commit_records (commit_state_transition, bounded CAS retry, 8 attempts)
  -> return the committed record

record_work_time_progress_update(...)
  -> boot_project (fresh)
  -> build_work_time_coordination_update (pure builder, schema-validates,
     cross-validates remaining_duration_unknown against the two revised_remaining_duration_*
     fields)
  -> _commit_records
  -> return the committed record

record_work_time_terminal_notice(...)
  -> boot_project (fresh)
  -> build_work_time_coordination_terminal (pure builder, schema-validates)
  -> _commit_records
  -> return the committed record
```

`_commit_records` is the identical bounded Compare-And-Swap retry template
`change_executor/route.py`'s own `_commit_records` uses: on `StaleStateError` (another
transaction landed first) it re-reads `store.load_current` and retries, up to 8 attempts; a real
identity/content conflict (`RecordConflictError`) is never swallowed into a retry -- it always
propagates to the caller.

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
`material_result_or_blocker`, `is_material_reestimate` (a caller-computed flag, cross-checkable
against `is_material_reestimate()`, see WTT-C4), `remaining_duration_unknown` plus the two
nullable `revised_remaining_duration_*_minutes` fields (schema `oneOf null/integer`, and
`build_work_time_coordination_update` refuses a body where `remaining_duration_unknown` doesn't
agree with whether both bounds are null), and `human_action_required`.

### WTT-C3 -- Exactly-one-terminal-outcome enforcement by construction

`work_time_coordination_terminal_id` is `f(open_id)` alone (§7). A second, differently-bodied
terminal notice for the identical coordination collides at the identical Store `(kind, id)` slot
and is refused by `RecordConflictError` -- "exactly one observable outcome" (Issue #22's own
phrase) is a structural property of the identity scheme, not a runtime check this package writes
itself. `terminal_outcome` is the closed 5-value vocabulary from Issue #22's own "Terminal
Notice" section, verbatim.

### WTT-C4 -- Material re-estimate rule, restated verbatim

`is_material_reestimate` restates Issue #22's own "Estimate Revision" section exactly: a
remaining-range change of >= 5 minutes on either bound, OR the upper bound expanding by >= 50
percent, OR a new blocking dependency appearing. A transition into or out of "unknown remaining
duration" (`None` bounds) is always treated as material -- genuinely losing or regaining the
ability to bound remaining work is exactly the kind of change the rule exists to surface, even
though it isn't literally describable as a numeric range delta.

### WTT-C5 -- Heartbeat-overdue detection, never enforcement

`is_heartbeat_overdue(opened_at_minutes, next_progress_update_due_minutes, now_minutes,
has_update)` is a pure, read-side, non-blocking observation: has the coordination's own deadline
passed with no update recorded yet? Detectable, never enforced -- Issue #22's own doctrine is
that silence must never be trusted as a health signal, not that silence must block anything this
package owns (§13 "no health claim"). `route.py` itself never refuses a late update or a
terminal notice on account of this function's result -- proved by
`test_a_late_heartbeat_past_its_own_due_deadline_is_still_accepted_and_recorded`.

### WTT-C6 -- Adapter composition, not adapter modification

See §11.

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
    major_steps, next_progress_update_due_minutes, variability_factors, opened_at, completed_at,
    perform: Callable[[], T],
) -> tuple[open_record, terminal_record, T]:
```

Opens a Work Coordination, calls the caller-supplied zero-argument `perform` (wrapping one real
adapter entrypoint call, unmodified), and closes the coordination: `COMPLETED` if `perform`
returns, `FAILED_TERMINAL` if it raises -- the original exception is always re-raised unchanged
after the terminal notice is durably committed, never swallowed. This is the one shared
composition point every adapter's own `route.py` (or, in this delivery, this package's own
conformance tests calling each adapter's real production entrypoint directly) wraps a call
through to get identical canonical timing semantics, without this package importing or modifying
that adapter's own code at all.

## 10. Kernel Placement continuity

Issue #22's own "Kernel Placement" section requires this contract to be "referenced by the
canonical execution entrypoint and by every adapter that can start work," with "the same fields
and timing rules" preserved regardless of adapter-specific UI formatting.
`test_every_declared_adapter_kind_composes_uniformly_through_the_shared_primitive` (parametrized
over all 8 `ADAPTER_KINDS`) proves the one shared primitive produces identical field shapes and
identical `COMPLETED`/`FAILED_TERMINAL` semantics regardless of which adapter kind is composing
through it.

## 11. Disclosed judgment call: composition, not modification, for the other 7 adapters

`adapters.py` deliberately does not import CLI/Temporary Agent/Model Runtime/Multi-Agent/Change
Executor/Independent Verification/GitHub Projection and does not wrap their public entrypoints
itself. Doing so would make `work_time_transparency` a new upstream dependency of 7 unrelated,
already-accepted, already-reviewed verticals' own `route.py` modules -- or force this module to
duplicate each one's own complex Authority/Boundary/Grant precondition chain -- which is exactly
the "second owner" duplication the adoption's own mandatory pre-design inventory instructs
against, and unjustified risk to 7 already-accepted verticals for a UX/coordination-only
concern.

What is proved instead, for all 8 adapters:

1. **Boot** (`test_boot_the_one_real_unmodified_production_entrypoint_composes_end_to_end`,
   `test_a_failing_real_call_produces_a_failed_terminal_notice_and_the_original_exception_still_propagates`)
   -- a genuinely real, unmodified `boot_project` call, against a real `FileStateStore`, wrapped
   through `with_work_time_coordination`, proving both the success route (`COMPLETED`, the real
   `BootContext` returned to the caller unchanged) and the failure route (a real refusal from
   `boot_project` itself -- never a fabricated failure -- produces a `FAILED_TERMINAL` notice
   naming the real exception type, and the original exception still propagates to the caller).
   Boot was chosen for the fully-real proof because it has the shallowest precondition chain of
   the 8 (a Store plus a valid `project_id`/`project_binding_id` pair), making a genuine,
   unmodified round-trip feasible within this bounded work unit.
2. **All 8 `ADAPTER_KINDS`** (`test_every_declared_adapter_kind_composes_uniformly_through_the_shared_primitive`)
   -- the shared primitive itself behaves identically for every declared adapter kind, using a
   representative callable standing in for "one real adapter call" at the interface
   `with_work_time_coordination` actually composes against (an arbitrary zero-argument
   callable) -- the identical technique this repository's own adapter *Protocol* boundaries
   (`RuntimeAdapter`, `GitHubAdapter`) are proved against before a specific implementation is
   wired in.

**What is not yet delivered:** wiring each of the remaining 7 adapters' own `route.py` through
this primitive, with that domain's own full fixture world (a real Authority Rule, a real
Execution Boundary, a real Model Execution Grant, etc.), so that a caller of e.g.
`change_executor.open_execution_intent` or `model_runtime.observe_runtime_target` gets a Work
Coordination automatically rather than by explicit composition at the call site. This is this
delivery's own disclosed follow-up, not a hidden gap -- named here, in `adapters.py`'s own module
docstring, and in the adapter-conformance test file's own module docstring.

```text
FULLY_REAL_PRODUCTION_ENTRYPOINT_PROOFS=1_OF_8   (BOOT)
UNIFORM_COMPOSITION_PROOFS=8_OF_8                (ALL ADAPTER_KINDS, representative callable)
REMAINING_7_ADAPTER_ROUTE_PY_WIRING=DISCLOSED_FOLLOW_UP
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
tests/unit/work_time_transparency/test_work_time_transparency_engine.py                63 tests
tests/contract/work_time_transparency/test_work_time_transparency_static_conformance.py 8 tests
tests/contract/work_time_transparency/test_work_time_transparency_non_authority_boundary.py 5 tests
tests/integration/work_time_transparency/test_work_time_transparency_natural_route.py   2 tests
tests/integration/work_time_transparency/test_work_time_transparency_negative_and_replay_matrix.py 11 tests
tests/integration/work_time_transparency/test_work_time_transparency_adapter_conformance.py 12 tests
tests/fixtures/work_time_transparency_world.py                                          1 fixture module
                                                                                TOTAL: 101 tests
```

- **Unit (63)** -- identity purity (same inputs -> same id, different inputs -> different id),
  schema round-trip validity for every kind, per-field semantic-fingerprint sensitivity
  (parametrized: mutating any one semantic field changes the fingerprint), invalid-input
  refusal (bad enum values, upper < lower, `major_steps` empty, `remaining_duration_unknown`
  disagreeing with the nullable bound pair), the full 9-case `is_material_reestimate` matrix,
  `is_heartbeat_overdue`.
- **Contract / static conformance (8)** -- module inventory matches the shipped directory
  exactly; no network/subprocess/filesystem-I/O import; only `route.py` calls
  `commit_state_transition`; no module ever calls the raw `store.commit()` method; exactly 3
  public route entrypoints; `__init__.py` re-exports exactly the public surface; every route
  function calls `boot_project` itself and accepts no `boot_context` parameter; no schema
  carries `human_authority_ref`/signature.
- **Contract / non-Authority boundary (5)** -- §12 above.
- **Integration / natural route (2)** -- the full open -> heartbeat -> material-reestimate ->
  terminal chain against a real `FileStateStore`, proving each record resolves back out of the
  Store byte-identical to what was returned, and that `state_revision` advances by exactly one
  per commit; a short-work zero-heartbeat direct open -> terminal path.
- **Integration / negative and replay matrix (11)** -- replaying an identical open/update/
  terminal call is idempotent; a differently-bodied retry at each of the three identity levels
  (open, update-at-sequence-N, terminal) is refused with `RecordConflictError`; two distinct
  work units produce two genuinely distinct coordinations; cross-project substitution (a
  coordination opened in one Store/project is absent from another); a late heartbeat past its
  own due deadline is still accepted and recorded (never refused for lateness); a terminal
  notice never requires any update to have been recorded first (the missing-heartbeat control);
  post-commit tampering is detectable via the semantic fingerprint.
- **Integration / adapter conformance (12)** -- §11 above.

## 14. Explicit non-claims

```text
SCHEDULER_IMPLEMENTED=false
PROGRESS_UI_IMPLEMENTED=false
NINTH_EXECUTION_ADAPTER_IMPLEMENTED=false
CLOCK_READ_BY_THIS_PACKAGE=false
WORK_TIME_TRANSPARENCY_IS_A_SECOND_STATE_OWNER=false
WORK_TIME_TRANSPARENCY_IS_A_SECOND_AUTHORITY_OWNER=false
WORK_TIME_TRANSPARENCY_IS_A_SECOND_EVIDENCE_OWNER=false
WORK_TIME_TRANSPARENCY_IS_A_SECOND_REFLOW_OWNER=false
WORK_TIME_TRANSPARENCY_IS_A_SECOND_BOOT_OWNER=false
WORK_TIME_TRANSPARENCY_DECLARES_COMPLETION=false
FULLY_REAL_PRODUCTION_ENTRYPOINT_PROOFS=1_OF_8_ADAPTERS   (BOOT only; see §11)
REMAINING_7_ADAPTER_ROUTE_PY_WIRING=DISCLOSED_FOLLOW_UP
HEARTBEAT_LATENESS_ENFORCED=false   (detected via is_heartbeat_overdue, never blocked; see WTT-C5)
```

No test suite existed for this vertical at the moment this document pair's first draft was
written -- confirmed absent by direct search immediately before writing. A full suite (6 test
files plus 1 fixture module, 101 tests, 0 skipped, 0 failed) was written and independently
verified immediately afterward; §13 above cites it by real file and test name.

```text
MERGE_ALLOWED=false
ISSUE_22_CLOSE_ALLOWED=false
PHASE_20_IMPLEMENTATION_ALLOWED=false
```
