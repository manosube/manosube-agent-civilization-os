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

#: The complete, closed *overall fetch* outcome vocabulary a URL Source Observation may ever
#: settle at (P17-C7): every one of the ten named typed failures, plus the one success outcome.
#: **Structural Review Round 1 (P17-R1-F2) correction:** unlike this package's first delivery,
#: none of these are accepted from the adapter as a direct assertion any more -- the route alone
#: derives this vocabulary from :data:`URL_HOP_TRANSPORT_OUTCOMES`, the bounded per-hop transport
#: facts the replaceable adapter reports one hop at a time (see :class:`UrlSourceAdapter`'s own
#: module-level discussion). ``IDENTITY_MISMATCH`` in particular is now purely a route-computed
#: judgment about already-bounded response content, never something an adapter's own report can
#: name.
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

#: The complete, closed *single-hop transport* outcome vocabulary a replaceable
#: :class:`UrlSourceAdapter` may ever report from one call to :meth:`UrlSourceAdapter.
#: fetch_one_hop` (Structural Review Round 1, P17-R1-F2). Deliberately smaller than, and
#: strictly upstream of, :data:`URL_FETCH_OUTCOMES`: an adapter reports only what it genuinely
#: observed at the transport layer for *one explicit hop the route itself chose* -- never a
#: final/effective identity, never a redirect-hop count, never ``IDENTITY_MISMATCH`` or
#: ``MALFORMED`` or any other outcome that depends on interpreting response *content* or on
#: following more than one hop. Every one of those remaining outcomes is derived by the route
#: alone, from these bounded per-hop facts, in :mod:`~manosube_agent_civilization.url_boot.route`.
URL_HOP_TRANSPORT_OUTCOMES: frozenset[str] = frozenset(
    {
        "DNS_FAILURE",
        "CONNECTION_FAILURE",
        "TLS_FAILURE",
        "TIMEOUT",
        "BOUNDARY_REFUSED",
        "RESPONSE",
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

    **Structural Review Round 1 (P17-R1-F2) correction.** This package's first delivery gave an
    adapter one ``fetch()`` method that followed an entire redirect chain internally and reported
    only the *final* identity, hop count, and outcome -- a conforming-looking but dishonest
    adapter could therefore follow a disallowed intermediate hop, or simply assert a plausible
    final identity/hop count/``IDENTITY_MISMATCH``/``BOUNDARY_REFUSED`` outcome, and the route had
    no way to catch it: it validated only what the adapter chose to report. An adapter now owns
    only the one bounded, single-hop transport primitive below; **the route itself owns the
    redirect loop**, calling :meth:`fetch_one_hop` once per hop with the exact
    ``source_identity`` *it* has already independently re-authorized against ``boundary``'s own
    ``network_scope``, reading each hop's own ``Location`` header from the bounded response
    itself, and performing every redirect/content/identity classification
    (:data:`URL_FETCH_OUTCOMES`) from those bounded facts alone
    (:mod:`~manosube_agent_civilization.url_boot.route`). An adapter can therefore no longer
    fabricate a hop count, hide an intermediate hop, or assert a route-only classification: there
    is no field left in its own report through which to do so.

    An adapter never owns canonical State, decides Authority, determines Evidence sufficiency,
    closes a Difference, mutates Store internals, or interprets fetched content as meaningful --
    it reports bounded, single-hop transport facts alone.
    """

    adapter_identity: Mapping[str, Any]

    def fetch_one_hop(
        self, *, source_identity: Mapping[str, Any], boundary: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """Perform exactly one bounded HTTP GET against *source_identity* -- no redirect
        following, no content-type/size/identity classification, and no boundary decision of any
        kind beyond the adapter's own genuine transport/DNS/TLS experience for *this one hop*:
        every one of those remains the route's own job, never this method's.

        Must return a mapping whose ``outcome`` is one of :data:`URL_HOP_TRANSPORT_OUTCOMES`:

        - a pre-response failure (``DNS_FAILURE``/``CONNECTION_FAILURE``/``TLS_FAILURE``/
          ``TIMEOUT``/``BOUNDARY_REFUSED``) -- carrying ``resolved_address: None``, since no
          response, and in the unsafe-address case no connection either, was ever reached;
        - ``RESPONSE`` -- a completed HTTP round trip, carrying ``resolved_address`` (the exact,
          single address this hop's own DNS resolution used and connected to -- never re-resolved
          a second time for this same hop), ``response_status`` (the real HTTP status code),
          ``content_type`` (the response's own ``Content-Type`` header, lowercased, with any
          parameters stripped, or ``None``), ``redirect_location`` (the response's own
          ``Location`` header when ``300 <= response_status < 400``, else ``None``), ``body``
          (the raw response bytes, bounded to ``boundary["max_response_bytes"]``), and
          ``oversized`` (``True`` when the real response exceeded that bound).

        Never a pre-computed fingerprint, a final/effective identity, or a redirect-hop count:
        every one of those is derived or recomputed by the route alone, from these bounded facts,
        never trusted from the adapter's own report.
        """
        ...


@dataclass(frozen=True, slots=True)
class UrlSourceObservationReceipt:
    """One immutable URL Source Observation receipt -- the ephemeral, in-memory attestation
    :func:`~manosube_agent_civilization.url_boot.route.observe_url_source` returns to its own
    caller, never itself a Store-committed record.

    **Structural Review Round 1 (P17-R1-F1) correction.** ``url_source_observation_envelope_id``
    is ``None`` whenever ``status`` is not ``"VERIFIED"``: a failed or refused fetch commits
    nothing at all (P17-C7's own "no failed or refused fetch may mutate canonical State"), so
    there is no ``url_source_observation_envelope`` record for such a receipt to name. Only a
    ``"VERIFIED"`` receipt (``fetch_outcome == "OBSERVED"``) ever names a real, committed
    envelope -- the durable, content-addressed fact
    :func:`~manosube_agent_civilization.url_boot.evidence_handoff.
    route_url_observation_to_evidence` resolves and independently re-verifies before deriving any
    Evidence from it."""

    status: str
    url_source_observation_envelope_id: str | None
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
        if self.status == "VERIFIED":
            if not self.url_source_observation_envelope_id:
                raise UrlBootRequirementError(
                    "a VERIFIED receipt must name the real, committed envelope it attests to"
                )
        elif self.url_source_observation_envelope_id is not None:
            raise UrlBootRequirementError(
                f"a {self.status!r} receipt must name no committed envelope (P17-C7) -- got "
                f"{self.url_source_observation_envelope_id!r}"
            )
        object.__setattr__(
            self, "requested_source_identity", deep_freeze(self.requested_source_identity)
        )
        object.__setattr__(self, "boundary", deep_freeze(self.boundary))
        object.__setattr__(self, "adapter_identity", deep_freeze(self.adapter_identity))
        object.__setattr__(self, "human_authority_ref", deep_freeze(self.human_authority_ref))
        object.__setattr__(self, "input_refs", deep_freeze(tuple(self.input_refs)))
        object.__setattr__(self, "observations", deep_freeze(self.observations))
