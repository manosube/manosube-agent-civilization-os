"""URL parsing, network-scope enforcement, and the one safe single-hop HTTP fetch primitive
(Phase 17, Issue #69, P17-C1/P17-C5).

**Deliberate departure from Runtime's own ``network.py`` precedent, disclosed here rather than
silently.** :mod:`manosube_agent_civilization.runtime.network` is pure and I/O-free by design --
Phase 15 explicitly declined to resolve DNS at all, and refused every redirect outright rather
than validating one. Phase 17's own adopted contract (P17-C5) requires the opposite: "every
redirect target must be normalized and re-authorized against the same Boundary before
following," and explicitly names "DNS rebinding or resolution drift" as an attack this route
must reject. That is not achievable without this module itself performing exactly one DNS
resolution per hop and connecting directly to the address that resolution returned -- never
asking the transport layer to resolve the same hostname a second time at socket-open, which is
precisely the time-of-check/time-of-use window a rebinding attack exploits. This module is
therefore the one place in this package permitted to import ``socket``/``http.client``/``ssl``
(the identical "network I/O confined to one named owner" discipline every prior adapter-boundary
package already keeps, just drawn one module earlier here because the safety property itself --
resolve once, connect to that exact address -- cannot be expressed correctly from outside the
socket-opening call).

Four layers, in the order a fetch actually uses them:

1. **Pure parsing/decomposition** (:func:`canonical_source_identity`, :func:`source_url`) --
   no I/O, refuses userinfo, unreadable hosts, and out-of-vocabulary schemes/ports before
   anything is resolved.
2. **Pure name-based scope check** (:func:`require_source_within_network_scope`) -- is this
   *hostname* (never mind what it resolves to) inside the Boundary's own closed allowlist. Runs
   once per hop, before that hop's own DNS resolution -- a hop naming a host outside the
   allowlist is refused without ever resolving it.
3. **Pure address-safety classification** (:func:`require_safe_resolved_address`) -- is this
   *already-resolved address* loopback/private/link-local/multicast/reserved. **Structural
   Review Round 2 (P17-R2-F1) correction:** this is no longer called from within this module's
   own impure fetch primitive at all -- calling it is now the route's own job alone
   (:mod:`~manosube_agent_civilization.url_boot.route`), on the resolved address the route
   itself sees *before* any connection is ever attempted, never something a replaceable adapter
   decides on the route's behalf.
4. **The two impure primitives** (:func:`resolve_hop_address`, :func:`connect_and_request_hop`)
   -- the first resolves a hop's host exactly once and returns that address to its own caller
   without connecting to it; the second connects directly to a caller-supplied, already-admitted
   address and performs one bounded HTTP GET -- the hostname is used only for the ``Host``
   header and, over HTTPS, TLS server-name/certificate verification, never for a second
   resolution. Splitting resolution from connection this way is what lets the route itself see,
   and independently classify, the resolved address before any connection is ever attempted
   (P17-R2-F1) -- Round 1's own single ``fetch_one_hop`` resolved and connected in one
   uninterruptible step, leaving no seam for the route to inspect the address in between.
"""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from typing import Any
from urllib.parse import urlsplit

from .errors import UrlBootRequirementError

PERMITTED_SOURCE_SCHEMES: frozenset[str] = frozenset({"http", "https"})
_PERMITTED_HOST_CHARACTERS: frozenset[str] = frozenset("abcdefghijklmnopqrstuvwxyz0123456789.-")
_DEFAULT_PORT: dict[str, int] = {"http": 80, "https": 443}


