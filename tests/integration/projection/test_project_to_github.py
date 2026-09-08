"""Phase 14 (Issue #62): the one public Projection route (``project_to_github``), end-to-end,
over a real ``FileStateStore`` -- V2 (controlled Adapter contract proof) and V4 (failure/tamper
proof).

A real bound Project (Phase 9 Binding), with one real, Store-committed ``observation_evidence``
record derived through the existing Evidence owner's own ``derive_evidence`` (never a bare,
schema-invalid fixture dict), the real Human Authority reference Boot independently re-verifies
for it, and a controlled :class:`~manosube_agent_civilization.projection.github_adapter.
FakeGitHubAdapter` -- proves the canonical successful route (create then reuse), the required
rejection proofs (authority mismatch, unresolvable subject, conflicting payload, adapter
failure at each of materialize/observe, a tampered/missing external artifact on replay), and
the receipt hand-off into the existing Evidence owner's own Change-Free Verification Evidence
position.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.evidence_helpers import (
    change_free_verification_evidence_request,
    observation_evidence_request,
)
from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.projection import (
    ConflictingProjectionPayloadError,
    FakeGitHubAdapter,
    ProjectionAdapterError,
    ProjectionRequirementError,
    project_to_github,
    route_observation_receipt_to_evidence,
)
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

_TARGET_REPOSITORY = {"host": "github", "owner": "acme", "repo": "widget"}
_PAYLOAD = {"title": "Evidence artifact", "body": "hello"}


def _bound(tmp_path: Path) -> tuple[FileStateStore, dict[str, Any]]:
    store_root = tmp_path / "backend"
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store, {
        "project_id": kwargs["project_id"],
        "project_binding_id": result["project_binding_id"],
        "genesis_state": result["committed_state"],
    }


def _commit_observation_evidence(
    store: FileStateStore, project_id: str, genesis_state: dict[str, Any], transaction_id: str
) -> str:
    evidence = derive_evidence(observation_evidence_request())
    evidence_id = evidence["evidence_id"]
    successor = dict(genesis_state)
    successor["state_revision"] = genesis_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = genesis_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": transaction_id,
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": genesis_state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": genesis_state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": "2026-09-08T00:00:00Z",
    }
    store.commit(
        project_id,
        genesis_state["state_revision"],
        genesis_state["semantic_fingerprint"],
        successor,
        event,
        records=[("observation_evidence", evidence_id, evidence)],
    )
    return evidence_id


@pytest.fixture
def _world(tmp_path: Path) -> dict[str, Any]:
    store, ctx = _bound(tmp_path)
    evidence_id = _commit_observation_evidence(
        store, ctx["project_id"], ctx["genesis_state"], "TX-PROJECTION-TEST-0001"
    )
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "evidence_id": evidence_id,
        "human_authority_ref": dict(boot_context.human_authority_ref),
    }


def _project(world: dict[str, Any], adapter: Any, **overrides: Any) -> dict[str, Any]:
    kwargs = {
        "store": world["store"],
        "project_id": world["project_id"],
        "project_binding_id": world["project_binding_id"],
        "subject_ref": {"kind": "observation_evidence", "id": world["evidence_id"]},
        "projection_kind": "EVIDENCE_ARTIFACT",
        "target_repository": _TARGET_REPOSITORY,
        "projection_payload": _PAYLOAD,
        "github_authority_ref": world["human_authority_ref"],
        "materialized_at": "2026-09-08T00:00:01Z",
        "adapter": adapter,
    }
    kwargs.update(overrides)
    return project_to_github(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Canonical successful route (create, then reuse)
# ---------------------------------------------------------------------------


def test_first_call_materializes_and_commits_a_new_envelope(_world: dict[str, Any]) -> None:
    adapter = FakeGitHubAdapter()
    outcome = _project(_world, adapter)
    assert outcome["reused"] is False
    assert adapter.materialize_call_count == 1
    assert adapter.observe_call_count == 1
    assert outcome["envelope"]["projection_envelope_id"].startswith("PROJECTION-")
    assert outcome["receipt"].status == "VERIFIED"

    resolved = _world["store"].resolve_record(
        _world["project_id"], "projection_envelope", outcome["envelope"]["projection_envelope_id"]
    )
    assert resolved == outcome["envelope"]


def test_replay_with_identical_payload_reuses_and_never_remateralizes(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    first = _project(_world, adapter)
    second = _project(_world, adapter, materialized_at="2026-09-08T00:00:02Z")
    assert second["reused"] is True
    assert adapter.materialize_call_count == 1
    assert adapter.observe_call_count == 2
    assert second["envelope"] == first["envelope"]


def test_conflicting_payload_at_the_identical_identity_refuses_with_zero_writes(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    first = _project(_world, adapter)
    envelope_id = first["envelope"]["projection_envelope_id"]
    before = _world["store"].resolve_record(
        _world["project_id"], "projection_envelope", envelope_id
    )

    with pytest.raises(ConflictingProjectionPayloadError):
        _project(_world, adapter, projection_payload={"title": "DIFFERENT", "body": "hello"})

    assert adapter.materialize_call_count == 1
    after = _world["store"].resolve_record(_world["project_id"], "projection_envelope", envelope_id)
    assert after == before


# ---------------------------------------------------------------------------
# Authority admission
# ---------------------------------------------------------------------------


def test_github_authority_ref_not_matching_the_real_human_authority_ref_refuses(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    with pytest.raises(ProjectionRequirementError):
        _project(
            _world, adapter, github_authority_ref={"kind": "human_authority", "id": "FABRICATED"}
        )
    assert adapter.materialize_call_count == 0


# ---------------------------------------------------------------------------
# Subject admission
# ---------------------------------------------------------------------------


def test_unresolvable_subject_ref_refuses_before_any_adapter_call(_world: dict[str, Any]) -> None:
    adapter = FakeGitHubAdapter()
    with pytest.raises(ProjectionRequirementError):
        _project(
            _world, adapter, subject_ref={"kind": "observation_evidence", "id": "EVIDENCE-NOPE"}
        )
    assert adapter.materialize_call_count == 0


def test_projection_kind_subject_kind_mismatch_refuses(_world: dict[str, Any]) -> None:
    adapter = FakeGitHubAdapter()
    with pytest.raises(ProjectionRequirementError):
        _project(_world, adapter, projection_kind="DIFFERENCE_ISSUE")
    assert adapter.materialize_call_count == 0


def test_difference_subject_requires_a_caller_supplied_subject_fingerprint(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    with pytest.raises(ProjectionRequirementError):
        _project(
            _world,
            adapter,
            subject_ref={"kind": "difference", "id": "D-DOESNOTMATTER"},
            projection_kind="DIFFERENCE_ISSUE",
        )
    assert adapter.materialize_call_count == 0


# ---------------------------------------------------------------------------
# V4: adapter/Store failure and tamper proofs
# ---------------------------------------------------------------------------


def test_adapter_materialize_failure_propagates_with_zero_commit(_world: dict[str, Any]) -> None:
    from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
    from manosube_agent_civilization.projection.identity import projection_mapping_key

    adapter = FakeGitHubAdapter(fail_materialize=ProjectionAdapterError("simulated outage"))
    with pytest.raises(ProjectionAdapterError):
        _project(_world, adapter)
    assert adapter.materialize_call_count == 1  # attempted, but its result was never committed

    resolved_subject = _world["store"].resolve_record(
        _world["project_id"], "observation_evidence", _world["evidence_id"]
    )
    mapping_key = projection_mapping_key(
        {"kind": "observation_evidence", "id": _world["evidence_id"]},
        evidence_semantic_fingerprint(resolved_subject),
        "EVIDENCE_ARTIFACT",
        _TARGET_REPOSITORY,
    )
    assert (
        _world["store"].resolve_record(_world["project_id"], "projection_envelope", mapping_key)
        is None
    )


def test_adapter_observe_failure_on_first_materialization_propagates(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter(fail_observe=ProjectionAdapterError("simulated rate limit"))
    with pytest.raises(ProjectionAdapterError):
        _project(_world, adapter)
    # The Envelope was already committed (materialize succeeded); only the receipt failed.
    assert adapter.materialize_call_count == 1


def test_missing_external_artifact_on_replay_yields_a_negative_receipt_not_a_recreation(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    first = _project(_world, adapter)
    adapter.delete(external_artifact_ref=first["envelope"]["external_artifact_ref"])
    second = _project(_world, adapter, materialized_at="2026-09-08T00:00:03Z")
    assert second["reused"] is True
    assert adapter.materialize_call_count == 1  # never recreated
    assert second["receipt"].status == "FAILED"
    assert second["receipt"].observations["exists"] is False


def test_tampered_external_artifact_on_replay_yields_a_mismatched_receipt(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    first = _project(_world, adapter)
    original_fingerprint = first["receipt"].observations["observed_content_fingerprint"]
    adapter.tamper(
        external_artifact_ref=first["envelope"]["external_artifact_ref"],
        new_payload={"title": "TAMPERED", "body": "TAMPERED"},
    )
    second = _project(_world, adapter, materialized_at="2026-09-08T00:00:04Z")
    assert second["reused"] is True
    assert adapter.materialize_call_count == 1  # never recreated/repaired
    assert second["receipt"].observations["observed_content_fingerprint"] != original_fingerprint


def test_adapter_without_a_readable_identity_refuses_before_materialize(
    _world: dict[str, Any],
) -> None:
    class _NoIdentityAdapter:
        def materialize(self, **kwargs: Any) -> Any:  # pragma: no cover - must never be called
            raise AssertionError("materialize must not be called")

        def observe(self, **kwargs: Any) -> Any:  # pragma: no cover - must never be called
            raise AssertionError("observe must not be called")

    with pytest.raises(ProjectionAdapterError):
        _project(_world, _NoIdentityAdapter())


# ---------------------------------------------------------------------------
# Receipt -> Evidence hand-off
# ---------------------------------------------------------------------------


def test_receipt_routes_to_a_real_change_free_verification_evidence_record(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    outcome = _project(_world, adapter)
    request = change_free_verification_evidence_request(provenance=None)
    evidence = route_observation_receipt_to_evidence(
        outcome["receipt"], request["difference_request"]["project_id"], request
    )
    assert evidence["evidence_position"] == "CHANGE_FREE_VERIFICATION_EVIDENCE"
    assert evidence["verification_result_provenance"]["status"] == "VERIFIED"
    assert (
        evidence["verification_result_provenance"]["requirement_id"]
        == outcome["envelope"]["projection_envelope_id"]
    )
