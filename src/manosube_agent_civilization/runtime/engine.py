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

from typing import Any

from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
)

from .errors import RuntimeRequirementError
from .identity import (
    runtime_observation_envelope_id,
    runtime_observation_envelope_semantic_fingerprint,
)
from .types import RUNTIME_OBSERVATION_METHODS, RUNTIME_OBSERVATION_OUTCOMES

RUNTIME_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "runtime/"
SCHEMA_VERSION = "0.1"


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

    _validate_canonical_record(
        envelope, "runtime_observation_envelope.schema.json", base=RUNTIME_SCHEMA_BASE
    )
    return envelope
