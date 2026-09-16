# Comparative Benchmark Contract

## 0. Governing authority

```text
GOVERNING_ISSUE=#89
PHASE=21
PHASE_NAME=COMPARATIVE_BENCHMARK
ADOPTION_ID=ADOPT_PHASE_21_COMPARATIVE_BENCHMARK
ADOPTION_COMMENT_ID=5692107525
ADOPTION_COMMENT_AUTHOR=manosube (OWNER)
STRUCTURAL_REVIEW_ROUND_1_ID=P90-R1
STRUCTURAL_REVIEW_ROUND_1_ADOPTION_COMMENT_ID=5694898062
STRUCTURAL_REVIEW_ROUND_1_FINDINGS_CLOSED=F1,F2,F3,F4,F5,F6,F7
STRUCTURAL_REVIEW_ROUND_2_ID=P90-R2
STRUCTURAL_REVIEW_ROUND_2_ADOPTION_COMMENT_ID=5699291360
STRUCTURAL_REVIEW_ROUND_2_FINDINGS_CLOSED=F3,F4,F5
STRUCTURAL_REVIEW_ROUND_2_FINDINGS_BLOCKED=F1,F2
```

This contract documents the proof `tests/comparative_benchmark/` and the durable package
`src/manosube_agent_civilization/comparative_benchmark/` implement against Issue #89's own
adopted required comparison groups (section 4), metrics discipline (section 5), authority
boundary (section 7), required decisive negative controls (section 8), and Gate 21 (section 9),
together with the adoption comment's own additional invariants (`WORK_TIME_COORDINATION_
REQUIRED=true`, verification-policy requirements). It does not redefine canonical roadmap
Gate 21 (`02_CANONICAL_ROADMAP.md`); it instantiates it. This revision of the contract also
folds in PR #90's Structural Review Round 1 (P90-R1-F1/F2/F3/F4/F5/F6/F7), replacing the
initial delivery's own now-superseded description of the ungated reference harness (former
section 6), the protocol-freeze identity fields (former section 3/4), and reproduction
independence (former section 8) with the corrected design -- see sections 6, 8, and 12 below.

**Round 2 (P90-R2).** Three of Round 2's five adopted findings are closed in this revision:
F4 (frozen-corpus-fidelity now enforced inside the production builder itself, section 6), F5
(the result bundle's own semantic fingerprint now covers every schema-required field, section
4), and F3 (a reproduction receipt now durably persists its own `reproduced_raw_events`,
section 8). The remaining two, F1 (`EXECUTE_THE_IDENTICAL_REAL_AGENT_IN_BOTH_CONDITIONS`) and
F2 (`BIND_REPRODUCTION_TO_A_VERIFIABLY_INDEPENDENT_ACTOR_OR_AUTHORITY`), are recorded as an
explicit, honest capability/authority blocker rather than closed -- see section 13. This is not
a partial or deferred implementation of F1/F2; it is the adoption's own anticipated, authorized
outcome under its own explicit two-way stop condition (`BLOCKED_REQUIRES_SHUKOU_AUTHORITY_
DECISION` as a legitimate alternative to advancing to the next review step, comment 5699291360).

## 1. Purpose

Prove, through real production routes only, that MANOSUBE's presence or absence is a genuinely
comparable, third-party-reproducible, evidence-bounded fact against one frozen task corpus and
one same-declared Agent -- without the benchmark becoming a new owner of Canonical State,
Authority, Change, Evidence-sufficiency, Reflow, or Completion, and without MANOSUBE's own
timing/Work-Time-Transparency/artifact records ever becoming Completion Evidence.

## 2. Package layout

```text
src/manosube_agent_civilization/comparative_benchmark/
  types.py      # COMPARISON_GROUP_ROLES, TASK_OUTCOMES, REPRODUCTION_AGREEMENTS
  identity.py   # narrow-id/broad-fingerprint content addressing for all 3 record kinds
  errors.py     # ProtocolFreezeValidationError / ResultBundleValidationError /
                # ReproductionReceiptValidationError
  engine.py     # build_protocol_freeze / aggregate_metrics / derive_bounded_claims /
                # build_result_bundle / build_reproduction_receipt (pure, no Store I/O)
  route.py      # commit_/resolve_{protocol_freeze,result_bundle,reproduction_receipt} --
                # the package's only 6 public entry points, all via
                # store.commit_coordination_record_at_tip, never commit_state_transition
01_SCHEMA/comparative_benchmark/comparative_benchmark_{protocol_freeze,result_bundle,
  reproduction_receipt}.schema.json

tests/fixtures/comparative_benchmark.py        # frozen 8-task corpus + protocol-freeze
                                                # declarations (self-contained, see section 6)
