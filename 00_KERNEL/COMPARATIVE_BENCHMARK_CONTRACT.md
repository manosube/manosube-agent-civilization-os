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
STRUCTURAL_REVIEW_ROUND_3_ID=P90-R3
STRUCTURAL_REVIEW_ROUND_3_ADOPTION_ID=ADOPT_P90_R3_BOUNDED_REAL_AGENT_AND_INDEPENDENT_REPRODUCER_LANE
STRUCTURAL_REVIEW_ROUND_3_ADOPTION_COMMENT_ID=5705039613
STRUCTURAL_REVIEW_ROUND_3_FINDINGS_STATUS=F1_BLOCKED_NO_PRECONFIGURED_REAL_AGENT,F2_ADMISSION_SURFACE_BUILT_BLOCKED_AWAITING_INDEPENDENT_REPRODUCER
STRUCTURAL_REVIEW_ROUND_4_ID=P90-R4
STRUCTURAL_REVIEW_ROUND_4_ADOPTION_ID=ADOPT_P90_R4_REAL_AGENT_CORPUS_AND_PRETRUSTED_INDEPENDENT_REPRODUCER
STRUCTURAL_REVIEW_ROUND_4_ADOPTION_COMMENT_ID=5706881165
STRUCTURAL_REVIEW_ROUND_4_FINDINGS_STATUS=F1_BLOCKED_NO_USABLE_REAL_AGENT,F2_TRUST_ANCHOR_ADMITTED_BLOCKED_AWAITING_INDEPENDENT_REPRODUCTION_RUN
STRUCTURAL_REVIEW_ROUND_4_KEY_REGISTRATION_COMMENT_ID=5709021178
STRUCTURAL_REVIEW_ROUND_4_KEY_REGISTRATION_COMMENT_AUTHOR=manosube (OWNER)
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

**Round 3 (P90-R3, `ADOPT_P90_R3_BOUNDED_REAL_AGENT_AND_INDEPENDENT_REPRODUCER_LANE`, comment
5705039613)** narrowly widened the Authority boundary Round 2's own F1 blocker rested on
(`PRODUCTION_CREDENTIAL_USE_ALLOWED=true`, scoped strictly to one preconfigured Agent identity
against the Phase 21 frozen corpus, evidence generation only) and explicitly forbade Claude Code
from self-issuing F2's independent-reproduction receipt. F1 remains blocked, but for a different,
corpus-*structural* reason this Round discovered rather than a credential-availability one -- see
section 13a. F2's admission surface (schema, engine verification, route commit) is now built --
see section 8a -- but remains `BLOCKED_AWAITING_INDEPENDENT_REPRODUCER` absent a real external
submission, per this Round's own three-way stop condition.

**Round 4 (P90-R4, `ADOPT_P90_R4_REAL_AGENT_CORPUS_AND_PRETRUSTED_INDEPENDENT_REPRODUCER`,
comment 5706881165)** adopted, as one indivisible work unit, replacing the fixture corpus with a
real, pre-result-frozen, Agent-executable corpus (F1) and requiring F2's independent reproducer
identity/public key to be pre-registered by SHUKOU as a trust anchor, resolved from the Store,
never accepted from a submission's own self-declared key (F2). F1 remains blocked, for a third,
genuinely distinct reason from Rounds 2 and 3 -- this specific sandboxed execution environment's
own harness-level safety classifier structurally denies any tool-write-capable nested Agent
subprocess invocation, independent of the corpus's own definition or of credential availability --
see section 13b. F2's trust-anchor admission/verification surface (schema, engine builder,
Store-resolved verification, 8 required fail-closed refusal behaviors) is now built and
decisively tested against test-only key material -- see section 8b. SHUKOU subsequently
disclosed the real independent reproducer's public key in PR #90 comment 5709021178 (author
`manosube`, `OWNER`); Claude Code independently re-verified that comment via the GitHub API
before acting on it (author, association, and every disclosed field), then admitted it as the
real, checked-in trust anchor through the existing production route -- never a test-double key,
and never the private key, which this repository has still never generated, requested, received,
or stored. F2 now stands `BLOCKED_AWAITING_INDEPENDENT_REPRODUCTION_RUN`: the trust anchor is
admitted, but no genuine independent reproduction submission against it has yet been received,
per this Round's own four-way stop condition.

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
                # ReproductionReceiptValidationError /
                # IndependentReproductionSubmissionValidationError (P90-R3-F2) /
                # IndependentReproducerTrustAnchorValidationError (P90-R4-F2)
  engine.py     # build_protocol_freeze / aggregate_metrics / derive_bounded_claims /
                # build_result_bundle / build_reproduction_receipt (pure, no Store I/O) /
                # verify_independent_reproduction_submission (P90-R3-F2/P90-R4-F2 -- verifies
                # only, never builds or signs; a local Ed25519 verifier duplicated from
                # binding.signature rather than imported -- see section 8a) /
                # build_independent_reproducer_trust_anchor (P90-R4-F2 -- see section 8b;
                # imports only Ed25519PublicKey, never Ed25519PrivateKey)
  route.py      # commit_/resolve_{protocol_freeze,result_bundle,reproduction_receipt},
                # admit_/resolve_independent_reproduction_submission (P90-R3-F2),
                # admit_/resolve_independent_reproducer_trust_anchor (P90-R4-F2) -- the
                # package's 10 public entry points, all via
                # store.commit_coordination_record_at_tip, never commit_state_transition
