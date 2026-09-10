"""V5 (Issue #69): Phase 16 Model Runtime continuity proof.

Proves, in the same real ``FileStateStore`` and the same real project, that a genuine Phase 16
Model Runtime execution and a genuine Phase 17 URL Source Observation coexist without either
disturbing the other -- and that URL-fetched content itself has no shipped path to mint
Authority, invoke a model, execute a Change, or bypass Evidence (P17-C4).

The static half of this proof -- no module in ``url_boot`` imports ``authority``, ``change``, or
``model_runtime`` at all -- lives in ``tests/contract/url_boot/test_url_boot_static_conformance.py``
(``test_no_module_imports_a_forbidden_existing_owner``). This file proves the behavioral half:
running both through the identical Store genuinely leaves each one's own records, and the other
element's own State-tree pointers, completely untouched by the other.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.model_runtime_world import authorized_world, open_kwargs
from tests.fixtures.url_boot_world import boundary_for

from manosube_agent_civilization.agent_runtime import start_temporary_agent
from manosube_agent_civilization.model_runtime import (
    FakeModelAdapter,
    execute_model_work_unit,
    open_model_work_unit,
)
from manosube_agent_civilization.url_boot.adapter import FakeUrlSourceAdapter
from manosube_agent_civilization.url_boot.network import canonical_source_identity
from manosube_agent_civilization.url_boot.route import observe_url_source

_ENVELOPE_RECORD_KIND = "url_source_observation_envelope"


@pytest.fixture
def _world(tmp_path: Path) -> dict[str, Any]:
    return authorized_world(tmp_path)


def test_a_model_execution_and_a_url_observation_coexist_without_interference(
    _world: dict[str, Any],
) -> None:
    store = _world["store"]
    project_id = _world["project_id"]
    project_binding_id = _world["project_binding_id"]

    # ---- Phase 16: a genuine Model Runtime execution, completely ordinary ----------------
    agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=project_binding_id
    )
    opened = open_model_work_unit(store, agent, **open_kwargs(_world))
    model_adapter = FakeModelAdapter()
    model_adapter.seed_candidate(
        model_work_unit_ref=opened["model_work_unit_ref"],
        candidate_fields={"summary": "model observed", "observed_status": "ok"},
    )
    model_result = execute_model_work_unit(
        store,
        agent,
        project_id=project_id,
        project_binding_id=project_binding_id,
        model_work_unit_ref=opened["model_work_unit_ref"],
        adapter=model_adapter,
        executed_at="2026-09-09T02:00:00Z",
    )
    model_envelope_id = model_result["envelope"]["model_execution_envelope_id"]
    state_after_model = store.load_current(project_id)

    # ---- Phase 17: a genuine URL Source Observation, in the identical project ------------
    source_identity = canonical_source_identity("http://127.0.0.1:1/status")
    boundary = boundary_for(
        admitted_hosts=["127.0.0.1"],
        admitted_ports=[1],
        issued_at="2026-09-09T02:00:00Z",
        expires_at="2026-09-09T02:05:00Z",
    )
    url_adapter = FakeUrlSourceAdapter()
    url_adapter.seed_source(source_identity=source_identity, fields={"status": "ok"})
    url_result = observe_url_source(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        source_identity=source_identity,
        boundary=boundary,
        adapter=url_adapter,
        observed_at="2026-09-09T02:00:01Z",
    )
    url_envelope_id = url_result["envelope"]["url_source_observation_envelope_id"]

    # ---- Neither commit disturbed the other's own records ---------------------------------
    resolved_model_envelope = store.resolve_record(
        project_id, "model_execution_envelope", model_envelope_id
    )
    assert resolved_model_envelope == model_result["envelope"]
    resolved_url_envelope = store.resolve_record(project_id, _ENVELOPE_RECORD_KIND, url_envelope_id)
    assert resolved_url_envelope == url_result["envelope"]

    # ---- The URL observation touched no Model Runtime State-tree pointer at all -----------
    state_after_url = store.load_current(project_id)
    model_runtime_tree_before = state_after_model.get("semantic_state", {}).get("model_runtime")
    model_runtime_tree_after = state_after_url.get("semantic_state", {}).get("model_runtime")
    assert model_runtime_tree_after == model_runtime_tree_before

    # ---- State advanced monotonically across both, real lineage, no collision -------------
    assert state_after_url["state_revision"] > state_after_model["state_revision"]
    assert (
        state_after_url["previous_state_fingerprint"] == state_after_model["semantic_fingerprint"]
    )
