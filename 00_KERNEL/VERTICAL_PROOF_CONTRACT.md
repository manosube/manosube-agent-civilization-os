# Vertical Proof Contract

```text
DOC_TYPE=VERTICAL_PROOF_CONTRACT
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=VERTICAL-PROOF-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
CONSTITUTIONAL_AUTHORITY=HUMAN
CANONICAL_KERNEL_ELEMENT_ADDED=false
KERNEL_ELEMENT=NONE_PROOF_AND_ACCEPTANCE_LAYER
CANONICAL_CYCLE_CHANGED=false
COMPLETION_GATE_WEAKENED=false
ADOPTED_BY=SHUKOU_ADOPTION_ADOPT_PHASE_8_VERTICAL_PROOF_ISSUE_41
CORRECTED_BY=SHUKOU_ADOPTION_PHASE_8_STRUCTURAL_REVIEW_ROUND_1
CORRECTED_BY=SHUKOU_ADOPTION_PHASE_8_FINAL_STRUCTURAL_REVIEW_ROUND_2
CORRECTED_BY=SHUKOU_ADOPTION_PHASE_8_FINAL_CLOSURE_ROUND_3
```

## 0. Revision History

```text
Round 0 (initial adoption, Issue #41): first version of this document and the proof it
  describes.

Round 1 (SHUKOU Phase 8 structural-review round 1, adopted): 構造参謀's independent
  re-observation of PR #42's real HEAD found five findings and required two further audits,
  all adopted by SHUKOU directly (not auto-adopted from bot output --
  BOT_FINDING_AUTO_ADOPTION=false, INDEPENDENT_STRUCTURAL_REPRODUCTION=true). Reproduced and
  corrected in place, on the same PR/branch:

  P8-R1-F1  Observation Evidence now genuinely precedes and grounds the Difference (§4, §7).
  P8-R1-F2  A real committed non-CLOSED (RETAINED) transition is now proven, distinct from
            the pre-existing rejected-CLOSED-proposal control (§6).
  P8-R1-F3  Replay/conflict is now proven over the full real vertical-proof record set, not
            an empty stub (§6).
  P8-R1-F4  A semantic fixture-input-class sensitivity matrix now covers all twelve named
            input classes, not one (§8A).
  P8-R1-F5  reflow()'s own authority_ref/change_refs/observation_refs/reflow_instant are now
            independently re-verified against real, already-verified records before commit
            -- the prior "descriptive metadata" non-claim is withdrawn (§7).
  Canonical-record-construction audit: invariant_evaluation now goes through its own real
            public producer; candidate_invariant_evaluation_binding/candidate_claim_
            evaluation_binding/_event were confirmed contractually caller-assembled, not a
            bypassed producer (§8B).
  Source Snapshot fixture truthfulness: both before/after Source Snapshots now digest real,
            checked-in fixture bytes at a locator that genuinely resolves (§3).

Round 2 (SHUKOU Phase 8 final structural-review round 2, adopted): 構造参謀's independent
  re-observation of PR #42's real HEAD after Round 1 found three further findings, all
  adopted directly by SHUKOU (again not auto-adopted bot output --
  BOT_FINDING_AUTO_ADOPTION=false, INDEPENDENT_STRUCTURAL_REPRODUCTION=true). Reproduced and
  corrected in place, on the same PR/branch:

  P8-R2-F1  Round 1 closed the placeholder-Evidence fixed point only at the final
            Difference -- the *accepted* request graph reaching Sufficiency, Closure and
            Reflow still carried the provisional, placeholder-seeded requests. Now closed
            across the whole accepted request graph and every persisted record (§4).
  P8-R2-F2  reflow()'s own provenance check (P8-R1-F5) compared only bare id sets, which
            silently accepted a right-id/wrong-kind reference, collapsed a duplicate, and
            could not distinguish a missing reference from an extra one. Now full canonical
            reference equality -- kind, id and any asserted digest, never id alone (§7).
  P8-R2-F3  The prior round's AUTHORITY_EVALUATION_INSTANT non-claim ("fully inert") was
            true only along the one no-Approval AUTONOMOUS-by-rule route it tested. The
            field is a transient admission context that governs real time-bound Approval
            admission on the route where an Approval must actually bind, and is still never
            part of authority_decision_id either way (§7, §8A).
  Reflow Instant semantic decision: reflow_instant's own causal-order contract against the
            Closure Evaluation's evaluated_at is now stated precisely (equal-or-later valid
            is admitted, an invalid timestamp fails closed with a typed error, a different
            valid instant may produce a different transaction identity) (§6).

Round 3 (SHUKOU Phase 8 final-closure round 3, adopted): 構造参謀's independent
  re-observation of PR #42's real HEAD after Round 2 found one further finding, adopted
  directly by SHUKOU (again not auto-adopted bot output -- BOT_FINDING_AUTO_ADOPTION=false,
  INDEPENDENT_STRUCTURAL_REPRODUCTION=true). Reproduced and corrected in place, on the same
  PR/branch:

  P8-R3-F1  The verification Observation's own observation_evidence_refs genuinely named
            the auxiliary Change-Free Verification Evidence Round 2 introduced -- but that
            Evidence, and the before-/post-change Observations two already-persisted
            Evidence records also named, were never themselves persisted. The persisted
            reference graph is now closed over this Finding's own explicitly-scoped
            vocabulary: an observation record's own source_snapshot_refs/observation_
            evidence_refs, and an observation_evidence record's own observed_result.
            observation_ref/lineage.derived_from/lineage.predecessor_evidence_refs (§4, §7).
```

