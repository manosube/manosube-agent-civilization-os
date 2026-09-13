"""Phase 19 (Issue #77) V3: non-skipped vertical proofs for 1-, 2- and N-Agent execution.

Real Difference records (``risk_class`` LOW/HIGH/CRITICAL, giving 1/2/3 slots under this
delivery's own closed mapping), the real accepted Phase 12 Temporary Agent lifecycle, the real
Phase 16 Model Runtime execution contract, and this package's own real routes end to end --
plan open, execution, and the Evidence hand-off -- with complete provenance and every
constructed Agent released.
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.fixtures.multi_agent_world import (
    SeededMultiAgentAdapter,
    StateRecordingMultiAgentAdapter,
    authorized_world,
    evidence_request_for,
    open_plan_kwargs,
)

from manosube_agent_civilization.agent_runtime import start_temporary_agent
from manosube_agent_civilization.multi_agent import (
    execute_dynamic_execution_plan,
    open_dynamic_execution_plan,
    route_orchestration_to_evidence,
)
import manosube_agent_civilization.multi_agent.route as route_module


def _coordinator(world: dict[str, Any]) -> Any:
    return start_temporary_agent(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
    )


@pytest.mark.parametrize(
    ("risk_class", "expected_slot_count"), [("LOW", 1), ("HIGH", 2), ("CRITICAL", 3)]
)
def test_vertical_proof_1_2_and_n_agent_execution(
    tmp_path: Any, risk_class: str, expected_slot_count: int
) -> None:
    world = authorized_world(tmp_path, risk_class=risk_class)
    store = world["store"]

    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()
    plan = opened["plan"]
    assert len(plan["slots"]) == expected_slot_count

    coordinator = _coordinator(world)
    executed = execute_dynamic_execution_plan(
        store,
        coordinator,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        plan_ref=opened["plan_ref"],
        model_adapter_factory=SeededMultiAgentAdapter,
        executed_at="2026-09-11T01:30:00Z",
    )
    coordinator.release()

    slot_outputs = executed["slot_outputs"]
    assert len(slot_outputs) == expected_slot_count
    assert {so["slot_index"] for so in slot_outputs} == set(range(expected_slot_count))
    for slot_output in slot_outputs:
        assert slot_output["outcome"] == "CANDIDATE_ACCEPTED"
        assert slot_output["result_fingerprint"] is not None
        assert slot_output["model_execution_envelope_ref"] is not None

    release_receipts = executed["release_receipts"]
    assert len(release_receipts) == expected_slot_count
    assert all(receipt["release_status"] == "RELEASED" for receipt in release_receipts)

    conflict_set = executed["conflict_set"]
    assert len(conflict_set["members"]) == 1
    assert conflict_set["members"][0]["member_kind"] == "AGREEING"

    aggregation_input = executed["aggregation_input"]
    assert aggregation_input["unresolved_capabilities"] == []
    assert len(aggregation_input["admitted_slot_output_refs"]["members"]) == expected_slot_count

    coordinator = _coordinator(world)
    handed_off = route_orchestration_to_evidence(
        store,
        coordinator,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        plan_ref=opened["plan_ref"],
        evidence_request_template=evidence_request_for(world["project_id"], provenance=None),
        completed_at="2026-09-11T01:40:00Z",
    )
    coordinator.release()

    orchestration_receipt = handed_off["orchestration_receipt"]
    assert orchestration_receipt["orchestration_outcome"] == "COMPLETED_ALL_RELEASED"
    assert len(orchestration_receipt["evidence_refs"]["members"]) == expected_slot_count
    assert len(handed_off["evidence_refs"]) == expected_slot_count


def test_p19_r1_f1_every_slot_shares_one_common_immutable_execution_snapshot(
    tmp_path: Any,
) -> None:
    """Structural Review Round 1, P19-R1-F1, superseded by Round 3, P19-R3-F1: Round 1's own fix
    bound only ``multi_agent_slot_output.execution_snapshot`` (this package's own metadata) to
    the plan's genesis snapshot, while the *real* adapter request each slot made still derived
    its own ``state_revision``/``semantic_fingerprint`` from a live reboot that genuinely
    advances slot to slot (each slot's own committed Model Execution Envelope is what advances
    it) -- exactly the "result metadata used as snapshot substitute" the Round 3 Structural
    Review named. The fix is a new ``pinned_execution_snapshot`` parameter on Model Runtime's own
    ``execute_model_work_unit`` (P19-R3-F1): every slot of this plan now passes the identical
    ``plan["boot_state_revision"]``/``plan["boot_semantic_fingerprint"]`` pair through it, so the
    *actual* committed Envelope -- not just this package's own bookkeeping -- carries the
    identical, plan-pinned snapshot for every slot.
    """

    from manosube_agent_civilization.model_runtime.route import (
        resolve_and_verify_committed_envelope,
    )

    world = authorized_world(tmp_path, risk_class="HIGH")
    store = world["store"]

    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()
    plan = opened["plan"]
    assert len(plan["slots"]) == 2

    live_before = store.load_current(world["project_id"])

    coordinator = _coordinator(world)
    executed = execute_dynamic_execution_plan(
        store,
        coordinator,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        plan_ref=opened["plan_ref"],
        model_adapter_factory=SeededMultiAgentAdapter,
        executed_at="2026-09-11T01:30:00Z",
    )
    coordinator.release()

    slot_outputs = {so["slot_index"]: so for so in executed["slot_outputs"]}
    expected_snapshot = {
        "state_revision": plan["boot_state_revision"],
        "semantic_fingerprint": plan["boot_semantic_fingerprint"],
    }
    assert slot_outputs[0]["execution_snapshot"] == expected_snapshot
    assert slot_outputs[1]["execution_snapshot"] == expected_snapshot
    assert slot_outputs[0]["execution_snapshot"] == slot_outputs[1]["execution_snapshot"]

    # Decisive proof this is not vacuous metadata: the *real committed Envelope* every slot's
    # own real adapter request produced also carries the identical, plan-pinned snapshot --
    # never the live, per-call-advancing value a fresh reboot would otherwise observe.
    envelope_0 = resolve_and_verify_committed_envelope(
        store, world["project_id"], slot_outputs[0]["model_execution_envelope_ref"]["id"]
    )
    envelope_1 = resolve_and_verify_committed_envelope(
        store, world["project_id"], slot_outputs[1]["model_execution_envelope_ref"]["id"]
    )
    assert envelope_0["executed_state_revision"] == plan["boot_state_revision"]
    assert envelope_1["executed_state_revision"] == plan["boot_state_revision"]
    assert envelope_0["executed_semantic_fingerprint"] == plan["boot_semantic_fingerprint"]
    assert envelope_1["executed_semantic_fingerprint"] == plan["boot_semantic_fingerprint"]

    # And the drift this pin closes is real: the Store's own live current State genuinely
    # advanced by two revisions (one Envelope commit + one multi_agent slot-complete commit per
    # slot) between the two slots' own real adapter calls -- had the request not been pinned, the
    # second slot's own real request would have observed a different, advanced live revision.
    live_after = store.load_current(world["project_id"])
    assert live_after["state_revision"] > live_before["state_revision"]
    assert live_after["state_revision"] > plan["boot_state_revision"]


def test_p19_r3_f1_state_sensitive_adapter_and_order_reversal_prove_no_snapshot_drift(
    tmp_path: Any,
) -> None:
    """Structural Review Round 3, P19-R3-F1's own required proof, in its strongest form: a
    state-sensitive fake adapter records the *exact* ``state_revision``/``semantic_fingerprint``
    every real adapter request it received itself carried (read from the adapter's own side of
    the request boundary, not inferred from this package's bookkeeping or the committed
    Envelope), across every slot of one CRITICAL-risk (3-slot) plan -- and this delivery drives
    the three slots' own real attempts in an order the *reverse* of ``slot_index`` (2, then 1,
    then 0), the opposite of :func:`~manosube_agent_civilization.multi_agent.route.
    execute_dynamic_execution_plan`'s own fixed ascending order, to rule out a fix that only
    happens to hold for one particular processing order.

    Each real attempt commits its own Model Execution Envelope and its own slot-complete
    transaction, so the Store's own live State genuinely advances between the three real
    adapter calls this test drives -- a request that read the live State instead of the pinned
    one would observe a different, order-dependent value every time. Every one of the three
    real requests, run in this reversed order, still observed the identical plan-pinned
    snapshot.
    """

    from manosube_agent_civilization.agent_runtime import TemporaryAgent

    world = authorized_world(tmp_path, risk_class="CRITICAL")
    store = world["store"]

    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()
    plan = opened["plan"]
    assert len(plan["slots"]) == 3

    observed: list[dict[str, Any]] = []
    live_between_calls: list[int] = []

    reversed_slots = sorted(plan["slots"], key=lambda item: -int(item["slot_index"]))
    assert [int(slot["slot_index"]) for slot in reversed_slots] == [2, 1, 0]

    for slot in reversed_slots:
        coordinator_agent: TemporaryAgent = _coordinator(world)
        _held, fresh_authority = route_module._live_contract(
            store,
            coordinator_agent,
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            require_exact_state=False,
        )
        route_module._execute_one_slot(
            store,
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            plan=plan,
            plan_ref=opened["plan_ref"],
            slot=slot,
            model_adapter_factory=lambda: StateRecordingMultiAgentAdapter(
                observed=observed, candidate_fields={"summary": "ok"}
            ),
            executed_at="2026-09-11T01:30:00Z",
            fresh_authority=fresh_authority,
        )
        coordinator_agent.release()
        live_between_calls.append(int(store.load_current(world["project_id"])["state_revision"]))

    assert len(observed) == 3
    first = observed[0]
    for later in observed[1:]:
        assert later["state_revision"] == first["state_revision"]
        assert later["semantic_fingerprint"] == first["semantic_fingerprint"]
    assert first["state_revision"] == plan["boot_state_revision"]
    assert first["semantic_fingerprint"] == plan["boot_semantic_fingerprint"]

    # The live State genuinely advanced between each of the three real adapter calls -- the
    # drift this pin closes is real, not vacuous, even under this reversed processing order.
    assert live_between_calls[0] < live_between_calls[1] < live_between_calls[2]
    assert live_between_calls[0] > plan["boot_state_revision"]
