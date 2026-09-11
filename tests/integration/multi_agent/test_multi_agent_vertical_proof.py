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
    """Structural Review Round 1, P19-R1-F1: reproduced the exact gap the review itself found --
    sequential slot execution means Model Runtime's own unchanged, live-observed
    ``executed_state_revision`` genuinely differs slot to slot (each slot's own Model Execution
    Envelope commit advances it before the next slot's own adapter call is even built). This
    delivery cannot and does not alter that accepted Model Runtime behaviour. What it does own is
    this: every slot's own committed ``multi_agent_slot_output.execution_snapshot`` is the plan's
    own ``boot_state_revision``/``boot_semantic_fingerprint`` -- read from the identical,
    immutable, already-committed plan record for every slot -- so it is bit-identical across
    every slot of one plan by construction, independent of whatever incidental revision drift
    Model Runtime's own live read happens to observe at each slot's own adapter-call time.
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

    # Decisive negative control: prove the drift this finding described is real, and that this
    # package's own bound snapshot is genuinely *not* the same thing as Model Runtime's own live
    # per-call observation -- otherwise this test would be vacuous.
    envelope_0 = resolve_and_verify_committed_envelope(
        store, world["project_id"], slot_outputs[0]["model_execution_envelope_ref"]["id"]
    )
    envelope_1 = resolve_and_verify_committed_envelope(
        store, world["project_id"], slot_outputs[1]["model_execution_envelope_ref"]["id"]
    )
    assert envelope_0["executed_state_revision"] != envelope_1["executed_state_revision"]
    assert envelope_1["executed_state_revision"] > plan["boot_state_revision"]
