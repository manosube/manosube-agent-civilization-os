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

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.evidence import derive_evidence

from .errors import EvidenceHandoffError
from .types import VerificationResult


def route_verification_result_to_evidence(
    verification_result: VerificationResult, evidence_request: Mapping[str, Any]
) -> dict[str, Any]:
    """Hand *verification_result* off to the existing Evidence owner and return the one
    canonical Evidence record it derives from *evidence_request*.

    *evidence_request* must already be a real, Change-free, ``verification_observation_
    request``-grounded Evidence request -- built by the caller from real Observation/
    Difference data exactly as every other Evidence caller in this codebase already builds
    one. This function fabricates none of that; it only validates the handoff's own two
    boundaries (Change-freedom, and that the derived record is actually about
    *verification_result*) before and after the one existing-owner call.

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

    evidence = derive_evidence(dict(evidence_request))

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
