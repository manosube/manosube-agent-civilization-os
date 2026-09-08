"""Deterministic Project Binding identity.

Canonical serialization has one owner in this repository -- ``state.canonicalize`` -- and
the repo-wide content-address convention has one owner, ``difference.canonical.
content_address``/``canonical_bytes``. This module reads both rather than restating them,
exactly as ``reflow/identity.py`` does for Reflow's own identities.

``project_binding_id`` is content-addressed from the Binding's own adopted semantic fields
(Issue #43 frozen decision 4): ``project_id``, the referenced Objective Revision, the
declared Boundary, the referenced Authority policy, the Source Registrations, the Command
Policy, and the Secret Exclusion Policy. ``schema_version`` is included because a future
schema revision that changes accepted semantics must mint a different identity for what is,
by construction, a different declaration. ``bound_at`` is excluded -- it is the instant the
declaration was adopted, not part of what was adopted, exactly as Reflow's own
``closure_evaluation_id`` excludes the later-stamped ``reflow_transition_ref`` receipt.
"""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.difference.canonical import canonical_bytes

from .errors import BindingIdentityError

#: The closed payload fields ``project_binding_id`` is computed over, in this exact order.
#: ``project_binding_id`` itself and ``bound_at`` are excluded -- see module docstring.
_IDENTITY_PAYLOAD_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "objective_revision_ref",
    "boundary",
    "authority_policy_ref",
    "source_registrations",
    "command_policy",
    "secret_exclusion_policy",
    "human_authority_ref",
    "human_authority_signing_key",
)


def project_binding_id(record: dict[str, Any]) -> str:
    """Return the ``PROJBIND-`` content address of *record*'s own adopted semantic fields.

    *record* need not yet carry ``project_binding_id``/``bound_at`` -- only the identity
    payload fields are read, so this same function both mints the identity (before those
    two fields exist) and re-derives it for verification (once they do).
    """

    payload = {key: record[key] for key in _IDENTITY_PAYLOAD_FIELDS}
    digest = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    return "PROJBIND-" + digest.upper()


def verify_project_binding_identity(record: dict[str, Any]) -> None:
    """Recompute ``project_binding_id`` from *record*'s own semantic fields and require it
    to equal the id the record itself claims.

    This is the identity *reverification* step Issue #43's own canonical successful route
    requires (item 3): never trust a caller-claimed id at face value, even one this same
    module's own :func:`project_binding_id` just minted -- recompute it from the assembled
    record's own fields and compare, the identical self-consistency check Reflow's own
    genesis lifecycle event admission already applies to a caller-supplied body.
    """

    claimed = record.get("project_binding_id")
    recomputed = project_binding_id(record)
    if claimed != recomputed:
        raise BindingIdentityError(
            f"project_binding_id does not reproduce from its own declared fields: "
            f"claimed {claimed!r}, recomputed {recomputed!r}"
        )


#: The closed payload fields ``human_grant_declaration_id`` is computed over, AND the exact
#: canonical payload the Human's own signature authenticates (Structural Review Round 5-R1,
#: Issue #51, P13-R5-R1, superseding Round 5's own narrower set) -- SHUKOU's own R5-R1
#: adoption explicitly names every one of these as a field the declaration must "completely
#: bind": the grant's own canonical id (``grant_ref``), ``project_id``, ``project_binding_id``,
#: the Human Authority reference (``declared_by``), ``requirement_id``, ``selection_id``,
#: ``verifier_identity``, ``permitted_boundary``, ``status``, and the declaration/revocation
#: instant itself. Unlike Round 5's own ``project_binding_id``-modeled convention above (which
#: excludes ``bound_at``), ``declared_at`` now participates: the signature is what proves
#: *who* declared this, and a signature that never bound *when* would validate identically at
#: any later replay instant -- it is Human Authority provenance, not a Store-write receipt
#: timestamp, so it belongs inside what is signed, not outside it (compare ``bound_at`` above,
#: which really is only the latter). ``human_grant_declaration_id`` itself and ``signature``
#: are excluded -- an identity cannot be computed over itself, and the signature cannot cover
#: its own value either.
_HUMAN_GRANT_DECLARATION_IDENTITY_PAYLOAD_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_id",
    "grant_ref",
    "declared_by",
    "requirement_id",
    "selection_id",
    "verifier_identity",
    "permitted_boundary",
    "status",
    "declared_at",
)


def human_grant_declaration_signing_payload(record: dict[str, Any]) -> bytes:
    """Return the exact canonical bytes a genuine Human signature over *record* must cover --
    the identical payload :func:`human_grant_declaration_id` itself hashes, over
    :data:`_HUMAN_GRANT_DECLARATION_IDENTITY_PAYLOAD_FIELDS`. One shared derivation for both
    purposes: the content address and the signed message are never allowed to drift apart
    into two different notions of "what this record adopted"."""

    payload = {key: record[key] for key in _HUMAN_GRANT_DECLARATION_IDENTITY_PAYLOAD_FIELDS}
    return canonical_bytes(payload)


