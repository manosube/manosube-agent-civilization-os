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
- :func:`runtime_root_admission_signing_payload` / :func:`runtime_root_admission_id` /
  :func:`runtime_root_admission_semantic_fingerprint` -- the identity of the *canonical,
  Store-committed root admission record* a trusted runtime provisioning call must present, and
  which :func:`~manosube_agent_civilization.runtime.bootstrap.
  compose_trusted_runtime_deployment_authority` verifies against an **externally supplied** trust
  anchor public key rather than against anything resolvable inside the Store being admitted
  (Phase 15 Structural Review Round 3, P15-R3-F1). Follows the identical shared-derivation
  convention the deployment declaration below already uses.
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
#:
#: ``valid_from``/``valid_until`` were added by Round 3 (P15-R3-F2) and *participate* for the
#: identical reason ``declared_at`` does: a declaration whose validity window were not covered
#: by its own content address and its own Human Authority signature could be silently re-dated
#: after signing, which is exactly what a validity window exists to prevent.
#:
#: ``generation``/``predecessor_ref`` were added by Round 4 (P15-R4-F2) and *participate* for a
#: reason the earlier additions only foreshadow: they are what makes a declaration's own place in
#: its target's transition chain a **signed** claim rather than a committer's bookkeeping. A
#: successor states, under the Human Authority's own signature, exactly which declaration it
#: replaces and exactly which generation it occupies; if either were outside the payload, a
#: committer (or anyone able to write a Store record) could re-point an already-signed body at a
#: different predecessor, and the "monotonic chain" would be a convention rather than a fact. It
#: is also precisely why the committer's concurrency loser **fails closed instead of retrying**
#: (``10_RUNTIME/RUNTIME_CONTRACT.md`` §13.3): adjusting a losing proposal to the new head would
#: require a new signature over a new payload, which only the Human Authority can produce.
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
    "valid_from",
    "valid_until",
    "generation",
    "predecessor_ref",
)


#: The closed tuple of *adopted semantic fields* a Runtime Root Admission's own identity,
#: semantic fingerprint, AND deployment-boundary trust-anchor signature are all computed over
#: (Phase 15 Structural Review Round 3, P15-R3-F1) -- the complete record minus exactly the
#: same three fields :data:`DEPLOYMENT_DECLARATION_SEMANTIC_FIELDS` excludes, for the identical
#: reasons: the record's own content address and its own semantic fingerprint (an identity
#: cannot be computed over itself) and ``signature`` (a signature cannot cover its own value).
#:
#: Note what is deliberately **absent**: there is no ``human_authority_ref`` field on this
#: record at all, and no field naming any key. A Runtime Root Admission's whole purpose is to
#: be verifiable against a trust anchor that is **not resolvable from within the Store being
#: admitted** -- an attacker's fully self-consistent alternate world has its own internally
#: valid Human Authority and its own signing key, so a record whose trust rested on *that* key
#: could simply be self-signed inside that world and would pass. See
#: :mod:`~manosube_agent_civilization.runtime.root_admission` and
#: ``10_RUNTIME/RUNTIME_CONTRACT.md`` §12.1.
#: ``generation``/``predecessor_ref`` were added by Round 4 (P15-R4-F1) for the identical reason
#: :data:`DEPLOYMENT_DECLARATION_SEMANTIC_FIELDS` states, applied to this record kind's own
#: chain: a root admission's place in its Project Binding's own admission chain is a claim the
#: **deployment trust anchor itself** signs, so an admission cannot be re-pointed at a different
#: predecessor after the anchor signed it, and a rotation or revocation cannot be forged by
#: whoever can write Store records.
ROOT_ADMISSION_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_ref",
    "status",
    "declared_at",
    "generation",
    "predecessor_ref",
)


#: The literal, deliberately **non-hex-only** prefix every Runtime Root Admission chain pointer
#: key carries (Phase 15 Structural Review Round 4, P15-R4-F1).
#:
#: Both chains -- root admissions and deployment declarations -- record their own current record
#: in the identical ``semantic_state.runtime.claims`` map Round 3 established, so the two key
#: spaces must be provably disjoint rather than merely observed not to collide. They are, by
#: construction and not by luck: :func:`runtime_deployment_target_key`'s own output alphabet is
#: exactly ``RUNTIME-DEPLOYMENT-TARGET-`` followed by 64 uppercase hex characters, which contains
#: no ``":"`` at any position, while every key this prefix produces contains one at a fixed
#: offset. See ``tests/unit/runtime/test_runtime_transition_chain.py``, which proves the
#: disjointness structurally (from the alphabets themselves) rather than by sampling.
ROOT_ADMISSION_TARGET_KEY_PREFIX = "ROOT-ADMISSION:"


#: Exactly the ``target_identity``/``runtime_deployment_declaration`` fields that decide *which
#: deployment target* a declaration is about, and therefore which canonical current-declaration
#: pointer it supersedes when it is committed (Phase 15 Structural Review Round 3, P15-R3-F2).
#:
#: These are :data:`~manosube_agent_civilization.runtime.route._DECLARATION_ANCHORED_TARGET_FIELDS`
#: **minus** ``deployment_fingerprint``, deliberately. A declaration's own
#: ``deployment_fingerprint`` is *what this target currently is*, not *which target this is*: a
#: legitimate rotation re-declares the identical provider/deployment/instance under a new
#: fingerprint, and that must **supersede** the previous declaration rather than open a second,
#: independent current-pointer beside it. Including the fingerprint in this key would make every
#: rotation fork the pointer space, leaving the superseded declaration permanently "current" for
#: its own old key -- which is exactly the ineffective-revocation defect P15-R3-F2 names.
DEPLOYMENT_TARGET_KEY_FIELDS: tuple[str, ...] = (
    "project_binding_ref",
    "provider",
    "deployment_id",
    "instance_identity",
)


