"""Reflow: EVIDENCE EVALUATION + CLOSURE EVALUATION + ATOMIC STATE TRANSITION.

See ``00_KERNEL/08_REFLOW/REFLOW_CONTRACT.md`` for the authority boundary, the canonical
input set, and the explicit list of what this element does and does not claim.
"""

from .bookkeeping import apply_reflow_bookkeeping
from .closure import (
    MANDATORY_X003_CLAIM_DESCRIPTOR,
    MANDATORY_X003_CLAIM_ID,
    MANDATORY_X003_CLAIM_REF,
    evaluate_closure,
)
from .commit import build_state_transition, commit_reflow
from .engine import REASON_CODES, decide_transition
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
from .lifecycle import mint_transition_event
from .reopen import REOPEN_REASON_CODES, decide_reopen
from .route import reflow, reopen

__all__ = [
    "MANDATORY_X003_CLAIM_DESCRIPTOR",
    "MANDATORY_X003_CLAIM_ID",
    "MANDATORY_X003_CLAIM_REF",
    "REASON_CODES",
    "REOPEN_REASON_CODES",
    "ReflowError",
    "ReflowValidationError",
    "StaleReflowError",
    "UnauthorizedReflowError",
    "after_state_candidate_id",
    "apply_reflow_bookkeeping",
    "build_state_transition",
    "closure_evaluation_decision_fingerprint",
    "closure_evaluation_id",
    "commit_reflow",
    "decide_reopen",
    "decide_transition",
    "evaluate_closure",
    "material_contradiction_id",
    "mint_transition_event",
    "reflow",
    "reopen",
    "transaction_id",
]
