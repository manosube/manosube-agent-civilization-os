"""The one public GitHubObservationReceipt-to-Evidence handoff (Phase 14, Issue #62).

Issue #62's minimum-acceptable-after-state item 7 requires GitHub re-observation to produce
"a bounded receipt connected to the existing Observation, Evidence and Reflow owners."
Independent Verification's own Change-Free Verification Evidence position
(``evidence/engine.py``'s ``CHANGE_FREE_VERIFICATION_EVIDENCE``) is CLOSURE_POLICY.md's own
``CHANGE_FREE`` row's already-ratified position for exactly this shape of fact: an
independent, Change-free confirmation that some external observation still corresponds to a
canonical subject. A GitHub re-observation confirming a projected artifact still round-trips
to its canonical subject is structurally the same kind of fact, so this module reuses the
identical position and the identical existing-owner call
(:func:`~manosube_agent_civilization.evidence.derive_evidence`, called exactly once) --
never a second Evidence, Observation, or Reflow owner (``NEW_EVIDENCE_OWNER=false``).

This module does **not** import ``independent_verification`` -- it is Projection's own,
package-local handoff, built from a real :class:`~manosube_agent_civilization.projection.
types.GitHubObservationReceipt` this package already holds, using the identical field shape
(``verification_result_provenance``'s own ten required keys) the Evidence schema itself
enforces for this position, since R6-R1 (``ADOPT_P13_R6_R1_EVIDENCE_OWNER_GLOBAL_PROVENANCE_
ENFORCEMENT``) made that provenance mandatory for *every* caller of this position, not only
Independent Verification's own handoff.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.evidence import derive_evidence

from .errors import ProjectionRequirementError
from .types import GitHubObservationReceipt

_ENVELOPE_RECORD_KIND = "projection_envelope"

#: The identical ten fields ``evidence.schema.json``'s own ``verification_result_provenance``
#: requires -- see ``evidence/identity.py``'s ``EVIDENCE_SEMANTIC_FIELDS`` and
#: ``independent_verification/evidence_handoff.py``'s own ``REQUIRED_PROVENANCE_FIELDS``.
REQUIRED_PROVENANCE_FIELDS: tuple[str, ...] = (
    "status",
    "requirement_id",
    "selection_id",
    "project_id",
    "target_refs",
    "verifier_identity",
    "selection_authority_ref",
    "verification_boundary",
    "input_refs",
    "observations",
)


def _reference_set(refs: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    members = [dict(ref) for ref in refs]
    members.sort(key=lambda ref: (ref.get("kind", ""), ref.get("id", "")))
    return {"collection_kind": "UNORDERED_SET", "members": members}


def _construct_provenance(receipt: GitHubObservationReceipt, project_id: str) -> dict[str, Any]:
    """Return the one, deterministic ``verification_result_provenance`` projection of
    *receipt* -- built here, from the real receipt this handoff already holds, and never
    accepted from a caller (the identical "derived, never declared" discipline Independent
    Verification's own R6-R6 handoff already applies)."""

    target_refs = (dict(receipt.subject_ref),)
    provenance = {
        "status": receipt.status,
        "requirement_id": receipt.projection_envelope_id,
        "selection_id": receipt.projection_envelope_id,
        "project_id": project_id,
        "target_refs": _reference_set(target_refs),
        "verifier_identity": dict(receipt.adapter_identity),
        "selection_authority_ref": dict(receipt.github_authority_ref),
        "verification_boundary": {"external_artifact_ref": dict(receipt.external_artifact_ref)},
        "input_refs": _reference_set(receipt.input_refs or target_refs),
        "observations": dict(receipt.observations),
    }
    if set(provenance) != set(REQUIRED_PROVENANCE_FIELDS):
        raise ProjectionRequirementError(
            "constructed verification_result_provenance does not carry exactly the required "
            f"field set: {sorted(provenance)} != {sorted(REQUIRED_PROVENANCE_FIELDS)}"
        )
    return provenance


def route_observation_receipt_to_evidence(
    store: Any,
    receipt: GitHubObservationReceipt,
    project_id: str,
    evidence_request: Mapping[str, Any],
) -> dict[str, Any]:
    """Hand *receipt* off to the existing Evidence owner and return the one canonical
    Evidence record it derives from *evidence_request*.

    *evidence_request* must already be a real, Change-free,
    ``verification_observation_request``-grounded Evidence request -- built by the caller
    from real Observation/Difference data, exactly as every other Evidence caller in this
    codebase already builds one. This function fabricates none of that; it only constructs
    and injects ``verification_result_provenance`` from *receipt* itself, and re-verifies the
    derived record actually carries exactly that provenance before returning it.

    Every :class:`~manosube_agent_civilization.evidence.errors.EvidenceError` the existing
    owner itself raises propagates unchanged.
    """

    if not isinstance(receipt, GitHubObservationReceipt):
        raise ProjectionRequirementError(
            f"receipt must be a GitHubObservationReceipt instance, not {type(receipt)!r}"
        )
    # Structural Review Round 1 (Issue #62, P14-R1-F3) checked only ``receipt.project_id ==
    # project_id`` -- both of them plain fields on a publicly constructible dataclass, so a
    # caller could copy a genuine receipt, overwrite ``project_id`` to name a different
    # project, and pass that same (matching) value here: the check above always passes
    # because it only ever compares the receipt against itself.
    #
    # Structural Review Round 2 (P14-R2-F3) replaces that self-comparison with an
    # independent resolution: *project_id*'s own Store is asked whether it ever actually
    # committed the exact Projection Envelope this receipt claims to be about. Store
    # partitions every record by project (``FileStateStore.resolve_record`` looks only
    # inside *project_id*'s own directory), so a receipt copied from a different project's
    # envelope resolves to nothing here and is refused before ``derive_evidence`` is ever
    # called -- there is no separate "receipt identity" to forge, because nothing about the
    # receipt itself is trusted until it is corroborated against the real, committed record.
    envelope = store.resolve_record(
        project_id, _ENVELOPE_RECORD_KIND, receipt.projection_envelope_id
    )
    if envelope is None:
        raise ProjectionRequirementError(
            "receipt names a projection_envelope_id that does not resolve under the "
            f"requested project {project_id!r} -- a receipt genuinely produced for a "
            "different project cannot be relabelled as Evidence for this one: "
            f"{receipt.projection_envelope_id!r}"
        )
    if envelope["subject_ref"] != dict(receipt.subject_ref):
        raise ProjectionRequirementError(
            "receipt's own subject_ref does not match the real, committed Envelope's "
            f"subject_ref: {dict(receipt.subject_ref)!r} != {envelope['subject_ref']!r}"
        )
    if envelope["external_artifact_ref"] != dict(receipt.external_artifact_ref):
        raise ProjectionRequirementError(
            "receipt's own external_artifact_ref does not match the real, committed "
            f"Envelope's external_artifact_ref: {dict(receipt.external_artifact_ref)!r} != "
            f"{envelope['external_artifact_ref']!r}"
        )
    if envelope["github_authority_ref"] != dict(receipt.github_authority_ref):
        raise ProjectionRequirementError(
            "receipt's own github_authority_ref does not match the real, committed "
            f"Envelope's github_authority_ref: {dict(receipt.github_authority_ref)!r} != "
            f"{envelope['github_authority_ref']!r}"
        )
    if receipt.project_id != project_id:
        raise ProjectionRequirementError(
            "receipt's own originating project_id does not match the requested project_id -- "
            f"a receipt cannot be relabelled across projects: {receipt.project_id!r} != "
            f"{project_id!r}"
        )
    if not isinstance(evidence_request, Mapping):
        raise ProjectionRequirementError(
            f"evidence_request must be an explicit mapping, not {type(evidence_request)!r}"
        )
    if evidence_request.get("change_request") is not None:
        raise ProjectionRequirementError(
            "evidence_request must be Change-free -- a GitHub Observation Receipt never "
            "executes or grounds a Change"
        )
    if evidence_request.get("post_change_observation_request") is not None:
        raise ProjectionRequirementError(
            "evidence_request must carry no post_change_observation_request -- a GitHub "
            "Observation Receipt never grounds a Change result"
        )
    if evidence_request.get("verification_observation_request") is None:
        raise ProjectionRequirementError(
            "evidence_request must carry a verification_observation_request -- the one "
            "Evidence position (Change-Free Verification Evidence) this handoff produces"
        )
    if evidence_request.get("verification_result_provenance") is not None:
        raise ProjectionRequirementError(
            "evidence_request must not already carry a verification_result_provenance -- "
            "this handoff constructs it from receipt itself"
        )

    provenance = _construct_provenance(receipt, project_id)
    request = dict(evidence_request)
    request["verification_result_provenance"] = provenance

    evidence = derive_evidence(request)

    if evidence["verification_result_provenance"] != provenance:
        raise ProjectionRequirementError(
            "the derived Evidence record's own verification_result_provenance does not "
            "exactly equal the one this handoff constructed from receipt -- refusing to "
            "return a record whose provenance this handoff cannot confirm"
        )
    if evidence["target"]["project_id"] != project_id:
        raise ProjectionRequirementError(
            "the derived Evidence record names a different project than requested: "
            f"{evidence['target']['project_id']!r} != {project_id!r}"
        )

    return evidence
