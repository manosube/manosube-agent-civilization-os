"""Actions-independent transport control for Runtime Observation (Issue #105; grant
authenticity corrected by PR #108 Structural Review Round 1, F1, F2).

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
grant answers only "may this exact transport be used for this exact target, right now" --
never an observation outcome, never a commit, never a substitute for the Boundary validation
:mod:`~manosube_agent_civilization.runtime.route` already performs on the identical
``host``/``port``/``user``/``probe_identity`` fields a grant also carries.

**PR #108 Structural Review Round 1, F1 -- authenticity is reused, not reinvented.** The first
delivery's grant was a plain JSON object whose ``decision_authority``/``decision_status``
fields were self-asserted strings -- a caller could fabricate ``{"decision_authority":
"SHUKOU", "decision_status": "RATIFIED", ...}`` and it would pass every check this module
performed. That is exactly the self-asserted-authority pattern the original adoption
prohibits. The correction reuses the identical trusted verification path
:mod:`~manosube_agent_civilization.runtime.deployment_declaration` already establishes for a
Runtime Deployment Declaration: a grant now carries a genuine Ed25519 ``signature``, verified
here (composing :func:`~manosube_agent_civilization.binding.signature.verify_ed25519_signature`
directly, never reimplemented) against the exact ``human_authority_signing_key`` a *fresh*
:func:`~manosube_agent_civilization.boot.boot_project` call restores for the *exact*
``project_id``/``project_binding_id`` the current attempt is actually using -- never a
caller-supplied key, never a key cached from an earlier call. A grant whose declared
``project_id``/``project_binding_id`` do not match the attempt's own is refused before Boot is
even reached. This introduces no second Authority owner: the signing key verified against is
the identical one Binding/Boot already canonically establish for this Project; this module
only *reuses* that existing trust path for one more signed record kind, exactly as
``deployment_declaration.py`` and ``root_admission.py`` already do for theirs.

**F1 (continued) -- the grant also binds the real target and real scope, not only the
transport label.** Beyond project/Binding, a verified grant additionally names the exact
deployment target (``provider``/``deployment_id``/``instance_identity``), the exact SSH
endpoint (``host``/``port``/``user``/``probe_identity``), and the exact closed field/byte/line
limits it authorizes. :func:`require_grant_matches_attempt` independently compares every one
of those against the real ``target_identity``/``boundary`` an attempt is about to use, so a
grant genuinely issued for one target can never be silently reused against another merely
because both happen to be valid, current, and permit the identical transport.

**F1 (continued) -- enforcement moved into the one place that actually spawns a process.**
The first delivery's enforcement lived only in this module's own functions, which a caller
could simply not call -- constructing
:class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter` directly and handing
it to :func:`~manosube_agent_civilization.runtime.route.observe_runtime_target` bypassed every
check here entirely. ``SshRuntimeAdapter`` itself now *requires* a grant at construction time,
verifies it completely (signature, window, ``PREAUTHORIZED_UNATTENDED_SSH`` permission) before
accepting it, and independently re-matches it against the real target/Boundary immediately
before spawning ``ssh`` -- so there is no executable path, direct or otherwise, that reaches
the real subprocess without this exact gate. This is the identical "enforced in the route, and
again in the adapter, so neither site is ever the only one" defense-in-depth discipline
``network.py``'s own host-allowlist check already keeps (P15-R1-F1).

**Tool availability must not create Authority** (Issue #105 design requirement 3/6,
unchanged by this round's correction): a grant that does not name
``PREAUTHORIZED_UNATTENDED_SSH`` is never treated as permitting it merely because
:func:`classify_actions_dispatch` reports ``GITHUB_ACTIONS`` ``UNAVAILABLE``, and an
``UNKNOWN`` startup cause is never silently treated as confirmed quota exhaustion.

**Manual (Capability A) and unattended execution (Capability B's automatic half) share one
command.** :func:`render_manual_ssh_command` and ``SshRuntimeAdapter`` both build their SSH
invocation through the identical :func:`~manosube_agent_civilization.runtime.network.
render_ssh_command_argv` -- the exact command a Human is shown is, field for field, the exact
command this package would otherwise run unattended, so neither path can silently diverge from
the other.
"""

