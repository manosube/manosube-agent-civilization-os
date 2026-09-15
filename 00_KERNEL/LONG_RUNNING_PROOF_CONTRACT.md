# Long-Running Proof Contract

## 0. Governing authority

```text
GOVERNING_ISSUE=#86
PHASE=20
PHASE_NAME=LONG_RUNNING_PROJECT_PROOF
ADOPTION_ID=ADOPT_PHASE_20_LONG_RUNNING_PROJECT_PROOF
DESIGN_OWNER=CHATGPT_STRUCTURAL_ADVISOR
IMPLEMENTATION_EXECUTOR=CLAUDE_CODE
```

This contract documents the proof `tests/long_running_proof/` implements against Issue #86's
own adopted Objective, Boundary, Required Evidence, and Gate 20 preservation. It does not
redefine canonical roadmap Gate 20 (`02_CANONICAL_ROADMAP.md`); it instantiates it.

## 1. Purpose

Prove, through the existing natural production routes only, that a long-running Project can
process many sequential Structural Differences while Canonical State and Lineage survive real
process/session loss, repeated Agent/runtime-identity swap, and runtime reachability
uncertainty -- without this proof becoming a second owner of Canonical State, Authority, Change,
Evidence, Reflow, or Completion.

## 2. Package layout

```text
tests/fixtures/long_running_proof.py         # deterministic, cycle-indexed fixture world
tests/fixtures/long_running_proof/*.txt      # 2 reused physical Source Snapshot files
tests/long_running_proof/cycle.py            # repeatable single-Difference natural-route cycle
tests/long_running_proof/session_loss.py     # real process-boundary restart + reconstruct()
tests/long_running_proof/agent_swap.py       # >=3 swaps / >=2 distinct adapter identities
tests/long_running_proof/runtime_reachability.py  # REACHABLE/UNREACHABLE/UNKNOWN measurement
tests/long_running_proof/metrics.py          # raw events + deterministic aggregator
tests/long_running_proof/orchestrator.py     # ties the above into one tier-parametrized run
tests/long_running_proof/test_long_running_proof_gate_20.py         # T10/T30/T50/T100
tests/long_running_proof/test_long_running_proof_negative_controls.py  # required control matrix
```

Nothing here lives under `src/manosube_agent_civilization/`: this proof creates no new
production package, no new schema family, and no new Canonical record kind
(`HARNESS_OWNS_CANONICAL_STATE=false`). It is proof/harness infrastructure, exactly the role
`00_KERNEL/VERTICAL_PROOF_CONTRACT.md` already establishes for Phase 8's own one-cycle proof --
this contract's own package is this repository's second, and last, instance of that role, one
level up in scale.

## 3. The repeatable cycle (`cycle.py`)

There is no single "process one Difference end-to-end" production entrypoint in this Kernel
(confirmed by inventory, not assumed): a caller composes `difference.derive_differences` ->
`authority.evaluate_authority` -> `change.derive_change` -> `observation.observe` /
`evidence.engine.derive_evidence` / `evidence.sufficiency.evaluate_sufficiency` ->
`reflow.route.reflow`, exactly as Phase 8's own `tests/natural_cycle/proof.py` already does for
one cycle. `cycle.py` generalizes that same composition to cycle index `k`, threading the
Store's own real `committed_state` (as `reflow()`'s own result returns it, or as a real Store
reconstruction returns it after a restart -- see section 5) from each cycle into the next.
`reflow()` itself always re-derives its own predecessor State via the Store
(`GENESIS_DANGLING_CANONICAL_REFERENCE_ALLOWED=false`-class discipline); this proof never
restates a predecessor State by hand.

One Objective Revision, declared once, carries all `MAX_CYCLES=100` Target Predicates up front
(`difference.engine.derive_differences` requires every bound predicate to already be declared);
T10/T30/T50/T100 are the first 10/30/50/100 entries of this identical, ordered predicate/subject
sequence -- literal prefixes of one corpus, never four independently generated or reshuffled
ones (`TIER_PREFIX_RELATION_REQUIRED=true`).

