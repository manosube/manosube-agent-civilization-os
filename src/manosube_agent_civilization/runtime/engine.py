"""The one Runtime Observation Envelope deriver (Phase 15, Issue #64).

```text
REAL, RESOLVED TARGET IDENTITY + CLOSED BOUNDARY
→ TARGET/BOUNDARY FINGERPRINTS RECOMPUTED (never trusted from a caller)
→ OBSERVATION REQUEST IDENTITY (target + boundary + issued_at)
→ REAL ADAPTER TRANSPORT FACTS, INDEPENDENTLY RECLASSIFIED
→ CANONICAL RUNTIME OBSERVATION ENVELOPE
```

This module builds and schema-validates one Runtime Observation Envelope from already-
resolved, already-verified inputs. It resolves nothing itself, calls no Store, no Boot, no
Authority, and no Adapter -- :mod:`~manosube_agent_civilization.runtime.route` owns every one
of those calls and is the only caller of :func:`derive_runtime_observation_envelope`. This is
the identical "derivation is pure, resolution is the route's job" discipline every other
Kernel engine in this repository already keeps (compare
:func:`~manosube_agent_civilization.projection.engine.derive_projection_envelope`).

Unlike Projection, Runtime Observation is read-only: there is no external artifact ever
created, so there is no intent/materialize-attempt claim-record pair here and no concurrency
barrier to provide -- a Runtime Observation Envelope commits directly, once, from a route that
has already independently reclassified whatever the adapter reported.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
    validate_subrecord as _validate_canonical_subrecord,
)

from .errors import RuntimeRequirementError
from .identity import (
    runtime_observation_envelope_id,
    runtime_observation_envelope_semantic_fingerprint,
)
from .types import RUNTIME_OBSERVATION_METHODS, RUNTIME_OBSERVATION_OUTCOMES

RUNTIME_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "runtime/"
SCHEMA_VERSION = "0.1"

ENVELOPE_SCHEMA_NAME = "runtime_observation_envelope.schema.json"
DEPLOYMENT_DECLARATION_SCHEMA_NAME = "runtime_deployment_declaration.schema.json"
ROOT_ADMISSION_SCHEMA_NAME = "runtime_root_admission.schema.json"


def _require_schema_valid(value: Any, pointer: str, context: str) -> dict[str, Any]:
    """Require *value* to be a mapping that is completely valid against the Runtime
    Observation Envelope schema's own *pointer* subschema, and return it as a plain ``dict``.

    Phase 15 Structural Review Round 1 (P15-R1-F2): before this correction the route checked
    only a handful of fields by hand (an observation method, two non-empty timestamp strings,
    a non-empty ``permitted_fields``) and left every other part of the declared shape --
    endpoint, network scope, timeout, redaction fields, exact key set, timestamp grammar --
    to the schema validation that runs inside :func:`derive_runtime_observation_envelope`,
    which happens *after* ``adapter.observe`` has already run. A malformed Boundary could
    therefore reach a real transport before anything refused it. The complete declared shape
    is now proved here, against the identical canonical schema, before Boot or any adapter is
    reached at all.
    """

    if not isinstance(value, Mapping):
        raise RuntimeRequirementError(f"{context} must be an explicit mapping: {value!r}")
    body = dict(value)
    try:
        _validate_canonical_subrecord(body, ENVELOPE_SCHEMA_NAME, pointer, base=RUNTIME_SCHEMA_BASE)
    except DifferenceValidationError as error:
        raise RuntimeRequirementError(f"{context} is not schema-valid: {error}") from error
    return body


def require_valid_timestamp(value: Any, context: str) -> str:
    """Require *value* to be one canonical UTC ``Z``-suffixed timestamp, in exactly the
    grammar ``common/timestamp.schema.json`` declares.

    P15-R1-F2: ``observed_at`` was previously checked only for being a non-empty,
    locator-free string here, so a timestamp in a form this repository's own canonical grammar
    does not admit reached the adapter and was refused afterwards, at Envelope derivation.
    """

    try:
        _validate_canonical_subrecord(
            value, ENVELOPE_SCHEMA_NAME, "#/properties/observed_at", base=RUNTIME_SCHEMA_BASE
        )
    except DifferenceValidationError as error:
        raise RuntimeRequirementError(
            f"{context} is not a canonical UTC timestamp: {value!r}"
        ) from error
    return str(value)


def parse_utc_instant(value: str, context: str) -> datetime:
    """Parse one canonical UTC ``Z``-suffixed timestamp into a real, comparable instant.

    **The one instant-parsing owner this package has** (Phase 15 Structural Review Round 5,
    P15-R5-F3). Round 1 (P15-R1-F2) established the reasoning below inside ``route.py``'s own
    private ``_instant`` helper; Round 5 found the *identical* unsoundness still present in
    ``deployment_registry.py``, which ordered a declaration's own validity window by comparing
    two timestamp **strings**. The correction is deliberately not a second helper: the adopted
    contract's own wording is that "no second timestamp grammar or Runtime-specific time owner
    may be created", so the existing parser moved here, to the module both the route and the
    committer already depend on, and every timestamp-window comparison in this package now goes
    through this one function.

    P15-R1-F2's reasoning, unchanged and now shared: string comparison is *not* sound over this
    schema's own timestamp grammar (``common/timestamp.schema.json`` admits an optional
    fractional part), and the failure is not merely cosmetic --
    ``"2026-01-01T00:00:00.5Z" < "2026-01-01T00:00:00Z"`` is ``True`` lexicographically (``.``
    sorts below ``Z``) while being ``False`` chronologically, so a lexicographic window check
    *accepts* an observation half a second past a whole-second ``expires_at``, and *refuses* one
    half a second after a whole-second ``issued_at``. Both directions are wrong; only real
    instants compare correctly. The identical inversion made a lexicographic
    ``valid_from``/``valid_until`` check accept an inverted window and refuse a genuine one.

    This function reads no clock. It converts a declared timestamp into a comparable instant and
    nothing else; *which* instants a caller then compares -- two declared bounds against each
    other, or a declared bound against an observation's own ``observed_at`` -- stays that
    caller's own question.
    """

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise RuntimeRequirementError(
            f"{context} is not a readable UTC instant: {value!r}"
        ) from error
    if parsed.tzinfo is None:
        raise RuntimeRequirementError(f"{context} carries no UTC designator: {value!r}")
    return parsed


def require_valid_target_identity(target_identity: Any) -> dict[str, Any]:
    """Return *target_identity* as a plain ``dict``, proved completely valid against
    ``runtime_observation_envelope.schema.json``'s own ``$defs/target_identity`` -- including
    the ``deployment_declaration_ref`` P15-R1-F6 made required."""

    return _require_schema_valid(target_identity, "#/$defs/target_identity", "target_identity")


def require_valid_boundary(boundary: Any) -> dict[str, Any]:
    """Return *boundary* as a plain ``dict``, proved completely valid against
    ``runtime_observation_envelope.schema.json``'s own ``$defs/boundary`` -- exact key set,
    endpoint, permitted fields, time-window timestamp grammar, network scope, timeout, and
    redaction fields all included."""

    checked = _require_schema_valid(boundary, "#/$defs/boundary", "boundary")
    if checked.get("observation_method") not in RUNTIME_OBSERVATION_METHODS:
        raise RuntimeRequirementError(
            f"boundary.observation_method is not recognized: {checked.get('observation_method')!r}"
        )
    return checked


def require_valid_deployment_declaration(declaration: Any) -> dict[str, Any]:
    """Return *declaration* as a plain ``dict``, proved completely valid against the canonical
    ``runtime_deployment_declaration.schema.json`` (P15-R1-F6) -- a Store-resolved record is
    never trusted on shape alone, exactly as no caller-supplied record ever is."""

    if not isinstance(declaration, Mapping):
        raise RuntimeRequirementError(
            f"runtime_deployment_declaration must be an explicit mapping: {declaration!r}"
        )
    body = dict(declaration)
    try:
        _validate_canonical_record(
            body, DEPLOYMENT_DECLARATION_SCHEMA_NAME, base=RUNTIME_SCHEMA_BASE
        )
    except DifferenceValidationError as error:
        raise RuntimeRequirementError(
            f"resolved runtime_deployment_declaration is not schema-valid: {error}"
        ) from error
    return body


def require_valid_root_admission(admission: Any) -> dict[str, Any]:
    """Return *admission* as a plain ``dict``, proved completely valid against the canonical
    ``runtime_root_admission.schema.json`` (Phase 15 Structural Review Round 3, P15-R3-F1) --
    a Store-resolved record is never trusted on shape alone, exactly as no caller-supplied
    record ever is, and exactly as :func:`require_valid_deployment_declaration` already
    requires for this package's own sibling record kind."""

    if not isinstance(admission, Mapping):
        raise RuntimeRequirementError(
            f"runtime_root_admission must be an explicit mapping: {admission!r}"
        )
    body = dict(admission)
    try:
        _validate_canonical_record(body, ROOT_ADMISSION_SCHEMA_NAME, base=RUNTIME_SCHEMA_BASE)
    except DifferenceValidationError as error:
        raise RuntimeRequirementError(
            f"resolved runtime_root_admission is not schema-valid: {error}"
        ) from error
    return body