tests/comparative_benchmark/orchestrator.py    # drives both group families over the frozen
                                                # corpus, commits all 3 record kinds, spawns the
                                                # separate-process reproduction (section 8)
tests/comparative_benchmark/reproduction_subprocess_entrypoint.py  # the P90-R1-F3 child-process
                                                # entrypoint the orchestrator spawns
tests/comparative_benchmark/conftest.py        # session-scoped shared real run
tests/comparative_benchmark/test_comparative_benchmark_gate_21.py
tests/comparative_benchmark/test_comparative_benchmark_negative_controls.py   # NC-1..NC-13
tests/comparative_benchmark/test_comparative_benchmark_control_treatment_equivalence.py
tests/contract/comparative_benchmark/test_comparative_benchmark_records.py       # fast unit proof
tests/contract/comparative_benchmark/test_comparative_benchmark_static_conformance.py
tests/contract/comparative_benchmark/test_comparative_benchmark_published_artifacts.py  # P90-R1-F2

scripts/generate_comparative_benchmark_artifacts.py  # regenerates the checked-in artifact bundle
examples/comparative_benchmark/{protocol_freeze,result_bundle,reproduction_receipt}.json
                                                # P90-R1-F2's own checked-in public bundle
examples/comparative_benchmark/README.md
```

Everything under `tests/comparative_benchmark/` and `tests/fixtures/comparative_benchmark.py`
creates no new Canonical record kind and owns no Canonical State/Authority/Evidence/Reflow/
Completion decision of its own -- the identical role `00_KERNEL/VERTICAL_PROOF_CONTRACT.md` and
`00_KERNEL/LONG_RUNNING_PROOF_CONTRACT.md` already establish for Phase 8 and Phase 20's own
proofs. The one `src/` package durably publishes the 3 record kinds Issue #89 itself requires
(a pre-result protocol freeze, a raw-result/metric/claim bundle, an independent reproduction
receipt) exactly the way `long_running_proof_artifact` durably publishes Phase 20's own required
Canonical outputs -- through the Store's own orthogonal coordination ledger only.

## 3. The frozen protocol (`types.py`, `engine.build_protocol_freeze`, `identity.py`)

```text
CONTROL_GROUP_IDENTITY_FROZEN_BEFORE_RUN=true    (engine.build_protocol_freeze is a pure
                                                   function of caller-supplied inputs; it never
                                                   reads a raw_event/metric/claim -- see
                                                   test_gate21_metrics_predeclared_before_any_
                                                   result_exists)
SAME_AGENT_COMPARISON_REQUIRED=true              (structural: MANOSUBE_PRESENT/MANOSUBE_ABSENT
                                                   mechanism_identity sets are provably disjoint
                                                   -- build_protocol_freeze's own fail-closed
                                                   check; NC-1)
MANOSUBE_PRESENT_AND_ABSENT_REQUIRED=true        (>=1 of each role required; NC-1's sibling
                                                   check)
COMPARABLE_PROJECT_AND_TASK_CORPUS_REQUIRED=true (one corpus_manifest.task_ids list, one frozen
                                                   order, every group attempts exactly it --
                                                   orchestrator.verify_corpus_fidelity, NC-2)
COMPARABLE_AUTHORITY_BOUNDARY_REQUIRED=true      (authority_boundary_equivalence_manifest is a
                                                   required, disclosed field -- never asserts
                                                   equivalence where none exists; NC-3)
COMPARABLE_RUNTIME_AND_RESOURCE_ENVELOPE_REQUIRED=true  (one shared, top-level resource_budget_
                                                   manifest; comparison_groups items admit no
                                                   per-group override at all, schema-enforced;
                                                   NC-4)
SUCCESS_ONLY_SUBSET_FORBIDDEN=true               (exclusion_policy's own required const-true
                                                   field, enforced in practice by orchestrator.
                                                   verify_corpus_fidelity refusing any omission;
                                                   NC-5)
```

The one same-Agent pairing this delivery's own fixture world declares:
`manosube_present_claude_code` (`MANOSUBE_PRESENT`) and `claude_code_alone`
(`MANOSUBE_ABSENT`) share the identical `agent_label` (`{"agent_family": "claude_code", ...}`)
and differ *only* in `mechanism_identity` -- the literal structural fact
`SAME_AGENT_COMPARISON_AVAILABLE` rests on.

## 4. Metrics discipline (`engine.aggregate_metrics`, `engine.derive_bounded_claims`)

```text
METRICS_PREDECLARED_BEFORE_RESULTS=true      (metric_definitions is a required protocol-freeze
                                               field, committed before any task runs)