## 4. Session-loss recovery (`session_loss.py`)

Reuses the identical, already-accepted real-process-boundary restart precedent
`tests/integration/boot/test_boot_project_route.py::test_a_fresh_python_process_boots_
successfully` establishes: `subprocess.run([sys.executable, "-c", script], ...)`, never an
in-process stand-in. The child process reconstructs canonical State solely from the Store's own
on-disk files via `FileStateStore.reconstruct` -- the `CANONICAL_BOOT_OR_RECONSTRUCTION_
REQUIRED=true` alternative to a full `boot_project` call Issue #86's own Boundary explicitly
permits (this proof's fixture world admits no Project Binding, so a bare reconstruction is the
correct natural-route boundary here, not a shortcut around one).

Of the four session-loss boundaries Issue #86 names (work-unit-open-before-Change,
Change-admission-after-before-Evidence, Evidence-after-before-Reflow, Reflow-after-before-
terminal-projection): direct inspection of every owner `cycle.py` calls before `reflow()` shows
none of them ever calls `store.commit` (`topology.py`'s own K-003/R-001 static scan already
proves exactly one module in the installed package, `reflow/commit.py`, ever does). A crash at
any of the first three named boundaries is therefore, by construction, identical in observable
effect to a crash before `reflow()` was ever called for that cycle -- nothing durable exists yet
to reconcile, and the sound recovery is to re-derive the identical cycle and retry, which this
proof's own negative-control matrix proves cannot duplicate a commit (Reflow's own Compare-And-
Swap staleness refusal). The fourth boundary -- during/after Reflow's own atomic commit -- is
covered by this repository's own already-accepted `FaultInjectingStore`/`fault` seam and crash-
recovery test matrix (Phase 8, `tests/natural_cycle/proof.py`; PR #84 Round 4's 7-stage
coordination-ledger matrix is the same discipline applied to a different ledger); this proof
does not re-derive that matrix a second time for the identical Reflow commit path.

## 5. Agent/runtime-identity swap (`agent_swap.py`)

There is no canonical `AgentIdentity` record in this Kernel (confirmed by inventory): a
Temporary Agent's only distinguishing fact is which real `BootContext` it independently re-
verified. The one real, fail-closed "these are genuinely two different identities" mechanism is
Model Runtime's own `adapter_identity` field plus `record_model_swap`'s independent Store
re-resolution and same-identity refusal (`model_runtime/route.py`). This proof reuses the
already-accepted V3 model-swap vertical proof machinery
(`tests/fixtures/model_runtime_world.py`, `tests/integration/model_runtime/
test_model_swap_vertical_proof.py`) unchanged, driving >=3 swaps across >=2 distinct
`adapter_identity` values, each transition genuinely discarding the predecessor Agent's own
session (`AgentReleasedError` on reuse) before the successor Agent resumes from nothing but the
Store and the Work Unit's own content address.

## 6. Runtime reachability (`runtime_reachability.py`)

Reuses `runtime.route.observe_runtime_target` against the fixture/local `FakeRuntimeAdapter`
unchanged -- no new production provider or credential. `REACHABLE`/`UNREACHABLE`/`UNKNOWN` are
three genuinely distinct, never-conflated classifications derived from the adapter's own honest
transport-level outcome (`OBSERVED`/`TIMEOUT`-or-`UNAVAILABLE`/`NOT_FOUND`), never assumed from
repository or mock state (`RUNTIME_REACHABILITY_MEASURED_NOT_ASSUMED=true`,
`REPOSITORY_SUCCESS_NE_RUNTIME_SUCCESS=true`).

