"""The Actions-independent local control entry point for Runtime Observation transports
(Issue #105, transport-independent runtime observation; mode-specific dispatch corrected by
PR #108 Structural Review Round 1, F2).

```text
subcommand           what it answers
-----------          ----------------------------------------------------------------
classify-dispatch    is a GitHub Actions dispatch attempt AVAILABLE / UNAVAILABLE / UNKNOWN?
render-command        the exact copy/paste SSH command for a Human operator (Capability A)
import-output          validate output a Human already captured and pasted back, through the
                        identical closed-shape check the real adapter itself applies
observe               perform the bounded observation now, through the real canonical route --
                        but ONLY when the selected transport is PREAUTHORIZED_UNATTENDED_SSH;
                        every other selection is refused by this subcommand outright (F2)
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
subcommand now refuses outright unless ``select_transport`` actually resolved
``PREAUTHORIZED_UNATTENDED_SSH`` -- the one mode this package ever executes without a Human
present. A Human-selected ``MANUAL_SSH`` attempt is directed to ``render-command``; a
``GITHUB_ACTIONS`` selection is directed to the real dispatched workflow (which itself only
renders a command, per ``.github/workflows/runtime_observation.yml``'s own docstring), never
silently executed locally by this CLI.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, TextIO

from manosube_agent_civilization.runtime import observe_runtime_target, transport_control as tc
from manosube_agent_civilization.runtime.adapter import SshRuntimeAdapter
from manosube_agent_civilization.runtime.types import SSH_PROBE_SCRIPT_SHA256
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
    themselves and pasting its stdout back -- never re-executes anything, and never applies a
    looser check than the real adapter does: the identical closed-shape parser
    (:meth:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter._parse_probe_report`)
    checks the exact key set, ``ok``'s own real boolean type, and every other field's own type
    (PR #108 SR1 F4), and the result is additionally required to carry the one pinned probe
    script digest (F3) -- a Human-captured transcript is checked exactly as strictly as an
    automatically-captured one."""

    try:
        with open(args.report_file, encoding="utf-8") as stream:
            raw_stdout = stream.read()
    except OSError as error:
        _write_json(sys.stdout, {"ok": False, "error": f"unreadable report file: {error}"})
        return 1
    report = SshRuntimeAdapter._parse_probe_report(raw_stdout)
    if report is None:
        _write_json(
            sys.stdout,
            {"ok": False, "error": "captured output is not the one closed probe report shape"},
        )
        return 1
    if report["probe_script_sha256"] != SSH_PROBE_SCRIPT_SHA256:
        _write_json(
            sys.stdout,
            {
                "ok": False,
                "error": "captured report's own probe_script_sha256 does not match the "
                "pinned, reviewed probe script digest",
            },
        )
        return 1
    _write_json(sys.stdout, {"ok": True, "imported_report": report})
    return 0


def _cmd_observe(args: argparse.Namespace) -> int:
    grant = _load_json_file(args.grant_file)
    target_identity = _load_json_file(args.target_identity_file)
    store = FileStateStore(Path(args.store_root), schema_root=Path(args.schema_root))

    try:
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
        _write_json(sys.stdout, {"ok": False, "error": str(error)})
        return 1

    if transport != "PREAUTHORIZED_UNATTENDED_SSH":
        # PR #108 SR1 F2: a transport label is never, by itself, permission to execute. This
        # subcommand performs the real, local, unattended SSH execution and nothing else --
        # GITHUB_ACTIONS means a real Actions job renders a command (never executes it here),
        # and MANUAL_SSH means a Human runs the command render-command already gave them.
        _write_json(
            sys.stdout,
            {
                "ok": False,
                "error": (
                    f"selected transport is {transport!r}, not PREAUTHORIZED_UNATTENDED_SSH -- "
                    "this subcommand never executes any other transport. Use render-command "
                    "for MANUAL_SSH, or the dispatched GitHub Actions workflow for "
                    "GITHUB_ACTIONS."
                ),
                "selected_transport": transport,
            },
        )
        return 1

    try:
        adapter = SshRuntimeAdapter(
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

    result = observe_runtime_target(
        store,
        project_id=args.project_id,
        project_binding_id=args.project_binding_id,
        target_identity=target_identity,
        boundary=boundary,
        adapter=adapter,
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
    render.add_argument("--store-root", required=True)
    render.add_argument("--schema-root", required=True)
    render.add_argument("--project-id", required=True)
    render.add_argument("--project-binding-id", required=True)
    render.add_argument("--now", required=True)
    render.set_defaults(func=_cmd_render_command)

    import_output = subparsers.add_parser(
        "import-output", help="validate a Human-captured probe report through the real schema"
    )
    import_output.add_argument("--report-file", required=True)
    import_output.set_defaults(func=_cmd_import_output)

    observe = subparsers.add_parser(
        "observe",
        help=(
            "perform the bounded observation now, through the real canonical route -- "
            "refuses outright unless the selected transport is PREAUTHORIZED_UNATTENDED_SSH"
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
    observe.set_defaults(func=_cmd_observe)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