from __future__ import annotations

from collections.abc import Mapping
import shlex
from typing import Any

from manosube_agent_civilization.binding.signature import (
    SUPPORTED_SIGNATURE_ALGORITHM,
    verify_ed25519_signature,
)
from manosube_agent_civilization.boot import boot_project

from .engine import parse_utc_instant, require_valid_timestamp
from .errors import RuntimeRequirementError
from .identity import runtime_observation_grant_signing_payload
from .network import render_ssh_command_argv
from .types import SSH_PROBE_IDENTITIES

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

#: Bounds this module itself enforces on a grant's own declared ``max_output_bytes``/
#: ``max_lines`` -- a grant naming an absurd ceiling (zero, negative, or unboundedly large) is
#: refused exactly as an out-of-range Boundary ``timeout_seconds`` already would be. The upper
#: bound matches ``scripts/runtime_observation_probe.py``'s own per-path read ceiling
#: (``EXCERPT_MAX_READ_BYTES``), so a grant can never authorize more than the probe itself
#: would ever read in one bounded pass.
_MIN_MAX_OUTPUT_BYTES = 1
_MAX_MAX_OUTPUT_BYTES = 1_048_576
_MIN_MAX_LINES = 1
_MAX_MAX_LINES = 10_000

_REQUIRED_GRANT_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "grant_id",
        "project_id",
        "project_binding_id",
        "provider",
        "deployment_id",
        "instance_identity",
        "host",
        "port",
        "user",
        "probe_identity",
        "permitted_fields",
        "max_output_bytes",
        "max_lines",
        "permitted_transports",
        "issued_at",
        "expires_at",
        "decision_status",
        "signature",
    }
)


def _verify_grant_signature(grant: Mapping[str, Any], *, signing_key: Mapping[str, Any]) -> bool:
    """Whether *grant*'s own ``signature`` is a genuine Ed25519 signature, by the holder of
    *signing_key*, over exactly the canonical payload
    :func:`~manosube_agent_civilization.runtime.identity.
    runtime_observation_grant_signing_payload` derives from *grant*'s own adopted semantic
    fields -- the identical four-line composition
    :func:`~manosube_agent_civilization.runtime.deployment_declaration.
    verify_runtime_deployment_declaration_signature` already keeps for its own record kind,
    restated here (rather than imported) because that module is owned by a different
    Structural Review round and because this is the one additional, narrowly scoped place this
    package composes the shared primitive (PR #108 SR1 F1) -- never a second cryptography
    implementation; ``verify_ed25519_signature`` is called exactly once.

    *signing_key* must always be the ``human_authority_signing_key`` of the Project Binding a
    *fresh* ``boot_project`` call this module itself performs restores for the exact
    ``project_id``/``project_binding_id`` the current attempt is using -- never a caller-
    supplied copy, never a value read from the grant itself.

    ``False`` on any mismatch -- never an exception.
    """

    signature = grant.get("signature")
    if not isinstance(signature, Mapping):
        return False
    algorithm = signature.get("algorithm")
    if algorithm != SUPPORTED_SIGNATURE_ALGORITHM or signing_key.get("algorithm") != algorithm:
        return False
    if signature.get("key_id") != signing_key.get("key_id"):
        return False
    signature_hex = signature.get("value")
    public_key_hex = signing_key.get("public_key")
    if not isinstance(signature_hex, str) or not isinstance(public_key_hex, str):
        return False
    return verify_ed25519_signature(
        public_key_hex=public_key_hex,
        message=runtime_observation_grant_signing_payload(dict(grant)),
        signature_hex=signature_hex,
    )


