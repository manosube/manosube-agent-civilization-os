"""Phase 19 (Issue #77) V5: conflict and aggregation matrix.

Agreement does not become truth, disagreement is preserved with full membership, missing/
failed outputs remain explicit, and the existing Evidence/Independent Verification owner --
never this package -- decides sufficiency (this package never even declares a "verdict";
:func:`~manosube_agent_civilization.multi_agent.route_orchestration_to_evidence` only ever
forwards admitted candidates).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from typing import Any

from tests.fixtures.multi_agent_world import (
    SeededMultiAgentAdapter,
    authorized_world,
    evidence_request_for,
    open_plan_kwargs,
)

from manosube_agent_civilization.agent_runtime import start_temporary_agent
from manosube_agent_civilization.model_runtime.types import ModelAdapter
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


def _sequential_factory(adapters: Sequence[ModelAdapter]) -> Callable[[], ModelAdapter]:
    iterator: Iterator[ModelAdapter] = iter(adapters)

    def factory() -> ModelAdapter:
        return next(iterator)

    return factory


def _open_and_execute(world: dict[str, Any], adapters: Sequence[ModelAdapter]) -> dict[str, Any]:
    store = world["store"]
    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()

    coordinator = _coordinator(world)
    executed = execute_dynamic_execution_plan(
        store,
        coordinator,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        plan_ref=opened["plan_ref"],
        model_adapter_factory=_sequential_factory(adapters),
        executed_at="2026-09-11T01:30:00Z",
    )
    coordinator.release()
    return {"plan_ref": opened["plan_ref"], **executed}


def test_two_agreeing_agents_produce_one_agreeing_member_and_admit_both(tmp_path: Any) -> None:
    world = authorized_world(tmp_path, risk_class="HIGH")
    adapters = [SeededMultiAgentAdapter(candidate_fields={"summary": "same"}) for _ in range(2)]
    result = _open_and_execute(world, adapters)

    conflict_set = result["conflict_set"]
    assert len(conflict_set["members"]) == 1
    member = conflict_set["members"][0]
    assert member["member_kind"] == "AGREEING"
    assert len(member["slot_output_refs"]["members"]) == 2

    aggregation_input = result["aggregation_input"]
    assert aggregation_input["unresolved_capabilities"] == []
    assert len(aggregation_input["admitted_slot_output_refs"]["members"]) == 2
    assert aggregation_input["absent_slot_output_refs"]["members"] == []


def test_two_contradicting_agents_preserve_full_membership_and_admit_neither(tmp_path: Any) -> None:
    world = authorized_world(tmp_path, risk_class="HIGH")
    adapters = [
        SeededMultiAgentAdapter(candidate_fields={"summary": "alpha"}),
        SeededMultiAgentAdapter(candidate_fields={"summary": "beta"}),
    ]
    result = _open_and_execute(world, adapters)

    slot_outputs = {so["slot_index"]: so for so in result["slot_outputs"]}
    assert slot_outputs[0]["result_fingerprint"] != slot_outputs[1]["result_fingerprint"]

    conflict_set = result["conflict_set"]
    assert len(conflict_set["members"]) == 1
    member = conflict_set["members"][0]
    assert member["member_kind"] == "CONTRADICTING"
    assert len(member["fingerprint_groups"]) == 2
    all_refs = {
        ref["id"]
        for group in member["fingerprint_groups"]
        for ref in group["slot_output_refs"]["members"]
    }
    assert all_refs == {so["multi_agent_slot_output_id"] for so in result["slot_outputs"]}

    aggregation_input = result["aggregation_input"]
    assert aggregation_input["unresolved_capabilities"] == ["PROPOSE_EVIDENCE_CANDIDATE"]
    assert aggregation_input["admitted_slot_output_refs"]["members"] == []

    # No majority vote, confidence average, or last-writer-wins anywhere: neither candidate is
    # ever silently promoted, regardless of call order.
    reversed_result = _open_and_execute(
        authorized_world(tmp_path, risk_class="HIGH", subdir="reversed"),
        list(reversed(adapters)),
    )
    reversed_member = reversed_result["conflict_set"]["members"][0]
    assert reversed_member["member_kind"] == "CONTRADICTING"
    assert reversed_result["aggregation_input"]["admitted_slot_output_refs"]["members"] == []


def test_a_failed_slot_stays_explicit_alongside_the_others_admitted_output(tmp_path: Any) -> None:
    world = authorized_world(tmp_path, risk_class="HIGH")
    adapters = [
        SeededMultiAgentAdapter(candidate_fields={"summary": "ok"}),
        SeededMultiAgentAdapter(adapter_outcome="REFUSED"),
    ]
    result = _open_and_execute(world, adapters)

    slot_outputs = {so["slot_index"]: so for so in result["slot_outputs"]}
    assert slot_outputs[0]["outcome"] == "CANDIDATE_ACCEPTED"
    assert slot_outputs[1]["outcome"] == "REFUSED"
    assert slot_outputs[1]["result_fingerprint"] is None

    conflict_set = result["conflict_set"]
    kinds = sorted(member["member_kind"] for member in conflict_set["members"])
    assert kinds == ["ABSENT", "AGREEING"]
    absent_member = next(m for m in conflict_set["members"] if m["member_kind"] == "ABSENT")
    assert absent_member["slot_index"] == 1
    assert absent_member["outcome"] == "REFUSED"

    aggregation_input = result["aggregation_input"]
    assert aggregation_input["unresolved_capabilities"] == []
    assert len(aggregation_input["admitted_slot_output_refs"]["members"]) == 1
    assert len(aggregation_input["absent_slot_output_refs"]["members"]) == 1


def test_no_slot_output_is_ever_silently_dropped_from_the_considered_set(tmp_path: Any) -> None:
    world = authorized_world(tmp_path, risk_class="CRITICAL")
    adapters = [
        SeededMultiAgentAdapter(candidate_fields={"summary": "x"}),
        SeededMultiAgentAdapter(candidate_fields={"summary": "y"}),
        SeededMultiAgentAdapter(adapter_outcome="TIMEOUT"),
    ]
    result = _open_and_execute(world, adapters)
    conflict_set = result["conflict_set"]
    assert set(conflict_set["considered_slot_output_refs"]["members"][0]) == {"kind", "id"}
    assert len(conflict_set["considered_slot_output_refs"]["members"]) == 3
    kinds = sorted(member["member_kind"] for member in conflict_set["members"])
    assert kinds == ["ABSENT", "CONTRADICTING"]


def test_this_package_never_marks_evidence_sufficient_or_declares_a_verdict(tmp_path: Any) -> None:
    """P19-C7: the aggregation input, and the terminal orchestration receipt, are inputs to
    the existing Evidence owner -- never an Evidence verdict this package itself declares."""

    world = authorized_world(tmp_path, risk_class="LOW")
    adapters = [SeededMultiAgentAdapter(candidate_fields={"summary": "ok"})]
    result = _open_and_execute(world, adapters)

    aggregation_input = result["aggregation_input"]
    assert "evidence_level" not in aggregation_input
    assert "status" not in aggregation_input
    assert "sufficient" not in str(aggregation_input).lower()

    coordinator = _coordinator(world)
    handed_off = route_orchestration_to_evidence(
        world["store"],
        coordinator,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        plan_ref=result["plan_ref"],
        evidence_request_template=evidence_request_for(world["project_id"], provenance=None),
        completed_at="2026-09-11T01:40:00Z",
    )
    coordinator.release()
    orchestration_receipt = handed_off["orchestration_receipt"]
    assert "evidence_level" not in orchestration_receipt
    assert "sufficient" not in str(orchestration_receipt).lower()
    # Sufficiency is the existing Evidence owner's own field, on its own record -- reached,
    # never declared, by this package.
    assert "evidence_level" in handed_off["evidence_refs"][0]
