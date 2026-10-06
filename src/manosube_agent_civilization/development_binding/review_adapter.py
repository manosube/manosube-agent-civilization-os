"""The sole external-effect adapter for one Bounded Review (Decision 0004, Issue #109).

Every other owner in this decision -- :mod:`.review_selection` (pure admission),
:mod:`.review_control` (the durable claim/budget ledger) -- performs no network call, launches
no process, and touches no filesystem beyond its own ledger file. This module is where that
changes: it is the one place this decision's own code may ever start a subprocess, build a
restricted environment for it, stage untrusted inspection inputs, or send it a signal. Nothing
in this delivery calls any of these functions with ``ACTIVATION_DEFAULT`` anything but
``False`` (`.policy.BOUNDED_REVIEW_ACTIVATION_DEFAULT`) -- every exercise of this module in
this delivery's own tests runs a controlled local fake executable, never the real Codex CLI
(``REAL_CODEX_MODEL_REQUEST_ALLOWED=false``).

**Credential isolation** (handoff §7). :func:`build_subprocess_environment` is an allowlist,
never a denylist: only the names a caller explicitly lists are ever copied from the orchestrating
process's own environment into the child's, and a name that is itself credential-shaped
(``TOKEN``/``SECRET``/``KEY``/``PASSWORD``/``CREDENTIAL`` appearing in it) is refused even if a
caller tries to allow it -- a repository write token or a production key can never reach the
reviewed subprocess through this function, because it is never in the one list this function
ever reads from.

**Read-only inspection workspace** (handoff §7). :func:`prepare_inspection_workspace` copies
only the grant's own ``permitted_paths`` -- never the whole checkout -- into a fresh temporary
directory, and marks every copied file read-only (``0o444``) before returning it. Untrusted PR
content (a changed ``AGENTS.md``, an install script, a shell fragment, a hook) that is not
itself one of those named paths is never staged into the workspace at all; it does not need a
second check to be refused, because this function never looks at it in the first place.

**Process-group-aware cancellation** (handoff §5). The observed Codex CLI runs a local
background server (`review_selection`'s own module docstring already states the pinned,
single-supported configuration this reflects); killing only the foreground process this module
started proves nothing about whatever that server continues doing on the reviewer's own
behalf. :func:`cancel_review_task` accordingly reports two separate facts, never conflated into
one: whether the process group *this call itself started* is confirmed terminated
(``local_process_group_terminated``), and the provider/server-side task's own state, which this
module can never confirm and therefore always reports as ``"UNAVAILABLE"`` -- never ``"STOPPED"``,
and never retried once recorded.

**Bounded launch** (handoff §4/§5). :func:`launch_review_process` enforces both bounds the
numeric ceiling names together: a wall-clock deadline (the whole process group is killed, not
merely the one child, the moment it is exceeded) and a captured-output cap (additional bytes
beyond the cap are drained and discarded, never buffered, so a reviewed PR cannot force
unbounded memory growth by producing unbounded output). Exceeding either is recorded on the
result, never silently treated as success.

**F3 correction (PR #112 comment 6019024445).** The deadline above is now enforced for the
whole call, not merely while a stdout/stderr pipe remains open -- a child that closes both
streams and keeps running no longer falls through to an unbounded ``process.wait()``. The
output cap is now one combined budget across both streams together, never two independent
per-stream caps that could each admit up to the full limit. :func:`cancel_review_task` now
requires *owned_process_identity* (:func:`process_identity_token`) and refuses to signal
anything -- sending zero signals -- when the live process at that PID no longer carries the
identity this module itself observed at launch, closing a PID-reuse signal-the-wrong-process
gap.

**F4 correction (PR #112 comment 6019024445).** An environment allowlist and a read-only
workspace are both reversible by the identical same-UID subprocess they appear to restrain --
neither is genuine isolation. :func:`launch_review_process` now refuses to launch at all
(``require_isolation=True`` by default) unless :func:`check_isolation_capability` has just
empirically confirmed, via a real negative-control probe (not a capability guess), that a
Linux mount+user namespace (:func:`build_isolated_argv`, via ``unshare``) actually hides the
requested *mask_paths* from the child -- a safe refusal, never a silent fallback to the weaker
allowlist/read-only boundary, when that cannot be confirmed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
import json
import os
from pathlib import Path
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any

from .errors import ReviewAdapterError
from .executor_selection import is_safe_repository_relative_path
from .policy import BOUNDED_REVIEW_NUMERIC_LIMITS

#: Every environment variable name whose presence alone marks it as credential-shaped --
#: checked against the *name*, never the value, so a caller cannot smuggle a secret through
#: under an innocuous-looking key this list happens not to catch; the caller's own
#: *allowed_keys* is the actual secret boundary, this is the one guard on top of it.
_FORBIDDEN_ENV_KEY_SUBSTRINGS: tuple[str, ...] = (
    "TOKEN",
    "SECRET",
    "KEY",
    "PASSWORD",
    "CREDENTIAL",
    "AUTH",
)

#: The default allowlist a caller may use for a minimal, credential-free POSIX child
#: environment. Never a denylist default -- every name not in this set (or a caller's own
#: narrower/wider explicit list, itself still checked against the forbidden substrings above)
#: is simply absent from the child's environment.
DEFAULT_ALLOWED_ENV_KEYS: frozenset[str] = frozenset({"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR"})


def build_subprocess_environment(
    base_env: Mapping[str, str], *, allowed_keys: frozenset[str] = DEFAULT_ALLOWED_ENV_KEYS
) -> dict[str, str]:
    """Return a new environment mapping containing only *allowed_keys*' own present values
    from *base_env* -- an allowlist copy, never a filtered copy of everything else.

    Refuses outright (:class:`~.errors.ReviewAdapterError`) if *allowed_keys* itself names
    anything that looks credential-shaped, whatever its actual value in *base_env* would have
    been -- this is a defense against the allowlist itself being misconfigured, not a check on
    what the orchestrating process happens to currently hold.
    """

    for key in allowed_keys:
        upper = key.upper()
        if any(forbidden in upper for forbidden in _FORBIDDEN_ENV_KEY_SUBSTRINGS):
            raise ReviewAdapterError(
                f"allowed_keys names a credential-shaped environment variable: {key!r}"
            )
    return {key: base_env[key] for key in allowed_keys if key in base_env}


def prepare_inspection_workspace(source_root: Path, *, permitted_paths: Sequence[str]) -> Path:
    """Return a fresh temporary directory containing read-only copies of exactly
    *permitted_paths*, resolved under *source_root* -- never the whole checkout, and never a
    path outside the identical safe, repository-relative grammar `.executor_selection.
    is_safe_repository_relative_path` already enforces for a grant's own ``permitted_paths``.

    Every copied file is ``chmod``-ed ``0o444`` before this function returns, so an inspecting
    subprocess that opens one of them for writing is refused by the filesystem itself -- a
    sandbox *label* alone is explicitly not proof of this (handoff §7); this is the one
    concrete, independently-inspectable boundary this module itself can set before any process
    is ever launched against the workspace.
    """

    if not permitted_paths:
        raise ReviewAdapterError("permitted_paths must not be empty")
    workspace = Path(tempfile.mkdtemp(prefix="bounded-review-workspace-"))
    try:
        for relative in permitted_paths:
            if not is_safe_repository_relative_path(relative):
                raise ReviewAdapterError(f"unsafe permitted path: {relative!r}")
            source = (source_root / relative).resolve()
            if source_root.resolve() not in source.parents and source != source_root.resolve():
                raise ReviewAdapterError(f"permitted path escapes source_root: {relative!r}")
            if not source.is_file():
                raise ReviewAdapterError(
                    f"permitted path does not resolve to a real file: {relative!r}"
                )
            destination = workspace / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            destination.chmod(0o444)
    except BaseException:
        shutil.rmtree(workspace, ignore_errors=True)
        raise
    return workspace


def cleanup_inspection_workspace(workspace: Path) -> None:
    """Remove a workspace :func:`prepare_inspection_workspace` returned. Best-effort: a
    workspace that cannot be removed is not this module's own external effect to retry."""

    shutil.rmtree(workspace, ignore_errors=True)


