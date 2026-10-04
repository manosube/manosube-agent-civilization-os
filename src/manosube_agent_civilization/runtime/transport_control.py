"""Actions-independent transport control for Runtime Observation (Issue #105).

```text
RUNTIME OBSERVATION (observe_runtime_target, route.py)
= the one canonical capability, already transport-agnostic (any RuntimeAdapter)

GitHub Actions / manual SSH / grant-gated unattended SSH
= interchangeable TRANSPORTS invoking that identical capability

THIS MODULE
= decides which transport an attempt may use, never how an observation is taken
```

Issue #105's own structural difference is transport *independence*, not a new capability:
``observe_runtime_target`` already does not care who or what calls it, and
:class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter` already does not care
whether a GitHub Actions job or a Human's own terminal spawned the process running it. What
was missing is the narrow authorization question sitting *in front of* that route for the one
transport this package will ever execute without a Human present at the moment of execution --
grant-gated unattended SSH -- and the Actions-independent classification that keeps a quota/
runner-allocation failure from ever being misread as a code, test, or runtime failure.

**This module creates no second Runtime, Authority, Evidence, State, or Reflow owner.** A
:func:`require_valid_grant` record is a narrower, transport-only gate: it never itself decides
an observation outcome, never itself commits anything, and never substitutes for the Boundary
validation :mod:`~manosube_agent_civilization.runtime.route` already performs on the identical
``host``/``port``/``user``/``probe_identity`` fields a grant also carries -- a grant answers
only "may this exact transport be used for this exact target, right now", exactly as
:mod:`manosube_agent_civilization.development_binding.executor_selection` answers the
analogous "is this eligible provider the one actually selected for this exact work unit" for a
different Kernel area, through the identical shape: a structured record, checked offline, with
no network call, no credential, and no default-admit path. An **unreadable** grant (wrong
Python shape, an unknown key, a missing required key, a malformed field) raises
:class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError`; there is no
other outcome a grant check in this package ever returns -- it is proved valid, scoped to the
requested transport, and current, or the call is refused.

**Tool availability must not create Authority** (Issue #105 design requirement 3/6): a grant
that does not name ``PREAUTHORIZED_UNATTENDED_SSH`` is never treated as permitting it merely
because :func:`classify_actions_dispatch` reports ``GITHUB_ACTIONS`` ``UNAVAILABLE``, and an
``UNKNOWN`` startup cause is never silently treated as confirmed quota exhaustion. Within a
grant's own valid window, selecting a transport the grant already names costs no fresh Human
adoption merely because the transport changed (the adopted operational-continuity design,
Issue #105 comment 5975523513); a new target, scope, probe, or an expired grant still
requires a new one.

**Manual (Capability A) and unattended execution (Capability B's automatic half) share one
command.** :func:`render_manual_ssh_command` and
:class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter` both build their SSH
invocation through the identical :func:`~manosube_agent_civilization.runtime.network.
render_ssh_command_argv` -- the exact command a Human is shown is, field for field, the exact
command this package would otherwise run unattended, so neither path can silently diverge from
the other.
"""

from __future__ import annotations

from collections.abc import Mapping
import shlex
from typing import Any

from .engine import parse_utc_instant, require_valid_timestamp
from .errors import RuntimeRequirementError
from .network import render_ssh_command_argv
from .types import SSH_PROBE_IDENTITIES

#: The sole authority that may ratify a bounded-SSH-observation grant. Matches
#: ``development_binding.policy.HUMAN_AUTHORITY`` by value, not import -- a self-contained
#: extension of the identical Human-authority convention this repository already keeps for
#: every other closed, offline-checked grant, never a second owner that merely happens to
#: agree with it today.
HUMAN_AUTHORITY = "SHUKOU"

#: Every transport/mode a grant may permit. ``GITHUB_ACTIONS`` and ``MANUAL_SSH`` carry no
#: further authorization beyond the grant's own scope and validity window -- a Human operator
#: running a rendered command, or a GitHub Actions job a Human already dispatched, is itself
#: the authorization act for that one attempt. ``PREAUTHORIZED_UNATTENDED_SSH`` is the one
#: mode this package will itself execute SSH for with no Human present at invocation time, and
#: is refused unless a grant explicitly names it.
PERMITTED_TRANSPORT_MODES: frozenset[str] = frozenset(
    {"GITHUB_ACTIONS", "MANUAL_SSH", "PREAUTHORIZED_UNATTENDED_SSH"}
)

#: What an Actions-independent control entry point may ever classify one dispatch attempt as.
#: Never a code/test/runtime verdict: ``AVAILABLE``/``UNAVAILABLE``/``UNKNOWN`` describe the
#: *transport*, and whatever this resolves to is kept entirely separate from
#: ``RUNTIME_OBSERVATION_OUTCOMES`` -- Actions being unavailable never becomes, and never
#: waives, a runtime observation outcome.
DISPATCH_STATUSES: frozenset[str] = frozenset({"AVAILABLE", "UNAVAILABLE", "UNKNOWN"})