---

## 1. Purpose

This document is the Issue #41 "Required package / A. Proof contract" deliverable.

It defines, for the v0.1 Natural Cycle's one required vertical proof
(`00_KERNEL/COMPLETION_SEMANTICS.md` §10 `v0.1`, `00_KERNEL/KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md`
§14): the Proof Entry, the Fixture Boundary, the Identity Ledger, the Terminal Receipt, Failure
Semantics, and this proof's own explicit non-claims.

This document is a verification projection. It owns no Kernel truth of its own, adds no ninth
Kernel element, and creates no new canonical record type merely to summarize test output.

```text
KERNEL_ELEMENT_COUNT=8
THIS_DOCUMENT_ADDS=0
```

---

## 2. Proof Entry

The one public proof entry is:

```text
tests/natural_cycle/proof.py :: run_vertical_proof(tmp_path, *, fault=None)
```

`run_vertical_proof` drives, exactly once, through real public canonical owners only
(`manosube_agent_civilization.{observation,difference,authority,change,evidence,reflow,state,
store}`) and returns a dict exposing every stage's real record and the Identity Ledger (§4).
It hand-writes no canonical record and reproduces no owner's own algorithm
(`NO_MANUAL_INTERMEDIATE_CANONICAL_RECORD_CONSTRUCTION=true`).

A caller that needs a *refused* route (a required negative/interruption route,
`tests/natural_cycle/test_vertical_proof_negative_routes.py`) calls
`assemble_vertical_proof_route(tmp_path, *, fault=None)` instead -- the identical assembly,
short of the one `reflow()` call and the reconstruction that follow it -- so a mutation can be
applied to exactly one already-real input before that one call, never a second hand-built
assembly that could silently drift from the one real route this module proves.

```text
tests/natural_cycle/proof.py :: assemble_vertical_proof_route(tmp_path, *, fault=None)
```

---

## 3. Fixture Boundary

The one Fixture Boundary is:

```text
tests/fixtures/vertical_proof.py
```

Per Issue #41's own Frozen semantic decision 2
(`PHASE_8_FIXTURE_BINDING_NE_PHASE_9_BINDING=true`, `FIXTURE_BINDING_CANONICAL_BUSINESS_
AUTHORITY=false`), this module supplies bounded *source-world inputs* only:

```text
PERMITTED FIXTURE CONTENT
= Objective / Objective Revision (Human-Authority input, no producing owner of its own)
+ initial semantic State domain content
+ bounded before-observation source input
+ bounded after-observation source input
+ one Difference-producing Target mismatch
+ applicable Authority rules
+ a Change request action/scope matching those rules
+ explicit evaluation/reflow instants
+ a satisfiable Closure Policy
```

It never supplies a completed Observation, Difference, Authority Decision, Change, Evidence,
Evidence Sufficiency Result, Closure Evaluation, lifecycle event, State transition, or
successor State -- every one of those is produced, every run, by calling its own real public
owner (§2).

```text
FIXTURE_MAY_SUPPLY=
  OBJECTIVE
  + INITIAL_STATE_DOMAIN_CONTENT
  + BEFORE_SOURCE_WORLD_INPUT
  + AFTER_SOURCE_WORLD_INPUT
  + AUTHORITY_RULES
  + EXPLICIT_INSTANTS

FIXTURE_MUST_NEVER_SUPPLY=
  OBSERVATION
  + DIFFERENCE
  + AUTHORITY_DECISION
  + CHANGE
  + EVIDENCE
  + EVIDENCE_SUFFICIENCY_RESULT
  + CLOSURE_EVALUATION
  + DIFFERENCE_LIFECYCLE_EVENT
  + STATE_TRANSITION
  + STATE_N_PLUS_1
```

All fixture bytes are pinned: literal, explicit-instant, content-addressed-where-applicable
values, never a wall-clock read, an environment-dependent path, or a secret-bearing value.

**Source Snapshot fixture truthfulness (P8-R1, corrected).** The before/after Source
Snapshots' own `content_digest` is the real `sha256` of two real, checked-in fixture files
(`tests/fixtures/vertical_proof/before_source_world.txt`/`after_source_world.txt`), read and
hashed at fixture-module load time -- the identical pattern `tests/state_helpers.py`'s own
`real_kernel_source_snapshot` already uses for the real Kernel source. Neither the locator
nor the digest is an arbitrary assertion about content nobody checked.

This module is deliberately self-contained -- it does not import `tests/difference_helpers.py`,
`tests/authority_helpers.py`, `tests/change_helpers.py` or `tests/evidence_helpers.py`, even
where a literal shape below matches theirs field-for-field (that is fidelity to the frozen
`01_SCHEMA/` request shapes, not duplication). The one deliberate exception is the real
Kernel-source-witness machinery `tests/state_helpers.py` already exposes
(`real_kernel_source_snapshot`/`real_kernel_git_objects`/`genesis_source_snapshot_records`/
`initial_state`) -- Kernel-wide, already-pinned, already-canonical infrastructure every Phase 7
test already depends on, not business/test-support content this proof would otherwise have to
re-derive.

---

## 4. Identity Ledger

