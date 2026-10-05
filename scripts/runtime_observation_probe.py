"""The one pinned, bounded probe script Runtime Observation's ``SSH_EXEC_BOUNDED`` method runs
(Issue #105, transport-independent runtime observation).

```text
SshRuntimeAdapter.observe()  ----ssh---->  THIS SCRIPT (on the target)  ----stdout(JSON)---->
render_manual_ssh_command()  ----(Human copy/paste runs the identical command)---->
```

Deployed once, read-only, to a target this repository's own ``runtime_observation_probe.py``
boundary trusts (the target identity/host/network-scope checks already happening before this
script is ever reached, in :mod:`manosube_agent_civilization.runtime`). This script performs
no network access, accepts no path or command argument from its caller -- only a closed
``probe_identity`` positional argument and (PR #108 Structural Review Round 5, SR5-F2) a
second, required ``expected_deployment_config_fingerprint`` positional argument -- and never
deploys, pulls, restarts, or edits anything. It prints exactly one JSON object to stdout and
exits ``0`` whether or not the probe itself succeeded; a non-zero exit or empty/malformed
stdout means this script could not even start (Python missing, script not installed, syntax
error), which :class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter` already
treats as an honest transport failure, never a fabricated observation.

**Closed output shape, always**::

    {"ok": true,  "fields": {...}, "deployment_identity": str | null, "reason": null,
     "probe_script_sha256": "<64 hex chars>", "deployment_config_fingerprint": "<64 hex chars>"}
    {"ok": false, "fields": null,  "deployment_identity": null,       "reason": "NOT_FOUND" | "...",
     "probe_script_sha256": "<64 hex chars>", "deployment_config_fingerprint": "<64 hex chars>"}

``probe_script_sha256`` (PR #108 Structural Review Round 1, F3) is this file's own SHA-256
content digest, computed at run time over the script's own bytes -- never a caller-supplied or
cached value. :class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter` compares
it against a bounded-SSH-observation grant's own *signed* ``probe_script_sha256`` field (never
the bare public constant alone, since PR #108 Structural Review Round 2, SR2-F4) and refuses
the observation outright on any mismatch -- a probe *name* identifies nothing, so this is a
genuine improvement over that alone. **Corrected claim (PR #108 Structural Review Round 4,
SR4-F4):** this remains only a consistency check, never proof of what genuinely executed --
``probe_script_sha256``/``SSH_PROBE_SCRIPT_SHA256`` are both *public* values, so a substitute
script can trivially echo back the expected digest without forging anything. No stronger
remote attestation primitive exists over plain SSH.

``deployment_config_fingerprint`` (PR #108 Structural Review Round 3, SR3-F4) is a content
digest over exactly which real excerpt paths this run is *actually* configured with (see
:func:`_deployment_config_fingerprint`) -- closing the gap a script digest alone leaves open:
two byte-identical copies of this script, each deployed beside a *different* sibling
configuration file, report the identical ``probe_script_sha256`` while reading entirely
different real files. The adapter compares this value against the identical grant's own
signed ``deployment_config_fingerprint`` field -- the identical consistency-check-only
discipline the script digest itself keeps, corrected the same way by SR4-F4.

**Pre-read configuration authorization (PR #108 Structural Review Round 4, SR4-F4; corrected
by Round 5, SR5-F2).** Every prior round's own check of ``deployment_config_fingerprint``
happened *after* this script had already read the configured source/log files -- an honest
after-the-fact mismatch report, but not an actual refusal to read an unauthorized
configuration in the first place. Round 4's own fix added a second sibling file,
``runtime_observation_probe.approved_config.json``, checked before any read -- but that file
was an unsigned local JSON value compared only against *this script's own* locally-resolved
configuration: a sibling config and its own local "approval" could be edited together, in
lockstep, by anyone with mere filesystem access to the target, with no connection whatsoever to
what the real, currently-verified bounded-SSH-observation Grant actually authorizes. The
Structural Advisor reproduced exactly that: a swapped sibling config plus a locally
self-consistent approval file, read and returned successfully, with no caller Grant involved
at all.

**Round 5's fix: the caller's own live Grant commitment travels with the command itself.**
This script now takes a **required second positional argument**,
*expected_deployment_config_fingerprint* -- not a file this script reads from disk at all, but
a value that can only ever reach this script by riding along on the one, specific, already-
Grant-verified SSH command
:func:`~manosube_agent_civilization.runtime.network.render_ssh_command_argv` renders for
*this exact attempt* (see that function's own docstring). For ``SOURCE_LOG_EXCERPT_BOUNDED``,
this script computes its own :func:`_deployment_config_fingerprint` exactly as before, and now
requires it to **equal the caller-supplied argument** before :func:`_source_log_excerpt` is
ever called. A missing argument, or one of the wrong shape (not exactly 64 lowercase hex
characters), is refused by :func:`main` itself as ``{"ok": false, "reason": "MALFORMED", ...}``
before :func:`run` is ever reached -- identically to any other malformed invocation of this
script; a correctly-shaped argument that simply does not match this deployment's own computed
fingerprint is refused by :func:`run` as ``{"ok": false, "reason": "CONFIG_NOT_AUTHORIZED",
...}`` instead. Both paths are zero-read before either check is reached. A party who can
only edit local sibling files on the target, but does not control what the real caller's own
freshly Boot-verified Grant actually says, can no longer silently redirect reads merely by
keeping two local files mutually consistent -- the decisive value now comes from outside the
target, supplied fresh on every single invocation, never a static file sitting there in
advance. No sibling *approval* file is read for this purpose any longer; the *path*-
configuration file (:data:`PROBE_CONFIG_FILENAME`) is unrelated and unchanged.

**Two pinned probe identities (Issue #105 V1; extended by PR #108 SR1 F3 to cover both bounded
source-code AND log retrieval, as Capability B's own adoption requires)**:

- ``OS_HEALTH_SNAPSHOT_BOUNDED``: ``hostname``, ``uptime_seconds``, ``os_release`` -- read-only
  local facts, no caller-supplied path.
- ``SOURCE_LOG_EXCERPT_BOUNDED``: a bounded tail of exactly two fixed, pre-configured paths
  (:data:`SOURCE_EXCERPT_PATH`, :data:`LOG_EXCERPT_PATH` below). Neither is ever taken from an
  argument, an environment variable, or any other caller-reachable input, so there is no path
  a remote caller can ever traverse (``PATH_PARAMETERIZED_PROBE_AUTHORIZED=false`` -- a future,
  separately reviewed extension, not this one). Either path may be independently absent
  (reported via ``source_available``/``log_available``); the probe reports ``NOT_FOUND`` only
  when **both** are unavailable.

**Per-deployment path configuration (PR #108 Structural Review Round 2, SR2-F4) is a sibling
file, never an edit to this reviewed script.** An operator who needs different excerpt paths on
a specific target creates a ``runtime_observation_probe.config.json`` file next to this script
(resolved via this script's own, already-resolved directory -- never a caller-supplied path),
naming ``source_excerpt_path``/``log_excerpt_path`` as needed; any key the file omits, or the
file's own total absence, falls back to this script's own built-in default below. This exists
precisely so :data:`manosube_agent_civilization.runtime.types.SSH_PROBE_SCRIPT_SHA256` -- the
one pinned digest a bounded-SSH-observation grant's own signed ``probe_script_sha256`` field is
checked against -- never has to change for an ordinary per-deployment path customization. The
earlier instruction to edit :data:`SOURCE_EXCERPT_PATH`/:data:`LOG_EXCERPT_PATH` directly before
deployment is withdrawn: doing so changes this file's own content digest, which breaks the
exact pin a grant's own Human Authority signature is supposed to bind to a specific, reviewed
artifact -- the one contradiction SR2-F4 itself identified and this round corrects.

Every bounded file read in this script opens with ``O_NOFOLLOW`` (refusing a symlinked *final
path component* outright -- PR #108 SR1 F4) and reads at most its own fixed byte ceiling,
seeking to the file's own current tail first so a file that has grown since this script started
cannot be read beyond that bound in one pass. Every path this script reads that an operator
configures -- the excerpt paths, and this script's own sibling configuration file -- is further
required to equal its own fully resolved real path before it is ever opened at all (PR #108
Structural Review Round 2, SR2-F3(C)): ``O_NOFOLLOW`` alone only ever refused a symlink at the
final path component, never one placed in an *ancestor* directory, through which a path that
never itself looks like a symlink can still resolve somewhere else entirely.

Stdlib only, Python 3.8+ compatible (a target's own Python need not match this repository's
own ``>=3.12`` requirement) -- deliberately so this one file can be copied to a target with no
dependency installation at all, mirroring :class:`~manosube_agent_civilization.runtime.adapter.
LocalHttpRuntimeAdapter`'s own "stdlib only" discipline for its transport.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import sys

#: The maximum number of trailing lines either excerpt ever returns, and the maximum number of
#: bytes either ever reads to find them -- both bounds exist so a target whose file has grown
#: unexpectedly large, or is being actively appended to while this script runs, cannot turn one
#: bounded probe into an unbounded read (PR #108 SR1 F4).
EXCERPT_MAX_LINES = 200
EXCERPT_MAX_READ_BYTES = 1_048_576

#: The bound this script applies to its own two small system-fact reads
#: (``/proc/uptime``, ``/etc/os-release``) -- normally tiny files, bounded anyway on the
#: identical "never an unbounded read of anything" discipline the excerpt reads already keep.
SYSTEM_FACT_MAX_READ_BYTES = 65_536

#: The one optional file this script reads to report a target's own declared identity back to
#: the caller -- an honest "this target declared no identity of its own" (``None``) when
#: absent, exactly as :class:`~manosube_agent_civilization.runtime.adapter.
#: LocalHttpRuntimeAdapter` never fabricates a ``deployment_fingerprint`` its target did not
#: actually report.
DEPLOYMENT_IDENTITY_PATH = "/etc/manosube/deployment_fingerprint"

#: This script's own optional sibling configuration file (PR #108 Structural Review Round 2,
#: SR2-F4) -- resolved only relative to this script's own, already-resolved directory, never
#: from a caller-supplied path, an argument, or an environment variable. See :func:`_load_probe_config`.
PROBE_CONFIG_FILENAME = "runtime_observation_probe.config.json"
PROBE_CONFIG_MAX_READ_BYTES = 65_536

#: The one shape *expected_deployment_config_fingerprint* (the required second positional CLI
#: argument, PR #108 Structural Review Round 5, SR5-F2) must satisfy before it is ever compared
#: against anything -- a lowercase, 64-character hex SHA-256 digest, identical to the shape
#: :func:`_deployment_config_fingerprint` itself always produces. A value of any other shape is
#: refused as ``MALFORMED`` before ``run()`` is ever reached.
_HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")

PROBE_IDENTITIES = ("OS_HEALTH_SNAPSHOT_BOUNDED", "SOURCE_LOG_EXCERPT_BOUNDED")


class _UnsafePathError(OSError):
    """Raised when a path this script would read turns out to be a symlink (or anything else
    ``O_NOFOLLOW`` refuses), or (PR #108 SR2-F3(C)) resolves through a symlink placed anywhere
    in its own *ancestor* directories -- never silently followed either way."""


def _open_bounded(path: str, *, max_bytes: int) -> bytes:
    """Open *path* read-only, refusing a symlinked *final path component* outright
    (PR #108 SR1 F4), and return at most its own trailing *max_bytes* -- seeking to the file's
    own current tail first, so this is one bounded read regardless of how large or
    actively-growing the file is.

    Deliberately applies no ancestor-directory symlink check of its own -- used directly only
    for this script's own ``__file__`` self-digest read, where *path* is whatever Python itself
    handed this script (which may be a relative path, depending on how it was invoked, and is
    never an attacker-reachable value in the first place). Every path this script reads that an
    operator configures goes through :func:`_open_bounded_strict` instead.
    """

    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        raise
    except PermissionError:
        raise
    except OSError as error:
        raise _UnsafePathError(str(error)) from error
    with os.fdopen(fd, "rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        read_from = max(0, size - max_bytes)
        handle.seek(read_from)
        return handle.read(max_bytes)


def _open_bounded_strict(path: str, *, max_bytes: int) -> bytes:
    """The identical bound :func:`_open_bounded` already applies, opened through a
    *descriptor-relative* no-follow walk rather than a single ``open(path)`` call -- closing a
    real race the prior round's own ``realpath(path) == path`` *then* ``os.open(path)`` left
    open (PR #108 Structural Review Round 3, SR3-F3(B)).

    **The race this closes.** ``realpath()`` and ``open()`` are two separate system calls
    against the same *string* path. Between them, nothing stops a concurrent process from
    replacing one of *path*'s own ancestor directories with a symlink to somewhere else --
    ``realpath()`` sees (and approves) the original, genuine ancestry, and the very next
    ``os.open()`` call then re-resolves the *same string* from scratch and walks through the
    now-swapped symlink instead, reading a file this check never actually approved. The
    Structural Advisor reproduced this deterministically against the prior correction with a
    real ancestor-directory swap timed between the two calls.

    **The fix.** This walks *path* one component at a time, starting from the filesystem
    root, opening each directory component with ``os.O_NOFOLLOW`` *relative to the previously
    opened directory's own file descriptor* (``dir_fd=``) rather than ever re-resolving a
    string path. No step here ever re-parses an absolute path from scratch, so there is no
    window between "check" and "open" for a concurrent rename or symlink-swap to exploit --
    the identity of every ancestor is pinned by the descriptor that was already opened for it,
    not re-derived from a name that could have changed since.
    """

    if not path.startswith("/"):
        raise _UnsafePathError(f"path must be absolute: {path!r}")
    components = [component for component in path.split("/") if component]
    if not components:
        raise _UnsafePathError(f"path has no real component to open: {path!r}")

    dir_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in components[:-1]:
            try:
                next_fd = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=dir_fd,
                )
            except FileNotFoundError:
                raise
            except PermissionError:
                raise
            except OSError as error:
                raise _UnsafePathError(str(error)) from error
            os.close(dir_fd)
            dir_fd = next_fd
        try:
            fd = os.open(
                components[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dir_fd
            )
        except FileNotFoundError:
            raise
        except PermissionError:
            raise
        except OSError as error:
            raise _UnsafePathError(str(error)) from error
    finally:
        os.close(dir_fd)
    with os.fdopen(fd, "rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        read_from = max(0, size - max_bytes)
        handle.seek(read_from)
        return handle.read(max_bytes)


def _load_probe_config() -> dict[str, object]:
    """Return this script's own optional sibling configuration (PR #108 SR2-F4), read once per
    run from exactly :data:`PROBE_CONFIG_FILENAME` beside this script's own already-resolved
    directory -- never a caller-supplied path. Absence, unreadable content, malformed JSON, or
    a non-object body are all treated identically: an empty configuration, meaning every
    setting falls back to its own built-in default -- a broken or missing config file degrades
    this script to its shipped defaults rather than breaking its own fixed "always prints one
    JSON object and exits 0" contract."""

    directory = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(directory, PROBE_CONFIG_FILENAME)
    try:
        raw = _open_bounded_strict(config_path, max_bytes=PROBE_CONFIG_MAX_READ_BYTES)
    except OSError:
        return {}
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


_PROBE_CONFIG = _load_probe_config()

#: The bounded source-code excerpt path ``SOURCE_LOG_EXCERPT_BOUNDED`` reads (PR #108 SR1 F3).
#: Configured per deployment through :data:`PROBE_CONFIG_FILENAME`'s own
#: ``source_excerpt_path`` key (SR2-F4) -- never by editing this constant directly, which would
#: change this reviewed script's own content digest. Falls back to this built-in default when
#: the sibling configuration file is absent or names no such key.
SOURCE_EXCERPT_PATH = str(
    _PROBE_CONFIG.get(
        "source_excerpt_path", "/opt/manosube-runtime-observation/source_excerpt.txt"
    )
)

#: The bounded log excerpt path ``SOURCE_LOG_EXCERPT_BOUNDED`` reads. Configured per deployment
#: through :data:`PROBE_CONFIG_FILENAME`'s own ``log_excerpt_path`` key (SR2-F4), identically to
#: :data:`SOURCE_EXCERPT_PATH` above.
LOG_EXCERPT_PATH = str(
    _PROBE_CONFIG.get("log_excerpt_path", "/var/log/manosube-runtime-observation/observed.log")
)


def _probe_script_sha256() -> str:
    """This script's own content digest, computed fresh every run over its own bytes on disk
    -- never cached, never a caller-supplied value (PR #108 SR1 F3)."""

    return hashlib.sha256(_open_bounded(__file__, max_bytes=EXCERPT_MAX_READ_BYTES)).hexdigest()


def _deployment_config_fingerprint() -> str:
    """This script's own effective per-deployment configuration digest -- a content digest
    over exactly which real excerpt paths this run is *actually* configured with, whether from
    a sibling configuration file or this script's own shipped defaults (PR #108 Structural
    Review Round 3, SR3-F4).

    **The gap this closes.** ``probe_script_sha256`` proves which *script* ran; it says
    nothing about which *configuration* that script was run with. Two byte-identical copies of
    this script, deployed beside two different sibling ``runtime_observation_probe.config.json``
    files, report the identical ``probe_script_sha256`` while
    :data:`SOURCE_EXCERPT_PATH`/:data:`LOG_EXCERPT_PATH` -- and therefore every real file
    actually read -- can differ completely. A bounded-SSH-observation grant's own signed
    ``deployment_config_fingerprint`` field binds the Human Authority's own approval to a
    specific configuration, not merely to the reviewed script's own bytes; this function is the
    one source of truth every run computes that value from, deterministically, over whichever
    paths are actually in effect right now -- never a cached value, and never read from the
    configuration file directly (a tampered report could otherwise simply echo a stale value).
    """

    payload = json.dumps(
        {"source_excerpt_path": SOURCE_EXCERPT_PATH, "log_excerpt_path": LOG_EXCERPT_PATH},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_deployment_identity() -> str | None:
    try:
        raw = _open_bounded_strict(DEPLOYMENT_IDENTITY_PATH, max_bytes=SYSTEM_FACT_MAX_READ_BYTES)
    except OSError:
        return None
    value = raw.decode("utf-8", errors="replace").strip()
    return value or None


def _os_health_snapshot() -> dict[str, object]:
    try:
        raw = _open_bounded("/proc/uptime", max_bytes=SYSTEM_FACT_MAX_READ_BYTES)
        uptime_seconds = float(raw.decode("ascii", errors="replace").split()[0])
    except (OSError, ValueError, IndexError):
        uptime_seconds = None

    os_release = None
    try:
        raw = _open_bounded("/etc/os-release", max_bytes=SYSTEM_FACT_MAX_READ_BYTES)
        for line in raw.decode("utf-8", errors="replace").splitlines():
            if line.startswith("PRETTY_NAME="):
                os_release = line.partition("=")[2].strip().strip('"')
                break
    except OSError:
        pass

    return {
        "hostname": platform.node(),
        "uptime_seconds": uptime_seconds,
        "os_release": os_release,
    }


def _bounded_excerpt(path: str) -> tuple[bool, dict[str, object]]:
    """Return ``(available, fields)`` for one bounded excerpt path -- ``available=False`` with
    empty *fields* on any read failure (missing, unreadable, or unsafe), never a fabricated
    excerpt and never a traceback."""

    try:
        raw = _open_bounded_strict(path, max_bytes=EXCERPT_MAX_READ_BYTES)
    except OSError:
        return False, {}
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()[-EXCERPT_MAX_LINES:]
    excerpt = "\n".join(lines)
    return True, {
        "line_count": len(lines),
        "excerpt": excerpt,
        "excerpt_byte_length": len(excerpt.encode("utf-8")),
    }


def _source_log_excerpt() -> tuple[dict[str, object], str | None]:
    """Return ``(fields, reason)`` -- *fields* reports both the source and log excerpt, each
    independently available or not; *reason* is set (and *fields* is ``{}``) only when
    **neither** path is available, so a target missing just one of the two still reports the
    other rather than failing the whole probe (PR #108 SR1 F3)."""

    source_available, source_fields = _bounded_excerpt(SOURCE_EXCERPT_PATH)
    log_available, log_fields = _bounded_excerpt(LOG_EXCERPT_PATH)
    if not source_available and not log_available:
        return {}, "NOT_FOUND"
    return {
        "source_available": source_available,
        "source_excerpt": source_fields.get("excerpt"),
        "source_line_count": source_fields.get("line_count"),
        "source_excerpt_byte_length": source_fields.get("excerpt_byte_length"),
        "log_available": log_available,
        "log_excerpt": log_fields.get("excerpt"),
        "log_line_count": log_fields.get("line_count"),
        "log_excerpt_byte_length": log_fields.get("excerpt_byte_length"),
    }, None


def run(
    probe_identity: str,
    *,
    deployment_config_fingerprint: str,
    expected_deployment_config_fingerprint: str,
) -> dict[str, object]:
    """Return this script's one closed-shape report for *probe_identity* -- never raises; an
    unrecognized identity is itself an ``ok: false`` report, not a traceback, so a caller
    always receives the one JSON shape it expects.

    *deployment_config_fingerprint* is the already-computed digest of whichever excerpt paths
    are actually in effect for this run (:func:`_deployment_config_fingerprint`).

    *expected_deployment_config_fingerprint* (PR #108 Structural Review Round 5, SR5-F2) is the
    caller-supplied second positional CLI argument -- the live, Grant-verified commitment that
    arrived only by riding along on this exact SSH command (see the module docstring's "Round
    5's fix" section). For ``SOURCE_LOG_EXCERPT_BOUNDED`` it is required to equal
    *deployment_config_fingerprint* **before** :func:`_source_log_excerpt` is ever called -- no
    local sibling approval file is consulted for this purpose any longer.
    """

    if probe_identity not in PROBE_IDENTITIES:
        return {"ok": False, "fields": None, "deployment_identity": None, "reason": "MALFORMED"}

    deployment_identity = _read_deployment_identity()
    if probe_identity == "OS_HEALTH_SNAPSHOT_BOUNDED":
        return {
            "ok": True,
            "fields": _os_health_snapshot(),
            "deployment_identity": deployment_identity,
            "reason": None,
        }

    # PR #108 Structural Review Round 5, SR5-F2: authorization is checked, and refused on any
    # failure, *before* this script ever reads SOURCE_EXCERPT_PATH/LOG_EXCERPT_PATH -- never
    # only reported as a mismatch after the fact, and never against a static local file. A
    # missing, malformed, or mismatched caller-supplied fingerprint is refused identically;
    # _source_log_excerpt() (the one function that actually opens either excerpt path) is never
    # called on any of them.
    if expected_deployment_config_fingerprint != deployment_config_fingerprint:
        return {
            "ok": False,
            "fields": None,
            "deployment_identity": None,
            "reason": "CONFIG_NOT_AUTHORIZED",
        }

    fields, reason = _source_log_excerpt()
    if reason is not None:
        return {"ok": False, "fields": None, "deployment_identity": None, "reason": reason}
    return {
        "ok": True,
        "fields": fields,
        "deployment_identity": deployment_identity,
        "reason": None,
    }


def main(argv: list[str]) -> int:
    probe_script_sha256 = _probe_script_sha256()
    deployment_config_fingerprint = _deployment_config_fingerprint()
    if (
        len(argv) != 2
        or not isinstance(argv[1], str)
        or not _HEX64_PATTERN.fullmatch(argv[1])
    ):
        report = {
            "ok": False,
            "fields": None,
            "deployment_identity": None,
            "reason": "MALFORMED",
        }
    else:
        report = run(
            argv[0],
            deployment_config_fingerprint=deployment_config_fingerprint,
            expected_deployment_config_fingerprint=argv[1],
        )
    report["probe_script_sha256"] = probe_script_sha256
    report["deployment_config_fingerprint"] = deployment_config_fingerprint
    json.dump(report, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
