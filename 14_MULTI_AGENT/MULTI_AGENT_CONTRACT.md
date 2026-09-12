# Multi-Agent Dynamic Execution Contract (Phase 19, Issue #77)

```text
DOC_TYPE=MULTI_AGENT_CONTRACT
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=MULTI-AGENT-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_MULTI_AGENT_ORCHESTRATION_ADAPTER
MULTI_AGENT_OWNER_COUNT=1
PUBLIC_MULTI_AGENT_ENTRY_POINT_COUNT=3
STRUCTURAL_REVIEW_ROUNDS_APPLIED=0
TEST_SUITE_PRESENT_AT_DELIVERY=true
CAPABILITY_VOCABULARY_SIZE=1
MAX_AGENT_SLOTS=3
```

## 1. Position

This layer selects 1, 2 or N temporary Agents from one canonical Difference and its required
capabilities, executes them independently without creating a permanent Agent organization,
preserves each output's own provenance and every disagreement, produces one Evidence-aggregation
input for the existing Evidence owner, and releases every temporary Agent. It is **not** a ninth
Kernel element (the Kernel is fixed at eight: `KERNEL_ELEMENT_COUNT=8`,
`ONE_KERNEL_ELEMENT_PER_PACKAGE=true`) -- an adapter/orchestration layer, exactly as Boot, CLI,
Agent Runtime, Independent Verification, Projection, Runtime, Model Runtime, URL Boot and Change
Executor already are. It mints no Authority, no canonical State, no Observation, no Evidence
sufficiency, no truth by consensus, no permanent Agent hierarchy, and no completion.

```text
MULTI_AGENT_OWNER_COUNT=1
PUBLIC_MULTI_AGENT_ENTRY_POINT_COUNT=3
```

This was written as a first delivery against Issue #77's own adopted proposal; no structural
review round has yet run (`STRUCTURAL_REVIEW_ROUNDS_APPLIED=0`). A real test suite (unit,
contract, integration) was written alongside this document and is cited throughout §6 and §12 by
real file and test name -- never asserted without a citation.

## 2. Public signature

```python
from manosube_agent_civilization.multi_agent import (
    open_dynamic_execution_plan,
    execute_dynamic_execution_plan,
    route_orchestration_to_evidence,
)

opened = open_dynamic_execution_plan(
    store, agent,                      # agent: a live Phase 12 TemporaryAgent (coordinator role)
    project_id=project_id,
    project_binding_id=project_binding_id,
    difference_ref={"kind": "difference", "id": difference_id},
    boundary_ref={"kind": "model_execution_boundary", "id": boundary_id},
    model_execution_grant_refs=[{"kind": "model_execution_grant", "id": grant_id}],
    adapter_identity={"adapter": "fake_model_adapter", "version": "0.1"},
    opened_at="2026-09-11T01:00:00Z",
    expires_at="2026-09-11T02:00:00Z",
)
opened["plan"]                          # the immutable, content-addressed plan
opened["plan_ref"]                      # {"kind": "multi_agent_dynamic_execution_plan", "id": ...}
opened["model_execution_decision"]      # the reproduced Model Runtime Authority Decision

executed = execute_dynamic_execution_plan(
    store, agent,                      # a fresh coordinator liveness proof (may differ from above)
    project_id=project_id,
    project_binding_id=project_binding_id,
    plan_ref=opened["plan_ref"],
    model_adapter_factory=lambda: SomeModelAdapter(),   # called once per slot not yet recorded
    executed_at="2026-09-11T01:30:00Z",
)
executed["plan"]                        # the resolved, re-verified plan
executed["slot_outputs"]                # one per slot's own attempt (fresh or replayed)
executed["release_receipts"]            # one per slot
executed["conflict_set"]                # P19-C6's own deterministic classification
executed["aggregation_input"]           # P19-C7's own aggregation input (refused if any
                                         # release is not RELEASED)

handed_off = route_orchestration_to_evidence(
    store, agent,
    project_id=project_id,
    project_binding_id=project_binding_id,
    plan_ref=opened["plan_ref"],
    evidence_request_template=evidence_request,  # verification_result_provenance must be None
    completed_at="2026-09-11T01:40:00Z",
)
handed_off["orchestration_receipt"]     # the terminal, immutable receipt
handed_off["evidence_refs"]             # the genuinely linked Evidence chain this plan produced
```

## 3. Disclosed judgment calls

Numbered so a later structural review can cite each by number, exactly as
`CHANGE_EXECUTOR_CONTRACT.md` §3 and `MODEL_RUNTIME_CONTRACT.md` already do for their own
deliveries.

1. **One shared Model Work Unit per plan, opened once, at plan-open time.** The proposal's own
   sketch left open whether each slot opens its own Work Unit or all slots share one. This
   delivery shares exactly one: every slot of one plan is independent execution of the *same*
   canonical question (one Difference, one required capability), so opening N Work Units for
   what is semantically one authorized unit of work assigned to N Agents would mean N separate
   Authority evaluations of an identical question -- wasteful, and not what "select N Agents from
   the canonical Difference and its required capabilities" (singular capabilities, plural Agents)
   means. `open_dynamic_execution_plan` therefore calls the existing
   `model_runtime.open_model_work_unit` exactly once, embeds the resulting `model_work_unit_ref`
   and the Work Unit's own `authority_ref` (the real, reproduced Authority Decision reference)
   directly into the plan record, and `execute_dynamic_execution_plan` calls the existing
   `model_runtime.execute_model_work_unit` once per slot against that one shared reference.
2. **The plan's own `authority_ref` is therefore never null in this delivery**, superseding an
   earlier draft of this design that left it nullable pending judgment call 1 above. Since every
   Work Unit this package ever opens is already, unconditionally, Authority-gated by the existing
   owner (Model Runtime refuses to open a Work Unit with no real Human Authority grant at all),
   and this plan always opens exactly one, the plan's own `authority_ref` is always the real,
   reproduced decision reference -- P19-C4's own "reproduced Authority decision reference where
   execution requires Authority" is satisfied structurally, not merely documented.