The proof mechanically asserts the exact producer→consumer identity handoff for every name
Issue #41's own "F. Identity ledger assertions" section lists. `run_vertical_proof`'s returned
`identity_ledger` dict carries each as a real, non-empty, content-addressed value -- never a
URL, filename, list position, or fixture label standing in for it:

```text
ISSUE #41 NAME                    IDENTITY_LEDGER KEY
objective_revision                objective_revision_id
initial_state revision/fingerprint initial_state_revision, initial_state_fingerprint
before_observation                 before_observation_id
difference + lifecycle head        difference_id, difference_lifecycle_head_ref
authority_decision                 authority_decision_id
change                              change_id
after_observation                   change_result_observation_id, verification_observation_id
observation_evidence                 observation_evidence_id
change_result_evidence                change_result_evidence_id
evidence_sufficiency_result            evidence_sufficiency_id
closure_evaluation                      closure_evaluation_id
difference_lifecycle_event                difference_lifecycle_event_id
state_transition                            state_transition_ref
final_state revision/fingerprint/lineage_head final_state_revision, final_state_fingerprint,
                                               final_lineage_head_ref
```

**Disclosed design decision -- two `after_observation` identities.** `reflow()`'s own G8
anti-self-closing gate refuses a `CHANGE_BOUND` closure whose independent re-observation shares
any Observation identity with the Change-result Evidence's own reproduced lineage (a Change
cannot verify itself). This proof therefore performs three genuinely separate real Observation
Engine calls rather than one: `before_observation_id` (grounds the Difference and both Evidence
records' `before_state`), `change_result_observation_id` (grounds Change-result Evidence's own
`after_state`), and `verification_observation_id` (grounds Reflow's own independent
`reobservation`). Issue #41's own "after_observation" name is therefore carried by two distinct
real identities here, both asserted genuinely distinct from each other and from
`before_observation_id` (`tests/natural_cycle/test_vertical_proof.py::
test_the_identity_ledger_names_every_required_stage_with_a_real_id`).

**Corrected (P8-R1-F1): `observation_evidence_id` now genuinely grounds the Difference.**
The prior version of this proof placed a bare, unresolved placeholder reference
(`EVID-VP8-0001`) in the before-Observation's own declared `observation_evidence_refs` field
-- schema-valid, but never the real Evidence this Difference's own `observation_evidence_refs`
field (populated verbatim from it by `difference.engine._evidence_union`) ought to name. Since
`observation.identity.OBSERVATION_SEMANTIC_FIELDS` excludes this field from an Observation's
own content-addressed identity, `tests/natural_cycle/proof.py::observe_before` now derives the
real Observation Evidence from a first, placeholder-seeded Observation, then re-observes with
the corrected, real reference before deriving the Difference from that corrected bundle -- the
identical real `observation_id` either way, but the Difference's own `observation_evidence_
refs` field now names the real Evidence, proven by `tests/natural_cycle/test_vertical_proof.py::
test_the_difference_actually_consumes_the_real_observation_evidence`.

**Corrected (P8-R2-F1): the Evidence fixed point closes across the whole accepted request
graph, not only the final Difference.** P8-R1-F1 proved the final Difference's own
`observation_evidence_refs` was placeholder-free, but `observe_before`'s own returned
`observation_evidence_request` -- what Sufficiency, Closure and Reflow actually consume --
was still the provisional, placeholder-seeded request. `tests/natural_cycle/proof.py`'s
`observe_before`, `observe_change_result`, and `observe_verification` each now run the full
ten-step fixed point (provisional Observation Request → provisional Observation →
provisional Evidence, seeding a corrected Observation Request → corrected Observation →
corrected Difference/Evidence Request → corrected Evidence, verified to reproduce the
identical id the provisional seed established) and return *only* the corrected artifacts --
`FULL_ACCEPTED_REQUEST_GRAPH_PLACEHOLDER_COUNT=0`, proven by `tests/natural_cycle/
test_vertical_proof.py::test_the_evidence_fixed_point_closes_across_the_full_accepted_
request_graph` over an exact leaf-value scan of `before["observation_evidence_request"]`,
`sufficiency.request`, `closure_request`, `reflow_kwargs`, the final Difference, and every
record this run's own committed transaction manifest names -- never a single-field check
this round's own finding showed was insufficient. The post-change and independent-
re-observation Observations (`change_result_observation_id`, `verification_observation_id`)
are closed the identical way: the former's own natural real backing Evidence is the
Change-result Evidence itself (self-referential, exactly like the before-Observation), the
latter's is an auxiliary Change-Free Verification Evidence pairing it with the same
before-Observation the real Difference was derived from.

**Withdrawn (P8-R3-F1): the auxiliary Change-Free Verification Evidence is not "never
persisted or referenced downstream."** The paragraph above, as this document stood after
Round 2, claimed the auxiliary Verification Evidence played "the identical role the
before-Observation's own seed Evidence plays" -- true of the *provisional* seed inside the
Evidence fixed point, but false of what actually reaches the Store: the verification
Observation's own `observation_evidence_refs` field genuinely names this auxiliary
Evidence's real id, and once that Observation is persisted (which it always was, via
Reflow's own G8 reobservation admission), the reference is real and must resolve --
reproduced directly: the field named a real, well-formed id that `store.resolve_record`
could not find. See §7's own corrected section and §4's continuation below for what
changes.

**Corrected (P8-R3-F1): the persisted reference graph now closes, not only the accepted
request graph.** Round 2 proved every *request* reaching Sufficiency/Closure/Reflow was
placeholder-free; it did not prove every *persisted record*'s own declared reference
resolves through the Store. Three gaps existed simultaneously: the verification
Observation's own `observation_evidence_refs` named the auxiliary Change-Free Verification
Evidence, never itself persisted; Observation Evidence's own `observed_result.
observation_ref` and Change-result Evidence's own `observed_result.observation_ref`/
`lineage.derived_from` named the before-Observation and the post-change Observation, and
neither of those two Observations was itself persisted as a Store record either (confirmed
directly: `store.resolve_record(project_id, "observation", before_observation_id)` returned
`None` on the unmodified Round 2 HEAD, even though the real Evidence records naming it were
already committed).

`tests/natural_cycle/proof.py`'s `observe_change_result` and `observe_verification` now
return their own corrected artifacts too (a Change-result Evidence request/record; a
verification Evidence request/record) rather than discarding them, and
`assemble_vertical_proof_route` threads the auxiliary Verification Evidence request through
a new, dedicated `reflow()` keyword, `provenance_only_evidence_requests` (never fed into
`evaluate_closure`/`evaluate_sufficiency`, so it can never move a Sufficiency verdict or a
Candidate's own `resolution_mode` -- `AUXILIARY_VERIFICATION_EVIDENCE_COUNTS_TOWARD_
SUFFICIENCY=false`). `route.py::_admitted_records` gains three additions, all reusing only
existing canonical owners (no second Evidence/Observation/Store/Lineage/Recovery owner is
created anywhere in this correction):

```text
_admitted_observations_from_evidence_requests  re-observes (real Observation owner,
                                                 manosube_agent_civilization.observation.
                                                 observe) the before/post-change/
                                                 verification Observation every admitted
                                                 Evidence request's own observation_request/
                                                 post_change_observation_request/
                                                 verification_observation_request field
                                                 names, re-verifies each against its own
                                                 content-addressed identity
                                                 (observation.identity.observation_identity),
                                                 and persists it
