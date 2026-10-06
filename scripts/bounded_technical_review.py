"""The one script Decision 0004 (Issue #109) authorizes to invoke the bounded-technical-review
owners -- :mod:`manosube_agent_civilization.development_binding.review_selection`,
``.review_control``, and ``.review_adapter`` -- and the only place this delivery composes them
into a sequence. It introduces no second admission route: every decision below is answered by
calling one of those three owners, never by re-deriving their logic here.

```text
validate-grant    -> review_selection.evaluate_review_selection            (pure, offline)
claim             -> review_control.claim_review_launch                   (durable ledger)
record-dispatch   -> review_control.record_dispatch_attempt               (durable ledger)
record-outcome    -> review_control.record_review_outcome                 (durable ledger)
activation-gate   -> review_control.evaluate_activation_gate              (pure, offline)
cancel            -> review_adapter.cancel_review_task                   (external effect)
dispatch          -> validate-grant, then claim, then the activation gate -- and stops there
```

**``dispatch`` never launches a real review in this delivery.** Runtime starts disabled
(``ACTIVATION_DEFAULT=false``, `.policy.BOUNDED_REVIEW_ACTIVATION_DEFAULT`), and this script
hardcodes ``activation_enabled=False`` on every activation-gate evidence it assembles -- there
is no flag, environment variable, or configuration file this script reads that can set it to
``True``. A caller that wants a real launch must build one outside this script entirely, after
an authenticated activation grant this delivery does not create. This is intentional, not a
missing feature: ``REAL_CODEX_MODEL_REQUEST_ALLOWED=false`` for this whole delivery, and this
script's own ``dispatch`` subcommand is where that boundary is enforced, not merely stated.

This script performs no automated-review request on its own initiative -- every subcommand
reads an explicit, caller-supplied grant/ledger/evidence file or argument and reports a
decision; none of them discover a PR, a repository, or a provider account on their own.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, TextIO

from manosube_agent_civilization.development_binding.policy import BOUNDED_REVIEW_NUMERIC_LIMITS
from manosube_agent_civilization.development_binding.review_adapter import (
    CancellationOutcome,
    cancel_review_task,
)
from manosube_agent_civilization.development_binding.review_control import (
    REVIEW_CLAIM_ADMITTED,
    claim_review_launch,
    compute_identity_key,
    evaluate_activation_gate,
    record_dispatch_attempt,
    record_review_outcome,
)
from manosube_agent_civilization.development_binding.review_selection import (
    REVIEW_SELECTION_ADMITTED,
    evaluate_review_selection,
)

SCHEMA_VERSION = "0.1"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _emit(stream: TextIO, payload: dict[str, Any]) -> None:
    stream.write(json.dumps(payload, indent=2, sort_keys=True))
    stream.write("\n")


def cmd_validate_grant(args: argparse.Namespace, stdout: TextIO) -> int:
    grant = _read_json(args.grant_file)
    decision = evaluate_review_selection(grant, now=args.now)
    _emit(stdout, decision)
    return 0 if decision["decision"] == REVIEW_SELECTION_ADMITTED else 1


def cmd_activation_gate(args: argparse.Namespace, stdout: TextIO) -> int:
    evidence = _read_json(args.evidence_file)
    decision = evaluate_activation_gate(evidence)
    _emit(stdout, decision)
    return 0 if decision["decision"] == "ACTIVATION_GATE_ACTIVATED" else 1


def cmd_claim(args: argparse.Namespace, stdout: TextIO) -> int:
    identity_key = compute_identity_key(
        repository=args.repository,
        pull_request=args.pull_request,
        base_sha=args.base_sha,
        head_sha=args.head_sha,
        requirement_id=args.requirement_id,
        input_digest=args.input_digest,
    )
    decision = claim_review_launch(
        args.ledger_file,
        identity_key=identity_key,
        work_unit_id=args.work_unit_id,
        repository=args.repository,
        now=args.now,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    _emit(stdout, decision)
    return 0 if decision["decision"] == REVIEW_CLAIM_ADMITTED else 1


def cmd_record_dispatch(args: argparse.Namespace, stdout: TextIO) -> int:
    record_dispatch_attempt(
        args.ledger_file,
        args.identity_key,
        repository=args.repository,
        acknowledged=args.acknowledged,
    )
    _emit(stdout, {"identity_key": args.identity_key, "acknowledged": args.acknowledged})
    return 0


def cmd_record_outcome(args: argparse.Namespace, stdout: TextIO) -> int:
    record_review_outcome(
        args.ledger_file,
        args.identity_key,
        repository=args.repository,
        status=args.status,
        result_digest=args.result_digest,
    )
    _emit(stdout, {"identity_key": args.identity_key, "status": args.status})
    return 0


def cmd_cancel(args: argparse.Namespace, stdout: TextIO) -> int:
    outcome: CancellationOutcome = cancel_review_task(args.pid)
    _emit(
        stdout,
        {
            "local_process_group_terminated": outcome.local_process_group_terminated,
            "provider_server_state": outcome.provider_server_state,
        },
    )
    return 0


def cmd_dispatch(args: argparse.Namespace, stdout: TextIO) -> int:
    """Validate a grant, then attempt a durable claim, then evaluate the activation gate --
    and stop. This subcommand never calls :mod:`.review_adapter` and never launches a process:
    the activation evidence it assembles always carries ``activation_enabled=False`` (see the
    module docstring), so the gate it reports is always ``ACTIVATION_GATE_NOT_ACTIVATED`` in
    this delivery, whatever else the grant or claim steps found.
    """

    grant = _read_json(args.grant_file)
    selection_decision = evaluate_review_selection(grant, now=args.now)
    if selection_decision["decision"] != REVIEW_SELECTION_ADMITTED:
        _emit(stdout, {"stage": "validate-grant", "decision": selection_decision})
        return 1

    identity_key = compute_identity_key(
        repository=grant["authorized_repository"],
        pull_request=grant["authorized_pull_request"],
        base_sha=grant["authorized_base_sha"],
        head_sha=grant["authorized_head_sha"],
        requirement_id=grant["requirement_id"],
        input_digest=grant["input_digest"],
    )
    claim_decision = claim_review_launch(
        args.ledger_file,
        identity_key=identity_key,
        work_unit_id=grant["work_unit_id"],
        repository=grant["authorized_repository"],
        now=args.now,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    if claim_decision["decision"] != REVIEW_CLAIM_ADMITTED:
        _emit(stdout, {"stage": "claim", "decision": claim_decision})
        return 1

    activation_evidence = {
        "auth_confirmed": bool(args.auth_confirmed),
        "cli_version": args.cli_version,
        "model": args.model,
        "allowance_confirmed_adequate": bool(args.allowance_confirmed_adequate),
        "auto_recharge_verified_disabled": bool(args.auto_recharge_verified_disabled),
        "native_github_dedup_disposition": args.native_github_dedup_disposition,
        "live_bounded_review_grant_admitted": selection_decision["decision"]
        == REVIEW_SELECTION_ADMITTED,
        # Never read from a flag -- see the module docstring. This is the one field this
        # script itself never lets a caller set True.
        "activation_enabled": False,
    }
    gate_decision = evaluate_activation_gate(activation_evidence)
    _emit(
        stdout,
        {
            "stage": "activation-gate",
            "identity_key": identity_key,
            "decision": gate_decision,
            "real_launch_performed": False,
        },
    )
    return 0 if gate_decision["decision"] == "ACTIVATION_GATE_ACTIVATED" else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bounded_technical_review",
        description=(
            "Decision 0004 (Issue #109): invoke review_selection/review_control/"
            "review_adapter. Never performs a real Codex launch in this delivery."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_grant = subparsers.add_parser("validate-grant", help="Evaluate a Bounded Review Grant")
    validate_grant.add_argument("grant_file", type=Path)
    validate_grant.add_argument("--now", required=True)
    validate_grant.set_defaults(handler=cmd_validate_grant)

    activation_gate = subparsers.add_parser(
        "activation-gate", help="Evaluate the activation/spending gate"
    )
    activation_gate.add_argument("evidence_file", type=Path)
    activation_gate.set_defaults(handler=cmd_activation_gate)

    claim = subparsers.add_parser("claim", help="Atomically claim one review launch identity")
    claim.add_argument("ledger_file", type=Path)
    claim.add_argument("--repository", required=True)
    claim.add_argument("--pull-request", required=True, dest="pull_request")
    claim.add_argument("--base-sha", required=True, dest="base_sha")
    claim.add_argument("--head-sha", required=True, dest="head_sha")
    claim.add_argument("--requirement-id", required=True, dest="requirement_id")
    claim.add_argument("--input-digest", required=True, dest="input_digest")
    claim.add_argument("--work-unit-id", required=True, dest="work_unit_id")
    claim.add_argument("--now", required=True)
    claim.set_defaults(handler=cmd_claim)

    record_dispatch = subparsers.add_parser(
        "record-dispatch", help="Record one dispatch attempt against an existing claim"
    )
    record_dispatch.add_argument("ledger_file", type=Path)
    record_dispatch.add_argument("identity_key")
    record_dispatch.add_argument("--repository", required=True)
    record_dispatch.add_argument("--acknowledged", action="store_true")
    record_dispatch.set_defaults(handler=cmd_record_dispatch)

    record_outcome = subparsers.add_parser(
        "record-outcome", help="Record the final outcome of a dispatched review"
    )
    record_outcome.add_argument("ledger_file", type=Path)
    record_outcome.add_argument("identity_key")
    record_outcome.add_argument("--repository", required=True)
    record_outcome.add_argument("--status", required=True, choices=["COMPLETED", "FAILED"])
    record_outcome.add_argument("--result-digest", dest="result_digest", default=None)
    record_outcome.set_defaults(handler=cmd_record_outcome)

    cancel = subparsers.add_parser("cancel", help="Cancel the owned review process group")
    cancel.add_argument("pid", type=int)
    cancel.set_defaults(handler=cmd_cancel)

    dispatch = subparsers.add_parser(
        "dispatch",
        help="Validate a grant, claim, and evaluate activation -- never launches a review",
    )
    dispatch.add_argument("grant_file", type=Path)
    dispatch.add_argument("ledger_file", type=Path)
    dispatch.add_argument("--now", required=True)
    dispatch.add_argument("--auth-confirmed", action="store_true", dest="auth_confirmed")
    dispatch.add_argument("--cli-version", default="", dest="cli_version")
    dispatch.add_argument("--model", default="", dest="model")
    dispatch.add_argument(
        "--allowance-confirmed-adequate", action="store_true", dest="allowance_confirmed_adequate"
    )
    dispatch.add_argument(
        "--auto-recharge-verified-disabled",
        action="store_true",
        dest="auto_recharge_verified_disabled",
    )
    dispatch.add_argument(
        "--native-github-dedup-disposition",
        default="UNRESOLVED",
        dest="native_github_dedup_disposition",
    )
    dispatch.set_defaults(handler=cmd_dispatch)

    return parser


def main(argv: list[str] | None = None, *, stdout: TextIO = sys.stdout) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = args.handler
    return handler(args, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