def canonical_source_identity(url: str) -> dict[str, Any]:
    """Decompose *url* into the closed ``source_identity`` shape -- scheme, host, port, path,
    query, fragment -- refusing every form P17-C1 names as a caller-prose ambiguity rather than
    silently normalizing it: userinfo-bearing URLs, unreadable hosts, out-of-vocabulary
    schemes, and non-numeric or out-of-range ports."""

    if not isinstance(url, str) or not url:
        raise UrlBootRequirementError(f"url must be a non-empty string: {url!r}")
    split = urlsplit(url)
    scheme = split.scheme.lower()
    if scheme not in PERMITTED_SOURCE_SCHEMES:
        raise UrlBootRequirementError(
            f"url scheme is not permitted: {split.scheme!r} (must be one of "
            f"{sorted(PERMITTED_SOURCE_SCHEMES)})"
        )
    if not split.netloc:
        raise UrlBootRequirementError(f"url carries no readable host: {url!r}")
    if "@" in split.netloc:
        raise UrlBootRequirementError(
            f"url carries userinfo (credential-bearing URL treatment, P17-C1): {url!r}"
        )
    host = split.hostname
    if not host:
        raise UrlBootRequirementError(f"url carries no readable host: {url!r}")
    host = host.lower()
    if any(character not in _PERMITTED_HOST_CHARACTERS for character in host):
        raise UrlBootRequirementError(f"url host carries a disallowed character: {host!r}")
    try:
        port = split.port
    except ValueError as error:
        raise UrlBootRequirementError(f"url carries an unreadable port: {url!r}") from error
    if port is None:
        port = _DEFAULT_PORT[scheme]
    if not (1 <= port <= 65535):
        raise UrlBootRequirementError(f"url carries an out-of-range port: {url!r}")
    path = split.path or "/"
    return {
        "scheme": scheme,
        "host": host,
        "port": port,
        "path": path,
        "query": split.query or None,
        "fragment": split.fragment or None,
    }


def source_url(source_identity: dict[str, Any]) -> str:
    """Reassemble one canonical ``source_identity`` back into a URL string -- the identical
    assembly :func:`fetch_one_hop` itself opens, so the string a caller sees validated is the
    string that is actually reached."""

    default = _DEFAULT_PORT.get(source_identity["scheme"])
    authority = source_identity["host"]
    if source_identity["port"] != default:
        authority = f"{authority}:{source_identity['port']}"
    url = f"{source_identity['scheme']}://{authority}{source_identity['path']}"
    if source_identity["query"]:
        url = f"{url}?{source_identity['query']}"
    if source_identity["fragment"]:
        url = f"{url}#{source_identity['fragment']}"
    return url


def require_source_within_network_scope(
    source_identity: dict[str, Any], network_scope: dict[str, Any]
) -> None:
    """Require *source_identity* to be a hostname (never mind what it resolves to) inside
    *network_scope*'s own closed allowlist -- refused before any DNS resolution is ever
    attempted."""

    if source_identity["scheme"] not in network_scope["admitted_schemes"]:
        raise UrlBootRequirementError(
            f"source scheme is outside the Boundary's own admitted_schemes: "
            f"{source_identity['scheme']!r} not in {sorted(network_scope['admitted_schemes'])}"
        )
    admitted_hosts = {host.lower() for host in network_scope["admitted_hosts"]}
    if source_identity["host"] not in admitted_hosts:
        raise UrlBootRequirementError(
            f"source host is outside the Boundary's own admitted_hosts: "
            f"{source_identity['host']!r} not in {sorted(admitted_hosts)}"
        )
    if source_identity["port"] not in network_scope["admitted_ports"]:
        raise UrlBootRequirementError(
            f"source port is outside the Boundary's own admitted_ports: "
            f"{source_identity['port']!r} not in {sorted(network_scope['admitted_ports'])}"
        )


class UnsafeResolvedAddressError(UrlBootRequirementError):
    """A hop's own host resolved to an address the closed network scope refuses to reach --
    loopback/private/link-local/multicast/reserved, unless the Boundary's own
    ``permit_loopback_test_hosts`` explicitly admits loopback for a controlled local test
    target."""


def resolve_hop_address(host: str, port: int) -> str:
    """Resolve *host* to exactly one IP address literal, through exactly one DNS lookup -- the
    address :func:`connect_and_request_hop` goes on to connect to directly, once its own caller
    (the route -- P17-R2-F1) has independently classified it as safe. Never called a second time
    for the identical hop, which is what closes the DNS-rebinding time-of-check/time-of-use
    window P17-C5 names. Raises :class:`socket.gaierror` for a genuine DNS failure."""

    try:
        info = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as error:
        raise socket.gaierror(str(error)) from error
    if not info:
        raise socket.gaierror(f"no address returned for host {host!r}")
    return info[0][4][0]


def require_safe_resolved_address(address: str, *, permit_loopback_test_hosts: bool) -> None:
    """Require *address* to be outside loopback/private/link-local/multicast/reserved --
    unless *permit_loopback_test_hosts* explicitly admits loopback for a controlled local test
    target. **Structural Review Round 2 (P17-R2-F1) correction:** this is now called by the
    route alone, on a resolved address the route itself already has in hand *before* any
    connection is attempted -- never by a replaceable adapter, and never as part of any impure
    fetch primitive in this module."""

    parsed = ipaddress.ip_address(address)
    if permit_loopback_test_hosts and parsed.is_loopback:
        return
    if (
        parsed.is_loopback
        or parsed.is_private
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_reserved
        or parsed.is_unspecified
    ):
        raise UnsafeResolvedAddressError(
            f"resolved address is outside the permitted public network scope: {address!r} "
            f"(loopback={parsed.is_loopback}, private={parsed.is_private}, "
            f"link_local={parsed.is_link_local}, multicast={parsed.is_multicast}, "
            f"reserved={parsed.is_reserved})"
        )