THRESHOLDS_PREDECLARED_BEFORE_RESULTS=true   (numeric_thresholds, identical timing)
DENOMINATORS_RECORDED=true                   (aggregate_metrics's own raw_event_count per group)
UNKNOWN_NE_ZERO=true                         (unknown_missing_handling.unknown_ne_zero, const
                                               true; TASK_OUTCOMES has no bare "unknown" bucket
                                               that silently folds into zero)
REFUSAL_NE_SYSTEM_FAILURE=true               (REFUSED and FAILED are two distinct, never-folded
                                               TASK_OUTCOMES members)
RETAINED_NE_CLOSED=true                      (RETAINED_INCOMPLETE is never counted as
                                               COMPLETED_VERIFIED -- aggregate_metrics keys every
                                               outcome separately)
FAILURE_AND_STOP_TIME_INCLUDED=true          (every raw_event carries its own started_at/
                                               closed_at, including REFUSED/FAILED/RETAINED_
                                               INCOMPLETE tasks)
POST_HOC_METRIC_SUBSTITUTION_FORBIDDEN=true  (P90-R1-F4: `identity.PROTOCOL_FREEZE_ID_FIELDS`
                                               was widened to include `metric_definitions`/
                                               `numeric_thresholds`/`claim_vocabulary` themselves
                                               -- the *only* field the id still excludes is
                                               `generated_at`. A post-hoc change to policy
                                               content therefore never overwrites or retroactively
                                               applies to the original, already-committed
                                               protocol identity: it mints a genuinely new
                                               `protocol_freeze_id` of its own, and the original
                                               id's own already-committed body is provably
                                               unchanged (NC-7). A same-id, different-body
                                               re-commit -- the one remaining, genuinely
                                               conflicting case, a `generated_at`-only change --
                                               is still refused, `RecordConflictError`)
NUMERIC_THRESHOLDS_MACHINE_CHECKED=true      (P90-R1-F7: `engine.evaluate_numeric_thresholds`
                                               evaluates every predeclared `(metric_name,
                                               comparison_group_id, operator, threshold_value)`
                                               tuple against the recomputed metrics, embedding
                                               its own `actual_value`/`passed` verdict in
                                               `result_bundle.threshold_evaluations` -- never an
                                               informational-only free-text rule)
RESULT_SEMANTIC_FINGERPRINT_COVERS_ALL_REQUIRED_FIELDS=true  (P90-R2-F5:
                                               `identity.RESULT_BUNDLE_SEMANTIC_FIELDS` widened
                                               to include `threshold_evaluations` and
                                               `generation_process_id` -- the two schema-required
                                               fields it previously excluded -- so tampering
                                               either now changes `result_bundle_semantic_
                                               fingerprint`; a dedicated static test asserts this
                                               tuple equals the schema's own `required` set minus
                                               `result_bundle_id`/`result_bundle_semantic_
                                               fingerprint` exactly, and the identical proof
                                               obligation is discharged for
                                               `REPRODUCTION_RECEIPT_SEMANTIC_FIELDS` against its
                                               own schema)
```

`derive_bounded_claims` (P90-R1-F5) renders each claim's own `statement` by formatting its
frozen `claim_statement_template` against the real, recomputed `computed_values` for its
declared `subject_metric_name`/`subject_group_ids` -- the rendered text is always bound to the
metrics that produced it (NC-12), never independent boilerplate that merely sits beside a
metric, and never anything beyond what the frozen template itself declares.

## 5. Authority boundary and Completion-Evidence exclusion (`route.py`, `engine.py`)

Every commit goes through `store.commit_coordination_record_at_tip`, the identical orthogonal,
append-only coordination ledger `long_running_proof_artifact/route.py` and `work_time_
transparency/route.py` already use -- never `store.commit`/`commit_state_transition`. This
package therefore structurally cannot mutate or authorize Canonical Project State, Authority,
Change, Evidence-sufficiency, Reflow closure, or Project Completion (NC-11). There is
deliberately no `evidence_handoff.py` in this package, and no module here ever imports
`manosube_agent_civilization.evidence`, `.reflow`, `.authority`, `.change`, or `.work_time_
transparency` (`tests/contract/comparative_benchmark/test_comparative_benchmark_static_
conformance.py` proves both by source scan) -- MANOSUBE's own timing/WTT/artifact records can
never become Completion Evidence through this package (NC-9).

## 6. Driving the two comparison-group families (`tests/fixtures/comparative_benchmark.py`,
`tests/comparative_benchmark/orchestrator.py`)

**Disclosed judgment call.** `tests/fixtures/comparative_benchmark.py` is deliberately
self-contained -- it does not import `tests/fixtures/long_running_proof.py` or `tests/fixtures/
vertical_proof.py`, the identical `PHASE_8_FIXTURE_BINDING_NE_PHASE_20_FIXTURE_BINDING=true`
reasoning both of those modules already give. It owns only this corpus's own frozen task
identity, comparison-group declarations, and predeclared protocol-freeze fields. Driving the
`MANOSUBE_PRESENT` group's 8 tasks through a genuine Observation -> Difference -> Authority ->
Change -> Evidence -> Sufficiency -> Reflow route, however, reuses `tests.long_running_proof.
cycle`'s already-proven per-cycle composer directly, against the first 8 positions of `tests.
fixtures.long_running_proof`'s own already-proven, deterministic corpus -- re-deriving that
several-times-structurally-reviewed assembly a third time from scratch for this one additional
phase would itself be new, unreviewed surface for exactly the class of subtle defect those
structural-review rounds exist to catch. This reuse lives only in `tests/comparative_benchmark/
orchestrator.py`, never in the fixture module itself.

Each of the 8 tasks is driven to one predeclared, frozen real outcome
(`tests.fixtures.comparative_benchmark.PRESENT_TASK_PLAN`): 5 real `CLOSED` Reflow closures
(`COMPLETED_VERIFIED`), 1 real Authority refusal for an out-of-scope action
(`REFUSED` -- `evaluate_authority`'s own "silence is not permission" floor), 1 real non-`CLOSED`
`RETAINED` Reflow closure via the proven Phase 8 negative/interruption-route recipe
(`RETAINED_INCOMPLETE`), and 1 real, unhandled `DifferenceError` from a deliberately malformed
derivation request (`FAILED`) -- so `FAILURES_INCLUDED` is a fact about this frozen plan, never
assembled after seeing results.

**P90-R1-F1 (Structural Review Round 1): the ungated reference harness is a real execution, not
a fixture table.** The 3 `MANOSUBE_ABSENT` groups (`codex_alone`, `claude_code_alone`,
`existing_agent_framework`) are driven by `orchestrator.run_ungated_reference_harness_group`
through the *identical real* natural-route mechanism the `MANOSUBE_PRESENT` group's own
`CLOSED` tasks use: its own fresh Store and fresh genesis/Project Binding
(`tests.long_running_proof.cycle.build_store`/`bind_genesis`), the real `cycle.
assemble_one_cycle` + the real, unmodified `reflow()`, over the byte-identical frozen 8-task
corpus -- never a hand-authored outcome-table lookup, and never a real invocation of any named
external product (`PRODUCTION_CREDENTIAL_USE_ALLOWED=false`, `REMOTE_COMMAND_AUTHORITY_
ALLOWED=false`, unchanged). Every task is always driven through the plain natural-route path --
never the deliberately-crafted out-of-scope/malformed-request/evidence-emptied branches the
`MANOSUBE_PRESENT` group's own frozen task-routing policy uses for some of its tasks, since that
routing choice is itself MANOSUBE's own deliberate policy, absent by definition in the
`MANOSUBE_ABSENT` condition. After each task's own real Reflow closure, the harness retroactively
(audit/classification only, never a live pre-flight gate) re-evaluates the identical real
Authority Rule fixture against the exact action actually taken, recording that classification in
the raw event's own free-text `reason` field. "Ungated" is therefore a structural fact about
*when* Authority is consulted (after the fact, never gating the attempt), not a claim that no
real Authority/Reflow mechanism is ever reached -- `codex_alone`/`existing_agent_framework` are
driven by the identical real mechanism, differing from `claude_code_alone` only in their
protocol freeze's own predeclared `agent_label`, never a real invocation of Codex or any other
third-party product.

The remaining, narrower disclosed asymmetry against `MANOSUBE_PRESENT` -- (1) `MANOSUBE_ABSENT`'s
uniform plain-route attempt vs. `MANOSUBE_PRESENT`'s own deliberate REFUSED/FAILED/RETAINED
task-routing policy, and (2) `MANOSUBE_ABSENT`'s retroactive, audit-only Authority classification
vs. `MANOSUBE_PRESENT`'s live, load-bearing pre-flight Authority gate -- is recorded in the
protocol freeze's own `comparability_loss_receipts` and `authority_boundary_equivalence_
manifest` (NC-3), never presented as true product-for-product parity.

**P90-R2-F4: frozen-corpus fidelity is now enforced by the production builder itself, not only
by a test-only orchestrator guard.** `engine.verify_exact_frozen_corpus` -- called
unconditionally, first, inside both `engine.build_result_bundle` and `engine.
build_reproduction_receipt` -- refuses (`ResultBundleValidationError`/
`ReproductionReceiptValidationError`, via its own `error_cls` parameter) unless every declared
comparison group's own raw events name exactly the frozen `task_ids`, in that exact order, once
each. This means the guard can no longer be bypassed by calling `build_result_bundle`/
`commit_result_bundle`/`build_reproduction_receipt`/`commit_reproduction_receipt` directly,
skipping `tests.comparative_benchmark.orchestrator.verify_corpus_fidelity` entirely -- decisive
proof: `tests/contract/comparative_benchmark/test_comparative_benchmark_records.py::
test_build_result_bundle_refuses_reordered_omitted_duplicated_or_substituted_corpus`/
`test_build_reproduction_receipt_refuses_a_non_full_corpus_reproduced_raw_events_set`, both
calling the production builders directly with no orchestrator involved. The orchestrator's own
`verify_corpus_fidelity` still runs as an additional, redundant test-suite-level guard (NC-2,
NC-5, NC-10) -- refusing reordering, omission, duplication, substitution, and partial-scale
corpus attempts before any result bundle or reproduction receipt is ever committed through
either surface.

## 7. Work-Time Transparency coordination

```text
WORK_TIME_COORDINATION_REQUIRED=true   (adoption comment 5692107525)
```

`work_time_transparency.types.ADAPTER_KINDS` gained its tenth member, `COMPARATIVE_BENCHMARK`
(`work_unit_ref.kind = "comparative_benchmark_run"`), following the identical P87-R1-F7
precedent Phase 20 already established. `orchestrator.run_one_full_pass` wraps the entire
comparison-group run (both group families, one full pass) in one real `with_work_time_
coordination` call, mirroring `tests.long_running_proof.orchestrator.run_long_running_proof`'s
own identical composition.

## 8. Independent reproduction (`engine.build_reproduction_receipt`)

`reproduced_metrics` is always recomputed by this function itself, from `reproduced_raw_events`
alone; `agreement` (`MATCH`/`DIVERGENT`/`INCOMPARABLE`) is always independently derived by
comparing that recomputation against the *original* bundle's own stored `metrics` -- never
accepted as a caller-supplied verdict (the function's own signature carries no `agreement`
parameter at all).

**P90-R1-F3: independence is structurally verified, never a caller-supplied boolean.**
`reproducer_identity` requires an integer `reproduction_process_id` and a 3-field
`reproduction_environment_manifest`; `build_reproduction_receipt` refuses fail-closed
(`ReproductionReceiptValidationError`) whenever `reproduction_process_id` equals the *original*
bundle's own `generation_process_id` -- a reproduction sharing its OS process with the run it
claims to reproduce is a self-assertion, never a genuinely separate execution, whatever
`is_original_author` claims (`SELF_ASSERTED_INDEPENDENCE_REFUSED=true`). `orchestrator.
run_comparative_benchmark` makes this check meaningful in practice: it spawns a real, separate
Python OS process (`python -m tests.comparative_benchmark.reproduction_subprocess_entrypoint`,
the identical `sys.executable`/fresh-process idiom `tests/integration/boot/
test_boot_project_route.py::test_a_fresh_python_process_boots_successfully` already establishes)
to run the reproduction pass -- its own fresh Store, fresh genesis/Project Binding, the identical
comparison-group mechanism the original run used -- and reads that child's own real
`os.getpid()`/environment manifest from its stdout JSON payload, never guessing or forwarding
values on the parent's behalf. Since the child is a genuinely different OS process, its own pid
is structurally guaranteed to differ from the parent's `generation_process_id`
(`REAL_SAME_AGENT_PRESENT_ABSENT_EXECUTION`-adjacent: `INDEPENDENT_REPRODUCER_PROVENANCE_
VERIFIED=true`). The committed reproduction receipt's own raw events are that child's own real
raw events (NC-13's positive counterpart; see Gate 21's own `THIRD_PARTY_REPRODUCIBLE`).

**P90-R2-F3: `reproduced_raw_events` is now durably persisted in the receipt itself, not only
its aggregated `reproduced_metrics`.** `REPRODUCTION_RECEIPT_SEMANTIC_FIELDS` and the
`comparative_benchmark_reproduction_receipt.schema.json`'s own `required` set both now include
`reproduced_raw_events` (schema shape identical to the result bundle's own `raw_events` --
`kind`/`comparison_group_id`/`task_id`/`outcome` required, `started_at`/`closed_at`/`reason`
optional); `REPRODUCTION_RECEIPT_ID_FIELDS` deliberately excludes it (raw events are the
finding a reproduction attempt produces, not part of "does an attempt for this bundle/reproducer
already exist"). `engine.build_reproduction_receipt` persists the caller's own
`reproduced_raw_events` verbatim in the committed record, so a third party can rederive
`reproduced_metrics` from the published raw bytes alone after reload -- decisive proof:
`test_reproduction_receipt_persists_reproduced_raw_events_and_rederives_reproduced_metrics` and
the published-artifact suite's own
`test_published_reproduction_receipt_metrics_rederive_from_published_reproduced_raw_events`.

## 9. Published artifacts (`examples/comparative_benchmark/`)

**P90-R1-F2: a public, versioned, checked-in artifact bundle.** `scripts/
generate_comparative_benchmark_artifacts.py` runs the full, real `run_comparative_benchmark`
against a disposable temp directory and writes the resulting `protocol_freeze`, `result_bundle`,
and `reproduction_receipt` bodies, pretty-printed (`json.dumps(..., indent=2, sort_keys=True)`),
to `examples/comparative_benchmark/{protocol_freeze,result_bundle,reproduction_receipt}.json`
-- real, genuine bytes this repository ships and versions, never hand-authored or fabricated
JSON, and never an ephemeral per-test `FileStateStore` that vanishes after the test run
(`PUBLIC_VERSIONED_PROTOCOL_FREEZE=true`, `PUBLIC_VERSIONED_RAW_RESULT_BUNDLE=true`,
`PUBLIC_VERSIONED_REPRODUCTION_RECEIPT=true`). This is a *display* serialization only -- the
records' own internal content addressing (`state.canonicalize.canonical_json_bytes`) is entirely
unaffected by how the checked-in copy is pretty-printed.

`tests/contract/comparative_benchmark/test_comparative_benchmark_published_artifacts.py` loads
the three files directly off disk (`json.loads(Path(...).read_text())` alone -- no Store, no
fixture module, no orchestrator call) and proves: each validates against its own canonical
schema; each record's own declared id/semantic-fingerprint fields are recomputed from the loaded
body and match exactly (`PUBLISHED_BYTES_RELOADABLE=true`); the result bundle's own `metrics`/
`claims`/`threshold_evaluations` are recomputed from its own loaded `raw_events` and the loaded
protocol freeze alone, matching the stored values byte-for-byte
(`REPRODUCED_RAW_EVENTS_DURABLY_REDERIVABLE=true`); the loaded raw events include at least one
real non-`COMPLETED_VERIFIED` outcome (`FAILURES_PRESENT_IN_PUBLISHED_RAW_DATA=true` --
real failures/refusals/retained outcomes survive into the published data, never a success-only
subset); and the reproduction receipt's own `agreement` verdict is recomputed from its own
loaded `reproduced_metrics` compared against the loaded result bundle's own `metrics`, using the
identical rule `engine.build_reproduction_receipt` itself applies, and matches the stored value.

## 10. The 13 required decisive negative controls

```text
NC-1   different Agent/runtime/configuration cannot be mislabeled as same-agent comparison
       -- engine.build_protocol_freeze's own mechanism_identity disjointness check
NC-2   task/corpus substitution, omission, reordering, duplicate sampling fail closed
       -- orchestrator.verify_corpus_fidelity
NC-3   Authority/tool-surface asymmetry is detected, not treated as a MANOSUBE effect
       -- comparability_loss_receipts + authority_boundary_equivalence_manifest, both required
NC-4   resource/time/budget asymmetry is detected
       -- one shared top-level resource_budget_manifest; per-group override is schema-refused
NC-5   successful runs cannot exclude failures/refusals/retained/incomplete outcomes
       -- orchestrator.verify_corpus_fidelity refuses any omission, including a success-only one
NC-6   raw-result deletion/edit invalidates derived metrics and claims
       -- aggregate_metrics/build_reproduction_receipt recompute independently; a tampered/
          deleted raw_event set diverges from the stored bundle's own metrics
NC-7   post-hoc metric/denominator/threshold change is rejected
       -- P90-R1-F4: protocol_freeze_id now includes metric_definitions/numeric_thresholds/
          claim_vocabulary in its own identity, so a post-hoc change mints a genuinely new
          protocol_freeze_id, never overwriting or retroactively applying to the original,
          already-committed identity (proven: the original id's own body is unchanged after the
          attempt); a same-id, different-body re-commit -- a generated_at-only change, the one
          field the id still excludes -- is still refused (RecordConflictError)
NC-8   cross-group/cross-project/cross-binding/cross-environment substitutions fail closed
       -- ResultBundleValidationError on an undeclared comparison_group_id; build_reproduction_
          receipt returns INCOMPARABLE against a foreign bundle's own differing group-id set
NC-9   MANOSUBE timing/WTT/artifact records cannot become Completion Evidence
       -- no evidence_handoff.py; no import of the Evidence/Reflow/WTT owners (static proof)
NC-10  shorter or partial runs cannot impersonate the adopted benchmark scale
       -- orchestrator.verify_corpus_fidelity refuses a partial-task-count attempt
NC-11  the benchmark harness cannot mutate existing Canonical owners through an extension surface
       -- route.py/engine.py never call commit_state_transition; only route.py commits (static)
NC-12  unsupported causal/superiority claims cannot exceed recorded Evidence
       -- P90-R1-F5: derive_bounded_claims' own rendered claim statement is exactly its frozen
          claim_statement_template formatted against its own recomputed computed_values -- never
          anything beyond that frozen template's own declared placeholders, however favorable
          the metrics handed in; every other claim field (id/bound/subject_*) is unaffected by
          the metrics content
NC-13  a self-run reproduction cannot impersonate an independent third-party receipt
       -- build_reproduction_receipt always independently recomputes agreement; a self-claimed
          is_original_author=True with divergent reproduced_raw_events still yields DIVERGENT;
          P90-R1-F3's own sibling proof: a reproduction_process_id identical to the original
          bundle's own generation_process_id is refused outright (ReproductionReceiptValidation
          Error), whatever is_original_author claims
