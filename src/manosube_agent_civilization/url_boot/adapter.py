"""The two :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter`
implementations Phase 17 ships (Issue #69).

``FakeUrlSourceAdapter`` is a controlled, in-memory, fully deterministic adapter -- the V1/V2/V4
proof target every unit/contract test in this package's own suites exercises. A caller seeds
exactly the bounded, single-hop transport facts
(:data:`~manosube_agent_civilization.url_boot.types.URL_HOP_RESOLVE_OUTCOMES`/
:data:`~manosube_agent_civilization.url_boot.types.URL_HOP_CONNECT_OUTCOMES`) a real probe of one
explicit hop would honestly report; this adapter never itself decides a redirect, a final
identity, a hop count, a resolved address's own safety, or any content classification -- every
redirect/content/identity/boundary decision belongs solely to
:mod:`~manosube_agent_civilization.url_boot.route` (P17-R1-F2/P17-R2-F1). Its own ``connect_hop``
method (Structural Review Round 3, P17-R3-F1) is **not** part of the
:class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter` Protocol any more -- see
that Protocol's own module-level discussion -- it survives only as this class's own additional,
deterministic-test-only capability, reachable exclusively through this repository's own internal
test-composition path, never through either genuinely-networked public entry point.

``LocalHttpUrlSourceAdapter`` performs the one genuine DNS resolution for one explicit hop, via
:mod:`~manosube_agent_civilization.url_boot.network`'s own :func:`~manosube_agent_civilization.
url_boot.network.resolve_hop_address` -- the V3 vertical-proof target's DNS-resolution half,
exercised against one disposable, local HTTP server this delivery's own test suite starts and
stops itself (``127.0.0.1``, an ephemeral port). It performs no connection of any kind
(Structural Review Round 3, P17-R3-F1) -- see its own class docstring.

**Structural Review Round 1 (P17-R1-F3) correction, further corrected in Round 2
(P17-R2-F2).** This delivery's first version read ``permit_loopback_test_hosts`` out of the
caller-supplied, request-facing ``boundary`` data itself -- an ordinary Boundary field any caller
submitting Boundary *data* could set. Round 1 moved that switch to this adapter's own
constructor, reasoning it was then only reachable by test-composition code -- but Round 2
correctly identified that reasoning as merely *relocating* the same caller-reachable switch one
level earlier: ``LocalHttpUrlSourceAdapter`` is exported from this package's own public surface,
so any caller able to supply the ``adapter`` argument to public ``observe_url_source`` could
still construct exactly that object with ``permit_loopback_test_hosts=True``. This adapter now
carries **no loopback-permitting parameter of any kind, anywhere on its public surface** -- it
never resolves an address's own safety at all (P17-R2-F1 already moved that decision to the
route alone), so it has nothing left to be told to permit. The loopback decision now lives
exclusively in this repository's own trusted, non-shipped test-composition boundary (Structural
Review Round 3, P17-R3-F2) -- see ``tests/fixtures/url_boot_local_test_authority.py``'s own
module docstring.
"""

from __future__ import annotations

from collections.abc import Mapping
import socket
from typing import Any

from .errors import UrlBootAdapterError
from .network import resolve_hop_address
from .types import URL_HOP_CONNECT_OUTCOMES


