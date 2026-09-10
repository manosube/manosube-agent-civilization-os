"""Closed URL Boot vocabularies and the URL Source Adapter Protocol (Phase 17, Issue #69).

Mirrors :mod:`manosube_agent_civilization.runtime.types`'s own discipline exactly: closed
``frozenset`` vocabularies, a minimal ``Protocol`` a replaceable adapter must satisfy -- since
Structural Review Round 4 (P17-R4-F1), a declared ``adapter_identity`` attribute alone, no
executable method of any kind -- and one deep-frozen receipt dataclass carrying nothing an
adapter itself supplied unchecked.
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

#: The complete, closed *single-hop resolution* outcome vocabulary the one trusted resolve-stage
#: primitive, :func:`~manosube_agent_civilization.url_boot.network.perform_resolution`, may ever
#: report (Structural Review Round 2, P17-R2-F1; **no longer an adapter-reportable vocabulary at
#: all since Structural Review Round 4, P17-R4-F1** -- see :class:`UrlSourceAdapter`'s own
#: module-level discussion). A resolution either genuinely fails (``DNS_FAILURE``) or genuinely
#: returns the one address that lookup returned (``RESOLVED``) -- never classifying that address
#: as safe/unsafe, and never connecting to it: both remain the route's own job alone, in
#: :mod:`~manosube_agent_civilization.url_boot.route`. ``BOUNDARY_REFUSED`` is deliberately absent
#: from every member of either vocabulary below -- it is purely a route-computed verdict about a
#: resolved address the route itself independently classified, never an outcome either trusted
#: primitive itself asserts.
URL_HOP_RESOLVE_OUTCOMES: frozenset[str] = frozenset({"DNS_FAILURE", "RESOLVED"})

#: The complete, closed *single-hop connection* outcome vocabulary the one trusted connect-stage
#: primitive, :func:`~manosube_agent_civilization.url_boot.network.perform_admitted_connection`,
#: may ever report (Structural Review Round 2, P17-R2-F1; **no longer an adapter-reportable
#: vocabulary at all since Structural Review Round 3, P17-R3-F1** -- see :class:`UrlSourceAdapter`
#: 's own module-level discussion). A connection either genuinely fails at the transport layer
#: (``CONNECTION_FAILURE``/``TLS_FAILURE``/``TIMEOUT``) or genuinely completes (``RESPONSE``),
#: full stop -- never ``BOUNDARY_REFUSED``.
URL_HOP_CONNECT_OUTCOMES: frozenset[str] = frozenset(
    {"CONNECTION_FAILURE", "TLS_FAILURE", "TIMEOUT", "RESPONSE"}
)

#: The union of both bounded per-hop vocabularies above -- retained only as a documentation and
#: totality-sweep convenience (every member either :data:`URL_HOP_RESOLVE_OUTCOMES` or
#: :data:`URL_HOP_CONNECT_OUTCOMES` names, nothing else); no single call site is ever validated
#: against this union directly -- :meth:`UrlSourceAdapter.resolve_hop` is checked against
#: :data:`URL_HOP_RESOLVE_OUTCOMES` alone, and :func:`~manosube_agent_civilization.url_boot.
#: network.perform_admitted_connection`'s own return value is checked against
#: :data:`URL_HOP_CONNECT_OUTCOMES` alone, precisely so neither stage can ever report the other
#: stage's own outcome.
URL_HOP_TRANSPORT_OUTCOMES: frozenset[str] = URL_HOP_RESOLVE_OUTCOMES | URL_HOP_CONNECT_OUTCOMES

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
    """The one replaceable identity a URL Source Observation ever carries -- since Structural
    Review Round 4, inert configuration/data only, no executable transport method of any kind.

    **Structural Review Round 1 (P17-R1-F2) correction.** This package's first delivery gave an
    adapter one ``fetch()`` method that followed an entire redirect chain internally and reported
    only the *final* identity, hop count, and outcome -- a conforming-looking but dishonest
    adapter could therefore follow a disallowed intermediate hop, or simply assert a plausible
    final identity/hop count/``IDENTITY_MISMATCH``/``BOUNDARY_REFUSED`` outcome, and the route had
    no way to catch it: it validated only what the adapter chose to report. An adapter now owns
    only bounded, single-hop transport primitives; **the route itself owns the redirect loop**,
    reading each hop's own ``Location`` header from the bounded response itself, and performing
    every redirect/content/identity classification (:data:`URL_FETCH_OUTCOMES`) from those bounded
    facts alone (:mod:`~manosube_agent_civilization.url_boot.route`). An adapter can therefore no
    longer fabricate a hop count, hide an intermediate hop, or assert a route-only classification:
    there is no field left in its own report through which to do so.

    **Structural Review Round 2 (P17-R2-F1) correction.** Round 1's own single ``fetch_one_hop``
    still let a replaceable adapter both *resolve* a hop's address and *classify* whether that
    resolved address was safe to reach at all (``BOUNDARY_REFUSED``) -- the route re-authorized
    only the *hostname* against ``network_scope`` before ever calling the adapter, but the
    adapter's own resolution was still the sole authority for the *resolved address*'s own
    safety, and the adapter's own connection step was the sole authority for *which* address was
    actually reached. A dishonest adapter could therefore report a safe-looking resolved address
    while connecting somewhere else entirely, or simply assert ``BOUNDARY_REFUSED`` for a
    perfectly safe target. This delivery split single-hop transport into two bounded
    primitives with two disjoint, strictly smaller outcome vocabularies
    (:data:`URL_HOP_RESOLVE_OUTCOMES`, :data:`URL_HOP_CONNECT_OUTCOMES` -- neither of which
    contains ``BOUNDARY_REFUSED`` at all): ``resolve_hop`` reported only what a genuine DNS
    lookup returned, never classifying it; the route alone independently classifies that resolved
    address's own safety (loopback/private/link-local/multicast/reserved) and binds it as *this
    hop's one admitted address*, refusing with the route-only outcome ``BOUNDARY_REFUSED`` itself,
    never asking the adapter.

    **Structural Review Round 3 (P17-R3-F1) correction: ``connect_hop`` removed from this
    Protocol entirely.** Round 2's own ``connect_hop`` handed a replaceable adapter the exact
    admitted address and trusted its own report of which address it actually reached -- refusing
    only when that report *disagreed* with what it was handed. That is an after-the-fact
    self-attestation, not a structural guarantee: a dishonest or buggy adapter implementation
    could connect anywhere it pleased and simply echo the admitted address back, and the route
    would have no way to know. The actual connect-and-fetch step became
    :func:`~manosube_agent_civilization.url_boot.network.perform_admitted_connection`'s own job
    alone, called *directly* by :mod:`~manosube_agent_civilization.url_boot.route`.

    **Structural Review Round 4 (P17-R4-F1) correction: ``resolve_hop`` removed from this
    Protocol too.** Round 3's own reasoning applied only to *connection* -- ``resolve_hop``
    remained a Protocol member, still executed as arbitrary caller-supplied Python inside the
    genuine trusted pre-commit network path for every hop. Removing only ``connect_hop`` did not
    make that execution effect-free: a conforming-looking ``resolve_hop`` implementation could
    perform its own, entirely separate network I/O to any address at all as a side effect, then
    return a safe-looking ``RESOLVED`` result naming the real requested host -- nothing checked
    what the adapter's own code *did*, only what it *reported*, and a Protocol method's own name
    constrains shape, never effects. The real DNS lookup is now exclusively
    :func:`~manosube_agent_civilization.url_boot.network.perform_resolution`'s own job, called
    *directly* by the route, the identical structural move Round 3 already made for connection.
    This Protocol therefore declares no executable method of any kind any more -- only
    ``adapter_identity``, inert data recorded in every Envelope/receipt this route ever produces.
    A replaceable ``UrlSourceAdapter`` implementation has **no call through which to perform any
    network I/O at all**, in either genuinely-networked public entry point: not "the report is
    checked", "the side effect is sandboxed", or "the method is differently named", but "there is
    no method on this Protocol, or asked for by either public entry point, through which this
    Protocol's own conformer could ever execute at all".

    An adapter never owns canonical State, decides Authority, determines Evidence sufficiency,
    closes a Difference, mutates Store internals, classifies a resolved address's own safety,
    resolves or connects to any network address at all, or interprets fetched content as
    meaningful -- it is a declared identity, full stop.
    """

    adapter_identity: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class UrlSourceObservationReceipt:
    """One immutable URL Source Observation receipt -- the ephemeral, in-memory attestation the
    closure :func:`~manosube_agent_civilization.url_boot.route.compose_url_source_observer`
    returns produces on every call, never itself a Store-committed record.

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