_admitted_provenance_only_evidence             reproduces (real Evidence owner,
                                                 evidence.engine.derive_evidence) the
                                                 auxiliary provenance-only Evidence request
                                                 a caller supplies and persists the result,
                                                 entirely outside evaluate_closure/
                                                 evaluate_sufficiency
_merge_verified_record                          the one merge primitive both of the above
                                                 (and the existing source_snapshot
                                                 admission) now go through: two independent
                                                 reproductions that claim the identical
                                                 (kind, id) but disagree on body raise
                                                 before any write --
                                                 SAME_KIND_ID_DIFFERENT_BODY=CORRUPTION_
                                                 OR_VALIDATION_ERROR, neither
                                                 FIRST_BODY_WINS nor LAST_BODY_WINS
```

An admitted Observation's own `source_snapshot_refs` is resolved against an *extended*
snapshot pool (the existing, G8/G4-validated `closure_request["source_snapshots"]` plus a
new, separate `auxiliary_source_snapshots` `reflow()` keyword) rather than widening the
gate-validated pool itself -- widening it would have loosened G4/G8's own exact-match
checks against the reobservation's own declared snapshot set, an unrelated regression this
correction must not introduce. This is how the before-Observation's own real Source
Snapshot (`BEFORE_SOURCE_SNAPSHOT`, previously never persisted either, since the existing
`closure_request["source_snapshot_refs"]`/`["source_snapshots"]` pair only ever carried the
after-state one) now resolves too, once the before-Observation itself is admitted.

`PERSISTED_REFERENCE_GRAPH_CLOSED=true`, `UNRESOLVED_STORE_OWNED_REFERENCE_COUNT=0` -- both
proven over this Finding's own explicitly-scoped reference vocabulary (§7), not a blind
full-graph sweep: `tests/natural_cycle/test_vertical_proof_reference_closure.py` reads the
real committed transaction's own manifest, resolves every record it names, recursively
walks each `observation`/`observation_evidence` record's own known reference-bearing
fields, and resolves every edge found -- through a fresh `FileStateStore` instance and a
brand-new Python subprocess too, never only the in-process objects this run produced.

A negative control this Finding itself requires -- `provenance_only_evidence_requests`
supplied but empty -- fails the whole route closed (`ReflowValidationError`, before any
State/Lineage/record/manifest mutation): the persisted verification Observation's own real
reference to the auxiliary Evidence would otherwise silently never resolve. This check is
gated on the caller having supplied `provenance_only_evidence_requests` at all (even an
empty list) rather than enforced unconditionally on every `reflow()` call: several
pre-existing Phase 5-7 test fixtures already persist an Observation whose own declared
`observation_evidence_refs` is a bare, never-resolved placeholder, predating this Finding
and unrelated to it (`ISSUE_22_OR_PR_27_CHANGES=false`, and retrofitting those fixtures is
outside `P8-R3-F1`'s own authorized scope) -- an unconditional gate would have refused all
of them. Confirmed directly: enforcing the check unconditionally during this correction's
own development broke 20 pre-existing, otherwise-unrelated Phase 7 tests; gating it on
opt-in restored them to green with zero behavior change for any caller that does not pass
this keyword.

---

## 5. Terminal Receipt

The one terminal receipt a successful run produces is `run_vertical_proof`'s returned
`reflow_result` dict (`{"evaluation", "decision", "next_semantic_state", "committed_state",
"state_transition_ref", "event"}`, exactly `reflow()`'s own public return shape) together with
`reconstructed_state` -- the same project's State, reconstructed from a *fresh*
`FileStateStore` instance over only the persisted backend, never the in-process object
`run_vertical_proof` itself returned.

```text
ONE_FULL_NATURAL_CYCLE_PASS
=
ONE_BOUND_FIXTURE_WORLD
+ EVERY_CANONICAL_RECORD_PRODUCED_BY_ITS_REAL_OWNER
+ EXACT_IDENTITY_HANDOFF_AT_EVERY_BOUNDARY  (§4)
+ ONE_ATOMIC_REFLOW_COMMIT
+ FINAL_STATE_RECONSTRUCTS_IDENTICALLY
+ NO_MATERIAL_CONTRADICTION
+ ALL_APPLICABLE_V01_INVARIANTS_PASS
```

`reflow_result["decision"]["to_status"] == "CLOSED"` only after the atomic Reflow commit itself
succeeded -- proven, not merely asserted, by the fact that a real `committed_state` and
`state_transition_ref` exist at all (a failed commit raises before `run_vertical_proof` returns
anything).

---

## 6. Failure Semantics

A refused or non-closing route is not an error condition external to this contract -- it is a
proven, repository-resident outcome in its own right
(`tests/natural_cycle/test_vertical_proof_negative_routes.py`, Issue #41 item E, all fourteen
bullets). Three invariants hold across every one of them:

```text
A REFUSED ROUTE NEVER PARTIALLY APPLIES
= the Store's committed State stays at exactly its pre-transition revision
+ that State remains reconstructable from a fresh Store instance

