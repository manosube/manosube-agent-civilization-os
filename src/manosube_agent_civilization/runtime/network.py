"""Pure, I/O-free Observation-Boundary network-scope enforcement (Phase 15, Issue #64,
Structural Review Round 1, P15-R1-F1; extended for ``SSH_EXEC_BOUNDED``, Issue #105).

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

:func:`require_ssh_endpoint_within_network_scope` is this module's ``SSH_EXEC_BOUNDED``
sibling (Issue #105): the same zero-call, string-only refusal, reusing the identical
``network_scope.allowed_hosts`` shape (already host-based, never transport-specific) but
never the HTTP URL-assembly logic above -- an SSH endpoint is ``{host, port, user,
probe_identity}``, not a URL, so it gets its own canonicalization rather than being forced
through :func:`canonical_endpoint_url`.
"""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any
from urllib.parse import urlsplit

from .errors import RuntimeRequirementError
from .types import SSH_PROBE_IDENTITIES, SSH_PROBE_LAUNCHER_CODE, SSH_PROBE_REMOTE_COMMANDS

#: A SHA-256 hex digest, lowercase, exactly 64 characters -- the one shape a grant's own
#: ``deployment_config_fingerprint`` (and this module's own re-validation of it, PR #108
#: Structural Review Round 5, SR5-F2) must satisfy. The identical pattern
#: ``transport_control.py`` already enforces at grant-validation time; restated here (rather
#: than imported) because this module is pure and I/O-free and takes no dependency on that
#: module's own, heavier validation surface -- the same "re-validate every dynamic element,
#: never trust a caller already checked it" discipline this module already keeps for every
#: other field it builds a command from.
_HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")

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

    permitted = _canonical_allowed_hosts(network_scope)
    url = canonical_endpoint_url(endpoint)
    host = canonical_endpoint_host(url)
    if host not in permitted:
        raise RuntimeRequirementError(
            f"boundary.endpoint resolves to host {host!r}, which is not within the Boundary's "
            f"own declared network scope {sorted(permitted)} -- refusing before any connection"
        )
    return url


def _canonical_allowed_hosts(network_scope: Any) -> set[str]:
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
    return permitted


def canonical_ssh_endpoint_host(endpoint: Any) -> str:
    """Return the lowercased host an ``SSH_EXEC_BOUNDED`` *endpoint* names, refusing every
    ambiguous or unsupported form -- the SSH-endpoint-shaped sibling of
    :func:`canonical_endpoint_host`.

    *endpoint* is the Boundary's own ``{"host", "port", "user", "probe_identity"}`` object
    (already schema-shape-checked by the time this runs; this function re-derives the
    canonical host independently rather than trusting that shape check alone, exactly as
    :func:`canonical_endpoint_host` never trusts ``urlsplit`` alone). The port and user are not
    inspected here -- they carry no host ambiguity of their own, and the schema already bounds
    port to ``1..65535`` and user/host to a closed character length.
    """

    if not isinstance(endpoint, Mapping):
        raise RuntimeRequirementError(
            f"boundary.endpoint must be an explicit mapping: {endpoint!r}"
        )
    host = endpoint.get("host")
    if not isinstance(host, str) or not host:
        raise RuntimeRequirementError(
            f"boundary.endpoint.host must be a non-empty string: {host!r}"
        )
    host = host.lower()
    if "@" in host:
        raise RuntimeRequirementError(
            "boundary.endpoint.host carries an '@', which makes the effective destination "
            f"ambiguous -- refusing before any connection: {host!r}"
        )
    if not set(host) <= _PERMITTED_HOST_CHARACTERS:
        raise RuntimeRequirementError(
            f"boundary.endpoint.host is an ambiguously encoded host: {host!r}"
        )
    if host.startswith("-"):
        # An SSH adapter passes "user@host" as one argv element to the real ``ssh`` binary.
        # ssh's own argument parser treats any argv it has not yet consumed a destination
        # from as an option when it starts with "-" -- a host of e.g. "-oProxyCommand=..."
        # would be parsed as an additional ssh option, not as part of the destination,
        # regardless of this module never invoking a shell. Refused here, independently of
        # the adapter, exactly as every other ambiguous encoding in this function is.
        raise RuntimeRequirementError(
            f"boundary.endpoint.host must not begin with '-' (argument-injection risk against "
            f"an SSH client's own option parser): {host!r}"
        )
    return host


