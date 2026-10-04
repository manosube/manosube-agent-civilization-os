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

    {"ok": true,  "fields": {...}, "deployment_identity": str | null, "reason": null}
    {"ok": false, "fields": null,  "deployment_identity": null,       "reason": "NOT_FOUND" | "PERMISSION_DENIED" | "..."}

**Two pinned probe identities (Issue #105 V1 -- a disclosed, deliberately minimal scope)**:

- ``OS_HEALTH_SNAPSHOT_BOUNDED``: ``hostname``, ``uptime_seconds``, ``os_release`` -- read-only
  local facts, no caller-supplied path.
- ``SOURCE_LOG_EXCERPT_BOUNDED``: a bounded tail of exactly one fixed, pre-configured log path
  (:data:`LOG_EXCERPT_PATH` below) -- an operator deploying this script to a real target edits
  that one constant before deployment; it is never taken from an argument, an environment
  variable, or any other caller-reachable input, so there is no path a remote caller can ever
  traverse (``PATH_PARAMETERIZED_PROBE_AUTHORIZED=false`` -- a future, separately reviewed
  extension, not this one).

Stdlib only, Python 3.8+ compatible (a target's own Python need not match this repository's
own ``>=3.12`` requirement) -- deliberately so this one file can be copied to a target with no
dependency installation at all, mirroring :class:`~manosube_agent_civilization.runtime.adapter.
LocalHttpRuntimeAdapter`'s own "stdlib only" discipline for its transport.
"""

from __future__ import annotations

import json
import platform
import sys

#: The bounded log excerpt path ``SOURCE_LOG_EXCERPT_BOUNDED`` reads -- fixed at deployment
#: time by whoever installs this script on a real target, never supplied by a caller. Edit
#: this one constant (and nothing else) before copying this script to a specific target.
LOG_EXCERPT_PATH = "/var/log/manosube-runtime-observation/observed.log"

#: The maximum number of trailing lines ``SOURCE_LOG_EXCERPT_BOUNDED`` ever returns, and the
#: maximum number of bytes it ever reads to find them -- both bounds exist so a target whose
#: log file has grown unexpectedly large cannot turn one bounded probe into an unbounded read.
LOG_EXCERPT_MAX_LINES = 200
LOG_EXCERPT_MAX_READ_BYTES = 1_048_576

#: The one optional file this script reads to report a target's own declared identity back to
#: the caller -- an honest "this target declared no identity of its own" (``None``) when
#: absent, exactly as :class:`~manosube_agent_civilization.runtime.adapter.
#: LocalHttpRuntimeAdapter` never fabricates a ``deployment_fingerprint`` its target did not
#: actually report.
DEPLOYMENT_IDENTITY_PATH = "/etc/manosube/deployment_fingerprint"

PROBE_IDENTITIES = ("OS_HEALTH_SNAPSHOT_BOUNDED", "SOURCE_LOG_EXCERPT_BOUNDED")


def _read_deployment_identity() -> str | None:
    try:
        with open(DEPLOYMENT_IDENTITY_PATH, encoding="utf-8") as handle:
            value = handle.read().strip()
    except OSError:
        return None
    return value or None


def _os_health_snapshot() -> dict[str, object]:
    try:
        with open("/proc/uptime", encoding="utf-8") as handle:
            uptime_seconds = float(handle.read().split()[0])
    except (OSError, ValueError, IndexError):
        uptime_seconds = None

    os_release = None
    try:
        with open("/etc/os-release", encoding="utf-8") as handle:
            for line in handle:
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


def _source_log_excerpt() -> tuple[dict[str, object], str | None]:
    """Return ``(fields, reason)`` -- *fields* is ``{}`` and *reason* is set when the bounded
    log path does not exist or cannot be read, never a fabricated excerpt."""

    try:
        with open(LOG_EXCERPT_PATH, "rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            read_from = max(0, size - LOG_EXCERPT_MAX_READ_BYTES)
            handle.seek(read_from)
            raw = handle.read()
    except FileNotFoundError:
        return {}, "NOT_FOUND"
    except PermissionError:
        return {}, "PERMISSION_DENIED"
    except OSError:
        return {}, "UNAVAILABLE"

    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()[-LOG_EXCERPT_MAX_LINES:]
    excerpt = "\n".join(lines)
    return {
        "line_count": len(lines),
        "excerpt": excerpt,
        "excerpt_byte_length": len(excerpt.encode("utf-8")),
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
    if len(argv) != 1:
        json.dump(
            {"ok": False, "fields": None, "deployment_identity": None, "reason": "MALFORMED"},
            sys.stdout,
        )
        sys.stdout.write("\n")
        return 0
    report = run(argv[0])
    json.dump(report, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