```

Every NC above has its own dedicated, non-skipped test in `tests/comparative_benchmark/
test_comparative_benchmark_negative_controls.py`, numbered `test_nc1_...` through
`test_nc13_...`.

## 11. Gate 21

```text
SAME_AGENT_COMPARISON_AVAILABLE=true   (section 3; test_gate21_same_agent_comparison_available_
                                         by_declared_label_and_real_route)
CONTROL_GROUPS_DEFINED=true            (4 groups, matching Issue #89 section 4 exactly;
                                         test_gate21_control_groups_defined_matches_issue_89_
                                         section_4)
METRICS_PREDECLARED=true               (section 4; test_gate21_metrics_predeclared_before_any_
                                         result_exists)
RAW_RESULTS_PUBLIC=true                (durably committed, independently resolvable through the
                                         coordination ledger; test_gate21_raw_results_public_
                                         durably_resolvable_from_the_ledger)
FAILURES_INCLUDED=true                 (section 6; test_gate21_failures_included_real_non_
                                         success_outcomes_present)
THIRD_PARTY_REPRODUCIBLE=true          (section 8; test_gate21_third_party_reproducible_
                                         independent_receipt_matches)
CLAIMS_BOUNDED_BY_EVIDENCE=true        (section 4/9-NC-12; test_gate21_claims_bounded_by_
                                         evidence_and_rederivation_matches_byte_for_byte -- also
                                         the required raw -> metric -> claim rederivation proof)