3. **A single, plan-level admitted `adapter_identity`, checked at execute time.** The plan
   declares one admitted adapter identity at open time; at execute time, every slot's own adapter
   (from the caller's `model_adapter_factory`) must declare that identical identity, or the slot
   is refused (a caller-input malformation, propagated uncaught -- see judgment call 5). This
   delivery does not implement per-slot heterogeneous admitted adapter identities: with exactly
   one capability existing system-wide, there is no genuine reason yet to assign two Agents in
   one plan two different admitted model/runtime identities, and inventing that mechanism now
   would be exercising a capability this delivery cannot honestly test. `execution_bounds.
   max_concurrent_slots`, `execution_order`, `conflict_policy`, and `release_policy` are each
   closed to exactly one declared value today for the identical reason -- see `types.py`'s own
   docstring for each.
4. **"CONCURRENT" is an honest, narrower claim than real OS-level parallelism.** This package
   builds no thread pool, `asyncio` task group, or subprocess fan-out: `execute_dynamic_
   execution_plan`'s own slot loop is an ordinary, sequential Python `for` loop. What
   "CONCURRENT" states, and what is actually proven (by this package's own static conformance
   suite -- no `threading`/`asyncio`/`multiprocessing` import anywhere in this package, and no
   slot's own outcome is ever read, branched on, or required by an earlier slot's own execution),
   is that the orchestration layer itself imposes no execution-order *dependency* between any two
   slots of one plan. A future delivery that genuinely threads or schedules slots across real
   concurrency primitives could adopt this identical plan/slot/conflict-set shape unchanged; this
   delivery does not build it.
5. **Two literal `start_temporary_agent` call sites, not one, and each disclosed.** Model
   Runtime's own equivalent static-conformance discipline pins exactly one literal call site,
   because Model Runtime never constructs an execution-purpose Agent itself -- it only ever
   receives one from its caller. This package's own entire purpose is the opposite: it *is* the
   caller that constructs 1/2/N execution-purpose Agents. The two call sites are therefore
   genuinely distinct roles, not an accidental drift toward a second, competing mechanism:
   `route._fresh_execution_contract` (a snapshot-and-immediately-release freshness proof, reused
   at every commit boundary -- the identical role Model Runtime's own function of the same name
   plays) and the per-slot construction inside `route._execute_one_slot` (the actual multi-Agent
   fan-out point). `tests/contract/multi_agent/test_multi_agent_static_conformance.py`'s own
   `test_start_temporary_agent_has_exactly_two_disclosed_call_sites` pins this exact count and
   names both functions by AST inspection, and
   `test_every_start_temporary_agent_call_site_is_guarded_by_a_releasing_finally` proves every
   Agent either function constructs is released even if the code between construction and
   release raises.
6. **A caught `ModelRuntimeError`/`AgentRuntimeError` inside one slot's own attempt becomes a
   first-class, honestly-classified `UNAVAILABLE` outcome for that slot alone; any other,
   genuinely unexpected exception propagates and aborts the whole orchestration call.** The
   proposal's own text asks for judgment here ("I believe this is the correct, more decisive
   interpretation... but exercise your own judgment and disclose the choice"). This delivery
   catches exactly the two error families Model Runtime and Agent Runtime themselves define as
   *operational* failures -- a stale contract, a malformed reference, an adapter defect, a
   released Agent -- and converts each into a typed slot-level outcome so one failed slot never
   loses provenance for the others (P19-C5's own "missing, refused, failed... remain first-class"
   and V6's own "partial execution" requirement). A bare `Exception` catch-all is deliberately
   *not* used: it would make a genuine coordinator/infrastructure crash indistinguishable from an
   ordinary operational failure, and would make V6's own crash-recovery proof untestable (there
   would be no way to simulate "the process died mid-slot" if every exception were silently
   absorbed into a typed outcome). The `finally` clause around every constructed Agent still
   releases it regardless of which of the two paths is taken (judgment call 5).
7. **`attempt_ordinal` is always `1`; this delivery implements no automatic retry of a failed
   attempt within one plan.** Once an attempt (of any outcome, including a failure) is recorded
   at a slot's own single, deterministic attempt identity, a later `execute_dynamic_execution_
   plan` call for the identical plan always replays it verbatim -- there is no mechanism in this
   delivery that allocates a second `attempt_ordinal` for the same slot. A caller wanting a
   genuinely fresh second attempt must open a new plan (a new content address, since at minimum
   `opened_at` must differ) rather than reuse the existing one; P19-C9's own "conflicting reuse of
   ... an attempt identity must refuse" is what a second, different-content attempt at the
   *identical* identity would trigger, so this delivery does not also build a parallel
   allow-a-retry escape hatch that would compete with that refusal.
8. **A deliberate deviation from the usual "id == full-content hash" convention, for five of this
   package's six record kinds.** See `identity.py`'s own module docstring for the full reasoning
   (repeated in outline in §4.1 below): `multi_agent_slot_output`, `multi_agent_agent_release_
   receipt`, `multi_agent_conflict_set`, `multi_agent_evidence_aggregation_input` and
   `multi_agent_orchestration_receipt` each address their own `<kind>_id` from a *narrow*,
   natural-key projection (which plan, which slot, which attempt ordinal -- never the outcome,
   timing, or membership content), while their own `<kind>_semantic_fingerprint` still covers the
   complete record. This is what makes "resolve before executing" (replay) and "a
   different-content commit at the identical natural key refuses" (conflicting reuse) native
   Store behaviours rather than application-level bookkeeping this package would otherwise have
   to build and keep consistent by hand. `multi_agent_dynamic_execution_plan` is the one exception
   -- P19-C2 itself requires every field that can widen execution or change provenance to
   participate in the plan's own identity, so the plan uses the ordinary full-content convention
   every other Kernel record already uses.
9. **`route.py`'s own private commit/freshness/validation helpers are reused directly by
   `evidence_handoff.py`, rather than each module keeping an independent copy.** This repository's
   established convention -- each *package* keeps its own private `deep_freeze`/canonicalization
   copy rather than importing another package's -- decouples *independently owned* adapter-layer
   packages from one another (Model Runtime from Runtime, Runtime from Projection). It was never a
   rule against one package's own two files sharing one committer. Model Runtime's own
   `evidence_handoff.py` needed no committer of its own at all (`derive_evidence` commits nothing
   to Store); this package's own terminal orchestration receipt genuinely must be committed, and
   duplicating `route.py`'s Compare-And-Swap retry and authority-freshness machinery a second time
   inside the *same* single-owner package would be a second, divergent implementation of the
   identical logic, not decoupling. `test_multi_agent_static_conformance.py`'s own
   `test_evidence_handoff_reuses_the_routes_own_commit_helper_rather_than_a_second_one` proves this
   reuse is exactly one call site.
10. **The Evidence hand-off is its own, separate, Store-resolution-based route -- never folded
    into `execute_dynamic_execution_plan` itself.** The proposal's own text left this open ("fold
    this into execute_dynamic_execution_plan directly if that's cleaner -- your call, document
    it"). This delivery keeps them separate for the identical reason Model Runtime's own
    `execute_model_work_unit` and `evidence_handoff.route_model_execution_to_evidence` are two
    separate calls: the hand-off resolves everything it needs from the Store alone (never an
    in-memory object from a possibly different process/session), which is what makes it
    genuinely replayable and lets a caller defer or retry the hand-off independently of
    execution. `evidence_handoff._receipt_from_envelope` rebuilds an equivalent, ephemeral
    `ModelExecutionReceipt` purely from a real, resolved, integrity-checked Envelope -- safe by
    construction, since every field it copies is the identical fact the existing hand-off itself
    re-resolves and re-verifies before trusting anything.
11. **Genesis-immutable aggregation input; `evidence_refs` live only on the terminal orchestration
    receipt, appended after the hand-off runs.** See `evidence_handoff.py`'s own module docstring.
    The aggregation input is a pure function of the admitted output set, the conflict set, the
    absent slots and the release receipts -- stable and content-addressed independent of what
    Evidence eventually makes of it. This is exactly the separation P19-C7 draws between "an
    aggregation input" and "an Evidence verdict": this package never marks anything sufficient,
    and the one record that could be mistaken for a verdict (the aggregation input) never even
    carries a field shaped like one.

## 4. Canonical owner

```text
multi_agent/route.py               the two orchestration routes (open_dynamic_execution_plan,
                                    execute_dynamic_execution_plan); the freshness-check helper
                                    and every resolve-and-verify function for the plan, slot
                                    output, release receipt, conflict set and aggregation input
multi_agent/evidence_handoff.py    the one Evidence hand-off (route_orchestration_to_evidence);
                                    resolve-and-verify for the terminal orchestration receipt
multi_agent/engine.py              pure record builders and schema validators for all six kinds;
                                    no Store I/O, no clock, no Agent, no Adapter, no Evidence call
multi_agent/identity.py            deterministic identities -- full-content for the plan, narrow
                                    natural-key for the other five (see §3 item 8)
multi_agent/selection.py           P19-C1's own bounded, total, caller-immune slot selection
multi_agent/types.py               closed vocabularies (mostly reused from Model Runtime -- see
                                    §7), the package's own private deep_freeze
multi_agent/errors.py              the typed refusal vocabulary
```

### 4.1 Canonical records

```text
multi_agent_dynamic_execution_plan
    id: full-content hash over PLAN_SEMANTIC_FIELDS (schema_version, project_id,
    project_binding_ref, boot_state_revision, boot_semantic_fingerprint, difference_ref,
    capability_selection_fingerprint, slots, model_work_unit_ref, authority_ref,
    adapter_identity, execution_order, execution_bounds, conflict_policy, release_policy,
    opened_at, expires_at)

multi_agent_slot_output
    id: narrow natural key (schema_version, project_id, plan_ref, slot_index, attempt_ordinal)
    fingerprint: full content, additionally covering capability, attempt_id,
    model_execution_envelope_ref, outcome, result_fingerprint, outcome_detail, started_at,
    ended_at

multi_agent_agent_release_receipt
    id: narrow natural key (schema_version, project_id, plan_ref, slot_index)
    fingerprint: full content, additionally covering attempt_id, release_status, released_at

multi_agent_conflict_set
    id: narrow natural key (schema_version, project_id, plan_ref)
    fingerprint: full content, additionally covering considered_slot_output_refs, members

multi_agent_evidence_aggregation_input
    id: narrow natural key (schema_version, project_id, plan_ref)
    fingerprint: full content, additionally covering conflict_set_ref,
    admitted_slot_output_refs, unresolved_capabilities, absent_slot_output_refs,
    release_receipt_refs

multi_agent_orchestration_receipt
    id: narrow natural key (schema_version, project_id, plan_ref)
    fingerprint: full content, additionally covering slot_output_refs, release_receipt_refs,
    conflict_set_ref, aggregation_input_ref, evidence_refs, orchestration_outcome, completed_at
```

## 5. Canonical route

```text
open_dynamic_execution_plan:
  live Phase 12 coordinator contract (require_exact_state=True)
  -> Store-resolved, schema-valid, identity-recomputed Difference
  -> selection.select_agent_slots (P19-C1) -- bounded, total, caller-immune
  -> existing Model Runtime open_model_work_unit (Authority evaluated exactly once, by the
     existing evaluator, never reimplemented here) -- one shared Work Unit for the whole plan
  -> canonical, content-addressed plan, committed once

execute_dynamic_execution_plan:
  live Phase 12 coordinator contract (require_exact_state=False)
  -> resolve-and-verify the plan
  -> for each slot, in slot_index order:
       resolve its own attempt identity (computable before any Agent exists)
       -> already recorded?  resolve-and-verify and reuse verbatim, zero new Agent/adapter
       -> otherwise: construct one fresh Phase 12 Temporary Agent
          -> existing Model Runtime execute_model_work_unit, against the plan's shared Work Unit
          -> (caught ModelRuntimeError/AgentRuntimeError becomes a typed UNAVAILABLE outcome;
              any other exception propagates -- see §3 item 6)
          -> release the Agent (always, via finally)
          -> commit the slot output, then the release receipt
  -> classify every slot output into the deterministic conflict set (P19-C6)
  -> build the Evidence-aggregation input (P19-C7), refusing unless every release is RELEASED
     (P19-C8)

route_orchestration_to_evidence:
  live Phase 12 coordinator contract
  -> resolve-and-verify the plan, its conflict set, its aggregation input (must already exist)
  -> re-verify every release receipt is RELEASED (defense in depth)
  -> for each admitted slot output, in order: resolve-and-verify its Envelope, rebuild an
     equivalent ModelExecutionReceipt, hand it to the existing Model Runtime Evidence hand-off,
     chaining predecessor_evidence_refs -- a genuinely linked Evidence chain, never N unrelated
     records
  -> build + commit the terminal orchestration receipt (evidence_refs appended here, never on
     the aggregation input -- see §3 item 11)
```

## 6. P19-C1 through P19-C10

### P19-C1 -- Difference-derived Agent count and capabilities

*Requirement:* one canonical Difference and its required capabilities determine the execution
slots; caller preference, model recommendation, provider availability, majority strategy, or a
preconfigured organization cannot decide the count. Bounded and total; closed maximum; typed
refusal for unknown/unsupported/ambiguous/stale/over-limit requirements.

*Code:* `selection.select_agent_slots(difference)` takes exactly one parameter -- there is no
call shape through which a caller preference could reach it
(`test_select_agent_slots_has_no_caller_selected_count_parameter`). `RISK_CLASS_TO_SLOT_COUNT` is
a fixed, immutable `MappingProxyType`, total over the Difference schema's own closed four-member
`risk_class` enum, giving 1/1/2/3 slots -- a genuine 1, 2 and N (`MAX_AGENT_SLOTS=3`). An
out-of-enum, missing, or non-string `risk_class` raises `MultiAgentUnsupportedRequirementError`;
a (currently unreachable, but checked) over-limit mapped count raises
`MultiAgentOverLimitError`; an ambiguous system-wide capability vocabulary (more than the one
member that exists today) raises the same. The resolved Difference itself is schema/identity/
project-binding re-verified by `route._resolve_difference` before `select_agent_slots` is ever
called -- staleness/substitution refuse before selection, not inside it.

*Proof layer:* V2, `tests/unit/multi_agent/test_multi_agent_selection.py` (11 tests).

### P19-C2 -- Deterministic dynamic execution plan

*Requirement:* one immutable, content-addressed plan binding Project/Binding/Boot identity;
State revision/fingerprint; Difference identity and required-capability fingerprint; reproduced
Authority decision reference; exact slots/capability/count; runtime/model/adapter identity;
ordering; deadlines/cancellation/resource bounds; conflict/aggregation and release policy;
validity window. Every field that can widen execution or change provenance participates in
identity.

*Code:* `engine.derive_multi_agent_dynamic_execution_plan` builds exactly this record;
`identity.PLAN_SEMANTIC_FIELDS` is the complete field list (§4.1) both digests hash. Every field
the requirement names has a corresponding required, schema-validated field in
`multi_agent_dynamic_execution_plan.schema.json` (`additionalProperties: false`).
`capability_selection_fingerprint` content-addresses the derivation's own *output* (the exact
`(capability, slot_index)` tuple list), not only its input, so a tampered slot list is
independently detectable even without recomputing the whole plan.

*Proof layer:* V1, `tests/unit/multi_agent/test_multi_agent_identity.py`
(`test_plan_identity_recomputes_and_is_schema_valid`,
`test_every_plan_field_is_identity_sensitive` -- parametrized over every field).

### P19-C3 -- Existing Temporary Agent lifecycle continuity

*Requirement:* construction, execution and release reuse the accepted Phase 12 lifecycle/
execution-contract owner. No second Agent lifecycle owner, persistent Agent memory, permanent
registry, standing organization, hierarchy or hidden delegation graph. Every Agent remains
temporary, stateless, non-authoritative and replaceable.

*Code:* every Agent this package ever holds is a real `agent_runtime.TemporaryAgent`, obtained
only from `agent_runtime.start_temporary_agent`, at exactly two disclosed literal call sites
(§3 item 5). No class in this package implements both `boot_context` and `release`
(`test_no_module_defines_a_second_temporary_agent_shaped_class`), `boot_project` is never
imported here at all (`test_no_module_boots_a_project_or_constructs_a_temporary_agent_directly`),
and every constructed Agent is released before this package's own terminal receipt can even be
built (`test_every_start_temporary_agent_call_site_is_guarded_by_a_releasing_finally`, and
P19-C8's own runtime proof below).

*Proof layer:* V3, static conformance
(`tests/contract/multi_agent/test_multi_agent_static_conformance.py`).

### P19-C4 -- Authority and Change continuity

*Requirement:* the plan cannot mint, infer, delegate or aggregate Authority. Any side effect
must already be represented by a canonical authorized Change and pass the accepted Phase 18
Boundary before the first effect. No Agent, coordinator, model, consensus, output count, score
or adapter claim may authorize a Change or widen its scope. Read-only work stays distinguishable
from authorized mutation.

*Code:* Authority is reproduced, never minted -- `open_dynamic_execution_plan` calls the
existing `model_runtime.open_model_work_unit` exactly once
(`test_model_runtime_execution_routes_are_reused_not_reimplemented`), which itself calls the
existing `evaluate_model_execution_authorization`; this package calls neither Authority
evaluator itself, anywhere (`test_no_module_evaluates_authority_or_derives_a_change_itself`).
Since the one capability that exists today
(`multi_agent.types.MULTI_AGENT_CAPABILITIES`'s own single member) is read-only, no slot ever
reaches `change_executor` -- this package never imports it at all
(`test_no_module_imports_a_change_executor_composition_or_execution_surface`), and no Change
record is ever created as a side effect of this package's own work
(`test_no_change_record_is_ever_created_by_this_package`). A decisive negative control proves the
zero-effect boundary structurally, not merely by absence: an adapter reporting a forged
`change_ref`/`authority_ref`/`boundary_widened`/`difference_closed` claim inside its own
candidate fields is refused outright by the existing, unchanged Model Runtime route the instant
it reports a field the Boundary never permitted (P16-C3, reused unchanged) -- the forged content
never reaches any canonical record, is never read by anyone, and the slot is honestly classified
`UNAVAILABLE`
(`test_a_forged_change_authority_or_boundary_claim_never_survives_boundary_projection`). A second
control proves an adapter cannot authorize itself: an adapter claiming the route-only
`CANDIDATE_ACCEPTED` classification for itself is refused as an adapter defect, never promoted to
success (`test_an_adapter_claiming_the_accepting_classification_itself_is_refused_not_promoted`).
A third proves no per-slot self-authorization: N slots of one plan share exactly one committed
`model_execution_decision` and one `model_work_unit`, never N
(`test_authority_is_evaluated_exactly_once_per_plan_never_per_slot`). The defensive-but-currently-
unreachable path this requirement's own "where execution requires Authority" clause anticipates
for a future mutating capability is disclosed in §3 item 2 and §13's own non-claims.

*Proof layer:* V4, `tests/contract/multi_agent/test_multi_agent_authority_boundary.py`.

### P19-C5 -- Agent-specific provenance and independent outputs

*Requirement:* each slot emits a typed output binding Agent execution identity, assigned
capability, exact inputs, plan identity, runtime/model/adapter identity, attempt identity,
bounded timing, typed outcome and result fingerprint. Outputs are candidates, never canonical
Observation/Evidence/State/Authority/Change/closure/completion proof. Missing/refused/failed/
timed-out/cancelled/partial/unknown outcomes remain first-class.

*Code:* `engine.derive_multi_agent_slot_output` builds exactly this record, reusing Model
Runtime's own closed `MODEL_EXECUTION_OUTCOMES` vocabulary directly
(`multi_agent.types.MULTI_AGENT_SLOT_OUTCOMES is` that exact frozenset, proved by
`test_the_capability_vocabulary_is_reused_never_restated`) -- never a second outcome
vocabulary. A slot output is never treated as canonical anything: it is only ever read by
`route.py`'s own conflict classification and by `evidence_handoff.py`'s own hand-off, both of
which forward it as a *candidate* to the existing Evidence owner. §3 item 6 documents exactly
which failures are caught and honestly reclassified versus propagated.

*Proof layer:* V1 (per-output identity), V3 (real vertical proof), V5 (a failed slot stays
explicit alongside an admitted one) -- see §12.

### P19-C6 -- Conflict representation without silent collapse

*Requirement:* contradictory outputs, incompatible claims, divergent fingerprints, missing
outputs and verification failures produce an explicit deterministic conflict set. No majority
vote, confidence average, last-writer-wins, model rank or coordinator preference may silently
collapse conflict into truth. Membership, provenance, claim identity and disposition status are
preserved.

*Code:* `route._classify_conflicts` implements the one closed policy `types.CONFLICT_POLICY`
names (`EXACT_FINGERPRINT_EQUALITY_OR_EXPLICIT_DISAGREEMENT`): per capability, every
`CANDIDATE_ACCEPTED` attempt's `result_fingerprint` is compared byte-for-byte; one distinct value
across the whole group is `AGREEING` (admitted); two or more distinct values is `CONTRADICTING`,
preserving every fingerprint group and every member ref, and admits neither; every non-accepted
attempt is its own explicit `ABSENT` member, naming its own real outcome, never dropped from the
set. `test_two_contradicting_agents_preserve_full_membership_and_admit_neither` additionally
proves call-order independence (reversing which adapter answers first produces the identical
`CONTRADICTING` classification, never a "first/last" bias).

*Proof layer:* V5, `tests/contract/multi_agent/test_multi_agent_conflict_matrix.py` (5 tests).

### P19-C7 -- Evidence aggregation input, not Evidence verdict

*Requirement:* one deterministic aggregation input binding the complete admitted output set,
conflict set, absent/failed slots, and plan/release identities, submitted to the existing
Evidence/Independent Verification owners. Aggregation cannot mark Evidence sufficient, mutate
State, close the Difference, or declare the Objective complete.

*Code:* `engine.derive_multi_agent_evidence_aggregation_input` builds exactly this record; it
carries no `evidence_level`, `status`, or any field shaped like a verdict
(`test_this_package_never_marks_evidence_sufficient_or_declares_a_verdict`). Every admitted
output is handed, individually, to the existing
`model_runtime.evidence_handoff.route_model_execution_to_evidence` -- reused exactly once, from
exactly one module (`test_route_model_execution_to_evidence_is_reused_exactly_once`) -- chaining
`predecessor_evidence_refs` so N admitted outputs for one plan produce a genuinely linked
Evidence chain. A `CONTRADICTING` capability group is recorded in the conflict set but produces
no admitted output and is named explicitly in `unresolved_capabilities` -- visible, never
silently resolved by this hand-off either.

*Proof layer:* V5 (aggregation half), V3 (the real chain, `evidence_refs` length equal to slot
count in the vertical proof).

### P19-C8 -- Release receipts and no leaked temporary Agents

*Requirement:* every constructed Agent yields an identity-bound release receipt on every
terminal path, including coordinator crash and recovery. Release is idempotent. Unknown/failed
release remains visible and blocks clean terminal completion. All Agents released before a
successful orchestration receipt is possible.

*Code:* every `start_temporary_agent` call site sits inside a `try/finally` that calls
`.release()` unconditionally (§3 item 5/6, structurally proven). `engine.derive_multi_agent_
evidence_aggregation_input` refuses (`MultiAgentReleaseIncompleteError`) unless every supplied
release receipt declares `release_status == "RELEASED"` -- the one gate through which a clean
terminal aggregation input, and therefore orchestration receipt, can ever exist. This is
re-checked independently, a second time, by `evidence_handoff.route_orchestration_to_evidence`
itself (never trusting the aggregation input's own history) --
`test_release_incompleteness_blocks_aggregation_and_therefore_clean_completion` proves the
hand-off refuses even when a release receipt is tampered to `RELEASE_FAILED` directly at the
Store after a real, successful run. `ORCHESTRATION_OUTCOMES` includes the disclosed,
currently-unreachable-via-the-route `ABORTED_RELEASE_INCOMPLETE` member for schema honesty (§13).

*Proof layer:* V6, `tests/integration/multi_agent/test_multi_agent_replay_and_recovery.py`
(release-visibility and crash/recovery tests) plus the engine-level
`test_aggregation_input_refuses_when_any_release_receipt_is_not_released`.

### P19-C9 -- Replay, substitution, concurrency and recovery safety

*Requirement:* exact replay returns the recorded plan/outcomes without re-running completed work.
Conflicting reuse of a plan/slot/attempt identity refuses. Cross-project/State/Difference/
capability/Agent/output substitution fails closed. Concurrent duplicate orchestration and crash
recovery do not duplicate side effects, lose conflict records, omit release obligations, or
upgrade unknown work to success.

*Code:* §3 item 8's own narrow-key identity scheme is what makes replay a plain Store lookup
(`compute_slot_output_id`, resolved *before* any Agent is constructed) rather than bespoke
bookkeeping. `test_exact_replay_reuses_every_slot_output_with_zero_new_adapter_calls` proves a
second `execute_dynamic_execution_plan` call reuses every slot output with an adapter factory
that raises if ever called. `test_conflicting_reuse_of_an_attempt_identity_refuses` plants a
different-content record at an already-occupied natural key directly at the Store and proves
`route._commit` converts the resulting `RecordConflictError` into
`MultiAgentReplayConflictError`. `test_partial_execution_coordinator_crash_and_recovery_leak_no_
agent` simulates a genuinely unexpected (non-`ModelRuntimeError`) exception on a HIGH-risk
plan's second slot, proving: the first slot's own output and release receipt are durably
committed before the crash; every Agent constructed so far (proved via a release-counting proxy)
is released; the second slot's own attempt is *not* committed (the crash happened before it
could be); and a fresh call for the identical plan then reuses the first slot untouched and
completes the second fresh, with all release receipts `RELEASED` and the aggregation input
buildable. Cross-project/State/plan substitution is proven in
`tests/integration/multi_agent/test_multi_agent_substitution_and_continuity.py` (§12).

*Proof layer:* V6, and V7's own substitution half.

### P19-C10 -- Canonical-owner and re-observation continuity

*Requirement:* this package remains an adapter/orchestration surface. Existing owners remain
singular for State, Observation, Difference, Authority, Change, Evidence, Independent
Verification and Reflow. When an authorized Change is performed, after-state facts still require
independent re-observation through the accepted Phase 18 route -- coordinator summaries, Agent
outputs, aggregation inputs and release receipts cannot substitute for it.

*Code:* this package never imports `reflow`, `independent_verification`, `projection`, `runtime`,
`change`, or `change_executor`, in whole or in part
(`test_no_module_imports_a_forbidden_existing_owner`), and never calls `reflow`/`reopen` by name
anywhere (`test_no_module_calls_reflow_or_reopen`). Since this delivery's one capability is
read-only and never reaches `change_executor` at all (P19-C4), there is no authorized Change for
this delivery to ever need to re-observe after -- so P19-C10 is satisfied here by never inventing
a second re-observation channel at all, not by wiring into the existing one. The repository-wide
static topology inventory (`manosube_agent_civilization.topology`) still reports exactly one
canonical State owner and one canonical Authority/transition owner after this delivery
(`test_kernel_topology_still_reports_single_canonical_owners`), and Phase 12/16/18's own accepted
public surfaces are pinned unchanged
(`test_phase_12_public_surface_is_unchanged_by_this_delivery`,
`test_phase_16_public_surface_is_unchanged_by_this_delivery`,
`test_phase_18_public_surface_is_unchanged_by_this_delivery`).

*Proof layer:* V7, static conformance.

## 7. Closed vocabularies

```text
MULTI_AGENT_CAPABILITIES        reused verbatim from model_runtime.types.
                                 MODEL_EXECUTION_CAPABILITIES -- {"PROPOSE_EVIDENCE_CANDIDATE"}
MULTI_AGENT_SLOT_OUTCOMES       reused verbatim from model_runtime.types.MODEL_EXECUTION_OUTCOMES
                                 -- CANDIDATE_ACCEPTED, UNAVAILABLE, REFUSED, MALFORMED, TIMEOUT,
                                 CANCELLED, INCOMPLETE_EVIDENCE
RISK_CLASS_TO_SLOT_COUNT        LOW->1, MODERATE->1, HIGH->2, CRITICAL->3 (selection.py)
EXECUTION_ORDERS                {"CONCURRENT"} -- see §3 item 4
RELEASE_POLICIES                {"RELEASE_ON_TERMINAL_OUTCOME"}
CONFLICT_POLICIES               {"EXACT_FINGERPRINT_EQUALITY_OR_EXPLICIT_DISAGREEMENT"}
CANCELLATION_POLICIES           {"COOPERATIVE_PER_SLOT_TIMEOUT"} -- declared, not runtime-enforced
RELEASE_STATUSES                RELEASED, RELEASE_FAILED
CONFLICT_MEMBER_KINDS           AGREEING, CONTRADICTING, ABSENT
ORCHESTRATION_OUTCOMES          COMPLETED_ALL_RELEASED, COMPLETED_WITH_UNRESOLVED_CAPABILITY,
                                 ABORTED_RELEASE_INCOMPLETE (the last, disclosed-unreachable --
                                 see §13)
```

## 8. Required proof layers

```text
V1  Deterministic schema and identity proof            tests/unit/multi_agent/
    test_multi_agent_identity.py (21 tests): every one of the six kinds recomputes its own
    identity and fingerprint from its own real content, is schema-valid, and every field is
    identity-sensitive (fingerprint if not the narrow id -- §3 item 8).

V2  Difference-derived selection matrix                 tests/unit/multi_agent/
    test_multi_agent_selection.py (14 tests): a genuine 1/2/N across the four risk classes, the
    closed maximum, unsupported/ambiguous refusal, and the structural absence of any
    caller-count parameter.

V3  Non-skipped vertical proofs, 1/2/N-Agent execution   tests/integration/multi_agent/
    test_multi_agent_vertical_proof.py (3 tests, parametrized LOW/HIGH/CRITICAL): real Difference
    records, the real accepted Phase 12 lifecycle, the real Phase 16 execution contract, plan
    open -> execute -> Evidence hand-off end to end, complete provenance, every Agent released.

V4  Authority/Change boundary proof                      tests/contract/multi_agent/
    test_multi_agent_authority_boundary.py (4 tests): read-only stays read-only (zero Change
    records), Authority evaluated exactly once per plan, and two decisive zero-effect negative
    controls (a forged Change/Authority/Boundary claim; a self-authorizing adapter) -- neither
    ever mutates a canonical record or is promoted to success.

V5  Conflict and aggregation matrix                       tests/contract/multi_agent/
    test_multi_agent_conflict_matrix.py (5 tests): agreement, contradiction (with call-order
    independence), a failed slot alongside an admitted one, full membership never dropped, and a
    decisive proof this package never declares an Evidence verdict.

V6  Replay/concurrency/crash/release matrix               tests/integration/multi_agent/
    test_multi_agent_replay_and_recovery.py (4 tests): exact replay (zero adapter calls),
    conflicting-reuse refusal at the Store's own content-addressed commit path, a genuinely
    unexpected mid-orchestration exception with proved no-leaked-Agent and clean recovery, and
    release-incompleteness blocking the Evidence hand-off even under direct Store tampering.

V7  Tamper/substitution and Kernel continuity             tests/integration/multi_agent/
    test_multi_agent_substitution_and_continuity.py (8 tests): cross-project Difference
    substitution, a stale coordinator contract, evidence hand-off before execution (cross-output
    substitution), a cross-project plan_ref, and Phase 12/16/18/Kernel-topology continuity pins.

Static conformance                                        tests/contract/multi_agent/
    test_multi_agent_static_conformance.py (20 tests): no permanent Agent hierarchy/registry, no
    second canonical owner, no majority-as-truth route (no majority/average/rank vocabulary
    exists at all -- §6 P19-C6), no hidden Authority creation, exactly two disclosed
    start_temporary_agent call sites each release-guarded, one sanctioned committer reused (never
    duplicated), the reused Model Runtime execution contract and Evidence hand-off each called
    exactly once, and Phase 20 is not implemented (no long-running-proof vocabulary or module
    exists anywhere in this package).
```

## 9. Gate 19

```text
AGENT_COUNT_DIFFERENCE_DERIVED=true            -- selection.select_agent_slots takes no other
                                                   parameter (P19-C1, V2)
MULTI_AGENT_NOT_PERMANENT_ORGANIZATION=true    -- every Agent temporary/stateless/released; no
                                                   registry, hierarchy, or persisted Agent memory
                                                   (P19-C3, static conformance)
EACH_AGENT_OUTPUT_HAS_PROVENANCE=true          -- every multi_agent_slot_output binds plan,
                                                   slot, capability, attempt, envelope ref,
                                                   outcome, timing (P19-C5, V1/V3)
CONSENSUS_NOT_TRUTH=true                       -- exact-fingerprint-equality-or-explicit-
                                                   disagreement is the only policy; no majority/
                                                   average/rank vocabulary exists (P19-C6, V5)
CONFLICT_NOT_SILENTLY_COLLAPSED=true           -- CONTRADICTING preserves every fingerprint
                                                   group and member; ABSENT is first-class (V5)
CANONICAL_STATE_OWNER_COUNT=1                  -- topology.k002_single_canonical_state_owner()
                                                   still true after this delivery (P19-C10, V7)
ALL_TEMPORARY_AGENTS_RELEASED=true             -- P19-C8's own aggregation-input gate, proved
                                                   under a genuine mid-orchestration crash (V6)
```

## 10. Explicit non-claims

- **No real multi-capability catalog.** `MULTI_AGENT_CAPABILITIES` has exactly one member today;
  every slot of every plan this delivery ever opens requires the identical capability. This
  delivery proves the *mechanism* for genuine N-capability fan-out, never a hypothetical catalog
  it would have had to invent to exercise (see `selection.py`'s own module docstring).
- **No real OS-level concurrency.** "CONCURRENT" (§3 item 4) is an honest, structurally-checked
  absence-of-dependency claim, never a claim that slots run on separate threads, processes, or
  async tasks.
- **`CANCELLATION_POLICIES`' one declared value is not runtime-enforced.** No module in this
  package reads a clock, schedules a timeout, or cancels a running Agent -- an adapter that hangs
  simply has not returned yet. `TIMEOUT`/`CANCELLED` remain honestly representable outcomes (an
  adapter may report them), but nothing in this package *produces* one by watching a deadline.
- **`ORCHESTRATION_OUTCOMES.ABORTED_RELEASE_INCOMPLETE` is schema-representable but unreachable
  through this package's own public route in this delivery.** `agent_runtime.TemporaryAgent.
  release()` is documented "local, idempotent, and zero-write" and cannot currently fail, so
  `execute_dynamic_execution_plan` never actually reaches a state where an aggregation input --
  and therefore an orchestration receipt -- could exist with an unreleased Agent. The vocabulary
  member, and the engine-level refusal a caller could reach by handing a tampered,
  already-`RELEASE_FAILED` receipt directly to `engine.derive_multi_agent_evidence_aggregation_
  input`, exist for schema honesty about what a real release failure would look like, proved
  directly by `test_aggregation_input_refuses_when_any_release_receipt_is_not_released` and by
  `test_release_incompleteness_blocks_aggregation_and_therefore_clean_completion`'s own
  direct-Store-tamper control -- never claimed as a reachable route-level outcome today.
- **This delivery never implements a real long-running Agent proof (Phase 20) or a comparative
  benchmark (Phase 21).** Neither vocabulary, module, nor schema field exists anywhere in this
  package.
- **This delivery never automatically closes a Difference, an Issue, or merges anything.** No
  module in this package imports `reflow`, `change_executor`, or any GitHub/git surface at all.
- **A model output is never treated as executable authority-bearing instruction here.** Every
  candidate this package's own conflict classification and Evidence hand-off ever read is the
  identical, already-Boundary-projected, already-independently-reclassified fact the existing
  Model Runtime route itself produces -- never an adapter's raw report read directly by this
  package (§6 P19-C4's own decisive controls).
- **`route_orchestration_to_evidence`'s own `evidence_request_template` is reused unchanged
  across every admitted output of one plan.** This delivery does not support per-slot distinct
  Evidence request shapes within a single plan; every slot of one plan already concerns the
  identical canonical Difference, so one shared template (varying only `predecessor_evidence_
  refs`, threaded by this hand-off itself) is correct for this delivery's own one-Difference-
  per-plan design, not a limitation this delivery works around.

## 11. Structural Review Round 1 corrections (P19-R1-F1..F6)

Adopted as `ADOPT_P19_R1_STRUCTURAL_CORRECTIONS` against reviewed head
`18a4ba8093477fb2a954d1327424f7e0f0cfe8a8` (PR #78). Six findings, all addressed on the
existing branch/PR, no new module or owner introduced.

- **P19-R1-F1 (common immutable execution snapshot).** `route.py::_execute_one_slot` now binds
  `plan["boot_state_revision"]`/`plan["boot_semantic_fingerprint"]` -- the plan's own immutable,
  genesis-once snapshot -- into every slot's own new `multi_agent_slot_output.execution_snapshot`
  field (`engine.py::derive_multi_agent_slot_output`, `identity.py::SLOT_OUTPUT_SEMANTIC_FIELDS`,
  schema-required). This is deliberately *not* Model Runtime's own live `executed_state_revision`
  (which legitimately differs slot to slot, since each slot's own Envelope commit advances it
  before the next slot's own adapter call -- an accepted, unchanged Model Runtime behaviour this
  delivery neither can nor should alter): it is this package's own bound, order-invariant fact
  about which execution a slot's attempt belongs to, read from the identical immutable plan
  record for every slot of one plan. Proved decisively by
  `test_p19_r1_f1_every_slot_shares_one_common_immutable_execution_snapshot`, which also
  independently confirms the underlying Model Runtime drift is real (so the fix is not vacuous).
- **P19-R1-F2 (atomic slot-output/release-receipt commit).** `_execute_one_slot` now derives
  both the slot output and its release receipt before committing either, then commits both in
  one atomic `_commit` call (`TX-MULTI-AGENT-SLOT-COMPLETE`) -- the identical multi-record
  atomic-commit discipline Model Runtime's own `open_model_work_unit` already uses for its
  Decision+Work-Unit pair. The previous two-separate-commit crash gap (a crash between them left
  a committed slot output with no release receipt, and every later replay raised
  `MultiAgentRequirementError` forever) is closed by construction. Proved by
  `test_p19_r1_f2_a_crash_between_slot_output_derivation_and_commit_leaves_neither_record`.
- **P19-R1-F3 (orchestration receipt semantic-fingerprint verification).**
  `evidence_handoff.py::resolve_and_verify_committed_orchestration_receipt` now recomputes and
  verifies the full semantic fingerprint, matching every sibling resolver in this package
  (previously it verified only the narrow identity).
- **P19-R1-F4 (Evidence records persisted, not only referenced).**
  `evidence_handoff.py::route_orchestration_to_evidence` now commits every derived Evidence
  record (kind `observation_evidence`, `derive_evidence`'s own pure-function output) in the
  identical atomic transaction as the terminal orchestration receipt that names it -- the
  identical convention `reflow.route` already uses for its own `derive_evidence` calls. Before
  this fix, only the orchestration receipt was ever committed, so every one of its own
  `evidence_refs` was dangling.
- **P19-R1-F5 (fail-closed plan expiry/deadline enforcement).**
  `execute_dynamic_execution_plan` now refuses (`MultiAgentPlanExpiredError`) before any slot's
  own Agent is constructed, any adapter is reached, or any new Store mutation is made, when
  `executed_at` is at or past the plan's own `expires_at` or `execution_bounds.deadline_at` --
  the identical fail-closed discipline `reflow.commit`'s own G18 `evaluation_expires_at` check
  already applies to an unrelated validity window. Proved with boundary-time controls (at the
  exact deadline instant, and one second before it) by
  `test_p19_r1_f5_execution_past_the_plans_own_deadline_refuses_with_zero_side_effects`,
  `test_p19_r1_f5_execution_exactly_at_the_deadline_instant_also_refuses`, and
  `test_p19_r1_f5_execution_one_second_before_the_deadline_still_succeeds`.
- **P19-R1-F6 (bounded current-state restatement).** `docs/project_sources/
  03_CURRENT_DEVELOPMENT_STATE.md` §41 appends a bounded, last-wins restatement of
  `CURRENT_PHASE`/`CURRENT_PHASE_STATE`/`CURRENT_PR`/`MAIN_ACCEPTED_BASE_SHA` reflecting Phase 19
  Round 1 as the live work unit, without rewriting §0's header block or any historical section.
  per-plan design, not a limitation this delivery works around.

## 12. Structural Review Round 3 corrections (P19-R3-F1..F5)

Adopted as `ADOPT_P19_R3_STRUCTURAL_CORRECTIONS` against reviewed head/authorized target
`7485e49229b77e6507626f16fe76a824ef4da3fa` (PR #78). Five findings, all addressed on the
existing branch/PR, no new module or owner introduced.

- **P19-R3-F1 (real per-request common execution snapshot).** Round 1's own P19-R1-F1 fix bound
  only this package's own `multi_agent_slot_output.execution_snapshot` bookkeeping field to the
  plan's genesis snapshot -- the *real* adapter request each slot made still derived its own
  `state_revision`/`semantic_fingerprint` from a live reboot that genuinely advances slot to
  slot (each slot's own committed Model Execution Envelope is what advances it). This is the
  "result metadata used as snapshot substitute" gap the Round 3 review named. The fix is a new
  `pinned_execution_snapshot` optional parameter on Model Runtime's own
  `model_runtime.route.execute_model_work_unit` (additive, fully backward compatible -- every
  existing caller that supplies none keeps its unchanged live-reboot behaviour): when supplied,
  its own `state_revision`/`semantic_fingerprint` are what the adapter's own real request and
  the committed Envelope declare instead of the freshly-rebooted live values, while every
  freshness/staleness check still runs against the true live Boot underneath, unchanged. Every
  slot of one plan now passes the identical `plan["boot_state_revision"]`/
  `plan["boot_semantic_fingerprint"]` pair through it (`route.py::_execute_one_slot`), so the
  *actual* committed Envelope -- not just this package's own bookkeeping -- carries the
  identical, plan-pinned snapshot for every slot, in front-to-back and reversed slot-execution
  order alike. Proved by the rewritten
  `test_p19_r1_f1_every_slot_shares_one_common_immutable_execution_snapshot` (now asserting the
  real committed Envelope's own `executed_state_revision`/`executed_semantic_fingerprint`, and
  independently confirming the Store's own live state genuinely advanced between the real
  adapter calls it would otherwise have leaked into an unpinned request) and by the new
  `test_p19_r3_f1_state_sensitive_adapter_and_order_reversal_prove_no_snapshot_drift`, which
  records the exact `state_revision`/`semantic_fingerprint` a state-sensitive fake adapter's own
  request carried across a 3-slot plan driven in the *reverse* of this package's own fixed
  ascending execution order.
- **P19-R3-F2 (independent re-derivation of the admitted slot selection).**
  `execute_dynamic_execution_plan` now calls a new `_require_selection_matches_difference` right
  after resolving the plan and before any Agent is constructed, any adapter is reached, or any
  new Store mutation is made: it independently re-resolves the plan's own `difference_ref`,
  recomputes `select_agent_slots` and `capability_selection_fingerprint` against that resolved
  Difference, and raises the new `MultiAgentPlanSelectionMismatchError`
  (`multi_agent/errors.py`) on any mismatch -- closing the route through which a plan committed
  by some path other than `open_dynamic_execution_plan` could declare a self-consistent but
  forged selection (e.g. a HIGH-risk Difference requiring 2 slots, with a committed plan
  self-consistently declaring only 1). Proved by
  `test_p19_r3_f2_a_forged_self_consistent_one_slot_plan_against_a_high_risk_difference_is_refused_before_any_effect`,
  which commits such a plan directly (bypassing `open_dynamic_execution_plan`) and proves zero
  Agent construction (the adapter factory itself is never called), zero new Store records of
  any kind this package writes, and an unchanged `state_revision`.
- **P19-R3-F3 (crash-safe envelope reuse, no duplicate adapter call on recovery).** A new record
  kind, `multi_agent_slot_attempt_envelope_claim`
  (`01_SCHEMA/multi_agent/multi_agent_slot_attempt_envelope_claim.schema.json`,
  `engine.py::derive_multi_agent_slot_attempt_envelope_claim`,
  `identity.py::multi_agent_slot_attempt_envelope_claim_id`), is committed durably right after
  the real adapter call succeeds and its own Model Execution Envelope is committed -- strictly
  *before* this slot's own terminal `multi_agent_slot_output`/`multi_agent_agent_release_receipt`
  pair is derived or committed. `_execute_one_slot` now resolves this claim first
  (`resolve_and_verify_committed_slot_attempt_envelope_claim`): if it already exists, the already
  -committed Envelope it names is reused verbatim and the adapter is never called a second time
  for that slot attempt. A coordinator/infrastructure crash at any point -- including exactly
  where Round 1's own P19-R1-F2 fix already made the slot-output/release-receipt pair atomic --
  now always leaves a durable, typed outcome to recover from: either the claim (real adapter work
  already paid for, safely reusable) or nothing at all (a genuine retry, not a duplicate charge).
  Proved by the rewritten
  `test_p19_r1_f2_a_crash_between_slot_output_derivation_and_commit_leaves_neither_record`, which
  now additionally proves the claim survives the injected crash and that recovery's own adapter
  `execute_call_count` is `0` -- the decisive `RECOVERY_DUPLICATE_ADAPTER_CALL_COUNT=0` proof.
- **P19-R3-F4 (real, runtime-enforced per-slot timeout).** The previously declared-but-unread
  `CANCELLATION_POLICY = "COOPERATIVE_PER_SLOT_TIMEOUT"` (Round 1's own honest disclosure: "no
  module in this package reads a clock, schedules a timeout, or cancels a running Agent") is now
  backed by a real bound. `open_dynamic_execution_plan` takes a new
  `per_slot_timeout_seconds` parameter (default `types.DEFAULT_PER_SLOT_TIMEOUT_SECONDS = 30`, a
  whole number of seconds -- Canonical State's own v0.1 encoding prohibits floating-point values
  entirely, so this bound, like every other `timeout_seconds` field in this repository, is an
  `int`, never a fraction), validated and recorded in the plan's own
  `execution_bounds.per_slot_timeout_seconds` (schema-required). `_execute_one_slot` submits its
  real adapter call to a disposable, one-worker `concurrent.futures.ThreadPoolExecutor` and reads
  the result via `future.result(timeout=...)` bound to that exact per-plan value: this call never
  blocks past the bound and never reports success for an unbounded attempt -- the disclosed,
  accepted Python limitation is that a blocked thread cannot be forcibly killed, so an abandoned
  background call may still be running when this call already returned. A timeout produces a
  typed `TIMEOUT` outcome (no Envelope reference, no result fingerprint -- there is no real
  Envelope this attempt could ever truthfully name) and the constructed slot Agent is still
  released and accounted for as `RELEASED`, exactly as every other terminal path already is. No
  second Model Runtime/Agent Runtime/State Store/Evidence owner is introduced -- the bound wraps
  the identical, unmodified `execute_model_work_unit` call this package already made. Proved by
  the new
  `test_p19_r3_f4_a_genuinely_hanging_adapter_is_bounded_by_the_plans_own_real_timeout`, which
  drives a real `time.sleep()` adapter far longer than a short, test-supplied
  `per_slot_timeout_seconds` and proves the call returns in bounded time with a typed `TIMEOUT`
  outcome and a resolving release receipt.
- **P19-R3-F5 (bounded current-state restatement).** `docs/project_sources/
  03_CURRENT_DEVELOPMENT_STATE.md` §42 appends a bounded, last-wins restatement of
  `CURRENT_PHASE`/`CURRENT_PHASE_STATE`/`CURRENT_PR`/`MAIN_ACCEPTED_BASE_SHA` reflecting Phase 19
  Round 3 as the live work unit, and records Issue #75/PR #79 (a separate, unrelated work item)
  as independently re-verified `CLOSED`/unmerged/cancelled and no longer an integration barrier
  for Phase 19 -- without rewriting §0's header block or any section through §41.