def require_valid_grant(
    grant: Any, *, store: Any, project_id: str, project_binding_id: str
) -> dict[str, Any]:
    """Return *grant* as a plain ``dict``, proved to be a complete, closed, genuinely
    Human-Authority-signed bounded-SSH-observation grant, bound to exactly
    *project_id*/*project_binding_id* (PR #108 SR1 F1).

    Checked, in order: exact closed key set; ``schema_version``; non-empty string identity/
    scope fields; ``port`` an integer ``1..65535``; ``probe_identity`` one of
    :data:`~manosube_agent_civilization.runtime.types.SSH_PROBE_IDENTITIES`; a non-empty,
    unique ``permitted_fields`` list; ``max_output_bytes``/``max_lines`` within this module's
    own sane bounds; ``permitted_transports`` a non-empty list drawn only from
    :data:`PERMITTED_TRANSPORT_MODES`; a genuinely ordered ``issued_at``/``expires_at`` window;
    ``decision_status == "RATIFIED"`` -- all before any Store or Boot call, with zero I/O on a
    malformed grant. Only once every shape check passes does this function compare the grant's
    own declared ``project_id``/``project_binding_id`` against the caller's actual
    *project_id*/*project_binding_id* (refusing a scope mismatch with, again, zero Boot calls),
    and only then call ``boot_project`` fresh and verify the grant's own ``signature`` against
    the human_authority_signing_key that exact, live Boot restores.

    There is no default-admit path: a caller that wants an unratified, wrongly-scoped, or
    unsigned grant to be treated as valid gets a raised
    :class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError`, not a
    permissive decision value, exactly as every other requirement check in this package
    already keeps. Every ``boot_project`` failure (an unresolvable or inconsistent Project
    Binding) propagates unchanged, exactly as :mod:`~manosube_agent_civilization.runtime.route`
    already lets it.
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
    for key in (
        "grant_id",
        "project_id",
        "project_binding_id",
        "provider",
        "deployment_id",
        "instance_identity",
        "host",
        "user",
    ):
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
    permitted_fields = checked.get("permitted_fields")
    if (
        not isinstance(permitted_fields, list)
        or not permitted_fields
        or not all(isinstance(field, str) and field for field in permitted_fields)
        or len(set(permitted_fields)) != len(permitted_fields)
    ):
        raise RuntimeRequirementError(
            "runtime observation grant.permitted_fields must be a non-empty list of unique, "
            f"non-empty strings: {permitted_fields!r}"
        )
    max_output_bytes = checked.get("max_output_bytes")
    if (
        not isinstance(max_output_bytes, int)
        or isinstance(max_output_bytes, bool)
        or not (_MIN_MAX_OUTPUT_BYTES <= max_output_bytes <= _MAX_MAX_OUTPUT_BYTES)
    ):
        raise RuntimeRequirementError(
            "runtime observation grant.max_output_bytes must be an integer "
            f"{_MIN_MAX_OUTPUT_BYTES}..{_MAX_MAX_OUTPUT_BYTES}: {max_output_bytes!r}"
        )
    max_lines = checked.get("max_lines")
    if (
        not isinstance(max_lines, int)
        or isinstance(max_lines, bool)
        or not (_MIN_MAX_LINES <= max_lines <= _MAX_MAX_LINES)
    ):
        raise RuntimeRequirementError(
            f"runtime observation grant.max_lines must be an integer {_MIN_MAX_LINES}.."
            f"{_MAX_MAX_LINES}: {max_lines!r}"
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
    if checked.get("decision_status") != "RATIFIED":
        raise RuntimeRequirementError(
            "runtime observation grant.decision_status must be 'RATIFIED': "
            f"{checked.get('decision_status')!r}"
        )
    checked["permitted_fields"] = list(permitted_fields)
    checked["permitted_transports"] = list(permitted_transports)

    # Scope binding (PR #108 SR1 F1): a grant genuinely issued for one Project/Binding must
    # never be accepted for another, however valid its signature is for its own scope -- and
    # this comparison runs before any Store or Boot call, so a wrong-scope grant is refused
    # with zero I/O.
    if checked["project_id"] != project_id or checked["project_binding_id"] != project_binding_id:
        raise RuntimeRequirementError(
            "runtime observation grant is scoped to a different project/Project Binding than "
            f"this attempt: grant names {checked['project_id']!r}/"
            f"{checked['project_binding_id']!r}, attempt uses {project_id!r}/"
            f"{project_binding_id!r}"
        )

    # Authenticity (PR #108 SR1 F1): a fresh Boot restore of the exact Project Binding this
    # attempt is using, and the grant's own signature verified against that Binding's own
    # human_authority_signing_key -- never a caller-supplied key, never a cached one.
    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    signing_key = boot_context.project_binding.get("human_authority_signing_key")
    if not isinstance(signing_key, Mapping):
        raise RuntimeRequirementError(
            "the Boot-restored project_binding carries no readable "
            "human_authority_signing_key against which to verify this grant's signature"
        )
    if not _verify_grant_signature(checked, signing_key=dict(signing_key)):
        raise RuntimeRequirementError(
            f"runtime observation grant {checked['grant_id']!r} does not carry a genuine "
            "Human Authority signature over its own declared scope -- refusing rather than "
            "trusting a self-asserted decision_status"
        )
    return checked


def require_grant_permits_transport(
    grant: Mapping[str, Any],
    transport: str,
    *,
    store: Any,
    project_id: str,
    project_binding_id: str,
) -> dict[str, Any]:
    """Return *grant*, proved valid (see :func:`require_valid_grant`) and proved to permit
    *transport*.

    The one place "tool availability must not create Authority" is actually enforced: a
    caller that merely *can* reach a target over SSH is refused here unless a genuinely
    signed, correctly scoped grant already named that exact mode for that exact target --
    never because Actions happened to be unavailable at the moment of the attempt.
    """

    checked = require_valid_grant(
        grant, store=store, project_id=project_id, project_binding_id=project_binding_id
    )
    if transport not in PERMITTED_TRANSPORT_MODES:
        raise RuntimeRequirementError(f"transport is not a recognized transport mode: {transport!r}")
    if transport not in checked["permitted_transports"]:
        raise RuntimeRequirementError(
            f"runtime observation grant {checked['grant_id']!r} does not permit transport "
            f"{transport!r} -- only {checked['permitted_transports']!r}"
        )
    return checked


def require_grant_not_expired(
    grant: Mapping[str, Any],
    *,
    store: Any,
    project_id: str,
    project_binding_id: str,
    now: str,
) -> dict[str, Any]:
    """Return *grant*, proved valid and proved still within its own declared validity window
    at *now* -- a caller-supplied canonical UTC timestamp. This module calls no clock of its
    own, exactly as every other time-window check in this package already takes an explicit
    instant rather than reading one, so a test (or a real caller) controls what "now" means."""

    checked = require_valid_grant(
        grant, store=store, project_id=project_id, project_binding_id=project_binding_id
    )
    now_instant = parse_utc_instant(require_valid_timestamp(now, "now"), "now")
    issued_at_instant = parse_utc_instant(checked["issued_at"], "issued_at")
    expires_at_instant = parse_utc_instant(checked["expires_at"], "expires_at")
    if not (issued_at_instant <= now_instant <= expires_at_instant):
        raise RuntimeRequirementError(
            f"runtime observation grant {checked['grant_id']!r} is not valid at {now!r} -- its "
            f"own window is [{checked['issued_at']!r}, {checked['expires_at']!r}]"
        )
    return checked


def require_grant_matches_attempt(
    grant: Mapping[str, Any],
    *,
    target_identity: Mapping[str, Any],
    boundary: Mapping[str, Any],
) -> dict[str, Any]:
    """Require an already-*proved-valid* *grant* to bind exactly the real target and real
    scope *this* attempt is about to use, and return it unchanged (PR #108 SR1 F1).

    A grant that is otherwise valid, current, and permits the right transport must still be
    refused if it was issued for a *different* target or a broader/different field scope than
    the attempt's own real ``target_identity``/``boundary`` declare -- the exact gap the first
    delivery's own integration test demonstrated (a different-project grant accepted for the
    actual project's target). Every comparison here is exact-match or subset, never a prefix,
    substring, or best-effort heuristic.
    """

    endpoint = boundary.get("endpoint")
    if not isinstance(endpoint, Mapping):
        raise RuntimeRequirementError(f"boundary.endpoint must be an explicit mapping: {endpoint!r}")
    for field in ("host", "port", "user", "probe_identity"):
        if grant.get(field) != endpoint.get(field):
            raise RuntimeRequirementError(
                f"runtime observation grant {grant.get('grant_id')!r} does not match this "
                f"attempt's own boundary.endpoint.{field}: grant names {grant.get(field)!r}, "
                f"attempt uses {endpoint.get(field)!r}"
            )
    for field in ("provider", "deployment_id", "instance_identity"):
        if grant.get(field) != target_identity.get(field):
            raise RuntimeRequirementError(
                f"runtime observation grant {grant.get('grant_id')!r} does not match this "
                f"attempt's own target_identity.{field}: grant names {grant.get(field)!r}, "
                f"attempt uses {target_identity.get(field)!r}"
            )
    # boundary may already be a deep-frozen copy by the time this runs (route.py hands the
    # adapter frozen structures -- lists become tuples), so a sequence is accepted generally
    # rather than requiring a literal ``list``.
    permitted_fields = boundary.get("permitted_fields")
    if not isinstance(permitted_fields, list | tuple) or not set(permitted_fields) <= set(
        grant.get("permitted_fields", [])
    ):
        raise RuntimeRequirementError(
            f"runtime observation grant {grant.get('grant_id')!r} does not authorize every "
            f"field this attempt's own boundary.permitted_fields names: {permitted_fields!r} "
            f"is not a subset of {grant.get('permitted_fields')!r}"
        )
    return dict(grant)


def render_manual_ssh_command(
    grant: Mapping[str, Any],
    *,
    store: Any,
    project_id: str,
    project_binding_id: str,
    now: str,
) -> str:
    """Return the exact, copy/paste-able command string for a Human operator to run for
    *grant*'s own bounded probe (Issue #105 Capability A).

    Built through the identical :func:`~manosube_agent_civilization.runtime.network.
    render_ssh_command_argv` the real adapter itself calls for grant-gated unattended
    execution, so the attended and unattended paths can never silently diverge. Refuses a
    grant that does not genuinely verify (see :func:`require_valid_grant`), does not permit
    ``MANUAL_SSH``, or is not currently within its own validity window -- rendering a command
    is itself part of what this module gates, never a harmless preview available regardless of
    authorization.
    """

    checked = require_grant_permits_transport(
        grant,
        "MANUAL_SSH",
        store=store,
        project_id=project_id,
        project_binding_id=project_binding_id,
    )
    require_grant_not_expired(
        checked, store=store, project_id=project_id, project_binding_id=project_binding_id, now=now
    )
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
    store: Any,
    project_id: str,
    project_binding_id: str,
    now: str,
) -> str:
    """Return the one transport this call may actually use.

    Actions is preferred (the adopted operational-continuity design): used whenever
    *actions_status* is ``"AVAILABLE"`` and no explicit manual selection overrides it --
    dispatching an Actions job is itself an orthogonal, already-authorized GitHub-permissions
    act, and (per F2's own correction) a transport label selected here is never, by itself,
    permission to spawn a local SSH subprocess; only :class:`~manosube_agent_civilization.
    runtime.adapter.SshRuntimeAdapter`'s own construction-time grant gate is. Otherwise
    *requested_transport* is used, but only once proved both permitted by a genuinely verified
    *grant* and current -- Actions being unavailable never by itself escalates to a transport
    the grant does not name (``FALLBACK_CREATES_AUTHORITY=false``), and an operator must make
    an explicit selection rather than one being chosen automatically when Actions cannot run.
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
    require_grant_permits_transport(
        grant,
        requested_transport,
        store=store,
        project_id=project_id,
        project_binding_id=project_binding_id,
    )
    require_grant_not_expired(
        grant, store=store, project_id=project_id, project_binding_id=project_binding_id, now=now
    )
    return requested_transport


__all__ = [
    "DISPATCH_STATUSES",
    "PERMITTED_TRANSPORT_MODES",
    "classify_actions_dispatch",
    "render_manual_ssh_command",
    "require_grant_matches_attempt",
    "require_grant_not_expired",
    "require_grant_permits_transport",
    "require_valid_grant",
    "select_transport",
]