def human_grant_declaration_id(record: dict[str, Any]) -> str:
    """Return the ``HGD-`` content address of *record*'s own adopted semantic fields
    (Structural Review Round 5, P13-R5, payload widened Round 5-R1, P13-R5-R1) -- the
    identical content-addressing convention :func:`project_binding_id` already uses, over
    :func:`human_grant_declaration_signing_payload`'s own bytes."""

    digest = hashlib.sha256(human_grant_declaration_signing_payload(record)).hexdigest()
    return "HGD-" + digest.upper()


def verify_human_grant_declaration_identity(record: dict[str, Any]) -> None:
    """Recompute ``human_grant_declaration_id`` from *record*'s own semantic fields and
    require it to equal the id the record itself claims -- the identical self-consistency
    check :func:`verify_project_binding_identity` already applies, over
    :func:`human_grant_declaration_id`."""

    claimed = record.get("human_grant_declaration_id")
    recomputed = human_grant_declaration_id(record)
    if claimed != recomputed:
        raise BindingIdentityError(
            f"human_grant_declaration_id does not reproduce from its own declared fields: "
            f"claimed {claimed!r}, recomputed {recomputed!r}"
        )


#: The identical shape of anchor Phase 14 Structural Review Round 2 (Issue #62, P14-R2-F1)
#: requires for ``github_projection_grant``: a Human Grant Declaration sibling record kind
#: whose own restated fields are the projection grant's own semantic fields
#: (``subject_ref``/``subject_fingerprint``/``projection_kind``/``target_repository``/
#: ``payload_fingerprint``/``permitted_action``) rather than a verifier selection's. A separate
#: record kind, not a reuse of ``human_grant_declaration`` itself, because that schema's own
#: ``grant_ref.kind`` is ``const``-pinned to ``"verifier_selection_grant"`` and its restated
#: fields are shaped for a different question entirely -- exactly the identical
#: ``verifier_selection_grant``/``github_projection_grant`` sibling-not-shared-owner relationship
#: this repository already has one layer up, in ``authority/conformance.py``'s own
#: ``RECORD_TYPES``.
_GITHUB_PROJECTION_GRANT_DECLARATION_IDENTITY_PAYLOAD_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_id",
    "grant_ref",
    "declared_by",
    "subject_ref",
    "subject_fingerprint",
    "projection_kind",
    "target_repository",
    "payload_fingerprint",
    "permitted_action",
    "status",
    "declared_at",
)


def github_projection_grant_declaration_signing_payload(record: dict[str, Any]) -> bytes:
    """Return the exact canonical bytes a genuine Human signature over *record* must cover --
    the identical payload :func:`github_projection_grant_declaration_id` itself hashes, over
    :data:`_GITHUB_PROJECTION_GRANT_DECLARATION_IDENTITY_PAYLOAD_FIELDS`. The identical
    shared-derivation discipline :func:`human_grant_declaration_signing_payload` already
    establishes: the content address and the signed message are never allowed to drift apart."""

    payload = {
        key: record[key] for key in _GITHUB_PROJECTION_GRANT_DECLARATION_IDENTITY_PAYLOAD_FIELDS
    }
    return canonical_bytes(payload)


def github_projection_grant_declaration_id(record: dict[str, Any]) -> str:
    """Return the ``GH-PROJ-DECL-`` content address of *record*'s own adopted semantic fields
    (Phase 14 Structural Review Round 2, P14-R2-F1) -- the identical content-addressing
    convention :func:`human_grant_declaration_id` already uses, over
    :func:`github_projection_grant_declaration_signing_payload`'s own bytes."""

    digest = hashlib.sha256(github_projection_grant_declaration_signing_payload(record)).hexdigest()
    return "GH-PROJ-DECL-" + digest.upper()


def verify_github_projection_grant_declaration_identity(record: dict[str, Any]) -> None:
    """Recompute ``github_projection_grant_declaration_id`` from *record*'s own semantic
    fields and require it to equal the id the record itself claims -- the identical
    self-consistency check :func:`verify_human_grant_declaration_identity` already applies."""

    claimed = record.get("github_projection_grant_declaration_id")
    recomputed = github_projection_grant_declaration_id(record)
    if claimed != recomputed:
        raise BindingIdentityError(
            "github_projection_grant_declaration_id does not reproduce from its own declared "
            f"fields: claimed {claimed!r}, recomputed {recomputed!r}"
        )