A NON-SATISFIED CLOSURE EVALUATION NEVER BECOMES CLOSED
= sufficient Evidence alone does not close (item E4)
+ stale Evidence does not close (item E6)
+ a material contradiction does not close (item E6)
+ a Change/Evidence self-closing collision does not close (item E7)

A CRASH AT ANY STORE STAGE NEVER EXPOSES A PARTIAL CYCLE
= recovery converges to exactly one of two States -- the pre-transition genesis State
  (crash before COMMIT_INTENT was durably written) or the one fully-closed successor
  (at or after it) -- never a mixture (items E8/E9)
```

**A rejected proposal is not the same claim as a real committed non-CLOSED outcome (P8-R1-F2,
corrected).** The first invariant above proves a *rejected* `CLOSED` proposal leaves the Store
untouched. Issue #41 separately requires a genuinely `NOT_SATISFIED` Evaluation, correctly
proposed as `BLOCKED`/`RETAINED` instead of `CLOSED`, to actually commit --
`tests/natural_cycle/test_vertical_proof_negative_routes.py::
test_p8r1f2_a_genuinely_not_satisfied_evaluation_commits_a_real_retained_transition` proves
both claims separately: a real `RETAINED` State revision commits, the real lifecycle event
persists and resolves, a fresh Store instance reconstructs exactly what was committed, and the
Difference stays open -- through the real terminal-reason Evidence binding (R7-F4) every
non-`CLOSED` outcome already requires, not a hand-waved refusal.

Two guarantees this contract still claims -- identical replay is a no-op, and a conflicting
replay under the same transaction identity is rejected (items E10/E11) -- are proven at the
Reflow commit owner (`manosube_agent_civilization.reflow.commit.commit_reflow`) directly, one
real layer below the full `reflow()` orchestration, because `reflow()`'s own caller-side
staleness pre-check makes a literal second `reflow()` call unable to be a byte-identical replay
by construction (its freshly-loaded `current_state` has already moved). This is a disclosed
choice of layer, not a narrowing of the guarantee.

**The replay/conflict guarantee is proven over the full real record set, not a stub (P8-R1-F3,
corrected).** The `commit_reflow`-layer test above uses an empty `records`/`evidence_refs`
transaction, which never exercised the vertical proof's own ~50-plus-record manifest (every
mandatory Invariant Evaluation, the Candidate claim-evaluation event, the Completion Record,
both Evidence records, the Observation, the Source Snapshot, the Kernel witness).
`tests/natural_cycle/test_vertical_proof_negative_routes.py::
test_p8r1f3_the_full_vertical_transaction_record_set_replays_as_a_true_no_op` closes that gap:
it reads the real committed transaction's own manifest (`state/recovery/<tx>/manifest.json`,
the identical file `FileStateStore` itself reads and writes), resolves every real record body
through the public `resolve_record`, replays the identical `store.commit(...)` call, and
asserts the lineage event count, per-kind record file count, `load_current`, and
`reconstruct` are all bit-for-bit unchanged -- then asserts a single-field-tampered replay
under the same transaction identity is rejected before any write, with the Store still
unchanged afterward.

**Reflow Instant causal-order semantics (P8-R2, adopted).** `reflow_instant` is the real
transition time and is folded into the transaction's own content address
(`reflow.identity.transaction_id`) -- it is not required to exactly equal the Closure
Evaluation's own `evaluated_at`, only to never precede it:

```text
REFLOW_INSTANT_IS_TRANSITION_TIME=true
REFLOW_INSTANT_EXACTLY_EQUALS_EVALUATED_AT=false
REFLOW_INSTANT_MUST_NOT_PRECEDE_CLOSURE_EVALUATION=true
LATER_VALID_REFLOW_INSTANT_ALLOWED=true
REFLOW_INSTANT_INCLUDED_IN_TRANSACTION_ID=true
DIFFERENT_VALID_REFLOW_INSTANT_MAY_PRODUCE_DIFFERENT_TRANSACTION_ID=true
```

"Wrong instant" is fixed as `INVALID_TIMESTAMP OR REFLOW_INSTANT_BEFORE_CLOSURE_EVALUATION`,
never merely "differs from a fixture's own pinned value". `route.py::_preflight_verify_
reflow_provenance` now parses `reflow_instant` through the canonical `instant()` grammar
before any comparison and raises this Kernel's own typed `ReflowValidationError` on a
malformed value (previously a bare `ValueError` could escape uncaught), and still refuses
one that is well-formed but causally early. `tests/natural_cycle/
test_vertical_proof_reflow_provenance_matrix.py` proves all five required rows: an invalid
timestamp is rejected, an instant before `evaluated_at` is rejected, one exactly equal to it
is allowed, one strictly after it is allowed, and two otherwise-identical routes committed
at two different valid instants real a genuinely different transaction identity -- every
rejection proven to leave the Store's committed State, Lineage and manifest untouched.

---

## 7. Explicit Non-Claims

This proof does not claim, and its own tests do not assert, any of the following -- restated
here from Issue #41's own "Existing non-claims" and "Explicit non-claims" sections so this
contract cannot be read more broadly than the Issue that adopted it:

```text
G9_NON_NULL_REQUIRED_OBSERVATION_SCOPE=NOT_CLAIMED_FAIL_CLOSED
FULL_EXTERNAL_RUNTIME_CHANGE_EXECUTION=NOT_CLAIMED
FULL_NINE_KIND_TERMINAL_CAUSE_GROUNDING=NOT_CLAIMED
DOMAIN_CLAIMS_PROJECTION=NOT_CLAIMED
THREE_DEFERRED_REOPEN_TRIGGERS=NOT_CLAIMED

