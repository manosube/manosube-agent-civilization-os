"""Deterministic Runtime identities (Phase 15, Issue #64).

Canonical serialization has one owner in this repository -- ``state.canonicalize`` -- and this
module reads it rather than restating it, exactly as every other owner's own ``identity.py``
already does.

Three distinct identities exist here, deliberately never conflated (Issue #64's own minimum
acceptable after-state item 1 requires a "stable runtime-target and observation-request
identity" distinct from the eventual committed fact):

- :func:`runtime_target_fingerprint` -- *who/what* is being observed: a pure function of the
  declared ``target_identity`` alone (provider, deployment, instance/process/service identity,
  the owning Project Binding, and the immutable deployment identity the target itself must
  match). Stable across repeated observations of the identical target.
- :func:`runtime_observation_request_identity` -- *what was asked*: a pure function of the
  target fingerprint, the closed Observation Boundary, and the instant the observation was
  issued -- computable before the adapter is ever called, independent of whatever outcome it
  returns.
- :func:`runtime_deployment_declaration_signing_payload` /
  :func:`runtime_deployment_declaration_id` /
  :func:`runtime_deployment_declaration_semantic_fingerprint` -- the identity of the *canonical,
  Store-committed deployment declaration* a target's own claimed ``deployment_fingerprint`` must
  match (Phase 15 Structural Review Round 1, P15-R1-F6; signed and status-bound by Round 2,
  P15-R2-F2). Follows the identical single-projection convention the Envelope pair below uses --
  one canonical projection, hashed twice under two different prefixes/encodings, so tampering
  any field is detectable independently of the record's own id -- and, since Round 2,
  additionally the identical *shared-derivation* convention
  :func:`~manosube_agent_civilization.binding.identity.human_grant_declaration_signing_payload`
  and its ``github_projection_grant_declaration`` sibling already establish: the exact canonical
  bytes a genuine Human Authority signature must cover are the exact bytes both digests are
  computed over, so the content address and the signed message can never drift apart into two
  different notions of "what this record declared".
- :func:`runtime_observation_envelope_id` / :func:`runtime_observation_envelope_semantic_fingerprint`
  -- the identity of the *committed fact*: unlike Projection's own deliberately split mapping-
  key/semantic-fingerprint pair (see :mod:`manosube_agent_civilization.projection.identity`'s
  own module docstring), Runtime Observation has no create-once-reuse-after side effect to
  protect -- observing the identical target under the identical Boundary twice is not a
  duplicate external artifact, it is two independent facts, and a genuinely different outcome
  at a later instant must never collide with an earlier one at the same identity. Both digests
  therefore follow the single-projection convention every *other* owner module already uses
  (see ``evidence/identity.py``): one canonical projection, hashed twice under two different
  prefixes/encodings, covering every semantically meaningful field including the observed
  outcome itself.
"""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .errors import RuntimeRequirementError

#: Every field a Runtime Observation Envelope's own identity and semantic fingerprint are
#: computed over -- deliberately the complete record minus the two digest fields themselves,
#: so tampering *any* other field (target, Boundary, outcome, observed content, adapter
#: identity, owning project) is detectable.
ENVELOPE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "target_identity",
    "target_fingerprint",
    "boundary",
    "boundary_fingerprint",
    "observation_request_identity",
    "observed_at",
    "observation_outcome",
    "observed_fields",
    "observed_content_fingerprint",
    "adapter_identity",
    "human_authority_ref",
)


#: The closed tuple of *adopted semantic fields* a Runtime Deployment Declaration's own
#: identity, semantic fingerprint, AND Human Authority signature are all computed over
#: (Round 1, P15-R1-F6; ``status`` added and the signing role established by Round 2,
#: P15-R2-F2) -- deliberately the complete record minus exactly three fields, so tampering
#: *any* other field (the owning Project Binding, the provider/deployment/instance identity,
#: the declared deployment fingerprint, the declaring Human Authority, the declaration's own
#: ACTIVE/REVOKED status, the declaration instant) is detectable by either digest and
#: invalidates the signature.
#:
#: The three exclusions are exactly the three ``binding/identity.py``'s own declaration payload
#: tuples exclude, and for the identical reasons it states: the record's own content address
#: and its own semantic fingerprint (an identity cannot be computed over itself) and
#: ``signature`` (a signature cannot cover its own value). ``declared_at`` deliberately
#: *participates*: the signature is what proves *who* declared this deployment identity, and a
#: signature that never bound *when* would validate identically at any later replay instant.
DEPLOYMENT_DECLARATION_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_ref",
    "provider",
    "deployment_id",
    "instance_identity",
    "deployment_fingerprint",
    "human_authority_ref",
    "status",
    "declared_at",
)


def runtime_target_fingerprint(target_identity: dict[str, Any]) -> str:
    """Return the stable, derived-not-trusted fingerprint of *target_identity* alone -- never
    accepted as a caller-declared value anywhere in this package; always recomputed from the
    real declared fields."""

    return "sha256:" + hashlib.sha256(canonical_json_bytes(target_identity)).hexdigest()


