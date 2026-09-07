"""The one public VerificationResult-to-Evidence handoff (Phase 13, Issue #51).

Structural Review Round 2 (P13-R2-F2): a non-persisted :class:`~manosube_agent_civilization.
independent_verification.types.VerificationResult` documenting that Round 0's own stance --
"carrying it into existing Evidence-sufficiency semantics remains the caller's own, separate
concern" -- is not itself the handoff Issue #51 requires. This module is the real connection:
:func:`route_verification_result_to_evidence` calls the existing Evidence owner's own public
:func:`~manosube_agent_civilization.evidence.derive_evidence` exactly once, over an explicit,
already-real ``evidence_request`` the caller supplies (built from real Observation/Difference
data the caller already holds, exactly as every other Evidence caller in this codebase already
builds one -- this module fabricates no Observation, Scope, or Source Snapshot of its own),
and cross-verifies the resulting canonical Evidence record actually names the same project
(and, when the requirement named one, the same Difference) the supplied
``VerificationResult`` is about.

Structural Review Round 6 (P13-R6): the same real ``VerificationResult`` this handoff is
already given is now also the sole source of the derived Evidence record's own
``verification_result_provenance``. This module deterministically constructs that projection
from *verification_result*'s own ten fields -- never accepting one the caller already placed
on ``evidence_request``, which would let the handoff attach any provenance a caller chose to
supply rather than the one this call is actually for -- injects it into the request before the
one existing-owner call, and refuses to return a record whose own, schema-validated
``verification_result_provenance`` does not exactly equal what was just constructed. This is
the same "derived, never declared" discipline this module already gave ``target``/
``difference_ref`` in Round 2, applied to the field Round 6 adds.

``VerificationResult`` remains what Issue #51 and Structural Review Round 1 already fixed: it
is never itself an Evidence record, an Authority Decision, a Closure receipt, a State
transition, or a Merge authorization, and Independent Verification still never persists
canonical Evidence directly, writes to the Store, or grounds a Change. The Evidence request
must be Change-free and already in the ``verification_observation_request``-grounded position
``evidence/engine.py`` calls Change-Free Verification Evidence -- the one position CLOSURE_
POLICY.md's own ``CHANGE_FREE`` row already assigns to an independent verification result --
and the existing Evidence owner alone still decides that request's own identity, schema
validation, and canonical shape. Once this call returns a genuine canonical Evidence record,
it is already exactly the shape the existing evidence-sufficiency owner
(:func:`~manosube_agent_civilization.evidence.sufficiency.evaluate_sufficiency`) and the
existing Difference/Reflow owner's own reference-closure gate already accept -- connecting to
either is the caller's own next, unmodified call into those existing, already-established
public surfaces; this module does not call them itself, exactly as it must not become a
second Evidence, Difference, or Reflow owner (``NEW_EVIDENCE_OWNER=false``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from manosube_agent_civilization.evidence import derive_evidence

from .errors import EvidenceHandoffError
from .types import VerificationResult

#: The ten fields Structural Review Round 6 requires the Evidence record's own
#: ``verification_result_provenance`` to hold -- exactly :class:`VerificationResult`'s own
#: field set, no more and no fewer, so the projection is a complete capture of what this
#: verification actually established rather than a partial, caller-chosen subset.
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


def _thaw(value: Any) -> Any:
    """Return *value* with every ``MappingProxyType``/``tuple`` the frozen VerificationResult
    holds converted back to a plain, JSON/schema-shaped ``dict``/``list`` -- the exact inverse
    of ``types.py``'s own ``_deep_freeze``, applied recursively so a nested frozen structure
    inside ``verifier_identity``/``selection_authority_ref``/``verification_boundary``/
    ``observations`` (all opaque to this handoff and to the Evidence schema alike) is thawed
    just as completely as its top level.
    """

    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _provenance_reference_set(references: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return *references* in the Evidence schema's own ``unordered_references`` shape."""

    members = [_thaw(reference) for reference in references]
    members.sort(key=lambda reference: (reference.get("kind", ""), reference.get("id", "")))
    return {"collection_kind": "UNORDERED_SET", "members": members}


