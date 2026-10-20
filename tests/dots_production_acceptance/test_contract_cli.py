"""Contract tests for cli.py -- WU2 Phase A's preflight/reconcile/recompute/report subset.

Tracks #116 (WU2 Phase A). recompute's own negative controls use the real
recorder.write_raw_receipt/append_manifest_entry, never hand-built fixture files, so a
tampered/missing/duplicate/unreferenced detection is proven against this package's own
real receipt format.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.dots_production_acceptance import cli, recorder as rec
from tests.fixtures.dots_production_acceptance_world import bound


def _write_template(tmp_path: Path) -> Path:
    template = {
        "a": None,
        "b": {"c": None, "d": 0},
        "e": [],
    }
    path = tmp_path / "template.json"
    path.write_text(json.dumps(template))
    return path


def test_preflight_reports_fail_with_still_null_fields(tmp_path: Path) -> None:
    template_path = _write_template(tmp_path)
    instance_path = tmp_path / "instance.json"
    instance_path.write_text(json.dumps({"a": None, "b": {"c": None, "d": 5}, "e": [1]}))

    args = cli.build_parser().parse_args(
        ["preflight", "--manifest", str(instance_path), "--template", str(template_path)]
    )
    result = cli.cmd_preflight(args)

    assert result["manifest_shape_check"] == "FAIL"
    assert "a" in result["still_null_required_fields"]
    assert "b.c" in result["still_null_required_fields"]
    assert "disclaimer" in result


def test_preflight_reports_pass_once_every_required_field_is_filled(tmp_path: Path) -> None:
    template_path = _write_template(tmp_path)
    instance_path = tmp_path / "instance.json"
    instance_path.write_text(
        json.dumps({"a": "filled", "b": {"c": "also-filled", "d": 5}, "e": [1]})
    )

    args = cli.build_parser().parse_args(
        ["preflight", "--manifest", str(instance_path), "--template", str(template_path)]
    )
    result = cli.cmd_preflight(args)

    assert result["manifest_shape_check"] == "PASS"
    assert result["still_null_required_fields"] == []


def _receipt_fixture(tmp_path: Path) -> tuple[Path, Path]:
    evidence_root = tmp_path / "evidence_root"
    source_tree = tmp_path / "source_tree"
    source_tree.mkdir()
    manifest_path = tmp_path / "manifest.jsonl"

    for index, outcome in enumerate(("SUCCEEDED", "SUCCEEDED", "FAILED")):
        receipt = rec.write_raw_receipt(
            evidence_root,
            run_id=f"RUN-{index}",
            payload={
                "case_classification": "NORMAL_OPERATION",
                "run_state": "RESOLVED",
                "outcome": outcome,
            },
            source_tree_root=source_tree,
        )
        rec.append_manifest_entry(
            manifest_path,
            rec.ManifestEntry(
                receipt_id=receipt.receipt_id,
                sha256=receipt.sha256,
                run_id=receipt.run_id,
                recorded_at=receipt.recorded_at,
            ),
        )
    return evidence_root, manifest_path


def test_recompute_is_verified_and_computes_a_reference_aggregate_when_clean(
    tmp_path: Path,
) -> None:
    evidence_root, manifest_path = _receipt_fixture(tmp_path)
    args = cli.build_parser().parse_args(
        ["recompute", "--evidence-root", str(evidence_root), "--manifest", str(manifest_path)]
    )
    result = cli.cmd_recompute(args)

    assert result["integrity_verdict"] == "VERIFIED"
    assert result["anomalies"] == []
    assert result["reference_aggregate_from_verified_receipts_only"]["n_blocks"] == 3


def test_recompute_tampered_receipt_fails_integrity_and_never_pass_from_clean_subset(
    tmp_path: Path,
) -> None:
    evidence_root, manifest_path = _receipt_fixture(tmp_path)
    entries = rec.read_manifest_entries(manifest_path)
    tampered_path = evidence_root / entries[0]["run_id"] / f"{entries[0]['receipt_id']}.json"
    tampered_payload = json.loads(tampered_path.read_text())
    tampered_payload["outcome"] = "SUCCEEDED"  # flip a FAILED receipt to SUCCEEDED
    tampered_path.write_text(json.dumps(tampered_payload))

    args = cli.build_parser().parse_args(
        ["recompute", "--evidence-root", str(evidence_root), "--manifest", str(manifest_path)]
    )
    result = cli.cmd_recompute(args)

    assert result["integrity_verdict"] == "FAILED"
    assert any(a["type"] == "TAMPERED" for a in result["anomalies"])
    # the two untampered receipts may still form a reference aggregate, but the overall
    # verdict must stay FAILED -- never silently promoted by the clean subset.
    assert result["integrity_verdict"] != "VERIFIED"


def test_recompute_missing_receipt_file_is_detected(tmp_path: Path) -> None:
    evidence_root, manifest_path = _receipt_fixture(tmp_path)
    entries = rec.read_manifest_entries(manifest_path)
    missing_path = evidence_root / entries[1]["run_id"] / f"{entries[1]['receipt_id']}.json"
    missing_path.unlink()

    args = cli.build_parser().parse_args(
        ["recompute", "--evidence-root", str(evidence_root), "--manifest", str(manifest_path)]
    )
    result = cli.cmd_recompute(args)

    assert result["integrity_verdict"] == "FAILED"
    assert any(a["type"] == "MISSING" for a in result["anomalies"])


def test_recompute_duplicate_manifest_entry_is_detected(tmp_path: Path) -> None:
    evidence_root, manifest_path = _receipt_fixture(tmp_path)
    entries = rec.read_manifest_entries(manifest_path)
    rec.append_manifest_entry(
        manifest_path,
        rec.ManifestEntry(
            receipt_id=entries[0]["receipt_id"],
            sha256=entries[0]["sha256"],
            run_id=entries[0]["run_id"],
            recorded_at=entries[0]["recorded_at"],
        ),
    )

    args = cli.build_parser().parse_args(
        ["recompute", "--evidence-root", str(evidence_root), "--manifest", str(manifest_path)]
    )
    result = cli.cmd_recompute(args)

    assert result["integrity_verdict"] == "FAILED"
    assert any(a["type"] == "DUPLICATE" for a in result["anomalies"])


def test_recompute_unreferenced_raw_file_is_detected_as_incomplete(tmp_path: Path) -> None:
    evidence_root, manifest_path = _receipt_fixture(tmp_path)
    # a raw receipt written but never appended to the manifest (e.g. a crash between the
    # two writes) -- the one PROTOCOL.md Sec.8 negative control recorder.py's own
    # append-only design exists to let a later recompute detect.
    rec.write_raw_receipt(
        evidence_root,
        run_id="RUN-ORPHAN",
        payload={
            "case_classification": "NORMAL_OPERATION",
            "run_state": "RESOLVED",
            "outcome": "SUCCEEDED",
        },
        source_tree_root=evidence_root.parent / "source_tree",
    )

    args = cli.build_parser().parse_args(
        ["recompute", "--evidence-root", str(evidence_root), "--manifest", str(manifest_path)]
    )
    result = cli.cmd_recompute(args)

    assert result["integrity_verdict"] == "INCOMPLETE"
    assert any(a["type"] == "UNREFERENCED" for a in result["anomalies"])


def test_recompute_missing_evidence_root_and_manifest_is_detected_not_verified(
    tmp_path: Path,
) -> None:
    """Regression for PR #121 review finding F-CLI-1: a nonexistent evidence_root and
    manifest path must never fall through zero-entries/zero-anomalies to
    integrity_verdict=VERIFIED -- a missing required input is distinct from a
    verified-empty one."""

    evidence_root = tmp_path / "does_not_exist_evidence_root"
    manifest_path = tmp_path / "does_not_exist_manifest.jsonl"

    args = cli.build_parser().parse_args(
        ["recompute", "--evidence-root", str(evidence_root), "--manifest", str(manifest_path)]
    )
    result = cli.cmd_recompute(args)

    assert result["integrity_verdict"] == "FAILED"
    assert any(a["type"] == "MISSING_INPUT" for a in result["anomalies"])
    assert result["integrity_verdict"] != "VERIFIED"


def test_reconcile_cli_matches_real_store_state_and_external_snapshot(tmp_path: Path) -> None:
    from tests.state_helpers import SCHEMA_ROOT

    _store, world = bound(tmp_path)
    genesis_revision = world["genesis_state"]["state_revision"]

    snapshot_path = tmp_path / "external_snapshot.json"
    snapshot_path.write_text(json.dumps({"stop_acknowledged_for_run_id": "RUN-1"}))

    args = cli.build_parser().parse_args(
        [
            "reconcile",
            "--store-root",
            str(tmp_path / "dots_production_acceptance"),
            "--schema-root",
            str(SCHEMA_ROOT),
            "--project-id",
            world["project_id"],
            "--run-id",
            "RUN-1",
            "--expected-state-revision",
            str(genesis_revision),
            "--external-state-snapshot",
            str(snapshot_path),
        ]
    )
    result = cli.cmd_reconcile(args)

    assert result["store_matched"] is True
    assert result["external_matched"] is True
    assert result["reconciled"] is True


def test_report_merges_sub_reports_without_adding_a_new_verdict(tmp_path: Path) -> None:
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text(json.dumps({"manifest_shape_check": "PASS"}))
    recompute_path = tmp_path / "recompute.json"
    recompute_path.write_text(json.dumps({"integrity_verdict": "VERIFIED"}))

    args = cli.build_parser().parse_args(
        [
            "report",
            "--preflight-report",
            str(preflight_path),
            "--recompute-report",
            str(recompute_path),
        ]
    )
    result = cli.cmd_report(args)

    assert result["preflight"]["manifest_shape_check"] == "PASS"
    assert result["recompute"]["integrity_verdict"] == "VERIFIED"
    assert "reconcile" not in result