# --------------------------------------------------------------------------- #
# F4 correction (Issue #109 PR #112 Structural Review Round 1, comment 6019024445): an
# environment allowlist and a chmod'ed read-only workspace are not filesystem isolation -- a
# reviewed subprocess running under the same UID as the orchestrator can still read anything
# that UID can read via an absolute path, HOME included. This is the one real, kernel-enforced
# boundary this module adds: a fresh mount+PID namespace (``unshare``) with an empty, mode-000
# tmpfs mounted *over* each path in ``mask_paths`` -- genuinely hiding it from the launched
# process, not merely asking it not to look. Every launch empirically re-probes that this
# mechanism actually works in the current environment before relying on it; if the probe
# itself cannot confirm isolation, the launch refuses outright rather than silently falling
# back to the allowlist/chmod boundary alone (handoff §7's own "safe refusal" instruction).
#
# This does **not** make the workspace tamper-proof against a same-UID adversary: chmod 0o444
# is reversible, and an unlink/replace of a "read-only" file is permitted by the same owning
# UID regardless of the file's own mode, because that permission check is governed by the
# parent directory, not the file. No separate, lower-privilege reviewing account is
# established in this correction -- the handoff's own scope explicitly excludes requesting a
# new account/credential for this work -- so that residual risk is disclosed rather than
# papered over (`docs/bounded_technical_review.md` §8). What this mechanism closes is the
# more severe gap the review actually reproduced: reading an on-disk secret via an absolute
# path outside the staged workspace.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class IsolationCapability:
    """Whether this environment can genuinely hide a path from a launched subprocess, as
    actually confirmed by running a real negative-control probe -- never inferred merely from
    the presence of the ``unshare`` executable on ``PATH``."""

    available: bool
    mechanism: str
    reason: str | None


