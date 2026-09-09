"""Closed Model Runtime vocabularies and the Model Adapter Protocol (Phase 16, Issue #66).

Mirrors :mod:`manosube_agent_civilization.runtime.types`'s own discipline exactly: closed
``frozenset`` vocabularies, a minimal ``Protocol`` a replaceable adapter must satisfy (a
declared ``adapter_identity`` attribute, checked before the adapter is ever called, plus one
bounded ``execute`` method), and one deep-frozen receipt dataclass carrying nothing an adapter
itself supplied unchecked.

**Why the two outcome vocabularies differ by exactly one member.** P16-C3 requires model output
to be an untrusted candidate, never a self-authenticating result. That is achieved here the way
Phase 15 achieved it for a transport probe: the *accepting* classification does not exist in the
vocabulary an adapter may report at all. An adapter may say ``"CANDIDATE"`` -- "here is what I
produced" -- and nothing more; only :mod:`~manosube_agent_civilization.model_runtime.route`,
after independently projecting that candidate down to the Model Execution Boundary's own
``permitted_candidate_fields`` and independently re-fingerprinting the projection, ever computes
``"CANDIDATE_ACCEPTED"``. An adapter that returned ``"CANDIDATE_ACCEPTED"`` itself is refused as
an adapter defect, not recorded as a success.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol

from .errors import ModelRuntimeRequirementError

#: The one capability this delivery proves end to end. Deliberately a single closed literal
#: rather than a general capability taxonomy -- extensible later (a second closed literal, never
#: an open string) exactly as :data:`~manosube_agent_civilization.runtime.types.
#: RUNTIME_OBSERVATION_METHODS` started at one known value and stays closed. The vocabulary
#: itself is owned by ``01_SCHEMA/model_runtime/model_execution_boundary.schema.json``.
MODEL_EXECUTION_CAPABILITIES: frozenset[str] = frozenset({"PROPOSE_EVIDENCE_CANDIDATE"})

#: The closed kinds of candidate a model may ever propose under this delivery's own Boundary.
#: A candidate is a *proposal about what was observed*, never a Difference closure, a Change, an
#: Authority grant, or an Evidence record -- none of which has a member here, by construction.
MODEL_CANDIDATE_KINDS: frozenset[str] = frozenset({"OBSERVATION_CANDIDATE"})

#: The complete, closed outcome vocabulary a Model Execution may ever settle at -- the canonical
#: classification :func:`~manosube_agent_civilization.model_runtime.route.
#: execute_model_work_unit` computes, independently of whatever an adapter itself claims.
#:
#: Every member is *distinct and terminal for its own meaning* (P16-C6): unavailability, refusal,
#: malformed output, timeout, cancellation and incomplete evidence are six separate facts, none
#: of which is ever folded into another, promoted into ``CANDIDATE_ACCEPTED``, or silently
#: recorded as an authoritative absence of a result.
MODEL_EXECUTION_OUTCOMES: frozenset[str] = frozenset(
    {
        "CANDIDATE_ACCEPTED",
        "UNAVAILABLE",
        "REFUSED",
        "MALFORMED",
        "TIMEOUT",
        "CANCELLED",
        "INCOMPLETE_EVIDENCE",
    }
)

#: What a :class:`ModelAdapter` may honestly report from its own execution alone, before this
#: package's own independent Boundary projection and re-fingerprinting. ``CANDIDATE_ACCEPTED``
#: is deliberately **absent** and ``CANDIDATE`` is deliberately **present only here**: see this
#: module's own docstring. An adapter that reported ``CANDIDATE_ACCEPTED`` would be
#: self-authenticating its own semantic classification, exactly the "model output as
#: self-authenticating truth" failure P16-C3 forbids.
MODEL_ADAPTER_OUTCOMES: frozenset[str] = frozenset(
    {
        "CANDIDATE",
        "UNAVAILABLE",
        "REFUSED",
        "MALFORMED",
        "TIMEOUT",
        "CANCELLED",
        "INCOMPLETE_EVIDENCE",
    }
)

#: The Evidence owner's own closed verification status vocabulary (Independent Verification's
#: ``VERIFICATION_STATUSES``, reused verbatim here as the Model Runtime receipt's own ``status``
#: field, never a second, Model-Runtime-only status vocabulary -- the identical reuse
#: :data:`~manosube_agent_civilization.runtime.types.RECEIPT_STATUSES` already makes).
RECEIPT_STATUSES: frozenset[str] = frozenset({"VERIFIED", "FAILED", "INSUFFICIENT", "UNAVAILABLE"})

#: Every :data:`MODEL_EXECUTION_OUTCOMES` member maps to exactly one :data:`RECEIPT_STATUSES`
#: member -- the one shared classification :mod:`~manosube_agent_civilization.model_runtime.
#: route` and :mod:`~manosube_agent_civilization.model_runtime.evidence_handoff` both read, so
#: the two sites can only ever disagree over genuine content, never over mapping-table drift
#: between two independently maintained copies.
#:
#: ``INCOMPLETE_EVIDENCE`` maps to ``INSUFFICIENT`` and to nothing else: P16-C6 forbids
#: converting incomplete evidence into success *or* into authoritative absence, and
#: ``INSUFFICIENT`` is the one existing status that means exactly "not enough, and that is not
#: the same as absent".
MODEL_OUTCOME_TO_RECEIPT_STATUS: dict[str, str] = {
    "CANDIDATE_ACCEPTED": "VERIFIED",
    "REFUSED": "FAILED",
    "UNAVAILABLE": "UNAVAILABLE",
    "TIMEOUT": "UNAVAILABLE",
    "CANCELLED": "UNAVAILABLE",
    "MALFORMED": "UNAVAILABLE",
    "INCOMPLETE_EVIDENCE": "INSUFFICIENT",
}

#: Exactly the keys :mod:`~manosube_agent_civilization.model_runtime.route` ever reads back out
#: of an adapter's own returned mapping. Pinned as a value rather than left implicit in the
#: route's own body so that P16-C3's decisive control can be proved *structurally*: a return
#: value carrying ``authority_ref``, ``evidence``, ``difference_closed``, a decision record or a
#: commit instruction has no call shape at all here -- those keys are never read, by anyone, at
#: any point.
MODEL_ADAPTER_RESULT_KEYS: tuple[str, ...] = (
    "adapter_outcome",
    "candidate_kind",
    "candidate_fields",
)


def deep_freeze(value: Any) -> Any:
    """Recursively rebuild *value* into an immutable, alias-free equivalent -- deliberately
    duplicated rather than imported from ``boot/context.py``, ``projection/types.py`` or
    ``runtime/types.py``, the identical decoupling requirement each of those modules' own
    docstrings already states for one another.

    Package-public for the identical reason
    :func:`~manosube_agent_civilization.runtime.types.deep_freeze` is: the route hands a
    replaceable adapter deep-frozen copies of the exact canonical request it validated, so an
    adapter cannot mutate in place what the route goes on to fingerprint, persist, and attest
    to.
    """

    if isinstance(value, Mapping):
        return MappingProxyType({key: deep_freeze(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(deep_freeze(item) for item in value)
    return value


class ModelAdapter(Protocol):
    """The one replaceable model/provider boundary a Model Execution ever reaches through.

    An adapter never owns canonical State, decides Authority, determines Evidence sufficiency,
    closes a Difference, commits a Change, mutates Store internals, widens its own Boundary or
    capability, or classifies its own outcome as ``CANDIDATE_ACCEPTED`` -- it reports what it
    produced and nothing else; :mod:`~manosube_agent_civilization.model_runtime.route` is the
    sole owner of turning that into a canonical, independently-bounded outcome.

    Provider-specific payloads, chat transcripts, hidden model memory and provider session ids
    are not canonical inputs (P16-C1) and there is no parameter through which one could arrive:
    ``execute`` receives exactly one argument, and it is the provider-neutral canonical request
    :func:`~manosube_agent_civilization.model_runtime.route.execute_model_work_unit` derives
    from Store-resolved records alone.
    """

    adapter_identity: Mapping[str, Any]

    def execute(self, *, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return one bounded, provider-neutral execution result.

        Must return a mapping carrying ``adapter_outcome`` (one of
        :data:`MODEL_ADAPTER_OUTCOMES`), ``candidate_kind`` (one of
        :data:`MODEL_CANDIDATE_KINDS`, or ``None`` when ``adapter_outcome`` is not
        ``"CANDIDATE"``), and ``candidate_fields`` (a mapping bounded to
        ``request["boundary"]["permitted_candidate_fields"]``, or ``None`` when
        ``adapter_outcome`` is not ``"CANDIDATE"``) -- never a pre-computed fingerprint, never a
        claimed acceptance, and never a raw provider payload.

        **Never raises for an ordinary operational failure.** Unavailability, refusal, malformed
        output, timeout, cancellation and incomplete evidence are typed *return values*
        (P16-C6), not exceptions: an adapter that raised instead would make the six
        indistinguishable at the one place they must stay distinct.
        """
        ...


