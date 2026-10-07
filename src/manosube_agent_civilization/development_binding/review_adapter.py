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

**SR2-F4 correction (PR #112 comment 6021757577).** :func:`launch_review_process` is now a
thin composition of :func:`validate_review_launch_preconditions` (every refusal condition that
is confirmed to precede any process start -- ceiling checks, the isolation probe, an empty
*mask_paths* with ``require_isolation=True``), :func:`spawn_review_process` (the one moment
``Popen`` actually runs, returning immediately with a live process and its
:func:`process_identity_token` already known), and :func:`collect_review_process_result` (the
potentially long, blocking wait on an *already-started* process). A caller that durably
records "an attempt is about to be made" after precondition validation but *before* calling
:func:`spawn_review_process`, and durably records the real pid/process identity immediately
after it returns -- before ever calling :func:`collect_review_process_result` -- closes the
exact gap the finding names: a crash during the (potentially 30-minute) collection wait can
never be mistaken for "nothing was sent," because the ledger already shows a confirmed,
pid-bound dispatch before that wait ever begins. See ``scripts/bounded_technical_review.py``'s
own composed route for the caller that actually does this.

**SR2-F6 correction (PR #112 comment 6021757577).** A capability probe that confirms one
sentinel path is hidden is not proof that a real launch's own protections cannot be undone by
the launched child: a process still "root" inside its own mount+user namespace retains
``CAP_SYS_ADMIN`` there and can simply unmount or remount its own masks, and a chmod-0444 file
under a writable parent directory is never actually protected from unlink-and-replace by the
identical owning UID. :func:`build_isolated_argv` now additionally self-bind-mounts the
inspection workspace and remounts it read-only *inside* the new namespace (a real mount-level
boundary, enforced below any DAC/ownership check -- never merely a file mode bit), fully
isolates networking (``unshare --net``, no interface at all, not even loopback), and then drops
every capability from the launched process's own bounding and inheritable sets
(``setpriv --bounding-set=-all --inh-caps=-all --no-new-privs``) *before* it ever execs the
reviewed command -- so the same still-UID-0-in-namespace process that set the masks and the
read-only mount up can no longer undo either one. :func:`check_isolation_capability`'s own
probe now empirically re-confirms every one of these four properties (masking, read-only
workspace, the remount/unmount being genuinely blocked after the capability drop, and network
unreachability) rather than only the one original sentinel check, and
:func:`validate_review_launch_preconditions` refuses outright if *mask_paths* is empty when
isolation is required -- an empty mask list was never evidence of isolation, only of nothing
being masked.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import secrets
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Protocol

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

    SR3-F2 correction (PR #112 comment 6030487245): the ratified ``max_input_bytes`` ceiling
    (:data:`~manosube_agent_civilization.development_binding.policy.
    BOUNDED_REVIEW_NUMERIC_LIMITS`) is now enforced *here* -- checked against each file's own
    real size before it is ever opened, with a running total checked after each copy -- never
    only as a caller-suppliable, caller-widenable parameter checked against the bundle only
    after it was already fully staged. A file, or a running total, that would exceed the
    ceiling is refused immediately, and the partial workspace is removed before this function
    raises; nothing oversized is ever left staged, even transiently.
    """

    if not permitted_paths:
        raise ReviewAdapterError("permitted_paths must not be empty")
    max_input_bytes = BOUNDED_REVIEW_NUMERIC_LIMITS["max_input_bytes"]
    workspace = Path(tempfile.mkdtemp(prefix="bounded-review-workspace-"))
    try:
        staged_bytes = 0
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
            source_size = source.stat().st_size
            staged_bytes += source_size
            if staged_bytes > max_input_bytes:
                raise ReviewAdapterError(
                    f"staged inspection input exceeds the ratified max_input_bytes ceiling "
                    f"({staged_bytes} > {max_input_bytes}) at {relative!r} -- refusing before "
                    "staging it"
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


def build_isolated_argv(
    inner_argv: Sequence[str],
    *,
    mask_paths: Sequence[Path],
    workspace_path: Path | None = None,
) -> list[str]:
    """Return argv that runs *inner_argv* inside a fresh mount+user+PID+network namespace,
    with every path in *mask_paths* hidden, *workspace_path* (when given) remounted read-only,
    and every capability dropped from the launched process before it ever execs.

    Every *mask_paths* entry is masked with its own ``tmpfs`` mount (mode ``000``, size
    ``0``) -- the directory itself still exists (so the launched process does not fail merely
    for the path being absent), but nothing under it is readable, writable, or even listable.
    *workspace_path*, when given, is self-bind-mounted and then remounted read-only *inside*
    the namespace -- a real mount-level boundary a chmod-0444 file under a writable parent
    directory never actually is (SR2-F6, PR #112 comment 6021757577): the same owning UID can
    always unlink-and-replace a "read-only" file, because that permission check is governed by
    the parent directory, never the file's own mode bits; it cannot, however, write under a
    directory the kernel itself has mounted read-only.

    ``--net`` gives the namespace no network interface at all, not even loopback -- the
    launched process can reach nothing. Immediately before ``exec``, ``setpriv`` drops every
    capability from both the bounding and inheritable sets and sets ``no-new-privs`` -- the one
    step that stops the still-UID-0-inside-its-own-namespace launched process from simply
    unmounting or remounting-writable the very masks and read-only boundary just established
    for it; without this, a process that is "root" inside a namespace it was handed already
    holds ``CAP_SYS_ADMIN`` *there* and could undo any of the above on its own.

    ``mask_paths``/*workspace_path* are a fixed, trusted list/value this module's own caller
    builds (e.g. the orchestrator's own ``HOME``, the prepared inspection workspace) -- never
    content a reviewed PR influences, and the shell fragment below is a static template with
    each path individually ``shlex.quote``-d, never interpolated with untrusted text.
    """

    statements = ["set -e"]
    for path in mask_paths:
        quoted = shlex.quote(str(path))
        statements.append(f"mkdir -p {quoted} 2>/dev/null || true")
        statements.append(f"mount -t tmpfs -o size=0,mode=000 tmpfs {quoted}")
    if workspace_path is not None:
        quoted_workspace = shlex.quote(str(workspace_path))
        statements.append(f"mount --bind {quoted_workspace} {quoted_workspace}")
        statements.append(f"mount -o remount,ro,bind {quoted_workspace}")
    statements.append('exec setpriv --bounding-set=-all --inh-caps=-all --no-new-privs -- "$@"')
    script = "; ".join(statements)
    return [
        "unshare",
        "--user",
        "--map-root-user",
        "--mount",
        "--pid",
        "--net",
        "--fork",
        "--",
        "/bin/sh",
        "-c",
        script,
        "sh",
        *inner_argv,
    ]


#: One bit per property :func:`check_isolation_capability`'s own probe empirically re-confirms
#: (SR2-F6, PR #112 comment 6021757577) -- named so a failure's own *reason* can say exactly
#: which protection could not be confirmed, never just "isolation failed."
_PROBE_FAILURE_BITS: dict[int, str] = {
    1: "the masked sentinel path was still visible to the launched process",
    2: "the read-only-remounted workspace still accepted a write from the launched process",
    4: "the launched process could remount the workspace read-write after capability drop",
    8: "the launched process could still reach an external network address",
}


def check_isolation_capability() -> IsolationCapability:
    """Empirically confirm, with real negative-control probes, that this environment can
    genuinely provide every property :func:`build_isolated_argv` relies on -- run fresh before
    every launch that requires it, never cached or assumed from a prior success.

    SR2-F6 correction (PR #112 comment 6021757577): a probe that confirms only one hidden
    sentinel is not proof the real launch's own protections cannot be undone by the launched
    child itself. This probe launches one real child, wrapped exactly the way a review launch
    would be (masked path, read-only-remounted workspace, isolated network, capabilities
    dropped before exec), and the child itself empirically re-tests all four properties from
    the inside: the masked sentinel must still be invisible; a write into the read-only
    workspace must fail; *remounting* that workspace read-write must fail (proving the
    capability drop, not merely the read-only mount, holds); and an outbound network connection
    must fail. Only a probe that confirms every one of these reports ``available=True``.
    """

    if shutil.which("unshare") is None:
        return IsolationCapability(False, "unavailable", "the unshare executable is not on PATH")
    if shutil.which("setpriv") is None:
        return IsolationCapability(False, "unavailable", "the setpriv executable is not on PATH")
    with tempfile.TemporaryDirectory(prefix="bounded-review-isolation-probe-") as probe_dir:
        probe_path = Path(probe_dir) / "masked"
        probe_path.mkdir()
        sentinel = probe_path / "sentinel.txt"
        sentinel.write_text("SENTINEL", encoding="utf-8")

        workspace_path = Path(probe_dir) / "workspace"
        workspace_path.mkdir()
        workspace_file = workspace_path / "staged.txt"
        workspace_file.write_text("STAGED", encoding="utf-8")

        probe_code = f"""
import os, socket, subprocess, sys
failures = 0
if os.path.exists({str(sentinel)!r}):
    failures |= 1
try:
    with open({str(workspace_file)!r}, "w", encoding="utf-8") as handle:
        handle.write("tampered")
    failures |= 2
except OSError:
    pass
remount = subprocess.run(
    ["mount", "-o", "remount,rw,bind", {str(workspace_path)!r}],
    capture_output=True, check=False,
)
if remount.returncode == 0:
    failures |= 4
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2)
try:
    sock.connect(("8.8.8.8", 53))
    failures |= 8
except OSError:
    pass
finally:
    sock.close()
sys.exit(failures)
"""
        probe_argv = build_isolated_argv(
            [sys.executable, "-c", probe_code],
            mask_paths=[probe_path],
            workspace_path=workspace_path,
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
            failed_properties = [
                description
                for bit, description in _PROBE_FAILURE_BITS.items()
                if completed.returncode & bit
            ]
            return IsolationCapability(
                False,
                "unavailable",
                "isolation probe found: "
                + "; ".join(failed_properties or [f"exit code {completed.returncode}"])
                + f" (stderr: {completed.stderr[:500]!r})",
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


def _path_is_masked(root: Path, mask_paths: Sequence[Path]) -> bool:
    """Whether *root* is itself one of *mask_paths*, or lies under one of them -- resolved
    (symlinks followed where the path already exists) so a mask entry and the root it is meant
    to cover are compared by their real, canonical location, never by two merely
    textually-different spellings of the identical path."""

    resolved_root = root.resolve()
    for masked in mask_paths:
        resolved_masked = masked.resolve()
        if resolved_root == resolved_masked or resolved_root.is_relative_to(resolved_masked):
            return True
    return False


def validate_review_launch_preconditions(
    *,
    max_seconds: int,
    max_output_bytes: int,
    mask_paths: Sequence[Path],
    require_isolation: bool,
    required_mask_roots: Sequence[Path] = (),
) -> str:
    """Raise :class:`~.errors.ReviewAdapterError` for every refusal condition that is
    confirmed to precede any process start -- never one this module cannot be sure about --
    and otherwise return a one-shot *admission token* :func:`spawn_review_process` requires.

    SR2-F4 correction (PR #112 comment 6021757577): a caller that calls this function, and
    then chooses *not* to proceed to :func:`spawn_review_process`, has started no process, and
    may release a ledger reservation as genuinely unsent (see ``scripts/
    bounded_technical_review.py``'s own composed route). This is exactly the ceiling check and
    isolation probe :func:`launch_review_process` already performed inline before F4's own
    correction; splitting them out here lets a caller durably record "an attempt is about to
    be made" only *after* every one of these has already passed -- never before, and never
    only after the fact.

    SR2-F6 correction: *mask_paths* must be non-empty when *require_isolation* is true -- an
    empty mask list was never evidence that anything is actually isolated, only that nothing
    is masked; refusing here is cheaper and more honest than launching under a label with
    nothing behind it.

    SR3-F5 correction (PR #112 comment 6030487245): a non-empty *mask_paths* was never itself
    evidence that anything *sensitive* was actually masked -- the exact reproduced gap: the
    orchestrator's own source checkout, other same-UID files, and ancestor instruction/hook
    paths remained fully readable/writable from inside a launched process regardless of what
    *mask_paths* happened to contain, because this function never checked *mask_paths*
    against anything beyond its own emptiness. *required_mask_roots*, when given, is the
    caller's own declared list of roots that must actually be masked -- the orchestrator's
    source checkout and ``HOME`` (where ancestor instruction/hook files such as
    ``CLAUDE.md``/credential configuration live), in ``scripts/bounded_technical_review.py``'s
    own composed route. A *mask_paths* that omits (or only partially covers) a declared root
    is refused outright, never silently admitted merely for being non-empty. This remains the
    identical real, kernel-enforced tmpfs-mask mechanism :func:`build_isolated_argv` already
    provides -- an *allowlist*-of-explicitly-covered-roots boundary, not a filesystem-wide
    root-remount; the residual risk that anything *not* named in *required_mask_roots* (or
    *mask_paths*) remains reachable is disclosed, not papered over, exactly as this module's
    own F4 correction already discloses for the read-only-workspace mechanism above.

    SR3-F1 correction (PR #112 comment 6030487245): before this correction,
    :func:`spawn_review_process` was a public function anyone could call directly, with no
    precondition check of its own -- a caller (or a future edit) could reach the one real
    external effect through this public surface while skipping this function entirely, never
    exercising any of the checks above. The returned token is minted *only* here, consumed
    (and invalidated) by the one :func:`spawn_review_process` call it authorizes, and checked
    against the small in-process set :data:`_ADMISSION_TOKENS` -- a structural tie between
    "every precondition above already passed" and "a process may now actually be started",
    never a label this module merely documents. This never introduces a new Kernel record or
    second admission route: the token is process-local, ephemeral, and exists only to prevent
    this module's own two functions from being called out of order.
    """

    _require_within_ratified_ceiling(max_seconds=max_seconds, max_output_bytes=max_output_bytes)
    if require_isolation:
        if not mask_paths:
            raise ReviewAdapterError(
                "require_isolation is true but mask_paths is empty -- an empty mask protects "
                "nothing; refusing rather than launching under an isolation label with no "
                "actual masked path behind it"
            )
        uncovered_roots = [
            str(root) for root in required_mask_roots if not _path_is_masked(root, mask_paths)
        ]
        if uncovered_roots:
            raise ReviewAdapterError(
                "require_isolation is true but mask_paths does not cover every required "
                f"root: {uncovered_roots!r} -- a mask list that omits the orchestrator's own "
                "declared sensitive roots (source checkout, HOME) protects nothing there, "
                "regardless of what it does mask elsewhere"
            )
        capability = check_isolation_capability()
        if not capability.available:
            raise ReviewAdapterError(
                "genuine filesystem/network isolation is unavailable in this environment "
                f"({capability.reason}); refusing to launch rather than rely on the "
                "environment-allowlist/chmod-only boundary alone"
            )

    token = secrets.token_hex(32)
    _ADMISSION_TOKENS.add(token)
    return token


#: SR3-F1 correction: the small, process-local, in-memory set of admission tokens
#: :func:`validate_review_launch_preconditions` has issued and :func:`spawn_review_process` has
#: not yet consumed. Never persisted, never a Kernel record -- a one-shot structural tie
#: between the two functions, nothing more.
_ADMISSION_TOKENS: set[str] = set()


def spawn_review_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    admission_token: str,
    mask_paths: Sequence[Path] = (),
    require_isolation: bool = True,
) -> subprocess.Popen[bytes]:
    """Start *argv* as the one new process group this call owns, and return the live
    :class:`subprocess.Popen` immediately -- the one moment this module ever calls ``Popen``.

    SR2-F4 correction (PR #112 comment 6021757577): deliberately separate from
    :func:`collect_review_process_result`'s own potentially long (up to the ratified ceiling)
    blocking wait, so a caller can durably record the real pid and
    :func:`process_identity_token` the instant they exist -- before that wait ever begins,
    never only after it ends.

    SR3-F1 correction (PR #112 comment 6030487245): *admission_token* must be a still-valid
    token :func:`validate_review_launch_preconditions` itself returned -- never a caller-typed
    literal, never reusable (it is consumed, one-shot, the instant this check passes). A
    caller that calls this function directly, without first calling (and *passing*)
    :func:`validate_review_launch_preconditions`, is refused outright
    (:class:`~.errors.ReviewAdapterError`) before anything is started: the public surface can
    no longer bypass the shared precondition gate merely by skipping straight to this call.

    *argv* is passed to :class:`subprocess.Popen` as a literal list -- never through a shell,
    so nothing in a reviewed PR's own content can be interpolated into a second command; when
    isolation is required, :func:`build_isolated_argv` wraps it with *mask_paths* hidden and
    *cwd* itself remounted read-only (SR2-F6) before it is ever launched.
    """

    if admission_token not in _ADMISSION_TOKENS:
        raise ReviewAdapterError(
            "admission_token is not a currently valid token from "
            "validate_review_launch_preconditions -- refusing to spawn a process whose "
            "preconditions were never confirmed (or were already consumed by an earlier spawn)"
        )
    _ADMISSION_TOKENS.discard(admission_token)

    if require_isolation:
        effective_argv = build_isolated_argv(list(argv), mask_paths=mask_paths, workspace_path=cwd)
    else:
        effective_argv = list(argv)

    return subprocess.Popen(  # noqa: S603 -- effective_argv is a literal list, never shell-interpreted
        effective_argv,
        cwd=str(cwd),
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )


def collect_review_process_result(
    process: subprocess.Popen[bytes],
    *,
    max_seconds: int,
    max_output_bytes: int,
    clock: Any,
    started_at: str | None = None,
) -> ReviewLaunchResult:
    """Wait on an *already-started* `process` (:func:`spawn_review_process`'s own return
    value) and return its bounded outcome.

    The whole process group is killed (`os.killpg`) the moment *max_seconds* elapses, not
    merely the direct child, and not merely while its pipes remain open -- the deadline covers
    the process's own full lifetime, including the time after both streams reach EOF but the
    process itself has not yet exited (F3's own reproduced gap). Captured ``stdout``/``stderr``
    share one *combined* budget of *max_output_bytes* (F3: the ratified ceiling is a total,
    never one allowance per stream); bytes beyond it are read and discarded, never buffered, so
    unbounded output from the reviewed subprocess cannot grow this process's own memory without
    bound.

    *clock* is the caller's own trusted-clock callable (``Callable[[], str]``), used only for
    the two timestamps on the returned result -- this function still uses the real monotonic
    clock internally for the deadline itself, since a wall-clock timeout is a real-time
    property no injected logical clock can stand in for. *started_at*, when given, is the
    caller's own clock reading taken immediately after :func:`spawn_review_process` returned
    (more accurate than one taken only now, after this function's own setup); this function
    reads the clock itself only if the caller has none to offer.
    """

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
        started_at=started_at if started_at is not None else ended_at,
        ended_at=ended_at,
    )


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
    required_mask_roots: Sequence[Path] = (),
) -> ReviewLaunchResult:
    """Launch *argv* as the one new process group this call owns, and return its bounded
    outcome -- a thin composition of :func:`validate_review_launch_preconditions`,
    :func:`spawn_review_process`, and :func:`collect_review_process_result` (SR2-F4
    correction, PR #112 comment 6021757577), kept as one call for every direct caller
    (including this delivery's own tests) that has no need for the composed route's own
    finer-grained, durably-recorded staging between those three steps.

    Refuses outright, before any process is started, if *max_seconds*/*max_output_bytes*
    exceed the ratified ceiling (F3), or if *require_isolation* is true (the only mode any
    composed route in this delivery ever uses) and :func:`check_isolation_capability` cannot
    confirm genuine isolation is available right now (F4) -- never silently launching with
    only the weaker environment-allowlist/chmod boundary.
    """

    admission_token = validate_review_launch_preconditions(
        max_seconds=max_seconds,
        max_output_bytes=max_output_bytes,
        mask_paths=mask_paths,
        require_isolation=require_isolation,
        required_mask_roots=required_mask_roots,
    )
    started_at = clock()
    process = spawn_review_process(
        argv,
        cwd=cwd,
        env=env,
        admission_token=admission_token,
        mask_paths=mask_paths,
        require_isolation=require_isolation,
    )
    return collect_review_process_result(
        process,
        max_seconds=max_seconds,
        max_output_bytes=max_output_bytes,
        clock=clock,
        started_at=started_at,
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

    # SR3-F4 correction (PR #112 comment 6030487245): before this correction, the
    # confirmation loop below probed only *pid* -- the process-group leader -- never the
    # group as a whole, even though `os.killpg` above signals every member. A leader that
    # died while a sibling group member (e.g. one that forked just before the signal was
    # delivered) survived the kill was still reported `local_process_group_terminated=True`,
    # honestly confirming only the leader while silently implying the whole group. Fixed:
    # `os.killpg(pgid, 0)` -- a zero-signal existence probe against the *group*, not one pid
    # -- is what this loop now checks; it raises `ProcessLookupError` only once no member of
    # the group remains.
    deadline = time.monotonic() + confirmation_timeout_seconds
    terminated = False
    while time.monotonic() < deadline:
        # If *pid* is this process's own child, a killed leader becomes a zombie until
        # reaped -- and a zombie still counts as a live member of the group for
        # `os.killpg(pgid, 0)`'s own purposes, which would otherwise make a genuinely dead
        # group look alive for the caller's entire confirmation window. Opportunistically
        # reaping the leader here (when we are the parent) closes that gap; `ChildProcessError`
        # (this call's own caller never spawned *pid*, e.g. a controller restart recovering a
        # pid it only recorded) falls back to the group probe alone, this module's only
        # remaining tool in that cross-process case.
        with suppress(ChildProcessError):
            os.waitpid(pid, os.WNOHANG)
        try:
            os.killpg(pgid, 0)
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
#:
#: *inspected_base_sha* (SR2-F3, PR #112 comment 6021757577) is a genuinely separate field from
#: *reviewed_commit_sha*: the latter names the PR *head* the native review was run against, the
#: former names the merge-base/target it actually diffed that head against. Before this
#: correction, :func:`.review_selection.evaluate_native_review_relevance` checked only the head
#: field and never this one at all -- a native review of the exact right head commit, but
#: diffed against a stale or wrong base, was reported relevant with no check ever naming that
#: gap. Nullable for the identical disclosed-unknown reason as *reviewed_commit_sha*.
#: *fetched_via* (SR3-F3, PR #112 comment 6030487245) is a required, non-empty disclosure of
#: how this evidence was actually acquired (e.g. ``"github_mcp_pull_request_read"``) -- never
#: itself cryptographic proof, but an explicit, auditable acquisition claim this module can
#: at least require to be present and non-empty, rather than silently treating a bare caller
#: mapping with no provenance disclosure at all as equivalent to one that names its own
#: source. :func:`fetch_trusted_native_review_evidence` is the one real acquisition seam this
#: module now also offers, for a caller with a genuine transport to hand it.
NATIVE_REVIEW_EVIDENCE_SCHEMA_KEYS: tuple[str, ...] = (
    "schema_version",
    "provider",
    "repository",
    "pull_request",
    "review_id",
    "reviewed_commit_sha",
    "inspected_base_sha",
    "review_state",
    "submitted_at",
    "inspected_paths",
    "findings",
    "fetched_via",
)

#: GitHub's own real numeric review/comment id shape -- digits only. SR3-F3 correction
#: (PR #112 comment 6030487250): before this correction, any non-empty string (including an
#: obviously invented one) satisfied *review_id*; a reproduced invented value is now refused.
_NATIVE_REVIEW_ID_PATTERN = re.compile(r"^[0-9]+$")

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
        "fetched_via",
    ):
        if not isinstance(shaped[key], str) or not shaped[key]:
            raise ReviewAdapterError(f"native review evidence {key!r} must be a non-empty string")
    if shaped["provider"] != NATIVE_REVIEW_PROVIDER:
        raise ReviewAdapterError(
            f"native review evidence names an unsupported provider: {shaped['provider']!r}"
        )
    # SR3-F3 correction (PR #112 comment 6030487245): review_id must be GitHub's own real
    # numeric id shape -- an invented, non-numeric value (reproduced) is refused outright,
    # never accepted as if it were a genuine platform identity.
    if not _NATIVE_REVIEW_ID_PATTERN.match(shaped["review_id"]):
        raise ReviewAdapterError(
            f"native review evidence review_id is not a real numeric GitHub id: "
            f"{shaped['review_id']!r}"
        )
    # SR3-F3 correction: submitted_at must parse as a real timestamp -- an invented, non-
    # parseable value (reproduced: "not-a-time") is refused outright.
    try:
        datetime.fromisoformat(shaped["submitted_at"].replace("Z", "+00:00"))
    except ValueError as error:
        raise ReviewAdapterError(
            f"native review evidence submitted_at is not a real timestamp: "
            f"{shaped['submitted_at']!r}"
        ) from error
    if shaped["reviewed_commit_sha"] is not None and (
        not isinstance(shaped["reviewed_commit_sha"], str) or not shaped["reviewed_commit_sha"]
    ):
        raise ReviewAdapterError(
            "native review evidence reviewed_commit_sha must be a non-empty string or null "
            "(null means genuinely unknown, never a guess at the current head)"
        )
    if shaped["inspected_base_sha"] is not None and (
        not isinstance(shaped["inspected_base_sha"], str) or not shaped["inspected_base_sha"]
    ):
        raise ReviewAdapterError(
            "native review evidence inspected_base_sha must be a non-empty string or null "
            "(null means genuinely unknown, never a guess at the current base -- SR2-F3)"
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


class NativeReviewTransport(Protocol):
    """The one trusted-acquisition seam for native review evidence (SR3-F3 correction, PR
    #112 comment 6030487245): a caller's own already-authenticated GitHub API/MCP client --
    this module never implements one itself, and never makes a network call. Before this
    correction, a bare caller-supplied mapping was treated identically whether it had
    genuinely been fetched through a real client or merely typed by hand; this protocol, and
    :func:`fetch_trusted_native_review_evidence` below, are the one real distinction this
    module now draws between the two, for a caller with a genuine transport to hand it. A
    caller with no transport, only an already-fetched mapping, still has
    :func:`validate_native_review_evidence` directly -- a deliberately generic, directly-
    testable shape check, never itself the canonical "this was genuinely acquired" claim.
    """

    def fetch_native_review(
        self, *, repository: str, pull_request: str, review_id: str
    ) -> Mapping[str, Any]:
        """Return the real, already-fetched native review evidence for exactly this
        (*repository*, *pull_request*, *review_id*) -- never fabricated, never a network call
        this module itself performs."""
        ...


def fetch_trusted_native_review_evidence(
    transport: NativeReviewTransport, *, repository: str, pull_request: str, review_id: str
) -> dict[str, Any]:
    """Return genuinely-acquired, shape-validated native review evidence for exactly
    (*repository*, *pull_request*, *review_id*) -- the one call that actually invokes
    *transport* (a caller's own real client, or, in this delivery's own tests, a controlled
    fake standing in for one) and then independently confirms the evidence it returned
    actually names the identical (*repository*, *pull_request*, *review_id*) this function was
    asked for, before returning it.

    SR3-F3 correction (PR #112 comment 6030487245): a transport that returns evidence for a
    different review than the one requested -- whether through a caller bug or a genuinely
    malicious transport -- is refused outright (:class:`~.errors.ReviewAdapterError`), never
    silently trusted merely because *some* well-shaped evidence came back.
    """

    evidence = transport.fetch_native_review(
        repository=repository, pull_request=pull_request, review_id=review_id
    )
    validated = validate_native_review_evidence(evidence)
    if validated["repository"] != repository:
        raise ReviewAdapterError(
            f"transport returned evidence for repository {validated['repository']!r}, not "
            f"the requested {repository!r}"
        )
    if validated["pull_request"] != pull_request:
        raise ReviewAdapterError(
            f"transport returned evidence for pull_request {validated['pull_request']!r}, "
            f"not the requested {pull_request!r}"
        )
    if validated["review_id"] != review_id:
        raise ReviewAdapterError(
            f"transport returned evidence for review_id {validated['review_id']!r}, not the "
            f"requested {review_id!r}"
        )
    return validated