_SCHEMA_VERSION = "0.1"

_REQUIRED_GRANT_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "grant_id",
        "project_id",
        "host",
        "port",
        "user",
        "probe_identity",
        "permitted_transports",
        "issued_at",
        "expires_at",
        "decision_authority",
        "decision_status",
    }
)


def require_valid_grant(grant: Any) -> dict[str, Any]:
    """Return *grant* as a plain ``dict``, proved to be a complete, closed, Human-ratified
    bounded-SSH-observation grant.

    Checked, in order: exact closed key set; ``schema_version``; non-empty string identity/
    scope fields; ``port`` an integer ``1..65535``; ``probe_identity`` one of
    :data:`~manosube_agent_civilization.runtime.types.SSH_PROBE_IDENTITIES` (a grant naming an
    unpinned probe is exactly as refused as a Boundary naming one); ``permitted_transports`` a
    non-empty list drawn only from :data:`PERMITTED_TRANSPORT_MODES`; a genuinely ordered
    ``issued_at``/``expires_at`` window; ``decision_authority`` ``== HUMAN_AUTHORITY`` and
    ``decision_status`` ``== "RATIFIED"``. There is no default-admit path: a caller that wants
    an unratified grant to be treated as a draft gets a raised
    :class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError`, not a
    permissive decision value, exactly as every other requirement check in this package
    already keeps.
    """

    if not isinstance(grant, Mapping):
        raise RuntimeRequirementError(
            f"runtime observation grant must be an explicit mapping: {grant!r}"
        )
    unknown = set(grant) - _REQUIRED_GRANT_KEYS
    if unknown:
        raise RuntimeRequirementError(
            f"runtime observation grant carries unknown keys: {sorted(unknown)}"
        )
    missing = _REQUIRED_GRANT_KEYS - set(grant)
    if missing:
        raise RuntimeRequirementError(
            f"runtime observation grant omits required keys: {sorted(missing)}"
        )

    checked = dict(grant)
    if checked.get("schema_version") != _SCHEMA_VERSION:
        raise RuntimeRequirementError(
            "unsupported runtime observation grant schema_version: "
            f"{checked.get('schema_version')!r}"
        )
    for key in ("grant_id", "project_id", "host", "user"):
        value = checked.get(key)
        if not isinstance(value, str) or not value:
            raise RuntimeRequirementError(
                f"runtime observation grant.{key} must be a non-empty string: {value!r}"
            )
    port = checked.get("port")
    if not isinstance(port, int) or isinstance(port, bool) or not (1 <= port <= 65535):
        raise RuntimeRequirementError(
            f"runtime observation grant.port must be an integer 1..65535: {port!r}"
        )
    probe_identity = checked.get("probe_identity")
    if probe_identity not in SSH_PROBE_IDENTITIES:
        raise RuntimeRequirementError(
            f"runtime observation grant.probe_identity is not a pinned probe: {probe_identity!r}"
        )
    permitted_transports = checked.get("permitted_transports")
    if not isinstance(permitted_transports, list) or not permitted_transports:
        raise RuntimeRequirementError(
            "runtime observation grant.permitted_transports must be a non-empty list: "
            f"{permitted_transports!r}"
        )
    if not all(
        isinstance(transport, str) and transport in PERMITTED_TRANSPORT_MODES
        for transport in permitted_transports
    ):
        raise RuntimeRequirementError(
            "runtime observation grant.permitted_transports names an unrecognized transport "
            f"mode: {permitted_transports!r}"
        )
    issued_at = require_valid_timestamp(
        checked.get("issued_at"), "runtime observation grant.issued_at"
    )
    expires_at = require_valid_timestamp(
        checked.get("expires_at"), "runtime observation grant.expires_at"
    )
    if parse_utc_instant(issued_at, "issued_at") >= parse_utc_instant(expires_at, "expires_at"):
        raise RuntimeRequirementError(
            "runtime observation grant.issued_at must be strictly before its own expires_at: "
            f"{issued_at!r} >= {expires_at!r}"
        )
    if checked.get("decision_authority") != HUMAN_AUTHORITY:
        raise RuntimeRequirementError(
            f"runtime observation grant.decision_authority must be {HUMAN_AUTHORITY!r}: "
            f"{checked.get('decision_authority')!r}"
        )
    if checked.get("decision_status") != "RATIFIED":
        raise RuntimeRequirementError(
            "runtime observation grant.decision_status must be 'RATIFIED': "
            f"{checked.get('decision_status')!r}"
        )
    checked["permitted_transports"] = list(permitted_transports)
    return checked


def require_grant_permits_transport(grant: Mapping[str, Any], transport: str) -> dict[str, Any]:
    """Return *grant*, proved valid and proved to permit *transport*.

    The one place "tool availability must not create Authority" is actually enforced: a
    caller that merely *can* reach a target over SSH is refused here unless a Human-ratified
    grant already named that exact mode for that exact target -- never because Actions
    happened to be unavailable at the moment of the attempt.
    """

    checked = require_valid_grant(grant)
    if transport not in PERMITTED_TRANSPORT_MODES:
        raise RuntimeRequirementError(f"transport is not a recognized transport mode: {transport!r}")
    if transport not in checked["permitted_transports"]:
        raise RuntimeRequirementError(
            f"runtime observation grant {checked['grant_id']!r} does not permit transport "
            f"{transport!r} -- only {checked['permitted_transports']!r}"
        )
    return checked