```

Phase 21 is not complete until SHUKOU accepts the exact reviewed delivery head, that head is
merged, and resulting `main` is independently re-observed.

## 13. P90-R2-F1/F2: capability/authority blocker (not closed)

Round 2's own Structural Advisor review (PR #90 comment 5699255260) and SHUKOU's adoption
(comment 5699291360) required two further corrections this contract does **not** claim to have
implemented:

```text
F1=EXECUTE_THE_IDENTICAL_REAL_AGENT_IN_BOTH_CONDITIONS
   (a genuine real invocation of the Agent under test -- Claude Code/Codex/an existing
   framework's own real runtime/adapter/model -- run once with MANOSUBE present and once with
   MANOSUBE genuinely absent from the execution path, never MANOSUBE's own Observation ->
   Difference -> Authority -> Change -> Evidence -> Reflow composer re-labeled as "the Agent
   alone")
F2=BIND_REPRODUCTION_TO_A_VERIFIABLY_INDEPENDENT_ACTOR_OR_AUTHORITY
   (a reproduction receipt whose independence rests on a real, separate third-party actor or
   authority -- explicitly not satisfied by "separate OS process" alone, per the adoption's own
   `SEPARATE_PROCESS_ONLY_IS_NOT_ACCEPTED_AS_THIRD_PARTY=true`)
```

The adoption itself anticipates this outcome: it requires a feasibility inventory *before* any
implementation attempt, and states explicitly that "a Python child process, PID inequality, a
fixture label, or the MANOSUBE natural route relabeled as 'Agent alone' may not satisfy F1 or
F2," that Claude Code "may not weaken Gate 21, rewrite the objective, or turn an unavailable
capability into a passing test," and sets a two-way stop condition: advance to the next review
step, or `BLOCKED_REQUIRES_SHUKOU_AUTHORITY_DECISION`.

**F1 is infeasible inside the existing Authority boundary.** A genuine real invocation of an
Agent product (Claude Code, Codex, or an existing agent framework) as the actual subject under
test -- not MANOSUBE's own natural-route composer, whatever it is labeled -- requires calling a
real model/product with real credentials. `PRODUCTION_CREDENTIAL_USE_ALLOWED=false` (Issue #89
section 7, reaffirmed unchanged by this adoption) forecloses this outright: there is no way to
execute "the identical real Agent" against this repository's own frozen corpus, present and
absent MANOSUBE, without production credential use. This is not a missing implementation; it is
a capability this session's own Authority grant does not extend, by the founding adoption's own
explicit, still-unchanged design.

**F2 is infeasible for the identical structural reason.** A "verifiably independent third-party
actor or authority" is, by definition, a party other than the one operator/session/credential
set that produced the original result bundle. Manufacturing one from inside a single Claude Code
session -- the only executor this adoption authorizes -- is not a code change; it requires either
a real external actor to genuinely participate (something no code path this session owns can
conjure into existing) or `REMOTE_COMMAND_AUTHORITY_ALLOWED=true` to command one, which remains
`false`. A separate OS process, however genuinely distinct its `os.getpid()` (P90-R1-F3's own
proof), is still the identical operator's own repository, credentials, and authorization --
exactly what the adoption's own `SEPARATE_PROCESS_ONLY_IS_NOT_ACCEPTED_AS_THIRD_PARTY=true`
already states is insufficient.

**This is the outcome Issue #89's own founding adoption (comment 5692107525) already
anticipated**, in its own original design guidance for this exact boundary: given
`PRODUCTION_CREDENTIAL_USE_ALLOWED=false`/`REMOTE_COMMAND_AUTHORITY_ALLOWED=false`, real external
product invocation was never something this benchmark could mean -- only a closed,
honestly-labeled, disclosed-asymmetry model, which is what P90-R1-F1's ungated-reference-harness
design and this Round's own F4/F5/F3 corrections continue to be. Repository-wide precedent is
unbroken across all 18+ prior phases (`13_CHANGE_EXECUTOR/CHANGE_EXECUTOR_CONTRACT.md`'s executor
only ever runs already-decided Changes on disposable worktrees, never lets an Agent decide an
action; `10_RUNTIME/RUNTIME_CONTRACT.md`'s own adapters are in-memory or loopback-only, "no
redirect ever" to a real external target): no shipped code in this repository has ever invoked a
real external AI product or model, and this contract does not introduce the first instance to
satisfy F1/F2.

```text
F1_STATUS=BLOCKED_REQUIRES_SHUKOU_AUTHORITY_DECISION
F2_STATUS=BLOCKED_REQUIRES_SHUKOU_AUTHORITY_DECISION
F1_BLOCKING_CONSTRAINT=PRODUCTION_CREDENTIAL_USE_ALLOWED_FALSE
F2_BLOCKING_CONSTRAINT=REMOTE_COMMAND_AUTHORITY_ALLOWED_FALSE_AND_NO_REAL_THIRD_PARTY_AVAILABLE
SIMULATED_OR_RELABELED_SUBSTITUTE_PROVIDED=false
GATE_21_WEAKENED_OR_OBJECTIVE_REWRITTEN=false
```

Gate 21's own `SAME_AGENT_COMPARISON_AVAILABLE` and `THIRD_PARTY_REPRODUCIBLE` booleans (section
11) therefore remain proven only under Round 1's own disclosed, honestly-labeled design -- not
under Round 2's stricter, real-external-invocation reading of F1/F2. Phase 21 is not complete;
SHUKOU's own next decision (widen the Authority boundary, accept the Round 1 reading as
sufficient, or another disposition) is required before this specific pair can be closed.

## 14. Explicit non-claims

```text
PHASE_22_V1_0_DECLARATION=false
NEW_CANONICAL_STATE_OWNER=false
NEW_AUTHORITY_OWNER=false
NEW_EVIDENCE_OWNER=false
NEW_REFLOW_OWNER=false
NEW_COMPLETION_OWNER=false
MANOSUBE_TIMING_WTT_ARTIFACT_RECORDS_ARE_COMPLETION_EVIDENCE=false
REAL_EXTERNAL_PRODUCT_INVOCATION=false
PRODUCTION_DEPLOYMENT=false
PRODUCTION_CREDENTIAL_USE=false
REMOTE_COMMAND_AUTHORITY=false
GITHUB_MERGE_OR_ISSUE_CLOSE_AUTOMATION=false
MERGE_ALLOWED=false
ISSUE_89_CLOSE_ALLOWED=false
P90_R2_F1_CLOSED=false
P90_R2_F2_CLOSED=false
```
