"""Phase 19 (Issue #77) V7: tamper/substitution and Kernel continuity.

Cross-project/State/Difference/plan/slot/output substitution refuses; the canonical owner
counts this repository already established remain exactly one; Phase 12, 16 and 18's own
accepted public contracts remain intact and untouched by this delivery.
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.fixtures.model_runtime_world import touch_state
from tests.fixtures.multi_agent_world import (
    SeededMultiAgentAdapter,
    authorized_world,
    bind_into,
    commit_boundary,
    commit_difference,
    commit_grant,
    evidence_request_for,
    open_plan_kwargs,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.agent_runtime import start_temporary_agent
from manosube_agent_civilization.multi_agent import (
    execute_dynamic_execution_plan,
    open_dynamic_execution_plan,
    route_orchestration_to_evidence,
)
from manosube_agent_civilization.multi_agent.errors import (
    MultiAgentRequirementError,
    MultiAgentStaleStateError,
)
from manosube_agent_civilization.store import FileStateStore


def _coordinator(world: dict[str, Any]) -> Any:
    return start_temporary_agent(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
    )


def test_a_difference_belonging_to_another_project_is_never_relabelled_in(tmp_path: Any) -> None:
    """One real Store, two genuinely bound projects. A Difference committed under project B
    does not resolve at all when a coordinator for project A names it -- the Store's own
    project-scoped storage refuses the substitution before this package's own identity checks
    would even run."""

    store = FileStateStore(tmp_path / "shared", schema_root=SCHEMA_ROOT)
    project_a = bind_into(store, project_id="PRJ-MULTI-AGENT-CROSS-A")
    project_b = bind_into(store, project_id="PRJ-MULTI-AGENT-CROSS-B")
    foreign_difference_ref, _ = commit_difference(store, project_b["project_id"], risk_class="LOW")

    boundary_ref, _ = commit_boundary(
        store, project_a["project_id"], project_a["project_binding_id"]
    )
    grant_ref, _ = commit_grant(
        store, project_a["project_id"], foreign_difference_ref, boundary_ref
    )
    # Constructed only after every seeding commit above -- so the only thing "wrong" about
    # this call is the cross-project foreign difference_ref, never a stale contract.
    coordinator = start_temporary_agent(
        store,
        project_id=project_a["project_id"],
        project_binding_id=project_a["project_binding_id"],
    )
    with pytest.raises(MultiAgentRequirementError):
        open_dynamic_execution_plan(
            store,
            coordinator,
            project_id=project_a["project_id"],
            project_binding_id=project_a["project_binding_id"],
            difference_ref=foreign_difference_ref,
            boundary_ref=boundary_ref,
            model_execution_grant_refs=[grant_ref],
            adapter_identity={"adapter": "fake_model_adapter", "version": "0.1"},
            opened_at="2026-09-11T01:00:00Z",
            expires_at="2026-09-11T02:00:00Z",
        )
    coordinator.release()


def test_a_stale_coordinator_contract_refuses_to_open_a_plan(tmp_path: Any) -> None:
    world = authorized_world(tmp_path, risk_class="LOW")
    store = world["store"]
    stale_coordinator = _coordinator(world)
    # The Canonical State moves underneath the already-constructed coordinator, entirely
    # unrelated to anything this plan is about.
    touch_state(store, world["project_id"])

    with pytest.raises(MultiAgentStaleStateError):
        open_dynamic_execution_plan(store, stale_coordinator, **open_plan_kwargs(world))
    stale_coordinator.release()


def test_evidence_handoff_refuses_a_plan_that_was_never_executed(tmp_path: Any) -> None:
    """Cross-output substitution's own decisive form: no in-memory shortcut exists from
    "a plan was opened" to "an Evidence hand-off can run" -- the aggregation input a real
    ``execute_dynamic_execution_plan`` call alone produces must actually exist in the Store."""

    world = authorized_world(tmp_path, risk_class="LOW")
    store = world["store"]
    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()

    coordinator = _coordinator(world)
    with pytest.raises(MultiAgentRequirementError):
        route_orchestration_to_evidence(
            store,
            coordinator,
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            plan_ref=opened["plan_ref"],
            evidence_request_template=evidence_request_for(world["project_id"], provenance=None),
            completed_at="2026-09-11T01:40:00Z",
        )
    coordinator.release()


def test_a_plan_ref_from_a_different_project_is_refused_by_execute(tmp_path: Any) -> None:
    world_a = authorized_world(tmp_path, risk_class="LOW", subdir="a")
    world_b = authorized_world(tmp_path, risk_class="LOW", subdir="b")

    coordinator_a = _coordinator(world_a)
    opened_a = open_dynamic_execution_plan(
        world_a["store"], coordinator_a, **open_plan_kwargs(world_a)
    )
    coordinator_a.release()

    coordinator_b = _coordinator(world_b)
    with pytest.raises(MultiAgentRequirementError):
        execute_dynamic_execution_plan(
            world_b["store"],
            coordinator_b,
            project_id=world_b["project_id"],
            project_binding_id=world_b["project_binding_id"],
            plan_ref=opened_a["plan_ref"],
            model_adapter_factory=lambda: SeededMultiAgentAdapter(),
            executed_at="2026-09-11T01:30:00Z",
        )
    coordinator_b.release()


def test_phase_12_public_surface_is_unchanged_by_this_delivery() -> None:
    import manosube_agent_civilization.agent_runtime as agent_runtime_package

    assert sorted(agent_runtime_package.__all__) == [
        "AgentReleasedError",
        "AgentRuntimeError",
        "TemporaryAgent",
        "start_temporary_agent",
    ]


def test_phase_16_public_surface_is_unchanged_by_this_delivery() -> None:
    import manosube_agent_civilization.model_runtime as model_runtime_package

    assert model_runtime_package.PUBLIC_MODEL_RUNTIME_ENTRY_POINT_COUNT == 5
    routes = {
        "open_model_work_unit",
        "execute_model_work_unit",
        "record_model_swap",
        "recover_model_execution_session",
        "route_model_execution_to_evidence",
    }
    assert routes <= set(model_runtime_package.__all__)


def test_phase_18_public_surface_is_unchanged_by_this_delivery() -> None:
    import manosube_agent_civilization.change_executor as change_executor_package

    assert "compose_change_executor" in dir(change_executor_package) or hasattr(
        change_executor_package, "compose_change_executor"
    )


def test_kernel_topology_still_reports_single_canonical_owners() -> None:
    """K-002/K-003's own repository-wide static topology inventory
    (:mod:`manosube_agent_civilization.topology`) is untouched by this delivery, and still
    reports exactly one canonical State owner and one canonical Authority/transition owner."""

    from manosube_agent_civilization import topology

    topology.kernel_topology_inventory.cache_clear()
    assert topology.k002_single_canonical_state_owner() is True
    assert topology.k003_single_authority_and_transition_owner() is True
