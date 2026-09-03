"""Reopen: the one ``CLOSED -> REOPENED`` transition Reflow admits without re-running the
G1-G22 gate engine.

``CLOSURE_POLICY.md`` section 9 defines five reopen triggers. This module claims two:
``OBSERVATION_CONTRADICTION`` (a post-closure Observation shows the Target no longer
satisfied) and ``MATERIAL_CONTRADICTION`` (a Material Contradiction record -- the schema
this vertical's RF1 added -- names conflicting Evidence or Authority provenance the
original Closure Evaluation never saw). ``CLOSURE_EVIDENCE_REVOKED``,
``CLOSURE_EVIDENCE_INVALID`` and ``POLICY_REOPEN_CONDITION_SATISFIED`` are **NOT CLAIMED**:
the first two require an Evidence-revocation/invalidation producer this Kernel does not yet
have, and the third requires re-evaluating a Closure Policy's ``reopen_conditions`` Target
Predicates against current State -- a Target Predicate evaluator Reflow does not own (that
is Difference's own comparison machinery, and re-deriving Target Satisfaction outside a
fresh Closure Evaluation would be a second, competing answer to the question G10 already
owns). A caller reaching for either is refused, not silently accepted.

Reopen does not re-run :func:`~manosube_agent_civilization.reflow.closure.evaluate_closure`:
the closed Difference's original Closure Evaluation stays exactly as it was (``REFLOW_
CONTRACT.md`` section 8, "Reopen preserves old Closure Evaluation/Evidence"), and this
module's decision *re-references* it rather than replacing it -- which is why
``difference/lifecycle.py``'s own ``REQUIRES_CLOSURE_EVALUATION`` deliberately excludes
``REOPENED``: it is bound to an Evaluation by a different rule, applied here.
"""

from __future__ import annotations

from typing import Any

from .errors import ReflowValidationError

#: The reopen triggers this vertical implements, and the reason code each mints.
REOPEN_REASON_CODES: dict[str, str] = {
    "OBSERVATION_CONTRADICTION": "POST_CLOSURE_OBSERVATION_CONTRADICTS_TARGET",
    "MATERIAL_CONTRADICTION": "MATERIAL_CONTRADICTION_DETECTED_POST_CLOSURE",
}


def decide_reopen(old_closure_evaluation: dict[str, Any], trigger: str) -> dict[str, Any]:
    """Return the ``CLOSED -> REOPENED`` decision this trigger admits.

    *old_closure_evaluation* must be the Evaluation that actually closed the Difference --
    ``result == "SATISFIED"`` and ``proposed_terminal_status == "CLOSED"`` -- since Reopen
    exists to contradict exactly that closure, not any other Evaluation on file for the
    Difference.
    """

    if (
        old_closure_evaluation.get("result") != "SATISFIED"
        or old_closure_evaluation.get("proposed_terminal_status") != "CLOSED"
    ):
        raise ReflowValidationError(
            "reopen requires the Closure Evaluation that actually closed the Difference"
        )
    reason_code = REOPEN_REASON_CODES.get(trigger)
    if reason_code is None:
        raise ReflowValidationError(
            f"reopen trigger is not implemented in this vertical: {trigger!r}"
        )
    return {
        "to_status": "REOPENED",
        "reason_code": reason_code,
        "reason": f"{reason_code}: closure_evaluation {old_closure_evaluation['closure_evaluation_id']}",
        "closure_evaluation_ref": {
            "kind": "closure_evaluation",
            "id": old_closure_evaluation["closure_evaluation_id"],
        },
        "reopen_trigger": trigger,
    }