class FakeUrlSourceAdapter:
    """A controlled, in-memory, fully deterministic
    :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter`.

    Backs every V1/V2/V4 test in this package's own suites. Seeded single-hop facts live only in
    this instance's own dict for the lifetime of the test that constructs it -- no filesystem
    write, no network call, no shared or global state between instances.
    """

    def __init__(self, *, adapter_identity: Mapping[str, Any] | None = None) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "fake_url_source_adapter", "version": "0.1"}
        )
        self._world: dict[tuple[str, str, int, str, str | None, str | None], dict[str, Any]] = {}
        self._forced_resolve_result: Mapping[str, Any] | None = None
        self._forced_connect_result: Mapping[str, Any] | None = None
        self.resolve_call_count = 0
        self.connect_call_count = 0

    @staticmethod
    def _key(
        source_identity: Mapping[str, Any],
    ) -> tuple[str, str, int, str, str | None, str | None]:
        return (
            source_identity["scheme"],
            source_identity["host"],
            source_identity["port"],
            source_identity["path"],
            source_identity["query"],
            source_identity["fragment"],
        )

    def seed_hop(
        self,
        *,
        source_identity: Mapping[str, Any],
        outcome: str = "RESPONSE",
        resolved_address: str = "93.184.216.34",
        response_status: int | None = 200,
        content_type: str | None = "application/json",
        redirect_location: str | None = None,
        body: bytes | None = b"{}",
        oversized: bool = False,
    ) -> None:
        """Declare what a real two-stage probe of *source_identity* would honestly report.

        *outcome* must be one of ``"DNS_FAILURE"`` (:data:`~manosube_agent_civilization.url_boot.
        types.URL_HOP_RESOLVE_OUTCOMES`) or a member of :data:`~manosube_agent_civilization.
        url_boot.types.URL_HOP_CONNECT_OUTCOMES` (``"CONNECTION_FAILURE"``/``"TLS_FAILURE"``/
        ``"TIMEOUT"``/``"RESPONSE"``) -- never ``"BOUNDARY_REFUSED"``, which is purely a
        route-computed verdict no adapter may ever assert (P17-R2-F1); a test that wants the
        route to refuse a hop as unsafe seeds a ``"RESPONSE"``-shaped (or other connect-stage)
        outcome at an unsafe ``resolved_address`` (e.g. a loopback literal) instead, exactly as a
        real DNS lookup returning an unsafe address would.
        """

        if outcome != "DNS_FAILURE" and outcome not in URL_HOP_CONNECT_OUTCOMES:
            raise UrlBootAdapterError(
                f"outcome is not a recognized hop resolve/connect outcome: {outcome!r}"
            )
        if outcome == "DNS_FAILURE":
            self._world[self._key(source_identity)] = {
                "resolve_outcome": "DNS_FAILURE",
                "resolved_address": None,
                "connect_outcome": None,
            }
            return
        if outcome != "RESPONSE":
            self._world[self._key(source_identity)] = {
                "resolve_outcome": "RESOLVED",
                "resolved_address": resolved_address,
                "connect_outcome": outcome,
            }
            return
        self._world[self._key(source_identity)] = {
            "resolve_outcome": "RESOLVED",
            "resolved_address": resolved_address,
            "connect_outcome": "RESPONSE",
            "response_status": response_status,
            "content_type": content_type,
            "redirect_location": redirect_location,
            "body": body if body is not None else b"{}",
            "oversized": oversized,
        }

    def remove_hop(self, *, source_identity: Mapping[str, Any]) -> None:
        """Test-only control surface: simulate the source disappearing (V4 proofs)."""

        self._world.pop(self._key(source_identity), None)

    def force_resolve_result(self, result: Mapping[str, Any] | None) -> None:
        """Test-only control surface: force the exact next ``resolve_hop()`` return value,
        bypassing seeded world state entirely -- used to prove this package's own
        ``UrlBootAdapterError`` fail-closed handling of a malformed or out-of-vocabulary adapter
        report (an adapter bug, never a legitimate transport-level outcome)."""

        self._forced_resolve_result = result

    def force_connect_result(self, result: Mapping[str, Any] | None) -> None:
        """Test-only control surface: force the exact next ``connect_hop()`` return value,
        bypassing seeded world state entirely -- used both for adapter-defect fail-closed proofs
        and to prove the route refuses an adapter that reports having connected to an address
        other than the one the route itself admitted (P17-R2-F1)."""

        self._forced_connect_result = result

    def resolve_hop(self, *, source_identity: Mapping[str, Any]) -> Mapping[str, Any]:
        self.resolve_call_count += 1
        if self._forced_resolve_result is not None:
            return self._forced_resolve_result

        record = self._world.get(self._key(source_identity))
        if record is None or record["resolve_outcome"] == "DNS_FAILURE":
            return {"outcome": "DNS_FAILURE"}
        return {"outcome": "RESOLVED", "resolved_address": record["resolved_address"]}

    def connect_hop(
        self,
        *,
        source_identity: Mapping[str, Any],
        boundary: Mapping[str, Any],
        admitted_address: str,
    ) -> Mapping[str, Any]:
        self.connect_call_count += 1
        if self._forced_connect_result is not None:
            return self._forced_connect_result

        record = self._world.get(self._key(source_identity))
        if record is None or record.get("connect_outcome") is None:
            return {"outcome": "CONNECTION_FAILURE", "resolved_address": None}
        connect_outcome = record["connect_outcome"]
        if connect_outcome != "RESPONSE":
            return {"outcome": connect_outcome, "resolved_address": None}
        return {
            "outcome": "RESPONSE",
            "resolved_address": admitted_address,
            "response_status": record["response_status"],
            "content_type": record["content_type"],
            "redirect_location": record["redirect_location"],
            "body": record["body"],
            "oversized": record["oversized"],
        }