def require_ssh_endpoint_within_network_scope(endpoint: Any, network_scope: Any) -> str:
    """Require an ``SSH_EXEC_BOUNDED`` *endpoint*'s own host to be an exact, case-insensitive
    member of *network_scope*'s own ``allowed_hosts``, and return the canonical host.

    The zero-call, string-only SSH sibling of :func:`require_endpoint_within_network_scope` --
    same refusal discipline (malformed endpoint, malformed scope, or an out-of-scope host, all
    before any transport call), same ``allowed_hosts`` shape, no URL involved at either side.
    """

    permitted = _canonical_allowed_hosts(network_scope)
    host = canonical_ssh_endpoint_host(endpoint)
    if host not in permitted:
        raise RuntimeRequirementError(
            f"boundary.endpoint resolves to host {host!r}, which is not within the Boundary's "
            f"own declared network scope {sorted(permitted)} -- refusing before any connection"
        )
    return host


#: The characters a safe SSH login name may consist of: POSIX portable username grammar
#: (IEEE Std 1003.1), a conservative closed subset an SSH adapter can pass as half of one
#: ``user@host`` argv element with no further quoting.
_PERMITTED_SSH_USER_CHARACTERS: frozenset[str] = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)


def require_safe_ssh_user(endpoint: Any) -> str:
    """Return an ``SSH_EXEC_BOUNDED`` *endpoint*'s own ``user``, refusing an unsafe login name.

    The schema already bounds ``user`` to a non-empty string of at most 64 characters but not
    to any particular character set -- this is the character-set and leading-character check
    :func:`canonical_ssh_endpoint_host` already applies to ``host``, applied to the other half
    of the same ``user@host`` argv element an SSH adapter builds.
    """

    if not isinstance(endpoint, Mapping):
        raise RuntimeRequirementError(
            f"boundary.endpoint must be an explicit mapping: {endpoint!r}"
        )
    user = endpoint.get("user")
    if not isinstance(user, str) or not user:
        raise RuntimeRequirementError(
            f"boundary.endpoint.user must be a non-empty string: {user!r}"
        )
    if not set(user) <= _PERMITTED_SSH_USER_CHARACTERS:
        raise RuntimeRequirementError(
            f"boundary.endpoint.user is an ambiguously encoded login name: {user!r}"
        )
    if user[0] in "-0123456789":
        raise RuntimeRequirementError(
            f"boundary.endpoint.user must not begin with '-' or a digit: {user!r}"
        )
    return user


#: Bounded seconds this package ever waits for an SSH connection itself (not the remote
#: command) to establish -- shared by the real adapter and the rendered manual command, so
#: a Human's copy/paste run behaves identically to the unattended path's own bound.
SSH_CONNECT_TIMEOUT_SECONDS = 10


