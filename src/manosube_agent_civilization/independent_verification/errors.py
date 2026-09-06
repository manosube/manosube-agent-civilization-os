"""Fail-closed Independent Verification errors (Phase 13, Issue #51).

This layer owns typed errors only for its own boundary -- requirement/selection/boundary
admission, and the shape of what an explicit verifier returns. Every Boot/Binding/Store/
Authority/Evidence/Difference/Reflow failure remains that owning domain's own typed error;
this module never catches or reclassifies one, because it never calls into any of them
beyond the one read-only ``store.resolve_record`` provenance check
(``08_VERIFICATION/VERIFICATION_CONTRACT.md`` §5 documents that one call site).
"""

from __future__ import annotations


class IndependentVerificationError(RuntimeError):
    """Base error: an Independent Verification operation could not proceed."""


class VerificationRequirementError(IndependentVerificationError):
    """The supplied requirement/selection/boundary/target does not admit.

    Raised for: a wrong project, a selection that does not apply to the supplied
    requirement, a selection whose own authority or boundary diverges from the
    requirement's, a selection that is not ``ACTIVE``, a malformed or out-of-vocabulary
    target reference, or a target reference this project's Store does not resolve."""


class VerifierOutputError(IndependentVerificationError):
    """The supplied verifier's own return value cannot be trusted as one
    :class:`~manosube_agent_civilization.independent_verification.types.VerificationResult`.

    Raised for: a non-mapping return value, an unrecognized ``status``, a malformed
    ``input_refs``/``observations`` shape, or input references that cite nothing beyond the
    requirement's own target references -- implementation-indistinguishable provenance does
    not satisfy an independent verification requirement (frozen semantic decision 5)."""