class LocalHttpUrlSourceAdapter:
    """A complete :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter`
    performing the one genuine DNS resolution for one explicit hop -- stdlib ``socket`` only, via
    :mod:`~manosube_agent_civilization.url_boot.network`'s own :func:`resolve_hop_address`. No
    redirect following, no content classification, no resolved-address safety classification of
    any kind (Structural Review Round 2, P17-R2-F1), and (since Structural Review Round 3,
    P17-R3-F1) **no connection of any kind** -- this class carries no method capable of opening a
    socket at all any more.

    **Structural Review Round 3 (P17-R3-F1) correction.** This class previously also implemented
    ``connect_hop``, performing the real bounded HTTP GET itself and reporting the result back to
    the route, which trusted that report as proof of which address was actually reached (checked
    only for after-the-fact disagreement with the address it was handed). A dishonest or buggy
    ``UrlSourceAdapter`` implementation could therefore connect anywhere it pleased and simply
    echo the admitted address back. :func:`~manosube_agent_civilization.url_boot.route.
    observe_url_source` and its disposable-local-test counterpart no longer call any adapter
    method to perform a connection at all -- the real connect-and-fetch step is now
    :mod:`~manosube_agent_civilization.url_boot.network`'s own :func:`
    ~manosube_agent_civilization.url_boot.network.perform_admitted_connection`, called *directly*
    by the route, using only the exact address the route itself already resolved and classified.
    This class's own ``connect_hop`` method (and the ``UrlSourceAdapter`` Protocol member it used
    to implement) is therefore removed rather than merely left unused: a replaceable adapter has
    no call through which to substitute a different destination because there is no method left
    on either the Protocol or this class through which a connection could ever be requested.

    Carries no loopback-related constructor parameter at all (Structural Review Round 2,
    P17-R2-F2) -- see this module's own docstring.

    The V3 vertical-proof target's own DNS-resolution half: exercised in this delivery's own test
    suite against one disposable, local HTTP server the test itself starts and stops
    (``127.0.0.1``, an ephemeral port) -- never a VPS or cloud target, per Issue #69's own
    explicit non-target. The actual HTTP round trip against that server is performed by
    :func:`~manosube_agent_civilization.url_boot.network.perform_admitted_connection` alone.
    """

    def __init__(self, *, adapter_identity: Mapping[str, Any] | None = None) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "local_http_url_source_adapter", "version": "0.1"}
        )

    def resolve_hop(self, *, source_identity: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            address = resolve_hop_address(source_identity["host"], source_identity["port"])
        except socket.gaierror:
            return {"outcome": "DNS_FAILURE"}
        return {"outcome": "RESOLVED", "resolved_address": address}


__all__ = ["FakeUrlSourceAdapter", "LocalHttpUrlSourceAdapter"]
