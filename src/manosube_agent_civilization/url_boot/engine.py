"""The one URL Source Observation Envelope deriver (Phase 17, Issue #69).

```text
REAL, RESOLVED REQUESTED SOURCE IDENTITY + CLOSED BOUNDARY
→ SOURCE/BOUNDARY FINGERPRINTS RECOMPUTED (never trusted from a caller)
→ SOURCE REQUEST IDENTITY (requested source + boundary + issued_at)
→ REAL ADAPTER TRANSPORT FACTS (already per-hop reauthorized by the adapter itself)
→ CANONICAL URL SOURCE OBSERVATION ENVELOPE
```

This module builds and schema-validates one URL Source Observation Envelope from already-
resolved, already-verified inputs. It resolves nothing itself, calls no Store, no Boot, no
Authority, and no Adapter -- :mod:`~manosube_agent_civilization.url_boot.route` owns every one
of those calls and is the only caller of :func:`derive_url_source_observation_envelope`. This
is the identical "derivation is pure, resolution is the route's job" discipline every other
Kernel engine in this repository already keeps.

Like Runtime Observation, a URL Source Observation is read-only: there is no external artifact
ever created, so there is no intent/materialize-attempt claim-record pair here and no
concurrency barrier to provide -- a URL Source Observation Envelope commits directly, once,
from a route that has already independently trusted only what its own network-scope checks and
the adapter's own honest per-hop-reauthorized report together establish.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
    validate_subrecord as _validate_canonical_subrecord,
)

from .errors import UrlBootRequirementError
from .identity import (
    url_source_observation_envelope_id,
    url_source_observation_envelope_semantic_fingerprint,
)
from .types import URL_FETCH_METHODS, URL_FETCH_OUTCOMES

URL_BOOT_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "url_boot/"
SCHEMA_VERSION = "0.1"

ENVELOPE_SCHEMA_NAME = "url_source_observation_envelope.schema.json"


def _require_schema_valid(value: Any, pointer: str, context: str) -> dict[str, Any]:
    """Require *value* to be a mapping that is completely valid against the URL Source
    Observation Envelope schema's own *pointer* subschema, and return it as a plain ``dict``.

    The complete declared shape is proved here, against the canonical schema, before Boot or
    any adapter is ever reached -- the identical discipline Runtime's own P15-R1-F2 correction
    established, applied here from the start rather than corrected into later.
    """

    if not isinstance(value, dict):
        raise UrlBootRequirementError(f"{context} must be an explicit mapping: {value!r}")
    body = dict(value)
    try:
        _validate_canonical_subrecord(
            body, ENVELOPE_SCHEMA_NAME, pointer, base=URL_BOOT_SCHEMA_BASE
        )
    except DifferenceValidationError as error:
        raise UrlBootRequirementError(f"{context} is not schema-valid: {error}") from error
    return body


def require_valid_timestamp(value: Any, context: str) -> str:
    """Require *value* to be one canonical UTC ``Z``-suffixed timestamp, in exactly the
    grammar ``common/timestamp.schema.json`` declares."""

    try:
        _validate_canonical_subrecord(
            value, ENVELOPE_SCHEMA_NAME, "#/properties/retrieved_at", base=URL_BOOT_SCHEMA_BASE
        )
    except DifferenceValidationError as error:
        raise UrlBootRequirementError(
            f"{context} is not a canonical UTC timestamp: {value!r}"
        ) from error
    return str(value)


def parse_utc_instant(value: str, context: str) -> datetime:
    """Parse one canonical UTC ``Z``-suffixed timestamp into a real, comparable instant --
    **the one instant-parsing owner this package has**, exactly the discipline Runtime's own
    P15-R1-F2/P15-R5-F3 correction established: lexicographic string comparison over this
    schema's own timestamp grammar (which admits an optional fractional part) is unsound, so
    every timestamp-window comparison in this package goes through this one function, never a
    second, package-local reimplementation."""

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise UrlBootRequirementError(
            f"{context} is not a readable UTC instant: {value!r}"
        ) from error
    if parsed.tzinfo is None:
        raise UrlBootRequirementError(f"{context} carries no UTC designator: {value!r}")
    return parsed


def require_valid_source_identity(source_identity: Any) -> dict[str, Any]:
    """Return *source_identity* as a plain ``dict``, proved completely valid against
    ``url_source_observation_envelope.schema.json``'s own ``$defs/source_identity``."""

    return _require_schema_valid(
        source_identity, "#/$defs/source_identity", "requested_source_identity"
    )


def require_valid_boundary(boundary: Any) -> dict[str, Any]:
    """Return *boundary* as a plain ``dict``, proved completely valid against
    ``url_source_observation_envelope.schema.json``'s own ``$defs/boundary`` -- exact key set,
    network scope, redirect policy, timeout, max response bytes, admitted content types,
    permitted fields, time-window timestamp grammar, redaction fields, and the closed
    ``credentials_permitted`` field all included."""

    checked = _require_schema_valid(boundary, "#/$defs/boundary", "boundary")
    if checked.get("fetch_method") not in URL_FETCH_METHODS:
        raise UrlBootRequirementError(
            f"boundary.fetch_method is not recognized: {checked.get('fetch_method')!r}"
        )
    return checked


