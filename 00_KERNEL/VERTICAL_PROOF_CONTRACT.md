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

Two guarantees this contract still claims -- identical replay is a no-op, and a conflicting
replay under the same transaction identity is rejected (items E10/E11) -- are proven at the
Reflow commit owner (`manosube_agent_civilization.reflow.commit.commit_reflow`) directly, one
real layer below the full `reflow()` orchestration, because `reflow()`'s own caller-side
staleness pre-check makes a literal second `reflow()` call unable to be a byte-identical replay
by construction (its freshly-loaded `current_state` has already moved). This is a disclosed
choice of layer, not a narrowing of the guarantee.

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

In Completion Ladder terms (`00_KERNEL/COMPLETION_SEMANTICS.md` §2), this proof establishes
`L6 CONNECTED` and `L7 NATURALLY_REACHABLE` for the v0.1 Natural Cycle. It does not claim
`L8 RUNTIME_PROVEN` (no target Runtime's real Authority/Filesystem/Process/Network/Timing/
Identity conditions are exercised -- the fixture's own before/after Source Snapshots are
declared, deterministic inputs, never the output of an executed Change) and it does not claim
`L9 REPEATEDLY_PROVEN` beyond the specific, bounded repetitions item E10/E11 assert (idempotent
replay, conflicting-payload rejection) -- a single successful `pytest` run of this suite is
`L7`, not `L8` or `L9`, and remains so regardless of how many times CI re-runs it.

**Disclosed design decision -- `authority_ref`/`change_refs`/`observation_refs`/
`reflow_instant` are `reflow()`'s own descriptive lifecycle-event metadata for a `CLOSED`
route, not independently re-verified identities at that layer.** Probing confirmed that, for
the successful `CHANGE_BOUND` → `CLOSED` route, `reflow()` accepts a mismatched value for any
of these four keyword arguments without raising -- the actual identities G1-G22 verify for a
`CLOSED` outcome live inside `closure_request` itself (`producing_change_refs`,
`change_result_evidence_requests`/`_refs`, `reobservation.after_observation_refs`, the policy's
own freshness fields), not in these four convenience parameters. This proof's own negative
tests (item E3) therefore mutate the closure_request keys G1-G22 actually check, and this
contract records the four inert kwargs as a truthful, bounded non-claim rather than asserting a
"wrong X fails closed" behavior at a layer that does not implement it. This is an existing,
unwidened Phase 7 boundary -- not a gap this Phase 8 proof introduces or is asked to close.

---

## 8. Reading Order

```text
1. 00_KERNEL/KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md §14 (this proof's place in the v0.1 route)
2. 00_KERNEL/COMPLETION_SEMANTICS.md §2, §10 (the Completion Ladder and v0.1 Natural Cycle)
3. This document
4. tests/fixtures/vertical_proof.py (the Fixture Boundary)
5. tests/natural_cycle/proof.py (the Proof Entry)
6. tests/natural_cycle/test_vertical_proof.py (item D, the required successful route)
7. tests/natural_cycle/test_vertical_proof_negative_routes.py (item E, the required
   negative/interruption routes)
```
