"""Phase 14 (Issue #62), Structural Review Round 2 (P14-R2-F2): the atomic recoverable
projection claim/attempt state machine, over a real ``FileStateStore``.

Deliberately a separate, self-contained fixture world from ``test_project_to_github.py``'s
own -- it exercises the same public ``project_to_github`` route, but its own purpose (proving
the concurrency barrier and the crash-recovery matrix) needs direct control over the
``projection_intent``/``projection_materialize_attempt`` Store records themselves, which the
other suite's own fixtures have no reason to expose.

Covers the required recovery matrix (``PROJECTION_CONTRACT.md`` §10, F2): before any write;
during the intent claim (a genuinely concurrent, differently-timed caller); after the intent
claim but before materialize (a crashed materialize call, safe to retry); after a materialize
call that never registered anything discoverable (the genuinely ambiguous reconciliation
state); a materialize call whose external result *is* discoverable on retry (external success,
response lost); and a genuine same-caller process retry (identical ``materialized_at``).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from tests.evidence_helpers import observation_evidence_request
from tests.fixtures.product_binding import (
    bind_project_kwargs,
    genesis_records,
    sign_github_projection_grant_declaration,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.identity import github_projection_grant_id
from manosube_agent_civilization.binding import bind_project, declare_github_projection_grant
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
from manosube_agent_civilization.projection import (
    FakeGitHubAdapter,
    ProjectionAdapterError,
    ProjectionConcurrentClaimError,
    ProjectionReconciliationRequiredError,
    project_to_github,
)
from manosube_agent_civilization.projection.identity import (
    projection_mapping_key,
    projection_payload_fingerprint,
)
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

_TARGET_REPOSITORY = {"host": "github", "owner": "acme", "repo": "atomic-claims"}
_PAYLOAD = {
    "name": "MANOSUBE Evidence Check",
    "head_sha": "b" * 40,
    "status": "completed",
    "conclusion": "neutral",
    "output": {"title": "Evidence artifact", "summary": "hello"},
}
_PERMITTED_ACTION = "MATERIALIZE_PROJECTION"
_INTENT_KIND = "projection_intent"
_ATTEMPT_KIND = "projection_materialize_attempt"


def _commit_records(
    store: FileStateStore,
    project_id: str,
    current_state: dict[str, Any],
    transaction_id: str,
    records: list[tuple[str, str, Mapping[str, Any]]],
    committed_at: str = "2026-09-08T00:00:00Z",
) -> dict[str, Any]:
    successor = dict(current_state)
    successor["state_revision"] = current_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": transaction_id,
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": current_state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": current_state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": committed_at,
    }
    store.commit(
        project_id,
        current_state["state_revision"],
        current_state["semantic_fingerprint"],
        successor,
        event,
        records=records,
    )
    return successor


@pytest.fixture
def _world(tmp_path: Path) -> dict[str, Any]:
    store_root = tmp_path / "backend"
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    project_id = kwargs["project_id"]
    project_binding_id = result["project_binding_id"]
    genesis_state = result["committed_state"]

    evidence = derive_evidence(observation_evidence_request())
    evidence_id = evidence["evidence_id"]
    current_state = _commit_records(
        store,
        project_id,
        genesis_state,
        "TX-ATOMIC-TEST-0001",
        [("observation_evidence", evidence_id, evidence)],
    )
    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    human_authority_ref = dict(boot_context.human_authority_ref)
    evidence_subject_ref = {"kind": "observation_evidence", "id": evidence_id}
    evidence_fingerprint = evidence_semantic_fingerprint(evidence)
    payload_fingerprint = projection_payload_fingerprint(dict(_PAYLOAD))
    mapping_key = projection_mapping_key(
        evidence_subject_ref, evidence_fingerprint, "EVIDENCE_ARTIFACT", _TARGET_REPOSITORY
    )

    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": dict(evidence_subject_ref),
        "subject_fingerprint": evidence_fingerprint,
        "projection_kind": "EVIDENCE_ARTIFACT",
        "target_repository": dict(_TARGET_REPOSITORY),
        "payload_fingerprint": payload_fingerprint,
        "permitted_action": _PERMITTED_ACTION,
        "status": "ACTIVE",
        "granted_by": dict(human_authority_ref),
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    current_state = _commit_records(
        store,
        project_id,
        current_state,
        "TX-ATOMIC-TEST-0002",
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    grant_ref = {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}
    declaration_result = declare_github_projection_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        status="ACTIVE",
        declared_at="2026-09-08T00:00:00Z",
        signature=sign_github_projection_grant_declaration(
            project_id=project_id,
            project_binding_id=project_binding_id,
            grant_ref=grant_ref,
            declared_by=human_authority_ref,
            subject_ref=evidence_subject_ref,
            subject_fingerprint=evidence_fingerprint,
            projection_kind="EVIDENCE_ARTIFACT",
            target_repository=_TARGET_REPOSITORY,
            payload_fingerprint=payload_fingerprint,
            permitted_action=_PERMITTED_ACTION,
            status="ACTIVE",
            declared_at="2026-09-08T00:00:00Z",
        ),
        schema_root=SCHEMA_ROOT,
    )
    declaration = declaration_result["github_projection_grant_declaration"]
    declaration_ref = {
        "kind": "github_projection_grant_declaration",
        "id": declaration["github_projection_grant_declaration_id"],
    }

    return {
        "store": store,
        "project_id": project_id,
        "project_binding_id": project_binding_id,
        "evidence_id": evidence_id,
        "evidence_subject_ref": evidence_subject_ref,
        "evidence_fingerprint": evidence_fingerprint,
        "human_authority_ref": human_authority_ref,
        "grant_ref": grant_ref,
        "declaration_ref": declaration_ref,
        "mapping_key": mapping_key,
        "_next_tx": 3,
    }


def _project(world: dict[str, Any], adapter: Any, **overrides: Any) -> dict[str, Any]:
    kwargs = {
        "store": world["store"],
        "project_id": world["project_id"],
        "project_binding_id": world["project_binding_id"],
        "subject_ref": world["evidence_subject_ref"],
        "projection_kind": "EVIDENCE_ARTIFACT",
        "target_repository": _TARGET_REPOSITORY,
        "projection_payload": _PAYLOAD,
        "github_authority_ref": world["human_authority_ref"],
        "materialized_at": "2026-09-08T00:00:01Z",
        "adapter": adapter,
        "github_projection_grant_refs": [world["grant_ref"]],
        "github_projection_grant_declaration_refs": [world["declaration_ref"]],
    }
    kwargs.update(overrides)
    return project_to_github(**kwargs)


def _commit_competing_intent(world: dict[str, Any], materialized_at: str) -> None:
    """Directly commit a ``projection_intent`` at *world*'s own mapping key, with a
    *different* ``materialized_at`` than any call under test will use -- simulating a
    genuinely distinct, already-durable competing attempt (Structural Review Round 2,
    P14-R2-F2's own concurrency-barrier stage)."""

    from manosube_agent_civilization.projection.engine import derive_projection_intent

    store = world["store"]
    project_id = world["project_id"]
    intent = derive_projection_intent(
        subject_ref=world["evidence_subject_ref"],
        subject_fingerprint=world["evidence_fingerprint"],
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        project_id=project_id,
        materialized_at=materialized_at,
    )
    current_state = store.load_current(project_id)
    _commit_records(
        store,
        project_id,
        current_state,
        f"TX-COMPETING-INTENT-{world['mapping_key']}",
        [(_INTENT_KIND, world["mapping_key"], intent)],
    )


def _commit_intent_and_attempt(world: dict[str, Any], materialized_at: str) -> None:
    """Directly commit both durable claim records at *world*'s own mapping key, for the
    *same* ``materialized_at`` a subsequent call under test will use -- simulating a prior
    attempt that reserved the slot and recorded it was about to call ``materialize``, then
    crashed (or genuinely failed) before anything discoverable existed."""

    from manosube_agent_civilization.projection.engine import (
        derive_projection_intent,
        derive_projection_materialize_attempt,
    )

    store = world["store"]
    project_id = world["project_id"]
    intent = derive_projection_intent(
        subject_ref=world["evidence_subject_ref"],
        subject_fingerprint=world["evidence_fingerprint"],
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        project_id=project_id,
        materialized_at=materialized_at,
    )
    current_state = store.load_current(project_id)
    current_state = _commit_records(
        store,
        project_id,
        current_state,
        f"TX-PRIOR-INTENT-{world['mapping_key']}",
        [(_INTENT_KIND, world["mapping_key"], intent)],
    )
    attempt = derive_projection_materialize_attempt(
        subject_ref=world["evidence_subject_ref"],
        subject_fingerprint=world["evidence_fingerprint"],
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        project_id=project_id,
        materialized_at=materialized_at,
    )
    _commit_records(
        store,
        project_id,
        current_state,
        f"TX-PRIOR-ATTEMPT-{world['mapping_key']}",
        [(_ATTEMPT_KIND, world["mapping_key"], attempt)],
    )


# ---------------------------------------------------------------------------
# Stage: before any write -- the ordinary first-ever attempt at this slot
# ---------------------------------------------------------------------------


def test_first_ever_attempt_claims_and_materializes_normally(_world: dict[str, Any]) -> None:
    store = _world["store"]
    assert store.resolve_record(_world["project_id"], _INTENT_KIND, _world["mapping_key"]) is None
    adapter = FakeGitHubAdapter()
    outcome = _project(_world, adapter)
    assert outcome["reused"] is False
    assert adapter.materialize_call_count == 1
    intent = store.resolve_record(_world["project_id"], _INTENT_KIND, _world["mapping_key"])
    attempt = store.resolve_record(_world["project_id"], _ATTEMPT_KIND, _world["mapping_key"])
    assert intent is not None and intent["materialized_at"] == "2026-09-08T00:00:01Z"
    assert attempt is not None and attempt["materialized_at"] == "2026-09-08T00:00:01Z"


# ---------------------------------------------------------------------------
# Stage: a genuinely concurrent/differently-timed competing attempt
# ---------------------------------------------------------------------------


def test_competing_intent_refuses_before_any_adapter_call(_world: dict[str, Any]) -> None:
    _commit_competing_intent(_world, materialized_at="2026-09-08T09:00:00Z")
    adapter = FakeGitHubAdapter()
    with pytest.raises(ProjectionConcurrentClaimError):
        _project(_world, adapter, materialized_at="2026-09-08T00:00:01Z")
    assert adapter.materialize_call_count == 0
    assert adapter.find_by_correlation_key_call_count == 0


# ---------------------------------------------------------------------------
# Stage: after the intent claim, before materialize -- safe to proceed
# ---------------------------------------------------------------------------


def test_identical_retry_after_intent_alone_proceeds_to_materialize(
    _world: dict[str, Any],
) -> None:
    from manosube_agent_civilization.projection.engine import derive_projection_intent

    store = _world["store"]
    project_id = _world["project_id"]
    materialized_at = "2026-09-08T00:00:01Z"
    intent = derive_projection_intent(
        subject_ref=_world["evidence_subject_ref"],
        subject_fingerprint=_world["evidence_fingerprint"],
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        project_id=project_id,
        materialized_at=materialized_at,
    )
    current_state = store.load_current(project_id)
    _commit_records(
        store,
        project_id,
        current_state,
        f"TX-PRIOR-INTENT-ONLY-{_world['mapping_key']}",
        [(_INTENT_KIND, _world["mapping_key"], intent)],
    )
    assert store.resolve_record(project_id, _ATTEMPT_KIND, _world["mapping_key"]) is None

    adapter = FakeGitHubAdapter()
    outcome = _project(_world, adapter, materialized_at=materialized_at)
    assert outcome["reused"] is False
    assert adapter.materialize_call_count == 1


# ---------------------------------------------------------------------------
# Stage: materialize genuinely failed (or crashed) with nothing discoverable --
# the ambiguous reconciliation state
# ---------------------------------------------------------------------------


def test_prior_attempt_with_nothing_discoverable_requires_reconciliation(
    _world: dict[str, Any],
) -> None:
    materialized_at = "2026-09-08T00:00:01Z"
    _commit_intent_and_attempt(_world, materialized_at=materialized_at)

    adapter = FakeGitHubAdapter()
    with pytest.raises(ProjectionReconciliationRequiredError):
        _project(_world, adapter, materialized_at=materialized_at)
    # The retry never blindly re-calls materialize under this ambiguous state.
    assert adapter.materialize_call_count == 0
    assert adapter.find_by_correlation_key_call_count == 1


def test_materialize_failure_then_identical_retry_requires_reconciliation(
    _world: dict[str, Any],
) -> None:
    """A materialize call that genuinely raised (a transport failure, say) still leaves the
    attempt marker durably committed -- the exact state the reconciliation refusal exists to
    catch on the next identical-owner retry, since this route cannot itself distinguish
    "definitely failed" from "may have partially succeeded"."""

    adapter = FakeGitHubAdapter(fail_materialize=ProjectionAdapterError("simulated outage"))
    materialized_at = "2026-09-08T00:00:01Z"
    with pytest.raises(ProjectionAdapterError):
        _project(_world, adapter, materialized_at=materialized_at)
    assert adapter.materialize_call_count == 1

    with pytest.raises(ProjectionReconciliationRequiredError):
        _project(_world, adapter, materialized_at=materialized_at)
    # The reconciliation refusal itself never calls materialize again.
    assert adapter.materialize_call_count == 1


# ---------------------------------------------------------------------------
# Stage: external success, response lost -- discoverable on retry, reused not
# re-materialized
# ---------------------------------------------------------------------------


def test_prior_attempt_with_discoverable_artifact_reuses_without_rematerializing(
    _world: dict[str, Any],
) -> None:
    materialized_at = "2026-09-08T00:00:01Z"
    adapter = FakeGitHubAdapter()
    # Simulate a prior attempt whose own external write genuinely succeeded, but whose
    # response never reached the caller before it crashed (so no Envelope was ever
    # committed) -- the artifact is nonetheless durably associated with the correlation key
    # on the adapter's own side, exactly as a real GitHub Issue/PR/Check-Run search would
    # find it.
    adapter.materialize(
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        payload=dict(_PAYLOAD),
        correlation_key=_world["mapping_key"],
    )
    assert adapter.materialize_call_count == 1
    _commit_intent_and_attempt(_world, materialized_at=materialized_at)

    outcome = _project(_world, adapter, materialized_at=materialized_at)
    assert outcome["reused"] is False  # no Envelope existed yet -- this call commits the first
    assert adapter.materialize_call_count == 1  # never called a second time
    assert adapter.find_by_correlation_key_call_count == 1


# ---------------------------------------------------------------------------
# Stage: genuine process retry after full success -- idempotent, single Envelope
# ---------------------------------------------------------------------------


def test_repeated_identical_calls_never_duplicate_intent_or_attempt_records(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    materialized_at = "2026-09-08T00:00:01Z"
    first = _project(_world, adapter, materialized_at=materialized_at)
    second = _project(_world, adapter, materialized_at=materialized_at)
    assert first["envelope"] == second["envelope"]
    assert second["reused"] is True
    assert adapter.materialize_call_count == 1

    store = _world["store"]
    intent = store.resolve_record(_world["project_id"], _INTENT_KIND, _world["mapping_key"])
    attempt = store.resolve_record(_world["project_id"], _ATTEMPT_KIND, _world["mapping_key"])
    assert intent is not None
    assert attempt is not None


# ---------------------------------------------------------------------------
# find_by_correlation_key lookup failure blocks new creation (P14-R2-F2)
# ---------------------------------------------------------------------------


def test_correlation_lookup_failure_blocks_materialize(_world: dict[str, Any]) -> None:
    adapter = FakeGitHubAdapter(
        fail_find_by_correlation_key=ProjectionAdapterError("simulated lookup outage")
    )
    with pytest.raises(ProjectionAdapterError):
        _project(_world, adapter)
    assert adapter.materialize_call_count == 0
