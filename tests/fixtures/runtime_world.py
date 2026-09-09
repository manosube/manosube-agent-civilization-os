"""Phase 15 (Issue #64) shared Runtime Observation test world.

Deliberately mirrors ``tests/integration/projection/test_project_to_github.py``'s own
``_bound``/``_commit_records``/``_commit_grant``/``_commit_declaration`` helpers rather than
importing them directly (that module is a test module, never a fixture module other test
modules should import from) -- the identical "self-contained fixture, not cross-test-module
reuse" discipline every other phase's own fixture layer in this repository already keeps.

Structural Review Round 2 (P15-R2-F1/F2) gives this module two further, deliberately
test-confined responsibilities:

- :func:`test_only_trusted_runtime_root` -- the *only* issuer of a
  :class:`~manosube_agent_civilization.runtime.bootstrap.TrustedRuntimeRoot` that exists
  anywhere, now that the shipped public minting factory is deleted (P15-R2-F1).
- :func:`sign_runtime_deployment_declaration` and the three test-only Ed25519 key pairs
  (canonical, alternate world, post-re-binding rotation) a
  ``runtime_deployment_declaration``'s own Human Authority signature is produced with
  (P15-R2-F2). Every one is a *test* signer: a real Human's private key never touches this
  system, and shipped code only ever verifies.
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
    _signing_private_key as _canonical_signing_private_key,
    bind_project_kwargs,
    genesis_records,
    human_authority_ref as canonical_human_authority_ref,
    human_authority_signing_key,
    sign_github_projection_grant_declaration,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.identity import github_projection_grant_id, rule_id
from manosube_agent_civilization.binding import (
    assemble_project_binding,
    bind_project,
    declare_github_projection_grant,
)
from manosube_agent_civilization.runtime.bootstrap import (
    _PROVISIONING_SENTINEL,
    TrustedRuntimeRoot,
)
from manosube_agent_civilization.runtime.identity import (
    runtime_deployment_declaration_id,
    runtime_deployment_declaration_semantic_fingerprint,
    runtime_deployment_declaration_signing_payload,
)
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

TARGET_REPOSITORY: dict[str, str] = {"host": "github", "owner": "acme", "repo": "widget"}

DEPLOYMENT_DECLARATION_RECORD_KIND = "runtime_deployment_declaration"
DEFAULT_DEPLOYMENT_FINGERPRINT = "sha256:" + "a" * 64


# ---------------------------------------------------------------------------
# The one TrustedRuntimeRoot issuer that exists anywhere -- and it lives in tests
# ---------------------------------------------------------------------------
#
# Phase 15 Structural Review Round 2 (P15-R2-F1) deleted the shipped public
# ``provision_trusted_runtime_root`` factory: it accepted exactly the caller-controlled
# Store/Project/Binding tuple Round 1's own correction existed to stop an untrusted surface from
# selecting, so moving those three arguments one call earlier changed the API's shape rather
# than control of the trust decision. Nothing in the shipped package mints a
# ``TrustedRuntimeRoot`` any more -- proved mechanically by an AST walk over the installed
# package in ``tests/contract/runtime/test_runtime_static_conformance.py``.
#
# ``bootstrap_projection_execution_capability`` still needs one to be exercised at all, so this
# module holds the issuer, structurally confined to ``tests/``: it reaches into
# ``runtime.bootstrap``'s own module-private ``_PROVISIONING_SENTINEL``, which Python does not
# enforce across an import boundary. That is deliberate, named, and honest -- it is exactly the
# "explicitly injected test issuer that is structurally unavailable to the live path" the
# Structural Review's own text permits, and the shipped package can never reach it (production
# code importing any ``tests.*`` module is itself statically forbidden).


def test_only_trusted_runtime_root(
    store: Any, *, project_id: str, project_binding_id: str
) -> TrustedRuntimeRoot:
    """Return a genuine :class:`~manosube_agent_civilization.runtime.bootstrap.
    TrustedRuntimeRoot` over *store*/*project_id*/*project_binding_id* -- the test-only
    replacement for the deleted shipped minting factory (P15-R2-F1).

    Named ``test_only_`` so that no reading of a call site can mistake it for a production
    entry point, and defined here rather than in ``src/`` precisely so that the shipped package
    contains no function of this shape at all.
    """

    return TrustedRuntimeRoot(store, project_id, project_binding_id, _PROVISIONING_SENTINEL)


#: This is a fixture helper, not a test case: its name starts with ``test_`` deliberately, so no
#: call site can read as a production entry point, which would otherwise make pytest collect it
#: as a (zero-assertion, argument-hungry) test wherever a test module imports it.
test_only_trusted_runtime_root.__test__ = False  # type: ignore[attr-defined]


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


def alternate_signing_private_key() -> Ed25519PrivateKey:
    """The alternate world's own private signing half -- exposed so a negative control can sign
    a *canonical*-world record with a genuinely different, but genuinely legitimate, Human
    Authority's key (P15-R2-F2's own "wrong signer" control)."""

    return _alternate_signing_private_key()


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


# ---------------------------------------------------------------------------
# A legitimate Human Authority signing-key re-binding, inside one project
# ---------------------------------------------------------------------------
#
# P15-R2-F2 requires proving that a declaration signed under a *previous* Project Binding is
# refused once the project has legitimately been re-bound, and that a newly issued, newly signed
# one succeeds. This repository has no separate "re-bind" route: ``bind_project`` owns genesis
# and genesis is strictly one-shot. A re-binding here is therefore exactly what it is in this
# Kernel -- a genuinely new ``project_binding`` record, assembled through the *real* Binding
# producer (``assemble_project_binding``, the identical function ``bind_project`` itself calls),
# carrying a rotated ``human_authority_signing_key`` under the identical Human Authority, and
# committed into the identical project. Because a Project Binding is content-addressed over its
# own ``human_authority_ref``/``human_authority_signing_key``, that rotation necessarily mints a
# new ``project_binding_id``, and Boot restores it exactly as it restores the original.

REBOUND_SIGNING_KEY_ID = "AUTH-KEY-REBOUND-0001"


def _rebound_signing_private_key() -> Ed25519PrivateKey:
    """A third fixed, deterministic, test-only Ed25519 private key -- the one a legitimate
    signing-key rotation of the *canonical* Human Authority moves to, generated exactly the way
    :func:`_alternate_signing_private_key` above already generates its own."""

    seed = hashlib.sha256(b"tests.fixtures.runtime_world rebound_human_authority").digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def rebound_signing_private_key() -> Ed25519PrivateKey:
    """The post-re-binding private signing half -- what a newly issued declaration must be
    signed with once :func:`rebind_with_rotated_signing_key` has run."""

    return _rebound_signing_private_key()


def rebound_human_authority_signing_key() -> dict[str, Any]:
    public_bytes = (
        _rebound_signing_private_key()
        .public_key()
        .public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    )
    return {
        "algorithm": "ed25519",
        "key_id": REBOUND_SIGNING_KEY_ID,
        "public_key": public_bytes.hex(),
    }


def rebind_with_rotated_signing_key(
    store: FileStateStore, project_id: str, *, transaction_id: str = "TX-RUNTIME-REBIND-0001"
) -> dict[str, Any]:
    """Commit one genuinely new, real ``project_binding`` for *project_id* under the identical
    Human Authority but a rotated ``human_authority_signing_key``, and return that new record.

    Assembled through the real Binding producer
    (:func:`~manosube_agent_civilization.binding.assemble_project_binding`) -- never a hand-built
    dict -- so the resulting record is schema-valid, content-addressed, and restorable by the
    real ``boot_project`` exactly as the original is.
    """

    kwargs = deepcopy(bind_project_kwargs())
    rebound = assemble_project_binding(
        project_id=kwargs["project_id"],
        objective_revision_ref={
            "kind": "objective_revision",
            "id": kwargs["objective_revision"]["objective_revision_id"],
        },
        boundary=kwargs["boundary"],
        authority_policy_ref=kwargs["authority_policy_ref"],
        source_registrations=kwargs["source_registrations"],
        command_policy=kwargs["command_policy"],
        secret_exclusion_policy=kwargs["secret_exclusion_policy"],
        human_authority_ref=kwargs["human_authority_ref"],
        human_authority_signing_key=rebound_human_authority_signing_key(),
        bound_at=kwargs["bound_at"],
        schema_root=SCHEMA_ROOT,
    )
    commit_records(
        store,
        project_id,
        store.load_current(project_id),
        transaction_id,
        [("project_binding", rebound["project_binding_id"], rebound)],
    )
    return rebound


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


def canonical_signing_private_key() -> Ed25519PrivateKey:
    """The canonical fixture Human Authority's own fixed, deterministic, test-only Ed25519
    private key -- the private half of ``tests.fixtures.product_binding``'s own
    :func:`~tests.fixtures.product_binding.human_authority_signing_key`, and therefore the one
    key a canonical world's own Boot-restored Project Binding actually verifies against.

    A real Human's private key never touches this system (see
    ``manosube_agent_civilization.binding.signature``'s own module docstring, which only ever
    verifies); this is a test signer, exactly as every other signing helper in this repository's
    own fixture layer is.
    """

    return _canonical_signing_private_key()


def sign_runtime_deployment_declaration(
    declaration: Mapping[str, Any], *, private_key: Ed25519PrivateKey, key_id: str
) -> dict[str, Any]:
    """Sign the exact canonical payload
    :func:`~manosube_agent_civilization.runtime.identity.
    runtime_deployment_declaration_signing_payload` derives from *declaration*'s own adopted
    semantic fields (Phase 15 Structural Review Round 2, P15-R2-F2) -- the identical sibling of
    ``tests.fixtures.product_binding``'s own ``sign_github_projection_grant_declaration``, over
    a Runtime Deployment Declaration's own restated fields instead.
    """

    message = runtime_deployment_declaration_signing_payload(dict(declaration))
    return {
        "algorithm": "ed25519",
        "key_id": key_id,
        "value": private_key.sign(message).hex(),
    }


def deployment_declaration_for(
    project_id: str,
    project_binding_id: str,
    human_authority_ref: Mapping[str, Any],
    *,
    provider: str = "local",
    deployment_id: str = "widget-service",
    instance_identity: str = "widget-service-1",
    deployment_fingerprint: str = DEFAULT_DEPLOYMENT_FINGERPRINT,
    status: str = "ACTIVE",
    declared_at: str = "2026-09-08T00:00:00Z",
    signer: Ed25519PrivateKey | None = None,
    signing_key_id: str | None = None,
) -> dict[str, Any]:
    """Return one real, schema-valid, content-addressed, genuinely Ed25519-signed
    ``runtime_deployment_declaration`` body (Round 1, P15-R1-F6; signed and status-bound by
    Round 2, P15-R2-F2) -- the canonical record a target's own declared
    ``deployment_fingerprint`` must now match, minted through the real identity owner exactly as
    every other fixture in this repository mints a content-addressed record.

    *signer*/*signing_key_id* default to the canonical fixture Human Authority's own key pair --
    the identical ``signer``-with-a-canonical-default convention :func:`commit_declaration`
    already uses in this same module -- so a test that simply wants a legitimate declaration
    gets one, while a negative control passes an attacker's, an alternate world's, or a
    pre-re-binding key explicitly.

    The signature is produced over the body *before* either digest field exists (a signature
    cannot cover its own value; an identity cannot be computed over itself), and both digests
    are then computed over the identical payload the signature covers -- the shared-derivation
    discipline ``binding/identity.py``'s own declaration payloads already establish.
    """

    declaration: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": project_id,
        "project_binding_ref": {"kind": "project_binding", "id": project_binding_id},
        "provider": provider,
        "deployment_id": deployment_id,
        "instance_identity": instance_identity,
        "deployment_fingerprint": deployment_fingerprint,
        "human_authority_ref": dict(human_authority_ref),
        "status": status,
        "declared_at": declared_at,
    }
    declaration["signature"] = sign_runtime_deployment_declaration(
        declaration,
        private_key=signer if signer is not None else canonical_signing_private_key(),
        key_id=(
            signing_key_id
            if signing_key_id is not None
            else str(human_authority_signing_key()["key_id"])
        ),
    )
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
    status: str = "ACTIVE",
    declared_at: str = "2026-09-08T00:00:00Z",
    signer: Ed25519PrivateKey | None = None,
    signing_key_id: str | None = None,
) -> dict[str, Any]:
    """Commit the canonical, ACTIVE, genuinely signed ``runtime_deployment_declaration``
    anchoring this target and return the matching ``target_identity`` referencing it -- the one
    helper every V1-V5 test uses now that ``deployment_declaration_ref`` is a required,
    Store-resolved, Authority-bound, signature-verified field (P15-R1-F6, P15-R2-F2)."""

    declaration = deployment_declaration_for(
        project_id,
        project_binding_id,
        human_authority_ref,
        provider=provider,
        deployment_id=deployment_id,
        instance_identity=instance_identity,
        deployment_fingerprint=deployment_fingerprint,
        status=status,
        declared_at=declared_at,
        signer=signer,
        signing_key_id=signing_key_id,
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
    "REBOUND_SIGNING_KEY_ID",
    "TARGET_REPOSITORY",
    "alternate_bound",
    "alternate_human_authority_signing_key",
    "alternate_signing_private_key",
    "bound",
    "boundary_for",
    "canonical_signing_private_key",
    "commit_declaration",
    "commit_deployment_declaration",
    "commit_grant",
    "commit_records",
    "commit_target_identity",
    "deployment_declaration_for",
    "human_authority_signing_key",
    "rebind_with_rotated_signing_key",
    "rebound_human_authority_signing_key",
    "rebound_signing_private_key",
    "sign_alternate_github_projection_grant_declaration",
    "sign_runtime_deployment_declaration",
    "target_identity_for",
    "test_only_trusted_runtime_root",
]
