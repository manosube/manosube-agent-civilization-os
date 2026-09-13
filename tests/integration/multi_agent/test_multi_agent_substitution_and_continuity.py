"""Phase 19 (Issue #77) V7: tamper/substitution and Kernel continuity.

Cross-project/State/Difference/plan/slot/output substitution refuses; the canonical owner
counts this repository already established remain exactly one; Phase 12, 16 and 18's own
accepted public contracts remain intact and untouched by this delivery.
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.fixtures.model_runtime_world import commit_records, touch_state
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
from manosube_agent_civilization.evidence import EVIDENCE_REFERENCE_KIND
from manosube_agent_civilization.model_runtime.claim_identity import (
    multi_agent_slot_attempt_envelope_claim_semantic_fingerprint,
)
from manosube_agent_civilization.model_runtime.identity import (
    model_execution_envelope_id,
    model_execution_envelope_semantic_fingerprint,
)
from manosube_agent_civilization.multi_agent import (
    execute_dynamic_execution_plan,
    open_dynamic_execution_plan,
    route_orchestration_to_evidence,
)
from manosube_agent_civilization.multi_agent.engine import (
    compute_attempt_id,
    compute_slot_output_id,
)
from manosube_agent_civilization.multi_agent.errors import (
    MultiAgentRecordIntegrityError,
    MultiAgentRequirementError,
    MultiAgentStaleStateError,
)
from manosube_agent_civilization.multi_agent.identity import (
    multi_agent_agent_release_receipt_semantic_fingerprint,
    multi_agent_evidence_aggregation_input_semantic_fingerprint,
    multi_agent_slot_output_semantic_fingerprint,
)
import manosube_agent_civilization.multi_agent.route as route_module
from manosube_agent_civilization.multi_agent.route import (
    compute_slot_attempt_envelope_claim_id,
    resolve_and_verify_committed_slot_attempt_envelope_claim,
)
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.store.atomic_write import atomic_write


def _overwrite_committed_record(
    store: FileStateStore, project_id: str, kind: str, record_id: str, body: dict[str, Any]
) -> None:
    """Overwrite an already-committed record's own file content in place, at its own unchanged
    (kind, id) key -- including any staged recovery-journal copy of the same record -- so the
    Store's own manifest-tracked committed-boundary visibility (which keys by (kind, id), never
    by content) is never itself tripped by a change targeted at exactly the narrow-key-excluded
    fields this delivery's own tests exercise. See ``test_p19_r4_f5_...``'s own established
    convention, reused unchanged here for Round 9's own required proofs."""

    body_bytes = canonical_json_bytes(body)
    record_path = store.root / "projects" / project_id / "records" / kind / f"{record_id}.json"
    recovery_dir = store.root / "projects" / project_id / "state" / "recovery"
    staged_name = f"{kind}__{record_id}.json"
    for journal in recovery_dir.iterdir() if recovery_dir.exists() else []:
        staged_path = journal / "records" / staged_name
        if staged_path.exists():
            atomic_write(staged_path, body_bytes)
    atomic_write(record_path, body_bytes)


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


