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
``probe_identity`` positional argument -- and never deploys, pulls, restarts, or edits
anything. It prints exactly one JSON object to stdout and exits ``0`` whether or not the probe
itself succeeded; a non-zero exit or empty/malformed stdout means this script could not even
start (Python missing, script not installed, syntax error), which
:class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter` already treats as an
honest transport failure, never a fabricated observation.

**Closed output shape, always**::

    {"ok": true,  "fields": {...}, "deployment_identity": str | null, "reason": null,
     "probe_script_sha256": "<64 hex chars>"}
    {"ok": false, "fields": null,  "deployment_identity": null,       "reason": "NOT_FOUND" | "...",
     "probe_script_sha256": "<64 hex chars>"}

``probe_script_sha256`` (PR #108 Structural Review Round 1, F3) is this file's own SHA-256
content digest, computed at run time over the script's own bytes -- never a caller-supplied or
cached value. :class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter` compares
it against :data:`manosube_agent_civilization.runtime.types.SSH_PROBE_SCRIPT_SHA256`, the one
pinned expected digest this repository reviews, and refuses the observation outright on any
mismatch -- a probe *name* identifies nothing; this is what actually proves the file executed
on the target is the exact reviewed artifact, not a same-named substitute.

**Two pinned probe identities (Issue #105 V1; extended by PR #108 SR1 F3 to cover both bounded
source-code AND log retrieval, as Capability B's own adoption requires)**:

- ``OS_HEALTH_SNAPSHOT_BOUNDED``: ``hostname``, ``uptime_seconds``, ``os_release`` -- read-only
  local facts, no caller-supplied path.
- ``SOURCE_LOG_EXCERPT_BOUNDED``: a bounded tail of exactly two fixed, pre-configured paths
  (:data:`SOURCE_EXCERPT_PATH`, :data:`LOG_EXCERPT_PATH` below) -- an operator deploying this
  script to a real target edits those two constants before deployment; neither is ever taken
  from an argument, an environment variable, or any other caller-reachable input, so there is
  no path a remote caller can ever traverse (``PATH_PARAMETERIZED_PROBE_AUTHORIZED=false`` -- a
  future, separately reviewed extension, not this one). Either path may be independently
  absent (reported via ``source_available``/``log_available``); the probe reports ``NOT_FOUND``
  only when **both** are unavailable.

Every bounded file read in this script opens with ``O_NOFOLLOW`` (refusing a symlink outright --
PR #108 SR1 F4) and reads at most its own fixed byte ceiling, seeking to the file's own current
tail first so a file that has grown since this script started cannot be read beyond that bound
in one pass.

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
import sys

#: The bounded source-code excerpt path ``SOURCE_LOG_EXCERPT_BOUNDED`` reads (PR #108 SR1 F3)
#: -- fixed at deployment time by whoever installs this script on a real target, never
#: supplied by a caller. Edit this constant (and :data:`LOG_EXCERPT_PATH`, and nothing else)
#: before copying this script to a specific target.
SOURCE_EXCERPT_PATH = "/opt/manosube-runtime-observation/source_excerpt.txt"

#: The bounded log excerpt path ``SOURCE_LOG_EXCERPT_BOUNDED`` reads -- fixed at deployment
#: time by whoever installs this script on a real target, never supplied by a caller.
LOG_EXCERPT_PATH = "/var/log/manosube-runtime-observation/observed.log"

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

PROBE_IDENTITIES = ("OS_HEALTH_SNAPSHOT_BOUNDED", "SOURCE_LOG_EXCERPT_BOUNDED")


class _UnsafePathError(OSError):
    """Raised when a path this script would read turns out to be a symlink (or anything else
    ``O_NOFOLLOW`` refuses) -- never silently followed."""


def _open_bounded(path: str, *, max_bytes: int) -> bytes:
    """Open *path* read-only, refusing a symlink outright (PR #108 SR1 F4), and return at most
    its own trailing *max_bytes* -- seeking to the file's own current tail first, so this is
    one bounded read regardless of how large or actively-growing the file is."""

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


def _probe_script_sha256() -> str:
    """This script's own content digest, computed fresh every run over its own bytes on disk
    -- never cached, never a caller-supplied value (PR #108 SR1 F3)."""

    return hashlib.sha256(_open_bounded(__file__, max_bytes=EXCERPT_MAX_READ_BYTES)).hexdigest()


def _read_deployment_identity() -> str | None:
    try:
        raw = _open_bounded(DEPLOYMENT_IDENTITY_PATH, max_bytes=SYSTEM_FACT_MAX_READ_BYTES)
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
        raw = _open_bounded(path, max_bytes=EXCERPT_MAX_READ_BYTES)
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


def run(probe_identity: str) -> dict[str, object]:
    """Return this script's one closed-shape report for *probe_identity* -- never raises; an
    unrecognized identity is itself an ``ok: false`` report, not a traceback, so a caller
    always receives the one JSON shape it expects."""

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
    if len(argv) != 1:
        report = {
            "ok": False,
            "fields": None,
            "deployment_identity": None,
            "reason": "MALFORMED",
        }
    else:
        report = run(argv[0])
    report["probe_script_sha256"] = probe_script_sha256
    json.dump(report, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