PHASE_9_BINDING_COMPLETE=false
KERNEL_V0_1_COMPLETE=false
CHANGE_EXECUTOR_IMPLEMENTED=false
EXTERNAL_OPERATION_EXECUTED=false
CAUSALITY_PROVEN=false
RUNTIME_PROVEN=false
INDEPENDENT_VERIFICATION_IMPLEMENTED=false
BOOT_IMPLEMENTED=false
CLI_IMPLEMENTED=false
TEMPORARY_AGENT_IMPLEMENTED=false
GITHUB_ADAPTER_IMPLEMENTED=false
AUTONOMOUS_CHANGE_IMPLEMENTED=false
MULTI_AGENT_IMPLEMENTED=false
```

**Disclosed scope boundary (P8-R3-F1): the persisted-reference-graph closure claim is
scoped to an explicit reference vocabulary, not every reference this Kernel's own records
carry.**

```text
AUXILIARY_VERIFICATION_EVIDENCE_ROLE=PROVENANCE_ONLY
AUXILIARY_VERIFICATION_EVIDENCE_PERSISTED=true
AUXILIARY_VERIFICATION_EVIDENCE_COUNTS_TOWARD_SUFFICIENCY=false
PERSISTED_REFERENCE_GRAPH_CLOSED=true
UNRESOLVED_STORE_OWNED_REFERENCE_COUNT=0
```

Both of the last two hold over the closed, explicitly-managed reference vocabulary this
Finding is about: an `observation` record's own `source_snapshot_refs` and
`observation_evidence_refs`, and an `observation_evidence` record's own `observed_result.
observation_ref`, `lineage.derived_from` (`observation`-kind members only), and `lineage.
predecessor_evidence_refs`. Recognized structurally (a dict shaped like `common/
reference.schema.json` -- `kind`+`id`, both non-empty strings -- with `kind` restricted to
`{observation, observation_evidence}`), never by a fuzzy text search over key names.

References this Kernel names but never gives a Store-owned producer of its own --
`difference`, `change`, `authority_decision`, `artifact`, `negative_evidence` -- are outside
this scope, not silently treated as resolved (no second canonical owner is created for any
of them here, or anywhere else in this correction, to bring them into scope).
`closure_evaluation.difference_event_head_ref` in particular names the Difference's own
genesis lifecycle event, which this Kernel's own design never persists as a separate
`difference_event` record at genesis time -- confirmed directly: it does not resolve
through `store.resolve_record` even before any `reflow()` call is ever made, on every round
of this proof including this one. That non-resolution predates P8-R3-F1, is not caused by
it, and is disclosed here rather than folded into this Finding's own `PERSISTED_REFERENCE_
GRAPH_CLOSED` claim -- a materially different, wider claim this round was not asked to make
and did not reproduce as a real gap requiring correction.

In Completion Ladder terms (`00_KERNEL/COMPLETION_SEMANTICS.md` §2), this proof establishes
`L6 CONNECTED` and `L7 NATURALLY_REACHABLE` for the v0.1 Natural Cycle. It does not claim
`L8 RUNTIME_PROVEN` (no target Runtime's real Authority/Filesystem/Process/Network/Timing/
Identity conditions are exercised -- the fixture's own before/after Source Snapshots are
declared, deterministic inputs, never the output of an executed Change) and it does not claim
`L9 REPEATEDLY_PROVEN` beyond the specific, bounded repetitions item E10/E11 assert (idempotent
replay, conflicting-payload rejection) -- a single successful `pytest` run of this suite is
`L7`, not `L8` or `L9`, and remains so regardless of how many times CI re-runs it.

**Withdrawn (P8-R1-F5): `authority_ref`/`change_refs`/`observation_refs`/`reflow_instant` are
no longer an inert non-claim -- they are now independently re-verified.** The prior version of
this document recorded these four `reflow()` keyword arguments as descriptive-only metadata,
since probing had shown a mismatched value did not raise. SHUKOU's Phase 8 structural-review
round 1 held that Issue #41's own acceptance conditions govern this, not a PR body's own
non-claim, and required a real fix. `reflow()` (`src/manosube_agent_civilization/reflow/
route.py::_preflight_verify_reflow_provenance`, called for every outcome, immediately before
`_admitted_records`/commit) now independently re-verifies all four, before any commit:

```text
change_refs        must equal closure_request.producing_change_refs exactly, as a full
                    canonical reference (kind, id and any asserted digest -- never id
                    alone), as an UNORDERED_SET (canonical sort, duplicate rejection, exact
                    member equality) -- a field G-gates already bind to the real, reproduced
                    Change
