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

**PR #108 Structural Review Round 5, SR5-F1, corrected by Round 6, SR6-F1 -- a thread cannot
genuinely bound an arbitrary call.** Round 5 added ``bounded_dispatch_status_acquisition``
here specifically because this module is the one package-wide exception (alongside
:func:`_run_bounded_subprocess` above) permitted to import ``threading``: it ran a raw
``dispatch_status_provider`` call in a background daemon thread and joined with a timeout, so
the *caller* never waited past its own budget. The Structural Advisor reproduced the real
defect that approach could never close: ``join(timeout=...)`` only stops the *caller* from
waiting -- it neither stops nor contains the spawned thread, which keeps running, and keeps
accumulating, for as long as the real process lives (twenty 1ms-capped calls against a
stalled provider returned ``"UNKNOWN"`` in roughly 25ms each, while all twenty provider
threads remained alive and only finished well after every one of those timeouts). Python has
no safe way to preempt a running thread, so no amount of tuning this wrapper could ever
actually bound the thing it claimed to bound -- only the caller's own patience. This function
is removed; the one caller that used it
(:func:`scripts.runtime_observation_transport._dispatch_status_file_provider`) now performs a
direct, synchronous, strictly bounded read instead (refusing outright, via a file-type check,
anything that is not a genuine regular file -- never spawning a thread to "wait out" a read
that was never going to be preemptible to begin with). See that function's own docstring for
the corrected design.

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

from collections.abc import Callable, Mapping
from copy import deepcopy
import json
import subprocess
import threading
import time
from typing import Any, ClassVar
import urllib.error
import urllib.request

from .engine import current_utc_instant
from .errors import RuntimeAdapterError, RuntimeRequirementError
from .network import (
    render_ssh_command_argv,
    require_endpoint_within_network_scope,
    require_ssh_endpoint_within_network_scope,
)
from .transport_control import (
    require_boundary_within_live_window,
    require_grant_matches_attempt,
    require_grant_not_expired,
    require_grant_permits_transport,
)


class _OutputTooLargeError(Exception):
    """Raised by :func:`_run_bounded_subprocess` when a subprocess's own stdout or stderr
    exceeds the grant's own declared ``max_output_bytes`` -- PR #108 Structural Review
    Round 1, F4. The process is killed the moment this is detected, never merely truncated
    and accepted."""


def _drain_bounded(stream: Any, *, max_bytes: int, chunks: list[bytes], overflow: threading.Event) -> None:
    """Read *stream* in a background thread, accumulating into *chunks*, and set *overflow*
    (without raising inside this thread) the instant the running total exceeds *max_bytes* --
    the calling thread is the one that kills the process and raises, so the subprocess is
    never left running past that instant waiting on this thread to notice."""

    total = 0
    while True:
        chunk = stream.read(65536)
        if not chunk:
            return
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            overflow.set()
            return


