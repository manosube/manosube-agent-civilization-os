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
