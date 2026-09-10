"""Deterministic URL Boot identities (Phase 17, Issue #69).

Canonical serialization has one owner in this repository -- ``state.canonicalize`` -- and this
module reads it rather than restating it, exactly as every other owner's own ``identity.py``
already does.

Four distinct identities exist here, deliberately never conflated (P17-C1/P17-C6's own required
separation of "requested" from "effective" from "committed fact"):

- :func:`url_source_fingerprint` -- *what was asked for*: a pure function of one canonical,
  fully decomposed ``source_identity`` (scheme, host, port, path, query, fragment) alone.
  Applied twice by the route -- once to the caller's own *requested* identity, once to whatever
  *effective* identity the adapter actually reached after redirects -- so the two can be
  compared and both independently persisted, never conflated into one "the URL" field the way a
  caller-supplied string would be.
- :func:`url_boundary_fingerprint` -- the closed fetch Boundary's own identity.
- :func:`url_source_request_identity` -- *what was asked, as one request*: a pure function of
  the requested source fingerprint, the Boundary fingerprint, and the instant the request was
  issued -- computable before the adapter is ever called, independent of whatever outcome it
  returns.
- :func:`url_observed_content_fingerprint` -- the fingerprint of the route's own already-bounded/
  redacted ``observed_fields``, never the adapter's raw, unbounded response body.
- :func:`url_source_observation_envelope_id` / :func:`url_source_observation_envelope_semantic_fingerprint`
  -- the identity of the *committed fact*: a single-projection, full-content digest (like
  Runtime's own Observation Envelope and Evidence's own ``evidence_id``), because a URL Source
  Observation has no create-once-reuse-after side effect to protect -- observing the identical
  source under the identical Boundary twice is not a duplicate to deduplicate, it is two
  independent facts about the world at two different instants.

Every one of these is a pure function of already-validated content. None reads a clock, opens a
socket, or resolves a DNS name -- this module has no I/O of any kind.
"""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

#: Every field a URL Source Observation Envelope's own identity and semantic fingerprint are
#: computed over -- the complete record minus the two digest fields themselves.
ENVELOPE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "project_binding_ref",
    "boot_state_fingerprint",
    "requested_source_identity",
    "requested_source_fingerprint",
    "effective_source_identity",
    "effective_source_fingerprint",
    "boundary",
    "boundary_fingerprint",
    "source_request_identity",
    "retrieved_at",
    "fetch_outcome",
    "response_status",
    "redirect_hop_count",
    "resolution_provenance",
    "observed_fields",
    "observed_content_fingerprint",
    "adapter_identity",
    "human_authority_ref",
)


def _projection(
    record: dict[str, Any], fields: tuple[str, ...], record_kind: str
) -> dict[str, Any]:
    missing = [field for field in fields if field not in record]
    if missing:
        raise KeyError(
            f"{record_kind} carries no readable {', '.join(missing)} -- its own identity cannot "
            "be recomputed"
        )
    return {field: record[field] for field in fields}


def url_source_fingerprint(source_identity: dict[str, Any]) -> str:
    """The digest of one canonical, fully decomposed URL source identity."""

    return "sha256:" + hashlib.sha256(canonical_json_bytes(source_identity)).hexdigest()


def url_boundary_fingerprint(boundary: dict[str, Any]) -> str:
    """The digest of one closed fetch Boundary."""

    return "sha256:" + hashlib.sha256(canonical_json_bytes(boundary)).hexdigest()


def url_source_request_identity(
    requested_source_fingerprint_value: str, boundary_fingerprint_value: str, issued_at: str
) -> str:
    """The content address of one URL source retrieval request -- computable before the adapter
    is ever called."""

    payload = {
        "requested_source_fingerprint": requested_source_fingerprint_value,
        "boundary_fingerprint": boundary_fingerprint_value,
        "issued_at": issued_at,
    }
    return (
        "URL-SOURCE-OBSERVATION-REQUEST-"
        + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()
    )


def url_observed_content_fingerprint(observed_fields: dict[str, Any] | None) -> str | None:
    """The digest of the route's own already-bounded ``observed_fields``, never the adapter's
    raw response body -- ``None`` when nothing was observed."""

    if observed_fields is None:
        return None
    return "sha256:" + hashlib.sha256(canonical_json_bytes(observed_fields)).hexdigest()


def url_source_observation_envelope_id(envelope: dict[str, Any]) -> str:
    """The content address of a URL Source Observation Envelope -- a pure function of the
    complete, real record content, never of a caller-declared value."""

    projection = _projection(envelope, ENVELOPE_SEMANTIC_FIELDS, "url_source_observation_envelope")
    return (
        "URL-SOURCE-OBSERVATION-"
        + hashlib.sha256(canonical_json_bytes(projection)).hexdigest().upper()
    )


def url_source_observation_envelope_semantic_fingerprint(envelope: dict[str, Any]) -> str:
    """The digest of a URL Source Observation Envelope's full meaning -- the identical
    projection :func:`url_source_observation_envelope_id` hashes."""

    projection = _projection(envelope, ENVELOPE_SEMANTIC_FIELDS, "url_source_observation_envelope")
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()
