# Human Wait-Time Transparency Index (Issue #22)

```text
DOC_TYPE=WORK_TIME_TRANSPARENCY_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=WORK-TIME-TRANSPARENCY-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_CROSS_CUTTING_COORDINATION
CANONICAL_TIMING_OWNER_COUNT=1
PUBLIC_WORK_TIME_TRANSPARENCY_ENTRY_POINT_COUNT=3
ROADMAP_PHASE_ADDED=false
GOVERNING_ISSUE=#22
STRUCTURAL_REVIEW_ROUNDS_APPLIED=1
LATEST_ROUND_ADOPTION_ID=ADOPT_P84_R1_F1_F6_HUMAN_WAIT_TIME_TRANSPARENCY_CORRECTION
```

---

## 0. What this document is

This is the one entry point for the **Human Wait-Time Transparency** contract set -- the two
documents under `16_WORK_TIME_TRANSPARENCY/` that define how every execution-capable adapter in
this repository communicates work-time forecasts and progress to a waiting Human, without that
communication ever becoming Authority, Evidence, Difference closure, Issue closure, or project
completion.

```text
1. WORK_TIME_TRANSPARENCY_INDEX.md      (this document)
2. WORK_TIME_TRANSPARENCY_CONTRACT.md   the closed timing/status schemas, the deterministic
                                         coordination identity scheme, the material-reestimate
                                         rule, adapter composition, the disclosed judgment call,
                                         the required proof layers, and the explicit non-claims
```

