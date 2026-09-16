"""Phase 20 -- repeated Agent/runtime-identity swap proof (Issue #86 section 7).

Reuses the already-accepted V3 model-swap vertical proof machinery
(``tests/integration/model_runtime/test_model_swap_vertical_proof.py``,
``tests/fixtures/model_runtime_world.py``) exactly as it stands, rather than inventing a second
"Agent identity" concept. Per the inventory this Issue's own design was built from: there is no
canonical ``AgentIdentity`` record anywhere in this Kernel -- a Temporary Agent's only
distinguishing fact is which real ``BootContext`` it independently re-verified, and the one
real, fail-closed "prove these are genuinely two different identities" mechanism in this
repository is Model Runtime's own ``adapter_identity`` field plus
:func:`~manosube_agent_civilization.model_runtime.record_model_swap`'s independent Store
re-resolution and same-identity refusal. This module drives that real mechanism through >=3
swaps across >=2 genuinely distinct ``adapter_identity`` values, chained through the identical
session-loss discipline the V3 proof already establishes (each swap discards the predecessor
Agent's own handle for real -- ``AgentReleasedError`` on reuse -- before the successor Agent is
constructed from nothing but the Store and the Work Unit's own content address).
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.fixtures.model_runtime_world import (
    commit_boundary,
    commit_difference,
    commit_grant,
    open_kwargs,
)

from manosube_agent_civilization.agent_runtime import start_temporary_agent
from manosube_agent_civilization.agent_runtime.errors import AgentReleasedError
from manosube_agent_civilization.model_runtime import (
    FakeModelAdapter,
    execute_model_work_unit,
    open_model_work_unit,
    record_model_swap,
    recover_model_execution_session,
)
from manosube_agent_civilization.store import FileStateStore

ENVELOPE_KIND = "model_execution_envelope"
WORK_UNIT_KIND = "model_work_unit"

#: >=2 genuinely distinct adapter identities, driven across >=3 swaps below (A -> B -> A),
#: satisfying both ``AGENT_SWAP_COUNT_MINIMUM=3`` and
#: ``DISTINCT_AGENT_OR_RUNTIME_IDENTITIES_MINIMUM=2`` from the same real mechanism.
ADAPTER_IDENTITY_A: dict[str, Any] = {"adapter": "long_running_proof_adapter_a", "version": "0.1"}
ADAPTER_IDENTITY_B: dict[str, Any] = {"adapter": "long_running_proof_adapter_b", "version": "0.1"}
SWAP_ADAPTER_IDENTITIES = [
    ADAPTER_IDENTITY_A,
    ADAPTER_IDENTITY_B,
    ADAPTER_IDENTITY_A,
    ADAPTER_IDENTITY_B,
]


def build_agent_swap_world(
    store: FileStateStore,
    *,
    project_id: str,
    project_binding_id: str,
    human_authority_ref: dict[str, Any],
    transaction_prefix: str,
) -> dict[str, Any]:
    """One real, committed Difference/Boundary/Grant bound into *store*'s own already-real
    Project Binding (P87-R1-F4) -- the identical (Difference, Boundary, Grant) shape the V3
    proof's own ``authorized_world`` builds, but committed into the long-running cycle
    sequence's own Store/Project/Binding rather than a second, unrelated fixture world, so the
    Agent-swap slice's own Work Unit shares the exact ``project_binding_id`` and lineage every
    cycle Difference/Reflow commit also advances."""

    difference_ref, difference = commit_difference(
        store, project_id, transaction_id=f"{transaction_prefix}-DIFF"
    )
    boundary_ref, boundary = commit_boundary(
        store,
        project_id,
        project_binding_id,
        transaction_id=f"{transaction_prefix}-BOUND",
        declared_by=dict(human_authority_ref),
    )
    grant_ref, grant = commit_grant(
        store,
        project_id,
        difference_ref,
        boundary_ref,
        transaction_id=f"{transaction_prefix}-GRANT",
        granted_by=dict(human_authority_ref),
    )
    return {
        "store": store,
        "project_id": project_id,
        "project_binding_id": project_binding_id,
        "difference_ref": difference_ref,
        "difference": difference,
        "boundary_ref": boundary_ref,
        "boundary": boundary,
        "grant_ref": grant_ref,
        "grant": grant,
    }


def _discard_session(agent: Any) -> None:
    agent.release()
    with pytest.raises(AgentReleasedError):
        _ = agent.boot_context


def run_agent_swap_sequence(world: dict[str, Any]) -> dict[str, Any]:
    """Open one real Model Work Unit under Agent 0 / Adapter A, then repeatedly discard the
    session and resume through the next real, independently constructed Agent + a genuinely
    different Adapter identity, minting one real ``model_swap_receipt`` per transition.
    Returns every swap receipt plus the identities/state-revisions each one recorded, for the
    caller's own metric dataset and negative-control assertions."""

    store = world["store"]
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]

    agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=project_binding_id
    )
    opened = open_model_work_unit(store, agent, **open_kwargs(world))
    work_unit_ref = {"kind": WORK_UNIT_KIND, "id": opened["model_work_unit"]["model_work_unit_id"]}

    adapter = FakeModelAdapter(adapter_identity=SWAP_ADAPTER_IDENTITIES[0])
    adapter.seed_candidate(
        model_work_unit_ref=opened["model_work_unit_ref"],
        candidate_fields={"summary": "long_running_proof agent swap seed", "observed_status": "ok"},
    )
    executed = execute_model_work_unit(
        store,
        agent,
        project_id=project_id,
        project_binding_id=project_binding_id,
        model_work_unit_ref=opened["model_work_unit_ref"],
        adapter=adapter,
        executed_at="2026-09-15T13:00:00Z",
    )
    predecessor_envelope_id = executed["envelope"]["model_execution_envelope_id"]
    _discard_session(agent)

    receipts: list[dict[str, Any]] = []
    for i, adapter_identity in enumerate(SWAP_ADAPTER_IDENTITIES[1:], start=1):
        agent = start_temporary_agent(
            store, project_id=project_id, project_binding_id=project_binding_id
        )
        recovered = recover_model_execution_session(
            store,
            agent,
            project_id=project_id,
            project_binding_id=project_binding_id,
            model_work_unit_ref=work_unit_ref,
            recovered_at=f"2026-09-15T13:{i:02d}:00Z",
        )
        assert recovered["model_work_unit"]["model_work_unit_id"] == work_unit_ref["id"]

        adapter = FakeModelAdapter(adapter_identity=adapter_identity)
        adapter.seed_candidate(
            model_work_unit_ref=work_unit_ref,
            candidate_fields={"summary": f"long_running_proof swap {i}", "observed_status": "ok"},
        )
        executed = execute_model_work_unit(
            store,
            agent,
            project_id=project_id,
            project_binding_id=project_binding_id,
            model_work_unit_ref=work_unit_ref,
            adapter=adapter,
            executed_at=f"2026-09-15T13:{i:02d}:30Z",
        )
        successor_envelope_id = executed["envelope"]["model_execution_envelope_id"]

        swap = record_model_swap(
            store,
            agent,
            project_id=project_id,
            project_binding_id=project_binding_id,
            model_work_unit_ref=work_unit_ref,
            predecessor_execution_ref={"kind": ENVELOPE_KIND, "id": predecessor_envelope_id},
            successor_execution_ref={"kind": ENVELOPE_KIND, "id": successor_envelope_id},
            recorded_at=f"2026-09-15T13:{i:02d}:45Z",
        )
        receipt = swap["model_swap_receipt"]
        assert receipt["predecessor_adapter_identity"] != receipt["successor_adapter_identity"]
        receipts.append(receipt)

        _discard_session(agent)
        predecessor_envelope_id = successor_envelope_id

    distinct_identities = {
        tuple(sorted(r["predecessor_adapter_identity"].items())) for r in receipts
    } | {tuple(sorted(r["successor_adapter_identity"].items())) for r in receipts}

    return {
        "work_unit_ref": work_unit_ref,
        "swap_receipts": receipts,
        "swap_count": len(receipts),
        "distinct_identity_count": len(distinct_identities),
    }
