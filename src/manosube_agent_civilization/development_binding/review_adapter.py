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
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
from typing import Any

from .errors import ReviewAdapterError
from .executor_selection import is_safe_repository_relative_path

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
) -> ReviewLaunchResult:
    """Launch *argv* as the one new process group this call owns, and return its bounded
    outcome.

    *argv* is passed to :class:`subprocess.Popen` as a literal list -- never through a shell,
    so nothing in a reviewed PR's own content can be interpolated into a second command. The
    whole process group is killed (`os.killpg`) the moment *max_seconds* elapses, not merely
    the direct child -- a process that forked its own children before the deadline cannot
    outlive it by handing work to them. Captured ``stdout``/``stderr`` are each capped
    independently at *max_output_bytes*; bytes beyond the cap are read and discarded, never
    buffered, so unbounded output from the reviewed subprocess cannot grow this process's own
    memory without bound.

    *clock* is the caller's own trusted-clock callable (``Callable[[], str]``), used only for
    the two timestamps on the returned result -- this function still uses the real monotonic
    clock internally for the deadline itself, since a wall-clock timeout is a real-time
    property no injected logical clock can stand in for.
    """

    started_at = clock()
    process = subprocess.Popen(  # noqa: S603 -- argv is a literal list, never shell-interpreted
        list(argv),
        cwd=str(cwd),
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    assert process.stdout is not None  # noqa: S101 -- PIPE guarantees this; narrows for mypy
    assert process.stderr is not None  # noqa: S101
    stdout_fd = process.stdout.fileno()
    stderr_fd = process.stderr.fileno()
    os.set_blocking(stdout_fd, False)
    os.set_blocking(stderr_fd, False)

    buffers: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
    truncated: dict[str, bool] = {"stdout": False, "stderr": False}
    fd_names = {stdout_fd: "stdout", stderr_fd: "stderr"}

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
                capacity = max_output_bytes - len(buffers[name])
                if capacity <= 0:
                    truncated[name] = True
                    continue
                buffers[name].extend(chunk[:capacity])
                if len(chunk) > capacity:
                    truncated[name] = True
    finally:
        selector.close()

    if timed_out:
        with suppress(ProcessLookupError):
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        with suppress(subprocess.TimeoutExpired):
            process.wait(timeout=5)
    else:
        process.wait()

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
    """The two separate facts a cancellation attempt can ever establish. See the module
    docstring's own "Process-group-aware cancellation" section for why these are never
    conflated into one boolean or one status string."""

    local_process_group_terminated: bool
    provider_server_state: str


def cancel_review_task(
    pid: int, *, confirmation_timeout_seconds: float = 5.0
) -> CancellationOutcome:
    """Terminate the process group rooted at *pid* -- the one this delivery's own
    :func:`launch_review_process` started -- and report what was actually confirmed.

    Never touches any process outside that group: a shared Codex background server process,
    or any other task the operator is separately running, is not *pid*'s own process group and
    is never signalled by this call.
    """

    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return CancellationOutcome(
            local_process_group_terminated=True,
            provider_server_state=PROVIDER_SERVER_STATE_UNAVAILABLE,
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