def derive_runtime_observation_envelope(
    *,
    project_id: str,
    target_identity: dict[str, Any],
    target_fingerprint: str,
    boundary: dict[str, Any],
    boundary_fingerprint: str,
    observation_request_identity: str,
    observed_at: str,
    observation_outcome: str,
    observed_fields: dict[str, Any] | None,
    observed_content_fingerprint: str | None,
    adapter_identity: dict[str, Any],
    human_authority_ref: dict[str, Any],
) -> dict[str, Any]:
    """Return one canonical, schema-valid Runtime Observation Envelope record.

    Every argument must already be real: *target_fingerprint*, *boundary_fingerprint*, and
    *observation_request_identity* must already be recomputed by the caller from the real
    *target_identity*/*boundary* (this function does not recompute any of them -- it only
    asserts the assembled record is internally self-consistent and schema-valid), and
    *observation_outcome*/*observed_fields*/*observed_content_fingerprint* must already be the
    route's own independently-reclassified outcome, never an adapter's raw, untrusted report.
    This function performs no Store I/O of any kind and reaches no Adapter.
    """

    if boundary.get("observation_method") not in RUNTIME_OBSERVATION_METHODS:
        raise RuntimeRequirementError(
            "boundary names an unrecognized observation_method: "
            f"{boundary.get('observation_method')!r}"
        )
    if observation_outcome not in RUNTIME_OBSERVATION_OUTCOMES:
        raise RuntimeRequirementError(
            f"observation_outcome is not a recognized outcome: {observation_outcome!r}"
        )

    envelope = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "target_identity": dict(target_identity),
        "target_fingerprint": target_fingerprint,
        "boundary": dict(boundary),
        "boundary_fingerprint": boundary_fingerprint,
        "observation_request_identity": observation_request_identity,
        "observed_at": observed_at,
        "observation_outcome": observation_outcome,
        "observed_fields": observed_fields,
        "observed_content_fingerprint": observed_content_fingerprint,
        "adapter_identity": dict(adapter_identity),
        "human_authority_ref": dict(human_authority_ref),
    }
    envelope["runtime_observation_envelope_id"] = runtime_observation_envelope_id(envelope)
    envelope["runtime_observation_semantic_fingerprint"] = (
        runtime_observation_envelope_semantic_fingerprint(envelope)
    )

    _validate_canonical_record(envelope, ENVELOPE_SCHEMA_NAME, base=RUNTIME_SCHEMA_BASE)
    return envelope