This delivery's first draft was implemented under SHUKOU's formal adoption of the Structural
Advisor's rebind determination (`ADOPT_ISSUE_22_HUMAN_WAIT_TIME_TRANSPARENCY_VERTICAL`, Issue #22
comment
[5659817582](https://github.com/manosube/manosube-agent-civilization-os/issues/22#issuecomment-5659817582)),
against authorized base `main@279572fb51775bd8a13665376aa751a63c1d0c35` (the PR #83 / FD-0004
merge commit). `STRUCTURAL_REVIEW_ROUNDS_APPLIED=1`: SHUKOU's formal adoption of Structural
Review Round 1's 6 findings (`ADOPT_P84_R1_F1_F6_HUMAN_WAIT_TIME_TRANSPARENCY_CORRECTION`, PR #84
comment 5660679037, citing the Structural Advisor's review comment 5660655523) required the
corrections this document pair now reflects -- real adapter integration for all 8
`ADAPTER_KINDS` (not just Boot), resolve-and-verify lineage at the public route boundary, derived
(never caller-asserted) material-reestimate/heartbeat-breach/elapsed-time fields, a single
injected clock plus a real in-flight progress channel, and caller-input detachment as the literal
first operation of every public entrypoint.

Issue #22's own contract, `00_KERNEL/HUMAN_AGENT_WORK_COMMUNICATION.md`, already exists on
`main` and is not restated in full here; this document pair is the **closed schema,
deterministic evaluator, and adapter-conformance realization** of that design, which the prior
disposition (`CANONICAL_SCHEMA_PRESENT=false`, `COORDINATION_ENGINE_PRESENT=false`,
`ALL_EXECUTION_ADAPTERS_INTEGRATED=false`, `NATURAL_ROUTE_PROVEN=false`) found missing.

---

## 1. This is not a ninth Kernel element

`KERNEL_ELEMENT_COUNT=8` is unchanged. This package declares
`KERNEL_ELEMENT=NONE_CROSS_CUTTING_COORDINATION` -- the same `none`-style convention Boot, CLI,
Agent Runtime, Independent Verification, Projection, Runtime, URL Boot, and Change Executor
already use for adapter/coordination layers that are not one of the eight canonical Kernel
elements (State, Difference, Authority, Change, Evidence, Reflow, Binding, Boot).

What that means concretely: this layer mints no Authority, updates no canonical State's semantic
content beyond its own three new record kinds, proves no causality, establishes no sufficient
Evidence, closes no Difference, and declares no completion -- for any of the underlying project
work it is layered over. Its own three record kinds are its entire semantic footprint.

---

## 2. This is not a second State, Authority, Evidence, Reflow, Boot, or completion owner

| Existing owner | How this layer reaches it | What this layer never does |
|---|---|---|
| State / Store | `store.commit.commit_state_transition`, one call site shared by all 3 entrypoints (`route.py`'s own `_commit_records`, mirroring `change_executor/route.py`'s identical template) | never writes a file directly, never builds a second persistence path |
| Boot | `boot_project`, called fresh inside every one of the 3 public entrypoints, never cached across calls (TOCTOU closure) | never accepts a `boot_context` parameter anywhere in `route.py` (`tests/contract/work_time_transparency/test_work_time_transparency_static_conformance.py::test_route_module_boots_fresh_on_every_public_entry_point_never_caches_boot_context`) |
| Authority | not at all | this package imports no Authority evaluator; no schema carries `human_authority_ref` or a signature field (`test_no_schema_carries_a_human_authority_ref_or_signature_field`) |
| Evidence | not at all | `evidence.engine.EVIDENCE_REFERENCE_KIND` is a fixed constant (`"observation_evidence"`), never a `work_time_coordination_*` kind; this package never imports `evidence` at all |
| Reflow / Difference | not at all | none of the 3 new kinds are members of `reflow.reference_registry.STORE_OWNED_REFERENCE_KINDS`; `reference_edges()` fail-closed refuses a body that names one anyway; this package never imports `reflow`, `evidence`, `authority`, or `difference.graph` (AST-verified, not only a naming convention -- `tests/contract/work_time_transparency/test_work_time_transparency_non_authority_boundary.py`) |
| Completion | not at all | declares no completion, closes no Issue/Difference/PR; a `COMPLETED` terminal outcome is this package's own coordination-state fact about *its own* Work Coordination record, never a claim about the underlying project work's correctness |

```text
WORK_TIME_TRANSPARENCY_IS_A_SECOND_STATE_OWNER=false
WORK_TIME_TRANSPARENCY_IS_A_SECOND_AUTHORITY_OWNER=false
WORK_TIME_TRANSPARENCY_IS_A_SECOND_EVIDENCE_OWNER=false
WORK_TIME_TRANSPARENCY_IS_A_SECOND_REFLOW_OWNER=false
WORK_TIME_TRANSPARENCY_IS_A_SECOND_BOOT_OWNER=false
WORK_TIME_TRANSPARENCY_DECLARES_COMPLETION=false
```

---

## 3. This is not a scheduler, a progress UI, or a ninth execution adapter

No shell, subprocess, network, or credential surface is opened anywhere in this package
(`test_no_module_imports_a_network_subprocess_or_filesystem_i_o_surface`). Exactly one function in
this package ever reads the real wall clock -- `clock.default_clock`, used only as
`with_work_time_coordination`'s own default `clock=` argument, always overridable by an injected
deterministic clock (Structural Review Round 1, P84-R1-F4, correcting this section's own original
"this package reads no clock" claim); `route.py`/`engine.py` still never read a clock themselves,
only convert already-observed timestamps. It does not modify, wrap, or gate any of the 8 existing
execution-capable adapters' own route.py files; it composes with them from the outside, once,
through `adapters.with_work_time_coordination`.

```text
SCHEDULER_IMPLEMENTED=false
PROGRESS_UI_IMPLEMENTED=false
NINTH_EXECUTION_ADAPTER_IMPLEMENTED=false
CLOCK_READ_BY_THIS_PACKAGE=1_FUNCTION_ONLY
```

---

## 4. Canonical owner

### 4.1 The three public entry points

```text
open_work_time_coordination           Issue #22's own "Required Start Notice" -- commits one
                                       work_time_coordination_open record. Idempotent replay at
                                       the identical work_unit_ref; a differently-bodied retry
                                       collides and is refused.
record_work_time_progress_update      Issue #22's own "Progress Heartbeat" / "Estimate Revision"
                                       / "External Wait" sections, unified into one record kind
                                       discriminated by position_kind. Idempotent replay at the
                                       identical (open_id, sequence_number); a differently-bodied
                                       retry at that sequence number collides and is refused.
record_work_time_terminal_notice      Issue #22's own "Terminal Notice" -- the one
                                       work_time_coordination_terminal record a coordination will
                                       ever admit, enforced by construction (its id is a pure
                                       function of open_id alone).
```

Plus one composition primitive, not itself a fourth public route entrypoint:
`adapters.with_work_time_coordination` -- opens, calls a caller-supplied `perform` (receiving one
`ProgressReporter` for real in-flight heartbeats, Structural Review Round 1, P84-R1-F4) wrapping
one real adapter entrypoint call unmodified, and closes (`COMPLETED` on return, `FAILED_TERMINAL`
with the original exception re-raised on an unhandled exception).

### 4.2 The three new record kinds

```text
work_time_coordination_open       the start estimate: duration range, confidence, major steps,
                                   next-update-due. Id = f(project_id, work_unit_ref).
work_time_coordination_update     heartbeat / re-estimate / external wait / blocker, unified,
                                   discriminated by position_kind (WORK_RUNNING,
                                   EXTERNAL_REVIEW_WAIT, BLOCKED, ERROR). Id =
                                   f(open_id, sequence_number).
work_time_coordination_terminal   the one terminal outcome a coordination will ever have.
                                   Id = f(open_id) alone.
```

### 4.3 The closed vocabularies

```text
ADAPTER_KINDS         CLI, BOOT, TEMPORARY_AGENT, MODEL_RUNTIME, MULTI_AGENT, CHANGE_EXECUTOR,
                       INDEPENDENT_VERIFICATION, GITHUB_PROJECTION  (8, index-matched to
                       WORK_UNIT_REF_KINDS: cli_invocation, boot_session,
                       temporary_agent_session, model_runtime_work_unit,
                       multi_agent_execution_plan, change_executor_execution,
                       independent_verification_run, github_projection_attempt)
ESTIMATE_CONFIDENCE   HIGH, MEDIUM, LOW
POSITION_KINDS        WORK_RUNNING, EXTERNAL_REVIEW_WAIT, BLOCKED, ERROR
TERMINAL_OUTCOMES     COMPLETED, BLOCKED_HUMAN_ACTION_REQUIRED, FAILED_RETRYABLE,
                       FAILED_TERMINAL, PAUSED_BY_HUMAN   (Issue #22's own exact 5-value
                       vocabulary, verbatim)
```

See `WORK_TIME_TRANSPARENCY_CONTRACT.md` §7 for the full identity/idempotency discipline and §9
for the material-reestimate rule.

---

## 5. Explicit non-claims

Restated here so the index and the contract cannot drift; `WORK_TIME_TRANSPARENCY_CONTRACT.md`
§13 is the full list.

- This package creates no Authority, updates no canonical State's semantic content beyond its
  own three new record kinds, proves no causality, establishes no sufficient Evidence, closes no
  Difference, and declares no completion of the underlying project work -- structurally proven,
  not only documented (§2 above; `WORK_TIME_TRANSPARENCY_CONTRACT.md` §12).
- Adapter conformance is delivered as: a fully-real, unmodified-production-entrypoint proof for
  every one of the 8 declared `ADAPTER_KINDS` (Boot, CLI, Temporary Agent, Model Runtime,
  Multi-Agent, Change Executor, Independent Verification, GitHub Projection -- Structural Review
  Round 1, P84-R1-F1, `REAL_ADAPTER_INTEGRATION_TESTS_REQUIRED=8_OF_8`, superseding this
  delivery's own first draft, which proved only Boot this way), plus a retained
  uniform-composition proof that the one shared primitive (`with_work_time_coordination`) behaves
  identically for every one of the 8 declared `ADAPTER_KINDS`. Each real adapter's own substantial
  precondition chain (Authority Rules, Execution Boundaries, Model Execution Grants, kill
  switches, verifier selections, GitHub projection grants) is built genuinely -- real committed
  Differences/Boundaries/Grants, real Ed25519 signatures, a real git worktree -- through each
  adapter's own existing test-side fixture builders, never reconstructed from scratch or
  duplicated inside this package. `work_time_transparency` still never imports, wraps, or gates
  any of the 8 adapters' own `route.py` files -- this remains a deliberate, permanent design
  decision (§3 above), not something Round 1 asked to change; what Round 1 corrected was only
  this document's own prior disclosure of a narrower proof scope. See
  `WORK_TIME_TRANSPARENCY_CONTRACT.md` §11 for the full per-adapter account.
- This package never implements a scheduler, a progress UI, or a ninth execution adapter (§3).
- A `work_time_coordination_*` record is never treated, by this package or by any existing
  owner it touches, as sufficient Authority, Evidence, Difference closure, Issue closure, or
  merge authorization (§2 above).

```text
MERGE_ALLOWED=false
ISSUE_22_CLOSE_ALLOWED=false
PHASE_20_IMPLEMENTATION_ALLOWED=false
```
