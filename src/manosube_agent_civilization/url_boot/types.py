"""Closed URL Boot vocabularies and the URL Source Adapter Protocol (Phase 17, Issue #69).

Mirrors :mod:`manosube_agent_civilization.runtime.types`'s own discipline exactly: closed
``frozenset`` vocabularies, a minimal ``Protocol`` a replaceable adapter must satisfy (a
declared ``adapter_identity`` attribute, checked before the adapter is ever called, plus one
bounded ``fetch`` method), and one deep-frozen receipt dataclass carrying nothing an adapter
itself supplied unchecked.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol

from .errors import UrlBootRequirementError

#: The one fetch method this delivery implements end to end -- a single bounded HTTP GET
#: against an explicit, closed Boundary, with a bounded number of per-hop-reauthorized
#: redirects. Extensible later (a second closed literal, never an open string).
URL_FETCH_METHODS: frozenset[str] = frozenset({"HTTP_GET_BOUNDED"})

#: The complete, closed outcome vocabulary a URL Source Observation may ever settle at
#: (P17-C7): every one of the ten named typed failures, plus the one success outcome. All
#: eleven are adapter-reportable here -- unlike Runtime's route-only ``NEGATIVE``/
#: ``IDENTITY_MISMATCH`` split, URL Boot performs no route-level semantic re-interpretation of
#: fetched *content* (fetched content is never trusted to mean anything on its own, per
#: P17-C4), so every member of this vocabulary is an honest classification of what the adapter
#: itself experienced at the transport/boundary layer, never a route-computed judgment about
#: content the adapter already reported honestly.
URL_FETCH_OUTCOMES: frozenset[str] = frozenset(
    {
        "OBSERVED",
        "DNS_FAILURE",
        "CONNECTION_FAILURE",
        "TLS_FAILURE",
        "TIMEOUT",
        "REDIRECT_REFUSED",
        "OVERSIZED_RESPONSE",
        "UNSUPPORTED_MEDIA_TYPE",
        "MALFORMED",
        "IDENTITY_MISMATCH",
        "BOUNDARY_REFUSED",
    }
)

#: The Evidence owner's own closed verification status vocabulary, reused verbatim here as the
#: URL Boot receipt's own ``status`` field, never a second, package-only status vocabulary.
RECEIPT_STATUSES: frozenset[str] = frozenset({"VERIFIED", "FAILED", "UNAVAILABLE"})

#: Every :data:`URL_FETCH_OUTCOMES` member maps to exactly one :data:`RECEIPT_STATUSES` member
#: -- the one shared classification :mod:`~manosube_agent_civilization.url_boot.route` and
#: :mod:`~manosube_agent_civilization.url_boot.evidence_handoff` both read.
URL_OUTCOME_TO_RECEIPT_STATUS: dict[str, str] = {
    "OBSERVED": "VERIFIED",
    "DNS_FAILURE": "UNAVAILABLE",
    "CONNECTION_FAILURE": "UNAVAILABLE",
    "TLS_FAILURE": "UNAVAILABLE",
    "TIMEOUT": "UNAVAILABLE",
    "REDIRECT_REFUSED": "FAILED",
    "OVERSIZED_RESPONSE": "FAILED",
    "UNSUPPORTED_MEDIA_TYPE": "FAILED",
    "MALFORMED": "UNAVAILABLE",
    "IDENTITY_MISMATCH": "FAILED",
    "BOUNDARY_REFUSED": "FAILED",
}


def deep_freeze(value: Any) -> Any:
    """Recursively rebuild *value* into an immutable, alias-free equivalent -- deliberately
    duplicated rather than imported from any other package's own copy, the identical
    decoupling requirement every other owner's own ``deep_freeze`` already states for the
    others."""

    if isinstance(value, Mapping):
        return MappingProxyType({key: deep_freeze(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(deep_freeze(item) for item in value)
    return value


class UrlSourceAdapter(Protocol):
    """The one replaceable transport boundary a URL Source Observation ever reaches through.

    An adapter never owns canonical State, decides Authority, determines Evidence sufficiency,
    closes a Difference, mutates Store internals, interprets fetched content as meaningful, or
    classifies ``IDENTITY_MISMATCH``/``BOUNDARY_REFUSED`` from anything but its own genuine
    transport/DNS experience -- it reports bounded transport facts alone;
    :mod:`~manosube_agent_civilization.url_boot.route` is the sole owner of turning those facts
    into a canonical, independently-verified, committed record.
    """

    adapter_identity: Mapping[str, Any]

    def fetch(
        self, *, source_identity: Mapping[str, Any], boundary: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """Return one bounded transport fetch result.

        Must return a mapping carrying ``fetch_outcome`` (one of :data:`URL_FETCH_OUTCOMES`),
        ``effective_source_identity`` (the canonical decomposed identity actually reached after
        every redirect this call followed, re-authorized against *boundary* at every hop, or
        ``None`` when no response was ever reached), ``response_status`` (the final HTTP status
        code, or ``None``), ``redirect_hop_count`` (an integer, ``0`` when no redirect was
        followed), and ``observed_fields`` (a mapping bounded to
        ``boundary["permitted_fields"]``, or ``None`` when ``fetch_outcome`` is not
        ``"OBSERVED"``) -- never a pre-computed fingerprint: every fingerprint this package
        persists is independently recomputed by the caller, never trusted from the adapter's
        own report.

        An adapter never follows a redirect it has not first re-validated against *boundary*'s
        own ``network_scope`` (P17-C5); a redirect target outside scope, or beyond
        ``boundary["redirect_policy"]["max_redirects"]`` hops, is reported as
        ``"REDIRECT_REFUSED"``, never silently followed and never raised as an uncaught
        exception.
        """
        ...


@dataclass(frozen=True, slots=True)
class UrlSourceObservationReceipt:
    """One immutable URL Source Observation receipt -- the ephemeral, in-memory attestation
    :func:`~manosube_agent_civilization.url_boot.route.observe_url_source` returns to its own
    caller, never itself a Store-committed record (the durable, content-addressed fact is the
    ``url_source_observation_envelope`` record; this receipt is threaded, unchanged, into
    :func:`~manosube_agent_civilization.url_boot.evidence_handoff.
    route_url_observation_to_evidence`)."""

    status: str
    url_source_observation_envelope_id: str
    project_id: str
    requested_source_identity: Mapping[str, Any]
    boundary: Mapping[str, Any]
    adapter_identity: Mapping[str, Any]
    human_authority_ref: Mapping[str, Any]
    input_refs: tuple[Mapping[str, Any], ...]
    observations: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.status not in RECEIPT_STATUSES:
            raise UrlBootRequirementError(
                f"status is not a recognized receipt status: {self.status!r}"
            )
        if not isinstance(self.project_id, str) or not self.project_id:
            raise UrlBootRequirementError(
                f"project_id must be a non-empty string identity: {self.project_id!r}"
            )
        object.__setattr__(
            self, "requested_source_identity", deep_freeze(self.requested_source_identity)
        )
        object.__setattr__(self, "boundary", deep_freeze(self.boundary))
        object.__setattr__(self, "adapter_identity", deep_freeze(self.adapter_identity))
        object.__setattr__(self, "human_authority_ref", deep_freeze(self.human_authority_ref))
        object.__setattr__(self, "input_refs", deep_freeze(tuple(self.input_refs)))
        object.__setattr__(self, "observations", deep_freeze(self.observations))