This proof deliberately does **not** wrap runtime observation in `with_work_time_coordination`.
`work_time_transparency.types.ADAPTER_KINDS` is a closed 8-member enum with no `RUNTIME` entry,
and `observe_runtime_target` itself never imports `work_time_transparency` (confirmed by
inspection). Minting a 9th kind, or reusing an unrelated one, would be an unauthorized Kernel
schema/enum change or a caller misrepresenting what kind of work opened; Issue #86's own
Boundary (`the harness may orchestrate and measure only`) is satisfied instead by treating
runtime reachability as un-coordinated, harness-owned diagnostic scaffolding.

## 7. Raw metric dataset and deterministic aggregation (`metrics.py`)

Every one of the 11 required metrics (`Issue #86` section 9) is recomputed by `metrics.
aggregate` from a plain `list[dict]` of raw events alone -- there is no orchestrator-private
running counter a caller without the raw events could not also reproduce
(`SUMMARY_DERIVABLE_FROM_RAW_DATA=true`). A zero denominator yields `None` (undefined), never a
silently substituted `0.0`/`1.0` (`ZERO_DENOMINATOR_HANDLING_DECLARED=true`). `UNKNOWN` runtime
observations are counted as `UNKNOWN`, never folded into `0` (`UNKNOWN_NE_ZERO=true`). A
`cycle_refused` raw event is never dropped from the dataset (`FAILURES_NOT_EXCLUDED_FROM_
DATASET=true`) -- the negative-control matrix proves this directly.

## 8. Orchestration (`orchestrator.py`)

`run_long_running_proof(tmp_path, tier=N)` is the one Gate 20 proof entry point: it runs `N`
sequential cycles (with real process-boundary session-loss restarts injected at ~25%/50%/75% of
the run), one agent/runtime-identity swap slice, and one runtime-reachability slice, then
aggregates every raw event. It owns no Canonical State/Authority/Evidence/Reflow/Completion
decision of its own -- every commit, decision, and terminal status is produced by the real owner
it called.

## 9. Gate 20

```text
LONG_RUNNING_STATE_CONTINUITY_PROVEN=true   (section 3 + section 8, all 4 tiers)
STATE_RECONSTRUCTION_REPEATABLE=true        (section 4, every session-loss boundary)
SESSION_LOSS_RECOVERY_PROVEN=true           (section 4)
AGENT_SWAP_REPEATEDLY_PROVEN=true           (section 5, >=3 swaps / >=2 identities per run)
RUNTIME_REACHABILITY_MEASURED=true          (section 6, all 3 classifications every run)
AUTHORITY_VIOLATIONS_RECORDED=true          (metrics.py's own authority_violation_count field;
                                              0 in the positive run, exercised by the negative-
                                              control matrix)
FAILURES_NOT_EXCLUDED_FROM_DATASET=true     (section 7, proven directly)

ALL_PROOF_TIERS_COMPLETE=true               (test_long_running_proof_gate_20.py, all 4 tiers)
NATURAL_ROUTE_PROVEN=true                   (sections 3-6, every mechanism reuses an existing,
                                              already-accepted public production entrypoint)
CANONICAL_OWNER_COUNT_UNCHANGED=true        (no new src/ package, no new schema family, no new
                                              record kind, no new adapter_kind)
```

Phase 20 is not complete until SHUKOU accepts the exact reviewed delivery head, that head is
merged, and resulting `main` is independently re-observed.

## 10. Explicit non-claims

```text
PHASE_21_COMPARATIVE_BENCHMARK=false
PHASE_22_V1_0_DECLARATION=false
NEW_CANONICAL_STATE_OWNER=false
NEW_AUTHORITY_OWNER=false
NEW_EVIDENCE_OWNER=false
NEW_REFLOW_OWNER=false
PRODUCTION_DEPLOYMENT=false
PRODUCTION_CREDENTIAL_USE=false
REMOTE_COMMAND_AUTHORITY=false
GITHUB_MERGE_OR_ISSUE_CLOSE_AUTOMATION=false
MERGE_ALLOWED=false
ISSUE_86_CLOSE_ALLOWED=false
PHASE_21_ALLOWED=false
```
