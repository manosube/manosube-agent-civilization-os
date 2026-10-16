"""WU2 Phase A: the subset of ``WU2_PLAN.md``'s deferred CLI contract delivered in this
revision -- ``preflight`` / ``reconcile`` / ``recompute`` / ``report``, each a thin,
offline wrapper over an existing WU2 module. None makes a live dots/GitHub call.

**Deferred to Phase B / later (not in this module):**
  - ``freeze``: pins/ratifies a ``RUN_MANIFEST_TEMPLATE.json`` instance. Distinct from
    ``preflight``'s shape check below -- freezing is a human-authority act
    (``authorization.ratifying_authority``/``ratified_at``), not a format validation, and
    is deferred until a real manifest instance exists to ratify.
  - ``run --phase ...``: the real dispatch-loop launcher. Requires live authorization
    (``RUN_MANIFEST_TEMPLATE.json``'s own ``authorization.live_model_launch_authorized``)
    this harness is never permitted to grant itself.

Every subcommand below is a format/integrity check or a reused-module wrapper, never an
authorization or PASS/FAIL production verdict.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from typing import Any

from tests.dots_production_acceptance import aggregator as agg

MANIFEST_SHAPE_DISCLAIMER = (
    "manifest_shape_check is a FORMAT validation only (every REQUIRED_HUMAN_INPUT field is "
    "non-null) -- it is NOT an authorization check, a live-launch permission, or a judgment "
    "that this manifest should be ratified. authorization.* boolean VALUES are never "
    "evaluated for truthiness here; only their presence/shape is checked. Ratification is "
    "SHUKOU's own act (see RUN_MANIFEST_TEMPLATE.json authorization.ratifying_authority), "
    "performed by the deferred `freeze` subcommand, not this one."
)

RECOMPUTE_DISCLAIMER = (
    "integrity_verdict is a RECORD-INTEGRITY judgment over raw receipts and their manifest "
    "(tampered/missing/duplicate/unreferenced detection) -- it is NOT "
    "MEASUREMENT_CONTRACT.md Sec.B's own statistical PASS/INCOMPLETE verdict, which still "
    "applies on top of (never in place of) this check, including its own rule that a "
    "zero-failure window is always reported INCOMPLETE, never PASS."
)


def _manifest_null_paths(template: Any, instance: Any, *, path: str = "") -> list[str]:
    """Every JSON path where *template* has a literal ``null`` but *instance* either lacks
    the key or is also ``null`` there. Walks dicts recursively; a template list value is
    treated as an opaque leaf (shape, not element-by-element, checked)."""

    missing: list[str] = []
    if isinstance(template, dict):
        if not isinstance(instance, dict):
            return [path or "<root>"]
        for key, template_value in template.items():
            child_path = f"{path}.{key}" if path else key
            instance_value = instance.get(key, None) if isinstance(instance, dict) else None
            if key not in instance:
                if template_value is None or isinstance(template_value, dict):
                    missing.append(child_path)
                continue
            missing.extend(_manifest_null_paths(template_value, instance_value, path=child_path))
    elif template is None:
        if instance is None:
            missing.append(path)
    return missing


def cmd_preflight(args: argparse.Namespace) -> dict[str, Any]:
    template = json.loads(Path(args.template).read_text())
    instance = json.loads(Path(args.manifest).read_text())
    null_paths = _manifest_null_paths(template, instance)
    return {
        "command": "preflight",
        "disclaimer": MANIFEST_SHAPE_DISCLAIMER,
        "manifest_shape_check": "FAIL" if null_paths else "PASS",
        "still_null_required_fields": null_paths,
    }


def cmd_reconcile(args: argparse.Namespace) -> dict[str, Any]:
    from manosube_agent_civilization.store import FileStateStore

    from tests.dots_production_acceptance import reconciliation as recon

    store = FileStateStore(Path(args.store_root), schema_root=Path(args.schema_root))
    external_snapshot = json.loads(Path(args.external_state_snapshot).read_text())

    result = recon.reconcile(
        store,
        project_id=args.project_id,
        expected_state_predicate=lambda s: s.get("state_revision") == args.expected_state_revision,
        external_reader=lambda: external_snapshot,
        expected_external_predicate=lambda ext: ext.get("stop_acknowledged_for_run_id")
        == args.run_id,
    )
    return {
        "command": "reconcile",
        "store_matched": result.store_matched,
        "external_matched": result.external_matched,
        "reconciled": result.reconciled,
        "checked_at": result.checked_at,
    }


def _sha256_of_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _recompute_integrity(evidence_root: Path, manifest_path: Path) -> dict[str, Any]:
    from tests.dots_production_acceptance import recorder as rec

    entries = rec.read_manifest_entries(manifest_path)

    anomalies: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    verified_payloads: list[Mapping[str, Any]] = []
    referenced_paths: set[Path] = set()

    for entry in entries:
        entry_key = (entry["run_id"], entry["receipt_id"])
        if entry_key in seen_keys:
            anomalies.append({"type": "DUPLICATE", "run_id": entry["run_id"], "receipt_id": entry["receipt_id"]})
            continue
        seen_keys.add(entry_key)

        raw_path = evidence_root / entry["run_id"] / f"{entry['receipt_id']}.json"
        referenced_paths.add(raw_path.resolve())
        if not raw_path.exists():
            anomalies.append({"type": "MISSING", "run_id": entry["run_id"], "receipt_id": entry["receipt_id"]})
            continue

        actual_sha256 = _sha256_of_file(raw_path)
        if actual_sha256 != entry["sha256"]:
            anomalies.append(
                {
                    "type": "TAMPERED",
                    "run_id": entry["run_id"],
                    "receipt_id": entry["receipt_id"],
                    "manifest_sha256": entry["sha256"],
                    "actual_sha256": actual_sha256,
                }
            )
            continue

        verified_payloads.append(json.loads(raw_path.read_text()))

    if evidence_root.exists():
        for run_dir in evidence_root.iterdir():
            if not run_dir.is_dir():
                continue
            for raw_file in run_dir.glob("RCT-*.json"):
                if raw_file.resolve() not in referenced_paths:
                    anomalies.append({"type": "UNREFERENCED", "path": str(raw_file)})

    anomaly_types = {anomaly["type"] for anomaly in anomalies}
    if anomaly_types & {"TAMPERED", "MISSING", "DUPLICATE"}:
        integrity_verdict = "FAILED"
    elif "UNREFERENCED" in anomaly_types:
        integrity_verdict = "INCOMPLETE"
    else:
        integrity_verdict = "VERIFIED"

    return {
        "anomalies": anomalies,
        "integrity_verdict": integrity_verdict,
        "verified_receipt_count": len(verified_payloads),
        "verified_payloads": verified_payloads,
    }


def cmd_recompute(args: argparse.Namespace) -> dict[str, Any]:
    evidence_root = Path(args.evidence_root)
    manifest_path = Path(args.manifest)
    integrity = _recompute_integrity(evidence_root, manifest_path)

    blocks = [
        {"successes": 1 if payload.get("outcome") == "SUCCEEDED" else 0, "total": 1}
        for payload in integrity["verified_payloads"]
        if payload.get("case_classification") in {"NORMAL_OPERATION", "ENVIRONMENT_FAULT"}
    ]
    reference_aggregate = None
    if blocks:
        reference_aggregate = {
            "pooled_rate": agg.pooled_rate(blocks),
            "n_blocks": len(blocks),
        }

    return {
        "command": "recompute",
        "disclaimer": RECOMPUTE_DISCLAIMER,
        "integrity_verdict": integrity["integrity_verdict"],
        "anomalies": integrity["anomalies"],
        "reference_aggregate_from_verified_receipts_only": reference_aggregate,
        "note": (
            "reference_aggregate is computed from verified receipts only and is labeled "
            "reference-only -- per this session's own governing instruction, a non-VERIFIED "
            "integrity_verdict is never silently dropped in favor of this number, and this "
            "number never upgrades integrity_verdict to PASS/VERIFIED by itself."
        ),
    }


def cmd_report(args: argparse.Namespace) -> dict[str, Any]:
    report: dict[str, Any] = {"command": "report"}
    for name, path in (
        ("preflight", args.preflight_report),
        ("reconcile", args.reconcile_report),
        ("recompute", args.recompute_report),
    ):
        if path is not None:
            report[name] = json.loads(Path(path).read_text())
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dots_production_acceptance.cli")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--manifest", required=True)
    preflight.add_argument(
        "--template",
        default=str(
            Path(__file__).resolve().parents[2]
            / "docs/validation/dots_production_acceptance/RUN_MANIFEST_TEMPLATE.json"
        ),
    )
    preflight.set_defaults(func=cmd_preflight)

    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("--store-root", required=True)
    reconcile.add_argument("--schema-root", required=True)
    reconcile.add_argument("--project-id", required=True)
    reconcile.add_argument("--run-id", required=True)
    reconcile.add_argument("--expected-state-revision", required=True, type=int)
    reconcile.add_argument("--external-state-snapshot", required=True)
    reconcile.set_defaults(func=cmd_reconcile)

    recompute = sub.add_parser("recompute")
    recompute.add_argument("--evidence-root", required=True)
    recompute.add_argument("--manifest", required=True)
    recompute.set_defaults(func=cmd_recompute)

    report = sub.add_parser("report")
    report.add_argument("--preflight-report")
    report.add_argument("--reconcile-report")
    report.add_argument("--recompute-report")
    report.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.func(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
