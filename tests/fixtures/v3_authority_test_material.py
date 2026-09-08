"""Test-only V3 live-write authority material builder (Structural Review Round 8, Issue #62,
P14-R8-F1).

This module assembles the exact genuinely-issuable ``project_binding`` +
``github_projection_grant`` + ``github_projection_grant_declaration`` material
:mod:`tests.fixtures.v3_live_write_authority` consumes -- by reusing this repository's own
established test-only Product Binding fixtures
(:mod:`tests.fixtures.product_binding`) rather than inventing a second signing convention.
It never touches the Store: :func:`~manosube_agent_civilization.binding.engine.
assemble_project_binding` validates, identifies and returns the full ``project_binding``
record without ever calling ``store.initialize`` (the real genesis route,
:func:`~manosube_agent_civilization.binding.route.bind_project`, does that separately; V3's
own offline material-building has no need to persist anything to construct a genuinely
content-address-verifiable record).

**This module is never imported by** :mod:`tests.fixtures.v3_live_write_authority` **or by
the one live call site** (``_v3_live_authorized()`` in
``tests/integration/projection/test_v3_real_github_vertical_proof.py``) -- a static
conformance test
(``tests/contract/projection/test_v3_live_write_authority_static_conformance.py``) proves
this by AST-walking both modules' own import statements. The live gate consumes only
already-assembled JSON material (via
:func:`~tests.fixtures.v3_live_write_authority.load_v3_live_write_authority_material`);
nothing in it can construct or sign a new record.
"""

from __future__ import annotations

import hashlib
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from manosube_agent_civilization.authority.identity import github_projection_grant_id
from manosube_agent_civilization.binding import assemble_project_binding

from . import product_binding
from .v3_live_write_authority import (
    V3_PERMITTED_ACTION,
    V3_PROJECTION_KINDS,
    v3_configuration_subject_ref,
)
from .v3_target_configuration import V3TargetConfiguration


def genuine_project_binding() -> dict[str, Any]:
    """The real, content-address-verifiable ``project_binding`` record
    :func:`tests.fixtures.product_binding.bind_project_kwargs`'s own fixture material
    produces -- identical to what a real ``bind_project`` genesis commit would persist,
    assembled here without any Store."""

    kwargs = product_binding.bind_project_kwargs()
    kwargs.pop("genesis_state")
    kwargs.pop("authority_rule")
    objective_revision = kwargs.pop("objective_revision")
    kwargs["objective_revision_ref"] = {
        "kind": "objective_revision",
        "id": objective_revision["objective_revision_id"],
    }
    return assemble_project_binding(**kwargs)


def _grant(
    config: V3TargetConfiguration, *, projection_kind: str, project_binding: dict[str, Any]
) -> dict[str, Any]:
    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_binding["project_id"],
        "subject_ref": v3_configuration_subject_ref(config),
        "subject_fingerprint": config.configuration_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": dict(config.target_repository),
        "payload_fingerprint": config.configuration_fingerprint,
        "permitted_action": V3_PERMITTED_ACTION,
        "status": "ACTIVE",
        "granted_by": dict(project_binding["human_authority_ref"]),
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    return grant


def _declaration(
    *,
    project_binding: dict[str, Any],
    grant: dict[str, Any],
    declared_at: str = "2026-09-08T00:00:00Z",
) -> dict[str, Any]:
    from manosube_agent_civilization.binding.identity import (
        github_projection_grant_declaration_id,
    )

    grant_ref = {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}
    signature = product_binding.sign_github_projection_grant_declaration(
        project_id=grant["project_id"],
        project_binding_id=project_binding["project_binding_id"],
        grant_ref=grant_ref,
        declared_by=grant["granted_by"],
        subject_ref=grant["subject_ref"],
        subject_fingerprint=grant["subject_fingerprint"],
        projection_kind=grant["projection_kind"],
        target_repository=grant["target_repository"],
        payload_fingerprint=grant["payload_fingerprint"],
        permitted_action=grant["permitted_action"],
        status="ACTIVE",
        declared_at=declared_at,
    )
    declaration: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_declaration_id": "",
        "project_id": grant["project_id"],
        "project_binding_id": project_binding["project_binding_id"],
        "grant_ref": grant_ref,
        "declared_by": grant["granted_by"],
        "subject_ref": grant["subject_ref"],
        "subject_fingerprint": grant["subject_fingerprint"],
        "projection_kind": grant["projection_kind"],
        "target_repository": grant["target_repository"],
        "payload_fingerprint": grant["payload_fingerprint"],
        "permitted_action": grant["permitted_action"],
        "status": "ACTIVE",
        "declared_at": declared_at,
        "signature": signature,
    }
    declaration["github_projection_grant_declaration_id"] = github_projection_grant_declaration_id(
        declaration
    )
    return declaration


def genuine_v3_authority_material(config: V3TargetConfiguration) -> dict[str, Any]:
    """A complete, genuinely issuable V3 live-write authority material blob -- one real
    ``project_binding`` plus one ``github_projection_grant``/``github_projection_grant_
    declaration`` pair per :data:`~tests.fixtures.v3_live_write_authority.
    V3_PROJECTION_KINDS`, each genuinely Ed25519-signed against that exact project_binding's
    own ``human_authority_signing_key`` -- the identical route
    (:func:`~tests.fixtures.product_binding.sign_github_projection_grant_declaration`) a real
    production ``github_projection_grant`` declaration already uses."""

    project_binding = genuine_project_binding()
    grants = [
        _grant(config, projection_kind=kind, project_binding=project_binding)
        for kind in V3_PROJECTION_KINDS
    ]
    declarations = [_declaration(project_binding=project_binding, grant=grant) for grant in grants]
    return {
        "project_id": project_binding["project_id"],
        "project_binding": project_binding,
        "grants": grants,
        "grant_declarations": declarations,
    }


def _wrong_signing_private_key() -> Ed25519PrivateKey:
    """A fixed, deterministic Ed25519 private key distinct from
    :func:`tests.fixtures.product_binding`'s own -- test-only, used solely to prove the "wrong
    signer" negative control: a declaration genuinely signed, but not by the real
    project_binding's own registered key, must never authorize."""

    seed = hashlib.sha256(
        b"tests.fixtures.v3_authority_test_material wrong signer -- never the real Project "
        b"Binding's own key"
    ).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def sign_declaration_with_the_wrong_key(declaration: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *declaration* re-signed by a key other than the real project_binding's
    own -- the exact regression the "wrong signer" negative control proves refused."""

    from manosube_agent_civilization.binding.identity import (
        github_projection_grant_declaration_signing_payload,
    )

    message = github_projection_grant_declaration_signing_payload(declaration)
    signature_bytes = _wrong_signing_private_key().sign(message)
    return {
        **declaration,
        "signature": {
            "algorithm": "ed25519",
            # Same key_id as the real project_binding's own key -- this negative control
            # proves the *signature bytes* are checked, not merely the declared key_id.
            "key_id": "AUTH-KEY-0001",
            "value": signature_bytes.hex(),
        },
    }