def runtime_deployment_target_key(fields: dict[str, Any]) -> str:
    """Return the deterministic canonical key naming *which deployment target*
    :data:`DEPLOYMENT_TARGET_KEY_FIELDS` describes -- the key under which that target's own
    current ``runtime_deployment_declaration`` id is recorded in Project State
    (``semantic_state.runtime.claims``; P15-R3-F2).

    A pure function of the real declared fields, computed the identical way every other
    derivation in this module is: one canonical projection, hashed once, under a stable prefix.
    *fields* may be a full ``target_identity`` or a full ``runtime_deployment_declaration`` --
    only the four key fields are read, so both sides of the comparison the route performs derive
    the identical key from their own independently checked copies.
    """

    missing = [field for field in DEPLOYMENT_TARGET_KEY_FIELDS if field not in fields]
    if missing:
        raise RuntimeRequirementError(
            f"a runtime deployment target key cannot be derived without {', '.join(missing)}"
        )
    projection = {field: fields[field] for field in DEPLOYMENT_TARGET_KEY_FIELDS}
    return (
        "RUNTIME-DEPLOYMENT-TARGET-"
        + hashlib.sha256(canonical_json_bytes(projection)).hexdigest().upper()
    )


def runtime_root_admission_target_key(admission: dict[str, Any]) -> str:
    """Return the chain key naming *which Project Binding's own admission chain* *admission*
    belongs to -- the key under which that Binding's own current ``runtime_root_admission`` id is
    recorded in Project State (``semantic_state.runtime.claims``; Round 4, P15-R4-F1).

    Deliberately **not** a digest. A root admission chain is per Project Binding, and the Binding
    id is already a canonical identity, so hashing it would only obscure which chain a pointer
    belongs to while buying nothing -- the key space is not adversarially chosen here, it is
    exactly the set of Binding ids this project has ever admitted. What the shape *is* chosen for
    is provable disjointness from :func:`runtime_deployment_target_key`'s own key space: see
    :data:`ROOT_ADMISSION_TARGET_KEY_PREFIX`.

    *admission* may be a full ``runtime_root_admission`` or any mapping carrying a
    ``project_binding_ref`` -- only that one field is read, so a composition boundary and a
    committer derive the identical key from their own independently checked copies.
    """

    binding_ref = admission.get("project_binding_ref")
    binding_id = binding_ref.get("id") if isinstance(binding_ref, dict) else None
    if not isinstance(binding_id, str) or not binding_id:
        raise RuntimeRequirementError(
            "a runtime root admission chain key cannot be derived without a readable "
            f"project_binding_ref.id: {binding_ref!r}"
        )
    return ROOT_ADMISSION_TARGET_KEY_PREFIX + binding_id


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


def _root_admission_projection(admission: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in ROOT_ADMISSION_SEMANTIC_FIELDS if field not in admission]
    if missing:
        raise RuntimeRequirementError(
            "runtime_root_admission carries no readable "
            f"{', '.join(missing)} -- its own identity cannot be recomputed"
        )
    return {field: admission[field] for field in ROOT_ADMISSION_SEMANTIC_FIELDS}


def runtime_root_admission_signing_payload(admission: dict[str, Any]) -> bytes:
    """Return the exact canonical bytes a genuine trust-anchor signature over *admission* must
    cover -- the identical payload :func:`runtime_root_admission_id` and
    :func:`runtime_root_admission_semantic_fingerprint` themselves hash, over
    :data:`ROOT_ADMISSION_SEMANTIC_FIELDS` (Phase 15 Structural Review Round 3, P15-R3-F1).

    One shared derivation for all three purposes -- the identical discipline
    :func:`runtime_deployment_declaration_signing_payload` already establishes here, and
    :func:`~manosube_agent_civilization.binding.identity.human_grant_declaration_signing_payload`
    established before it: the content address and the signed message are never allowed to
    drift apart into two different notions of "what this record admitted".

    *admission* need not yet carry its own two digest fields or its own ``signature`` -- none of
    the three is read -- so this same function both mints the payload (before those fields
    exist) and re-derives it for verification (once they do).
    """

    return canonical_json_bytes(_root_admission_projection(admission))


def runtime_root_admission_id(admission: dict[str, Any]) -> str:
    """Return the content address of a canonical Runtime Root Admission -- a pure function of
    the complete, real record content, never of a caller-declared value, computed over
    :func:`runtime_root_admission_signing_payload`'s own bytes (P15-R3-F1)."""

    digest = hashlib.sha256(runtime_root_admission_signing_payload(admission))
    return "RUNTIME-ROOT-ADMISSION-" + digest.hexdigest().upper()


def runtime_root_admission_semantic_fingerprint(admission: dict[str, Any]) -> str:
    """Return the digest of a canonical Runtime Root Admission's full meaning -- the identical
    payload :func:`runtime_root_admission_id` hashes, under the ``sha256:`` encoding every other
    owner's own semantic fingerprint already uses."""

    digest = hashlib.sha256(runtime_root_admission_signing_payload(admission))
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