def connect_and_request_hop(
    source_identity: dict[str, Any],
    *,
    admitted_address: str,
    timeout_seconds: float,
    max_response_bytes: int,
) -> dict[str, Any]:
    """Connect directly to *admitted_address* -- the one address the route itself already
    resolved, classified as safe, and admitted for this hop (P17-R2-F1) -- and perform one
    bounded HTTP GET against *source_identity*. Never resolves *source_identity*'s own host: the
    caller supplies the exact address to connect to, already admitted.

    Returns ``{"status": int, "headers": dict[str, str], "body": bytes, "redirect_location":
    str | None, "oversized": bool, "resolved_address": str}`` on any completed HTTP response
    (including a redirect response, which this function never follows itself -- following is the
    caller's own per-hop-reauthorized decision); ``resolved_address`` echoes back the exact
    *admitted_address* this call actually connected to, so its own caller can refuse a report
    that ever disagreed. Raises :class:`TimeoutError` for a timed-out connection/read,
    :class:`OSError` for a lower-level connection failure, or :class:`ssl.SSLError` for a TLS
    failure -- the caller classifies each into its own typed
    :data:`~manosube_agent_civilization.url_boot.types.URL_HOP_CONNECT_OUTCOMES` member; this
    function itself never returns a partial/oversized body silently -- reading stops the instant
    *max_response_bytes* would be exceeded and the caller is handed exactly that many bytes plus
    a marker the caller uses to classify ``OVERSIZED_RESPONSE``.
    """

    host = source_identity["host"]
    port = source_identity["port"]

    request_target = source_identity["path"]
    if source_identity["query"]:
        request_target = f"{request_target}?{source_identity['query']}"

    # Deliberately a plain ``HTTPConnection`` even for https, for *both* schemes: its own
    # ``connect()`` performs only the raw TCP connect against *admitted_address* and never
    # itself touches TLS. Using the stdlib ``HTTPSConnection`` here instead would be wrong --
    # its own ``connect()`` wraps the socket itself, using ``self.host`` (which this function
    # has deliberately set to the *admitted address*, never the hostname, per this module's own
    # resolve-once-connect-to-that-exact-address discipline) as the TLS server name, which fails
    # certificate verification (or is rejected outright as an IP-literal SNI name) before this
    # function's own hostname-aware wrap below ever runs -- and would then wrap an
    # already-TLS-wrapped socket a second time. Exactly one TLS wrap happens here, explicitly,
    # against the real hostname.
    connection = http.client.HTTPConnection(admitted_address, port, timeout=timeout_seconds)

    try:
        connection.connect()
        if source_identity["scheme"] == "https":
            context = ssl.create_default_context()
            raw_sock = connection.sock
            connection.sock = context.wrap_socket(raw_sock, server_hostname=host)
        connection.putrequest("GET", request_target, skip_host=True, skip_accept_encoding=True)
        default_port = _DEFAULT_PORT[source_identity["scheme"]]
        host_header = host if port == default_port else f"{host}:{port}"
        connection.putheader("Host", host_header)
        connection.putheader("Accept", "application/json")
        connection.putheader("Connection", "close")
        connection.endheaders()
        response = connection.getresponse()
        status = response.status
        headers = {key.lower(): value for key, value in response.getheaders()}
        redirect_location = headers.get("location") if 300 <= status < 400 else None
        body = response.read(max_response_bytes + 1)
        oversized = len(body) > max_response_bytes
        if oversized:
            body = body[:max_response_bytes]
        return {
            "status": status,
            "headers": headers,
            "body": body,
            "oversized": oversized,
            "redirect_location": redirect_location,
            "resolved_address": admitted_address,
        }
    finally:
        connection.close()


__all__ = [
    "PERMITTED_SOURCE_SCHEMES",
    "UnsafeResolvedAddressError",
    "canonical_source_identity",
    "connect_and_request_hop",
    "require_safe_resolved_address",
    "require_source_within_network_scope",
    "resolve_hop_address",
    "source_url",
]
