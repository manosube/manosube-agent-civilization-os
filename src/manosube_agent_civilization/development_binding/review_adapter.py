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
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Protocol
from urllib.parse import urlparse

from .errors import ReviewAdapterError
from .executor_selection import is_safe_repository_relative_path
from .policy import BOUNDED_REVIEW_NUMERIC_LIMITS

#: SR7-F1 correction (PR #112 comment 6037312445): unlike every other constant/type this
#: module duplicates by value rather than importing (see :data:`_AUTHENTICATION_DECISION_
#: ADMITTED` below), :func:`require_authenticated_review_launch_admission` must call the real
#: owners themselves -- a caller-supplied decision, however correctly shaped, is never itself
#: evidence that either real owner actually ran. Neither import below is circular:
#: :mod:`.review_selection`/:mod:`.review_control` import :mod:`.errors`/:mod:`.
#: executor_selection`/:mod:`.policy` only, never this module.
from .review_control import (
    STATUS_ACK_UNKNOWN,
    STATUS_CLAIMED,
    STATUS_DISPATCHED,
    read_claim,
)
from .review_selection import authenticate_bounded_review_grant

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
    BOUNDED_REVIEW_NUMERIC_LIMITS`) is now enforced *here* -- never only as a
    caller-suppliable, caller-widenable parameter checked against the bundle only after it was
    already fully staged. A running total that would exceed the ceiling is refused
    immediately, and the partial workspace is removed before this function raises; nothing
    oversized is ever left staged, even transiently.

    SR4-F2 correction (PR #112 comment 6032479337): before this correction, the ceiling was
    enforced against ``source.stat().st_size`` -- read *before* ``shutil.copyfile`` ever
    opened the file -- and ``shutil.copyfile`` itself then read and wrote the file's *actual*,
    current bytes with no bound of its own. A source file that grows between that ``stat()``
    and the real copy (reproduced: a controlled fixture growing its own file in exactly that
    window) staged more bytes than the ceiling had ever actually permitted; ``stat()`` was
    checked, but never what was genuinely read. Fixed: this function no longer calls
    ``shutil.copyfile`` or trusts ``stat()`` for anything but an initial, non-authoritative
    hint -- it reads *and counts* the real bytes copied in bounded chunks, refusing the
    instant the running total of genuinely-read bytes would exceed the ceiling, regardless of
    what size the file reported, or grew to, beforehand.
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
            destination = workspace / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            # SR4-F2 correction: the ceiling is enforced against the real bytes this loop
            # itself reads and writes, one bounded chunk at a time -- never against a
            # pre-read stat() size that a source file could have already outgrown by the
            # time it is actually opened and copied.
            with source.open("rb") as source_handle, destination.open("wb") as dest_handle:
                while True:
                    chunk = source_handle.read(65536)
                    if not chunk:
                        break
                    staged_bytes += len(chunk)
                    if staged_bytes > max_input_bytes:
                        raise ReviewAdapterError(
                            "staged inspection input exceeds the ratified max_input_bytes "
                            f"ceiling ({staged_bytes} > {max_input_bytes}) at {relative!r} -- "
                            "refusing the real bytes read, not merely a pre-copy size hint"
                        )
                    dest_handle.write(chunk)
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


def default_sensitive_mask_roots() -> list[Path]:
    """Return the fixed set of same-UID temp/runtime filesystem roots :func:`build_isolated_argv`
    always gives a fresh, empty mount of their own -- independent of whatever a caller
    separately declares.

    SR5-F5 correction (PR #112 comment 6034603745): before this correction,
    :func:`build_isolated_argv` only ever masked *mask_paths* and remounted *workspace_path*
    read-only -- the rest of the inherited host filesystem, including every one of these
    roots, remained fully readable/writable from inside a launched process, exactly as before
    any masking at all. The independent review's own named example: "same-UID files elsewhere
    in /tmp or /var/tmp" -- neither path was ever a caller-declared ``required_mask_root`` (the
    composed route's own ``[source_root, Path.home()]`` never named either one), so SR4-F5's
    own "``required_mask_roots`` may never be empty" fix never closed this: an empty-root
    bypass and an *incomplete* allowlist are two different gaps, and this one is the second.
    Fixed: these roots are enumerated here, once, by this module itself, and are *always* in
    scope for :func:`build_isolated_argv` -- never dependent on any caller's own declaration.

    This set deliberately excludes the platform temp directory itself
    (:func:`tempfile.gettempdir`, ``/tmp`` on every environment this delivery targets):
    *workspace_path* -- the one directory this delivery's own staged inspection input, and this
    delivery's own test fixtures' controlled fake executables, actually live under -- is itself
    always created there (:func:`prepare_inspection_workspace`), so an unconditional fresh mount
    directly over it would hide the one directory a review launch actually needs to read, not
    merely the unrelated same-UID content beside it; closing that half of the reproduction
    correctly requires the launch's own legitimately-needed paths (workspace, prompt, executable)
    to first be consolidated under one caller-declared, explicitly preserved root. ``/var/tmp``
    and ``XDG_RUNTIME_DIR`` have no such conflict -- nothing in this delivery's own code or tests
    ever places anything needed by a launch under either of them -- so both are closed
    unconditionally, in full, by this correction.

    SR6-F4 correction (PR #112 comment 6036263982): the paragraph above, unchanged since SR5-F5,
    was itself named as the remaining gap: "tracked as further, not-yet-delivered work" left the
    platform temp directory's other same-UID content permanently reachable from inside a real
    local launch, and a successful ``/var/tmp`` sentinel proof was never itself proof of a
    *complete* boundary. This module still does not perform that consolidation -- *workspace*,
    *prompt_path*, and *codex_executable* are not one caller-declared preserved root here or
    anywhere in this module. Instead, ``scripts/bounded_technical_review.py``'s own
    ``compose_bounded_technical_review_dispatch`` -- the one real composed route that could ever
    reach a genuine local launch referencing all three -- now refuses that launch outright,
    before send (``"local-dispatch-boundary"``/``"INCOMPLETE_FILESYSTEM_BOUNDARY"``), whenever it
    would need to; an operator who needs a review performed today uses the already-delivered
    ``REUSE_NATIVE_ONLY`` native-reuse path instead. This function's own exclusion of the
    platform temp directory is therefore still real and still disclosed, never silently treated
    as solved -- what has changed is that the one caller who could have launched into that gap
    no longer can.

    Each root gets a *fresh, empty, writable* tmpfs (unlike *mask_paths*'s own mode-``000``,
    fully inaccessible mount) -- a launched process may still use its own scratch space exactly
    as it would expect to find at these conventional locations; what it can never do is see or
    touch anything that existed there before the launch. :func:`check_isolation_capability`'s
    own probe empirically re-confirms this mechanism actually works in the current environment
    before every isolated launch, exactly as it already does for *mask_paths*/*workspace_path*
    -- an environment where it cannot be confirmed refuses the launch outright (the identical
    existing ``capability.available`` check in :func:`validate_review_launch_preconditions`),
    never silently proceeding under a weaker, merely-disclosed boundary.
    """

    roots = {Path("/var/tmp")}  # noqa: S108 -- this is the deliberate baseline root itself, not an insecure scratch-file race
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        roots.add(Path(runtime_dir))
    return sorted(roots, key=str)


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

    SR5-F5 correction (PR #112 comment 6034603745): every root :func:`default_sensitive_mask_
    roots` names also gets a fresh, empty tmpfs of its own -- unconditionally, regardless of
    whether a caller's own *mask_paths* ever named it -- see that function's own docstring for
    the exact reproduced gap this closes. A root already covered by *mask_paths* (fully
    hidden, mode ``000``) is never double-mounted here. These baseline mounts are built *last*,
    after *workspace_path*'s own bind-mount: *workspace_path* is, in this delivery's own
    production use, itself a fresh directory under one of these same baseline roots (the
    prepared inspection workspace lives under the platform temp directory) -- mounting it first
    establishes it as its own distinct mount, which a later, broader mount over its parent
    directory never retroactively hides (the identical nested-mount behavior that already lets
    ``/proc``/``/sys`` remain visible under a remounted ``/``); reversing this order would hide
    the one directory a review launch actually needs to read.
    """

    statements = ["set -e"]
    if workspace_path is not None:
        quoted_workspace = shlex.quote(str(workspace_path))
        statements.append(f"mount --bind {quoted_workspace} {quoted_workspace}")
        statements.append(f"mount -o remount,ro,bind {quoted_workspace}")
    for path in mask_paths:
        quoted = shlex.quote(str(path))
        statements.append(f"mkdir -p {quoted} 2>/dev/null || true")
        statements.append(f"mount -t tmpfs -o size=0,mode=000 tmpfs {quoted}")
    for path in default_sensitive_mask_roots():
        if _path_is_masked(path, mask_paths):
            continue
        quoted = shlex.quote(str(path))
        statements.append(f"mkdir -p {quoted} 2>/dev/null || true")
        statements.append(f"mount -t tmpfs -o size=64m,mode=1777 tmpfs {quoted}")
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
    # SR5-F5 correction (PR #112 comment 6034603745).
    16: "a pre-existing same-UID file under /var/tmp was still visible to the launched process",
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
    must fail.

    SR5-F5 correction (PR #112 comment 6034603745): a fifth property is now also re-tested
    from inside the same real child: a sentinel this probe plants directly under ``/var/tmp``
    -- a location no caller ever explicitly declares as a mask -- must also be invisible,
    confirming :func:`default_sensitive_mask_roots`'s own baseline mounts (built into
    :func:`build_isolated_argv` unconditionally) genuinely work in this environment, exactly as
    already required for the caller-declared mask above. Only a probe that confirms every one
    of these five properties reports ``available=True``; an environment where this fifth
    property cannot be confirmed refuses the launch outright through the identical existing
    ``capability.available`` check, never silently falling back to the weaker, merely-disclosed
    boundary this correction replaces.
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

        try:
            with tempfile.NamedTemporaryFile(
                dir="/var/tmp",
                prefix="bounded-review-baseline-root-probe-",
                suffix=".txt",
                delete=False,
            ) as baseline_sentinel_handle:
                baseline_sentinel_handle.write(b"BASELINE-SENTINEL")
                baseline_sentinel = Path(baseline_sentinel_handle.name)
        except OSError as error:
            return IsolationCapability(
                False, "unavailable", f"could not plant the baseline-root probe sentinel: {error}"
            )
        try:
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
if os.path.exists({str(baseline_sentinel)!r}):
    failures |= 16
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
        finally:
            with suppress(OSError):
                baseline_sentinel.unlink()
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


#: SR6-F1 correction (PR #112 comment 6036263982): the two real upstream Decision shapes this
#: function now requires -- duplicated here by *value* (never by import of :mod:`.
#: review_selection`/:mod:`.review_control`, exactly the existing precedent
#: :data:`NATIVE_REVIEW_PROVIDER` already sets for this module) so this module's own import
#: surface stays exactly what it always was.
_AUTHENTICATION_DECISION_ADMITTED = "REVIEW_SELECTION_ADMITTED"
_CLAIM_DECISION_ADMITTED = "REVIEW_CLAIM_ADMITTED"