def build_isolated_argv(inner_argv: Sequence[str], *, mask_paths: Sequence[Path]) -> list[str]:
    """Return argv that runs *inner_argv* inside a fresh mount+PID namespace with an empty,
    unreadable tmpfs mounted over every path in *mask_paths*.

    Every path is masked with its own ``tmpfs`` mount (mode ``000``, size ``0``) -- the
    directory itself still exists (so the launched process does not fail merely for the path
    being absent), but nothing under it is readable, writable, or even listable by the
    launched process. ``mask_paths`` is a fixed, trusted list this module's own caller builds
    (e.g. the orchestrator's own ``HOME``) -- never content a reviewed PR influences, and the
    shell fragment below is a static template with each path individually ``shlex.quote``-d,
    never interpolated with untrusted text.
    """

    statements = ["set -e"]
    for path in mask_paths:
        quoted = shlex.quote(str(path))
        statements.append(f"mkdir -p {quoted} 2>/dev/null || true")
        statements.append(f"mount -t tmpfs -o size=0,mode=000 tmpfs {quoted}")
    statements.append('exec "$@"')
    script = "; ".join(statements)
    return [
        "unshare",
        "--user",
        "--map-root-user",
        "--mount",
        "--pid",
        "--fork",
        "--",
        "/bin/sh",
        "-c",
        script,
        "sh",
        *inner_argv,
    ]