def derive_url_source_observation_envelope(
    *,
    project_id: str,
    project_binding_ref: dict[str, Any],
    boot_state_fingerprint: dict[str, Any],
    requested_source_identity: dict[str, Any],
    requested_source_fingerprint: str,
    effective_source_identity: dict[str, Any],
    effective_source_fingerprint: str,
    boundary: dict[str, Any],
    boundary_fingerprint: str,
    source_request_identity: str,
    retrieved_at: str,
    fetch_outcome: str,
    response_status: int,
    redirect_hop_count: int,
    resolution_provenance: list[dict[str, Any]],
    observed_fields: dict[str, Any],
    observed_content_fingerprint: str,
    adapter_identity: dict[str, Any],
    human_authority_ref: dict[str, Any],
) -> dict[str, Any]:
    """Return one canonical, schema-valid URL Source Observation Envelope record.

    **Structural Review Round 1 (P17-R1-F1) correction.** This function is now reachable for
    exactly one *fetch_outcome*: ``"OBSERVED"``. P17-C7 requires that no failed or refused fetch
    ever mutate canonical State; the route enforces that by never calling this function, or its
    own committer, for any other outcome (see ``route.py``'s own module docstring) -- and this
    function itself refuses, structurally, to derive an envelope for anything else, so the
    invariant holds even if some future caller forgets the route's own discipline.

    Every argument must already be real: *requested_source_fingerprint*,
    *effective_source_fingerprint*, *boundary_fingerprint*, and *source_request_identity* must
    already be recomputed by the caller from the real identities/boundary (this function does
    not recompute any of them -- it only asserts the assembled record is internally
    self-consistent and schema-valid), and *observed_fields*/*observed_content_fingerprint* must
    already be the route's own bounded, redacted projection of a genuinely reached response
    (P17-R1-F2: never the adapter's own unclassified report). *project_binding_ref* and
    *boot_state_fingerprint* are the exact Project Binding / Boot-observed State identity this
    call's own Boot restored (P17-R1-F5); *resolution_provenance* is the ordered, per-(host,
    port) DNS resolution this route itself admitted across every hop of this successful fetch
    (P17-R1-F4). This function performs no Store I/O of any kind, opens no socket, and reaches
    no Adapter.
    """

    if boundary.get("fetch_method") not in URL_FETCH_METHODS:
        raise UrlBootRequirementError(
            f"boundary names an unrecognized fetch_method: {boundary.get('fetch_method')!r}"
        )
    if fetch_outcome != "OBSERVED":
        raise UrlBootRequirementError(
            "a url_source_observation_envelope may only ever be derived for fetch_outcome="
            f"'OBSERVED' (P17-C7) -- got {fetch_outcome!r}: every other outcome is bounded, "
            "ephemeral failure evidence that commits nothing"
        )
    if fetch_outcome not in URL_FETCH_OUTCOMES:
        raise UrlBootRequirementError(
            f"fetch_outcome is not a recognized outcome: {fetch_outcome!r}"
        )

    envelope = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "project_binding_ref": dict(project_binding_ref),
        "boot_state_fingerprint": dict(boot_state_fingerprint),
        "requested_source_identity": dict(requested_source_identity),
        "requested_source_fingerprint": requested_source_fingerprint,
        "effective_source_identity": dict(effective_source_identity),
        "effective_source_fingerprint": effective_source_fingerprint,
        "boundary": dict(boundary),
        "boundary_fingerprint": boundary_fingerprint,
        "source_request_identity": source_request_identity,
        "retrieved_at": retrieved_at,
        "fetch_outcome": fetch_outcome,
        "response_status": response_status,
        "redirect_hop_count": redirect_hop_count,
        "resolution_provenance": [dict(hop) for hop in resolution_provenance],
        "observed_fields": observed_fields,
        "observed_content_fingerprint": observed_content_fingerprint,
        "adapter_identity": dict(adapter_identity),
        "human_authority_ref": dict(human_authority_ref),
    }
    envelope["url_source_observation_envelope_id"] = url_source_observation_envelope_id(envelope)
    envelope["url_source_observation_semantic_fingerprint"] = (
        url_source_observation_envelope_semantic_fingerprint(envelope)
    )

    _validate_canonical_record(envelope, ENVELOPE_SCHEMA_NAME, base=URL_BOOT_SCHEMA_BASE)
    return envelope


__all__ = [
    "ENVELOPE_SCHEMA_NAME",
    "SCHEMA_VERSION",
    "URL_BOOT_SCHEMA_BASE",
    "derive_url_source_observation_envelope",
    "parse_utc_instant",
    "require_valid_boundary",
    "require_valid_source_identity",
    "require_valid_timestamp",
]