def _run_bounded_subprocess(
    argv: list[str], *, timeout_seconds: float, max_output_bytes: int
) -> tuple[bytes, bytes, int]:
    """Run *argv*, streaming stdout/stderr through a hard byte ceiling and a hard wall-clock
    ceiling (PR #108 SR1 F4) -- never ``subprocess.run(capture_output=True)``'s own unbounded
    buffering, which accepts however much a target chooses to print before this process ever
    gets to inspect it. Raises :class:`subprocess.TimeoutExpired` or
    :class:`_OutputTooLargeError` (killing the process first in either case) exactly as a
    caller already expects the first of those two to be raised."""

    proc = subprocess.Popen(  # noqa: S603 -- fixed executable, closed/validated argv, never shell=True
        argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False
    )
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    overflow = threading.Event()
    if proc.stdout is None or proc.stderr is None:
        # Unreachable given stdout=PIPE/stderr=PIPE above; stated explicitly so the type
        # checker (and any future refactor) never has to trust an unchecked assumption.
        proc.kill()
        proc.wait()
        raise OSError("subprocess was started without readable stdout/stderr pipes")
    stdout_thread = threading.Thread(
        target=_drain_bounded,
        args=(proc.stdout,),
        kwargs={"max_bytes": max_output_bytes, "chunks": stdout_chunks, "overflow": overflow},
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_drain_bounded,
        args=(proc.stderr,),
        kwargs={"max_bytes": max_output_bytes, "chunks": stderr_chunks, "overflow": overflow},
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    deadline = time.monotonic() + timeout_seconds
    try:
        while True:
            if overflow.is_set():
                raise _OutputTooLargeError(
                    f"subprocess stdout/stderr exceeded {max_output_bytes} bytes"
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, timeout_seconds)
            try:
                proc.wait(timeout=min(0.05, remaining))
                break
            except subprocess.TimeoutExpired:
                continue
    except (_OutputTooLargeError, subprocess.TimeoutExpired):
        proc.kill()
        proc.wait()
        raise
    finally:
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        # The drain threads only ever read from these pipes; closing them here (rather than
        # waiting for Popen's own __del__ to do it, non-deterministically) is what this
        # repository's own fail-closed-on-every-warning pytest configuration requires.
        proc.stdout.close()
        proc.stderr.close()

    # PR #108 Structural Review Round 2, SR2-F3(A): the polling loop above only ever checks
    # ``overflow.is_set()`` *before* calling ``proc.wait()`` on each iteration. A short-lived
    # child that writes more than ``max_output_bytes`` before either drain thread has had a
    # scheduling slot to notice can make ``proc.wait()`` return normally (the process already
    # exited) with the overflow never caught mid-flight -- the loop then ``break``s and this
    # function would otherwise return the full, oversized output with no error at all. The
    # join calls above only return once each drain thread's own read-to-EOF loop has actually
    # finished (and ``_drain_bounded`` sets ``overflow`` *before* returning whenever it saw
    # more than the bound), so this is the one required final, authoritative check: whichever
    # path got here, an overflow detected at any point -- mid-flight or only discovered during
    # this join -- is never silently accepted.
    if overflow.is_set():
        raise _OutputTooLargeError(f"subprocess stdout/stderr exceeded {max_output_bytes} bytes")
    return b"".join(stdout_chunks), b"".join(stderr_chunks), proc.returncode


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


#: The exact, closed key set a probe report must carry -- an extra or missing key refuses the
#: whole report (PR #108 SR1 F4). ``probe_script_sha256`` is required on every report; see
#: :data:`~manosube_agent_civilization.runtime.types.SSH_PROBE_SCRIPT_SHA256`.
#: ``deployment_config_fingerprint`` was added by Structural Review Round 3 (SR3-F4): a
#: content digest over whatever ``SOURCE_EXCERPT_PATH``/``LOG_EXCERPT_PATH`` the probe script
#: is *actually* configured with (sibling config or shipped default) -- closing the gap where
#: two byte-identical scripts, differing only in sibling configuration, reported the identical
#: ``probe_script_sha256`` while reading entirely different real files.
_PROBE_REPORT_KEYS: frozenset[str] = frozenset(
    {
        "ok",
        "fields",
        "deployment_identity",
        "reason",
        "probe_script_sha256",
        "deployment_config_fingerprint",
    }
)

#: The transports :class:`SshRuntimeAdapter` itself may ever be constructed under
#: (PR #108 Structural Review Round 2, SR2-F1) -- deliberately excludes ``MANUAL_SSH``, which
#: is Capability A's own render-only path (:func:`~manosube_agent_civilization.runtime.
#: transport_control.render_manual_ssh_command`): a Human copying and running a command
#: themselves is that mode's whole authorization act, so this package must never itself
#: construct a live adapter for it. ``GITHUB_ACTIONS`` and ``PREAUTHORIZED_UNATTENDED_SSH``
#: each carry their own distinct authorization basis (an already-dispatched Actions job a
#: Human authorized, versus a grant explicitly naming unattended execution with no Human
#: present) -- :meth:`SshRuntimeAdapter.__init__` requires the grant to permit whichever one of
#: the two this adapter is actually being constructed under, never a hardcoded assumption that
#: every execution is the unattended case.
_ADAPTER_EXECUTABLE_TRANSPORTS: frozenset[str] = frozenset(
    {"GITHUB_ACTIONS", "PREAUTHORIZED_UNATTENDED_SSH"}
)

#: ``SshRuntimeAdapter.__init__``'s own transport-admission check reads ``type(self).
#: _ALLOWED_TRANSPORTS`` rather than this module-level constant directly (PR #108 Structural
#: Review Round 3, SR3-F3(A)) -- :class:`CapturedProbeReportRuntimeAdapter` overrides it to
#: exactly ``{"MANUAL_SSH"}``, since *that* subclass never spawns anything live and exists
#: solely to replay a Human-captured transcript through the identical validation/classification
#: logic this class itself applies to a real subprocess result.


class SshRuntimeAdapter:
    """A complete :class:`~manosube_agent_civilization.runtime.types.RuntimeAdapter` performing
    one real, bounded SSH command execution against ``boundary["endpoint"]`` -- stdlib
    ``subprocess`` invoking the system ``ssh`` binary only, no new runtime dependency.

    **PR #108 Structural Review Round 1, F1 -- a verified grant is required at construction,
    not merely recommended.** The first delivery let a caller construct this adapter directly
    and bypass every check :mod:`~manosube_agent_civilization.runtime.transport_control` owns.
    Construction now itself performs the one gate every executable path must pass: *grant*
    must genuinely verify (a real Ed25519 signature by the exact Project Binding's own Human
    Authority, resolved through a fresh ``boot_project`` call for *project_id*/
    *project_binding_id* -- never a self-asserted string), must currently be within its own
    validity window at *now*, and must explicitly permit ``PREAUTHORIZED_UNATTENDED_SSH`` --
    the one mode this package will itself execute SSH for with no Human present. ``observe()``
    additionally re-matches the verified grant against the real ``target_identity``/
    ``boundary`` immediately before spawning ``ssh``, so a grant genuinely issued for one
    target can never be reused against another.

    **PR #108 Structural Review Round 2, SR2-F2 -- construction-time verification is re-run,
    live, at every attempt.** The first correction's own gate above still only ran once, at
    construction; an adapter retained across a longer-lived process (an Actions job, an
    unattended controller) could then observe repeatedly without ever re-proving the grant is
    still signed, current, Boot-authentic, or permitted. ``observe()`` now re-runs the complete
    chain -- signature, fresh ``boot_project`` restoration, transport permission, expiry --
    immediately before anything is spawned, using this exact attempt's own
    ``boundary["time_window"]["issued_at"]`` as the live instant (the one instant
    :mod:`~manosube_agent_civilization.runtime.route` has already proved the whole attempt
    genuinely occurs at). The same round also extended ``require_grant_matches_attempt`` to
    additionally bind the attempt's own claimed ``deployment_fingerprint`` and to require the
    attempt's own ``boundary.timeout_seconds`` never exceed the grant's own signed
    ``max_timeout_seconds`` ceiling.

    **PR #108 Structural Review Round 2, SR2-F1 -- constructed under either executable
    transport, never a hardcoded assumption.** The first two rounds always required
    ``PREAUTHORIZED_UNATTENDED_SSH`` specifically, as though every execution of this adapter
    were the fully unattended, no-Human-present case. A real ``GITHUB_ACTIONS``-dispatched
    observation now also executes through this identical adapter (never a second, parallel
    implementation) -- an already-dispatched Actions job a Human authorized is itself that
    attempt's own authorization act, distinct from the unattended case's own grant-only basis.
    *transport* (one of :data:`_ADAPTER_EXECUTABLE_TRANSPORTS`, never ``MANUAL_SSH`` -- that
    mode's whole point is that a Human runs the rendered command themselves, so this package
    never constructs a live adapter for it) says which of the two this construction, and every
    later live re-verification inside ``observe()``, requires the grant to explicitly permit.

    The V-proof target for Issue #105's ``SSH_EXEC_BOUNDED`` method: exercised in this
    delivery's own test suite against one disposable, local target the test itself controls
    when a real local SSH fixture is available without any machine/service/credential
    modification; otherwise that specific proof is reported pending rather than claimed from a
    fixture (the same ``FakeRuntimeAdapter``-backed fixture proofs every other counterexample
    in this module's own test matrix, exactly as they already do for HTTP).

    Expects the remote probe to print exactly one JSON object as the last non-empty line of
    its stdout, carrying exactly ``{"ok": bool, "fields": {...} | None, "deployment_identity":
    str | None, "reason": str | None, "probe_script_sha256": str}`` -- the identical closed
    shape ``scripts/runtime_observation_probe.py`` (this delivery's own pinned probe script,
    run locally for Capability A/B and remotely for this adapter) always emits.
    ``probe_script_sha256`` must equal the live-reverified grant's own signed
    ``probe_script_sha256`` field (F3; bound to the Human Authority's own signature rather than
    to the bare public constant by SR2-F4) -- a probe *name* identifies nothing, so this is a
    genuine improvement over that alone. **Corrected claim (PR #108 Structural Review Round 4,
    SR4-F4):** this is still only a consistency check, never proof of what genuinely executed.
    ``probe_script_sha256``/``SSH_PROBE_SCRIPT_SHA256`` are both *public* values; a substitute
    script can trivially echo back the expected public digest without forging anything, since
    nothing about printing a known value requires defeating a signature. What is actually
    proved is "the probe's self-report agrees with the grant's signed value" -- no stronger
    remote attestation primitive exists over plain SSH, and a fully compromised target can
    report whatever digest it likes. A nonzero process exit code (other
    than ``ssh``'s own documented ``255``) is never parsed as a report at all, however
    well-formed the text happens to look (F4) -- the probe's own convention is to always exit
    ``0``, so anything else means it never ran to completion on its own terms. Subprocess
    stdout/stderr are read through a hard byte ceiling and the Boundary's own ``timeout_seconds``
    through a hard wall-clock ceiling (:func:`_run_bounded_subprocess`), both drawn from the
    verified grant's own ``max_output_bytes``; ``observed_fields`` is the closed subset of
    ``fields`` named by ``boundary["permitted_fields"]`` (itself already proved a subset of the
    grant's own ``permitted_fields`` by ``require_grant_matches_attempt``).
    """

    #: Overridden by :class:`CapturedProbeReportRuntimeAdapter` to exactly ``{"MANUAL_SSH"}``.
    _ALLOWED_TRANSPORTS: ClassVar[frozenset[str]] = _ADAPTER_EXECUTABLE_TRANSPORTS

    def __init__(
        self,
        *,
        grant: Mapping[str, Any],
        store: Any,
        project_id: str,
        project_binding_id: str,
        now: str,
        transport: str = "PREAUTHORIZED_UNATTENDED_SSH",
        adapter_identity: Mapping[str, Any] | None = None,
        ssh_executable: str = "ssh",
        now_fn: Callable[[], str] | None = None,
    ) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "ssh_runtime_adapter", "version": "0.1"}
        )
        #: Overridable only for this delivery's own real-transport test (a disposable local
        #: SSH fixture reached through a non-default port/executable) -- never a caller-
        #: supplied value reachable through any Boundary field.
        self._ssh_executable = ssh_executable
        #: The one trusted clock this adapter's own live re-verification reads (PR #108
        #: Structural Review Round 3, SR3-F2) -- defaults to
        #: :func:`~manosube_agent_civilization.runtime.engine.current_utc_instant`, this
        #: package's own single real-clock owner. Overridable only by a deterministic test
        #: fixture; never reachable through any Boundary/grant/CLI field a caller controls.
        self._now_fn: Callable[[], str] = now_fn or current_utc_instant
        #: Retained only so ``observe()`` can re-verify the grant *again*, fresh, immediately
        #: before it is actually used (PR #108 Structural Review Round 2, SR2-F2) -- never read
        #: for any other purpose, and never a substitute for that live re-check.
        self._store = store
        self._project_id = project_id
        self._project_binding_id = project_binding_id
        # PR #108 Structural Review Round 2, SR2-F1 (SR3-F3(A)): this adapter is now
        # constructed under either of its two own executable transports -- never a hardcoded
        # assumption that every execution is the unattended one -- and the grant must
        # explicitly permit *that exact* transport, not merely "some" transport.
        # ``type(self)._ALLOWED_TRANSPORTS`` rather than the module constant directly, so
        # :class:`CapturedProbeReportRuntimeAdapter` can narrow it to exactly ``MANUAL_SSH``.
        allowed_transports = type(self)._ALLOWED_TRANSPORTS
        if transport not in allowed_transports:
            raise RuntimeRequirementError(
                f"{type(self).__name__} may only be constructed for one of "
                f"{sorted(allowed_transports)}, never {transport!r}"
            )
        self._transport = transport
        checked_grant = require_grant_permits_transport(
            grant,
            transport,
            store=store,
            project_id=project_id,
            project_binding_id=project_binding_id,
        )
        self._grant = require_grant_not_expired(
            checked_grant,
            store=store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            now=now,
        )

    def _reverify_live_grant(
        self, *, target_identity: Mapping[str, Any], boundary: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Re-run the complete grant verification chain fresh, immediately before anything is
        spawned or classified (PR #108 Structural Review Round 2, SR2-F2; the live instant
        corrected by Round 3, SR3-F2) -- shared by :meth:`observe` and by
        :class:`CapturedProbeReportRuntimeAdapter`'s identical use, so neither path trusts only
        what construction verified once and cached.

        **SR3-F2.** The prior round used ``boundary["time_window"]["issued_at"]`` as the live
        instant -- a value a CLI/workflow caller supplies, and which can trivially be backdated
        to resurrect an otherwise-expired grant. This now reads ``self._now_fn()`` instead --
        this package's own one trusted clock (:func:`~manosube_agent_civilization.runtime.
        engine.current_utc_instant` in production, an injected deterministic stub only in
        tests) -- so grant expiry is checked against the actual instant execution is genuinely
        happening at, never a caller-suppliable string.
        """

        live_now = self._now_fn()
        checked_grant = require_grant_permits_transport(
            self._grant,
            self._transport,
            store=self._store,
            project_id=self._project_id,
            project_binding_id=self._project_binding_id,
        )
        checked_grant = require_grant_not_expired(
            checked_grant,
            store=self._store,
            project_id=self._project_id,
            project_binding_id=self._project_binding_id,
            now=live_now,
        )
        # PR #108 SR1 F1 (retained): the freshly re-verified grant must also bind exactly this
        # attempt's own real target and real scope -- additionally the attempt's own claimed
        # deployment_fingerprint and timeout ceiling (SR2-F2), and the Boundary's own window
        # bound inside the grant's own authorized window (SR3-F2; see
        # ``transport_control.require_grant_matches_attempt``).
        checked_grant = require_grant_matches_attempt(
            checked_grant, target_identity=target_identity, boundary=boundary
        )
        # PR #108 Structural Review Round 4, SR4-F2: the trusted actual instant must also fall
        # inside *this attempt's own Boundary* window directly -- not only inside the grant's
        # (checked above) and not only structurally contained by it (checked by
        # ``require_grant_matches_attempt`` immediately above). A grant valid for a wide window
        # that structurally contains a much narrower Boundary window still passed both of those
        # checks at a live instant that fell inside the grant's own window but outside the
        # Boundary's -- this is the missing third check that closes that gap.
        require_boundary_within_live_window(boundary, now=live_now)
        return checked_grant

    def observe(
        self, *, target_identity: Mapping[str, Any], boundary: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        checked_grant = self._reverify_live_grant(target_identity=target_identity, boundary=boundary)
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
            expected_probe_script_sha256=checked_grant["probe_script_sha256"],
            expected_deployment_config_fingerprint=checked_grant["deployment_config_fingerprint"],
            ssh_executable=self._ssh_executable,
        )
        try:
            stdout_bytes, stderr_bytes, returncode = _run_bounded_subprocess(
                argv,
                timeout_seconds=boundary["timeout_seconds"],
                max_output_bytes=checked_grant["max_output_bytes"],
            )
        except subprocess.TimeoutExpired:
            return {
                "transport_outcome": "TIMEOUT",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }
        except _OutputTooLargeError:
            return {
                "transport_outcome": "MALFORMED",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }
        except OSError:
            return {
                "transport_outcome": "UNAVAILABLE",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }
        return self._classify_probe_result(
            stdout_bytes, stderr_bytes, returncode, checked_grant=checked_grant, boundary=boundary
        )

    def _classify_probe_result(
        self,
        stdout_bytes: bytes,
        stderr_bytes: bytes,
        returncode: int,
        *,
        checked_grant: Mapping[str, Any],
        boundary: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Turn one already-obtained ``(stdout, stderr, returncode)`` triple into this
        adapter's own closed transport-outcome report -- shared, unchanged, by :meth:`observe`
        (a real subprocess result) and by :class:`CapturedProbeReportRuntimeAdapter` (a
        Human-captured transcript); PR #108 Structural Review Round 3, SR3-F3(A) -- a captured
        report is classified through the identical scope/digest/excerpt validation a live one
        is, never a second, looser parser.
        """

        # PR #108 SR3-F3(A): the grant's own max_output_bytes is enforced here too, not only by
        # _run_bounded_subprocess upstream of a real subprocess call -- the one defense-in-depth
        # site a captured transcript (which never goes through that helper at all) would
        # otherwise have none of. A CLI's own file-read ceiling (e.g. import-output's fixed 1
        # MiB cap) is a different, independent bound; this is the signed grant's own.
        max_output_bytes = checked_grant["max_output_bytes"]
        if len(stdout_bytes) > max_output_bytes or len(stderr_bytes) > max_output_bytes:
            return {
                "transport_outcome": "MALFORMED",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        # PR #108 SR1 F4: exit-code semantics precede report parsing entirely. The probe
        # script always exits 0 on its own terms (see its module docstring); any other code
        # means it never ran to completion, so nothing in stdout is ever trusted as a report,
        # however well-formed it looks -- this is what closes the "a truthy-looking report
        # overrides a nonzero exit" finding, structurally, rather than by special-casing the
        # one reported example.
        if returncode == 255:
            if "permission denied" in stderr.lower():
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
        if returncode != 0:
            return {
                "transport_outcome": "MALFORMED",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }

        probe_report = self._parse_probe_report(stdout)
        if probe_report is None:
            return {
                "transport_outcome": "MALFORMED",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }

        # PR #108 SR1 F3 (SR2-F4): a probe *name* identifies nothing about which file actually
        # executed on the target -- only a matching content digest does, and that digest is now
        # compared against the live-reverified grant's own *signed* ``probe_script_sha256``
        # field (never the bare public constant a same-named substitute could simply print
        # back). Corrected claim (SR4-F4): ``probe_script_sha256`` is a *public* value, so
        # echoing it back is not forgery and defeats no signature -- this comparison is a
        # consistency check against the grant's own signed expectation, never an independent
        # cryptographic attestation of what actually executed on the target.
        if probe_report["probe_script_sha256"] != checked_grant["probe_script_sha256"]:
            return {
                "transport_outcome": "MALFORMED",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }

        # PR #108 Structural Review Round 3, SR3-F4: a probe artifact's own content digest
        # proves which *script* ran, but two byte-identical scripts, each deployed beside a
        # different sibling configuration, still report the identical ``probe_script_sha256``
        # while reading entirely different real source/log files. The probe's own self-reported
        # ``deployment_config_fingerprint`` -- a digest over whichever excerpt paths it is
        # *actually* configured with -- is compared against the live-reverified grant's own
        # signed value for exactly the same reason the script digest is: a deployment that
        # silently drifted to a different sibling config than the one the Human Authority
        # actually approved is refused, never silently observed under the old approval.
        if (
            probe_report["deployment_config_fingerprint"]
            != checked_grant["deployment_config_fingerprint"]
        ):
            return {
                "transport_outcome": "MALFORMED",
                "observed_fields": None,
                "observed_deployment_identity": None,
            }

        if not probe_report["ok"]:
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
        # PR #108 SR1 F4 (SR2-F3(B)): the grant's own max_lines bounds whatever excerpt line
        # counts a SOURCE_LOG_EXCERPT_BOUNDED report self-reports. The first correction only
        # ever compared the report's own self-reported ``*_line_count`` integer against the
        # bound -- never against the real excerpt string it claimed to describe -- so a report
        # could declare an acceptable (or missing, or negative, or non-int) count while the
        # actual ``*_excerpt`` content it shipped was arbitrarily larger, and it would still be
        # accepted. Both self-reported counters are now independently recomputed from the real
        # excerpt content and must *exactly* equal what was reported -- the one shape a
        # genuinely honest probe (see ``scripts/runtime_observation_probe.py``'s own
        # ``_bounded_excerpt``) always produces -- before the line-count bound is even checked
        # against the real, recomputed value.
        max_lines = checked_grant["max_lines"]
        for excerpt_field, count_field, byte_length_field in (
            ("source_excerpt", "source_line_count", "source_excerpt_byte_length"),
            ("log_excerpt", "log_line_count", "log_excerpt_byte_length"),
        ):
            excerpt = fields.get(excerpt_field)
            if excerpt is None:
                continue
            if not isinstance(excerpt, str):
                return {
                    "transport_outcome": "MALFORMED",
                    "observed_fields": None,
                    "observed_deployment_identity": None,
                }
            actual_line_count = len(excerpt.splitlines())
            actual_byte_length = len(excerpt.encode("utf-8"))
            reported_line_count = fields.get(count_field)
            reported_byte_length = fields.get(byte_length_field)
            if (
                not isinstance(reported_line_count, int)
                or isinstance(reported_line_count, bool)
                or reported_line_count != actual_line_count
                or not isinstance(reported_byte_length, int)
                or isinstance(reported_byte_length, bool)
                or reported_byte_length != actual_byte_length
                or actual_line_count > max_lines
            ):
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
        precedes it rather than replacing it) -- or ``None`` if no line parses as one, carries
        any key other than exactly :data:`_PROBE_REPORT_KEYS`, or carries a wrongly-typed
        ``ok``/``fields``/``reason``/``deployment_identity``/``probe_script_sha256``
        (PR #108 SR1 F4 -- a truthy-looking string can never again stand in for a genuine
        boolean)."""

        for line in reversed(stdout.splitlines()):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return None
            if not isinstance(parsed, dict) or set(parsed) != _PROBE_REPORT_KEYS:
                return None
            if not isinstance(parsed.get("ok"), bool):
                return None
            if parsed.get("fields") is not None and not isinstance(parsed["fields"], dict):
                return None
            if parsed.get("reason") is not None and not isinstance(parsed["reason"], str):
                return None
            if parsed.get("deployment_identity") is not None and not isinstance(
                parsed["deployment_identity"], str
            ):
                return None
            if not isinstance(parsed.get("probe_script_sha256"), str):
                return None
            if not isinstance(parsed.get("deployment_config_fingerprint"), str):
                return None
            return parsed
        return None


class CapturedProbeReportRuntimeAdapter(SshRuntimeAdapter):
    """Replays one already-captured ``(stdout, stderr, returncode)`` triple -- a Human-run
    manual command's own output, pasted back -- through :class:`SshRuntimeAdapter`'s identical
    grant-scoped validation and classification, never spawning a subprocess or opening a
    connection of its own (PR #108 Structural Review Round 3, SR3-F3(A)).

    **The gap this closes.** The first two rounds' own ``import-output`` CLI subcommand parsed
    a captured transcript through the identical closed-shape report parser and compared its
    digest against the grant's own signed value, then stopped -- it never applied the grant's
    own ``max_output_bytes``/``max_lines``/``permitted_fields`` bounds, never bound the captured
    report to a real ``target_identity``/request, never redacted anything, and never produced
    the canonical ``runtime_observation_envelope``/receipt/Evidence hand-off every other
    transport's own observation produces. A captured report naming the wrong target, an
    unpermitted field, or a self-reported line count that lied about the real excerpt it shipped
    was still echoed back as ``{"ok": true, ...}``.

    **The fix.** This class is constructed with the grant (verified exactly as
    :class:`SshRuntimeAdapter` itself verifies it -- signature, fresh Boot-restored authority,
    and, via :attr:`_ALLOWED_TRANSPORTS`, permission for exactly ``MANUAL_SSH``, never
    ``GITHUB_ACTIONS``/``PREAUTHORIZED_UNATTENDED_SSH``) plus the already-captured triple, and
    its own ``observe()`` override does nothing but re-verify the grant live
    (:meth:`SshRuntimeAdapter._reverify_live_grant`, identical to every other transport) and
    hand the captured triple to :meth:`SshRuntimeAdapter._classify_probe_result` -- the exact
    same method a real subprocess result is classified through. A caller that wants this
    captured-and-validated result to become a genuine canonical fact passes this adapter to
    :func:`~manosube_agent_civilization.runtime.route.observe_runtime_target` exactly as it
    would any other adapter -- reaching the real envelope, receipt, and Evidence hand-off,
    never a second, parallel, unbound return path.

    **PR #108 Structural Review Round 4, SR4-F3 -- capture provenance is now required, never
    silently defaulted.** *captured_stderr*/*captured_returncode* previously defaulted to
    ``b""``/``0``, so a caller (this delivery's own ``import-output`` CLI subcommand, in
    particular) that never actually captured a Human operator's real exit status still
    constructed this adapter successfully and classified the pasted stdout as though the
    command that produced it had exited cleanly -- a report left behind by a *failed* command
    was indistinguishable from one a successful command produced. Both parameters are now
    required, with no default: a caller must explicitly supply the real captured exit code and
    stderr it actually observed (or explicitly pass ``b""``/``0`` if that is genuinely what was
    captured) -- the deliberate act of supplying them is this package's own disclosed
    "operator attestation", the identical category of act as a Human running a rendered SSH
    command themselves already is for ``MANUAL_SSH``'s own authorization, never a new
    cryptographic signature or a new key.
    """

    #: Never ``GITHUB_ACTIONS``/``PREAUTHORIZED_UNATTENDED_SSH`` -- this class never spawns
    #: anything live, so it is only ever constructed under the one transport whose own
    #: authorization act is a Human running a command themselves.
    _ALLOWED_TRANSPORTS: ClassVar[frozenset[str]] = frozenset({"MANUAL_SSH"})

    def __init__(
        self,
        *,
        captured_stdout: bytes,
        captured_stderr: bytes,
        captured_returncode: int,
        grant: Mapping[str, Any],
        store: Any,
        project_id: str,
        project_binding_id: str,
        now: str,
        adapter_identity: Mapping[str, Any] | None = None,
        now_fn: Callable[[], str] | None = None,
    ) -> None:
        super().__init__(
            grant=grant,
            store=store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            now=now,
            transport="MANUAL_SSH",
            adapter_identity=(
                adapter_identity
                or {"adapter": "captured_probe_report_runtime_adapter", "version": "0.1"}
            ),
            now_fn=now_fn,
        )
        self._captured_stdout = captured_stdout
        self._captured_stderr = captured_stderr
        self._captured_returncode = captured_returncode

    def observe(
        self, *, target_identity: Mapping[str, Any], boundary: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        checked_grant = self._reverify_live_grant(target_identity=target_identity, boundary=boundary)
        return self._classify_probe_result(
            self._captured_stdout,
            self._captured_stderr,
            self._captured_returncode,
            checked_grant=checked_grant,
            boundary=boundary,
        )
