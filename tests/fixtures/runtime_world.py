"""Phase 15 (Issue #64) shared Runtime Observation test world.

Deliberately mirrors ``tests/integration/projection/test_project_to_github.py``'s own
``_bound``/``_commit_records``/``_commit_grant``/``_commit_declaration`` helpers rather than
importing them directly (that module is a test module, never a fixture module other test
modules should import from) -- the identical "self-contained fixture, not cross-test-module
reuse" discipline every other phase's own fixture layer in this repository already keeps.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from tests.fixtures.product_binding import (
    bind_project_kwargs,
    genesis_records,
    human_authority_ref as canonical_human_authority_ref,
    human_authority_signing_key,
    sign_github_projection_grant_declaration,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.identity import github_projection_grant_id, rule_id
from manosube_agent_civilization.binding import bind_project, declare_github_projection_grant
from manosube_agent_civilization.runtime.identity import (
    runtime_deployment_declaration_id,
    runtime_deployment_declaration_semantic_fingerprint,
)
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

TARGET_REPOSITORY: dict[str, str] = {"host": "github", "owner": "acme", "repo": "widget"}

DEPLOYMENT_DECLARATION_RECORD_KIND = "runtime_deployment_declaration"
DEFAULT_DEPLOYMENT_FINGERPRINT = "sha256:" + "a" * 64


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


# ---------------------------------------------------------------------------
# A second, fully self-consistent world under its own external Human Authority
# ---------------------------------------------------------------------------
#
# P15-R1-F4's own decisive control needs an alternate Store that is not merely "a different
# temporary directory" but a genuinely complete, internally valid world on its own terms: its
# own Human Authority, its own Ed25519 signing key, its own Project Binding, and its own
# grants/declarations signed by that key and verifiable against that Binding. Anything less
# would prove only that two directories differ, not that a *legitimate* alternate authority
# world cannot be substituted for the canonical one.

ALTERNATE_HUMAN_AUTHORITY_REF: dict[str, str] = {
    "kind": "human_authority",
    "id": "AUTH-ALTERNATE-0001",
}


def _alternate_signing_private_key() -> Ed25519PrivateKey:
    """A second fixed, deterministic, test-only Ed25519 private key -- genuinely different
    from ``tests.fixtures.product_binding``'s own, so the alternate world below is signed by
    an authority the canonical world has never heard of."""

    seed = hashlib.sha256(b"tests.fixtures.runtime_world alternate_human_authority").digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def alternate_human_authority_signing_key() -> dict[str, Any]:
    public_bytes = (
        _alternate_signing_private_key()
        .public_key()
        .public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    )
    return {
        "algorithm": "ed25519",
        "key_id": "AUTH-KEY-ALTERNATE-0001",
        "public_key": public_bytes.hex(),
    }


def _rebind_authority(value: Any) -> Any:
    """Recursively replace every appearance of the canonical fixture Human Authority reference
    with :data:`ALTERNATE_HUMAN_AUTHORITY_REF` -- the three-way cross-match ``bind_project``
    enforces (Binding, Objective Revision, Authority Rule) means all of them must move
    together or the alternate world would not be internally valid at all."""

    canonical = canonical_human_authority_ref()
    if isinstance(value, dict):
        if value == canonical:
            return dict(ALTERNATE_HUMAN_AUTHORITY_REF)
        return {key: _rebind_authority(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_rebind_authority(item) for item in value]
    return value


def alternate_bound(tmp_path: Path) -> tuple[FileStateStore, dict[str, Any]]:
    """Bind one complete alternate world -- its own external Human Authority, its own signing
    key, its own Project Binding -- through the identical real ``bind_project`` route, and
    return it exactly as :func:`bound` returns the canonical one."""

    store_root = tmp_path / "alternate-backend"
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = deepcopy(bind_project_kwargs())
    kwargs = _rebind_authority(kwargs)
    kwargs["human_authority_signing_key"] = alternate_human_authority_signing_key()
    kwargs["authority_rule"]["authority_rule_id"] = rule_id(kwargs["authority_rule"])
    kwargs["authority_policy_ref"] = {
        "kind": "authority_rule",
        "id": kwargs["authority_rule"]["authority_rule_id"],
    }
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store, {
        "project_id": kwargs["project_id"],
        "project_binding_id": result["project_binding_id"],
        "genesis_state": result["committed_state"],
    }


def sign_alternate_github_projection_grant_declaration(**payload_fields: Any) -> dict[str, Any]:
    """Sign the identical canonical declaration payload
    :func:`tests.fixtures.product_binding.sign_github_projection_grant_declaration` signs, with
    the alternate world's own private key -- so the alternate world's declarations are
    genuinely valid *there*, and genuinely foreign everywhere else."""

    from manosube_agent_civilization.binding.identity import (
        github_projection_grant_declaration_signing_payload,
    )

    payload_record = {"schema_version": "0.1", **payload_fields}
    message = github_projection_grant_declaration_signing_payload(payload_record)
    return {
        "algorithm": "ed25519",
        "key_id": alternate_human_authority_signing_key()["key_id"],
        "value": _alternate_signing_private_key().sign(message).hex(),
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


def deployment_declaration_for(
    project_id: str,
    project_binding_id: str,
    human_authority_ref: Mapping[str, Any],
    *,
    provider: str = "local",
    deployment_id: str = "widget-service",
    instance_identity: str = "widget-service-1",
    deployment_fingerprint: str = DEFAULT_DEPLOYMENT_FINGERPRINT,
    declared_at: str = "2026-09-08T00:00:00Z",
) -> dict[str, Any]:
    """Return one real, schema-valid, content-addressed ``runtime_deployment_declaration``
    body (Phase 15 Structural Review Round 1, P15-R1-F6) -- the canonical record a target's own
    declared ``deployment_fingerprint`` must now match, minted through the real identity owner
    exactly as every other fixture in this repository mints a content-addressed record."""

    declaration: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": project_id,
        "project_binding_ref": {"kind": "project_binding", "id": project_binding_id},
        "provider": provider,
        "deployment_id": deployment_id,
        "instance_identity": instance_identity,
        "deployment_fingerprint": deployment_fingerprint,
        "human_authority_ref": dict(human_authority_ref),
        "declared_at": declared_at,
    }
    declaration["runtime_deployment_declaration_id"] = runtime_deployment_declaration_id(
        declaration
    )
    declaration["runtime_deployment_declaration_semantic_fingerprint"] = (
        runtime_deployment_declaration_semantic_fingerprint(declaration)
    )
    return declaration


def commit_deployment_declaration(
    store: FileStateStore, project_id: str, declaration: Mapping[str, Any]
) -> dict[str, str]:
    """Commit *declaration* (idempotently -- a content address already resolved is the
    identical record, never a second one) and return the reference naming it."""

    declaration_id = str(declaration["runtime_deployment_declaration_id"])
    if store.resolve_record(project_id, DEPLOYMENT_DECLARATION_RECORD_KIND, declaration_id) is None:
        commit_records(
            store,
            project_id,
            store.load_current(project_id),
            f"TX-RUNTIME-DEPLOY-DECL-{declaration_id[-16:]}",
            [(DEPLOYMENT_DECLARATION_RECORD_KIND, declaration_id, dict(declaration))],
        )
    return {"kind": DEPLOYMENT_DECLARATION_RECORD_KIND, "id": declaration_id}


def target_identity_for(
    project_binding_id: str,
    *,
    deployment_declaration_ref: Mapping[str, str],
    provider: str = "local",
    deployment_id: str = "widget-service",
    instance_identity: str = "widget-service-1",
    deployment_fingerprint: str = DEFAULT_DEPLOYMENT_FINGERPRINT,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "deployment_id": deployment_id,
        "instance_identity": instance_identity,
        "project_binding_ref": {"kind": "project_binding", "id": project_binding_id},
        "deployment_declaration_ref": dict(deployment_declaration_ref),
        "deployment_fingerprint": deployment_fingerprint,
    }


def commit_target_identity(
    store: FileStateStore,
    project_id: str,
    project_binding_id: str,
    human_authority_ref: Mapping[str, Any],
    *,
    provider: str = "local",
    deployment_id: str = "widget-service",
    instance_identity: str = "widget-service-1",
    deployment_fingerprint: str = DEFAULT_DEPLOYMENT_FINGERPRINT,
    declared_at: str = "2026-09-08T00:00:00Z",
) -> dict[str, Any]:
    """Commit the canonical ``runtime_deployment_declaration`` anchoring this target and
    return the matching ``target_identity`` referencing it -- the one helper every V1-V5 test
    uses now that ``deployment_declaration_ref`` is a required, Store-resolved field."""

    declaration = deployment_declaration_for(
        project_id,
        project_binding_id,
        human_authority_ref,
        provider=provider,
        deployment_id=deployment_id,
        instance_identity=instance_identity,
        deployment_fingerprint=deployment_fingerprint,
        declared_at=declared_at,
    )
    ref = commit_deployment_declaration(store, project_id, declaration)
    return target_identity_for(
        project_binding_id,
        deployment_declaration_ref=ref,
        provider=provider,
        deployment_id=deployment_id,
        instance_identity=instance_identity,
        deployment_fingerprint=deployment_fingerprint,
    )


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
    signer: Any = None,
) -> dict[str, Any]:
    """Declare and commit one real, genuinely Ed25519-signed
    ``github_projection_grant_declaration`` through the real, fail-closed committing route
    -- never a raw record insert, mirroring ``test_project_to_github.py``'s own identical
    helper exactly.

    *signer* defaults to the canonical fixture Human Authority's own signing helper; the
    alternate world (P15-R1-F4) passes
    :func:`sign_alternate_github_projection_grant_declaration` instead, so its declarations
    are signed by its own genuinely different key.
    """

    sign = signer or sign_github_projection_grant_declaration
    grant_ref = {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}
    signature = sign(
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
    "ALTERNATE_HUMAN_AUTHORITY_REF",
    "DEFAULT_DEPLOYMENT_FINGERPRINT",
    "DEPLOYMENT_DECLARATION_RECORD_KIND",
    "TARGET_REPOSITORY",
    "alternate_bound",
    "alternate_human_authority_signing_key",
    "bound",
    "boundary_for",
    "commit_declaration",
    "commit_deployment_declaration",
    "commit_grant",
    "commit_records",
    "commit_target_identity",
    "deployment_declaration_for",
    "human_authority_signing_key",
    "sign_alternate_github_projection_grant_declaration",
    "target_identity_for",
]