def check_isolation_capability() -> IsolationCapability:
    """Empirically confirm, with a real negative-control probe, that this environment can
    genuinely isolate a path via :func:`build_isolated_argv` -- run fresh before every launch
    that requires it, never cached or assumed from a prior success.

    The probe plants a real sentinel file under a fresh temporary directory, launches a real
    child wrapped exactly the way a review launch would be, and the child itself asserts the
    sentinel is unreachable (exits non-zero if it can still see it). Only a confirmed-correct
    probe outcome reports ``available=True``.
    """

    if shutil.which("unshare") is None:
        return IsolationCapability(False, "unavailable", "the unshare executable is not on PATH")
    with tempfile.TemporaryDirectory(prefix="bounded-review-isolation-probe-") as probe_dir:
        probe_path = Path(probe_dir)
        sentinel = probe_path / "sentinel.txt"
        sentinel.write_text("SENTINEL", encoding="utf-8")
        probe_code = (
            f"import os, sys\nsys.exit(0 if not os.path.exists({str(sentinel)!r}) else 1)\n"
        )
        probe_argv = build_isolated_argv(
            [sys.executable, "-c", probe_code], mask_paths=[probe_path]
        )
        try:
            completed = subprocess.run(  # noqa: S603 -- probe_argv is this function's own literal list
                probe_argv, capture_output=True, timeout=10, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return IsolationCapability(
                False, "unavailable", f"isolation probe failed to run: {error}"
            )
        if completed.returncode != 0:
            return IsolationCapability(
                False,
                "unavailable",
                "isolation probe process still observed the masked sentinel "
                f"(exit code {completed.returncode}, stderr: {completed.stderr[:500]!r})",
            )
    return IsolationCapability(True, "unshare_mount_namespace", None)


def _read_proc_start_time(pid: int) -> str | None:
    """Return the Linux ``/proc/<pid>/stat`` ``starttime`` field for *pid*, or ``None`` when
    unavailable (non-Linux, or the process no longer exists). Stable for the lifetime of a
    single process instance, including across its own ``exec`` calls -- the one cheap,
    dependency-free way to bind a PID to the *exact* process instance rather than to whatever
    unrelated process the kernel may have since reused that PID for.
    """

    try:
        contents = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        # Field 2 (``comm``) is parenthesized and may itself contain spaces or parens; split
        # from the *last* ``)`` so a comm like ``(my (odd) prog)`` cannot shift every field
        # after it.
        after_comm = contents.rsplit(")", 1)[1].split()
        starttime = after_comm[19]  # field 22 overall; index 19 once fields 1-3 are removed
    except (IndexError, ValueError):
        return None
    return starttime


def process_identity_token(pid: int) -> str | None:
    """Return a token binding *pid* to its exact current process instance, or ``None`` when
    that cannot be established. :func:`cancel_review_task` requires the caller's previously
    recorded token to still match this one before it will ever signal *pid* -- a bare PID is
    not ownership, because PIDs are reused."""

    starttime = _read_proc_start_time(pid)
    if starttime is None:
        return None
    return f"{pid}:{starttime}"


def _require_within_ratified_ceiling(*, max_seconds: int, max_output_bytes: int) -> None:
    if max_seconds > BOUNDED_REVIEW_NUMERIC_LIMITS["max_process_seconds"]:
        raise ReviewAdapterError(
            f"max_seconds {max_seconds} exceeds the ratified ceiling "
            f"{BOUNDED_REVIEW_NUMERIC_LIMITS['max_process_seconds']}"
        )
    if max_output_bytes > BOUNDED_REVIEW_NUMERIC_LIMITS["max_result_bytes"]:
        raise ReviewAdapterError(
            f"max_output_bytes {max_output_bytes} exceeds the ratified ceiling "
            f"{BOUNDED_REVIEW_NUMERIC_LIMITS['max_result_bytes']}"
        )


@dataclass(frozen=True)
class ReviewLaunchResult:
    """The one external-effect launch's own bounded, structured outcome.

    *exit_code* is ``None`` only when *timed_out* is ``True`` and the process group could not
    be confirmed to have actually produced one before this module gave up waiting on it --
    never defaulted to ``0`` or any other value that could be mistaken for a real exit.
    """

    exit_code: int | None
    stdout: bytes
    stderr: bytes
    stdout_truncated: bool
    stderr_truncated: bool
    timed_out: bool
    pid: int
    process_identity: str | None
    started_at: str
    ended_at: str


def launch_review_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    max_seconds: int,
    max_output_bytes: int,
    clock: Any,
    mask_paths: Sequence[Path] = (),
    require_isolation: bool = True,
) -> ReviewLaunchResult:
    """Launch *argv* as the one new process group this call owns, and return its bounded
    outcome.

    Refuses outright, before any process is started, if *max_seconds*/*max_output_bytes*
    exceed the ratified ceiling (F3), or if *require_isolation* is true (the only mode any
    composed route in this delivery ever uses) and :func:`check_isolation_capability` cannot
    confirm genuine isolation is available right now (F4) -- never silently launching with
    only the weaker environment-allowlist/chmod boundary.

    *argv* is passed to :class:`subprocess.Popen` as a literal list -- never through a shell,
    so nothing in a reviewed PR's own content can be interpolated into a second command; when
    isolation is required, :func:`build_isolated_argv` wraps it with *mask_paths* hidden
    before it is ever launched. The whole process group is killed (`os.killpg`) the moment
    *max_seconds* elapses, not merely the direct child, and not merely while its pipes remain
    open -- the deadline covers the process's own full lifetime, including the time after both
    streams reach EOF but the process itself has not yet exited (F3's own reproduced gap).
    Captured ``stdout``/``stderr`` share one *combined* budget of *max_output_bytes* (F3: the
    ratified ceiling is a total, never one allowance per stream); bytes beyond it are read and
    discarded, never buffered, so unbounded output from the reviewed subprocess cannot grow
    this process's own memory without bound.

    *clock* is the caller's own trusted-clock callable (``Callable[[], str]``), used only for
    the two timestamps on the returned result -- this function still uses the real monotonic
    clock internally for the deadline itself, since a wall-clock timeout is a real-time
    property no injected logical clock can stand in for.
    """

    _require_within_ratified_ceiling(max_seconds=max_seconds, max_output_bytes=max_output_bytes)

    if require_isolation:
        capability = check_isolation_capability()
        if not capability.available:
            raise ReviewAdapterError(
                "genuine filesystem isolation is unavailable in this environment "
                f"({capability.reason}); refusing to launch rather than rely on the "
                "environment-allowlist/chmod-only boundary alone"
            )
        effective_argv = build_isolated_argv(list(argv), mask_paths=mask_paths)
    else:
        effective_argv = list(argv)

    started_at = clock()
    process = subprocess.Popen(  # noqa: S603 -- effective_argv is a literal list, never shell-interpreted
        effective_argv,
        cwd=str(cwd),
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    process_identity = process_identity_token(process.pid)
    assert process.stdout is not None  # noqa: S101 -- PIPE guarantees this; narrows for mypy
    assert process.stderr is not None  # noqa: S101
    stdout_fd = process.stdout.fileno()
    stderr_fd = process.stderr.fileno()
    os.set_blocking(stdout_fd, False)
    os.set_blocking(stderr_fd, False)

    buffers: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
    truncated: dict[str, bool] = {"stdout": False, "stderr": False}
    fd_names = {stdout_fd: "stdout", stderr_fd: "stderr"}
    total_captured = 0

    selector = selectors.DefaultSelector()
    selector.register(stdout_fd, selectors.EVENT_READ)
    selector.register(stderr_fd, selectors.EVENT_READ)
    open_fds = {stdout_fd, stderr_fd}

    deadline = time.monotonic() + max_seconds
    timed_out = False
    try:
        while open_fds:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            for key, _ in selector.select(timeout=min(remaining, 1.0)):
                fd = key.fd
                name = fd_names[fd]
                try:
                    chunk = os.read(fd, 65536)
                except BlockingIOError:
                    continue
                except OSError:
                    chunk = b""
                if chunk == b"":
                    selector.unregister(fd)
                    open_fds.discard(fd)
                    continue
                # F3: one combined budget across both streams, never one allowance per
                # stream -- the ratified ceiling is a total captured-result/log size.
                capacity = max_output_bytes - total_captured
                if capacity <= 0:
                    truncated[name] = True
                    continue
                kept = chunk[:capacity]
                buffers[name].extend(kept)
                total_captured += len(kept)
                if len(chunk) > capacity:
                    truncated[name] = True
    finally:
        selector.close()

    if not timed_out:
        # F3's own reproduced gap: both streams reaching EOF is not proof the process itself
        # exited -- a child that closes stdout/stderr early but keeps running must still be
        # bound by the same deadline, not an unbounded ``process.wait()``.
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
        else:
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                timed_out = True

    if timed_out:
        with suppress(ProcessLookupError):
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        with suppress(subprocess.TimeoutExpired):
            process.wait(timeout=5)

    # os.read() on the raw fds above never goes through these BufferedReader objects' own
    # buffering, but they are still open file objects that must be closed explicitly --
    # otherwise Python's own GC closes them later, at an unpredictable time, and in a
    # filterwarnings=error test suite a ResourceWarning at that point fails an unrelated test.
    process.stdout.close()
    process.stderr.close()

    ended_at = clock()
    return ReviewLaunchResult(
        exit_code=process.returncode,
        stdout=bytes(buffers["stdout"]),
        stderr=bytes(buffers["stderr"]),
        stdout_truncated=truncated["stdout"],
        stderr_truncated=truncated["stderr"],
        timed_out=timed_out,
        pid=process.pid,
        process_identity=process_identity,
        started_at=started_at,
        ended_at=ended_at,
    )


#: The provider/server-side cancellation state this module may ever report. There is no
#: ``"STOPPED"`` or ``"CANCELLED"`` value here at all -- this module performs no provider API
#: call and has no way to confirm the local background server actually stopped the owned
#: task, so that side of a cancellation is *always* this one value, never upgraded to a
#: stronger claim by anything this module itself observes about the local process.
PROVIDER_SERVER_STATE_UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class CancellationOutcome:
    """The three separate facts a cancellation attempt can ever establish. See the module
    docstring's own "Process-group-aware cancellation" section for why these are never
    conflated into one boolean or one status string.

    ``ownership_confirmed`` is the F3 correction (PR #112 comment 6019024445): a bare PID is
    never ownership, because PIDs are reused -- the caller's own previously recorded
    :func:`process_identity_token` must still match *pid*'s current identity before this
    function will ever signal it. ``False`` means no signal was ever sent, to this *or any*
    process: this function refuses rather than risk signalling an unrelated task that happens
    to now hold the same PID.
    """

    local_process_group_terminated: bool
    provider_server_state: str
    ownership_confirmed: bool


def cancel_review_task(
    *,
    pid: int,
    owned_process_identity: str,
    confirmation_timeout_seconds: float = 5.0,
) -> CancellationOutcome:
    """Terminate the process group rooted at *pid* -- the one this delivery's own
    :func:`launch_review_process` started, and whose :func:`process_identity_token` the
    caller recorded as *owned_process_identity* at that time -- and report what was actually
    confirmed.

    Refuses to signal anything at all unless *pid*'s *current* identity still matches
    *owned_process_identity*: a reused PID, or a bare caller-supplied PID with no recorded
    identity to check, is never treated as ownership. Never touches any process outside the
    owned group even once ownership is confirmed: a shared Codex background server process,
    or any other task the operator is separately running, is not *pid*'s own process group
    and is never signalled by this call.
    """

    current_identity = process_identity_token(pid)
    if current_identity is None or current_identity != owned_process_identity:
        return CancellationOutcome(
            local_process_group_terminated=False,
            provider_server_state=PROVIDER_SERVER_STATE_UNAVAILABLE,
            ownership_confirmed=False,
        )

    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return CancellationOutcome(
            local_process_group_terminated=True,
            provider_server_state=PROVIDER_SERVER_STATE_UNAVAILABLE,
            ownership_confirmed=True,
        )
    with suppress(ProcessLookupError):
        os.killpg(pgid, signal.SIGKILL)

    deadline = time.monotonic() + confirmation_timeout_seconds
    terminated = False
    while time.monotonic() < deadline:
        # If *pid* is this process's own child, a killed process becomes a zombie until
        # reaped -- and a zombie still answers `kill(pid, 0)` successfully, which would
        # otherwise make a genuinely dead process look alive for the caller's entire
        # confirmation window. Opportunistically reaping here (when we are the parent) closes
        # that gap; `ChildProcessError` (this call's own caller never spawned *pid*, e.g. a
        # controller restart recovering a pid it only recorded) falls back to the kill probe,
        # which is this module's only remaining tool in that cross-process case.
        try:
            reaped_pid, _status = os.waitpid(pid, os.WNOHANG)
            if reaped_pid == pid:
                terminated = True
                break
        except ChildProcessError:
            pass
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            terminated = True
            break
        time.sleep(0.05)
    return CancellationOutcome(
        local_process_group_terminated=terminated,
        provider_server_state=PROVIDER_SERVER_STATE_UNAVAILABLE,
        ownership_confirmed=True,
    )


#: The one structured-result key every parsed event is required to carry for
#: :func:`parse_structured_review_output` to treat it as a candidate final result. Validated
#: in this delivery only against a controlled local fake executable emitting this exact shape
#: (``tests/integration/binding/test_bounded_technical_review_route.py``) -- never against a
#: real Codex CLI invocation, consistent with ``REAL_CODEX_MODEL_REQUEST_ALLOWED=false``. The
#: real CLI's own structured-output shape for the pinned, supported configuration
#: (`.review_selection.SUPPORTED_ENVIRONMENT_FINGERPRINT`) remains independently unverified by
#: this delivery and is disclosed as such rather than assumed.
_RESULT_MARKER_KEY = "review_status"


def parse_structured_review_output(stdout: bytes) -> dict[str, Any]:
    """Return the last well-formed, newline-delimited JSON object in *stdout* that carries
    :data:`_RESULT_MARKER_KEY`, or an explicit ``UNAVAILABLE`` placeholder if none is found.

    Never raises on malformed input: a line that is not valid JSON, or a JSON value that is
    not an object carrying the marker key, is simply skipped -- the complete absence of a
    structured result is itself reported, never silently treated as zero findings.
    """

    last_event: dict[str, Any] | None = None
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and _RESULT_MARKER_KEY in parsed:
            last_event = parsed
    if last_event is None:
        return {
            _RESULT_MARKER_KEY: "UNAVAILABLE",
            "reason": "NO_STRUCTURED_RESULT_FOUND",
            "findings": [],
        }
    return last_event


def build_codex_review_argv(
    *, codex_executable: str, workspace: Path, prompt_path: Path
) -> list[str]:
    """Return the fixed argv this delivery would launch the pinned, supported Codex CLI
    configuration with -- never shell-interpolated, and never a second variant chosen at
    runtime from reviewed content.

    This exact flag set is this delivery's own best-effort construction for CLI 0.160.1's
    documented non-interactive, read-only-sandboxed ``exec`` mode (the design-preparation
    checkpoint's own cited route); it has not been independently exercised against the real
    CLI in this delivery (``REAL_CODEX_MODEL_REQUEST_ALLOWED=false``), and the activation gate
    (`.review_control.evaluate_activation_gate`) must independently confirm the installed
    CLI's own exact supported flags before any real launch -- this function alone does not
    constitute that confirmation.
    """

    return [
        codex_executable,
        "exec",
        "--json",
        "--sandbox",
        "read-only",
        "--cd",
        str(workspace),
        "--",
        str(prompt_path),
    ]


# --------------------------------------------------------------------------- #
# REUSE_NATIVE_ONLY supplement (Issue #109 comment 6019865174, PR #112 comment 6019870622):
# trusted, read-only import of a native GitHub review's own already-published evidence --
# never a second launch mode, never a network call, never a new model request.
# --------------------------------------------------------------------------- #

#: Every field :func:`validate_native_review_evidence` requires, closed -- an unknown key is
#: refused identically to every other admission grammar this delivery uses
#: (`.review_selection`'s own ``_require_request_shape``). *reviewed_commit_sha* is explicitly
#: nullable (``None``): a native review whose own platform record never named the exact commit
#: it inspected is a real, disclosed state (the design supplement's own "inspected-base-unknown
#: は現在PRベースと区別し、絶対に推定しない" requirement) -- never fabricated as "probably the
#: current head", and never silently treated the same as a confirmed match.
NATIVE_REVIEW_EVIDENCE_SCHEMA_KEYS: tuple[str, ...] = (
    "schema_version",
    "provider",
    "repository",
    "pull_request",
    "review_id",
    "reviewed_commit_sha",
    "review_state",
    "submitted_at",
    "inspected_paths",
    "findings",
)

#: The closed set of native review states this delivery recognises -- the real GitHub review
#: states (never a Binding handoff state; this delivery's own route states live in `.policy`'s
#: ratified ``handoff_states`` and never overlap this vocabulary). ``PENDING`` is the one
#: disclosed "not yet submitted/still running" state a caller's own already-fetched evidence
#: may report -- this module takes no action to poll or wait for it, and never on its own
#: initiative queues a local launch merely because a native review has not finished (the design
#: supplement's own "実行中・取得済みのレビューをWSLから重複起動しない" requirement).
NATIVE_REVIEW_STATES: frozenset[str] = frozenset(
    {"PENDING", "COMMENTED", "APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
)

#: The one provider this supplement ever imports native evidence for, in this delivery --
#: matching `.policy.BOUNDED_TECHNICAL_REVIEWER`'s own ratified value, duplicated by value
#: rather than imported (this module never imports `.policy` for anything else either).
NATIVE_REVIEW_PROVIDER = "CODEX"


def validate_native_review_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Return *evidence* once it is the one closed, immutable shape this delivery trusts as
    native GitHub review evidence -- never a network call, never a new model request:
    *evidence* is whatever the caller already independently fetched (e.g. through the GitHub
    API/MCP tooling this delivery never wraps a second time) and is handing this module purely
    to be shape-checked before anything downstream treats it as evidence.

    Raises :class:`~.errors.ReviewAdapterError` for an unreadable record only -- the wrong
    Python shape, an unknown key, a missing required key, or a field of the wrong type --
    following the identical grammar `.review_selection.evaluate_review_selection`'s own module
    docstring states for a Bounded Review Grant. *review_id* is this record's own immutable
    platform identity (a GitHub review or comment id, as a string): :func:`.review_control.
    native_review_content_address` content-addresses over it, never over anything this module
    itself computed, so two reads of the identical native review always content-address
    identically and a caller can never cause a duplicate import merely by re-fetching it.
    """

    if not isinstance(evidence, Mapping):
        raise ReviewAdapterError(f"native review evidence is not an object: {type(evidence)!r}")
    shaped = dict(evidence)
    unknown = set(shaped) - set(NATIVE_REVIEW_EVIDENCE_SCHEMA_KEYS)
    if unknown:
        raise ReviewAdapterError(f"native review evidence carries unknown keys: {sorted(unknown)}")
    missing = set(NATIVE_REVIEW_EVIDENCE_SCHEMA_KEYS) - set(shaped)
    if missing:
        raise ReviewAdapterError(f"native review evidence omits required keys: {sorted(missing)}")

    for key in (
        "schema_version",
        "provider",
        "repository",
        "pull_request",
        "review_id",
        "submitted_at",
    ):
        if not isinstance(shaped[key], str) or not shaped[key]:
            raise ReviewAdapterError(f"native review evidence {key!r} must be a non-empty string")
    if shaped["provider"] != NATIVE_REVIEW_PROVIDER:
        raise ReviewAdapterError(
            f"native review evidence names an unsupported provider: {shaped['provider']!r}"
        )
    if shaped["reviewed_commit_sha"] is not None and (
        not isinstance(shaped["reviewed_commit_sha"], str) or not shaped["reviewed_commit_sha"]
    ):
        raise ReviewAdapterError(
            "native review evidence reviewed_commit_sha must be a non-empty string or null "
            "(null means genuinely unknown, never a guess at the current head)"
        )
    if shaped["review_state"] not in NATIVE_REVIEW_STATES:
        raise ReviewAdapterError(
            f"native review evidence names an unrecognized review_state: {shaped['review_state']!r}"
        )
    if not isinstance(shaped["inspected_paths"], list) or not all(
        isinstance(path, str) and path for path in shaped["inspected_paths"]
    ):
        raise ReviewAdapterError("native review evidence inspected_paths must be a list of strings")
    if not isinstance(shaped["findings"], list):
        raise ReviewAdapterError("native review evidence findings must be a list")
    return shaped