authority_ref       wherever a real change_result_evidence_requests exists, must equal --
                    as a full canonical SINGLE_REFERENCE, exact kind and id, no unknown
                    field -- the real Authority Decision reference that reproduction
                    (derive_evidence) actually carries
observation_refs    wherever a reobservation is declared, must equal its own real
                    after_observation_refs exactly, under the identical full canonical
                    UNORDERED_SET equality (the identical set G8 already resolves)
reflow_instant      may never precede the Closure Evaluation's own real evaluated_at (§6)
```

Proven by five new negative controls in `tests/natural_cycle/test_vertical_proof_negative_
routes.py` (wrong change/authority/observation refs, a too-early `reflow_instant`), all
raising before any State or record mutation, and by the retained Phase 3-7 suite passing
unchanged (six pre-existing fixtures in `tests/unit/reflow/test_structural_review_
correction.py` were themselves correcting a `observation_refs=[]` placeholder their own tests
never needed checked before -- fixed to pass their own real, already-computed
`reobservation.after_observation_refs`, not weakened).

**Corrected (P8-R2-F2): canonical reference equality, not bare id-set equality.** The
Round 1 check above compared only `{ref["id"], ...}` Python sets for `change_refs`/
`observation_refs`, and only a bare `ref["id"]` membership test for `authority_ref` --
`REFERENCE_ID_ONLY_EQUALITY_SUFFICIENT=false`: this silently accepted a reference naming the
right id under the wrong `kind`, collapsed a genuine duplicate reference into one, and could
not distinguish a missing reference from an extra one once only ids were compared.
`route.py::_reference_key`/`_require_unordered_reference_set_equal`/`_require_single_
reference_member` now compare the whole reference (kind, id, and any asserted digest),
reject an unknown field, and reject a duplicate rather than silently collapsing it.
`tests/natural_cycle/test_vertical_proof_reflow_provenance_matrix.py` proves every required
negative control -- right-id/wrong-kind, duplicate, missing, extra, and wrong-id, for both
`change_refs` and `observation_refs`, plus right-id/wrong-kind, wrong-id, and an unknown
field for `authority_ref` -- each raising before any State, Lineage, record or transaction
manifest mutation.

**Corrected (P8-R2-F3): `AUTHORITY_EVALUATION_INSTANT` is a transient admission context, not
an inert field.** The Round 1 finding ("fully inert") held only along the one route its own
test exercised -- a rule granting `AUTONOMOUS` outright, with no Approval ever consulted for
the outcome. `authority/approval.py::binding_mismatches` reads `evaluation_time` against
every Approval's own `approved_at`/`expires_at` validity window whenever an Approval must
actually bind a request (`HUMAN_APPROVAL_REQUIRED` with a real Approval on file), so the
field is not inert in general:

```text
AUTHORITY_EVALUATION_INSTANT_ROLE=TRANSIENT_ADMISSION_CONTEXT
AUTHORITY_EVALUATION_INSTANT_IN_DECISION_ID=false
AUTHORITY_EVALUATION_INSTANT_AFFECTS_TIME_BOUND_ADMISSION=true
```

What is unchanged from the original finding: the real Authority Decision's own
content-addressed `authority_decision_id` never includes `evaluation_time` (mirroring
State's own Semantic Fingerprint excluding `observed_at`/`observer` by design --
`00_KERNEL/KERNEL_INDEX.md` §2). `tests/natural_cycle/
test_vertical_proof_fixture_sensitivity_matrix.py::
test_p8r2f3_authority_evaluation_instant_governs_time_bound_approval_admission` proves a
real, time-bound Approval: before its `approved_at` and after its `expires_at`, the Approval
does not bind and authorization is not granted; within the window, it binds and is used;
two valid times landing in the identical real outcome share one Decision id, while a time
that genuinely changes the outcome changes the id too -- never because the raw timestamp
was folded into the identity itself, only because the outcome it produced actually differed.
`test_p8r1f4_authority_evaluation_instant_is_inert_on_the_no_approval_route` (renamed from
the withdrawn claim) keeps proving the original, narrower route's own real behavior
unchanged.

---

## 8A. Semantic Fixture-Input-Class Sensitivity Matrix (P8-R1-F4)

`tests/natural_cycle/test_vertical_proof_fixture_sensitivity_matrix.py` proves, for every one
of the twelve semantic input classes Issue #41 names (one single field's sensitivity --
item E2's own before-Observation value -- does not stand in for the rest), the real,
empirically observed downstream effect:

```text
INPUT_CLASS                       ACTUAL_CHANGED_IDENTITY_OR_VERDICT        FAIL_CLOSED_OR_REDERIVED
OBJECTIVE_OR_OBJECTIVE_REVISION    difference_id / objective_semantic_       re-derived
                                   fingerprint change
