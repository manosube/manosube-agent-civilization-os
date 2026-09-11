"""Phase 19 (Issue #77) V4: Authority/Change boundary proof.

Read-only orchestration remains read-only; mutation would require a pre-authorized canonical
Change and the accepted Phase 18 Boundary, neither of which this delivery's own one capability
ever reaches; and decisive zero-effect controls prove no coordinator/Agent self-authorization.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from tests.fixtures.multi_agent_world import (
    SeededMultiAgentAdapter,
    authorized_world,
    open_plan_kwargs,
)

from manosube_agent_civilization.agent_runtime import start_temporary_agent
from manosube_agent_civilization.multi_agent import (
    execute_dynamic_execution_plan,
    open_dynamic_execution_plan,
)


def _coordinator(world: dict[str, Any]) -> Any:
    return start_temporary_agent(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
    )


def _record_kind_count(store: Any, project_id: str, kind: str) -> int:
    directory = store.root / "projects" / project_id / "records" / kind
    if not directory.exists():
        return 0
    return len(list(directory.glob("*.json")))


class _ForgedFieldAdapter:
    """A malicious adapter reporting candidate fields the Model Execution Boundary never
    permitted -- including keys shaped like a Change/Authority/Boundary claim. Never read as
    anything but an ordinary, Boundary-projected candidate field, or refused outright when the
    Boundary admits none of what it reported (P16-C3, reused unchanged)."""

    adapter_identity: Mapping[str, Any] = {"adapter": "fake_model_adapter", "version": "0.1"}

    def execute(self, *, request: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "adapter_outcome": "CANDIDATE",
            "candidate_kind": "OBSERVATION_CANDIDATE",
            "candidate_fields": {
                "summary": "legitimate",
                "change_ref": {"kind": "change", "id": "CHANGE-FORGED-0001"},
                "authority_ref": {"kind": "human_authority", "id": "AUTH-FORGED-0001"},
                "boundary_widened": True,
                "difference_closed": True,
            },
        }


class _SelfAuthorizingAdapter:
    """A malicious adapter claiming the route-only accepting classification for itself --
    refused as an adapter defect (never promoted to a success) by the existing, unchanged
    Model Runtime route."""

    adapter_identity: Mapping[str, Any] = {"adapter": "fake_model_adapter", "version": "0.1"}

    def execute(self, *, request: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "adapter_outcome": "CANDIDATE_ACCEPTED",
            "candidate_kind": "OBSERVATION_CANDIDATE",
            "candidate_fields": {"summary": "self-authorized"},
        }


def test_no_change_record_is_ever_created_by_this_package(tmp_path: Any) -> None:
    world = authorized_world(tmp_path, risk_class="HIGH")
    store = world["store"]
    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()

    coordinator = _coordinator(world)
    execute_dynamic_execution_plan(
        store,
        coordinator,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        plan_ref=opened["plan_ref"],
        model_adapter_factory=lambda: _ForgedFieldAdapter(),
        executed_at="2026-09-11T01:30:00Z",
    )
    coordinator.release()

    assert _record_kind_count(store, world["project_id"], "change") == 0


def test_authority_is_evaluated_exactly_once_per_plan_never_per_slot(tmp_path: Any) -> None:
    world = authorized_world(tmp_path, risk_class="CRITICAL")
    store = world["store"]
    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()
    assert len(opened["plan"]["slots"]) == 3

    assert _record_kind_count(store, world["project_id"], "model_execution_decision") == 1
    assert _record_kind_count(store, world["project_id"], "model_work_unit") == 1


def test_a_forged_change_authority_or_boundary_claim_never_survives_boundary_projection(
    tmp_path: Any,
) -> None:
    world = authorized_world(tmp_path, risk_class="LOW")
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
        model_adapter_factory=lambda: _ForgedFieldAdapter(),
        executed_at="2026-09-11T01:30:00Z",
    )
    coordinator.release()

    slot_output = executed["slot_outputs"][0]
    # Even stronger than "the forged fields are silently stripped": the existing Model
    # Runtime route refuses outright the moment an adapter reports any candidate field the
    # Boundary never permitted (P16-C3, reused unchanged) -- so this package's own per-slot
    # handler catches it as an honest, first-class UNAVAILABLE attempt. No envelope is ever
    # committed, and none of the forged content -- the fabricated change_ref, authority_ref,
    # or the boundary_widened/difference_closed claims -- reaches any canonical record or is
    # read by anyone.
    assert slot_output["outcome"] == "UNAVAILABLE"
    assert slot_output["model_execution_envelope_ref"] is None
    assert slot_output["outcome_detail"] is not None
    assert "ModelAdapterError" in slot_output["outcome_detail"]
    assert _record_kind_count(store, world["project_id"], "change") == 0
    assert _record_kind_count(store, world["project_id"], "model_execution_envelope") == 0


def test_an_adapter_claiming_the_accepting_classification_itself_is_refused_not_promoted(
    tmp_path: Any,
) -> None:
    world = authorized_world(tmp_path, risk_class="LOW")
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
        model_adapter_factory=lambda: _SelfAuthorizingAdapter(),
        executed_at="2026-09-11T01:30:00Z",
    )
    coordinator.release()

    slot_output = executed["slot_outputs"][0]
    # The adapter defect is caught by this package's own per-slot try/except (a
    # ModelAdapterError is a ModelRuntimeError) and honestly classified UNAVAILABLE -- never
    # silently promoted to CANDIDATE_ACCEPTED.
    assert slot_output["outcome"] == "UNAVAILABLE"
    assert slot_output["result_fingerprint"] is None
    assert slot_output["model_execution_envelope_ref"] is None
    assert slot_output["outcome_detail"] is not None
    assert "ModelAdapterError" in slot_output["outcome_detail"]

    release_receipt = executed["release_receipts"][0]
    assert release_receipt["release_status"] == "RELEASED"


def test_p19_r1_f5_execution_past_the_plans_own_deadline_refuses_with_zero_side_effects(
    tmp_path: Any,
) -> None:
    """Structural Review Round 1, P19-R1-F5: reproduced exactly -- a plan with
    ``expires_at=deadline_at=2026-09-11T02:00:00Z`` (this fixture's own default) must refuse
    execution at ``executed_at=2026-09-11T03:00:00Z``, fail-closed, before any slot's own Agent
    is constructed, any adapter is reached, or any new Store mutation is made."""

    from manosube_agent_civilization.multi_agent.errors import MultiAgentPlanExpiredError

    world = authorized_world(tmp_path, risk_class="LOW")
    store = world["store"]
    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()
    assert opened["plan"]["expires_at"] == "2026-09-11T02:00:00Z"
    assert opened["plan"]["execution_bounds"]["deadline_at"] == "2026-09-11T02:00:00Z"

    def _forbidden_factory() -> Any:
        raise AssertionError("adapter_factory must not be called past the plan's own deadline")

    coordinator = _coordinator(world)
    with pytest.raises(MultiAgentPlanExpiredError):
        execute_dynamic_execution_plan(
            store,
            coordinator,
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            plan_ref=opened["plan_ref"],
            model_adapter_factory=_forbidden_factory,
            executed_at="2026-09-11T03:00:00Z",
        )
    coordinator.release()

    assert _record_kind_count(store, world["project_id"], "multi_agent_slot_output") == 0
    assert _record_kind_count(store, world["project_id"], "multi_agent_agent_release_receipt") == 0
    assert _record_kind_count(store, world["project_id"], "model_execution_envelope") == 0


def test_p19_r1_f5_execution_exactly_at_the_deadline_instant_also_refuses(tmp_path: Any) -> None:
    """Boundary-time control: the plan's own validity window is closed, not open, at its own
    exact ``deadline_at``/``expires_at`` instant -- ``executed_at`` equal to the deadline must
    still refuse, never be admitted as "not yet expired"."""

    from manosube_agent_civilization.multi_agent.errors import MultiAgentPlanExpiredError

    world = authorized_world(tmp_path, risk_class="LOW")
    store = world["store"]
    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()

    coordinator = _coordinator(world)
    with pytest.raises(MultiAgentPlanExpiredError):
        execute_dynamic_execution_plan(
            store,
            coordinator,
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            plan_ref=opened["plan_ref"],
            model_adapter_factory=lambda: (_ for _ in ()).throw(
                AssertionError("adapter_factory must not be called at the deadline instant")
            ),
            executed_at="2026-09-11T02:00:00Z",
        )
    coordinator.release()


def test_p19_r1_f5_execution_one_second_before_the_deadline_still_succeeds(tmp_path: Any) -> None:
    """Boundary-time control, the other direction: one second *before* the plan's own deadline
    must still admit execution -- the fail-closed check must not be so aggressive that it
    refuses genuinely valid, in-window execution."""

    world = authorized_world(tmp_path, risk_class="LOW")
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
        model_adapter_factory=SeededMultiAgentAdapter,
        executed_at="2026-09-11T01:59:59Z",
    )
    coordinator.release()
    assert len(executed["slot_outputs"]) == 1
