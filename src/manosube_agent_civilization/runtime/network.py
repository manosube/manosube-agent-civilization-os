"""Pure, I/O-free Observation-Boundary network-scope enforcement (Phase 15, Issue #64,
Structural Review Round 1, P15-R1-F1).

Round 1 found that ``LocalHttpRuntimeAdapter.observe`` constructed and opened
``boundary["endpoint"]`` without ever consulting ``boundary["network_scope"]["allowed_hosts"]``
-- a Boundary could name one allowed host and the GET would still be sent to another, which
makes ``OBSERVATION_BOUNDARY_CLOSED=true`` a claim the code did not actually keep. This module
is the one place that answers "does this Boundary's own declared endpoint fall inside its own
declared network scope?", and it answers it *before* any connection exists:
:func:`~manosube_agent_civilization.runtime.route.observe_runtime_target` calls it during
Boundary validation, so a wrong-host Boundary refuses with the adapter never invoked at all
(zero-call), whichever adapter implementation a caller supplied; and
:class:`~manosube_agent_civilization.runtime.adapter.LocalHttpRuntimeAdapter` calls it again
itself, immediately before opening a socket, so the enforcement never depends on the route
being the only caller in the world (defense in depth).

**This module performs no I/O of any kind.** It imports ``urllib.parse`` -- a pure
string-parsing surface, never ``urllib.request`` -- and that is the *only* reason this package's
own static conformance test admits a second module naming ``urllib`` at all (see
``tests/contract/runtime/test_runtime_static_conformance.py``, which pins this module's own
admitted import to exactly ``urllib.parse`` and proves it opens nothing). It resolves no name,
opens no socket, reads no file, and reaches no network: every check here is a decision about a
string a caller already declared.

What is deliberately *not* attempted here (``OVER_ENGINEERING_REFUSED=true``): no DNS
resolution and therefore no claim that an allowed hostname resolves to an allowed address, no
IDN/punycode normalization, and no per-port scoping. ``allowed_hosts`` is matched as an exact,
case-insensitive host string, exactly as the Boundary schema declares it -- a closed
allowlist of names, not a resolved-address allowlist. The redirect half of P15-R1-F1 is
enforced in ``adapter.py`` (no redirect is ever followed at all), not here, because refusing to
follow a redirect is a transport decision, not a parsing one.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from .errors import RuntimeRequirementError

#: The only two URL schemes a bounded Runtime Observation may ever name. Anything else --
#: ``file``, ``ftp``, ``gopher``, a bare scheme-less string -- is refused before any
#: canonicalization, never "handled" by falling back to a default.
PERMITTED_ENDPOINT_SCHEMES: frozenset[str] = frozenset({"http", "https"})

#: The characters an accepted host may consist of, after lowercasing: ASCII letters/digits,
#: ``.``/``-``/``_`` for ordinary DNS names, and ``[``/``]``/``:`` for a bracketed IPv6
#: literal. A host carrying anything else -- percent-encoding (``%2e``), whitespace, a
#: non-ASCII codepoint -- is an ambiguous encoding this module refuses rather than normalizes.
_PERMITTED_HOST_CHARACTERS: frozenset[str] = frozenset("abcdefghijklmnopqrstuvwxyz0123456789.-_[]:")

_MIN_PORT = 1
_MAX_PORT = 65535


def canonical_endpoint_url(endpoint: Any) -> str:
    """Return the one canonical absolute URL *endpoint* names, refusing any malformed shape.

    *endpoint* is the Boundary's own ``{"base_url", "path"}`` object. The URL is assembled
    exactly the way this package's own HTTP adapter assembles it (one ``/`` between the two,
    never two, never zero) so the string this module validates is the identical string a
    transport would open -- a canonicalization that disagreed with the transport's own
    assembly would validate one URL and open another.
    """

    if not isinstance(endpoint, Mapping):
        raise RuntimeRequirementError(
            f"boundary.endpoint must be an explicit mapping: {endpoint!r}"
        )
    base_url = endpoint.get("base_url")
    path = endpoint.get("path")
    if not isinstance(base_url, str) or not base_url:
        raise RuntimeRequirementError(
            f"boundary.endpoint.base_url must be a non-empty string: {base_url!r}"
        )
    if not isinstance(path, str) or not path:
        raise RuntimeRequirementError(
            f"boundary.endpoint.path must be a non-empty string: {path!r}"
        )
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def canonical_endpoint_host(url: str) -> str:
    """Return the lowercased host *url* names, refusing every ambiguous or unsupported form.

    Refused, each before any connection could exist: an unsupported scheme (only
    :data:`PERMITTED_ENDPOINT_SCHEMES`), userinfo (``user@host`` -- the classic
    "``https://allowed.example@attacker.example/``" confusion), an absent or empty host, an
    ambiguously encoded host (:data:`_PERMITTED_HOST_CHARACTERS`), and a port that is present
    but non-numeric or outside ``1..65535``.
    """

    if not isinstance(url, str) or not url:
        raise RuntimeRequirementError(f"endpoint URL must be a non-empty string: {url!r}")
    try:
        split = urlsplit(url)
    except ValueError as error:  # pragma: no cover -- urlsplit is total for str input today
        raise RuntimeRequirementError(f"endpoint URL is not parseable: {url!r}") from error

    scheme = split.scheme.lower()
    if scheme not in PERMITTED_ENDPOINT_SCHEMES:
        raise RuntimeRequirementError(
            f"endpoint URL names an unsupported scheme {scheme!r} -- only "
            f"{sorted(PERMITTED_ENDPOINT_SCHEMES)} may ever be observed: {url!r}"
        )
    netloc = split.netloc
    if not netloc:
        raise RuntimeRequirementError(f"endpoint URL carries no network location: {url!r}")
    if "@" in netloc:
        raise RuntimeRequirementError(
            "endpoint URL carries userinfo (user@host), which makes the effective destination "
            f"ambiguous -- refusing before any connection: {url!r}"
        )

    # ``urlsplit`` raises for a non-numeric or out-of-range port only when ``.port`` is read;
    # the raw text is read first so a malformed port is refused in this module's own words.
    host_part, _, port_part = netloc.rpartition(":")
    if host_part and "]" not in port_part:
        if not port_part.isdigit():
            raise RuntimeRequirementError(
                f"endpoint URL carries a non-numeric port {port_part!r}: {url!r}"
            )
        port = int(port_part)
        if not (_MIN_PORT <= port <= _MAX_PORT):
            raise RuntimeRequirementError(
                f"endpoint URL carries a port outside 1..65535: {port!r} in {url!r}"
            )

    host = split.hostname
    if not host:
        raise RuntimeRequirementError(f"endpoint URL carries no readable host: {url!r}")
    host = host.lower()
    if not set(host) <= _PERMITTED_HOST_CHARACTERS:
        raise RuntimeRequirementError(
            f"endpoint URL carries an ambiguously encoded host {host!r}: {url!r}"
        )
    return host


def require_endpoint_within_network_scope(endpoint: Any, network_scope: Any) -> str:
    """Require *endpoint*'s own effective destination host to be an exact, case-insensitive
    member of *network_scope*'s own ``allowed_hosts``, and return the canonical URL.

    Raises :class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError` on a
    malformed endpoint, a malformed network scope, or a host outside the allowlist -- always
    before any transport call, never as a post-hoc audit of a connection already made.
    """

    if not isinstance(network_scope, Mapping):
        raise RuntimeRequirementError(
            f"boundary.network_scope must be an explicit mapping: {network_scope!r}"
        )
    allowed_hosts = network_scope.get("allowed_hosts")
    if not isinstance(allowed_hosts, list | tuple) or not allowed_hosts:
        raise RuntimeRequirementError(
            "boundary.network_scope.allowed_hosts must be a non-empty list of host strings: "
            f"{allowed_hosts!r}"
        )
    permitted: set[str] = set()
    for candidate in allowed_hosts:
        if not isinstance(candidate, str) or not candidate:
            raise RuntimeRequirementError(
                f"boundary.network_scope.allowed_hosts carries a non-string host: {candidate!r}"
            )
        permitted.add(candidate.lower())

    url = canonical_endpoint_url(endpoint)
    host = canonical_endpoint_host(url)
    if host not in permitted:
        raise RuntimeRequirementError(
            f"boundary.endpoint resolves to host {host!r}, which is not within the Boundary's "
            f"own declared network scope {sorted(permitted)} -- refusing before any connection"
        )
    return url


__all__ = [
    "PERMITTED_ENDPOINT_SCHEMES",
    "canonical_endpoint_host",
    "canonical_endpoint_url",
    "require_endpoint_within_network_scope",
]
