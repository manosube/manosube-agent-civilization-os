"""Reflow's admission and decision layer: what lifecycle transition a Closure Evaluation
actually admits, and under what reason code.

``evaluate_closure`` already decides *whether* a proposed terminal status is legal (G22,
checked against the Closure Policy's ``allowed_terminal_states``) and *what* it is when the
result is ``SATISFIED`` (the schema forces ``proposed_terminal_status == "CLOSED"``). What
it does not decide is the single ``reason_code`` a ``difference_lifecycle_event.TRANSITION``
event must carry -- that event is Difference's own record, owned and minted by a later step
of this same Reflow element, not by this module. This module is the seam between the two: it
reads one Closure Evaluation and returns the transition decision, without reading or writing
anything else.

``CLOSURE_POLICY.md`` section 6's Fail-Closed Mapping table is the source of every reason
code below; :data:`REASON_CODES` names each row this module can reach.
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.difference.lifecycle import is_legal_transition

from .errors import ReflowValidationError

#: One reason code per Closure Evaluation ``result`` this module maps to a transition.
#: ``EVALUATING`` and ``NOT_EVALUATED`` are excluded on purpose: a Closure Evaluation this
#: module is asked to decide on has already run to completion, so those two values reaching
#: here are the caller's error, not a transition this module can admit.
REASON_CODES: dict[str, str] = {
    "SATISFIED": "TARGET_SATISFIED_AND_CLOSURE_GATES_PASSED",
    "NOT_SATISFIED": "TARGET_NOT_SATISFIED",
    "BLOCKED": "REQUIRED_INPUT_OR_OBSERVATION_UNAVAILABLE",
    "STALE": "EVALUATION_OR_BINDING_STALE",
    "CONTRADICTED": "MATERIAL_CONTRADICTION_DETECTED",
    "REVOKED": "CLOSURE_PREMISE_REVOKED",
}


def decide_transition(
    evaluation: dict[str, Any], current_status: str
) -> dict[str, Any]:
    """Return the one lifecycle transition this Closure Evaluation admits.

    Returns ``{"to_status", "reason_code", "reason", "closure_evaluation_ref"}``. Raises
    :class:`~manosube_agent_civilization.reflow.errors.ReflowValidationError` if the
    Evaluation's own ``result`` is not one this module can decide on, or if the transition
    it names is not legal from *current_status* -- ``evaluate_closure`` already checked
    legality against the status it was told, but a caller must not be able to silently
    apply that decision against a Difference that has since moved to a different status.
    """

    result = evaluation.get("result")
    reason_code = REASON_CODES.get(result)
    if reason_code is None:
        raise ReflowValidationError(
            f"Closure Evaluation result admits no transition decision: {result!r}"
        )
    to_status = evaluation["proposed_terminal_status"]
    if not is_legal_transition(current_status, to_status):
        raise ReflowValidationError(
            f"the Evaluation's proposed_terminal_status is not a legal transition from "
            f"{current_status!r}: {to_status!r}"
        )
    return {
        "to_status": to_status,
        "reason_code": reason_code,
        "reason": f"{reason_code}: closure_evaluation {evaluation['closure_evaluation_id']}",
        "closure_evaluation_ref": {
            "kind": "closure_evaluation",
            "id": evaluation["closure_evaluation_id"],
        },
    }