#: SR8-F1 correction (PR #112 comment 6050757530): the one reason every direct/token/launch/
#: spawn entrance to a real local review process launch now refuses with, unconditionally,
#: regardless of any parameter supplied -- including a fully genuine authenticated grant and a
#: fully genuine durable claim. See :func:`validate_review_launch_preconditions`'s own
#: docstring for why this delivery accepts local launch remaining unavailable rather than
#: closing the residual surface any other way.
LOCAL_PRODUCTION_LAUNCH_UNAVAILABLE_REASON = "LOCAL_PRODUCTION_LAUNCH_UNAVAILABLE"


def validate_review_launch_preconditions(
    *,
    argv: Sequence[str],
    cwd: Path,
    max_seconds: int,
    max_output_bytes: int,
    mask_paths: Sequence[Path],
    require_isolation: bool,
    authentication_decision: Mapping[str, Any],
    claim_decision: Mapping[str, Any],
    required_mask_roots: Sequence[Path] = (),
) -> str:
    """SR8-F1 correction (PR #112 comment 6050757530): refuses unconditionally, as the very
    first statement, regardless of every parameter given -- including a genuinely admitted
    *authentication_decision*/*claim_decision* pair. This used to be the generic ceiling/
    mask-coverage/isolation-capability precondition primitive every real launch, and this
    module's own tests, passed through; the independent review found that primitive still
    directly, publicly callable with a hand-typed admitted decision pair, with no Authority/
    Store/ledger operation behind it, reaching a genuine subprocess launch -- the exact SR6-F1/
    SR7-F1 reproduction, merely bypassing the new SR7-F1 gate rather than passing through it.

    Fixed: a real local review process launch is not an available capability of this
    delivery, through this function or any other. See :func:`require_authenticated_review_
    launch_admission`'s own docstring for the full SR8-F1/SR9-F1 history.

    SR9-F1 correction (PR #112 comment 6053084718): the SR8-F1 fix above preserved this
    function's former mechanics body -- ceiling/mask-coverage/isolation-capability checks and
    admission-token minting -- as :func:`mint_review_launch_admission_for_controlled_
    mechanics_test`, still defined in this module, still shipped in the installed wheel. The
    independent review reproduced the exact SR6-F1/SR7-F1 counterexample against that renamed
    function directly: "the same installed arbitrary-argv effect has only been renamed to a
    test fixture... Calling it a fixture does not remove the shipped effect." Fixed: that
    function, and its spawn/launch counterparts, are removed from this module entirely --
    the identical ceiling/mask-coverage/isolation-capability mechanics are now defined only as
    test-local helpers inside ``tests/integration/binding/test_bounded_technical_review_
    route.py``, never imported from, or shipped in, this package.
    """

    raise ReviewAdapterError(
        f"{LOCAL_PRODUCTION_LAUNCH_UNAVAILABLE_REASON}: local review process launch is not an "
        "available capability of this delivery -- use the native GitHub review reuse route "
        "(compose_bounded_technical_review_native_reuse_dispatch) instead"
    )