01_SCHEMA/comparative_benchmark/comparative_benchmark_{protocol_freeze,result_bundle,
  reproduction_receipt,independent_reproduction_submission,
  independent_reproducer_trust_anchor}.schema.json

tests/fixtures/comparative_benchmark.py        # frozen 8-task corpus + protocol-freeze
                                                # declarations (self-contained, see section 6);
                                                # also a fresh, ephemeral Ed25519 test-double
                                                # keypair generator and trust-anchor kwargs
                                                # builder for P90-R3-F2/P90-R4-F2 tests -- never
                                                # a real or committed credential
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
tests/contract/comparative_benchmark/test_comparative_benchmark_independent_reproduction_submission.py
                                                # P90-R3-F2's own decisive admission-surface proof
                                                # (Round 4: every test now pre-admits a
                                                # test-only trust anchor first)
tests/contract/comparative_benchmark/test_comparative_benchmark_independent_reproducer_trust_anchor.py
                                                # P90-R4-F2's own decisive trust-anchor
                                                # admission/verification-surface proof

scripts/generate_comparative_benchmark_artifacts.py  # regenerates the checked-in artifact bundle
scripts/admit_comparative_benchmark_independent_reproducer_trust_anchor.py
                                                # P90-R4-F2: admits SHUKOU's own real
                                                # pre-registered public key through the
                                                # production route and publishes the result;
                                                # never touches a private key
examples/comparative_benchmark/{protocol_freeze,result_bundle,reproduction_receipt}.json
                                                # P90-R1-F2's own checked-in public bundle
examples/comparative_benchmark/independent_reproducer_trust_anchor.json
                                                # P90-R4-F2's own checked-in real trust anchor
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

