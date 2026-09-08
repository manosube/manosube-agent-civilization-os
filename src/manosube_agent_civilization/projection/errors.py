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


class ProjectionConcurrentClaimError(ProjectionError):
    """This attempt does not own the durable claim on this projection identity's mapping
    slot -- a distinct attempt (a genuinely different caller, or the same caller supplying a
    different ``materialized_at``) already claimed it and has not yet resolved to a
    committed Envelope (Structural Review Round 2, Issue #62, P14-R2-F2).

    Raised before ``adapter.materialize`` is ever called: two concurrent callers for the
    identical semantic projection must never both receive permission to POST. The route
    reads no clock and makes no timing assumption about which attempt "wins" -- ownership is
    decided entirely by which attempt's own ``projection_intent`` commit the Store's single
    per-project commit lock admits first."""


class ProjectionReconciliationRequiredError(ProjectionError):
    """This attempt owns the claim on this projection identity's mapping slot, and a prior
    attempt under the identical claim already recorded that it was about to call
    ``adapter.materialize``, but neither a committed Envelope nor a discoverable external
    artifact (via ``adapter.find_by_correlation_key``) exists for it (Structural Review
    Round 2, Issue #62, P14-R2-F2).

    This is genuinely ambiguous: the prior ``materialize`` call may have failed cleanly (safe
    to retry), or it may have succeeded externally while its response was lost before this
    route ever saw it (a blind retry would then create a real, untracked duplicate artifact).
    This route never guesses -- it refuses outright rather than calling ``materialize`` a
    second time under the same claim, and leaves both the claim and the external state as
    they are for an operator to reconcile. A disclosed simplification: this route does not
    itself distinguish "materialize never actually ran" from "materialize ran and failed"
    from "materialize ran and the external system is not yet consistent" -- all three collapse
    to this one fail-closed refusal, which is the correct behavior for all three (never
    silently re-create)."""


class ProjectionAdapterError(ProjectionError):
    """The supplied :class:`~manosube_agent_civilization.projection.types.GitHubAdapter`
    could not materialize or observe the requested external artifact, or its own return value
    cannot be trusted as one materialization/observation result.

    Raised for: a non-mapping return value from ``materialize``/``observe``, a malformed or
    out-of-vocabulary ``artifact_kind``/observation ``status``, or any adapter-reported
    outage, permission denial, rate limit, ambiguous outcome, or transport failure -- this
    route neither retries nor silently substitutes a manufactured success for one of these."""
