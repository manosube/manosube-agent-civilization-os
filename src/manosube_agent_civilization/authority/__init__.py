"""Deterministic, adapter-free Authority evaluation for the v0.1 canonical route.

Authority decides whether a proposed action **may** occur against one exact State. It never
executes Change, closes a Difference, updates State, judges Evidence, or declares Objective
Completion.

```text
CAN_DO  != MAY_DO
AUTHORITY_REQUIRED != AUTHORITY_GRANTED
AUTHORIZED != EXECUTED
```

There is exactly one evaluator, and it is :func:`evaluate_authority`.
"""

from .engine import evaluate_authority
from .errors import (
    AuthorityError,
    AuthorityValidationError,
    BoundaryViolationError,
    StaleAuthorityInputError,
)
from .levels import AUTONOMOUS, HUMAN_APPROVAL_REQUIRED, PROHIBITED

__all__ = [
    "AUTONOMOUS",
    "HUMAN_APPROVAL_REQUIRED",
    "PROHIBITED",
    "AuthorityError",
    "AuthorityValidationError",
    "BoundaryViolationError",
    "StaleAuthorityInputError",
    "evaluate_authority",
]
