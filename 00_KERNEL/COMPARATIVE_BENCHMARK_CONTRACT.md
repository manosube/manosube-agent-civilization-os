# Comparative Benchmark Contract

## 0. Governing authority

```text
GOVERNING_ISSUE=#89
PHASE=21
PHASE_NAME=COMPARATIVE_BENCHMARK
ADOPTION_ID=ADOPT_PHASE_21_COMPARATIVE_BENCHMARK
ADOPTION_COMMENT_ID=5692107525
ADOPTION_COMMENT_AUTHOR=manosube (OWNER)
```

This contract documents the proof `tests/comparative_benchmark/` and the durable package
`src/manosube_agent_civilization/comparative_benchmark/` implement against Issue #89's own
adopted required comparison groups (section 4), metrics discipline (section 5), authority
boundary (section 7), required decisive negative controls (section 8), and Gate 21 (section 9),
together with the adoption comment's own additional invariants (`WORK_TIME_COORDINATION_
REQUIRED=true`, verification-policy requirements). It does not redefine canonical roadmap
Gate 21 (`02_CANONICAL_ROADMAP.md`); it instantiates it.

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
                                                # corpus, commits all 3 record kinds
tests/comparative_benchmark/conftest.py        # session-scoped shared real run
tests/comparative_benchmark/test_comparative_benchmark_gate_21.py
tests/comparative_benchmark/test_comparative_benchmark_negative_controls.py   # NC-1..NC-13
tests/comparative_benchmark/test_comparative_benchmark_control_treatment_equivalence.py
tests/contract/comparative_benchmark/test_comparative_benchmark_records.py       # fast unit proof
tests/contract/comparative_benchmark/test_comparative_benchmark_static_conformance.py
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
POST_HOC_METRIC_SUBSTITUTION_FORBIDDEN=true  (protocol_freeze_id excludes metric_definitions/
                                               numeric_thresholds/claim_vocabulary from its own
                                               identity -- a post-hoc change collides at the
                                               identical already-committed id with a different
                                               body and is refused, RecordConflictError; NC-7)
```

`derive_bounded_claims` never reads `metrics`' own numeric content into a claim's text -- every
claim is the frozen `claim_vocabulary` entry, verbatim (NC-12).

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

The 3 `MANOSUBE_ABSENT` groups (`codex_alone`, `claude_code_alone`, `existing_agent_framework`)
are driven by a small, honestly-named, in-repo "ungated reference harness"
(`orchestrator.run_ungated_reference_harness_group`): a deterministic function, reading a fixed,
hand-authored outcome table (`tests.fixtures.comparative_benchmark.ABSENT_OUTCOME_TABLE`), that
never invokes any real external Codex/Claude Code/other-framework product
(`PRODUCTION_CREDENTIAL_USE_ALLOWED=false`, `REMOTE_COMMAND_AUTHORITY_ALLOWED=false`) and never
passes through Observation/Difference/Authority/Change/Evidence/Reflow at all -- so it
structurally cannot itself produce `CLOSED` Canonical State, making its own `mechanism_identity`
genuinely disjoint from the `MANOSUBE_PRESENT` group's real natural route, not merely a
relabeling. This disclosed asymmetry is recorded in the protocol freeze's own
`comparability_loss_receipts` (NC-3), never presented as true product-for-product parity.

`orchestrator.verify_corpus_fidelity` is the one test-suite-level decisive guard (mirroring
`tests.long_running_proof.cycle.CorpusPositionError`'s own identical role) that every declared
comparison group's own raw events name exactly the frozen `task_ids`, in that exact order, once
each -- refusing reordering, omission, duplication, substitution, and partial-scale corpus
attempts (NC-2, NC-5, NC-10) before any result bundle or reproduction receipt is ever committed.

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
parameter at all). `orchestrator.run_comparative_benchmark` performs a genuinely second,
independent full pass -- a fresh Store, a fresh project genesis/binding, its own reproducer
identity -- and commits its own raw events as the reproduction receipt's `reproduced_raw_events`
(NC-13's positive counterpart; see Gate 21's own `THIRD_PARTY_REPRODUCIBLE`).

## 9. The 13 required decisive negative controls

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
       -- protocol_freeze_id excludes policy fields; a changed body collides at the identical id
          (RecordConflictError)
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
       -- derive_bounded_claims' own claim text is verbatim from claim_vocabulary regardless of
          the metrics content handed to it
NC-13  a self-run reproduction cannot impersonate an independent third-party receipt
       -- build_reproduction_receipt always independently recomputes agreement; a self-claimed
          is_original_author=True with divergent reproduced_raw_events still yields DIVERGENT
```

Every NC above has its own dedicated, non-skipped test in `tests/comparative_benchmark/
test_comparative_benchmark_negative_controls.py`, numbered `test_nc1_...` through
`test_nc13_...`.

## 10. Gate 21

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

## 11. Explicit non-claims

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
```