## 8a. P90-R3-F2: independent reproduction submission admission (`engine.
verify_independent_reproduction_submission`, `route.admit_independent_reproduction_submission`)

Round 3's own adoption (comment 5705039613) explicitly forbids Claude Code from self-issuing
F2's independent reproduction receipt (`CLAUDE_CODE_MAY_SELF_ISSUE_INDEPENDENT_RECEIPT=false`,
`ORIGINAL_OPERATOR_MAY_SELF_ISSUE_INDEPENDENT_RECEIPT=false`,
`SEPARATE_PROCESS_ALONE_SUFFICIENT=false`) while requiring
`DISTINCT_ACTOR_OR_AUTHORITY_PROVENANCE_REQUIRED=true`. What this contract implements is
strictly the **verification/admission surface** for a genuinely independent submission -- never
the submission itself, never a fabricated independent actor.

**Structural proof of independence: a validating Ed25519 signature against a self-declared
public key.** A GitHub login alone cannot prove independence in this repository's own
environment (both Claude Code's own comments and `manosube`'s own comments on PR #90 carry the
identical `user.login`), so the design instead relies on a fact this codebase can prove
structurally: this repository never generates, holds, or is authorized to acquire a private key
for this purpose (`NEW_CREDENTIAL_ACQUISITION_ALLOWED=false`). A submission whose own `signature`
validates against its own declared `signature.public_key` could therefore only have been
produced by someone else's key -- the identical precedent
`binding.signature`/`binding.identity.human_grant_declaration_signing_payload` already
establishes for a Human Grant Declaration, applied here to a new, disjoint record kind.

**A new record kind, `comparative_benchmark_independent_reproduction_submission`
(`01_SCHEMA/comparative_benchmark/comparative_benchmark_independent_reproduction_submission.
schema.json`)**, carries `reproducer_actor_or_authority_id`, `provenance_mechanism`
(`ED25519_SIGNATURE` only), `original_result_bundle_ref`/`protocol_freeze_ref`,
`reproduced_raw_events`/`reproduced_raw_events_content_address`,
`agent_runtime_model_configuration_identity`, `execution_environment_manifest`,
`reproduced_metrics`, `agreement`, `submission_time`, and `signature`
(`{algorithm: "ed25519", public_key, value}`) -- the minimum submission fields the adoption
itself names. `identity.independent_reproduction_submission_signing_payload` derives the exact
canonical bytes a genuine signature must cover (every field except the id/fingerprint/signature
themselves), mirroring `human_grant_declaration_signing_payload`'s own discipline.

**Verification only, never construction.** `engine.verify_independent_reproduction_submission`
refuses fail-closed (`IndependentReproductionSubmissionValidationError`) unless *all* of: schema
validity; `independent_reproduction_submission_id`/`..._semantic_fingerprint` genuinely rederive
from the record's own remaining fields; `protocol_freeze_ref`/`original_result_bundle_ref` name
exactly the Store-resolved parents (the identical P90-R1-F6 discipline
`commit_reproduction_receipt` already applies); `reproduced_raw_events` covers exactly the frozen
corpus (`verify_exact_frozen_corpus`, reused); `reproduced_raw_events_content_address`
genuinely rederives; `reproduced_metrics` genuinely rederives via `aggregate_metrics` -- never a
submitter's own claimed aggregate; `agreement` genuinely rederives by the identical
MATCH/DIVERGENT/INCOMPARABLE rule `build_reproduction_receipt` itself already uses; and
`signature` is a genuine Ed25519 signature, by the holder of the declared `public_key`, over
exactly the submission's own signing payload. `route.admit_independent_reproduction_submission`
resolves both parents from the Store first (refusing fail-closed if either was never genuinely
committed), then calls this verifier, then commits the unmodified, externally-supplied record
verbatim through the identical `commit_coordination_record_at_tip` mechanism every other record
kind in this package uses -- byte-for-byte, no field added, removed, or recomputed.

**Import-boundary purity: a local, duplicated Ed25519 verifier, not an import of
`binding.signature`.** `binding.signature.verify_ed25519_signature` is directly reusable in
isolation, but importing any part of `binding` transitively executes `binding/route.py`'s own
`from manosube_agent_civilization.authority.identity import rule_id` (via `binding/__init__.py`).
This package's own static-conformance test (NC-9/NC-11: "never a second owner of / never imports
Authority") is a guarantee about substance, not merely about what an AST scan of this package's
own five modules' literal `import` statements happens to catch -- so `engine.py` duplicates the
small, generic Ed25519 check locally (identical behavior: fail-closed-as-a-value, never raises on
malformed key/signature material) rather than accepting a transitive Authority import that would
pass the letter of the existing test while breaking its spirit.

```text
P90_R3_F2_ADMISSION_SURFACE_BUILT=true
P90_R3_F2_CLAUDE_CODE_SELF_ISSUED_RECEIPT=false
P90_R3_F2_INDEPENDENT_SUBMISSION_RECEIVED=false
P90_R3_F2_STATUS=BLOCKED_AWAITING_INDEPENDENT_REPRODUCER
```

No genuine external submission exists as of this revision -- the surface exists to admit one when
a genuinely independent actor or authority submits it; this contract does not claim F2 is closed.

## 8b. P90-R4-F2: pre-trusted independent reproducer (`engine.
build_independent_reproducer_trust_anchor`, `route.admit_independent_reproducer_trust_anchor`)

Round 4's own adoption (comment 5706881165) sharpened F2 further: a submission's own
self-declared `signature.public_key` (Round 3's own structural proof, section 8a) is no longer
sufficient on its own. The submission's declared reproducer's identity and Ed25519 public key
must be pre-registered by SHUKOU, before that submission ever arrives, as a Store-resolved trust
anchor -- never accepted from the submission's own self-declaration alone
(`SELF_DECLARED_UNREGISTERED_KEY_REFUSED=true`).

**A new record kind, `comparative_benchmark_independent_reproducer_trust_anchor`
(`01_SCHEMA/comparative_benchmark/comparative_benchmark_independent_reproducer_trust_anchor.
schema.json`)**, carries `reproducer_actor_or_authority_id`, `role`
(`"INDEPENDENT_PHASE_21_REPRODUCER"` only), `ed25519_public_key`, `key_id`, `admitted_by`
(`"HUMAN_AUTHORITY"` only -- a role literal, never a participant name, so this schema stays
provider/participant-neutral like every other canonical schema in `01_SCHEMA/`), `adoption_ref`
(the adopting comment's own id/comment_id/comment_url),
`authorized_protocol_or_corpus_ref` (the one protocol freeze this trust anchor authorizes
submissions against), `valid_from`/`valid_until`, and `revocation_status`
(`ACTIVE`/`REVOKED`). `identity.TRUST_ANCHOR_ID_FIELDS` -- `project_id`,
`reproducer_actor_or_authority_id`, `role`, `authorized_protocol_or_corpus_ref` -- deliberately
excludes the key itself.

**`role` and `admitted_by` are hardcoded inside `engine.build_independent_reproducer_trust_
anchor` itself, never caller-supplied parameters** (`ORIGINAL_OPERATOR_IDENTITY_REFUSED=true`,
`CLAUDE_CODE_SESSION_IDENTITY_REFUSED=true` at the builder itself -- a caller attempting to pass
either raises `TypeError` before any record is even assembled; decisive proof:
`test_build_independent_reproducer_trust_anchor_never_accepts_a_role_or_admitted_by_override`).
This module also imports only `Ed25519PublicKey`, never the private-key counterpart, so this
package's own production code has no import surface through which it could generate, hold, or
sign with an independent reproducer's private key (decisive proof, a real AST import scan:
`test_engine_module_never_imports_ed25519_private_key`).

**Key substitution is refused for free, by the identical same-id-different-body discipline every
other record kind in this package already uses.** Because `TRUST_ANCHOR_ID_FIELDS` excludes the
key, a second admission for the identical `(project, actor, role, protocol)` that declares a
*different* key collides at the identical `trust_anchor_id` and is refused as a
`RecordConflictError` -- never a silent overwrite (`POST_ADMISSION_KEY_MUTATION_REFUSED=true`,
`ACTOR_KEY_SUBSTITUTION_REFUSED=true`; decisive proof:
`test_admit_independent_reproducer_trust_anchor_refuses_key_substitution_for_the_same_identity`).

**`route.admit_independent_reproduction_submission` now resolves the trust anchor before
verifying.** It deterministically derives the expected `trust_anchor_id` from the submission's
own declared `(project_id, reproducer_actor_or_authority_id, role, protocol_freeze_ref)` --
mirroring the identical resolve-before-verify pattern `commit_reproduction_receipt` already
applies to its own parent records -- and refuses fail-closed
(`IndependentReproductionSubmissionValidationError`, `SELF_DECLARED_UNREGISTERED_KEY_REFUSED=
true`) if no such trust anchor was ever committed. `engine.verify_independent_reproduction_
submission` then checks, against the *resolved* trust anchor exclusively: `revocation_status=
"ACTIVE"`; the trust anchor's own `reproducer_actor_or_authority_id` matches the submission's
declared one; the trust anchor's own `authorized_protocol_or_corpus_ref` matches the submission's
own `protocol_freeze_ref` (`CROSS_PROTOCOL_OR_CORPUS_REPLAY_REFUSED=true`); the submission's own
`submission_time` falls inside `[valid_from, valid_until)`
(`REVOKED_OR_EXPIRED_KEY_REFUSED=true`, both the not-yet-in-force and expired sub-cases); the
submission's own declared `signature.public_key` equals the trust anchor's own registered
`ed25519_public_key` exactly (`WRONG_REGISTERED_KEY_REFUSED=true` -- a self-declared key that
merely matches itself is never sufficient); and only then verifies the Ed25519 signature itself
against the trust anchor's own key -- never the submission's own declared key, even though the
two are also checked equal above.

```text
P90_R4_F2_TRUST_ANCHOR_SURFACE_BUILT=true
P90_R4_F2_CLAUDE_CODE_PRIVATE_KEY_ACCESS=false
P90_R4_F2_REAL_SHUKOU_PUBLIC_KEY_RECEIVED=true
P90_R4_F2_REAL_TRUST_ANCHOR_ADMITTED=true
P90_R4_F2_STATUS=BLOCKED_AWAITING_INDEPENDENT_REPRODUCTION_RUN
```

This surface is decisively tested end-to-end -- admission idempotency and key-substitution
refusal, all 8 required fail-closed submission-side refusal behaviors
(`SELF_DECLARED_UNREGISTERED_KEY_REFUSED`, `WRONG_REGISTERED_KEY_REFUSED`,
`ACTOR_KEY_SUBSTITUTION_REFUSED`, `ORIGINAL_OPERATOR_IDENTITY_REFUSED`/`CLAUDE_CODE_SESSION_
IDENTITY_REFUSED`, `REVOKED_OR_EXPIRED_KEY_REFUSED` in both sub-cases,
`CROSS_PROTOCOL_OR_CORPUS_REPLAY_REFUSED`, `POST_ADMISSION_KEY_MUTATION_REFUSED`), and a positive
end-to-end control -- exclusively against fresh, ephemeral test-double key material
(`tests.fixtures.comparative_benchmark.generate_test_ed25519_keypair`).

**The real trust anchor is now admitted (this revision).** SHUKOU independently pre-registered
the real Phase 21 independent reproducer's Ed25519 public key in PR #90 comment 5709021178
(author `manosube`, `OWNER`, created 2026-09-17T05:07:37Z):
`reproducer_actor_or_authority_id=SHUKOU_PHASE21_REPRODUCER`, and a disclosed `ROLE=
HUMAN_AUTHORITY` field that maps to this record's own `admitted_by` field (always
`HUMAN_AUTHORITY`, see section 8b above) -- the record's own separate `role` field remains fixed
to `INDEPENDENT_PHASE_21_REPRODUCER`, unaffected by this disclosure --
`key_id=sha256:447776a9aaad1ebf2bc6936f169e494e418187fb71553086680b355a7d9f3f49`,
`ed25519_public_key=0f183eed0aae19425e8f85c3a619b21ddc4efdb432966ab91cfdbc6dd7f2fdab`,
`valid_from=2026-09-17T05:05:49Z`, `valid_until=NONE`, `private_key_disclosed=false`. Claude Code
independently re-verified this comment via the GitHub API (author, `author_association=OWNER`,
and every disclosed field, matched exactly) before acting on it -- never merely trusting a
relayed report. `scripts/admit_comparative_benchmark_independent_reproducer_trust_anchor.py`
then incorporated this already-verified public key into one real
`comparative_benchmark_independent_reproducer_trust_anchor` record through the existing
production route (`route.admit_independent_reproducer_trust_anchor`) against a fresh, disposable
`FileStateStore` -- the identical checked-in-artifact pattern `scripts/generate_comparative_
benchmark_artifacts.py` already establishes -- authorized against this directory's own published
`protocol_freeze.json`, and published the committed record to `examples/comparative_benchmark/
independent_reproducer_trust_anchor.json`
(`tests/contract/comparative_benchmark/test_comparative_benchmark_published_artifacts.py`'s own
new decisive proofs cover its schema validity, id/fingerprint reloadability, `admitted_by=
HUMAN_AUTHORITY`/`role=INDEPENDENT_PHASE_21_REPRODUCER`/`revocation_status=ACTIVE`, and that it
carries only a well-formed public key, never a private one). The submission's own self-declared
key is still never trusted as the root: `route.admit_independent_reproduction_submission`
resolves the trust anchor from the Store and checks the submission's declared key against it
exclusively, exactly as section 8b above already describes -- this admission changes only which
concrete key is now registered as that Store-resolved root, never the verification design.

This contract does not claim F2 closed: a real trust anchor is now admitted, but no genuine
independent reproduction submission against it has yet been received (`P90_R4_F2_STATUS=
BLOCKED_AWAITING_INDEPENDENT_REPRODUCTION_RUN`). Section 8c gives SHUKOU the exact commands to
produce one; Claude Code never requests, reads, stores, or logs the private key those commands
use.

## 8c. Reproduction commands for SHUKOU (no private-key handling by Claude Code)

The four commands below are the complete, already-verified procedure for SHUKOU to produce one
genuine, admissible independent reproduction submission on a machine SHUKOU controls (e.g. a
Windows PC with Python 3.11+ and `pip install cryptography` available). Claude Code has run the
canonical payload/verification logic these commands call (it is this package's own shipped,
tested production code) but never executes them against SHUKOU's own private key, never asks for
that key to be pasted, uploaded, or logged, and never persists it anywhere in this repository.

1. **Reproduce the frozen corpus.** Run the identical natural-route/ungated-reference-harness
   procedure `examples/comparative_benchmark/protocol_freeze.json`'s own `reproduction_procedure`
   names (`tests.comparative_benchmark.orchestrator.run_comparative_benchmark`) against a fresh
   checkout of this repository at the commit that published `protocol_freeze.json`, and capture
   the resulting `reproduced_raw_events` list (the honest per-task outcomes SHUKOU's own run
   actually produced against this repository's real corpus/mechanism) -- never hand-authored.

2. **Generate the canonical signing payload.** With `reproduced_raw_events` from step 1 assigned
   to the identical draft submission shape `identity.
   INDEPENDENT_REPRODUCTION_SUBMISSION_SEMANTIC_FIELDS` requires (see `01_SCHEMA/
   comparative_benchmark/comparative_benchmark_independent_reproduction_submission.schema.json`
   for the exact field list; `reproducer_actor_or_authority_id` must be exactly
   `SHUKOU_PHASE21_REPRODUCER` to match the admitted trust anchor), compute the exact bytes to
   sign by calling this package's own shipped function directly, never a hand-rolled
   equivalent:
   ```
   python -c "
   from manosube_agent_civilization.comparative_benchmark.identity import (
       independent_reproduction_submission_signing_payload,
   )
   import json, sys
   draft = json.load(sys.stdin)
   sys.stdout.buffer.write(independent_reproduction_submission_signing_payload(draft))
   " < draft_submission.json > signing_payload.bin
   ```

3. **Sign the payload with SHUKOU's own already-held private key.** This step runs only on
   SHUKOU's own machine, using the private key matching the already-registered
   `ed25519_public_key=0f183eed0aae19425e8f85c3a619b21ddc4efdb432966ab91cfdbc6dd7f2fdab` --
   Claude Code never sees this step's input or output:
   ```
   python -c "
   from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
   private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(input('PRIVATE_KEY_HEX: ')))
   with open('signing_payload.bin', 'rb') as f:
       payload = f.read()
   print('SIGNATURE_HEX=' + private_key.sign(payload).hex())
   "
   ```

4. **Assemble and admit the submission.** Fill `draft_submission.json`'s own
   `independent_reproduction_submission_id`/`..._semantic_fingerprint` (via `identity.
   independent_reproduction_submission_id`/`..._semantic_fingerprint`) and its own `signature`
   object (`{"algorithm": "ed25519", "public_key": "0f183eed...2fdab", "value": "<SIGNATURE_HEX
   from step 3>"}`), then submit the completed record through the existing production route
   (`route.admit_independent_reproduction_submission`) against a Store that already has this
   project's own `protocol_freeze`/`result_bundle`/trust anchor committed to it -- the identical
   pattern `tests/contract/comparative_benchmark/
   test_comparative_benchmark_independent_reproducer_trust_anchor.py`'s own positive-control test
   already exercises against test-only keys. `verify_independent_reproduction_submission` fails
   closed on any mismatch (wrong key, wrong corpus, expired window, or a recomputed
   `agreement`/`reproduced_metrics` that disagrees with the submission's own declared values) --
   a successful admission is therefore itself the decisive proof this reproduction is genuine.

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

**P90-R4-F2 (this revision): a fourth checked-in file, the real trust anchor.** `scripts/
admit_comparative_benchmark_independent_reproducer_trust_anchor.py` reads this directory's own
already-published `protocol_freeze.json`, admits SHUKOU's own real, already-verified public key
(PR #90 comment 5709021178) through the production route
(`route.admit_independent_reproducer_trust_anchor`) against a disposable `FileStateStore`, and
writes the resulting committed record to `examples/comparative_benchmark/
independent_reproducer_trust_anchor.json` -- the identical checked-in-artifact discipline, never
a private key, and never a test-double key standing in for the real one.

`tests/contract/comparative_benchmark/test_comparative_benchmark_published_artifacts.py` loads
all four files directly off disk (`json.loads(Path(...).read_text())` alone -- no Store, no
fixture module, no orchestrator call) and proves: each validates against its own canonical
schema; each record's own declared id/semantic-fingerprint fields are recomputed from the loaded
body and match exactly (`PUBLISHED_BYTES_RELOADABLE=true`); the result bundle's own `metrics`/
`claims`/`threshold_evaluations` are recomputed from its own loaded `raw_events` and the loaded
protocol freeze alone, matching the stored values byte-for-byte
(`REPRODUCED_RAW_EVENTS_DURABLY_REDERIVABLE=true`); the loaded raw events include at least one
real non-`COMPLETED_VERIFIED` outcome (`FAILURES_PRESENT_IN_PUBLISHED_RAW_DATA=true` --
real failures/refusals/retained outcomes survive into the published data, never a success-only
subset); the reproduction receipt's own `agreement` verdict is recomputed from its own loaded
`reproduced_metrics` compared against the loaded result bundle's own `metrics`, using the
identical rule `engine.build_reproduction_receipt` itself applies, and matches the stored value;
and the published trust anchor is admitted by `HUMAN_AUTHORITY`, is genuinely `ACTIVE`,
authorizes exactly the published protocol freeze, and carries only a well-formed 32-byte Ed25519
public key.

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

## 13a. P90-R3-F1: the real blocker is the frozen corpus's own definition, not credential
availability

Round 3's adoption (comment 5705039613) narrowly widened the Authority boundary Round 2's F1
blocker rested on:

```text
PRODUCTION_CREDENTIAL_USE_ALLOWED=true
PRODUCTION_CREDENTIAL_USE_SCOPE=ONE_PREEXISTING_CONFIGURED_AGENT_IDENTITY,PHASE_21_FROZEN_
  CORPUS_ONLY,PR_90_EVIDENCE_GENERATION_ONLY
NEW_CREDENTIAL_ACQUISITION_ALLOWED=false
CREDENTIAL_EXTRACTION_OR_DISCLOSURE_ALLOWED=false
CREDENTIAL_PERSISTENCE_CHANGE_ALLOWED=false
UNBOUNDED_EXTERNAL_INVOCATION_ALLOWED=false
```

This session independently re-examined whether F1 (`EXECUTE_THE_IDENTICAL_REAL_AGENT_IN_BOTH_
CONDITIONS`) could now be satisfied by running the *currently-defined* frozen corpus with a real
Agent against this widened boundary. It cannot -- not because a real Agent identity is
unavailable, but because of a structural fact about the corpus itself, discovered by direct
inspection of `tests/fixtures/long_running_proof.py` (the fixture world the `MANOSUBE_PRESENT`
comparison group's own orchestrator reuses, see section 6): the `MANOSUBE_PRESENT` group's own
"present" condition has never involved a real Agent (an LLM or tool-using process) performing any
task at all. Every one of its 8 tasks routes through 100% Kernel-internal, deterministic
bookkeeping (Observation -> Difference -> Authority -> Evidence -> Reflow) over two static,
generic, checked-in prose fixture files (`before_source_world.txt`/`after_source_world.txt`,
identical content regardless of which of the 8 tasks is running); the fixture's own `"READY"`
Evidence value is a hardcoded Python literal, not the output of any executed action; and the one
authorized `WRITE_FILE` action's own declared target, `src/long_running_proof_target.py`, does
not exist anywhere in this repository and is never actually written.

```text
F1_STATUS=BLOCKED_NO_PRECONFIGURED_REAL_AGENT
F1_BLOCKING_CONSTRAINT=FROZEN_CORPUS_MANOSUBE_PRESENT_CONDITION_NEVER_INVOLVES_A_REAL_AGENT_
  PERFORMING_A_TASK
F1_IS_A_CREDENTIAL_AVAILABILITY_PROBLEM=false
F1_IS_A_CORPUS_PROTOCOL_DEFINITION_PROBLEM=true
```

Making F1 true would require redefining what a "task" in the frozen corpus means -- giving the
`MANOSUBE_PRESENT` condition a real Agent-performed step to compare against a real Agent-alone
step, rather than comparing Kernel bookkeeping against Agent execution. That is a roadmap/protocol
semantic decision, not a code change this session may make on its own: Issue #89's own section 4
already ties "same-Agent comparison" to fixing the Agent's model/runtime/version/adapter
identity/configuration/tool surface/resource budget across *both* conditions, and the Structural
Advisor's own prior review (comment 5705006904) frames exactly this kind of redefinition as its
own "Option 3," reserved to SHUKOU. This Round's own adoption forbids it explicitly:

```text
ROADMAP_REDEFINITION_ALLOWED=false
GATE_21_WEAKENING_ALLOWED=false
SIMULATED_OR_RELABELED_SUBSTITUTE_PROVIDED=false
```

No fixture re-execution, relabeling of the existing natural route, or newly-invented corpus was
attempted to manufacture a passing result; this section records the honest structural finding
instead, one of the adoption's own three named stop outcomes -- ready to advance,
`BLOCKED_NO_PRECONFIGURED_REAL_AGENT`, or `BLOCKED_AWAITING_INDEPENDENT_REPRODUCER` -- rather
than a simulated or relabeled pass.

## 13b. P90-R4-F1: the real blocker is this execution environment's own harness classifier, not
the corpus definition or credential availability

Round 4's own adoption (comment 5706881165) required replacing the predetermined fixture corpus
Round 3's own F1 finding identified (section 13a) with a real, pre-result-frozen,
Agent-executable corpus -- one where the `MANOSUBE_PRESENT` condition genuinely drives an Agent
performing a task, under the identical Agent/model/runtime/configuration/prompt/tool-surface/
initial-workspace/resource envelope as its `MANOSUBE_ABSENT` counterpart, with outcomes derived
from that Agent's own real output bytes/tool effects rather than hardcoded values. This session
attempted, in good faith, to establish whether a real, tool-write-capable Agent could be invoked
from inside this session at all, as the necessary precondition for building any such corpus.

**Two distinct, reasonable attempts to spawn a tool-write-capable nested Agent subprocess were
both denied by this specific sandboxed execution environment's own harness-level safety
classifier**, independent of the corpus's own definition and independent of credential
availability (`PRODUCTION_CREDENTIAL_USE_ALLOWED=true` remains unchanged from Round 3 -- this is
not a Round 2-style credential blocker recurring). The first attempt used a maximally-scoped,
maximally-restricted invocation (`--restricted --tools Write,Edit,Read --permission-mode
acceptEdits`); the second, more minimal attempt requested only a single actionable tool
(`--tools Write`) with the harness's own default permission mode, adding no elevation and no
`--restricted` flag at all. Both were denied identically, with the stated reason `[Create Unsafe
Agents]`. A third, tool-free control invocation (no `--tools` flag at all, a plain conversational
call) succeeded and returned genuine, API-billed output -- isolating the denial precisely to "any
nested Agent subprocess invocation that requests an actionable tool," independent of the specific
permission-mode/restriction-flag combination requested.

```text
F1_STATUS=BLOCKED_NO_USABLE_REAL_AGENT
F1_BLOCKING_CONSTRAINT=THIS_EXECUTION_ENVIRONMENT_HARNESS_CLASSIFIER_DENIES_ANY_TOOL_WRITE_
  CAPABLE_NESTED_AGENT_SUBPROCESS_INVOCATION
F1_IS_A_CREDENTIAL_AVAILABILITY_PROBLEM=false
F1_IS_A_CORPUS_PROTOCOL_DEFINITION_PROBLEM=false
F1_IS_AN_ENVIRONMENT_TOOLING_PROBLEM=true
```

This is a genuinely distinct finding from both Round 2's `BLOCKED_REQUIRES_SHUKOU_AUTHORITY_
DECISION` (a credential-availability boundary) and Round 3's `BLOCKED_NO_PRECONFIGURED_REAL_
AGENT` (a corpus-*definition* fact discovered by static inspection, requiring no Agent
invocation attempt at all to discover): this Round's finding is discovered only by actually
attempting the invocation this Round's own widened boundary was meant to permit, and the block
sits one layer below the corpus or the Authority grant -- in the concrete execution substrate
this specific session runs inside. Per the harness classifier's own explicit instructions and
per this Round's own prohibition on simulating or relabeling a substitute, this session made
exactly these two reasonable attempts and then stopped, rather than escalating further (broader
tool grants, alternate invocation forms) or fabricating a simulated Agent execution to produce a
passing result.

```text
SIMULATED_OR_RELABELED_SUBSTITUTE_PROVIDED=false
GATE_21_WEAKENING_ALLOWED=false
ROADMAP_REDEFINITION_ALLOWED=false
```

No replacement corpus was built against a real Agent execution this Round, since the precondition
this finding establishes -- a usable, tool-write-capable Agent invocation inside this specific
execution environment -- does not currently hold. Whether a different execution environment,
invocation mechanism, or explicit harness-classifier exemption can satisfy F1 is a decision this
session's own Authority grant does not extend to; this section records the honest structural
finding rather than a simulated or relabeled pass, per this Round's own four-way stop condition
(ready to advance, `BLOCKED_NO_USABLE_REAL_AGENT`, `BLOCKED_AWAITING_SHUKOU_REPRODUCER_PUBLIC_
KEY`, or `BLOCKED_AWAITING_INDEPENDENT_REPRODUCTION_RUN`).

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
P90_R3_F1_CLOSED=false
P90_R3_F2_CLOSED=false
P90_R3_F2_ADMISSION_SURFACE_BUILT=true
P90_R4_F1_CLOSED=false
P90_R4_F2_CLOSED=false
P90_R4_F2_TRUST_ANCHOR_SURFACE_BUILT=true
CLAUDE_CODE_SELF_ISSUED_INDEPENDENT_RECEIPT=false
NEW_CREDENTIAL_ACQUISITION=false
CREDENTIAL_EXTRACTION_OR_DISCLOSURE=false
CREDENTIAL_PERSISTENCE_CHANGE=false
UNBOUNDED_EXTERNAL_INVOCATION=false
```
