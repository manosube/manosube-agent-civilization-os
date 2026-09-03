"""Reflow: EVIDENCE EVALUATION + CLOSURE EVALUATION + ATOMIC STATE TRANSITION.

See ``00_KERNEL/08_REFLOW/REFLOW_CONTRACT.md`` for the authority boundary, the canonical
input set, and the explicit list of what this element does and does not claim.
"""

from .closure import (
    MANDATORY_X003_CLAIM_DESCRIPTOR,
    MANDATORY_X003_CLAIM_ID,
    MANDATORY_X003_CLAIM_REF,
    evaluate_closure,
)
from .errors import (
    ReflowError,
    ReflowValidationError,
    StaleReflowError,
    UnauthorizedReflowError,
)
from .identity import (
    after_state_candidate_id,
    closure_evaluation_decision_fingerprint,
    closure_evaluation_id,
    material_contradiction_id,
    transaction_id,
)

__all__ = [
    "MANDATORY_X003_CLAIM_DESCRIPTOR",
    "MANDATORY_X003_CLAIM_ID",
    "MANDATORY_X003_CLAIM_REF",
    "ReflowError",
    "ReflowValidationError",
    "StaleReflowError",
    "UnauthorizedReflowError",
    "after_state_candidate_id",
    "closure_evaluation_decision_fingerprint",
    "closure_evaluation_id",
    "evaluate_closure",
    "material_contradiction_id",
    "transaction_id",
]
