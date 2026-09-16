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
tests/long_running_proof/crash_worker.py     # P87-R1-F1/F2: real subprocess crash/continuation worker
tests/long_running_proof/session_loss.py     # P87-R1-F1/F2: real two-process crash-and-recover
tests/long_running_proof/agent_swap.py       # >=3 swaps / >=2 distinct adapter identities
tests/long_running_proof/runtime_reachability.py  # REACHABLE/UNREACHABLE/UNKNOWN measurement
tests/long_running_proof/metrics.py          # raw events + deterministic aggregator
tests/long_running_proof/orchestrator.py     # ties the above into one tier-parametrized run
tests/long_running_proof/test_long_running_proof_gate_20.py         # T10/T30/T50/T100
tests/long_running_proof/test_long_running_proof_negative_controls.py  # required control matrix
tests/contract/long_running_proof_artifact/  # P87-R1-F8: fast unit/contract proof of the bundle package

src/manosube_agent_civilization/long_running_proof_artifact/  # P87-R1-F8 (see section 11.8)
01_SCHEMA/long_running_proof_artifact/long_running_proof_artifact_bundle.schema.json
```

Everything above `tests/contract/long_running_proof_artifact/` lives under `tests/`: the
orchestration, session-loss, agent-swap, and runtime-reachability harness itself still creates no
new Canonical record kind, and owns no Canonical State/Authority/Evidence/Reflow/Completion
decision of its own (`HARNESS_OWNS_CANONICAL_STATE=false`) -- exactly the role
`00_KERNEL/VERTICAL_PROOF_CONTRACT.md` already establishes for Phase 8's own one-cycle proof.

**Correction (P87-R1-F8, Structural Review Round 1).** The original claim that this proof
"creates no new production package" is retracted: Issue #86 section 10's own required Canonical
outputs (a versioned corpus, long-running lineage, failure/recovery receipts, a metric dataset,
an environment manifest, raw output, and a reproduction procedure) have no existing owner in this
Kernel, so SHUKOU's own P87-R1-F8 adoption authorized (`PHASE_20_PRODUCTION_PACKAGE_ALLOWED=true`)
exactly one new, minimal `src/` package -- see section 11.8 -- to durably publish them. It commits
through the Store's own orthogonal coordination ledger, never through `commit_state_transition`,
so it still cannot become a new owner of Canonical State, Authority, Evidence, Reflow, or
Completion (`NEW_CANONICAL_STATE_OWNER=false` is unaffected, see section 10).

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

## 4. Session-loss recovery (`crash_worker.py`, `session_loss.py`)

**Corrected in full, Structural Review Round 1 (P87-R1-F1/F2, `ADOPT_P87_R1_F1_THROUGH_F9`).**
The original design only started a *reader* child process that reconstructed State and printed
it back as JSON, after a cycle had already run to completion, committed, *in the parent
process*; the parent that had just run the cycle stayed alive and went on to run the next one.
That proved object-identity independence, never that the process actually holding a cycle's own
execution state (process-local cache/imports/open handles) had been lost and replaced, and every
injected boundary landed only between two already-completed cycles, never mid-cycle -- so none of
the four documented recovery paths were ever actually exercised.

`session_loss.crash_mid_cycle_and_recover` is the real fix: cycle *k* itself now runs, up through
one of `crash_worker.BOUNDARIES`'s four named positions, inside a dedicated child process
(`subprocess.run`, the identical real-process-boundary precedent
`tests/integration/boot/test_boot_project_route.py::test_a_fresh_python_process_boots_
successfully` already establishes) that terminates via `os._exit()` -- a real, unconditional
kill that skips interpreter shutdown, `atexit`, and Python-level stack unwinding, never a
catchable exception a caller could quietly carry on from. A second, later, entirely separate
child process then performs the actual continuation, holding no object the first child ever
built -- it resolves the corpus position and committed State from the Store's own on-disk files
alone. Both processes' real, distinct PIDs are captured and asserted unequal
(`FRESH_WORKER_CONTINUATION_PROOF=true`).

Of the four session-loss boundaries Issue #86 names (`WORK_UNIT_BEFORE_CHANGE`,
`CHANGE_BEFORE_EVIDENCE`, `EVIDENCE_BEFORE_REFLOW`, `REFLOW_COMMIT_INTERRUPTION`): direct
inspection of every owner `cycle.py` calls before `reflow()` shows none of them ever calls
`store.commit` (`topology.py`'s own K-003/R-001 static scan already proves exactly one module in
the installed package, `reflow/commit.py`, ever does). A crash at any of the first three named
boundaries therefore always finds the Store untouched by that cycle -- nothing durable exists to
reconcile, and the sound recovery is to re-derive cycle *k* fresh, through the identical real
public entrypoints `cycle.py` itself calls, in the same order, proven decisively by three
distinct, separately-invoked partial call sequences, each ending in a real process kill. The
fourth boundary crashes *inside* `reflow()`'s own atomic Store commit, via the identical `fault`
crash-injection seam `tests/natural_cycle/proof.py`'s own `FaultInjectingStore` already
establishes, except the fault hook calls `os._exit()` rather than raising; the crash lands at
`AFTER_COMMIT_INTENT` -- durably journaled, but before the transaction's own event reaches the
lineage log -- the exact case `FileStateStore.recover` exists to forward-complete, so the
continuation process calls `store.recover(project_id)`, never a raw retried `reflow()` call.

The orchestrator injects one real crash-and-recover at each of these four boundaries, round-robin
across a tier run's own declared positions (`orchestrator.SESSION_LOSS_BOUNDARY_FRACTIONS`), in
place of that position's own normal `attempt_cycle` call -- so every required Gate 20 tier run
exercises all four boundaries at least once (`FOUR_MID_CYCLE_LOSS_BOUNDARIES_PROVEN=true`).

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
DATASET=true`) -- the negative-control matrix proves this directly, and (Structural Review Round
1, P87-R1-F3) that event is now always captured from the real orchestrated route's own actual
refusal (`cycle.CorpusPositionError`/`reflow`'s own `StaleReflowError`), never a synthetic dict a
caller hand-authors after the fact. **Corrected (P87-R2-F1).** The decisive negative control for
this now drives that refusal through the orchestrated entrypoint itself (`run_long_running_proof`'s
own `refuse_at_cycle` parameter), rather than manually appending a hand-authored `cycle_refused`
dict onto an otherwise-successful run's own event list -- the identical synthetic-event shortcut
P87-R1-F3 itself had already ruled out as decisive proof. See section 11.9.

**Corrected (P87-R1-F9).** `time_to_structural_closure_seconds` is computed from two real
`datetime.now(UTC)` reads bracketing each cycle's own actual execution (`orchestrator.
_observed_now`), including any real session-loss restart/retry time a boundary injected --
never the fixed one-minute-per-cycle placeholder the original delivery used. This observation
clock is deliberately kept separate from the corpus's own deterministic identity (`predicate_id`/
`subject`/`REFLOW_INSTANT`), which never varies with how long a cycle actually took.

## 8. Orchestration (`orchestrator.py`)

`run_long_running_proof(tmp_path, tier=N)` is the one Gate 20 proof entry point: it runs `N`
sequential cycles (with real process-boundary session-loss restarts injected at four declared
positions, one per named boundary, round-robin -- see section 4), one agent/runtime-identity swap
slice, and one runtime-reachability slice, then aggregates every raw event. It owns no Canonical
State/Authority/Evidence/Reflow/Completion decision of its own -- every commit, decision, and
terminal status is produced by the real owner it called.

**Corrected (P87-R1-F7, `ADOPT_P87_R1_F1_THROUGH_F9`).** The whole run is now WTT-coordinated
under one real `LONG_RUNNING_PROOF` Work Coordination (`work_time_transparency.adapters.
with_work_time_coordination`), a new `adapter_kind`/`work_unit_ref.kind` pair SHUKOU's own
adoption authorized (`WTT_BOUNDED_SCHEMA_ENUM_ADAPTER_CHANGE_ALLOWED=true`) -- correcting the
original delivery's declaration that this production proof entrypoint was un-coordinated because
no matching kind yet existed (`WORK_TIME_COORDINATION_REQUIRED=true`,
`UNCOORDINATED_LONG_RUNNING_WORK_ALLOWED=false`). Runtime reachability itself (section 6) remains
deliberately un-wrapped for the reason section 6 already gives.

**Added (P87-R1-F8).** As its own last step, once every cycle/swap/observation slice has run,
`run_long_running_proof` builds and durably commits one artifact bundle -- see section 11.8 --
gathering this run's own raw events, aggregated metrics, lineage refs, session-loss receipts
(including each crash boundary's own two real, distinct PIDs), Agent-swap refs, runtime-
observation refs, an environment manifest, the corpus manifest, and a reproduction procedure, and
returns its `artifact_bundle_id` alongside the pre-existing return fields.

**Corrected (P87-R2-F1).** A real refusal at the orchestrated route (`attempt_cycle` returning
`outcome="refused"` during the positive Gate 20 route) no longer aborts before any artifact is
ever committed. `run_long_running_proof` now durably commits a `run_outcome="FAILED"` artifact
bundle -- carrying every raw event gathered so far, including the real `cycle_refused` event, and
`lineage_refs` reflecting Canonical State exactly as of the last cycle that actually committed --
before raising `RunRefusedError`, which carries that bundle's id/body/Store root so a caller can
independently reload it through a fresh Store handle. See section 11.9.

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

FRESH_WORKER_CONTINUATION_PROOF=true        (section 4, P87-R1-F1)
FOUR_MID_CYCLE_LOSS_BOUNDARIES_PROVEN=true  (section 4, P87-R1-F2, every required Gate 20 run)
REAL_REFUSAL_DURABLY_RECORDED=true          (section 7, P87-R1-F3)
SAME_PROJECT_AND_BINDING_TOPOLOGY_PROOF=true (section 3/8, P87-R1-F4: cycles, swaps, and runtime
                                              observations share one project_id/Project Binding)
CORPUS_ORDER_OMISSION_DUPLICATE_PREFIX_REFUSAL=true  (cycle.verify_expected_corpus_position,
                                              P87-R1-F5)
CLOSED_RUNTIME_OUTCOME_TOTALITY=true        (runtime_reachability.py, P87-R1-F6)
WTT_ENFORCED_AT_PRODUCTION_PROOF_ENTRYPOINT=true  (section 8, P87-R1-F7)
DURABLE_VERSIONED_ARTIFACT_RELOAD_AND_TAMPER_PROOF=true  (section 11.8, P87-R1-F8)
ACTUAL_ELAPSED_TIME_RECORDED=true           (section 7, P87-R1-F9)
REAL_REFUSAL_DURABLY_RECORDED_AT_ORCHESTRATED_ROUTE=true  (section 11.9, P87-R2-F1: a real
                                              orchestrated-route refusal commits a FAILED
                                              artifact bundle before raising, never lost)

ALL_PROOF_TIERS_COMPLETE=true               (test_long_running_proof_gate_20.py, all 4 tiers)
NATURAL_ROUTE_PROVEN=true                   (sections 3-6, every mechanism reuses an existing,
                                              already-accepted public production entrypoint)
CANONICAL_OWNER_COUNT_UNCHANGED=true        (no new Canonical State/Authority/Evidence/Reflow/
                                              Completion owner -- P87-R1-F7/F8 add one new WTT
                                              adapter_kind and one new orthogonal-ledger-only
                                              src/ package, neither of which is one of those
                                              five owners; see section 11.7/11.8)
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

## 11. Structural Review Round 1 corrections (P87-R1, `ADOPT_P87_R1_F1_THROUGH_F9`)

PR #87's structural review found nine gaps between the original delivery and what Issue #86
actually requires; SHUKOU adopted all nine for correction on the existing branch/PR. Sections
3-9 above are already updated in place for each; this section is the one consolidated index.

```text
P87-R1-F1  FRESH_WORKER_CONTINUATION_PROOF        -- section 4
P87-R1-F2  FOUR_MID_CYCLE_LOSS_BOUNDARIES_PROVEN  -- section 4
P87-R1-F3  REAL_REFUSAL_DURABLY_RECORDED          -- section 7
P87-R1-F4  SAME_PROJECT_AND_BINDING_TOPOLOGY_PROOF -- sections 3/8
P87-R1-F5  CORPUS_ORDER_OMISSION_DUPLICATE_PREFIX_REFUSAL -- section 3 (cycle.py)
P87-R1-F6  CLOSED_RUNTIME_OUTCOME_TOTALITY        -- section 6
P87-R1-F7  WTT_ENFORCED_AT_PRODUCTION_PROOF_ENTRYPOINT -- section 8
P87-R1-F8  DURABLE_VERSIONED_ARTIFACT_RELOAD_AND_TAMPER_PROOF -- section 11.8 (below)
P87-R1-F9  ACTUAL_ELAPSED_TIME_RECORDED           -- section 7
```

Structural Review Round 2 reopened one finding against the just-delivered P87-R1-F8 work,
adopted by SHUKOU as `ADOPT_P87_R2_F1_REAL_REFUSAL_DURABLE_ARTIFACT`:

```text
P87-R2-F1  REAL_REFUSAL_DURABLY_RECORDED_AT_ORCHESTRATED_ROUTE -- section 11.9 (below)
```

### 11.8 The Long-Running Proof Artifact Bundle (P87-R1-F8)

Issue #86 section 10 requires canonical outputs this proof's own raw Python return dict never
durably published: a versioned corpus, the long-running lineage, failure/recovery receipts, the
metric dataset, an environment manifest, raw output, and a reproduction procedure -- with an
explicit constraint that the artifact "must never become a new owner of Project Completion,
Evidence sufficiency, or Canonical State." SHUKOU's own adoption additionally required the bundle
carry Agent-swap refs, runtime-observation refs, a corpus manifest/prefix identity, and a content
address or stable fingerprint, and required decisive proof of both reload equality and tamper
refusal (`ARTIFACT_BUNDLE_RELOAD_PROOF=true`, `ARTIFACT_TAMPER_REFUSAL=true`).

```text
src/manosube_agent_civilization/long_running_proof_artifact/
    errors.py     # ArtifactBundleError / ArtifactBundleValidationError
    identity.py   # artifact_bundle_id (run identity only) / artifact_bundle_semantic_fingerprint
                  # (full content address) -- deliberately two different hashes, see below
    engine.py     # build_artifact_bundle: pure builder + schema validation + stringify_floats
    route.py      # commit_artifact_bundle / resolve_artifact_bundle
01_SCHEMA/long_running_proof_artifact/long_running_proof_artifact_bundle.schema.json
```

**Never a new Canonical State/Authority/Evidence/Reflow/Completion owner, structurally.** Every
bundle commits through `FileStateStore.commit_coordination_record_at_tip` -- the same orthogonal,
append-only coordination ledger `work_time_transparency/route.py` already uses (never
`commit_state_transition`/`store.commit`) -- so a bundle commit never reads or advances
`state_revision`, never touches `semantic_fingerprint`/`lineage_head_ref`, and stages no
Project-State transition. Each bundle is the single, self-chained entry of its own coordination
chain (`chain_id == artifact_bundle_id`, `expected_predecessor=None`): one run publishes its own
bundle exactly once (a same-body retry is an idempotent replay; a differently-bodied re-commit
for the identical run's own identity is refused, `RecordConflictError`).

**Two deliberately distinct hashes** (`identity.py`), for the identical reason P87-R1-F9 keeps
observation time out of corpus identity: `artifact_bundle_id` is a pure function of *which run*
the bundle is for (`project_id`, `project_binding_ref`, `tier`, `lineage_refs`) -- excluding
`generated_at` and every other genuinely nondeterministic field, so two commit attempts
describing the identical completed run collide at the identical Store slot.
`artifact_bundle_semantic_fingerprint` is a full content address (`"sha256:" + sha256(canonical_
json_bytes(...))`, the identical convention `change_executor`/`evidence`/`work_time_transparency`
already use) over every field, including `generated_at` -- the bundle's own required content
address.

**Floats never reach the canonical serializer.** `state.canonicalize.canonical_json_bytes`
prohibits floating-point values repository-wide; `metrics.aggregate`'s own rate/duration fields
are genuine floats. `engine.stringify_floats` recursively replaces every float with `repr(x)` --
Python's own shortest round-tripping decimal string -- before a metrics dataset is embedded or
fingerprinted; any caller proving raw-to-summary derivation equality after reload must apply the
identical function to a freshly recomputed dataset before comparing it to the reloaded bundle's
own `metrics` field.

**Reload and tamper proof.** `resolve_artifact_bundle` is a thin wrapper over
`FileStateStore.resolve_coordination_record`, which always re-derives the bundle's authoritative
body from the coordination ledger itself -- never trusting a materialized on-disk cache file on
its own -- and raises `CorruptStoreError` if a directly-edited copy of that cache diverges from
the ledger fact (the identical class of check
`tests/integration/runtime/test_runtime_failure_tamper_matrix.py` already establishes for an
ordinary Store record). `tests/long_running_proof/test_long_running_proof_negative_controls.py`
section 12 proves, against a real Gate 20 run's own committed bundle: reload equality, raw-events-
to-summary re-derivation equality (recomputing `metrics.aggregate` from the reloaded bundle's own
raw events and comparing, through `stringify_floats`, to the reloaded `metrics` field), refusal
of a directly-edited materialized cache file, and that committing the bundle never advanced the
Project's own `state_revision`. `tests/contract/long_running_proof_artifact/` proves the same
package's identity/idempotency/conflict-refusal semantics at the fast, minimal-genesis level.

### 11.9 Real orchestrated-route refusal, durably recorded (P87-R2-F1)

Structural Review Round 2 found one reopened finding against the just-delivered P87-R1-F8 work:
the positive `run_long_running_proof` route immediately raised a bare `AssertionError` on a real
cycle refusal and never reached artifact-bundle build/commit, so a real refusal's own evidence was
lost; and the existing negative-control test for this still manually appended a synthetic
`cycle_refused` dict rather than driving a real one -- the identical shortcut P87-R1-F3 itself had
already banned.

**`run_outcome`, a new required bundle field.** `long_running_proof_artifact_bundle.schema.json`
now requires `run_outcome`, one of `COMMITTED` (every cycle up to `tier` committed with zero
refusals -- the required Gate 20 positive route) or `FAILED` (the run stopped at a real
orchestrated-route refusal; `raw_events`/`metrics` still carry that real `cycle_refused` event, and
`lineage_refs` reflects Canonical State exactly as of the last cycle that actually committed, never
advanced for the refused cycle itself). `identity.BUNDLE_SEMANTIC_FIELDS` includes `run_outcome` (a
`FAILED` bundle's own content address differs from a `COMMITTED` one); `identity.BUNDLE_ID_FIELDS`
deliberately excludes it -- `run_outcome` is "how the run ended," never part of "which run this is."

**A real refusal is never lost.** `orchestrator.run_long_running_proof` gained a
`_build_and_commit_artifact_bundle` helper shared, unchanged, by both routes, so a `FAILED` bundle
carries exactly the same closed set of canonical outputs a `COMMITTED` one does. On a real
orchestrated-route refusal (`attempt_cycle` returning `outcome="refused"` during the positive Gate
20 route), the run now commits a `run_outcome="FAILED"` bundle -- everything gathered so far,
including the real `cycle_refused` event -- before raising `orchestrator.RunRefusedError`, which
carries that bundle's `artifact_bundle_id`/full body/Store root as attributes, so a caller can
independently reload the evidence through a fresh Store handle after the exception propagates. The
refusal itself still propagates uncaught exactly as the previous bare `AssertionError` did --
a refusal during a genuine Gate 20 tier run remains a real bug, since the deterministic corpus is
walked in order and `attempt_cycle` should never organically refuse there; the only change is that
the failed run's own durable artifact is committed first.

**Decisive negative control, corrected.** `run_long_running_proof` gained a `refuse_at_cycle`
parameter: at that 0-indexed cycle position, the function deliberately calls the real
`attempt_cycle` for the *next* corpus position instead of the expected one -- genuinely violating
`cycle.verify_expected_corpus_position`, the identical omission case the existing corpus-order
negative controls already exercise directly against `cycle.py` (P87-R1-F5) -- so the resulting
refusal is a real one, organically produced by the real orchestrated route's own real code, never a
synthetic event a caller fabricates. `tests/long_running_proof/
test_long_running_proof_negative_controls.py`'s `test_a_refused_cycle_event_stays_in_the_dataset_
and_is_counted` drives this at `tier=1` (the fastest tier at which every session-loss boundary
fraction still rounds below one real cycle position, so no crash-injection subprocess ever runs
before the refusal fires) and proves, against the reloaded `FAILED` bundle alone, through a fresh
`FileStateStore` handle holding no object the failed run itself ever built: reload equality to
`RunRefusedError`'s own carried body, exactly one real `cycle_refused` event present,
`metrics.aggregate` recomputed from the reloaded raw events (through `stringify_floats`) equals the
reloaded `metrics` field with `refused_cycle_count == 1`, and Canonical State never advanced for the
refused cycle (`committed_cycle_count == 0` both on the freshly-loaded current State and in the
bundle's own `lineage_refs`).

**Fields carried by the bundle**: `corpus_manifest` (`corpus_kind`, `max_cycles`, `tier`, the
resolved `predicate_id(k)` list for `range(tier)` -- the actual resolved prefix, not merely a
pointer to how to regenerate it); `lineage_refs` (`final_state_revision`,
`cycle.committed_cycle_count`, and the committed State's own `lineage.identity_refs`);
`raw_events` and `metrics` (unchanged from sections 7-8); `session_loss_receipts` (one entry per
crash boundary, including that boundary's own two real, distinct `crash_pid`/`continuation_pid`
values `orchestrator.py` now threads through from `session_loss.crash_mid_cycle_and_recover`,
previously discarded); `agent_swap_refs`/`runtime_observation_refs` (extracted from the identical
raw events sections 5-6 already produce); `environment_manifest` (`python_implementation`,
`python_version`, `platform`); `reproduction_procedure` (the entrypoint, `tier`, `corpus_kind`,
and `lrp.PROJECT_ID`); `generated_at` (a real wall-clock reading via `work_time_transparency.
clock.default_clock`, which strips trailing-zero fractional digits to satisfy `01_SCHEMA/common/
timestamp.schema.json`'s own canonical pattern -- `orchestrator._observed_now`'s raw `%f` output
does not).
