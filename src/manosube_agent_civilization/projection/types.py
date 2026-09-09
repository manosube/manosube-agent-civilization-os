"""Immutable, non-persisted Projection value types (Phase 14, Issue #62).

:class:`GitHubObservationReceipt` is what a :class:`GitHubAdapter`'s own ``observe`` call
returns, made explicit and immutable -- exactly as :class:`~manosube_agent_civilization.
independent_verification.types.VerificationResult` already is for Phase 13. It is never
itself a canonical Evidence record, an Authority Decision, a Closure receipt, or a State
transition; it is the caller's own input to
:func:`~manosube_agent_civilization.projection.receipt_handoff.
route_observation_receipt_to_evidence`, exactly as ``VerificationResult`` is the input to
``independent_verification.evidence_handoff.route_verification_result_to_evidence``.

The ``_deep_freeze`` helper below is deliberately duplicated rather than imported from
``boot/context.py`` or ``independent_verification/types.py`` -- the same decoupling
requirement each of those modules' own docstrings already states for one another.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol

from .errors import ProjectionValueError

#: The one closed vocabulary of Projection subject kinds -- the Store-owned record kinds a
#: canonical Difference, Change or Evidence subject may actually resolve as. Difference and
#: Change are never Store-owned record kinds in this vertical
#: (``reflow/reference_registry.py``'s own documented classification); only
#: ``observation_evidence`` resolves through the Store, exactly as Independent Verification's
#: own ``TARGET_REF_KINDS`` already documents for the identical three-kind set.
SUBJECT_REF_KINDS: frozenset[str] = frozenset({"difference", "change", "observation_evidence"})

#: The one closed vocabulary of Projection kinds ``PROJECTION_CONTRACT.md`` §2 fixes --
#: canonical Difference projects to a GitHub Issue, canonical Change projects to a branch/
#: commit/Pull Request, canonical Evidence projects to a check/review/artifact.
PROJECTION_KINDS: frozenset[str] = frozenset(
    {"DIFFERENCE_ISSUE", "CHANGE_PULL_REQUEST", "EVIDENCE_ARTIFACT"}
)

#: The one closed vocabulary of external GitHub artifact kinds a
#: :class:`GitHubAdapter` may ever materialize or observe.
ARTIFACT_KINDS: frozenset[str] = frozenset(
    {"issue", "pull_request", "check_run", "review", "artifact"}
)

#: The identical four-value status vocabulary Independent Verification's own
#: ``VERIFICATION_STATUSES`` already fixes -- a GitHub re-observation confirming a projected
#: artifact still round-trips to its canonical subject is structurally the same kind of
#: independent, Change-free verification result, and reusing the vocabulary lets this
#: package's own receipt occupy the identical, already-ratified Change-Free Verification
#: Evidence position (``evidence/engine.py``'s own ``CHANGE_FREE_VERIFICATION_EVIDENCE``)
#: without widening what that position's own schema-enforced ``status`` enum admits.
RECEIPT_STATUSES: frozenset[str] = frozenset({"VERIFIED", "FAILED", "INSUFFICIENT", "UNAVAILABLE"})

#: The closed vocabulary a :class:`GitHubAdapter`'s own ``observe`` call must classify its own
#: result into (Phase 14, Structural Review Round 1, P14-R1-F6): only ``FOUND`` may carry a
#: content fingerprint for comparison, only ``NOT_FOUND`` is an authoritative absence, and
#: ``PERMISSION_DENIED``/``UNAVAILABLE`` both mean existence itself could not be determined --
#: never collapsed into a claim of absence or of verified content, which would let a
#: permission failure or a transient outage masquerade as either.
OBSERVATION_OUTCOME_KINDS: frozenset[str] = frozenset(
    {"FOUND", "NOT_FOUND", "PERMISSION_DENIED", "UNAVAILABLE"}
)


def _deep_freeze(value: Any) -> Any:
    """Recursively rebuild *value* into an immutable, alias-free equivalent, refusing
    (:class:`~manosube_agent_civilization.projection.errors.ProjectionValueError`) any leaf
    that is neither a ``Mapping``, a ``Sequence`` (excluding ``str``/``bytes``), nor a
    JSON-compatible scalar -- the identical fail-closed discipline Independent Verification's
    own Structural Review Round 1 (P13-R1-F3) already established, applied here rather than
    imported, per this module's own decoupling requirement above."""

    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, str | bytes | int | float | bool) or value is None:
        return value
    raise ProjectionValueError(
        f"value is neither a Mapping, a Sequence, nor a JSON-compatible scalar: {value!r}"
    )