def runtime_observation_boundary_fingerprint(boundary: dict[str, Any]) -> str:
    """Return the derived-not-trusted fingerprint of *boundary* alone."""

    return "sha256:" + hashlib.sha256(canonical_json_bytes(boundary)).hexdigest()


def runtime_observed_content_fingerprint(observed_fields: dict[str, Any]) -> str:
    """Return the derived-not-trusted fingerprint of a route's own already-redacted
    ``observed_fields`` projection alone -- computed only over whatever this package's own
    :mod:`~manosube_agent_civilization.runtime.route` has already bounded to
    ``boundary["permitted_fields"]`` and redacted per ``boundary["redaction_fields"]``, never
    over an adapter's raw, untrusted report directly."""

    return "sha256:" + hashlib.sha256(canonical_json_bytes(observed_fields)).hexdigest()


def runtime_observation_request_identity(
    target_fingerprint: str, boundary_fingerprint: str, issued_at: str
) -> str:
    """Return the stable identity of *this exact observation request* -- computable before the
    adapter is ever called, a pure function of *which target*, *which closed Boundary*, and
    *when the request was issued*, independent of whatever outcome the adapter later returns.
    """

    payload = {
        "target_fingerprint": target_fingerprint,
        "boundary_fingerprint": boundary_fingerprint,
        "issued_at": issued_at,
    }
    return (
        "RUNTIME-OBSERVATION-REQUEST-"
        + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()
    )


def _deployment_declaration_projection(declaration: dict[str, Any]) -> dict[str, Any]:
    missing = [
        field for field in DEPLOYMENT_DECLARATION_SEMANTIC_FIELDS if field not in declaration
    ]
    if missing:
        raise RuntimeRequirementError(
            "runtime_deployment_declaration carries no readable "
            f"{', '.join(missing)} -- its own identity cannot be recomputed"
        )
    return {field: declaration[field] for field in DEPLOYMENT_DECLARATION_SEMANTIC_FIELDS}


def runtime_deployment_declaration_signing_payload(declaration: dict[str, Any]) -> bytes:
    """Return the exact canonical bytes a genuine Human Authority signature over *declaration*
    must cover -- the identical payload :func:`runtime_deployment_declaration_id` and
    :func:`runtime_deployment_declaration_semantic_fingerprint` themselves hash, over
    :data:`DEPLOYMENT_DECLARATION_SEMANTIC_FIELDS` (Phase 15 Structural Review Round 2,
    P15-R2-F2).

    One shared derivation for all three purposes, the identical discipline
    :func:`~manosube_agent_civilization.binding.identity.human_grant_declaration_signing_payload`
    already establishes for a Human Grant Declaration: the content address and the signed
    message are never allowed to drift apart into two different notions of "what this record
    declared", so no field can ever be covered by one and not the other.

    *declaration* need not yet carry its own two digest fields or its own ``signature`` -- none
    of the three is read -- so this same function both mints the payload (before those fields
    exist) and re-derives it for verification (once they do).
    """

    return canonical_json_bytes(_deployment_declaration_projection(declaration))


def runtime_deployment_declaration_id(declaration: dict[str, Any]) -> str:
    """Return the content address of a canonical Runtime Deployment Declaration -- a pure
    function of the complete, real record content, never of a caller-declared value (Phase 15
    Structural Review Round 1, P15-R1-F6), computed over
    :func:`runtime_deployment_declaration_signing_payload`'s own bytes (Round 2, P15-R2-F2)."""

    digest = hashlib.sha256(runtime_deployment_declaration_signing_payload(declaration))
    return "RUNTIME-DEPLOYMENT-DECLARATION-" + digest.hexdigest().upper()


def runtime_deployment_declaration_semantic_fingerprint(declaration: dict[str, Any]) -> str:
    """Return the digest of a canonical Runtime Deployment Declaration's full meaning -- the
    identical payload :func:`runtime_deployment_declaration_id` hashes, under the
    ``sha256:`` encoding every other owner's own semantic fingerprint already uses."""

    digest = hashlib.sha256(runtime_deployment_declaration_signing_payload(declaration))
    return "sha256:" + digest.hexdigest()


def _envelope_projection(envelope: dict[str, Any]) -> dict[str, Any]:
    return {field: envelope[field] for field in ENVELOPE_SEMANTIC_FIELDS}


def runtime_observation_envelope_id(envelope: dict[str, Any]) -> str:
    """Return the content address of a Runtime Observation Envelope -- a pure function of the
    complete, real record content (target, Boundary, outcome, observed content included), never
    of a caller-declared value."""

    projection = _envelope_projection(envelope)
    return (
        "RUNTIME-OBSERVATION-"
        + hashlib.sha256(canonical_json_bytes(projection)).hexdigest().upper()
    )


def runtime_observation_envelope_semantic_fingerprint(envelope: dict[str, Any]) -> str:
    """Return the digest of a Runtime Observation Envelope's full meaning -- the identical
    projection :func:`runtime_observation_envelope_id` hashes, under the ``sha256:`` encoding
    every other owner's own semantic fingerprint already uses, so tampering any field is
    detectable independently of the record's own id."""

    projection = _envelope_projection(envelope)
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()
