"""Deterministic Projection Envelope identities (Phase 14, Issue #62).

Canonical serialization has one owner in this repository -- ``state.canonicalize`` -- and
this module reads it rather than restating it, exactly as every other owner's own
``identity.py`` already does. What is defined here is only *which payload* a Projection
Envelope's two digests are each computed over.

**Frozen semantic decision (deliberate deviation from the single-projection convention every
other owner module uses):** every other Kernel/adapter record content-addresses its ``_id``
and its own ``_semantic_fingerprint`` over the *identical* field projection (see
``evidence/identity.py``). A Projection Envelope cannot: Issue #62's own minimum-acceptable-
after-state requires re-projecting the *same* canonical subject, at the *same* fingerprint,
kind and target, to reuse the *same* projection identity regardless of payload, while a
*different* payload at that identical identity must fail closed as
``CONFLICTING_PROJECTION_PAYLOAD`` rather than silently minting a second identity next to the
first. That is only expressible if the identity that is looked up (:func:`projection_mapping_key`
/ :func:`projection_envelope_id`) is a function of the *mapping key* alone -- subject
reference, subject fingerprint, projection kind, and target repository -- while the
*semantic* fingerprint used for tamper/mutation detection after persistence
(:func:`projection_envelope_semantic_fingerprint`) additionally covers the payload. The two
are therefore deliberately different projections of the same record, not, as elsewhere, two
encodings of the identical one.
"""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

#: What identifies *which external GitHub target this canonical subject is projected to* --
#: the mapping key a replay must look up before ever calling
#: :meth:`~manosube_agent_civilization.projection.types.GitHubAdapter.materialize` again.
#: Deliberately excludes ``projection_payload``/``projection_payload_fingerprint``: two
#: payloads for the identical subject/kind/target are the *same* projection identity,
#: distinguished only by conflict, never by address (see the module docstring above).
MAPPING_KEY_FIELDS: tuple[str, ...] = (
    "subject_ref",
    "subject_fingerprint",
    "projection_kind",
    "target_repository",
)

#: What a Projection Envelope's own semantic fingerprint additionally covers, beyond the
#: mapping key: the payload actually materialized under that identity. Tampering the
#: payload of an already-committed Envelope (impossible through this package's own public
#: route, since Envelopes are immutable and never rewritten in place) would still be
#: detectable through this digest, exactly as every other record's own semantic fingerprint
#: detects tampering of its own body.
SEMANTIC_FIELDS: tuple[str, ...] = (*MAPPING_KEY_FIELDS, "projection_payload_fingerprint")


def _projection(envelope: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: envelope[field] for field in fields}


def projection_mapping_key(
    subject_ref: dict[str, Any],
    subject_fingerprint: str,
    projection_kind: str,
    target_repository: dict[str, Any],
) -> str:
    """Return the stable projection identity for one (subject, kind, target) mapping slot,
    computable *before* any external artifact exists -- the lookup key a route uses to
    decide reuse versus first materialization, without yet knowing ``external_artifact_ref``.
    """

    payload = {
        "subject_ref": subject_ref,
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": target_repository,
    }
    return "PROJECTION-" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def projection_envelope_id(envelope: dict[str, Any]) -> str:
    """Return the content address of a materialized Projection Envelope record.

    Identical to :func:`projection_mapping_key` applied to the envelope's own declared
    mapping-key fields -- a committed Envelope's own ``projection_envelope_id`` is always
    exactly the mapping key a fresh lookup over the same subject/kind/target would compute,
    which is what makes reuse-by-lookup possible at all.
    """

    projection = _projection(envelope, MAPPING_KEY_FIELDS)
    return "PROJECTION-" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest().upper()


def projection_envelope_semantic_fingerprint(envelope: dict[str, Any]) -> str:
    """Return the digest of a Projection Envelope's full meaning: mapping key plus payload."""

    projection = _projection(envelope, SEMANTIC_FIELDS)
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def projection_payload_fingerprint(payload: dict[str, Any]) -> str:
    """Return the deterministic digest of a caller-supplied ``projection_payload``.

    Always recomputed from the real payload a caller supplies to
    :func:`~manosube_agent_civilization.projection.route.project_to_github` -- a caller-
    supplied fingerprint is never accepted or trusted (the identical "derived, never
    declared" discipline every other identity function in this package already applies).
    """

    return "sha256:" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
