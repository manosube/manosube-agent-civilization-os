"""Canonical deterministic Difference Engine."""

from .engine import derive_differences
from .errors import (
    BoundaryViolationError,
    DifferenceError,
    DifferenceValidationError,
    IdentityCollisionError,
    SecurityRejectionError,
    UnsupportedProfileError,
)
from .identity import (
    COMPARISON_PROFILE,
    IDENTITY_PROFILE,
    NORMALIZATION_PROFILE,
    difference_id,
    objective_semantic_fingerprint,
    policy_semantic_fingerprint,
    resolved_scope_fingerprint,
    supersession_reason_codes,
)

__all__ = [
    "COMPARISON_PROFILE",
    "IDENTITY_PROFILE",
    "NORMALIZATION_PROFILE",
    "BoundaryViolationError",
    "DifferenceError",
    "DifferenceValidationError",
    "IdentityCollisionError",
    "SecurityRejectionError",
    "UnsupportedProfileError",
    "derive_differences",
    "difference_id",
    "objective_semantic_fingerprint",
    "policy_semantic_fingerprint",
    "resolved_scope_fingerprint",
    "supersession_reason_codes",
]
