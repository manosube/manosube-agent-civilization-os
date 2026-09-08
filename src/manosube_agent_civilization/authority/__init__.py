"""Deterministic, adapter-free Authority evaluation for the v0.1 canonical route.

Authority decides whether a proposed action **may** occur against one exact State. It never
executes Change, closes a Difference, updates State, judges Evidence, or declares Objective
Completion.

```text
CAN_DO  != MAY_DO
AUTHORITY_REQUIRED != AUTHORITY_GRANTED
AUTHORIZED != EXECUTED
```

There is exactly one Change-permission evaluator, :func:`evaluate_authority`.

Structural Review Round 3 (Issue #51, P13-R3-F1) adds one further, narrowly-scoped evaluator
to this same owner -- :func:`evaluate_verifier_selection` -- answering a distinct question:
whether a real Human Authority actually selected *this* Independent Verification
``VerifierSelection`` for *this* ``VerificationRequirement``, never by reusing
:func:`evaluate_authority`'s own Change/Difference/State-bound machinery for a purpose it was
not designed for. It is an extension of this owner, not a second Authority owner: it shares
this package's admission grammar, error vocabulary, and content-addressing conventions, and
introduces no registry, token, cache, or persisted artifact of its own.
"""

from .engine import evaluate_authority
from .errors import (
    AuthorityError,
    AuthorityValidationError,
    BoundaryViolationError,
    StaleAuthorityInputError,
)
from .levels import AUTONOMOUS, HUMAN_APPROVAL_REQUIRED, PROHIBITED
from .verifier_selection import REFUSED, SELECTED, evaluate_verifier_selection

__all__ = [
    "AUTONOMOUS",
    "HUMAN_APPROVAL_REQUIRED",
    "PROHIBITED",
    "REFUSED",
    "SELECTED",
    "AuthorityError",
    "AuthorityValidationError",
    "BoundaryViolationError",
    "StaleAuthorityInputError",
    "evaluate_authority",
    "evaluate_verifier_selection",
]
