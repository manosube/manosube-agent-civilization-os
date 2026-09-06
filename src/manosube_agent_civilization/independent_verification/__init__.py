"""Independent Verification over canonical Evidence (Phase 13, Issue #51):
``KERNEL_ELEMENT=INDEPENDENT_EVIDENCE_ADAPTER``.

Adds exactly one provider-neutral, explicit Independent Verification adapter:

.. code-block:: python

   result = run_independent_verification(
       store,
       project_id=project_id,
       verification_requirement=requirement,
       verifier_selection=selection,
       verifier=verifier,
   )
   result.status  # VERIFIED | FAILED | INSUFFICIENT | UNAVAILABLE

This is not a ninth Kernel element (the same ``KERNEL_ELEMENT=none``-style convention Boot,
the CLI, and the Temporary Agent lifecycle already use, here spelled
``INDEPENDENT_EVIDENCE_ADAPTER``): it owns verification-specific requirement, selection,
boundary, and provenance only, and creates no second State, Evidence, Difference, Authority,
Change, Store, or Closure owner. It introduces no fixed verifier, no automatic verifier
selection, no external reviewer gate, and no automatic closure -- ``VerifierSelection`` is
always SHUKOU-authorized and supplied by the caller, ``run_independent_verification`` never
selects, defaults, or infers one. A ``VerificationResult`` is not itself Evidence, an
Authority Decision, a Closure receipt, a State transition, or a Merge authorization; carrying
an admissible verification result into existing Evidence-sufficiency semantics remains
entirely the existing Evidence owner's own, separate concern.

See ``08_VERIFICATION/VERIFICATION_INDEX.md`` for the full contract set.
"""

from .errors import IndependentVerificationError, VerificationRequirementError, VerifierOutputError
from .route import run_independent_verification
from .types import (
    SELECTION_STATUSES,
    TARGET_REF_KINDS,
    VERIFICATION_STATUSES,
    IndependentVerifier,
    VerificationRequirement,
    VerificationResult,
    VerifierSelection,
)

__all__ = [
    "SELECTION_STATUSES",
    "TARGET_REF_KINDS",
    "VERIFICATION_STATUSES",
    "IndependentVerificationError",
    "IndependentVerifier",
    "VerificationRequirement",
    "VerificationRequirementError",
    "VerificationResult",
    "VerifierOutputError",
    "VerifierSelection",
    "run_independent_verification",
]