def require_authenticated_review_launch_admission(
    *,
    argv: Sequence[str],
    cwd: Path,
    max_seconds: int,
    max_output_bytes: int,
    mask_paths: Sequence[Path],
    require_isolation: bool,
    store: Any,
    project_id: str,
    project_binding_id: str,
    requirement_id: str,
    selection_id: str,
    verifier_identity: Mapping[str, Any],
    permitted_boundary: Mapping[str, Any],
    verifier_selection_grant_refs: Sequence[Mapping[str, Any]],
    human_grant_declaration_refs: Sequence[Mapping[str, Any]],
    ledger_path: Path,
    identity_key: str,
    repository: str,
    required_mask_roots: Sequence[Path] = (),
) -> str:
    """SR7-F1 correction (PR #112 comment 6037312445): the one genuine admission gate a real
    local launch must pass through -- never reachable merely by hand-typing two decision
    dicts, the exact reproduction :func:`validate_review_launch_preconditions`'s own
    *authentication_decision*/*claim_decision* parameters (SR6-F1) left open. SR6-F1 raised the
    bar from "zero context required" to "two caller-constructed dicts required"; this round's
    own independent review reproduced that bar being no bar at all:
    ``authentication_decision={"decision": "REVIEW_SELECTION_ADMITTED"}``,
    ``claim_decision={"decision": "REVIEW_CLAIM_ADMITTED"}``, with no Authority/Store/ledger
    operation ever performed, still minted a token and launched a genuine harmless subprocess.
    The independent review's own words: "an internally owned admitted operation must depend
    on the existing real checks/claim, or the production effect must refuse... requiring dict
    parameters does not establish that distinction."

    Fixed (SR7-F1): this function calls :func:`authenticate_bounded_review_grant` itself,
    fresh, with the caller's own real *store*/*project_id*/*project_binding_id*/
    *requirement_id*/*selection_id*/*verifier_identity*/*permitted_boundary*/
    *verifier_selection_grant_refs*/*human_grant_declaration_refs* -- the identical genuine
    Boot/Authority/Store authentication that function always performs, never re-derived or
    duplicated here -- and independently re-reads the real, durable ledger at *ledger_path*
    for *identity_key* to confirm a claim genuinely exists there and has not yet been
    terminally resolved, rather than trusting a caller-supplied assertion that one does. A
    caller cannot satisfy either check without having actually caused the real owner to
    produce it.

    SR8-F1 correction (PR #112 comment 6050757530): SR7-F1's own fix left
    :func:`validate_review_launch_preconditions`/:func:`spawn_review_process`/
    :func:`launch_review_process` "unchanged below... layered *in front of* them" --
    completely unchanged and still directly callable with the exact SR6-F1/SR7-F1
    reproduction (a hand-typed admitted decision pair, zero Authority/Store/ledger
    operation), still reaching a genuine harmless subprocess through that alternate surface.
    The independent review rejected the "disclosed residual, generic test primitive, never
    the admission gate" framing outright: "Merely calling the genuine helper from one
    composed route does not remove the alternate token-issuance/launch surface the handoff
    explicitly required testing... production effect must only consume genuine admitted
    operations or remain unavailable... Do not preserve arbitrary-argv production
    reachability just to preserve old positive tests."

    Fixed (SR8-F1): past the two genuine checks above -- which still run, and still
    distinguish "no real grant" from "no real claim" for anyone who calls this function --
    a real local launch remains unavailable, period: this function now raises
    :data:`LOCAL_PRODUCTION_LAUNCH_UNAVAILABLE_REASON` unconditionally rather than minting an
    admission token, and :func:`validate_review_launch_preconditions`/
    :func:`spawn_review_process`/:func:`launch_review_process` do likewise, each
    independently, as the very first statement of its own body, regardless of what it is
    given -- including a fully genuine authenticated grant and a fully genuine durable claim.
    There is no caller-settable flag, alternate helper, or "generic primitive" distinction
    that restores a real local launch anywhere in this module's public surface. This is an
    accepted correction outcome, not a regression: native GitHub review reuse
    (:func:`validate_native_review_evidence`, :func:`compose_bounded_technical_review_native_
    reuse_dispatch`) remains this delivery's primary, fully-available review path; local
    process launch is simply not a supported capability of this delivery, by design, with
    nothing this module exposes able to lift that.

    SR9-F1 correction (PR #112 comment 6053084718), superseding the claim two sentences above:
    "the former mechanics bodies of those three functions are preserved only as explicitly-
    named, controlled test fixtures" was itself the next gap -- those fixtures
    (``mint_review_launch_admission_for_controlled_mechanics_test``, ``spawn_review_process_
    for_controlled_mechanics_test``, ``launch_review_process_for_controlled_mechanics_test``)
    remained defined in this installed module, reachable with the identical hand-typed-
    decision-pair reproduction under their new names, with no restriction on the supplied
    argv: "Re-ran exact current functions with the original same argv/cwd/config and two
    invented admitted dictionaries... the newly named mint/spawn pair starts a real harmless
    child... This requires no mutation/monkeypatch of admission or effect functions, just
    their new public names." Fixed: those three functions are removed from this module
    entirely, not merely renamed again -- the identical mechanics they implemented now exist
    only as test-local helpers defined directly inside ``tests/integration/binding/
    test_bounded_technical_review_route.py``, never imported from this package, never shipped
    in the installed wheel. A caller of this module -- including a future one -- has no
    function, flag, or import path that ever mints a token or starts a process for any argv,
    genuine authority or not.
    """

    authentication_decision = authenticate_bounded_review_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        requirement_id=requirement_id,
        selection_id=selection_id,
        verifier_identity=verifier_identity,
        permitted_boundary=permitted_boundary,
        verifier_selection_grant_refs=verifier_selection_grant_refs,
        human_grant_declaration_refs=human_grant_declaration_refs,
    )
    if authentication_decision.get("decision") != _AUTHENTICATION_DECISION_ADMITTED:
        raise ReviewAdapterError(
            "authenticate_bounded_review_grant did not report REVIEW_SELECTION_ADMITTED for "
            f"this exact scope -- refusing local launch admission: {authentication_decision!r}"
        )

    claim = read_claim(ledger_path, identity_key, repository=repository)
    if claim is None or claim.get("status") not in (
        STATUS_CLAIMED,
        STATUS_DISPATCHED,
        STATUS_ACK_UNKNOWN,
    ):
        raise ReviewAdapterError(
            "no genuinely claimed, not-yet-terminally-resolved ledger record exists for "
            f"identity_key {identity_key!r} in repository {repository!r} -- refusing local "
            f"launch admission without a real, durable claim: {claim!r}"
        )
    del claim  # SR8-F1: a genuine claim was confirmed to exist; local launch still refuses.

    # SR8-F1 correction (PR #112 comment 6050757530): both checks above are genuine and have
    # now passed -- a real authenticated grant and a real, not-yet-terminally-resolved claim
    # both exist. Local launch still refuses here, unconditionally, exactly as every other
    # entrance to it does below: this function was never the thing standing between "genuine
    # authority" and "a real subprocess actually starts" -- that capability itself is what is
    # unavailable in this delivery, for every caller, regardless of how genuine its authority
    # is.
    raise ReviewAdapterError(
        f"{LOCAL_PRODUCTION_LAUNCH_UNAVAILABLE_REASON}: a real local review process launch is "
        "not an available capability of this delivery, even for a fully genuine authenticated "
        "grant and a fully genuine durable claim -- use the native GitHub review reuse route "
        "(compose_bounded_technical_review_native_reuse_dispatch) instead"
    )


