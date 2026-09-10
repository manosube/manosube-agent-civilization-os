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

Phase 14 Structural Review Round 1 (Issue #62, P14-R1-F1) adds one further such extension --
:func:`evaluate_projection_authorization` -- answering whether a real Human Authority actually
authorized *this exact* GitHub projection (subject, subject fingerprint, projection kind,
target repository, payload fingerprint, permitted action), never by reusing Change/Difference/
State-bound machinery, and never by mere equality with a Human Authority's own owner identity.

Phase 16 (Issue #66, P16-C1) adds one further such extension --
:func:`evaluate_model_execution_authorization` -- answering whether a real Human Authority
actually granted *this exact* model-execution capability (Difference, required capability,
Model Execution Boundary) to a State-bound Model Work Unit. It is an extension of this owner,
not a second Authority owner, and it is never reachable by a model, an adapter, or a provider:
see :mod:`.model_execution_authorization`'s own module docstring for why the Change-permission
evaluator could not answer this question.
"""

from .engine import evaluate_authority
from .errors import (
    AuthorityError,
    AuthorityValidationError,
    BoundaryViolationError,
    StaleAuthorityInputError,
)
from .levels import AUTONOMOUS, HUMAN_APPROVAL_REQUIRED, PROHIBITED
from .model_execution_authorization import (
    AUTHORIZED as MODEL_EXECUTION_AUTHORIZED,
    REFUSED as MODEL_EXECUTION_REFUSED,
    evaluate_model_execution_authorization,
)
from .projection_authorization import (
    AUTHORIZED as PROJECTION_AUTHORIZED,
    REFUSED as PROJECTION_REFUSED,
    evaluate_projection_authorization,
)
from .verifier_selection import REFUSED, SELECTED, evaluate_verifier_selection

__all__ = [
    "AUTONOMOUS",
    "HUMAN_APPROVAL_REQUIRED",
    "MODEL_EXECUTION_AUTHORIZED",
    "MODEL_EXECUTION_REFUSED",
    "PROHIBITED",
    "PROJECTION_AUTHORIZED",
    "PROJECTION_REFUSED",
    "REFUSED",
    "SELECTED",
    "AuthorityError",
    "AuthorityValidationError",
    "BoundaryViolationError",
    "StaleAuthorityInputError",
    "evaluate_authority",
    "evaluate_model_execution_authorization",
    "evaluate_projection_authorization",
    "evaluate_verifier_selection",
]