@dataclass(frozen=True, slots=True)
class ModelExecutionReceipt:
    """One immutable Model Execution receipt -- the ephemeral, in-memory attestation
    :func:`~manosube_agent_civilization.model_runtime.route.execute_model_work_unit` returns to
    its own caller, never itself a Store-committed record.

    The durable, content-addressed fact is the ``model_execution_envelope`` record; this receipt
    is threaded, unchanged, into :func:`~manosube_agent_civilization.model_runtime.
    evidence_handoff.route_model_execution_to_evidence`, which re-resolves the real Envelope
    from Store and never trusts this object -- exactly as
    :class:`~manosube_agent_civilization.runtime.types.RuntimeObservationReceipt` is never
    itself committed or trusted either.
    """

    status: str
    model_execution_envelope_id: str
    project_id: str
    model_work_unit_ref: Mapping[str, Any]
    adapter_identity: Mapping[str, Any]
    difference_ref: Mapping[str, Any]
    authority_ref: Mapping[str, Any]
    boundary_ref: Mapping[str, Any]
    required_capability: str
    evidence_requirements: Mapping[str, Any]
    human_authority_ref: Mapping[str, Any]
    input_refs: tuple[Mapping[str, Any], ...]
    observations: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.status not in RECEIPT_STATUSES:
            raise ModelRuntimeRequirementError(
                f"status is not a recognized receipt status: {self.status!r}"
            )
        if not isinstance(self.project_id, str) or not self.project_id:
            raise ModelRuntimeRequirementError(
                f"project_id must be a non-empty string identity: {self.project_id!r}"
            )
        if self.required_capability not in MODEL_EXECUTION_CAPABILITIES:
            raise ModelRuntimeRequirementError(
                f"required_capability is not recognized: {self.required_capability!r}"
            )
        for field in (
            "model_work_unit_ref",
            "adapter_identity",
            "difference_ref",
            "authority_ref",
            "boundary_ref",
            "evidence_requirements",
            "human_authority_ref",
            "observations",
        ):
            object.__setattr__(self, field, deep_freeze(getattr(self, field)))
        object.__setattr__(self, "input_refs", deep_freeze(tuple(self.input_refs)))
