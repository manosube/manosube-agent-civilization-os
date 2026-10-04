"""The Actions-independent local control entry point for Runtime Observation transports
(Issue #105, transport-independent runtime observation).

```text
subcommand           what it answers
-----------          ----------------------------------------------------------------
classify-dispatch    is a GitHub Actions dispatch attempt AVAILABLE / UNAVAILABLE / UNKNOWN?
render-command        the exact copy/paste SSH command for a Human operator (Capability A)
import-output          validate/normalize output a Human already captured and pasted back
observe               perform the bounded observation now, through the real canonical route
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
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, TextIO

from manosube_agent_civilization.runtime import observe_runtime_target, transport_control as tc
from manosube_agent_civilization.runtime.adapter import SshRuntimeAdapter
from manosube_agent_civilization.store.file_store import FileStateStore


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
    try:
        command = tc.render_manual_ssh_command(grant, now=args.now)
    except Exception as error:
        _write_json(sys.stdout, {"ok": False, "error": str(error)})
        return 1
    _write_json(sys.stdout, {"ok": True, "command": command})
    return 0


def _cmd_import_output(args: argparse.Namespace) -> int:
    """Validate and normalize a probe report a Human already captured by running the
    rendered command themselves and pasting its stdout back -- never re-executes anything."""

    try:
        report = _load_json_file(args.report_file)
    except (OSError, json.JSONDecodeError) as error:
        _write_json(sys.stdout, {"ok": False, "error": f"unreadable report file: {error}"})
        return 1
    if not isinstance(report, dict) or "ok" not in report:
        _write_json(sys.stdout, {"ok": False, "error": "report is not the one closed probe shape"})
        return 1
    _write_json(sys.stdout, {"ok": True, "imported_report": report})
    return 0


def _cmd_observe(args: argparse.Namespace) -> int:
    grant = _load_json_file(args.grant_file)
    target_identity = _load_json_file(args.target_identity_file)

    try:
        transport = tc.select_transport(
            actions_status=args.actions_status,
            requested_transport=args.requested_transport,
            grant=grant,
            now=args.now,
        )
        checked_grant = tc.require_grant_not_expired(grant, now=args.now)
    except Exception as error:
        _write_json(sys.stdout, {"ok": False, "error": str(error)})
        return 1

    permitted_fields = args.permitted_fields.split(",")
    boundary = {
        "observation_method": "SSH_EXEC_BOUNDED",
        "endpoint": {
            "host": checked_grant["host"],
            "port": checked_grant["port"],
            "user": checked_grant["user"],
            "probe_identity": checked_grant["probe_identity"],
        },
        "permitted_fields": permitted_fields,
        "time_window": {
            "issued_at": checked_grant["issued_at"],
            "expires_at": checked_grant["expires_at"],
        },
        "network_scope": {"allowed_hosts": [checked_grant["host"]]},
        "timeout_seconds": args.timeout_seconds,
        "redaction_fields": [],
    }

    store = FileStateStore(args.store_root)
    result = observe_runtime_target(
        store,
        project_id=args.project_id,
        project_binding_id=args.project_binding_id,
        target_identity=target_identity,
        boundary=boundary,
        adapter=SshRuntimeAdapter(),
        observed_at=args.now,
    )
    _write_json(
        sys.stdout,
        {
            "ok": True,
            "transport": transport,
            "envelope_id": result["envelope"]["runtime_observation_envelope_id"],
            "observation_outcome": result["envelope"]["observation_outcome"],
            "receipt_status": result["receipt"].status,
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
    render.add_argument("--now", required=True)
    render.set_defaults(func=_cmd_render_command)

    import_output = subparsers.add_parser(
        "import-output", help="validate/normalize a Human-captured probe report"
    )
    import_output.add_argument("--report-file", required=True)
    import_output.set_defaults(func=_cmd_import_output)

    observe = subparsers.add_parser(
        "observe", help="perform the bounded observation now, through the real canonical route"
    )
    observe.add_argument("--grant-file", required=True)
    observe.add_argument("--target-identity-file", required=True)
    observe.add_argument("--store-root", required=True)
    observe.add_argument("--project-id", required=True)
    observe.add_argument("--project-binding-id", required=True)
    observe.add_argument("--permitted-fields", required=True, help="comma-separated field names")
    observe.add_argument("--now", required=True)
    observe.add_argument("--timeout-seconds", type=float, default=30.0)
    observe.add_argument(
        "--actions-status", choices=sorted(tc.DISPATCH_STATUSES), default="UNAVAILABLE"
    )
    observe.add_argument(
        "--requested-transport", choices=sorted(tc.PERMITTED_TRANSPORT_MODES), default=None
    )
    observe.set_defaults(func=_cmd_observe)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