def spawn_review_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    admission_token: str,
    mask_paths: Sequence[Path] = (),
    require_isolation: bool = True,
) -> subprocess.Popen[bytes]:
    """SR8-F1 correction (PR #112 comment 6050757530): refuses unconditionally, as the very
    first statement, with zero subprocess effects -- regardless of *admission_token*. This
    used to be the one real ``Popen`` call site any admitted caller could reach. See
    :func:`require_authenticated_review_launch_admission`'s own docstring for the full
    SR8-F1/SR9-F1 history: the former mechanics body of this function no longer exists in
    this module at all, under any name -- it is a test-local helper inside
    ``tests/integration/binding/test_bounded_technical_review_route.py`` instead.
    """

    raise ReviewAdapterError(
        f"{LOCAL_PRODUCTION_LAUNCH_UNAVAILABLE_REASON}: local review process launch is not an "
        "available capability of this delivery -- use the native GitHub review reuse route "
        "(compose_bounded_technical_review_native_reuse_dispatch) instead"
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
    authentication_decision: Mapping[str, Any],
    claim_decision: Mapping[str, Any],
    mask_paths: Sequence[Path] = (),
    require_isolation: bool = True,
    required_mask_roots: Sequence[Path] = (),
) -> ReviewLaunchResult:
    """SR8-F1 correction (PR #112 comment 6050757530): refuses unconditionally, as the very
    first statement, with zero subprocess effects -- regardless of every parameter given,
    including a genuinely admitted *authentication_decision*/*claim_decision* pair. See
    :func:`require_authenticated_review_launch_admission`'s own docstring for the full
    SR8-F1/SR9-F1 history: the former mechanics body of this function no longer exists in
    this module at all, under any name -- it is a test-local helper inside
    ``tests/integration/binding/test_bounded_technical_review_route.py`` instead.
    ``scripts/bounded_technical_review.py``'s own composed route never called this function
    at all -- it calls :func:`require_authenticated_review_launch_admission` and
    :func:`spawn_review_process` directly, both of which likewise now refuse unconditionally.
    """

    raise ReviewAdapterError(
        f"{LOCAL_PRODUCTION_LAUNCH_UNAVAILABLE_REASON}: local review process launch is not an "
        "available capability of this delivery -- use the native GitHub review reuse route "
        "(compose_bounded_technical_review_native_reuse_dispatch) instead"
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
#: SR5-F3 correction (PR #112 comment 6034603745): *source_url*, *author*, and *fetched_at*
#: are new required fields. Before this correction, the only provenance check this module
#: performed was the bare non-empty *fetched_via* disclosure string (SR3-F3) -- a reproduced
#: fake transport could hand back matching repository/pull_request/review_id/base/head with
#: ``fetched_via="I_TYPED_THIS"`` and still reach ``VERIFIED``, because nothing here ever
#: checked *where* the review evidence actually came from (a real URL on the real platform
#: naming this exact PR) or *when this acquisition itself happened* (as distinct from
#: *submitted_at*, the review's own, possibly long-past, submission time -- never itself
#: grounds for refusal). *source_url* is cross-checked by :func:`fetch_trusted_native_review_
#: evidence` below against the requested (*repository*, *pull_request*); *fetched_at*'s
#: freshness is checked by the composed route (``compose_bounded_technical_review_native_
#: reuse_dispatch``), which already receives a real ``now``, following the identical shape-
#: here/freshness-there division ``fetch_trusted_live_review_state``/``_recheck_live_
#: authorization`` already draw for *observed_at* (SR5-F1).
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
    "source_url",
    "author",
    "fetched_at",
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
        "source_url",
        "author",
        "fetched_at",
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
    # SR5-F3 correction (PR #112 comment 6034603745): fetched_at -- this acquisition's own
    # time, never to be confused with submitted_at (the review's own, possibly long-past,
    # submission time) -- must likewise parse as a real timestamp. Its *freshness* relative
    # to now is a caller concern (the composed native route has a real now; this module does
    # not), identical to the shape-here/freshness-there split observed_at already draws.
    try:
        datetime.fromisoformat(shaped["fetched_at"].replace("Z", "+00:00"))
    except ValueError as error:
        raise ReviewAdapterError(
            f"native review evidence fetched_at is not a real timestamp: {shaped['fetched_at']!r}"
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


#: SR6-F2 correction (PR #112 comment 6036263982): the one origin this module ever trusts a
#: native review's own ``source_url`` to be hosted at -- a real parsed-URL check, never a
#: substring. Duplicated here by value for the identical reason :data:`NATIVE_REVIEW_PROVIDER`
#: already is: this module imports no second-party HTTP/URL-policy owner.
_PERMITTED_NATIVE_REVIEW_ORIGIN = "github.com"


def _require_genuine_native_review_source_url(
    source_url: str, *, repository: str, pull_request: str
) -> None:
    """Raise :class:`~.errors.ReviewAdapterError` unless *source_url* genuinely, exactly names
    (*repository*, *pull_request*) on the one permitted origin.

    SR6-F2 correction (PR #112 comment 6036263982): before this correction, this check was a
    bare substring test (``f"/{repository}/pull/{pull_request...}" in source_url``) -- it never
    checked the URL's own scheme or host at all, and a pull-request *number* match was itself
    only a substring, not an exact path segment. Reproduced: a transport returning
    ``https://example.invalid/{repository}/pull/{pull_request}999`` -- a different origin
    entirely, and a PR number that merely *begins with* the one requested -- still satisfied
    the old check. Fixed: this function now genuinely parses *source_url* (:func:`urllib.
    parse.urlparse`) and requires ``scheme == "https"``, ``netloc == "github.com"`` exactly,
    and the URL path's own first four segments to be exactly
    (*owner*, *repo*, ``"pull"``, *pull_request_number*) -- never a prefix, never a substring,
    and never any other origin, however the rest of the path continues (a real PR URL's own
    comment/review anchor fragment, e.g. ``#pullrequestreview-...``, is never required to
    match anything here). This is still a parsed-URL cross-check, never cryptographic proof
    the URL is genuine or reachable -- it closes the exact SR6-F2 reproduction, not every
    conceivable forgery of a URL this module can never actually fetch.
    """

    parsed = urlparse(source_url)
    if parsed.scheme != "https" or parsed.netloc != _PERMITTED_NATIVE_REVIEW_ORIGIN:
        raise ReviewAdapterError(
            f"native review evidence source_url {source_url!r} is not on the one permitted "
            f"origin (https://{_PERMITTED_NATIVE_REVIEW_ORIGIN}/...)"
        )
    segments = [segment for segment in parsed.path.split("/") if segment]
    expected_segments = [*repository.split("/"), "pull", pull_request.lstrip("#")]
    if segments[: len(expected_segments)] != expected_segments:
        raise ReviewAdapterError(
            f"native review evidence source_url {source_url!r} does not exactly name "
            f"{repository!r} pull request {pull_request!r} (path segments "
            f"{segments[: len(expected_segments)]!r} != {expected_segments!r})"
        )


def fetch_trusted_native_review_evidence(
    transport: NativeReviewTransport,
    *,
    repository: str,
    pull_request: str,
    review_id: str,
    expected_author: str,
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

    SR5-F3 correction (PR #112 comment 6034603745): a well-shaped, correctly-identified
    ``source_url`` is now also cross-checked against the requested (*repository*,
    *pull_request*).

    SR6-F2 correction (PR #112 comment 6036263982): that SR5-F3 cross-check was itself only a
    substring test, with no check of the URL's own origin at all -- see
    :func:`_require_genuine_native_review_source_url`'s own docstring for the exact
    reproduction this now closes. Separately, ``author`` was previously required only to be a
    non-empty string by :func:`validate_native_review_evidence` -- any value at all, including
    an unrelated account's own real login, satisfied it (reproduced: ``author="unrelated-
    user"`` reached ``VERIFIED``). Fixed: *expected_author* is now required -- the caller's own
    already-known expectation for exactly who should have authored this scope's native review
    (in this delivery's one real caller, the Bounded Review Grant's own ``inspector_session_
    ref`` -- the identical field the local dispatch route's own ``verifier_identity`` already
    uses) -- and this function refuses outright unless ``author`` exactly matches it. Missing,
    unknown, or merely non-empty provenance can no longer reach ``VERIFIED``.
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
    _require_genuine_native_review_source_url(
        validated["source_url"], repository=repository, pull_request=pull_request
    )
    if validated["author"] != expected_author:
        raise ReviewAdapterError(
            f"native review evidence author {validated['author']!r} does not match the "
            f"expected reviewer provenance {expected_author!r}"
        )
    return validated


#: The required keys :func:`fetch_trusted_live_review_state` requires its *transport* to
#: return -- SR4-F1 correction (PR #112 comment 6032479337).
#: SR5-F1 correction (PR #112 comment 6034603745): the two PR-readiness fields and the
#: freshness timestamp a live review-state observation must now carry -- see
#: :data:`_LIVE_REVIEW_STATE_KEYS` and :func:`fetch_trusted_live_review_state`'s own docstring.
LIVE_PR_STATE_OPEN = "open"
LIVE_PR_STATE_CLOSED = "closed"
_LIVE_PR_STATES: frozenset[str] = frozenset({LIVE_PR_STATE_OPEN, LIVE_PR_STATE_CLOSED})

_LIVE_REVIEW_STATE_KEYS: tuple[str, ...] = (
    "repository",
    "pull_request",
    "current_base_sha",
    "current_head_sha",
    "kill_switch_engaged",
    "pr_state",
    "pr_draft",
    "observed_at",
)


class LiveReviewStateTransport(Protocol):
    """The one trusted-acquisition seam for *live* review-selection state (SR4-F1 correction,
    PR #112 comment 6032479337): a caller's own already-authenticated GitHub API/MCP client
    (or local kill-switch reader) -- this module never implements one itself, and never makes
    a network call.

    Before this correction, the live re-check performed by ``scripts/bounded_technical_
    review.py``'s own ``_recheck_live_authorization`` evaluated ``evaluate_review_selection``
    against the grant's *own*, caller-written ``current_repository``/``current_pull_request``/
    ``current_base_sha``/``current_head_sha`` fields -- values nothing ever actually refreshed
    from anywhere live, so a "fresh" re-check against them could never distinguish a genuinely
    still-current PR from one that had moved on. A caller with a real transport now gets a
    genuinely fresh observation at the exact moment the composed route re-checks it; a caller
    with no transport at all cannot reach the composed route (it is a required parameter, not
    an optional one with a silently-stale default) -- this module's own "safe refusal when a
    trusted live input cannot be obtained" requirement, enforced structurally rather than left
    to a caller's own discipline.
    """

    def fetch_live_review_state(self, *, repository: str, pull_request: str) -> Mapping[str, Any]:
        """Return the real, freshly-observed live state for exactly (*repository*,
        *pull_request*) -- its current base/head sha, whether an operator kill switch is
        currently engaged, whether the PR itself is still open and ready for review
        (``pr_state``/``pr_draft``, SR5-F1 correction), and the real wall-clock instant this
        observation was taken (``observed_at``) -- never fabricated, never a network call this
        module itself makes.
        """
        ...


def fetch_trusted_live_review_state(
    transport: LiveReviewStateTransport, *, repository: str, pull_request: str
) -> dict[str, Any]:
    """Return genuinely-acquired, shape-validated live review state for exactly
    (*repository*, *pull_request*) -- the one call that actually invokes *transport* (a
    caller's own real client, or, in this delivery's own tests, a controlled fake standing in
    for one) and then independently confirms the state it returned actually names the
    identical (*repository*, *pull_request*) this function was asked for, before returning it.

    SR4-F1 correction (PR #112 comment 6032479337): a transport that returns state for a
    different repository/pull request than the one requested -- whether through a caller bug
    or a genuinely malicious transport -- is refused outright (:class:`~.errors.
    ReviewAdapterError`), never silently trusted merely because *some* well-shaped state came
    back; a transport that raises, times out, or returns a malformed mapping is likewise never
    treated as "nothing to report" -- the exception propagates, and the composed route's own
    caller is the one responsible for turning an unobtainable live read into a safe refusal
    (never a silent proceed).

    SR5-F1 correction (PR #112 comment 6034603745): before this correction, the required shape
    carried only ``current_base_sha``/``current_head_sha``/``kill_switch_engaged`` -- nothing
    about whether the PR itself was still genuinely open and ready, or when the observation
    was actually taken. Reproduced gap: matching shas with the live PR already ``draft=True``
    or ``state="closed"``, or an ``observed_at`` from 1900, passed this shape check and reached
    the selection re-check unrefused -- an identical sha was never itself proof the PR was
    still a live, reviewable target at the instant of this call. Fixed: ``pr_state`` (must be
    exactly ``"open"`` or ``"closed"``) and ``pr_draft`` (a real bool) are now required, and
    ``observed_at`` must parse as a real timestamp -- this function validates only the *shape*
    of these three; :func:`~manosube_agent_civilization.development_binding.review_selection.
    evaluate_review_selection`'s own caller (``scripts/bounded_technical_review.py``'s own
    ``_recheck_live_authorization``) is where ``pr_draft``/``pr_state`` are actually checked
    for readiness and ``observed_at`` for freshness, against a real clock, at the instant of
    the call -- never here, where there is no ``now`` to check it against.
    """

    state = transport.fetch_live_review_state(repository=repository, pull_request=pull_request)
    if not isinstance(state, Mapping):
        raise ReviewAdapterError(f"live review state is not an object: {type(state)!r}")
    shaped = dict(state)
    missing = set(_LIVE_REVIEW_STATE_KEYS) - set(shaped)
    if missing:
        raise ReviewAdapterError(f"live review state omits required keys: {sorted(missing)}")
    if shaped["repository"] != repository:
        raise ReviewAdapterError(
            f"transport returned live state for repository {shaped['repository']!r}, not "
            f"the requested {repository!r}"
        )
    if shaped["pull_request"] != pull_request:
        raise ReviewAdapterError(
            f"transport returned live state for pull_request {shaped['pull_request']!r}, "
            f"not the requested {pull_request!r}"
        )
    if not isinstance(shaped["current_base_sha"], str) or not shaped["current_base_sha"]:
        raise ReviewAdapterError("live review state current_base_sha must be a non-empty string")
    if not isinstance(shaped["current_head_sha"], str) or not shaped["current_head_sha"]:
        raise ReviewAdapterError("live review state current_head_sha must be a non-empty string")
    if not isinstance(shaped["kill_switch_engaged"], bool):
        raise ReviewAdapterError("live review state kill_switch_engaged must be a real bool")
    if shaped["pr_state"] not in _LIVE_PR_STATES:
        raise ReviewAdapterError(
            f"live review state pr_state must be one of {sorted(_LIVE_PR_STATES)}, not "
            f"{shaped['pr_state']!r}"
        )
    if not isinstance(shaped["pr_draft"], bool):
        raise ReviewAdapterError("live review state pr_draft must be a real bool")
    if not isinstance(shaped["observed_at"], str) or not shaped["observed_at"]:
        raise ReviewAdapterError("live review state observed_at must be a non-empty string")
    try:
        datetime.fromisoformat(shaped["observed_at"].replace("Z", "+00:00"))
    except ValueError as error:
        raise ReviewAdapterError(
            f"live review state observed_at is not a real timestamp: {shaped['observed_at']!r}"
        ) from error
    return shaped