class GitHubAdapter(Protocol):
    """The one explicit adapter boundary Issue #62 requires (``PROJECTION_CONTRACT.md`` §3).

    A provider-neutral protocol -- a real GitHub REST client, a controlled fake for local
    tests, or a Human review interface may all implement it identically; no product,
    library, or transport is selected by this Phase. An implementation must not derive
    Difference meaning, select Change authority, determine Evidence sufficiency, close a
    Difference, transition Canonical State directly, or merge a Pull Request -- this
    Protocol's own two methods admit no such call.
    """

    #: A declared, caller-inspectable identity for the implementing adapter, checked by
    #: :func:`~manosube_agent_civilization.projection.route.project_to_github` before either
    #: method is ever called -- the identical attribute-declaration convention Independent
    #: Verification's own ``IndependentVerifier.verifier_identity`` already establishes.
    adapter_identity: Mapping[str, Any]

    def materialize(
        self,
        *,
        projection_kind: str,
        target_repository: Mapping[str, Any],
        payload: Mapping[str, Any],
        correlation_key: str,
    ) -> Mapping[str, Any]:
        """Create one external GitHub artifact and return its ``external_artifact_ref``.

        Called at most once per genuinely new projection identity -- a replay against an
        already-committed Envelope calls :meth:`observe` instead, never this method again
        (``PROJECTION_CONTRACT.md`` §3: "Replay must observe/reuse the recorded mapping
        rather than blindly creating another artifact").

        *correlation_key* (Phase 14, Structural Review Round 1, P14-R1-F4) is the
        deterministic projection identity (the mapping key) this call is for -- an
        implementation must durably associate it with the artifact it creates (embedded in
        the artifact's own content, or in a provider-native idempotency field) so that
        :meth:`find_by_correlation_key` can recover the same artifact on a later retry,
        without ever creating a second one for the identical key."""

    def find_by_correlation_key(
        self,
        *,
        correlation_key: str,
        target_repository: Mapping[str, Any],
        projection_kind: str,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        """Return the ``external_artifact_ref`` of an artifact already materialized under
        *correlation_key*, or ``None`` if none exists yet.

        Phase 14, Structural Review Round 1 (P14-R1-F4): called before every
        :meth:`materialize` call for a projection identity with no committed Envelope yet --
        including the very first attempt -- so that a prior :meth:`materialize` whose own
        response was lost, or whose Store commit failed after a genuine external success,
        converges on retry instead of creating a duplicate artifact. *payload* is supplied
        only because one artifact kind (``check_run``) needs the commit it would attach to
        (``payload["head_sha"]``) to look itself up; an implementation for a kind that does
        not need it may ignore the argument."""

    def observe(self, *, external_artifact_ref: Mapping[str, Any]) -> Mapping[str, Any]:
        """Re-observe one already-materialized external artifact and report what is
        actually there now -- never what was recorded at materialization time.

        Must return a mapping carrying ``observation_outcome`` (one of
        :data:`OBSERVATION_OUTCOME_KINDS`), ``observed_content_fingerprint`` (``str | None`` --
        required, non-empty, only when ``observation_outcome`` is ``"FOUND"``; ``None``
        otherwise), and ``observed_at`` (an ISO-8601 UTC timestamp string). Structural Review
        Round 1 (P14-R1-F6) requires ``NOT_FOUND`` to mean only an authoritative absence (a
        real 404 for a real, reachable repository) -- a permission failure, rate limit,
        transport error, or unavailable upstream must be reported as ``PERMISSION_DENIED`` or
        ``UNAVAILABLE`` instead, never folded into ``NOT_FOUND`` or into a fabricated
        ``FOUND``. A missing, deleted, or tampered artifact is reported here, as a negative or
        mismatched receipt -- never silently recreated or promoted to a new canonical
        identity."""


@dataclass(frozen=True, slots=True)
class GitHubObservationReceipt:
    """One immutable, non-persisted result of a :class:`GitHubAdapter`'s own ``observe`` call.

    Never itself a canonical Evidence record, Authority Decision, Closure receipt, or State
    transition (the identical frozen semantic decision ``VerificationResult`` already states
    for Phase 13) -- the caller's own explicit input to
    :func:`~manosube_agent_civilization.projection.receipt_handoff.
    route_observation_receipt_to_evidence`.

    ``project_id`` (Phase 14, Structural Review Round 1, P14-R1-F3) is the real project this
    receipt's own projection belongs to, set by :mod:`~manosube_agent_civilization.projection.
    route` from the exact ``project_id`` it already independently verified -- never a
    caller-supplied value at handoff time. Carrying it on the receipt itself, rather than
    trusting a project identity supplied separately to the handoff, is what makes a receipt
    genuinely projected under project A unable to be relabelled as Evidence for project B: the
    handoff can check the receipt's own claim against what the caller actually asked for,
    instead of the caller's claim being the only thing on either side of that comparison.
    """

    status: str
    projection_envelope_id: str
    project_id: str
    subject_ref: Mapping[str, Any]
    external_artifact_ref: Mapping[str, Any]
    adapter_identity: Mapping[str, Any]
    github_authority_ref: Mapping[str, Any]
    input_refs: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    observations: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in RECEIPT_STATUSES:
            raise ProjectionValueError(
                f"status is not a recognized receipt status: {self.status!r}"
            )
        if not isinstance(self.project_id, str) or not self.project_id:
            raise ProjectionValueError(
                f"project_id must be a non-empty string identity: {self.project_id!r}"
            )
        object.__setattr__(self, "subject_ref", _deep_freeze(self.subject_ref))
        object.__setattr__(self, "external_artifact_ref", _deep_freeze(self.external_artifact_ref))
        object.__setattr__(self, "adapter_identity", _deep_freeze(self.adapter_identity))
        object.__setattr__(self, "github_authority_ref", _deep_freeze(self.github_authority_ref))
        object.__setattr__(self, "input_refs", _deep_freeze(tuple(self.input_refs)))
        object.__setattr__(self, "observations", _deep_freeze(self.observations))
