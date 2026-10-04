"""The Actions-independent local control entry point for Runtime Observation transports
(Issue #105, transport-independent runtime observation; mode-specific dispatch corrected by
PR #108 Structural Review Round 1, F2; real execution and automatic fallback added by
Structural Review Round 2, SR2-F1/SR2-F3(D); ``import-output`` routed through the real
canonical route, and a genuinely independent fallback controller added, by Structural Review
Round 3, SR3-F1/SR3-F3(A)).

```text
subcommand           what it answers
-----------          ----------------------------------------------------------------
classify-dispatch    is a GitHub Actions dispatch attempt AVAILABLE / UNAVAILABLE / UNKNOWN?
render-command        the exact copy/paste SSH command for a Human operator (Capability A)
import-output          validate a Human-captured transcript through the real canonical route
                        (observe_runtime_target, via CapturedProbeReportRuntimeAdapter) --
                        bound by the grant's own permitted_fields/max_lines/max_output_bytes,
                        the real target_identity, and a real envelope/receipt/Evidence
                        hand-off, never a second, looser, unbound parser (SR3-F3(A))
observe               perform the bounded observation now, through the real canonical route --
                        for GITHUB_ACTIONS (a real Actions job a Human already dispatched) and
                        PREAUTHORIZED_UNATTENDED_SSH (a grant naming it explicitly) alike;
                        MANUAL_SSH is refused outright -- that mode's own authorization act is
                        a Human running the rendered command themselves (SR2-F1)
run-controller        the one genuinely independent, bounded Actions-to-SSH fallback
                        controller -- polls its own injected sequence of observed dispatch
                        facts up to a bounded start deadline and falls back to
                        PREAUTHORIZED_UNATTENDED_SSH only once that bound is exhausted AND the
                        grant itself already, explicitly preauthorizes it; no per-attempt
                        Human transport choice either way (SR3-F1)
```

None of these subcommands make this script "the" Runtime Observation owner: every one of
them is a thin CLI wrapper around
:mod:`manosube_agent_civilization.runtime.transport_control` and
:func:`manosube_agent_civilization.runtime.observe_runtime_target` -- the identical canonical
functions a GitHub Actions workflow step, a Human's own terminal, or a grant-gated unattended
controller all call. This script holds no credential, makes no network call of its own (the
``observe`` subcommand's own network/SSH call is made by the Runtime package it invokes, not
by this file), and never deploys, provisions, or installs anything. A downstream project that
actually binds a real target supplies its own Store root, project identity, and grant --
nothing here is production-ready on its own, and nothing here authorizes an actual
private/production VPS connection by existing (Issue #105 adoption comment 5975681963).

**PR #108 Structural Review Round 1, F2 -- a transport label is never, by itself, permission
to execute.** The first delivery's own ``observe`` subcommand constructed
:class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter` unconditionally after
selecting *any* mode, so an operator requesting ``MANUAL_SSH`` (which must only ever render a
command for a Human to run themselves) still reached the real executable adapter. This
subcommand refuses outright whenever the selected transport is ``MANUAL_SSH`` -- the one mode
a Human must run themselves via ``render-command``.

**PR #108 Structural Review Round 2, SR2-F1 -- GITHUB_ACTIONS now actually executes too, and
an operator may opt into automatic unattended fallback.** Round 1 additionally refused every
transport *except* ``PREAUTHORIZED_UNATTENDED_SSH``, which left ``GITHUB_ACTIONS``
render-only -- not what the whole point of transport independence requires: a real Actions job
a Human already dispatched is itself that attempt's own authorization act, exactly as a real
unattended grant is for the other mode, so this subcommand now executes the identical real
observation for either one (never for ``MANUAL_SSH``, whose authorization act is a Human
running a command themselves). ``--allow-automatic-fallback`` additionally opts into
:func:`~manosube_agent_civilization.runtime.transport_control.
select_transport_with_automatic_fallback`: once Actions is *confirmed* ``UNAVAILABLE`` (never
merely ``UNKNOWN``) and no explicit ``--requested-transport`` was given, a grant that already,
explicitly names ``PREAUTHORIZED_UNATTENDED_SSH`` resolves to it with no further per-attempt
Human selection -- the authority already fully pre-exists in that signed grant; only the
mechanical trigger is automated (``FALLBACK_CREATES_AUTHORITY=false`` still holds: this flag
changes nothing about what a grant may authorize, only who notices that it already did).
``--attempt-already-satisfied`` threads a caller's own bounded, local attempt-correlation fact
through to that same function, refusing a second, duplicate unattended execution of an attempt
the caller already knows reached a transport; this module owns no attempt ledger of its own
(see :func:`~manosube_agent_civilization.runtime.transport_control.
compute_runtime_observation_attempt_id`, surfaced in this subcommand's own output).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, TextIO

from manosube_agent_civilization.runtime import observe_runtime_target, transport_control as tc
from manosube_agent_civilization.runtime.adapter import (
    CapturedProbeReportRuntimeAdapter,
    SshRuntimeAdapter,
)
from manosube_agent_civilization.store.file_store import FileStateStore

#: The maximum number of bytes ``import-output`` will ever read from a Human-captured report
#: file (PR #108 SR2-F3(D)) -- matches this module's own grant-field bound
#: (``transport_control._MAX_MAX_OUTPUT_BYTES``) so a captured transcript can never itself
#: become an unbounded read, however large the file on disk happens to be.
_IMPORT_OUTPUT_MAX_BYTES = 1_048_576


def _load_json_file(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def _write_json(stream: TextIO, payload: dict[str, Any]) -> None:
    json.dump(payload, stream, indent=2, sort_keys=True)
    stream.write("\n")


def _cmd_classify_dispatch(args: argparse.Namespace) -> int:
    status = tc.classify_actions_dispatch(
        dispatched=args.dispatched,
        runner_allocated=args.runner_allocated,
        start_deadline_exceeded=args.start_deadline_exceeded,
    )
    _write_json(sys.stdout, {"dispatch_status": status})
    return 0


def _cmd_render_command(args: argparse.Namespace) -> int:
    grant = _load_json_file(args.grant_file)
    store = FileStateStore(Path(args.store_root), schema_root=Path(args.schema_root))
    try:
        command = tc.render_manual_ssh_command(
            grant,
            store=store,
            project_id=args.project_id,
            project_binding_id=args.project_binding_id,
            now=args.now,
        )
    except Exception as error:
        _write_json(sys.stdout, {"ok": False, "error": str(error)})
        return 1
    _write_json(sys.stdout, {"ok": True, "command": command})
    return 0


def _cmd_import_output(args: argparse.Namespace) -> int:
    """Validate a probe report a Human already captured by running the rendered command
    themselves and pasting its stdout back, through the real canonical
    :func:`~manosube_agent_civilization.runtime.observe_runtime_target` route -- never a
    second, parallel, unbound return path (PR #108 Structural Review Round 3, SR3-F3(A)).

    **The gap the first three rounds left.** Rounds 1-2 parsed the captured transcript through
    the identical closed-shape report parser the real adapter uses and compared its digest
    against the grant's own signed value, then stopped: the grant's own
    ``max_output_bytes``/``max_lines``/``permitted_fields`` bounds were never applied, the
    report was never bound to a real ``target_identity``/request, nothing was redacted, and no
    canonical envelope/receipt/Evidence hand-off was ever produced. A captured report naming
    the wrong target, an unpermitted field, or a self-reported line count that lied about the
    real excerpt it shipped was still echoed back as ``{"ok": true, ...}``.

    **The fix.** This subcommand now constructs
    :class:`~manosube_agent_civilization.runtime.adapter.CapturedProbeReportRuntimeAdapter` --
    the grant verified exactly as :class:`~manosube_agent_civilization.runtime.adapter.
    SshRuntimeAdapter` itself verifies it, restricted to exactly ``MANUAL_SSH`` -- and passes it
    to the real ``observe_runtime_target``, with a real ``target_identity`` and Boundary this
    subcommand now requires as explicit arguments. The captured bytes are classified through
    the identical ``_classify_probe_result`` a live subprocess result is classified through:
    wrong target, unpermitted field, lying counters, and a byte/line cap below this
    subcommand's own fixed read ceiling all now surface as the real, bounded
    ``observation_outcome`` (typically ``MALFORMED``/``IDENTITY_MISMATCH``) a genuine envelope
    and receipt record -- never a forged ``ok: true``. ``ok: false`` here means only that the
    route itself could not even be reached (the grant does not verify, or the declared
    target/Boundary shape itself is invalid) -- exactly the same split
    :func:`_cmd_observe` already keeps.

    The file read itself is still capped at :data:`_IMPORT_OUTPUT_MAX_BYTES`, refusing outright
    rather than silently truncating a larger file -- a bound this subcommand enforces before
    the captured bytes ever reach the adapter.
    """

    try:
        with open(args.report_file, "rb") as stream:
            raw_bytes = stream.read(_IMPORT_OUTPUT_MAX_BYTES + 1)
    except OSError as error:
        _write_json(sys.stdout, {"ok": False, "error": f"unreadable report file: {error}"})
        return 1
    if len(raw_bytes) > _IMPORT_OUTPUT_MAX_BYTES:
        _write_json(
            sys.stdout,
            {
                "ok": False,
                "error": f"captured report file exceeds {_IMPORT_OUTPUT_MAX_BYTES} bytes -- "
                "refusing rather than silently truncate it",
            },
        )
        return 1

    grant = _load_json_file(args.grant_file)
    target_identity = _load_json_file(args.target_identity_file)
    store = FileStateStore(Path(args.store_root), schema_root=Path(args.schema_root))

    try:
        adapter = CapturedProbeReportRuntimeAdapter(
            captured_stdout=raw_bytes,
            grant=grant,
            store=store,
            project_id=args.project_id,
            project_binding_id=args.project_binding_id,
            now=args.now,
        )
    except Exception as error:
        _write_json(sys.stdout, {"ok": False, "error": str(error)})
        return 1

    permitted_fields = args.permitted_fields.split(",")
    boundary = {
        "observation_method": "SSH_EXEC_BOUNDED",
        "endpoint": {
            "host": grant["host"],
            "port": grant["port"],
            "user": grant["user"],
            "probe_identity": grant["probe_identity"],
        },
        "permitted_fields": permitted_fields,
        "time_window": {
            "issued_at": grant["issued_at"],
            "expires_at": grant["expires_at"],
        },
        "network_scope": {"allowed_hosts": [grant["host"]]},
        "timeout_seconds": args.timeout_seconds,
        "redaction_fields": [],
    }

    try:
        result = observe_runtime_target(
            store,
            project_id=args.project_id,
            project_binding_id=args.project_binding_id,
            target_identity=target_identity,
            boundary=boundary,
            adapter=adapter,
            observed_at=args.now,
        )
    except Exception as error:
        _write_json(sys.stdout, {"ok": False, "error": str(error)})
        return 1
    _write_json(
        sys.stdout,
        {
            "ok": True,
            "transport": "MANUAL_SSH",
            "envelope_id": result["envelope"]["runtime_observation_envelope_id"],
            "observation_outcome": result["envelope"]["observation_outcome"],
            "receipt_status": result["receipt"].status,
            "observed_fields": result["envelope"]["observed_fields"],
        },
    )
    return 0


def _cmd_observe(args: argparse.Namespace) -> int:
    grant = _load_json_file(args.grant_file)
    target_identity = _load_json_file(args.target_identity_file)
    store = FileStateStore(Path(args.store_root), schema_root=Path(args.schema_root))

    attempt_id = tc.compute_runtime_observation_attempt_id(
        grant_id=str(grant.get("grant_id")), actions_status=args.actions_status, now=args.now
    )

    try:
        # PR #108 Structural Review Round 2, SR2-F1: automatic unattended fallback is an
        # explicit opt-in (``--allow-automatic-fallback``), never the default behavior of this
        # subcommand, and only ever engages when Actions is *confirmed* unavailable and no
        # explicit ``--requested-transport`` was given -- exactly
        # ``select_transport_with_automatic_fallback``'s own closed preconditions.
        if (
            args.allow_automatic_fallback
            and args.requested_transport is None
            and args.actions_status == "UNAVAILABLE"
        ):
            transport = tc.select_transport_with_automatic_fallback(
                actions_status=args.actions_status,
                requested_transport=args.requested_transport,
                grant=grant,
                store=store,
                project_id=args.project_id,
                project_binding_id=args.project_binding_id,
                now=args.now,
                attempt_already_satisfied=args.attempt_already_satisfied,
            )
        else:
            transport = tc.select_transport(
                actions_status=args.actions_status,
                requested_transport=args.requested_transport,
                grant=grant,
                store=store,
                project_id=args.project_id,
                project_binding_id=args.project_binding_id,
                now=args.now,
            )
    except Exception as error:
        _write_json(sys.stdout, {"ok": False, "error": str(error), "attempt_id": attempt_id})
        return 1

    if transport == "MANUAL_SSH":
        # PR #108 SR1 F2 (restated by SR2-F1): a transport label is never, by itself,
        # permission to execute. MANUAL_SSH's own entire authorization act is a Human running
        # the command render-command already gave them -- this subcommand never executes it.
        _write_json(
            sys.stdout,
            {
                "ok": False,
                "error": (
                    "selected transport is 'MANUAL_SSH' -- this subcommand never executes it. "
                    "Use render-command instead; a Human must run the rendered command "
                    "themselves."
                ),
                "selected_transport": transport,
                "attempt_id": attempt_id,
            },
        )
        return 1

    # PR #108 SR2-F1: both remaining transports -- a real, already-dispatched Actions job, and
    # a grant-gated unattended attempt -- now actually execute through this identical adapter.
    # Which one it is decides *which signed permission the grant must carry*, nothing else
    # about how the observation itself proceeds.
    try:
        adapter = SshRuntimeAdapter(
            grant=grant,
            store=store,
            project_id=args.project_id,
            project_binding_id=args.project_binding_id,
            now=args.now,
            transport=transport,
        )
    except Exception as error:
        _write_json(sys.stdout, {"ok": False, "error": str(error), "attempt_id": attempt_id})
        return 1

    permitted_fields = args.permitted_fields.split(",")
    boundary = {
        "observation_method": "SSH_EXEC_BOUNDED",
        "endpoint": {
            "host": grant["host"],
            "port": grant["port"],
            "user": grant["user"],
            "probe_identity": grant["probe_identity"],
        },
        "permitted_fields": permitted_fields,
        "time_window": {
            "issued_at": grant["issued_at"],
            "expires_at": grant["expires_at"],
        },
        "network_scope": {"allowed_hosts": [grant["host"]]},
        "timeout_seconds": args.timeout_seconds,
        "redaction_fields": [],
    }

    try:
        result = observe_runtime_target(
            store,
            project_id=args.project_id,
            project_binding_id=args.project_binding_id,
            target_identity=target_identity,
            boundary=boundary,
            adapter=adapter,
            observed_at=args.now,
        )
    except Exception as error:
        _write_json(sys.stdout, {"ok": False, "error": str(error), "attempt_id": attempt_id})
        return 1
    _write_json(
        sys.stdout,
        {
            "ok": True,
            "transport": transport,
            "attempt_id": attempt_id,
            "envelope_id": result["envelope"]["runtime_observation_envelope_id"],
            "observation_outcome": result["envelope"]["observation_outcome"],
            "receipt_status": result["receipt"].status,
            # PR #108 SR2-F3(D): the actually-acquired, bounded, already-redacted observed
            # content is now part of this subcommand's own output -- never only an identifier
            # a caller would have to separately resolve against the Store to ever actually see.
            "observed_fields": result["envelope"]["observed_fields"],
        },
    )
    return 0


def _dispatch_status_sequence_provider(statuses: list[str]) -> Any:
    """Return a zero-argument callable that pops through *statuses* in order, repeating the
    final entry once exhausted -- the one shape this CLI itself can exercise
    :func:`~manosube_agent_civilization.runtime.transport_control.
    resolve_bounded_actions_fallback`'s own injected ``dispatch_status_provider`` with: a
    sequence of *already observed* dispatch facts (PR #108 SR3-F1's own "consumes observed
    dispatch/start facts" input shape), never a real live GitHub Actions poll -- this script
    holds no GitHub credential and makes no network call of its own, unchanged from every
    other subcommand here."""

    state = {"index": 0}

    def _provider() -> str:
        index = min(state["index"], len(statuses) - 1)
        state["index"] += 1
        return statuses[index]

    return _provider


def _cmd_run_controller(args: argparse.Namespace) -> int:
    """Run the one genuinely independent Actions-to-SSH fallback controller SR3-F1 requires --
    never a caller-driven selector dressed up as one (PR #108 Structural Review Round 3).

    Unlike ``observe --allow-automatic-fallback`` (SR2-F1), which only ever accepted a single,
    already-decided ``--actions-status`` string, this subcommand hands
    :func:`~manosube_agent_civilization.runtime.transport_control.
    resolve_bounded_actions_fallback` its own bounded polling loop over a sequence of observed
    dispatch facts (``--dispatch-status-sequence``, comma-separated, repeating its own final
    entry once exhausted) -- the controller itself decides when a bounded start deadline
    (``--max-polls``) has been reached, never a Human choosing a transport per attempt. A
    stable ``operation_id`` (derived from the grant and the target's own stable coordinates
    alone -- never ``actions_status`` or ``now``) is computed once and reused whether this
    call defers to Actions or falls back to SSH, and ``--claim-already-satisfied`` threads a
    caller's own bounded, local correlation fact through to refuse a second, duplicate
    execution of the identical operation -- this subcommand itself keeps no ledger of its own
    across separate invocations.
    """

    grant = _load_json_file(args.grant_file)
    target_identity = _load_json_file(args.target_identity_file)
    store = FileStateStore(Path(args.store_root), schema_root=Path(args.schema_root))

    operation_id = tc.compute_runtime_observation_operation_id(
        grant_id=str(grant.get("grant_id")),
        provider=str(target_identity.get("provider")),
        deployment_id=str(target_identity.get("deployment_id")),
        instance_identity=str(target_identity.get("instance_identity")),
    )

    try:
        decision = tc.resolve_bounded_actions_fallback(
            operation_id=operation_id,
            dispatch_status_provider=_dispatch_status_sequence_provider(
                args.dispatch_status_sequence.split(",")
            ),
            max_polls=args.max_polls,
            grant=grant,
            store=store,
            project_id=args.project_id,
            project_binding_id=args.project_binding_id,
            now=args.now,
            already_satisfied=args.claim_already_satisfied,
            poll_interval_seconds=0.0,
            sleep_fn=lambda _seconds: None,
        )
    except Exception as error:
        _write_json(
            sys.stdout, {"ok": False, "error": str(error), "operation_id": operation_id}
        )
        return 1

    if decision != "FALLBACK_AUTHORIZED":
        # PR #108 SR3-F1: ACTIONS_AVAILABLE_DEFER, FALLBACK_REFUSED_NO_GRANT, and
        # ALREADY_SATISFIED all reach here with zero target calls -- this controller only ever
        # executes SSH on FALLBACK_AUTHORIZED, never speculatively.
        _write_json(
            sys.stdout,
            {"ok": True, "decision": decision, "operation_id": operation_id, "executed": False},
        )
        return 0

    try:
        adapter = SshRuntimeAdapter(
            grant=grant,
            store=store,
            project_id=args.project_id,
            project_binding_id=args.project_binding_id,
            now=args.now,
            transport="PREAUTHORIZED_UNATTENDED_SSH",
        )
    except Exception as error:
        _write_json(
            sys.stdout, {"ok": False, "error": str(error), "operation_id": operation_id}
        )
        return 1

    permitted_fields = args.permitted_fields.split(",")
    boundary = {
        "observation_method": "SSH_EXEC_BOUNDED",
        "endpoint": {
            "host": grant["host"],
            "port": grant["port"],
            "user": grant["user"],
            "probe_identity": grant["probe_identity"],
        },
        "permitted_fields": permitted_fields,
        "time_window": {
            "issued_at": grant["issued_at"],
            "expires_at": grant["expires_at"],
        },
        "network_scope": {"allowed_hosts": [grant["host"]]},
        "timeout_seconds": args.timeout_seconds,
        "redaction_fields": [],
    }

    try:
        result = observe_runtime_target(
            store,
            project_id=args.project_id,
            project_binding_id=args.project_binding_id,
            target_identity=target_identity,
            boundary=boundary,
            adapter=adapter,
            observed_at=args.now,
        )
    except Exception as error:
        _write_json(
            sys.stdout, {"ok": False, "error": str(error), "operation_id": operation_id}
        )
        return 1
    _write_json(
        sys.stdout,
        {
            "ok": True,
            "decision": decision,
            "operation_id": operation_id,
            "executed": True,
            "transport": "PREAUTHORIZED_UNATTENDED_SSH",
            "envelope_id": result["envelope"]["runtime_observation_envelope_id"],
            "observation_outcome": result["envelope"]["observation_outcome"],
            "receipt_status": result["receipt"].status,
            "observed_fields": result["envelope"]["observed_fields"],
        },
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify = subparsers.add_parser(
        "classify-dispatch", help="classify a single GitHub Actions dispatch attempt"
    )
    classify.add_argument("--dispatched", action="store_true")
    classify.add_argument("--runner-allocated", action="store_true")
    classify.add_argument("--start-deadline-exceeded", action="store_true")
    classify.set_defaults(func=_cmd_classify_dispatch)

    render = subparsers.add_parser(
        "render-command", help="render the manual SSH command a grant authorizes"
    )
    render.add_argument("--grant-file", required=True)
    render.add_argument("--store-root", required=True)
    render.add_argument("--schema-root", required=True)
    render.add_argument("--project-id", required=True)
    render.add_argument("--project-binding-id", required=True)
    render.add_argument("--now", required=True)
    render.set_defaults(func=_cmd_render_command)

    import_output = subparsers.add_parser(
        "import-output",
        help=(
            "validate a Human-captured probe report through the real canonical route "
            "(envelope/receipt/Evidence), restricted to the MANUAL_SSH transport"
        ),
    )
    import_output.add_argument("--report-file", required=True)
    import_output.add_argument("--grant-file", required=True)
    import_output.add_argument("--target-identity-file", required=True)
    import_output.add_argument("--store-root", required=True)
    import_output.add_argument("--schema-root", required=True)
    import_output.add_argument("--project-id", required=True)
    import_output.add_argument("--project-binding-id", required=True)
    import_output.add_argument("--permitted-fields", required=True, help="comma-separated field names")
    import_output.add_argument("--now", required=True)
    import_output.add_argument("--timeout-seconds", type=int, default=30)
    import_output.set_defaults(func=_cmd_import_output)

    observe = subparsers.add_parser(
        "observe",
        help=(
            "perform the bounded observation now, through the real canonical route, for "
            "GITHUB_ACTIONS or PREAUTHORIZED_UNATTENDED_SSH -- MANUAL_SSH is always refused"
        ),
    )
    observe.add_argument("--grant-file", required=True)
    observe.add_argument("--target-identity-file", required=True)
    observe.add_argument("--store-root", required=True)
    observe.add_argument("--schema-root", required=True)
    observe.add_argument("--project-id", required=True)
    observe.add_argument("--project-binding-id", required=True)
    observe.add_argument("--permitted-fields", required=True, help="comma-separated field names")
    observe.add_argument("--now", required=True)
    # int, not float: this repository's own canonical JSON state (v0.1) prohibits
    # floating-point values outright, and this value is committed verbatim into the
    # Boundary's own runtime_observation_envelope -- a float here crashed the committer
    # (incidentally discovered while testing this round's own corrections, fixed here since
    # it is a one-line type fix in a file already in scope this round, not a new finding
    # requiring separate adoption).
    observe.add_argument("--timeout-seconds", type=int, default=30)
    observe.add_argument(
        "--actions-status", choices=sorted(tc.DISPATCH_STATUSES), default="UNAVAILABLE"
    )
    observe.add_argument(
        "--requested-transport", choices=sorted(tc.PERMITTED_TRANSPORT_MODES), default=None
    )
    # PR #108 SR2-F1: opt-in automatic unattended fallback, and the caller-supplied attempt
    # correlation fact that guards against a second, duplicate unattended execution.
    observe.add_argument("--allow-automatic-fallback", action="store_true")
    observe.add_argument("--attempt-already-satisfied", action="store_true")
    observe.set_defaults(func=_cmd_observe)

    run_controller = subparsers.add_parser(
        "run-controller",
        help=(
            "run the genuinely independent, bounded Actions-to-SSH fallback controller "
            "(SR3-F1) -- polls its own injected dispatch-fact sequence up to a bounded "
            "start deadline, and falls back to PREAUTHORIZED_UNATTENDED_SSH only once the "
            "grant itself already, explicitly preauthorizes it"
        ),
    )
    run_controller.add_argument("--grant-file", required=True)
    run_controller.add_argument("--target-identity-file", required=True)
    run_controller.add_argument("--store-root", required=True)
    run_controller.add_argument("--schema-root", required=True)
    run_controller.add_argument("--project-id", required=True)
    run_controller.add_argument("--project-binding-id", required=True)
    run_controller.add_argument(
        "--permitted-fields", required=True, help="comma-separated field names"
    )
    run_controller.add_argument("--now", required=True)
    run_controller.add_argument("--timeout-seconds", type=int, default=30)
    run_controller.add_argument(
        "--dispatch-status-sequence",
        required=True,
        help=(
            "comma-separated sequence of observed GitHub Actions dispatch statuses "
            f"(one of {sorted(tc.DISPATCH_STATUSES)}), polled in order; the controller's own "
            "bounded loop repeats the final entry once exhausted"
        ),
    )
    run_controller.add_argument("--max-polls", type=int, default=5)
    run_controller.add_argument("--claim-already-satisfied", action="store_true")
    run_controller.set_defaults(func=_cmd_run_controller)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
