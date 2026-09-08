"""Fail-closed Projection errors (Phase 14, Issue #62).

This layer owns typed errors only for its own boundary -- subject/target/payload admission,
the explicit GitHub Authority check, the shape of what a supplied
:class:`~manosube_agent_civilization.projection.types.GitHubAdapter` returns, and the
idempotency/conflict semantics ``PROJECTION_CONTRACT.md`` §3 fixes. Every Boot/Store failure
remains that owning domain's own typed error; this module never catches or reclassifies one,
because this package never calls into any existing owner beyond the one read-only
``store.resolve_record`` subject/reuse-lookup call site, the one ``boot_project`` Human
Authority re-verification, and (for the receipt handoff) the one ``evidence.derive_evidence``
call.
"""

from __future__ import annotations


class ProjectionError(RuntimeError):
    """Base error: a Projection operation could not proceed."""


class ProjectionRequirementError(ProjectionError):
    """The supplied subject/target/payload/authority does not admit.

    Raised for: an unresolvable or wrong-kind subject reference, a subject whose recomputed
    fingerprint does not match what the route derived, a malformed ``target_repository`` or
    ``projection_payload``, or a ``github_authority_ref`` that does not canonical-reference-
    equal the real, Boot-verified Human Authority reference -- a caller-supplied reference is
    never trusted merely because it repeats known-real values."""


class ConflictingProjectionPayloadError(ProjectionRequirementError):
    """A projection identity that already resolves to a committed Envelope was re-requested
    with a different ``projection_payload_fingerprint`` (``PROJECTION_CONTRACT.md`` §3,
    Issue #62's own minimum-acceptable-after-state item 6: ``CONFLICTING_PROJECTION_PAYLOAD``).

    The existing, committed Envelope is never overwritten and no second external artifact is
    materialized on this refusal -- reusing one projection identity with a different semantic
    payload is refused outright, not silently resolved by picking either payload."""


class ProjectionValueError(ProjectionError):
    """A supplied value could not be safely deep-frozen (the identical fail-closed discipline
    Independent Verification's own Structural Review Round 1, P13-R1-F3, already established).

    Raised by :class:`~manosube_agent_civilization.projection.types.GitHubObservationReceipt`'s
    own construction for any nested value that is neither a ``Mapping``, a ``Sequence``
    (excluding ``str``/``bytes``), nor one of the JSON-compatible immutable scalars -- a
    ``set`` or any other mutable object is refused rather than silently admitted unfrozen."""


class ProjectionAdapterError(ProjectionError):
    """The supplied :class:`~manosube_agent_civilization.projection.types.GitHubAdapter`
    could not materialize or observe the requested external artifact, or its own return value
    cannot be trusted as one materialization/observation result.

    Raised for: a non-mapping return value from ``materialize``/``observe``, a malformed or
    out-of-vocabulary ``artifact_kind``/observation ``status``, or any adapter-reported
    outage, permission denial, rate limit, ambiguous outcome, or transport failure -- this
    route neither retries nor silently substitutes a manufactured success for one of these."""
