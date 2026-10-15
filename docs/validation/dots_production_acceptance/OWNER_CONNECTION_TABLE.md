# WU1: Implementation Connection Table

Tracks #116 / PR #117. Read-only investigation + design document; no code, no live
launch, no credential/billing/VPS change, no merge. Baseline SHA for every citation
below: `e320bc3bd1102c9fdb56c8657ea13b66252effc1` (the SHA PROTOCOL.md itself pins).

This table corrects two characterizations in PROTOCOL.md §1 where the actual source
disagrees with the summary that document gave; corrections are marked **[corrected]**.

## Boot, Store-recovery, and external-side-effect reconciliation are three separate processes

Per the Issue's own instruction ("Boot、Store復旧、外部副作用の照合を別処理として定義する"),
these three are never collapsed into one check in WU2:

1. **Boot** (`boot/route.py::boot_project`) — reconstructs a `BootContext` (the real,
   Store-verified `human_authority_ref` and `project_binding`) for an *already-bound*
   project. It performs no repair and commits nothing; a missing/tampered binding raises
   `BootNotFoundError`/`BootConsistencyError` and propagates unchanged.
2. **Store recovery** — `store.load_current(project_id)` / `store.read_current_consistent(...)`
   re-read the Store's own on-disk canonical state after a crash; `recover_coordination_ledger`
   (`store/file_store.py:695`) heals a torn Work-Time-Coordination ledger tail specifically.
   None of these contact any external system.
3. **External-side-effect reconciliation** — a WU2-built step, not an existing owner:
   independently re-reading the actual external system (GitHub API state of a PR/commit, or
   whatever dots control surface is in use) and comparing it against what the canonical
   Store believes happened. See `MEASUREMENT_CONTRACT.md` §A for the exact two-part gate.
   **No path may resend a change while this third step's outcome is unknown** — this is
   the binding invariant case `COMMIT_ACK_UNKNOWN`/`TRANSPORT_OUTAGE` in `case-catalog.json`
   already require.

## Connection table

