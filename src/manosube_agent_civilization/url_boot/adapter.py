"""The two :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter`
implementations Phase 17 ships (Issue #69).

``FakeUrlSourceAdapter`` is a controlled, in-memory, fully deterministic adapter -- the V1/V2/V4
proof target every unit/contract test in this package's own suites exercises. A caller seeds
exactly the :data:`~manosube_agent_civilization.url_boot.types.URL_FETCH_OUTCOMES` member a real
probe would honestly report; this adapter never itself decides ``IDENTITY_MISMATCH`` or
``BOUNDARY_REFUSED`` from anything but what it was told to report -- real classification of a
genuine transport probe belongs solely to :class:`LocalHttpUrlSourceAdapter`, mirroring exactly
how :mod:`~manosube_agent_civilization.runtime.route`, not
:class:`~manosube_agent_civilization.runtime.adapter.FakeRuntimeAdapter`, owns that decision in
Runtime.

``LocalHttpUrlSourceAdapter`` is a genuine, complete implementation performing one real, bounded
HTTP GET plus a bounded, per-hop-reauthorized redirect-following loop (P17-C5), built entirely on
:mod:`~manosube_agent_civilization.url_boot.network`'s own resolve-once-connect-to-that-address
primitive -- the V3 vertical-proof target, exercised against one disposable, local HTTP server
this delivery's own test suite starts and stops itself (``127.0.0.1``, an ephemeral port, admitted
only when the Boundary's own ``network_scope.permit_loopback_test_hosts`` is explicitly ``True`` --
never a VPS or cloud target, per Issue #69's own explicit non-target).

This is the one module besides :mod:`~manosube_agent_civilization.url_boot.network` itself
permitted to catch (never raise past its own boundary) the low-level transport exception types
:mod:`~manosube_agent_civilization.url_boot.network` deliberately lets escape (``socket.gaierror``,
``TimeoutError``, ``OSError``, ``ssl.SSLError``) -- classifying each into one honest, closed
:data:`~manosube_agent_civilization.url_boot.types.URL_FETCH_OUTCOMES` member, never letting one
escape uncaught to a route or a caller.

**Disclosed judgment call.** The closed outcome vocabulary (P17-C7) has no member for "a complete,
readable HTTP response whose status is outside 2xx/3xx" -- unlike Runtime's own richer
``NOT_FOUND``/``PERMISSION_DENIED`` split, URL Boot's contract names only ``MALFORMED`` for a
response that fails to honestly answer the bounded question asked. This adapter therefore reports
such a response (4xx/5xx, after every permitted redirect has already been followed) as
``MALFORMED``, carrying the real ``response_status`` alongside it so nothing about the real status
code is lost -- never a silent, undisclosed narrowing.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import socket
import ssl
from typing import Any
from urllib.parse import urljoin

from .errors import UrlBootAdapterError
from .network import (
    UnsafeResolvedAddressError,
    canonical_source_identity,
    fetch_one_hop,
    require_source_within_network_scope,
    source_url,
)
from .types import URL_FETCH_OUTCOMES

#: The same "no response was ever reached" outcome set the route itself now enforces
#: (:mod:`~manosube_agent_civilization.url_boot.route`'s own ``_NO_IDENTITY_OUTCOMES``) --
#: duplicated here, deliberately, rather than imported, the identical decoupling requirement
#: every other owner's own closed vocabulary already keeps between test-fixture and production
#: code. Used only to pick :meth:`FakeUrlSourceAdapter.seed_source`'s own honest default.
_NO_RESPONSE_OUTCOMES = frozenset(
    {
        "DNS_FAILURE",
        "CONNECTION_FAILURE",
        "TLS_FAILURE",
        "TIMEOUT",
        "BOUNDARY_REFUSED",
        "REDIRECT_REFUSED",
    }
)


class FakeUrlSourceAdapter:
    """A controlled, in-memory, fully deterministic
    :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter`.

    Backs every V1/V2/V4 test in this package's own suites. Seeded sources live only in this
    instance's own dict for the lifetime of the test that constructs it -- no filesystem write,
    no network call, no shared or global state between instances.
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

    def seed_source(
        self,
        *,
        source_identity: Mapping[str, Any],
        fields: Mapping[str, Any],
        fetch_outcome: str = "OBSERVED",
        effective_source_identity: Mapping[str, Any] | None = None,
        response_status: int | None = 200,
        redirect_hop_count: int = 0,
    ) -> None:
        """Declare what a real probe of *source_identity* would honestly report.

        *effective_source_identity*, left ``None``, defaults to *source_identity* itself for
        every outcome where a real probe would honestly have identified a reached source -- a
        direct, unredirected reach -- and to ``None`` itself for the outcomes where a real probe
        never reaches a response at all (mirrors :class:`LocalHttpUrlSourceAdapter`'s own
        ``_failure``/``_classify_response`` split exactly, so a caller who does not override this
        argument still cannot seed an outcome-inconsistent report). Passing an explicit, different
        identity is exactly how a V2 redirect-following proof is built. *fetch_outcome* must be
        one of :data:`~manosube_agent_civilization.url_boot.types.URL_FETCH_OUTCOMES`; a
        non-``OBSERVED`` outcome carries ``observed_fields=None`` regardless of *fields*.
        """

        if fetch_outcome not in URL_FETCH_OUTCOMES:
            raise UrlBootAdapterError(f"fetch_outcome is not recognized: {fetch_outcome!r}")
        if effective_source_identity is not None:
            resolved_effective_identity: dict[str, Any] | None = dict(effective_source_identity)
        elif fetch_outcome in _NO_RESPONSE_OUTCOMES:
            resolved_effective_identity = None
        else:
            resolved_effective_identity = dict(source_identity)
        self._world[self._key(source_identity)] = {
            "fields": dict(fields),
            "fetch_outcome": fetch_outcome,
            "effective_source_identity": resolved_effective_identity,
            "response_status": response_status,
            "redirect_hop_count": redirect_hop_count,
        }

    def remove_source(self, *, source_identity: Mapping[str, Any]) -> None:
        """Test-only control surface: simulate the source disappearing (V4 proofs)."""

        self._world.pop(self._key(source_identity), None)

    def tamper_fields(
        self, *, source_identity: Mapping[str, Any], fields: Mapping[str, Any]
    ) -> None:
        """Test-only control surface: simulate the source's own live content changing."""

        record = self._world.get(self._key(source_identity))
        if record is not None:
            record["fields"] = dict(fields)

    def force_result(self, result: Mapping[str, Any] | None) -> None:
        """Test-only control surface: force the exact next ``fetch()`` return value, bypassing
        seeded world state entirely -- used to prove this package's own ``UrlBootAdapterError``
        fail-closed handling of a malformed adapter report (an adapter bug, never a legitimate
        transport-level outcome)."""

        self._forced_result = result

    def fetch(
        self, *, source_identity: Mapping[str, Any], boundary: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        self.fetch_call_count += 1
        if self._forced_result is not None:
            return self._forced_result

        record = self._world.get(self._key(source_identity))
        if record is None:
            return {
                "fetch_outcome": "CONNECTION_FAILURE",
                "effective_source_identity": None,
                "response_status": None,
                "redirect_hop_count": 0,
                "observed_fields": None,
            }

        if record["fetch_outcome"] != "OBSERVED":
            return {
                "fetch_outcome": record["fetch_outcome"],
                "effective_source_identity": record["effective_source_identity"],
                "response_status": record["response_status"],
                "redirect_hop_count": record["redirect_hop_count"],
                "observed_fields": None,
            }

        permitted_fields = list(boundary["permitted_fields"])
        observed_fields = {field: record["fields"].get(field) for field in permitted_fields}
        return {
            "fetch_outcome": "OBSERVED",
            "effective_source_identity": record["effective_source_identity"],
            "response_status": record["response_status"],
            "redirect_hop_count": record["redirect_hop_count"],
            "observed_fields": deepcopy(observed_fields),
        }


class LocalHttpUrlSourceAdapter:
    """A complete :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter`
    performing one real, bounded HTTP GET plus a bounded, per-hop-reauthorized redirect-following
    loop -- stdlib ``socket``/``http.client``/``ssl`` only, via
    :func:`~manosube_agent_civilization.url_boot.network.fetch_one_hop`.

    The V3 vertical-proof target: exercised in this delivery's own test suite against one
    disposable, local HTTP server the test itself starts and stops (``127.0.0.1``, an ephemeral
    port) -- never a VPS or cloud target, per Issue #69's own explicit non-target. Expects a JSON
    object response body; ``observed_fields`` is the closed subset of that body named by
    ``boundary["permitted_fields"]``, redacted per ``boundary["redaction_fields"]``.
    """

    def __init__(self, *, adapter_identity: Mapping[str, Any] | None = None) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "local_http_url_source_adapter", "version": "0.1"}
        )

    def fetch(
        self, *, source_identity: Mapping[str, Any], boundary: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        network_scope = boundary["network_scope"]
        max_redirects = boundary["redirect_policy"]["max_redirects"]
        current_identity = dict(source_identity)

        for hop in range(max_redirects + 1):
            try:
                result = fetch_one_hop(
                    current_identity,
                    timeout_seconds=boundary["timeout_seconds"],
                    max_response_bytes=boundary["max_response_bytes"],
                    permit_loopback_test_hosts=network_scope["permit_loopback_test_hosts"],
                )
            except UnsafeResolvedAddressError:
                return self._failure("BOUNDARY_REFUSED", hop)
            except socket.gaierror:
                return self._failure("DNS_FAILURE", hop)
            except TimeoutError:
                return self._failure("TIMEOUT", hop)
            except ssl.SSLError:
                return self._failure("TLS_FAILURE", hop)
            except OSError:
                return self._failure("CONNECTION_FAILURE", hop)

            if result["redirect_location"] is not None and 300 <= result["status"] < 400:
                if hop == max_redirects:
                    return self._failure("REDIRECT_REFUSED", hop, status=result["status"])
                target_url = urljoin(source_url(current_identity), result["redirect_location"])
                try:
                    next_identity = canonical_source_identity(target_url)
                    require_source_within_network_scope(next_identity, network_scope)
                except Exception:
                    return self._failure("REDIRECT_REFUSED", hop, status=result["status"])
                current_identity = next_identity
                continue

            return self._classify_response(result, current_identity, hop, boundary)

        return self._failure("REDIRECT_REFUSED", max_redirects)

    @staticmethod
    def _failure(
        outcome: str, redirect_hop_count: int, *, status: int | None = None
    ) -> Mapping[str, Any]:
        return {
            "fetch_outcome": outcome,
            "effective_source_identity": None,
            "response_status": status,
            "redirect_hop_count": redirect_hop_count,
            "observed_fields": None,
        }

    def _classify_response(
        self,
        result: Mapping[str, Any],
        effective_identity: Mapping[str, Any],
        redirect_hop_count: int,
        boundary: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if result["oversized"]:
            return {
                "fetch_outcome": "OVERSIZED_RESPONSE",
                "effective_source_identity": dict(effective_identity),
                "response_status": result["status"],
                "redirect_hop_count": redirect_hop_count,
                "observed_fields": None,
            }

        content_type = result["headers"].get("content-type", "").split(";")[0].strip().lower()
        admitted_content_types = {value.lower() for value in boundary["admitted_content_types"]}
        if content_type not in admitted_content_types:
            return {
                "fetch_outcome": "UNSUPPORTED_MEDIA_TYPE",
                "effective_source_identity": dict(effective_identity),
                "response_status": result["status"],
                "redirect_hop_count": redirect_hop_count,
                "observed_fields": None,
            }

        try:
            body = json.loads(result["body"].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {
                "fetch_outcome": "MALFORMED",
                "effective_source_identity": dict(effective_identity),
                "response_status": result["status"],
                "redirect_hop_count": redirect_hop_count,
                "observed_fields": None,
            }
        if not isinstance(body, dict) or not (200 <= result["status"] < 300):
            return {
                "fetch_outcome": "MALFORMED",
                "effective_source_identity": dict(effective_identity),
                "response_status": result["status"],
                "redirect_hop_count": redirect_hop_count,
                "observed_fields": None,
            }

        expected_field = boundary.get("expected_field")
        if expected_field is not None and body.get(expected_field) != boundary.get(
            "expected_value"
        ):
            return {
                "fetch_outcome": "IDENTITY_MISMATCH",
                "effective_source_identity": dict(effective_identity),
                "response_status": result["status"],
                "redirect_hop_count": redirect_hop_count,
                "observed_fields": None,
            }

        permitted_fields = list(boundary["permitted_fields"])
        observed_fields = {field: body.get(field) for field in permitted_fields}
        redaction_fields = set(boundary.get("redaction_fields") or ())
        for field in redaction_fields:
            if field in observed_fields:
                observed_fields[field] = "REDACTED"

        return {
            "fetch_outcome": "OBSERVED",
            "effective_source_identity": dict(effective_identity),
            "response_status": result["status"],
            "redirect_hop_count": redirect_hop_count,
            "observed_fields": observed_fields,
        }


__all__ = ["FakeUrlSourceAdapter", "LocalHttpUrlSourceAdapter"]
