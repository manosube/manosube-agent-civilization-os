"""Independent Verification over canonical Evidence (Phase 13, Issue #51):
``KERNEL_ELEMENT=INDEPENDENT_EVIDENCE_ADAPTER``.

Adds exactly one provider-neutral, explicit Independent Verification adapter:

.. code-block:: python

   result = run_independent_verification(
       store,
       project_id=project_id,
       project_binding_id=project_binding_id,
       verification_requirement=requirement,
       verifier_selection=selection,
       verifier_selection_grants=grants,
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
Authority Decision, a Closure receipt, a State transition, or a Merge authorization.

Structural Review Round 1 corrections: the real selection authority is now re-verified
through the existing Boot owner rather than trusted by caller-supplied equality alone
(P13-R1-F2); the callable actually invoked as *verifier* must declare, on itself, the
identical identity SHUKOU selected, checked before it is ever called (P13-R1-F1); and every
immutable value type's own deep-freeze now refuses an unsupported mutable value rather than
returning it unfrozen (P13-R1-F3).

Structural Review Round 2 corrections: a real handoff --
:func:`route_verification_result_to_evidence` -- now connects an admissible
``VerificationResult`` to the existing Evidence owner's own public ``derive_evidence``, rather
than leaving that connection as the caller's own, separate, undocumented concern (P13-R2-F2);
every status, including ``UNAVAILABLE``, now requires the identical distinguishable-input
provenance (P13-R2-F3, superseding Round 0's disclosed ``UNAVAILABLE`` exemption). Round 2 also
disclosed P13-R2-F1 (binding a ``VerifierSelection`` to a real per-Requirement Authority
Decision, not merely a project's own Human Authority reference) as unresolved, since no
existing Authority owner exposed a public surface for it without misusing
``evaluate_authority``'s Change/Difference/State-bound machinery for a purpose it was not
designed for.

Structural Review Round 3 correction (P13-R3-F1) resolves that disclosed gap by extending the
existing Authority owner rather than inventing a second one: ``run_independent_verification``
now takes an explicit *verifier_selection_grants* collection and re-verifies
``verifier_selection`` through the existing Authority owner's own new, dedicated, read-only
:func:`~manosube_agent_civilization.authority.evaluate_verifier_selection` exactly once, before
the verifier is ever called. That surface binds ``project_id``, ``requirement_id``,
``verifier_identity``, ``permitted_boundary``, ``selection_status``, and the real,
Boot-verified selection authority identity to a genuine, content-addressed, Human-Authority-
declared ``verifier_selection_grant`` record -- a caller-created selection duplicating
known-real values without such a grant is refused (``VerificationRequirementError``) with the
verifier called zero times. It introduces no new Authority owner, registry, token, cache, or
Store write of its own (``EXISTING_EVIDENCE_OWNER_HANDOFF_REQUIRED``'s own sibling constraint
for Authority: reuse by call, never a second owner).

See ``08_VERIFICATION/VERIFICATION_INDEX.md`` for the full contract set.
"""

from .errors import (
    EvidenceHandoffError,
    IndependentVerificationError,
    VerificationRequirementError,
    VerificationValueError,
    VerifierOutputError,
)
from .evidence_handoff import route_verification_result_to_evidence
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
    "EvidenceHandoffError",
    "IndependentVerificationError",
    "IndependentVerifier",
    "VerificationRequirement",
    "VerificationRequirementError",
    "VerificationResult",
    "VerificationValueError",
    "VerifierOutputError",
    "VerifierSelection",
    "route_verification_result_to_evidence",
    "run_independent_verification",
]
