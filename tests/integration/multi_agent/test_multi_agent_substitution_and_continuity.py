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
    MultiAgentRecordIntegrityError,
    MultiAgentRequirementError,
    MultiAgentStaleStateError,
)
from manosube_agent_civilization.multi_agent.route import (
    compute_slot_attempt_envelope_claim_id,
    resolve_and_verify_committed_slot_attempt_envelope_claim,
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


def test_p19_r4_f5_a_redirected_envelope_ref_on_a_committed_claim_is_refused(
    tmp_path: Any,
) -> None:
    """Structural Review Round 4, P19-R4-F5's own required proof:
    ``resolve_and_verify_committed_slot_attempt_envelope_claim`` previously verified only the
    claim's own declared identity against the Store lookup key -- never recomputing its own
    identity or its own semantic fingerprint from its full content, unlike every sibling resolver
    in this module. A claim whose ``model_execution_envelope_ref`` is redirected to name a
    *different*, genuinely real, committed Envelope (never a forged or nonexistent one) --
    while its own declared identity and fingerprint fields are left exactly as they were before
    the redirection -- is a schema-valid record whose lookup key still matches its own declared
    id. Only an independent recomputation of its own semantic fingerprint from its actual
    content (which includes ``model_execution_envelope_ref``) can catch this, and this proof
    shows it now does.
    """

    import json

    world = authorized_world(tmp_path, risk_class="HIGH")
    store = world["store"]
    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()

    # Distinct candidate content per slot (never the same adapter instance twice): the two
    # slots share one Model Work Unit, so a real Envelope's own content-addressed identity
    # differs between slots only if the candidate content itself differs.
    factory_calls = iter(
        [
            SeededMultiAgentAdapter(candidate_fields={"summary": "slot-0-candidate"}),
            SeededMultiAgentAdapter(candidate_fields={"summary": "slot-1-candidate"}),
        ]
    )
    coordinator = _coordinator(world)
    executed = execute_dynamic_execution_plan(
        store,
        coordinator,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        plan_ref=opened["plan_ref"],
        model_adapter_factory=lambda: next(factory_calls),
        executed_at="2026-09-11T01:30:00Z",
    )
    coordinator.release()
    assert len(executed["slot_outputs"]) == 2
    envelope_ref_0 = executed["slot_outputs"][0]["model_execution_envelope_ref"]
    envelope_ref_1 = executed["slot_outputs"][1]["model_execution_envelope_ref"]
    assert envelope_ref_0 is not None and envelope_ref_1 is not None
    assert envelope_ref_0["id"] != envelope_ref_1["id"]

    claim_key = compute_slot_attempt_envelope_claim_id(
        project_id=world["project_id"], plan_ref=dict(opened["plan_ref"]), slot_index=0
    )
    # Sanity: the genuine, untampered claim resolves cleanly before this test tampers it.
    assert (
        resolve_and_verify_committed_slot_attempt_envelope_claim(
            store, world["project_id"], claim_key
        )
        is not None
    )

    from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
    from manosube_agent_civilization.store.atomic_write import atomic_write

    claim_kind = "multi_agent_slot_attempt_envelope_claim"
    claim_path = (
        store.root / "projects" / world["project_id"] / "records" / claim_kind / f"{claim_key}.json"
    )
    tampered = json.loads(claim_path.read_text(encoding="utf-8"))
    assert tampered["model_execution_envelope_ref"]["id"] == envelope_ref_0["id"]
    # The redirection: slot 0's own claim now names slot 1's own genuinely real, committed
    # Envelope, while every other declared field -- including the claim's own declared identity
    # and semantic fingerprint -- is left exactly as it was.
    tampered["model_execution_envelope_ref"] = dict(envelope_ref_1)
    tampered_bytes = canonical_json_bytes(tampered)

    # The Store's own manifest/journal claimant mechanism keeps a staged copy of this same
    # record alongside the permanent file and refuses (CorruptStoreError) if the two ever
    # diverge -- a real, independent, lower-layer integrity check this test must not trip, so
    # every staged copy this claim's own committing transaction(s) left behind is overwritten
    # identically, leaving only the claim's own declared fingerprint stale relative to its own
    # (now-redirected) content -- exactly the gap this proof targets.
    recovery_dir = store.root / "projects" / world["project_id"] / "state" / "recovery"
    staged_name = f"{claim_kind}__{claim_key}.json"
    for journal in recovery_dir.iterdir() if recovery_dir.exists() else []:
        staged_path = journal / "records" / staged_name
        if staged_path.exists():
            atomic_write(staged_path, tampered_bytes)
    atomic_write(claim_path, tampered_bytes)

    with pytest.raises(MultiAgentRecordIntegrityError):
        resolve_and_verify_committed_slot_attempt_envelope_claim(
            store, world["project_id"], claim_key
        )