def render_ssh_command_argv(
    *,
    host: Any,
    port: Any,
    user: Any,
    probe_identity: Any,
    expected_probe_script_sha256: Any,
    expected_deployment_config_fingerprint: Any,
    ssh_executable: str = "ssh",
) -> list[str]:
    """Return the one fixed argv list a bounded SSH observation ever runs, for the given
    endpoint fields -- the single source of truth :class:`~manosube_agent_civilization.
    runtime.adapter.SshRuntimeAdapter` (invoked by this package itself, for Actions or
    grant-gated unattended execution) and the manual-command renderer (Issue #105 Capability
    A, rendered for a Human to copy/paste) both build through, so neither can silently diverge
    from the other. Every dynamic element is independently re-validated here -- a caller
    passing an already-checked endpoint pays only a second, cheap check, never a skipped one.

    **PR #108 Structural Review Round 5, SR5-F2 -- the live Grant's own
    `deployment_config_fingerprint` is now part of the remote command itself.** A prior
    round's own probe-side authorization check (a local sibling ``approved_config.json``)
    compared the probe's own locally-resolved configuration only against *another local
    file*, never against anything the real, currently-verified Grant actually says -- a
    sibling config and its own local "approval" could be swapped together with no connection
    to live authorization at all. *expected_deployment_config_fingerprint* closes that gap:
    both callers of this function pass the exact, freshly-verified grant's own
    ``deployment_config_fingerprint`` (never a cached or locally-stored copy), which becomes
    one of the probe script's own required arguments -- a value that can only ever reach the
    target by riding along on *this exact, already-authorized* command, never by a party with
    mere filesystem access to the target alone. Re-validated here as exactly 64 lowercase hex
    characters (the identical shape a grant's own field is already required to carry) before
    it is ever appended to the remote command string.

    **PR #108 Structural Review Round 6, SR6-F2 -- the live Grant's own `probe_script_sha256`
    is independently verified BEFORE the probe script ever executes, not only compared against
    its own after-the-fact self-report.** SR5-F2 bound the *configuration* to the live grant;
    it left the *artifact* itself unverified before execution -- the remote command still ran
    a fixed pathname unconditionally, and ``probe_script_sha256`` was only ever compared
    against what the probe reported about *itself*, after it had already run. A substitute
    script at the identical pathname could simply echo the expected, public digest and have
    its own different code already executed by the time anything noticed. The remote command
    this function now builds is :data:`~manosube_agent_civilization.runtime.types.
    SSH_PROBE_LAUNCHER_CODE` -- a fixed, reviewed launcher (never built by interpolating any
    of this call's own arguments into its source) that reads the probe script's bytes into
    memory exactly once, independently recomputes their SHA-256, and compares that fresh
    computation against *expected_probe_script_sha256* (the live, Grant-verified value this
    call passes, exactly as every other gated field already is) -- never anything the file
    claims about itself. Only on an exact match does it ``exec()`` those *same in-memory
    bytes*; it never reopens or rereads the file for execution, so there is no window between
    verification and use for the file to be swapped. On any mismatch, it refuses with a closed
    ``ARTIFACT_NOT_AUTHORIZED`` report and ``exec()`` is never reached at all -- a substitute's
    own code genuinely never runs, not merely "runs and is reported as untrusted afterward."
    *expected_probe_script_sha256* is re-validated here as exactly 64 lowercase hex characters,
    identically to *expected_deployment_config_fingerprint*, before being appended (unquoted,
    since both are already restricted to a safe character set, and *probe_identity* is
    restricted to its own closed two-member vocabulary) as the launcher's own trailing
    arguments.

    Returned as a ``list[str]`` (an argv, never a shell string) because that is what
    :func:`subprocess.run` with ``shell=False`` takes directly; a Human-facing renderer joins
    it with :func:`shlex.join` for display, which is a presentation choice that function makes,
    not this one.
    """

    endpoint = {"host": host, "user": user}
    canonical_host = canonical_ssh_endpoint_host(endpoint)
    safe_user = require_safe_ssh_user(endpoint)
    if not isinstance(port, int) or isinstance(port, bool) or not (1 <= port <= _MAX_PORT):
        raise RuntimeRequirementError(f"boundary.endpoint.port must be an integer 1..65535: {port!r}")
    if probe_identity not in SSH_PROBE_IDENTITIES or probe_identity not in SSH_PROBE_REMOTE_COMMANDS:
        raise RuntimeRequirementError(
            f"boundary.endpoint.probe_identity is not a pinned probe: {probe_identity!r}"
        )
    if not isinstance(
        expected_probe_script_sha256, str
    ) or not _HEX64_PATTERN.fullmatch(expected_probe_script_sha256):
        raise RuntimeRequirementError(
            "expected_probe_script_sha256 must be a lowercase 64-character hex SHA-256 "
            f"digest: {expected_probe_script_sha256!r}"
        )
    if not isinstance(
        expected_deployment_config_fingerprint, str
    ) or not _HEX64_PATTERN.fullmatch(expected_deployment_config_fingerprint):
        raise RuntimeRequirementError(
            "expected_deployment_config_fingerprint must be a lowercase 64-character hex "
            f"SHA-256 digest: {expected_deployment_config_fingerprint!r}"
        )
    remote_command = (
        f'python3 -c "{SSH_PROBE_LAUNCHER_CODE}" '
        f"{expected_probe_script_sha256} {probe_identity} "
        f"{expected_deployment_config_fingerprint}"
    )
    return [
        ssh_executable,
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"ConnectTimeout={SSH_CONNECT_TIMEOUT_SECONDS}",
        "-p",
        str(port),
        f"{safe_user}@{canonical_host}",
        remote_command,
    ]


__all__ = [
    "PERMITTED_ENDPOINT_SCHEMES",
    "SSH_CONNECT_TIMEOUT_SECONDS",
    "canonical_endpoint_host",
    "canonical_endpoint_url",
    "canonical_ssh_endpoint_host",
    "render_ssh_command_argv",
    "require_endpoint_within_network_scope",
    "require_safe_ssh_user",
    "require_ssh_endpoint_within_network_scope",
]