BEFORE_OBSERVATION_VALUE           Difference verdict changes (0 vs 1)      re-derived (item E2)
SOURCE_SNAPSHOT_IDENTITY_OR_DIGEST observation_id changes                   re-derived
AUTHORITY_RULE                     Authority verdict changes                fails closed
REQUESTED_ACTION                   Authority verdict changes                fails closed
CHANGE_SCOPE                       Authority verdict changes                fails closed
POST_CHANGE_OBSERVATION            Evidence identity / observed_result      re-derived (status/
                                   change                                  level disclosed inert)
VERIFICATION_OBSERVATION           Reflow refuses CLOSED                    fails closed
CLOSURE_POLICY                     Sufficiency verdict changes              re-derived
EVIDENCE_INSTANT                   Evidence derivation refused              fails closed (item E3)
AUTHORITY_EVALUATION_INSTANT       inert on no-Approval AUTONOMOUS-by-rule  transient admission
                                   route; governs real time-bound Approval  context (P8-R2-F3);
                                   admission where an Approval must bind;   never in
                                   never in authority_decision_id           authority_decision_id
REFLOW_INSTANT                     Reflow refuses CLOSED                    fails closed (P8-R1-F5)
```

## 8B. Canonical-Record-Construction Audit (P8-R1)

"Previous test reuse of a hand-built record is not the same proof as calling the real owner"
(SHUKOU, P8-R1). Every record kind the Candidate-assembly step produces was audited against
this repository's own real, public producers:

```text
RECORD_KIND                          REAL_PUBLIC_PRODUCER              PRODUCED_OR_ASSEMBLED
invariant_evaluation                 difference.invariant_evaluation.  PRODUCED (corrected --
                                      build_invariant_evaluation        was hand-duplicated by
                                                                        a shared test helper;
                                                                        now called directly,
                                                                        see tests/natural_
                                                                        cycle/proof.py::
                                                                        phase8_invariant_
                                                                        bindings_and_
                                                                        evaluations)
candidate_invariant_evaluation_       none (contractually caller-       CALLER_ASSEMBLED
  binding                            assembled, G19 -- only a real,    (correct; only a real
                                      public identity function exists, ID function is
                                      candidate_invariant_evaluation_   available; kept)
                                      binding_id)
candidate_claim_evaluation_binding    none (contractually caller-       CALLER_ASSEMBLED
                                      assembled, G21 -- "caller         (correct; already uses
                                      supplies the pool, Reflow         the real
                                      validates and persists it",      build_completion_record
                                      reflow/claims.py's own module     for its embedded
                                      docstring)                       Completion Record; kept
                                                                        unchanged)
candidate_claim_evaluation_event      none (same G21 caller-assembled   CALLER_ASSEMBLED
                                      design; a real, public identity   (correct; kept
                                      function exists,                 unchanged)
                                      candidate_claim_evaluation_
                                      event_id)
candidate_completion_record           difference.completion.           PRODUCED (already
                                      build_completion_record           correct before this
                                                                        round)
```

Rule applied: a real public producer existing anywhere in this repository means the test
helper stops hand-duplicating it and calls that producer directly; a record kind whose own
contract (`CLOSURE_POLICY.md`'s G19/G21 sections, `reflow/claims.py`'s own module docstring)
names caller-assembly as the design stays caller-assembled, using only the real, public
identity/fingerprint functions that already exist for it. No second canonical owner was
created for any record kind in this audit.

---

## 9. Reading Order

```text
1. 00_KERNEL/KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md §14 (this proof's place in the v0.1 route)
2. 00_KERNEL/COMPLETION_SEMANTICS.md §2, §10 (the Completion Ladder and v0.1 Natural Cycle)
3. This document
4. tests/fixtures/vertical_proof.py (the Fixture Boundary)
5. tests/natural_cycle/proof.py (the Proof Entry)
6. tests/natural_cycle/test_vertical_proof.py (item D, the required successful route)
7. tests/natural_cycle/test_vertical_proof_negative_routes.py (item E, the required
   negative/interruption routes)
8. tests/natural_cycle/test_vertical_proof_fixture_sensitivity_matrix.py (§8A, item E.2's
   full input-class matrix)
9. tests/natural_cycle/test_vertical_proof_reflow_provenance_matrix.py (§7's P8-R2-F2
   canonical-reference-equality negative controls and §6's Reflow Instant causal-order
   proof)
10. tests/natural_cycle/test_vertical_proof_reference_closure.py (§4/§7's P8-R3-F1
    persisted-reference-graph closure proof, its explicit scope boundary, and its
    required negative controls)
```
