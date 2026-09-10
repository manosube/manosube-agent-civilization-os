"""The two :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter`
implementations Phase 17 ships (Issue #69).

``FakeUrlSourceAdapter`` is a controlled, in-memory, fully deterministic adapter -- the V1/V2/V4
proof target every unit/contract test in this package's own suites exercises. A caller seeds
exactly the bounded, single-hop transport fact
(:data:`~manosube_agent_civilization.url_boot.types.URL_HOP_TRANSPORT_OUTCOMES`) a real probe of
one explicit hop would honestly report; this adapter never itself decides a redirect, a final
identity, a hop count, or any content classification -- real per-hop transport classification of
a genuine probe belongs solely to :class:`LocalHttpUrlSourceAdapter`, and every redirect/content/
identity decision belongs solely to
:mod:`~manosube_agent_civilization.url_boot.route` (P17-R1-F2).

``LocalHttpUrlSourceAdapter`` is a genuine, complete implementation of exactly one bounded HTTP
GET for one explicit hop, built entirely on
:mod:`~manosube_agent_civilization.url_boot.network`'s own resolve-once-connect-to-that-address
primitive -- the V3 vertical-proof target, exercised against one disposable, local HTTP server
this delivery's own test suite starts and stops itself (``127.0.0.1``, an ephemeral port).

**Structural Review Round 1 (P17-R1-F3) correction.** This delivery's first version read
``permit_loopback_test_hosts`` out of the caller-supplied, request-facing ``boundary`` data
itself -- an ordinary Boundary field any caller submitting Boundary *data* could set, letting any
production caller mint its own loopback-test authority by construction. That field no longer
exists anywhere in the closed Boundary schema at all (``01_SCHEMA/url_boot/
url_source_observation_envelope.schema.json``'s own ``network_scope`` no longer names it, and
``additionalProperties: false`` refuses a caller who still tries). The one place this allowance
can now be set is this adapter's own constructor -- a Python call only test-composition code
ever makes, never something reachable from ``source_identity``/``boundary`` request data, and
never inspected or branched on by the route (no ``isinstance`` check, no sentinel value crossing
``observe_url_source``'s own public surface): ``LocalHttpUrlSourceAdapter(
permit_loopback_test_hosts=True)`` is a composition-time decision about *which adapter object is
constructed at all*, exactly the same kind of decision choosing ``FakeUrlSourceAdapter`` over
``LocalHttpUrlSourceAdapter`` already is -- never something a request-facing caller who only ever
supplies data can reach.
"""

from __future__ import annotations

from collections.abc import Mapping
import socket
import ssl
from typing import Any

from .errors import UrlBootAdapterError
from .network import UnsafeResolvedAddressError, fetch_one_hop
from .types import URL_HOP_TRANSPORT_OUTCOMES


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
        self._forced_result: Mapping[str, Any] | None = None
        self.fetch_call_count = 0

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
        resolved_address: str = "203.0.113.10",
        response_status: int | None = 200,
        content_type: str | None = "application/json",
        redirect_location: str | None = None,
        body: bytes | None = b"{}",
        oversized: bool = False,
    ) -> None:
        """Declare what a real single-hop probe of *source_identity* would honestly report.

        *outcome* must be one of
        :data:`~manosube_agent_civilization.url_boot.types.URL_HOP_TRANSPORT_OUTCOMES`. A
        pre-response failure (anything but ``"RESPONSE"``) carries no other field -- exactly the
        shape :class:`LocalHttpUrlSourceAdapter` itself reports for one.
        """

        if outcome not in URL_HOP_TRANSPORT_OUTCOMES:
            raise UrlBootAdapterError(
                f"outcome is not a recognized hop transport outcome: {outcome!r}"
            )
        if outcome != "RESPONSE":
            self._world[self._key(source_identity)] = {"outcome": outcome, "resolved_address": None}
            return
        self._world[self._key(source_identity)] = {
            "outcome": "RESPONSE",
            "resolved_address": resolved_address,
            "response_status": response_status,
            "content_type": content_type,
            "redirect_location": redirect_location,
            "body": body if body is not None else b"{}",
            "oversized": oversized,
        }

    def remove_hop(self, *, source_identity: Mapping[str, Any]) -> None:
        """Test-only control surface: simulate the source disappearing (V4 proofs)."""

        self._world.pop(self._key(source_identity), None)

    def force_result(self, result: Mapping[str, Any] | None) -> None:
        """Test-only control surface: force the exact next ``fetch_one_hop()`` return value,
        bypassing seeded world state entirely -- used to prove this package's own
        ``UrlBootAdapterError`` fail-closed handling of a malformed or out-of-vocabulary adapter
        report (an adapter bug, never a legitimate transport-level outcome)."""

        self._forced_result = result

    def fetch_one_hop(
        self, *, source_identity: Mapping[str, Any], boundary: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        self.fetch_call_count += 1
        if self._forced_result is not None:
            return self._forced_result

        record = self._world.get(self._key(source_identity))
        if record is None:
            return {"outcome": "CONNECTION_FAILURE", "resolved_address": None}
        return dict(record)


class LocalHttpUrlSourceAdapter:
    """A complete :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter`
    performing exactly one real, bounded HTTP GET for one explicit hop -- stdlib
    ``socket``/``http.client``/``ssl`` only, via
    :func:`~manosube_agent_civilization.url_boot.network.fetch_one_hop`. No redirect following,
    no content classification: both are the route's own job (P17-R1-F2).

    The V3 vertical-proof target: exercised in this delivery's own test suite against one
    disposable, local HTTP server the test itself starts and stops (``127.0.0.1``, an ephemeral
    port) -- never a VPS or cloud target, per Issue #69's own explicit non-target.
    """

    def __init__(
        self,
        *,
        adapter_identity: Mapping[str, Any] | None = None,
        permit_loopback_test_hosts: bool = False,
    ) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "local_http_url_source_adapter", "version": "0.1"}
        )
        # P17-R1-F3: an instance attribute set once at construction, never read from
        # request-facing ``boundary`` data -- the one and only place this allowance can be
        # reached from, and only by whatever code composed this exact adapter instance.
        self._permit_loopback_test_hosts = permit_loopback_test_hosts

    def fetch_one_hop(
        self, *, source_identity: Mapping[str, Any], boundary: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        try:
            result = fetch_one_hop(
                dict(source_identity),
                timeout_seconds=boundary["timeout_seconds"],
                max_response_bytes=boundary["max_response_bytes"],
                permit_loopback_test_hosts=self._permit_loopback_test_hosts,
            )
        except UnsafeResolvedAddressError:
            return {"outcome": "BOUNDARY_REFUSED", "resolved_address": None}
        except socket.gaierror:
            return {"outcome": "DNS_FAILURE", "resolved_address": None}
        except TimeoutError:
            return {"outcome": "TIMEOUT", "resolved_address": None}
        except ssl.SSLError:
            return {"outcome": "TLS_FAILURE", "resolved_address": None}
        except OSError:
            return {"outcome": "CONNECTION_FAILURE", "resolved_address": None}

        content_type = result["headers"].get("content-type", "").split(";")[0].strip().lower()
        return {
            "outcome": "RESPONSE",
            "resolved_address": result["resolved_address"],
            "response_status": result["status"],
            "content_type": content_type or None,
            "redirect_location": result["redirect_location"],
            "body": result["body"],
            "oversized": result["oversized"],
        }


__all__ = ["FakeUrlSourceAdapter", "LocalHttpUrlSourceAdapter"]