| Stage | Real function (file:line) | Inputs (key fields) | Output | Commits to Store? | Next consumer |
|---|---|---|---|---|---|
| **Binding** | `binding/route.py::bind_project` | `project_id`, Objective Revision, Boundary, Authority Rule/policy ref, Source Registrations, Command Policy, secret-exclusion policy, `human_authority_ref`, `human_authority_signing_key`, genesis state | `{"project_binding_id", "committed_state", ...}` | Yes — `store.initialize` (genesis) | `boot_project` (every later call); `declare_human_grant` for any grant needing this binding |
| **Boot** | `boot/route.py::boot_project(store, *, project_id, project_binding_id)` | project/binding identity only | `BootContext` (`human_authority_ref`, `project_binding`, deep-frozen) | No | `run_independent_verification`, `authenticate_bounded_review_grant`, any route needing the real signing key or Human Authority ref |
| **Observation** | `observation/engine.py::observe(request)` | `{"normalization_profile", "scope", "project_id", "target_identity", "state_revision_observed", ...}` — pure, deterministic, over explicit fixture facts (predicate vocabulary closed to `equals@v1`/`exists@v1`/`members@v1`, `normalization.py:30`) | `dict[str, list[dict]]` of normalized facts | No | `derive_differences` |
| **Difference** | `difference/engine.py::derive_differences(request)` (`engine.py:1556`) | a derivation request bundle (Objective Revision, Observation results, prior State) | Difference genesis records + the exact input records a cross-record validator needs | No (pure derivation; genesis records persist only via the caller's own later `store.commit`/`bind_project`) | `evaluate_authority` / `evaluate_verifier_selection`; `run_independent_verification`'s `target_refs` |
| **Authority** | `authority/engine.py::evaluate_authority(request)` (`engine.py:296`) — general Authority Decisions. `authority/verifier_selection.py::evaluate_verifier_selection(request)` (`verifier_selection.py:228`) — the narrower decision `run_independent_verification` itself calls | content-addressed request; for verifier selection: project/requirement/selection/verifier-identity/permitted-boundary/grants/declarations/signing-key | Content-addressed `authority_decision`/`verifier_selection_decision` (`SELECTED`/`REFUSED`, deterministic id) | No (pure; the record is committed by whichever caller needs it persisted) | `compose_change_executor` (for an Authority Decision); `run_independent_verification` (for a Verifier Selection Decision) |
| **Execution (Change Executor)** | `change_executor/route.py::compose_change_executor(store, *, project_id, project_binding_id, execution_boundary, adapter_identity, adapter, kill_switch_trust_anchor_public_key_hex)` → returns a closure `execute(change_id, *, claim_token, execution_instant, ...)` (`route.py:963`, `route.py:1587`) | one already-AUTHORIZED, AUTONOMOUS, boundary-admitted Change; a human kill switch re-resolved **twice** (fresh, ACTIVE) at two separate checkpoints | `{"receipt": <change_execution_receipt>, "replay": bool, "semantic_reuse": bool}` — never a bare receipt **[corrected: PROTOCOL.md §1 said "許可された低リスク変更、実行receipt"; the real envelope is a 3-record commit chain, not one receipt]** | Yes — up to 3 records: `execution_intent` → `execution_attempt` → `execution_receipt`, outcome one of `SUCCEEDED / PARTIAL_MUTATION / ADAPTER_FAILURE / KILL_SWITCH_STOPPED / BOUNDARY_VIOLATION / UNKNOWN / REOBSERVATION_MISMATCH` | `evidence_handoff.py` → Evidence |
| **Evidence** | `evidence/engine.py::derive_evidence(request)` (public re-export `evidence/__init__.py`) | a Change-free or Change-grounded Evidence request (Observation/Difference/Change/VerificationResult provenance) | canonical, schema-validated `evidence` record (`EVIDENCE-<hash>`), one of `evidence_position ∈ {OBSERVATION_EVIDENCE, CHANGE_RESULT_EVIDENCE, CHANGE_FREE_VERIFICATION_EVIDENCE}` | No itself (pure derivation + internal schema validation); caller commits | `reflow` |
| **Reflow** | `reflow/route.py::reflow(store, *, project_id, closure_request, previous_event_id, event_revision, observation_refs, reflow_instant, ...)` (`route.py:1449`) | Evidence + closure request + prior event/revision identity | `{"evaluation", "decision", "next_semantic_state", "committed_state", "state_transition_ref", "event"}` | Yes — atomic State transition + Lineage append, **for every outcome alike** | the next Observation cycle (via `next_observation_ref`) |
| **Store recovery** | `store/file_store.py::FileStateStore.load_current` / `.read_current_consistent` / `.recover_coordination_ledger` (`file_store.py:695`) | `project_id` (+ ledger context for the coordination-specific recovery) | the Store's own current canonical state / a healed ledger tail | No new canonical content; read/repair only | any route needing a fresh, post-crash state read |

### Reflow's real outcome vocabulary **[corrected]**

PROTOCOL.md §1 says "FAILED/BLOCKEDも既存経路へ戻す" (FAILED/BLOCKED also route back
through the existing path). There is no outcome literally named `FAILED` in this
Kernel. `reflow/engine.py::decide_transition` maps to: `CLOSED` (from a `SATISFIED`
Evaluation), or `NOT_SATISFIED`, `BLOCKED`, `STALE`, `CONTRADICTED`, `REVOKED`. There is
also no *separate* "existing path" these non-`CLOSED` outcomes "return to" — they are
committed by the **identical** `reflow()` call, in the identical atomic-commit step, as
a `CLOSED` result. WU2's driver must record the exact outcome value, not a collapsed
"FAILED" bucket.

### Existing proof infrastructure this campaign reuses, not reinvents

- `tests/long_running_proof/` + `00_KERNEL/LONG_RUNNING_PROOF_CONTRACT.md` (Gate 20)
  already proves 10/30/50/100-cycle continuity, real two-process session-loss recovery
  (`session_loss.py::crash_mid_cycle_and_recover`, an unconditional `os._exit()` kill at
  one of 4 named boundaries), and ≥3 agent/runtime-identity swaps
  (`agent_swap.py`, reusing `model_runtime/route.py`'s `adapter_identity` +
  `record_model_swap`). Q3 (Agent交換) and parts of Q5 should drive these same
  harness primitives against a real dots-originated work unit rather than building new
  crash/swap mechanics.
- `examples/false_completion/PROTOCOL.md` already fully specifies (but has **not yet
  executed**) the exact 40-task × 3-repetition × independent-oracle × 8-stratum design
  Q4 reuses; this campaign's Q4 should literally extend that document's methodology
  (strata, paired repetitions, task-level cluster-bootstrap CI) rather than designing a
  second, parallel comparison methodology.
- `03_BINDING/DEVELOPMENT_BINDING_POLICY.json` (`policy_version 0.4`) confirms the real
  field is `executor_providers: ["CLAUDE_CODE", "GITHUB_COPILOT"]`
  (`executor_provider_selection_authority: "SHUKOU"`). `CODEX` is a distinct capability
  (`BOUNDED_TECHNICAL_REVIEWER`) explicitly barred from `IMPLEMENTATION`/`CODE_AUTHORSHIP`/
  `MERGE_OPERATION`/etc. `dots` is not a member of either set today — see
  `OPEN_ITEMS.md` for what adding it would require.
- `docs/bounded_technical_review.md` §4 / ADR-0032 already establish a ratified,
  code-pinned numeric-ceiling manifest shape (`bounded_review_numeric_limits`:
  concurrency/launches-per-day/process-seconds/poll-window/bytes/retries, with
  `additional_spending_ceiling` hardcoded to `0`). This campaign's own run-manifest
  (`RUN_MANIFEST_TEMPLATE.json`) is modeled on this shape rather than duplicating it —
  it governs a *different* resource budget (model-call spend across Q1–Q5), so it adds
  its own money/token ceilings rather than reusing the reviewer-launch ceiling verbatim.
