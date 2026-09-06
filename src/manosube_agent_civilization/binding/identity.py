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