def _second_plan_kwargs_in(world: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Commit a second, genuinely distinct Difference (-> a second, genuinely distinct Model
    Work Unit) in *world*'s own already-bound project, reusing its already-committed Boundary --
    and return ``(open_dynamic_execution_plan kwargs, the first plan's own kwargs)`` so a caller
    can open two plans, of two genuinely different lineages, in the identical project/Store."""

    store = world["store"]
    second_difference_ref, _ = commit_difference(
        store,
        world["project_id"],
        risk_class="LOW",
        fact_value="OTHER-LINEAGE",
        transaction_id="TX-MULTI-AGENT-DIFFERENCE-0002",
    )
    second_grant_ref, _ = commit_grant(
        store,
        world["project_id"],
        second_difference_ref,
        world["boundary_ref"],
        transaction_id="TX-MODEL-GRANT-0002",
    )
    second_kwargs = {
        "project_id": world["project_id"],
        "project_binding_id": world["project_binding_id"],
        "difference_ref": second_difference_ref,
        "boundary_ref": world["boundary_ref"],
        "model_execution_grant_refs": [second_grant_ref],
        "adapter_identity": {"adapter": "fake_model_adapter", "version": "0.1"},
        "opened_at": "2026-09-11T01:00:00Z",
        "expires_at": "2026-09-11T02:00:00Z",
    }
    return second_kwargs, open_plan_kwargs(world)


def test_p19_r9_f1_a_claim_redirected_to_a_genuine_envelope_from_a_different_plans_lineage_is_refused(
    tmp_path: Any, monkeypatch: Any
) -> None:
    """Structural Review Round 9, P19-R9-F1's own required proof: a
    ``multi_agent_slot_attempt_envelope_claim`` that is itself fully self-consistent (its own
    declared identity and semantic fingerprint both independently recomputed and equal) and that
    names a genuinely real, committed Model Execution Envelope (never a forged or nonexistent
    one) still names the *wrong* Envelope when that Envelope belongs to a different plan's own
    Model Work Unit/Difference/Authority lineage -- every check Round 4-8 already established
    passes it; only ``_require_envelope_matches_plan_lineage`` (comparing the Envelope's own
    already-verified fields against this plan's own) catches it. Proves zero new Agent/adapter
    calls, zero terminal writes, and zero State advance on the refused replay.
    """

    world = authorized_world(tmp_path, risk_class="LOW")
    store = world["store"]

    coordinator = _coordinator(world)
    opened_a = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()

    second_kwargs, _ = _second_plan_kwargs_in(world)
    coordinator = _coordinator(world)
    opened_b = open_dynamic_execution_plan(store, coordinator, **second_kwargs)
    coordinator.release()
    assert opened_a["plan"]["model_work_unit_ref"] != opened_b["plan"]["model_work_unit_ref"]

    coordinator = _coordinator(world)
    executed_b = execute_dynamic_execution_plan(
        store,
        coordinator,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        plan_ref=opened_b["plan_ref"],
        model_adapter_factory=lambda: SeededMultiAgentAdapter(),
        executed_at="2026-09-11T01:30:00Z",
    )
    coordinator.release()
    foreign_envelope_ref = dict(executed_b["slot_outputs"][0]["model_execution_envelope_ref"])
    assert foreign_envelope_ref is not None

    # Crash Plan A's own sole slot strictly after its own real claim+Envelope commit but before
    # its own terminal slot_output/release_receipt commit -- the identical established technique
    # ``test_p19_r1_f2_a_crash_between_slot_output_derivation_and_commit_leaves_neither_record``
    # (Round 1/3) uses, reused here unchanged to reach a genuine claim-only intermediate state.
    real_derive = route_module.derive_multi_agent_agent_release_receipt

    def _crashing_derive(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("simulated crash before the atomic slot-complete commit")

    monkeypatch.setattr(route_module, "derive_multi_agent_agent_release_receipt", _crashing_derive)
    crashing_adapter = SeededMultiAgentAdapter(candidate_fields={"summary": "a-own"})
    coordinator = _coordinator(world)
    with pytest.raises(
        RuntimeError, match="simulated crash before the atomic slot-complete commit"
    ):
        execute_dynamic_execution_plan(
            store,
            coordinator,
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            plan_ref=opened_a["plan_ref"],
            model_adapter_factory=lambda: crashing_adapter,
            executed_at="2026-09-11T01:35:00Z",
        )
    coordinator.release()
    monkeypatch.setattr(route_module, "derive_multi_agent_agent_release_receipt", real_derive)

    claim_key = compute_slot_attempt_envelope_claim_id(
        project_id=world["project_id"], plan_ref=dict(opened_a["plan_ref"]), slot_index=0
    )
    real_claim = resolve_and_verify_committed_slot_attempt_envelope_claim(
        store, world["project_id"], claim_key
    )
    assert real_claim is not None
    assert real_claim["model_execution_envelope_ref"]["id"] != foreign_envelope_ref["id"]

    # The redirection: Plan A's own slot 0 claim now names Plan B's own genuinely real,
    # committed, but wholly unrelated Envelope, self-consistently refingerprinted.
    tampered_claim = dict(real_claim)
    tampered_claim["model_execution_envelope_ref"] = dict(foreign_envelope_ref)
    tampered_claim["multi_agent_slot_attempt_envelope_claim_semantic_fingerprint"] = (
        multi_agent_slot_attempt_envelope_claim_semantic_fingerprint(tampered_claim)
    )
    _overwrite_committed_record(
        store,
        world["project_id"],
        "multi_agent_slot_attempt_envelope_claim",
        claim_key,
        tampered_claim,
    )

    # Sanity: the tampered claim is now fully self-consistent on its own -- exactly the
    # individually-valid-but-cross-referentially-wrong case P19-R9-F1 targets.
    assert (
        resolve_and_verify_committed_slot_attempt_envelope_claim(
            store, world["project_id"], claim_key
        )
        is not None
    )

    state_before = store.load_current(world["project_id"])

    def _unreachable_adapter() -> Any:
        raise AssertionError("no new adapter call is ever permitted for this replay")

    coordinator = _coordinator(world)
    with pytest.raises(MultiAgentRecordIntegrityError):
        execute_dynamic_execution_plan(
            store,
            coordinator,
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            plan_ref=opened_a["plan_ref"],
            model_adapter_factory=_unreachable_adapter,
            executed_at="2026-09-11T01:40:00Z",
        )
    coordinator.release()

    state_after = store.load_current(world["project_id"])
    assert state_after["state_revision"] == state_before["state_revision"]
    slot_output_key = compute_slot_output_id(
        project_id=world["project_id"], plan_ref=dict(opened_a["plan_ref"]), slot_index=0
    )
    assert (
        store.resolve_record(world["project_id"], "multi_agent_slot_output", slot_output_key)
        is None
    )


def test_p19_r9_f2_a_slot_output_declaring_a_different_execution_snapshot_is_refused_on_replay(
    tmp_path: Any,
) -> None:
    """Structural Review Round 9, P19-R9-F2's own required proof: a self-consistently-
    fingerprinted ``multi_agent_slot_output`` planted at its own correct narrow key
    (``compute_slot_output_id`` covers only ``plan_ref``/``slot_index``/``attempt_ordinal`` --
    see :mod:`~manosube_agent_civilization.multi_agent.identity`'s own module docstring) but
    declaring a different ``execution_snapshot`` than this exact plan's own admitted
    ``boot_state_revision``/``boot_semantic_fingerprint`` passed every existing check unnoticed
    before this delivery; ``_require_slot_output_matches_plan_lineage`` now refuses it on replay.
    """

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
        model_adapter_factory=lambda: SeededMultiAgentAdapter(),
        executed_at="2026-09-11T01:30:00Z",
    )
    coordinator.release()
    genuine_slot_output = executed["slot_outputs"][0]

    tampered_slot_output = dict(genuine_slot_output)
    tampered_slot_output["execution_snapshot"] = {
        "state_revision": int(genuine_slot_output["execution_snapshot"]["state_revision"]) + 1,
        "semantic_fingerprint": dict(
            genuine_slot_output["execution_snapshot"]["semantic_fingerprint"]
        ),
    }
    tampered_slot_output["multi_agent_slot_output_semantic_fingerprint"] = (
        multi_agent_slot_output_semantic_fingerprint(tampered_slot_output)
    )
    slot_output_key = str(genuine_slot_output["multi_agent_slot_output_id"])
    _overwrite_committed_record(
        store, world["project_id"], "multi_agent_slot_output", slot_output_key, tampered_slot_output
    )

    # Sanity: the tampered slot output resolves cleanly as fully self-consistent on its own.
    assert (
        route_module.resolve_and_verify_committed_slot_output(
            store, world["project_id"], slot_output_key
        )
        is not None
    )

    def _unreachable_adapter() -> Any:
        raise AssertionError("no new adapter call is ever permitted for this replay")

    coordinator = _coordinator(world)
    with pytest.raises(MultiAgentRecordIntegrityError):
        execute_dynamic_execution_plan(
            store,
            coordinator,
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            plan_ref=opened["plan_ref"],
            model_adapter_factory=_unreachable_adapter,
            executed_at="2026-09-11T01:40:00Z",
        )
    coordinator.release()


def test_p19_r9_f2_a_release_receipt_naming_a_different_attempt_id_is_refused_at_evidence_handoff(
    tmp_path: Any,
) -> None:
    """Structural Review Round 9, P19-R9-F2's own required proof: a release receipt's own
    narrow Store key never includes its own declared ``attempt_id`` -- a self-consistently-
    fingerprinted receipt planted at the correct key but naming a *different*, validly-formatted
    ``attempt_id`` than the slot output it is supposed to release passed every existing check
    unnoticed before this delivery; ``_require_release_receipt_matches_slot_output`` now refuses
    it at Evidence hand-off."""

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
        model_adapter_factory=lambda: SeededMultiAgentAdapter(),
        executed_at="2026-09-11T01:30:00Z",
    )
    coordinator.release()
    genuine_receipt = executed["release_receipts"][0]

    wrong_attempt_id = compute_attempt_id(
        project_id=world["project_id"], plan_ref=dict(opened["plan_ref"]), slot_index=99
    )
    assert wrong_attempt_id != genuine_receipt["attempt_id"]
    tampered_receipt = dict(genuine_receipt)
    tampered_receipt["attempt_id"] = wrong_attempt_id
    tampered_receipt["multi_agent_agent_release_receipt_semantic_fingerprint"] = (
        multi_agent_agent_release_receipt_semantic_fingerprint(tampered_receipt)
    )
    receipt_key = str(genuine_receipt["multi_agent_agent_release_receipt_id"])
    _overwrite_committed_record(
        store,
        world["project_id"],
        "multi_agent_agent_release_receipt",
        receipt_key,
        tampered_receipt,
    )

    # Sanity: the tampered receipt resolves cleanly as fully self-consistent on its own.
    assert (
        route_module.resolve_and_verify_committed_release_receipt(
            store, world["project_id"], receipt_key
        )
        is not None
    )

    coordinator = _coordinator(world)
    with pytest.raises(MultiAgentRecordIntegrityError):
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


def test_p19_r9_f2_an_aggregation_input_admitting_an_unresolved_slot_output_is_refused_at_evidence_handoff(
    tmp_path: Any,
) -> None:
    """Structural Review Round 9, P19-R9-F2's own required proof: a self-consistently-
    fingerprinted ``multi_agent_evidence_aggregation_input`` whose own ``admitted_slot_output_
    refs`` falsely admits a slot output the real conflict classification never admitted (here,
    one half of a genuinely CONTRADICTING pair) passed every existing check unnoticed before this
    delivery, since its own narrow plan-keyed identity never covers ``admitted_slot_output_
    refs``. ``resolve_and_verify_canonical_terminal_graph`` now independently rederives the
    aggregation input from the plan's own canonical slot outputs/conflict set/release receipts
    and refuses to trust a committed one that disagrees, before any Evidence/receipt is ever
    written."""

    world = authorized_world(tmp_path, risk_class="HIGH")
    store = world["store"]
    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()
    assert len(opened["plan"]["slots"]) == 2

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
    # Two genuinely CONTRADICTING candidates for the identical capability -- the real
    # classification admits neither.
    assert (
        executed["slot_outputs"][0]["result_fingerprint"]
        != (executed["slot_outputs"][1]["result_fingerprint"])
    )

    plan = route_module.resolve_and_verify_committed_plan(
        store, world["project_id"], str(opened["plan_ref"]["id"])
    )
    genuine_graph = route_module.resolve_and_verify_canonical_terminal_graph(
        store, world["project_id"], plan, opened["plan_ref"]
    )
    genuine_aggregation_input = genuine_graph["aggregation_input"]
    assert genuine_aggregation_input["admitted_slot_output_refs"]["members"] == []

    falsely_admitted_ref = {
        "kind": "multi_agent_slot_output",
        "id": str(executed["slot_outputs"][0]["multi_agent_slot_output_id"]),
    }
    tampered_aggregation_input = dict(genuine_aggregation_input)
    tampered_aggregation_input["admitted_slot_output_refs"] = {
        "collection_kind": "UNORDERED_SET",
        "members": [falsely_admitted_ref],
    }
    tampered_aggregation_input["multi_agent_evidence_aggregation_input_semantic_fingerprint"] = (
        multi_agent_evidence_aggregation_input_semantic_fingerprint(tampered_aggregation_input)
    )
    aggregation_input_key = str(
        genuine_aggregation_input["multi_agent_evidence_aggregation_input_id"]
    )
    _overwrite_committed_record(
        store,
        world["project_id"],
        "multi_agent_evidence_aggregation_input",
        aggregation_input_key,
        tampered_aggregation_input,
    )

    # Sanity: the tampered aggregation input resolves cleanly as fully self-consistent on its
    # own.
    assert (
        route_module.resolve_and_verify_committed_aggregation_input(
            store, world["project_id"], aggregation_input_key
        )
        is not None
    )

    coordinator = _coordinator(world)
    with pytest.raises(MultiAgentRecordIntegrityError):
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

    # Zero Evidence/receipt writes: the rederivation-vs-stored comparison this delivery adds
    # raises before ``route_orchestration_to_evidence`` ever reaches its own commit call.
    assert _record_kind_count(store, world["project_id"], "multi_agent_orchestration_receipt") == 0
    assert _record_kind_count(store, world["project_id"], EVIDENCE_REFERENCE_KIND) == 0


def test_p19_r10_f1_an_envelope_with_the_plans_own_work_unit_but_a_different_genuine_boundary_is_refused(
    tmp_path: Any, monkeypatch: Any
) -> None:
    """Structural Review Round 10, P19-R10-F1's own required proof: Round 9's own
    ``_require_envelope_matches_plan_lineage`` treated ``model_work_unit_ref`` equality alone as
    sufficient transitive proof of Boundary lineage. A genuinely real, self-consistent Envelope
    (its own declared identity and semantic fingerprint both independently recomputed and equal)
    that names the *exact same* Model Work Unit as the resolved Plan, but declares a *different*,
    equally genuine, committed Model Execution Boundary, passes every check Round 4-9 already
    established -- only resolving the canonical Work Unit itself (through Model Runtime's own
    ``resolve_and_verify_committed_work_unit``) and comparing the Envelope's own ``boundary_ref``
    directly against it catches this.
    """

    world = authorized_world(tmp_path, risk_class="LOW")
    store = world["store"]
    project_id = world["project_id"]

    # A second, genuinely distinct, committed Model Execution Boundary in the same project --
    # never used by the Plan's own Work Unit, but equally real and equally self-consistent.
    foreign_boundary_ref, _ = commit_boundary(
        store,
        project_id,
        world["project_binding_id"],
        transaction_id="TX-MODEL-BOUNDARY-0002",
        declared_at="2026-09-11T00:00:01Z",
    )

    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()

    # Crash strictly after the sole slot's own real claim+Envelope commit but before its own
    # terminal slot_output/release_receipt commit -- the identical Round 1/3/9 technique -- so a
    # genuine claim naming a genuine Envelope exists with no terminal pair yet.
    real_derive = route_module.derive_multi_agent_agent_release_receipt

    def _crashing_derive(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("simulated crash before the atomic slot-complete commit")

    monkeypatch.setattr(route_module, "derive_multi_agent_agent_release_receipt", _crashing_derive)
    crashing_adapter = SeededMultiAgentAdapter()
    coordinator = _coordinator(world)
    with pytest.raises(
        RuntimeError, match="simulated crash before the atomic slot-complete commit"
    ):
        execute_dynamic_execution_plan(
            store,
            coordinator,
            project_id=project_id,
            project_binding_id=world["project_binding_id"],
            plan_ref=opened["plan_ref"],
            model_adapter_factory=lambda: crashing_adapter,
            executed_at="2026-09-11T01:30:00Z",
        )
    coordinator.release()
    monkeypatch.setattr(route_module, "derive_multi_agent_agent_release_receipt", real_derive)

    claim_key = compute_slot_attempt_envelope_claim_id(
        project_id=project_id, plan_ref=dict(opened["plan_ref"]), slot_index=0
    )
    real_claim = resolve_and_verify_committed_slot_attempt_envelope_claim(
        store, project_id, claim_key
    )
    assert real_claim is not None
    genuine_envelope = route_module.resolve_and_verify_committed_envelope(
        store, project_id, real_claim["model_execution_envelope_ref"]["id"]
    )
    assert dict(genuine_envelope["boundary_ref"]) == dict(world["boundary_ref"])
    assert dict(genuine_envelope["model_work_unit_ref"]) == dict(
        opened["plan"]["model_work_unit_ref"]
    )

    # A fully self-consistent forged Envelope: every field copied from the genuine one -- same
    # project, same Work Unit, same Difference/Authority/capability/execution snapshot -- except
    # its own ``boundary_ref``, redirected to the second genuine Boundary, with its own identity
    # and semantic fingerprint honestly recomputed from that changed content.
    forged_envelope = dict(genuine_envelope)
    forged_envelope["boundary_ref"] = dict(foreign_boundary_ref)
    forged_envelope["model_execution_envelope_id"] = model_execution_envelope_id(forged_envelope)
    forged_envelope["model_execution_semantic_fingerprint"] = (
        model_execution_envelope_semantic_fingerprint(forged_envelope)
    )
    assert (
        forged_envelope["model_execution_envelope_id"]
        != genuine_envelope["model_execution_envelope_id"]
    )
    commit_records(
        store,
        project_id,
        store.load_current(project_id),
        "TX-FORGED-ENVELOPE-BOUNDARY-0001",
        [
            (
                "model_execution_envelope",
                forged_envelope["model_execution_envelope_id"],
                forged_envelope,
            )
        ],
    )

    # The redirection: the claim now names the forged Envelope -- same Work Unit, wrong Boundary
    # -- self-consistently refingerprinted, at its own unchanged narrow claim key.
    tampered_claim = dict(real_claim)
    tampered_claim["model_execution_envelope_ref"] = {
        "kind": "model_execution_envelope",
        "id": forged_envelope["model_execution_envelope_id"],
    }
    tampered_claim["multi_agent_slot_attempt_envelope_claim_semantic_fingerprint"] = (
        multi_agent_slot_attempt_envelope_claim_semantic_fingerprint(tampered_claim)
    )
    _overwrite_committed_record(
        store,
        project_id,
        "multi_agent_slot_attempt_envelope_claim",
        claim_key,
        tampered_claim,
    )

    # Sanity: both the forged Envelope and the redirected claim resolve cleanly as fully
    # self-consistent on their own.
    assert (
        route_module.resolve_and_verify_committed_envelope(
            store, project_id, forged_envelope["model_execution_envelope_id"]
        )
        is not None
    )
    assert (
        resolve_and_verify_committed_slot_attempt_envelope_claim(store, project_id, claim_key)
        is not None
    )

    state_before = store.load_current(project_id)

    def _unreachable_adapter() -> Any:
        raise AssertionError("no new adapter call is ever permitted for this replay")

    coordinator = _coordinator(world)
    with pytest.raises(MultiAgentRecordIntegrityError):
        execute_dynamic_execution_plan(
            store,
            coordinator,
            project_id=project_id,
            project_binding_id=world["project_binding_id"],
            plan_ref=opened["plan_ref"],
            model_adapter_factory=_unreachable_adapter,
            executed_at="2026-09-11T01:40:00Z",
        )
    coordinator.release()

    state_after = store.load_current(project_id)
    assert state_after["state_revision"] == state_before["state_revision"]
    slot_output_key = compute_slot_output_id(
        project_id=project_id, plan_ref=dict(opened["plan_ref"]), slot_index=0
    )
    assert store.resolve_record(project_id, "multi_agent_slot_output", slot_output_key) is None


def test_p19_r10_f2_a_slot_output_and_release_receipt_sharing_the_same_wrong_attempt_id_is_refused(
    tmp_path: Any,
) -> None:
    """Structural Review Round 10, P19-R10-F2's own required proof: Round 9's own
    ``_require_release_receipt_matches_slot_output`` verified only that a release receipt's own
    ``attempt_id`` equals its slot output's own ``attempt_id`` -- never that either actually
    equals the deterministic attempt identity the verified Plan/slot themselves imply. A slot
    output and its release receipt that both declare the identical, validly-formatted, but wrong
    ``attempt_id`` -- each self-consistently refingerprinted at its own correct narrow key --
    would pass every check Round 9 already established. Both replay and Evidence hand-off must
    refuse."""

    world = authorized_world(tmp_path, risk_class="LOW")
    store = world["store"]
    project_id = world["project_id"]
    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(store, coordinator, **open_plan_kwargs(world))
    coordinator.release()

    coordinator = _coordinator(world)
    executed = execute_dynamic_execution_plan(
        store,
        coordinator,
        project_id=project_id,
        project_binding_id=world["project_binding_id"],
        plan_ref=opened["plan_ref"],
        model_adapter_factory=lambda: SeededMultiAgentAdapter(),
        executed_at="2026-09-11T01:30:00Z",
    )
    coordinator.release()
    genuine_slot_output = executed["slot_outputs"][0]
    genuine_receipt = executed["release_receipts"][0]

    wrong_attempt_id = compute_attempt_id(
        project_id=project_id, plan_ref=dict(opened["plan_ref"]), slot_index=99
    )
    assert wrong_attempt_id != genuine_slot_output["attempt_id"]

    tampered_slot_output = dict(genuine_slot_output)
    tampered_slot_output["attempt_id"] = wrong_attempt_id
    tampered_slot_output["multi_agent_slot_output_semantic_fingerprint"] = (
        multi_agent_slot_output_semantic_fingerprint(tampered_slot_output)
    )
    slot_output_key = str(genuine_slot_output["multi_agent_slot_output_id"])
    _overwrite_committed_record(
        store, project_id, "multi_agent_slot_output", slot_output_key, tampered_slot_output
    )

    tampered_receipt = dict(genuine_receipt)
    tampered_receipt["attempt_id"] = wrong_attempt_id
    tampered_receipt["multi_agent_agent_release_receipt_semantic_fingerprint"] = (
        multi_agent_agent_release_receipt_semantic_fingerprint(tampered_receipt)
    )
    receipt_key = str(genuine_receipt["multi_agent_agent_release_receipt_id"])
    _overwrite_committed_record(
        store, project_id, "multi_agent_agent_release_receipt", receipt_key, tampered_receipt
    )

    # Sanity: both tampered records resolve cleanly as fully self-consistent on their own, and
    # agree with each other -- exactly the case the receipt-to-slot-output comparison alone
    # cannot catch.
    assert (
        route_module.resolve_and_verify_committed_slot_output(store, project_id, slot_output_key)
        is not None
    )
    assert (
        route_module.resolve_and_verify_committed_release_receipt(store, project_id, receipt_key)
        is not None
    )

    def _unreachable_adapter() -> Any:
        raise AssertionError("no new adapter call is ever permitted for this replay")

    coordinator = _coordinator(world)
    with pytest.raises(MultiAgentRecordIntegrityError):
        execute_dynamic_execution_plan(
            store,
            coordinator,
            project_id=project_id,
            project_binding_id=world["project_binding_id"],
            plan_ref=opened["plan_ref"],
            model_adapter_factory=_unreachable_adapter,
            executed_at="2026-09-11T01:40:00Z",
        )
    coordinator.release()

    coordinator = _coordinator(world)
    with pytest.raises(MultiAgentRecordIntegrityError):
        route_orchestration_to_evidence(
            store,
            coordinator,
            project_id=project_id,
            project_binding_id=world["project_binding_id"],
            plan_ref=opened["plan_ref"],
            evidence_request_template=evidence_request_for(project_id, provenance=None),
            completed_at="2026-09-11T01:41:00Z",
        )
    coordinator.release()


def _record_kind_count(store: FileStateStore, project_id: str, kind: str) -> int:
    directory = store.root / "projects" / project_id / "records" / kind
    if not directory.exists():
        return 0
    return len(list(directory.glob("*.json")))
