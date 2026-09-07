"""Fail-closed Independent Verification errors (Phase 13, Issue #51).

This layer owns typed errors only for its own boundary -- requirement/selection/boundary
admission, the shape of what an explicit verifier returns, and (Structural Review Round 2,
P13-R2-F2) the linkage between one :class:`~manosube_agent_civilization.
independent_verification.types.VerificationResult` and the existing Evidence request handed
off with it. Every Boot/Binding/Store/Authority/Evidence/Difference/Reflow failure remains
that owning domain's own typed error; this module never catches or reclassifies one, because
this package never calls into any of them beyond the one read-only ``store.resolve_record``
provenance check, the one ``boot_project`` Human Authority re-verification, the one
``authority.evaluate_verifier_selection`` selection-decision re-verification (Structural
Review Round 3, P13-R3-F1), and the one ``evidence.derive_evidence`` handoff call
(``08_VERIFICATION/VERIFICATION_CONTRACT.md`` §5 documents every call site).
"""

from __future__ import annotations


class IndependentVerificationError(RuntimeError):
    """Base error: an Independent Verification operation could not proceed."""


class VerificationRequirementError(IndependentVerificationError):
    """The supplied requirement/selection/boundary/target does not admit.

    Raised for: a wrong project, a selection that does not apply to the supplied
    requirement, a selection whose own authority or boundary diverges from the
    requirement's, a selection that is not ``ACTIVE``, a malformed or out-of-vocabulary
    target reference, a target reference this project's Store does not resolve, or
    (Structural Review Round 3, P13-R3-F1) a ``verifier_selection`` the existing Authority
    owner's own ``evaluate_verifier_selection`` does not answer ``SELECTED`` for -- a
    caller-created selection is never trusted merely because it repeats known-real values."""


class VerifierOutputError(IndependentVerificationError):
    """The supplied verifier's own return value cannot be trusted as one
    :class:`~manosube_agent_civilization.independent_verification.types.VerificationResult`.

    Raised for: a non-mapping return value, an unrecognized ``status``, a malformed
    ``input_refs``/``observations`` shape, or input references that cite nothing beyond the
    requirement's own target references -- implementation-indistinguishable provenance does
    not satisfy an independent verification requirement (frozen semantic decision 5). Also
    raised (Structural Review Round 1, P13-R1-F1) when the supplied ``verifier`` callable's
    own declared identity does not match the SHUKOU-authorized
    :class:`~manosube_agent_civilization.independent_verification.types.VerifierSelection` --
    checked before the callable is ever invoked."""


class VerificationValueError(IndependentVerificationError):
    """A supplied value could not be safely deep-frozen (Structural Review Round 1,
    P13-R1-F3).

    Raised by every immutable value type's own construction for any nested value that is
    neither a ``Mapping``, a ``Sequence`` (excluding ``str``/``bytes``), nor one of the
    JSON-compatible immutable scalars (``str``, ``bytes``, ``int``, ``float``, ``bool``,
    ``None``) -- a ``set`` or any other mutable object is refused rather than silently
    admitted unfrozen, so a value this layer reports as ``frozen`` is always either
    recursively immutable or was never accepted in the first place."""


class EvidenceHandoffError(IndependentVerificationError):
    """The supplied Evidence request cannot be handed off for *this*
    :class:`~manosube_agent_civilization.independent_verification.types.VerificationResult`
    (Structural Review Round 2, P13-R2-F2).

    Raised for: a Change-bound Evidence request (Independent Verification never executes or
    grounds a Change), a request with no ``verification_observation_request`` (the one
    Evidence position this handoff produces), or a derived Evidence record whose own
    ``target.project_id`` or bound Difference does not match the supplied
    ``VerificationResult``. Never raised for the existing Evidence owner's own admission
    failures -- those propagate as :class:`~manosube_agent_civilization.evidence.errors.
    EvidenceError` unchanged."""
