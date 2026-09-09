"""Phase 15 (Issue #64) shared Runtime Observation test world.

Deliberately mirrors ``tests/integration/projection/test_project_to_github.py``'s own
``_bound``/``_commit_records``/``_commit_grant``/``_commit_declaration`` helpers rather than
importing them directly (that module is a test module, never a fixture module other test
modules should import from) -- the identical "self-contained fixture, not cross-test-module
reuse" discipline every other phase's own fixture layer in this repository already keeps.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tests.fixtures.product_binding import (
    bind_project_kwargs,
    genesis_records,
    human_authority_signing_key,
    sign_github_projection_grant_declaration,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.identity import github_projection_grant_id
from manosube_agent_civilization.binding import bind_project, declare_github_projection_grant
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

TARGET_REPOSITORY: dict[str, str] = {"host": "github", "owner": "acme", "repo": "widget"}


def bound(tmp_path: Path) -> tuple[FileStateStore, dict[str, Any]]:
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


def commit_records(
    store: FileStateStore,
    project_id: str,
    current_state: dict[str, Any],
    transaction_id: str,
    records: list[tuple[str, str, Mapping[str, Any]]],
    *,
    committed_at: str = "2026-09-09T00:00:00Z",
) -> dict[str, Any]:
    """Commit *records* over *current_state* and return the resulting next State -- the
    identical shared shape every fixture-side commit in this repository's own test suite
    uses (deliberately bypasses :func:`~manosube_agent_civilization.runtime.route.
    observe_runtime_target`'s own single sanctioned committer, since this helper exists only
    to seed pre-existing world state a real route call then observes/consumes)."""

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


def target_identity_for(
    project_binding_id: str,
    *,
    provider: str = "local",
    deployment_id: str = "widget-service",
    instance_identity: str = "widget-service-1",
    deployment_fingerprint: str = "sha256:" + "a" * 64,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "deployment_id": deployment_id,
        "instance_identity": instance_identity,
        "project_binding_ref": {"kind": "project_binding", "id": project_binding_id},
        "deployment_fingerprint": deployment_fingerprint,
    }


def boundary_for(
    *,
    base_url: str = "http://127.0.0.1:1",
    path: str = "/health",
    permitted_fields: list[str] | None = None,
    issued_at: str = "2026-01-01T00:00:00Z",
    expires_at: str = "2026-01-01T01:00:00Z",
    allowed_hosts: list[str] | None = None,
    timeout_seconds: int = 5,
    redaction_fields: list[str] | None = None,
    expected_field: str | None = None,
    expected_value: Any = None,
) -> dict[str, Any]:
    boundary: dict[str, Any] = {
        "observation_method": "HTTP_GET_BOUNDED",
        "endpoint": {"base_url": base_url, "path": path},
        "permitted_fields": list(permitted_fields if permitted_fields is not None else ["status"]),
        "time_window": {"issued_at": issued_at, "expires_at": expires_at},
        "network_scope": {
            "allowed_hosts": list(allowed_hosts if allowed_hosts is not None else ["127.0.0.1"])
        },
        "timeout_seconds": timeout_seconds,
        "redaction_fields": list(redaction_fields if redaction_fields is not None else []),
    }
    if expected_field is not None:
        boundary["expected_field"] = expected_field
        boundary["expected_value"] = expected_value
    return boundary


def commit_grant(
    store: FileStateStore,
    project_id: str,
    human_authority_ref: dict[str, Any],
    transaction_id: str,
    *,
    subject_ref: dict[str, Any],
    subject_fingerprint: str,
    projection_kind: str,
    target_repository: dict[str, Any] | None = None,
    payload_fingerprint: str,
    permitted_action: str = "MATERIALIZE_PROJECTION",
    status: str = "ACTIVE",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Commit one real, genuine, Store-resolvable ``github_projection_grant`` and return
    ``(ref, grant)`` -- needed by V5's own bootstrap continuity proof, mirroring
    ``test_project_to_github.py``'s own identical helper exactly."""

    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": dict(subject_ref),
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": dict(target_repository or TARGET_REPOSITORY),
        "payload_fingerprint": payload_fingerprint,
        "permitted_action": permitted_action,
        "status": status,
        "granted_by": dict(human_authority_ref),
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    current_state = store.load_current(project_id)
    commit_records(
        store,
        project_id,
        current_state,
        transaction_id,
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    return {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}, grant


def commit_declaration(
    store: FileStateStore,
    project_id: str,
    project_binding_id: str,
    human_authority_ref: dict[str, Any],
    grant: dict[str, Any],
    *,
    status: str = "ACTIVE",
    declared_at: str = "2026-09-08T00:00:00Z",
) -> dict[str, Any]:
    """Declare and commit one real, genuinely Ed25519-signed
    ``github_projection_grant_declaration`` through the real, fail-closed committing route
    -- never a raw record insert, mirroring ``test_project_to_github.py``'s own identical
    helper exactly."""

    grant_ref = {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}
    signature = sign_github_projection_grant_declaration(
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        declared_by=human_authority_ref,
        subject_ref=grant["subject_ref"],
        subject_fingerprint=grant["subject_fingerprint"],
        projection_kind=grant["projection_kind"],
        target_repository=grant["target_repository"],
        payload_fingerprint=grant["payload_fingerprint"],
        permitted_action=grant["permitted_action"],
        status=status,
        declared_at=declared_at,
    )
    result = declare_github_projection_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        status=status,
        declared_at=declared_at,
        signature=signature,
        schema_root=SCHEMA_ROOT,
    )
    declaration = result["github_projection_grant_declaration"]
    return {
        "kind": "github_projection_grant_declaration",
        "id": declaration["github_projection_grant_declaration_id"],
    }


__all__ = [
    "TARGET_REPOSITORY",
    "bound",
    "boundary_for",
    "commit_declaration",
    "commit_grant",
    "commit_records",
    "human_authority_signing_key",
    "target_identity_for",
]