def require_grant_not_expired(grant: Mapping[str, Any], *, now: str) -> dict[str, Any]:
    """Return *grant*, proved valid and proved still within its own declared validity window
    at *now* -- a caller-supplied canonical UTC timestamp. This module calls no clock of its
    own, exactly as every other time-window check in this package already takes an explicit
    instant rather than reading one, so a test (or a real caller) controls what "now" means."""

    checked = require_valid_grant(grant)
    now_instant = parse_utc_instant(require_valid_timestamp(now, "now"), "now")
    issued_at_instant = parse_utc_instant(checked["issued_at"], "issued_at")
    expires_at_instant = parse_utc_instant(checked["expires_at"], "expires_at")
    if not (issued_at_instant <= now_instant <= expires_at_instant):
        raise RuntimeRequirementError(
            f"runtime observation grant {checked['grant_id']!r} is not valid at {now!r} -- its "
            f"own window is [{checked['issued_at']!r}, {checked['expires_at']!r}]"
        )
    return checked


def render_manual_ssh_command(grant: Mapping[str, Any], *, now: str) -> str:
    """Return the exact, copy/paste-able command string for a Human operator to run for
    *grant*'s own bounded probe (Issue #105 Capability A).

    Built through the identical :func:`~manosube_agent_civilization.runtime.network.
    render_ssh_command_argv` the real adapter itself calls for grant-gated unattended
    execution, so the attended and unattended paths can never silently diverge. Refuses a
    grant that does not permit ``MANUAL_SSH`` or is not currently within its own validity
    window -- rendering a command is itself part of what this module gates, never a harmless
    preview available regardless of authorization.
    """

    checked = require_grant_permits_transport(grant, "MANUAL_SSH")
    require_grant_not_expired(checked, now=now)
    argv = render_ssh_command_argv(
        host=checked["host"],
        port=checked["port"],
        user=checked["user"],
        probe_identity=checked["probe_identity"],
    )
    return shlex.join(argv)


def classify_actions_dispatch(
    *, dispatched: bool, runner_allocated: bool, start_deadline_exceeded: bool
) -> str:
    """Return one of :data:`DISPATCH_STATUSES` for a single GitHub Actions dispatch attempt,
    given facts the caller itself independently observed -- never a status this function
    infers or guesses on its own (Issue #105 design requirement 3/4).

    ``AVAILABLE`` only once a runner was actually allocated -- the one fact this package ever
    treats as "Actions could run at all". ``UNAVAILABLE`` once the caller already knows
    dispatch failed outright, or once its own configured start deadline has passed without a
    runner. An attempt still within its own deadline, dispatched, but not yet runner-allocated
    is honestly ``UNKNOWN`` -- never prematurely read as quota exhaustion or any other
    specific cause without evidence for it.
    """

    if runner_allocated:
        return "AVAILABLE"
    if not dispatched or start_deadline_exceeded:
        return "UNAVAILABLE"
    return "UNKNOWN"


def select_transport(
    *,
    actions_status: str,
    requested_transport: str | None,
    grant: Mapping[str, Any],
    now: str,
) -> str:
    """Return the one transport this call may actually use.

    Actions is preferred (the adopted operational-continuity design): used whenever
    *actions_status* is ``"AVAILABLE"`` and no explicit manual selection overrides it.
    Otherwise *requested_transport* is used, but only once proved both permitted by *grant*
    and current -- Actions being unavailable never by itself escalates to a transport the
    grant does not name (``FALLBACK_CREATES_AUTHORITY=false``), and an operator must make an
    explicit selection rather than one being chosen automatically when Actions cannot run.
    """

    if actions_status not in DISPATCH_STATUSES:
        raise RuntimeRequirementError(f"actions_status is not a recognized status: {actions_status!r}")
    if actions_status == "AVAILABLE" and requested_transport is None:
        return "GITHUB_ACTIONS"
    if requested_transport is None:
        raise RuntimeRequirementError(
            "Actions is not available and no explicit transport was selected -- a Human "
            "operator must choose MANUAL_SSH, or an already-granted PREAUTHORIZED_UNATTENDED_SSH "
            "mode must be explicitly requested; no transport is ever chosen automatically"
        )
    require_grant_permits_transport(grant, requested_transport)
    require_grant_not_expired(grant, now=now)
    return requested_transport


__all__ = [
    "DISPATCH_STATUSES",
    "HUMAN_AUTHORITY",
    "PERMITTED_TRANSPORT_MODES",
    "classify_actions_dispatch",
    "render_manual_ssh_command",
    "require_grant_not_expired",
    "require_grant_permits_transport",
    "require_valid_grant",
    "select_transport",
]