def _construct_verification_result_provenance(
    verification_result: VerificationResult,
) -> dict[str, Any]:
    """Return the one, deterministic ``verification_result_provenance`` projection of
    *verification_result* -- built here, from the real value this handoff already holds,
    and never accepted from a caller (see the module docstring's Round 6 note)."""

    provenance = {
        "status": verification_result.status,
        "requirement_id": verification_result.requirement_id,
        "selection_id": verification_result.selection_id,
        "project_id": verification_result.project_id,
        "target_refs": _provenance_reference_set(verification_result.target_refs),
        "verifier_identity": _thaw(verification_result.verifier_identity),
        "selection_authority_ref": _thaw(verification_result.selection_authority_ref),
        "verification_boundary": _thaw(verification_result.verification_boundary),
        "input_refs": _provenance_reference_set(verification_result.input_refs),
        "observations": _thaw(verification_result.observations),
    }
    if set(provenance) != set(REQUIRED_PROVENANCE_FIELDS):
        raise EvidenceHandoffError(
            "constructed verification_result_provenance does not carry exactly the required "
            f"field set: {sorted(provenance)} != {sorted(REQUIRED_PROVENANCE_FIELDS)}"
        )
    return provenance


def route_verification_result_to_evidence(
    verification_result: VerificationResult, evidence_request: Mapping[str, Any]
) -> dict[str, Any]:
    """Hand *verification_result* off to the existing Evidence owner and return the one
    canonical Evidence record it derives from *evidence_request*.

    *evidence_request* must already be a real, Change-free, ``verification_observation_
    request``-grounded Evidence request -- built by the caller from real Observation/
    Difference data exactly as every other Evidence caller in this codebase already builds
    one. This function fabricates none of that; it only validates the handoff's own
    boundaries (Change-freedom, that the request carries no caller-supplied
    ``verification_result_provenance`` this handoff would otherwise have to trust, and that
    the derived record is actually about *verification_result*) before and after the one
    existing-owner call.

    ``verification_result_provenance`` is this handoff's own addition (Structural Review
    Round 6): constructed here from *verification_result* itself, injected into the request
    this function -- never the caller -- controls, and re-verified against the record
    ``derive_evidence`` actually returns before this function will return it. A caller that
    already placed a non-``None`` value under that key on *evidence_request* is refused
    outright, because accepting it would mean this handoff no longer controls which
    provenance the returned Evidence record carries.

    Every :class:`~manosube_agent_civilization.evidence.errors.EvidenceError` the existing
    owner itself raises propagates unchanged -- this function neither catches nor
    reclassifies one, and produces no partial or substitute Evidence record on any such
    rejection.
    """

    if not isinstance(verification_result, VerificationResult):
        raise EvidenceHandoffError(
            "verification_result must be a VerificationResult instance, not "
            f"{type(verification_result)!r}"
        )
    if not isinstance(evidence_request, Mapping):
        raise EvidenceHandoffError(
            f"evidence_request must be an explicit mapping, not {type(evidence_request)!r}"
        )
    if evidence_request.get("change_request") is not None:
        raise EvidenceHandoffError(
            "evidence_request must be Change-free -- Independent Verification never "
            "executes or grounds a Change"
        )
    if evidence_request.get("post_change_observation_request") is not None:
        raise EvidenceHandoffError(
            "evidence_request must carry no post_change_observation_request -- Independent "
            "Verification never grounds a Change result"
        )
    if evidence_request.get("verification_observation_request") is None:
        raise EvidenceHandoffError(
            "evidence_request must carry a verification_observation_request -- the one "
            "Evidence position (Change-Free Verification Evidence) this handoff produces"
        )
    if evidence_request.get("verification_result_provenance") is not None:
        raise EvidenceHandoffError(
            "evidence_request must not already carry a verification_result_provenance -- "
            "this handoff constructs it from verification_result itself and does not accept "
            "one a caller supplied"
        )

    provenance = _construct_verification_result_provenance(verification_result)
    request = dict(evidence_request)
    request["verification_result_provenance"] = provenance

    evidence = derive_evidence(request)

    if evidence["verification_result_provenance"] != provenance:
        raise EvidenceHandoffError(
            "the derived Evidence record's own verification_result_provenance does not "
            "exactly equal the one this handoff constructed from verification_result -- "
            "refusing to return a record whose provenance this handoff cannot confirm"
        )

    if evidence["target"]["project_id"] != verification_result.project_id:
        raise EvidenceHandoffError(
            "the derived Evidence record names a different project than "
            f"verification_result: {evidence['target']['project_id']!r} != "
            f"{verification_result.project_id!r}"
        )
    named_difference_ids = {
        ref["id"] for ref in verification_result.target_refs if ref.get("kind") == "difference"
    }
    if named_difference_ids and evidence["difference_ref"]["id"] not in named_difference_ids:
        raise EvidenceHandoffError(
            "the derived Evidence record is bound to a Difference verification_result never "
            f"named: {evidence['difference_ref']['id']!r} not in {sorted(named_difference_ids)}"
        )

    return evidence
