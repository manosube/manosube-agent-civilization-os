"""The three :class:`~manosube_agent_civilization.runtime.types.RuntimeAdapter`
implementations this package ships (Phase 15, Issue #64; ``SshRuntimeAdapter`` added by
Issue #105).

``FakeRuntimeAdapter`` is a controlled, in-memory, fully deterministic adapter -- the V1/V2/V4
proof target every unit/contract test in this package's own suites exercises. It reports
transport-level facts only (see :data:`~manosube_agent_civilization.runtime.types.
RUNTIME_ADAPTER_TRANSPORT_OUTCOMES`); it never itself decides ``NEGATIVE``/``IDENTITY_MISMATCH``
-- that classification belongs solely to :mod:`~manosube_agent_civilization.runtime.route`.

``LocalHttpRuntimeAdapter`` is a genuine, complete implementation performing one real, bounded
HTTP GET (stdlib ``urllib`` only, no new runtime dependency) -- the V3 vertical-proof target,
exercised against one disposable, local target this delivery's own test suite starts and stops
itself (no VPS, no cloud provider, per Issue #64's own explicit non-target).

``SshRuntimeAdapter`` (Issue #105) is a genuine, complete implementation performing one real,
bounded SSH command execution (stdlib ``subprocess`` invoking the system ``ssh`` binary only,
no new runtime dependency, the identical "stdlib transport only" discipline
``LocalHttpRuntimeAdapter`` already keeps for HTTP). The remote command is never caller-supplied
text: ``boundary["endpoint"]["probe_identity"]`` selects one of exactly
:data:`~manosube_agent_civilization.runtime.types.SSH_PROBE_IDENTITIES`, each mapped by the
closed, pinned :data:`~manosube_agent_civilization.runtime.types.SSH_PROBE_REMOTE_COMMANDS`
table (read through :func:`~manosube_agent_civilization.runtime.network.
render_ssh_command_argv`, the one argv builder this adapter and the manual-command renderer
both call) to one fixed remote command string -- there is no path, argument, or shell
fragment a caller can inject into that string. Both Actions and manual/unattended transports
(Issue #105's whole point) invoke this identical adapter through the identical
:func:`~manosube_agent_civilization.runtime.route.observe_runtime_target`; nothing about *how*
this adapter got invoked changes what it does.

This is the one module in the ``runtime`` package permitted to import a network/transport
surface that actually *opens* anything -- checked by name, exactly as
``projection/github_adapter.py`` already is (``PROJECTION_CONTRACT.md`` §3 precedent; see
``tests/contract/runtime/test_runtime_static_conformance.py``, which additionally admits the
pure, I/O-free ``urllib.parse`` import in :mod:`~manosube_agent_civilization.runtime.network`
and nothing else anywhere in this package).

**Structural Review Round 1 (P15-R1-F1).** ``LocalHttpRuntimeAdapter`` previously constructed
and opened ``boundary["endpoint"]`` without ever consulting
``boundary["network_scope"]["allowed_hosts"]``, and relied on ``urllib``'s own automatic
redirect following, so a Boundary could name one allowed host and the request could still end
up at another -- directly, or via a 3xx. Both halves are closed here: the endpoint is
re-checked against the allowlist immediately before a socket is opened (defense in depth --
:mod:`~manosube_agent_civilization.runtime.route` already refuses a wrong-host Boundary before
any adapter is called at all, and neither site relies on the other being the only one), and
redirect following is disabled outright. Not following any redirect, rather than validating
each hop's own host, is a deliberate choice: this is a bounded observation probe against one
explicit declared endpoint, not a general HTTP client, so a target that answers 3xx has not
answered the bounded question that was asked -- that is a transport failure (``UNAVAILABLE``),
never something to silently chase.

**Issue #105's identical discipline for SSH.** ``SshRuntimeAdapter`` re-checks the endpoint
against its own network scope immediately before the ``ssh`` process is spawned (defense in
depth, same reasoning). ``subprocess.run`` is called with ``shell=False`` and a fixed-length
argv list built only from schema- and character-set-validated fields
(:func:`~manosube_agent_civilization.runtime.network.canonical_ssh_endpoint_host`,
:func:`~manosube_agent_civilization.runtime.network.require_safe_ssh_user` -- both additionally
refuse a value beginning with ``-``, which would otherwise let a crafted ``host``/``user``
be parsed by ``ssh`` itself as a further option rather than as the destination) plus the one
pinned remote command string the closed ``probe_identity`` selected. ``BatchMode=yes`` and
``StrictHostKeyChecking=yes`` are always passed so a probe can never fall back to an
interactive password or host-key prompt that would hang until this process's own bounded
timeout, nor silently trust an unverified host key.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import subprocess
from typing import Any
import urllib.error
import urllib.request

from .errors import RuntimeAdapterError
from .network import (
    render_ssh_command_argv,
    require_endpoint_within_network_scope,
    require_ssh_endpoint_within_network_scope,
)


class FakeRuntimeAdapter:
    """A controlled, in-memory, fully deterministic
    :class:`~manosube_agent_civilization.runtime.types.RuntimeAdapter`.

    Backs every V1/V2/V4 test in this package's own suites. Seeded targets live only in this
    instance's own dict for the lifetime of the test that constructs it -- no filesystem
    write, no network call, no shared or global state between instances.
    """

    def __init__(self, *, adapter_identity: Mapping[str, Any] | None = None) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "fake_runtime_adapter", "version": "0.1"}
        )
        self._world: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._forced_result: Mapping[str, Any] | None = None
        self.observe_call_count = 0

    @staticmethod
    def _key(target_identity: Mapping[str, Any]) -> tuple[str, str, str]:
        return (
            target_identity["provider"],
            target_identity["deployment_id"],
            target_identity["instance_identity"],
        )

    def seed_target(
        self,
        *,
        target_identity: Mapping[str, Any],
        fields: Mapping[str, Any],
        observed_deployment_identity: str | None = None,
        transport_outcome: str = "OBSERVED",
    ) -> None:
        """Declare what a real probe of *target_identity* would honestly report.

        *observed_deployment_identity*, left ``None``, defaults to the target's own declared
        ``deployment_fingerprint`` -- a genuinely matching target. Passing an explicit,
        different value is exactly how a V4 identity-mismatch/spoofing control is built:
        the adapter honestly reports what it saw, and only
        :mod:`~manosube_agent_civilization.runtime.route`'s own independent recomputation
        may ever call that a mismatch.
        """

        self._world[self._key(target_identity)] = {
            "fields": dict(fields),
            "observed_deployment_identity": (
                observed_deployment_identity
                if observed_deployment_identity is not None
                else target_identity["deployment_fingerprint"]
            ),
            "transport_outcome": transport_outcome,
        }

    def remove_target(self, *, target_identity: Mapping[str, Any]) -> None:
        """Test-only control surface: simulate the target disappearing (V4 proofs)."""

        self._world.pop(self._key(target_identity), None)

    def tamper_fields(
        self, *, target_identity: Mapping[str, Any], fields: Mapping[str, Any]
    ) -> None:
        """Test-only control surface: simulate the target's own live content changing."""

        record = self._world.get(self._key(target_identity))
        if record is not None:
            record["fields"] = dict(fields)

    def force_result(self, result: Mapping[str, Any] | None) -> None:
        """Test-only control surface: force the exact next ``observe()`` return value,
        bypassing seeded world state entirely -- used to prove this package's own
        ``RuntimeAdapterError`` fail-closed handling of a malformed adapter report (an
        adapter bug, never a legitimate transport-level ``MALFORMED`` outcome)."""

        self._forced_result = result

    def observe(
        self, *, target_identity: Mapping[str, Any], boundary: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        self.observe_call_count += 1
        if self._forced_result is not None:
            return self._forced_result

        record = self._world.get(self._key(target_identity))
        if record is None:
            return {
                "transport_outcome": "NOT_FOUND",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }

        outcome = record["transport_outcome"]
        if outcome != "OBSERVED":
            return {
                "transport_outcome": outcome,
                "observed_fields": None,
                "observed_deployment_identity": None,
            }

        permitted_fields = list(boundary["permitted_fields"])
        observed_fields = {field: record["fields"].get(field) for field in permitted_fields}
        return {
            "transport_outcome": "OBSERVED",
            "observed_fields": deepcopy(observed_fields),
            "observed_deployment_identity": record["observed_deployment_identity"],
        }


class _RefuseEveryRedirectHandler(urllib.request.HTTPRedirectHandler):
    """A redirect handler that follows nothing (P15-R1-F1).

    Returning ``None`` from ``redirect_request`` makes ``urllib``'s own handler chain fall
    through to its default error handler, which raises the 3xx as an
    :class:`urllib.error.HTTPError` -- so a redirect becomes an ordinary, honestly reported
    transport failure (``UNAVAILABLE``) at the one place transport failures are already
    classified, and no second request is ever issued to anywhere.
    """

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        return None


class LocalHttpRuntimeAdapter:
    """A complete :class:`~manosube_agent_civilization.runtime.types.RuntimeAdapter` performing
    one real, bounded HTTP GET against ``boundary["endpoint"]`` -- stdlib ``urllib`` only.

    The V3 vertical-proof target: exercised in this delivery's own test suite against one
    disposable, local HTTP server the test itself starts and stops (``127.0.0.1``, an
    ephemeral port) -- never a VPS or cloud target, per Issue #64's own explicit non-target.
    Expects a JSON object response body; ``observed_fields`` is the closed subset of that
    body named by ``boundary["permitted_fields"]``, and ``observed_deployment_identity`` is
    read from the response body's own ``deployment_fingerprint`` key when present (a target
    that reports no such key yields ``None`` -- an honest "this target declared no identity
    of its own", never fabricated).
    """

    def __init__(self, *, adapter_identity: Mapping[str, Any] | None = None) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "local_http_runtime_adapter", "version": "0.1"}
        )
        #: One opener that follows no redirect at all (P15-R1-F1), built once per adapter --
        #: never ``urllib.request.urlopen``'s process-global opener, whose handler set this
        #: adapter neither owns nor can vouch for.
        self._opener = urllib.request.build_opener(_RefuseEveryRedirectHandler)

    def observe(
        self, *, target_identity: Mapping[str, Any], boundary: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        # Independent re-enforcement of the Boundary's own closed network scope, immediately
        # before a socket exists (P15-R1-F1). ``observe_runtime_target`` already refused a
        # wrong-host Boundary before ever reaching an adapter; this adapter still never
        # assumes it was called through that route, and refuses rather than connect.
        url = require_endpoint_within_network_scope(boundary["endpoint"], boundary["network_scope"])
        request = urllib.request.Request(url, method="GET")  # noqa: S310
        try:
            with self._opener.open(request, timeout=boundary["timeout_seconds"]) as response:
                status = response.status
                raw_body = response.read()
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return {
                    "transport_outcome": "NOT_FOUND",
                    "observed_fields": None,
                    "observed_deployment_identity": None,
                }
            if error.code in (401, 403, 429):
                return {
                    "transport_outcome": "PERMISSION_DENIED",
                    "observed_fields": None,
                    "observed_deployment_identity": None,
                }
            return {
                "transport_outcome": "UNAVAILABLE",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }
        except TimeoutError:
            return {
                "transport_outcome": "TIMEOUT",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }
        except urllib.error.URLError:
            return {
                "transport_outcome": "UNAVAILABLE",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }

        if status != 200:
            return {
                "transport_outcome": "UNAVAILABLE",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {
                "transport_outcome": "MALFORMED",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }
        if not isinstance(body, dict):
            return {
                "transport_outcome": "MALFORMED",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }

        permitted_fields = list(boundary["permitted_fields"])
        observed_fields = {field: body.get(field) for field in permitted_fields}
        observed_deployment_identity = body.get("deployment_fingerprint")
        if observed_deployment_identity is not None and not isinstance(
            observed_deployment_identity, str
        ):
            raise RuntimeAdapterError(
                "target's own deployment_fingerprint field is not a string: "
                f"{observed_deployment_identity!r}"
            )
        return {
            "transport_outcome": "OBSERVED",
            "observed_fields": observed_fields,
            "observed_deployment_identity": observed_deployment_identity,
        }


class SshRuntimeAdapter:
    """A complete :class:`~manosube_agent_civilization.runtime.types.RuntimeAdapter` performing
    one real, bounded SSH command execution against ``boundary["endpoint"]`` -- stdlib
    ``subprocess`` invoking the system ``ssh`` binary only, no new runtime dependency.

    The V-proof target for Issue #105's ``SSH_EXEC_BOUNDED`` method: exercised in this
    delivery's own test suite against one disposable, local target the test itself controls
    when a real local SSH fixture is available without any machine/service/credential
    modification; otherwise that specific proof is reported pending rather than claimed from a
    fixture (the same ``FakeRuntimeAdapter``-backed fixture proofs every other counterexample
    in this module's own test matrix, exactly as they already do for HTTP).

    Expects the remote probe to print exactly one JSON object as the last non-empty line of
    its stdout, carrying ``{"ok": bool, "fields": {...} | None, "deployment_identity": str |
    None, "reason": str | None}`` -- the identical closed shape
    ``scripts/runtime_observation_probe.py`` (this delivery's own pinned probe script, run
    locally for Capability A/B and remotely for this adapter) always emits. ``observed_fields``
    is the closed subset of ``fields`` named by ``boundary["permitted_fields"]``.
    """

    def __init__(
        self, *, adapter_identity: Mapping[str, Any] | None = None, ssh_executable: str = "ssh"
    ) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "ssh_runtime_adapter", "version": "0.1"}
        )
        #: Overridable only for this delivery's own real-transport test (a disposable local
        #: SSH fixture reached through a non-default port/executable) -- never a caller-
        #: supplied value reachable through any Boundary field.
        self._ssh_executable = ssh_executable

    def observe(
        self, *, target_identity: Mapping[str, Any], boundary: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        # Independent re-enforcement of the Boundary's own closed network scope, immediately
        # before a process is spawned (P15-R1-F1's identical discipline, applied to SSH).
        require_ssh_endpoint_within_network_scope(boundary["endpoint"], boundary["network_scope"])
        endpoint = boundary["endpoint"]
        # The one shared argv builder this adapter and the manual-command renderer both call
        # (Issue #105) -- re-validates every field itself, so this adapter never trusts the
        # route's own prior validation as the only check.
        argv = render_ssh_command_argv(
            host=endpoint["host"],
            port=endpoint["port"],
            user=endpoint["user"],
            probe_identity=endpoint["probe_identity"],
            ssh_executable=self._ssh_executable,
        )
        try:
            result = subprocess.run(  # noqa: S603 -- fixed executable, closed/validated argv, never shell=True
                argv,
                capture_output=True,
                timeout=boundary["timeout_seconds"],
                text=True,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "transport_outcome": "TIMEOUT",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }
        except OSError:
            return {
                "transport_outcome": "UNAVAILABLE",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }

        probe_report = self._parse_probe_report(result.stdout)
        if probe_report is None:
            # No well-formed probe report reached us at all -- either ssh itself never
            # reached/authenticated to the target (its own documented exit code 255), or the
            # remote command ran but produced something this adapter cannot read as the one
            # closed report shape it ever trusts. Both are honest transport failures, never
            # silently treated as "no observation needed."
            if result.returncode == 255:
                if "permission denied" in result.stderr.lower():
                    return {
                        "transport_outcome": "PERMISSION_DENIED",
                        "observed_fields": None,
                        "observed_deployment_identity": None,
                    }
                return {
                    "transport_outcome": "UNAVAILABLE",
                    "observed_fields": None,
                    "observed_deployment_identity": None,
                }
            return {
                "transport_outcome": "MALFORMED",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }

        if not probe_report.get("ok"):
            reason = probe_report.get("reason")
            if reason == "NOT_FOUND":
                return {
                    "transport_outcome": "NOT_FOUND",
                    "observed_fields": None,
                    "observed_deployment_identity": None,
                }
            if reason == "PERMISSION_DENIED":
                return {
                    "transport_outcome": "PERMISSION_DENIED",
                    "observed_fields": None,
                    "observed_deployment_identity": None,
                }
            return {
                "transport_outcome": "MALFORMED",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }

        fields = probe_report.get("fields")
        if not isinstance(fields, dict):
            return {
                "transport_outcome": "MALFORMED",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }
        permitted_fields = list(boundary["permitted_fields"])
        observed_fields = {field: fields.get(field) for field in permitted_fields}
        observed_deployment_identity = probe_report.get("deployment_identity")
        if observed_deployment_identity is not None and not isinstance(
            observed_deployment_identity, str
        ):
            raise RuntimeAdapterError(
                "probe report's own deployment_identity field is not a string: "
                f"{observed_deployment_identity!r}"
            )
        return {
            "transport_outcome": "OBSERVED",
            "observed_fields": observed_fields,
            "observed_deployment_identity": observed_deployment_identity,
        }

    @staticmethod
    def _parse_probe_report(stdout: str) -> dict[str, Any] | None:
        """Return the probe's one closed-shape JSON report, taken as the last non-empty line
        of *stdout* (a login banner or other preamble this adapter did not ask for, if any,
        precedes it rather than replacing it) -- or ``None`` if no line parses as one."""

        for line in reversed(stdout.splitlines()):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return None
            return parsed if isinstance(parsed, dict) and "ok" in parsed else None
        return None
