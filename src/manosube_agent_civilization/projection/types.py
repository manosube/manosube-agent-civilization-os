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
    ) -> Mapping[str, Any]:
        """Create one external GitHub artifact and return its ``external_artifact_ref``.

        Called at most once per genuinely new projection identity -- a replay against an
        already-committed Envelope calls :meth:`observe` instead, never this method again
        (``PROJECTION_CONTRACT.md`` §3: "Replay must observe/reuse the recorded mapping
        rather than blindly creating another artifact")."""

    def observe(self, *, external_artifact_ref: Mapping[str, Any]) -> Mapping[str, Any]:
        """Re-observe one already-materialized external artifact and report what is
        actually there now -- never what was recorded at materialization time.

        Must return a mapping carrying at least ``status`` (one of :data:`RECEIPT_STATUSES`),
        ``exists`` (``bool``), ``observed_content_fingerprint`` (``str | None``, ``None`` only
        when ``exists`` is ``False``) and ``observed_at`` (an ISO-8601 UTC timestamp string).
        A missing, deleted, or tampered artifact is reported here, as a negative or mismatched
        receipt -- never silently recreated or promoted to a new canonical identity."""


@dataclass(frozen=True, slots=True)
class GitHubObservationReceipt:
    """One immutable, non-persisted result of a :class:`GitHubAdapter`'s own ``observe`` call.

    Never itself a canonical Evidence record, Authority Decision, Closure receipt, or State
    transition (the identical frozen semantic decision ``VerificationResult`` already states
    for Phase 13) -- the caller's own explicit input to
    :func:`~manosube_agent_civilization.projection.receipt_handoff.
    route_observation_receipt_to_evidence`.
    """

    status: str
    projection_envelope_id: str
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
        object.__setattr__(self, "subject_ref", _deep_freeze(self.subject_ref))
        object.__setattr__(self, "external_artifact_ref", _deep_freeze(self.external_artifact_ref))
        object.__setattr__(self, "adapter_identity", _deep_freeze(self.adapter_identity))
        object.__setattr__(self, "github_authority_ref", _deep_freeze(self.github_authority_ref))
        object.__setattr__(self, "input_refs", _deep_freeze(tuple(self.input_refs)))
        object.__setattr__(self, "observations", _deep_freeze(self.observations))
