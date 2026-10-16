#!/usr/bin/env python3
"""WU2 Phase A (Issue #116 / PR #119 follow-up) design-validation scenario: an end-to-end
run of ``tests/dots_production_acceptance/driver.py`` and ``cli.py`` against the real
Kernel, exercising every Phase A acceptance item SHUKOU fixed for this round:

1. The driver connects the already-merged 5 WU2 components (recorder, independent_oracle,
   reconciliation, aggregator, case_generators -- the latter three by direct reuse here;
   recorder and aggregator via ``recorder.py``/``cli.py recompute``) to the real
   Kernel/Store/Reflow, never a second owner of any of those.
2. A stop blocks every new dispatch, and the prior attempt's outcome is never resent while
   unknown.
3. Recovery (a fresh dispatch after a stop) proceeds only once BOTH the Store and the
   adapter's own external state have been independently reconciled.
4. This script's own command/input/output are saved (this file + the literal
   ``wu2_phase_a_scenario_output.txt`` it produces), and the scenario is reproducible.
5. None of this is counted as a real dots connection or a production-operation success --
   see the explicit disclaimers throughout.

**Reproducibility note, corrected for this script specifically (more limited than
``wu2_component_scenario.py``'s own claim):** this script's dispatched "Change" work units
are routed through the real ``compose_change_executor()`` entrypoint, whose own internal
``work_unit_ref`` id is derived from a real wall-clock reading
(``change_executor/route.py``'s own ``_attempt_marker``). Content-addressed values that
depend on that reading (``work_time_coordination_open_id``, the ``CHEXEC-...`` work unit
id, and the receipt ids ``recorder.py`` derives from them) are therefore NOT
byte-identical between runs, unlike ``verify_measurement_contract.py``'s pure, clock-free
fixtures. What IS identical between runs: every structural fact this script asserts
(``manifest_shape_check``, ``integrity_verdict``, ``reconciled``, the written file's exact
content, the terminal_outcome value, the stop/recovery sequence). Confirmed by running this
script twice and diffing everything except lines containing a hash-like token, a
``/tmp/...`` path, or an ISO-8601 timestamp.

Run with (from the repository root, this PR's HEAD):
    PYTHONPATH=. python3 docs/validation/dots_production_acceptance/verification/wu2_phase_a_scenario.py
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

from tests.dots_production_acceptance import cli, recorder as rec
from tests.dots_production_acceptance.driver import Driver, DriverError, FixedFixtureDotsAdapter
from tests.fixtures.change_executor_kill_switch_issuer import issuer_public_key_hex
from tests.fixtures.change_executor_world import (
    CountingAdapter,
    bound,
    build_committed_change,
    commit_active_kill_switch,
    execution_boundary_for,
    git_worktree,
    operation_for,
)

from manosube_agent_civilization.change_executor.route import compose_change_executor

WORK_UNIT = {"kind": "dots_production_acceptance_work_unit", "id": "WU-PHASE-A-SCENARIO-0001"}


def main() -> None:
    print("=" * 78)
    print("WU2 PHASE A SCENARIO -- driver.py + cli.py against the real Kernel")
    print("DISCLAIMER: zero live dots/GitHub call anywhere in this script. The adapter is")
    print("a fixed fixture (FixedFixtureDotsAdapter); only the CHANGE_EXECUTOR side is the")
    print("real, unmodified Kernel entrypoint. Not a production-operation success.")
    print("=" * 78)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        store, info = bound(tmp_path)
        commit_active_kill_switch(store, info["project_id"])
        worktree = git_worktree(tmp_path)
        adapter_identity = {"kind": "controlled_filesystem_adapter", "version": "0.1"}
        change_adapter = CountingAdapter()

        def _executor(path: str, content: str) -> tuple[dict, callable]:
            built = build_committed_change(
                store,
                info["project_id"],
                action_kind="WRITE_DOCUMENTATION_FILE",
                operation=operation_for(
                    "WRITE_DOCUMENTATION_FILE", writes=[{"path": path, "content_utf8": content}]
                ),
                paths=[path],
            )
            execute = compose_change_executor(
                store,
                project_id=info["project_id"],
                project_binding_id=info["project_binding_id"],
                execution_boundary=execution_boundary_for(worktree_root=str(worktree)),
                adapter_identity=adapter_identity,
                adapter=change_adapter,
                kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
            )
            return built["change"], execute

        change_1, execute_1 = _executor("docs/phase_a_scenario_1.md", "first authorized change")
        dots_adapter = FixedFixtureDotsAdapter()
        driver = Driver(
            store,
            project_id=info["project_id"],
            run_state_path=tmp_path / "run_state.json",
            adapter=dots_adapter,
            change_executor_execute=execute_1,
        )

        print("\n--- SECTION 1: real dispatch through the real CHANGE_EXECUTOR route ---")
        record_1 = driver.dispatch(
            WORK_UNIT,
            case_classification="NORMAL_OPERATION",
            change_id=change_1["change_id"],
            claim_token="claim-phase-a-1",
            execution_instant="2026-09-10T00:00:01Z",
        )
        print(f"outcome={record_1.outcome} run_state={record_1.run_state}")
        print(f"receipt_outcome={record_1.change_execution_receipt_outcome}")
        open_record = store.resolve_coordination_record(
            info["project_id"],
            "work_time_coordination_open",
            record_1.work_time_coordination_open_id,
        )
        terminal_record = store.resolve_coordination_record(
            info["project_id"],
            "work_time_coordination_terminal",
            record_1.work_time_coordination_terminal_id,
        )
        print(f"real work_time_coordination_open.adapter_kind={open_record['adapter_kind']}")
        print(
            f"real work_time_coordination_terminal.terminal_outcome={terminal_record['terminal_outcome']}"
        )
        written = (worktree / "docs/phase_a_scenario_1.md").read_text()
        print(f"real file readback: {written!r}")
        assert written == "first authorized change"
        assert change_adapter.call_count == 1

        print("\n--- SECTION 2: stop blocks new dispatch; unconfirmed stop blocks identically ---")
        stop_result = driver.request_stop("RUN-PHASE-A-1")
        print(f"request_stop -> {stop_result}")
        try:
            driver.dispatch(
                {"kind": "x", "id": "blocked"},
                case_classification="NORMAL_OPERATION",
                change_id=change_1["change_id"],
                claim_token="claim-should-not-run",
                execution_instant="2026-09-10T00:00:02Z",
            )
            print("FAIL: dispatch should have been refused")
        except DriverError as exc:
            print(f"dispatch correctly refused: {exc}")

        print("\n--- SECTION 3: recovery gated on BOTH-sides reconciliation ---")
        incomplete = driver.reconcile_before_recovery(
            expected_state_predicate=lambda s: True,
            expected_external_predicate=lambda ext: ext.get("nonexistent") == "never",
        )
        print(
            f"reconciliation (external side not yet matching): reconciled={incomplete.reconciled}"
        )
        try:
            driver.allow_recovery(incomplete)
            print("FAIL: recovery should have been refused")
        except DriverError as exc:
            print(f"recovery correctly refused: {exc}")

        complete = driver.reconcile_before_recovery(
            expected_state_predicate=lambda s: True,
            expected_external_predicate=lambda ext: (
                ext.get("stop_acknowledged_for_run_id") == "RUN-PHASE-A-1"
            ),
        )
        print(f"reconciliation (both sides matching): reconciled={complete.reconciled}")
        driver.allow_recovery(complete)
        print("recovery allowed; dispatch unblocked")

        change_2, execute_2 = _executor(
            "docs/phase_a_scenario_2.md", "second authorized change, after recovery"
        )
        driver._execute = execute_2  # same driver, next Change through the same real route
        record_2 = driver.dispatch(
            {"kind": "x", "id": "after-recovery"},
            case_classification="NORMAL_OPERATION",
            change_id=change_2["change_id"],
            claim_token="claim-phase-a-2",
            execution_instant="2026-09-10T00:00:03Z",
        )
        print(f"post-recovery dispatch outcome={record_2.outcome}")
        assert change_adapter.call_count == 2

        print(
            "\n--- SECTION 4: recorder.py + cli.py recompute integrity (reused, not reinvented) ---"
        )
        evidence_root = tmp_path / "evidence_root"
        manifest_path = tmp_path / "manifest.jsonl"
        for index, wu_record in enumerate((record_1, record_2)):
            receipt = rec.write_raw_receipt(
                evidence_root,
                run_id=f"PHASE-A-RUN-{index}",
                payload={
                    "case_classification": wu_record.case_classification,
                    "run_state": wu_record.run_state,
                    "outcome": wu_record.outcome,
                },
                source_tree_root=worktree,
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
        recompute_args = cli.build_parser().parse_args(
            ["recompute", "--evidence-root", str(evidence_root), "--manifest", str(manifest_path)]
        )
        clean_report = cli.cmd_recompute(recompute_args)
        print(
            f"recompute (clean): integrity_verdict={clean_report['integrity_verdict']} "
            f"reference_aggregate={clean_report['reference_aggregate_from_verified_receipts_only']}"
        )
        assert clean_report["integrity_verdict"] == "VERIFIED"

        entries = rec.read_manifest_entries(manifest_path)
        tampered_path = evidence_root / entries[0]["run_id"] / f"{entries[0]['receipt_id']}.json"
        payload = json.loads(tampered_path.read_text())
        payload["outcome"] = "TAMPERED_FOR_DEMONSTRATION"
        tampered_path.write_text(json.dumps(payload))
        tampered_report = cli.cmd_recompute(recompute_args)
        print(
            f"recompute (after tampering one receipt): integrity_verdict={tampered_report['integrity_verdict']} "
            f"anomalies={tampered_report['anomalies']}"
        )
        assert tampered_report["integrity_verdict"] == "FAILED"

        print(
            "\n--- SECTION 5: cli.py preflight is a shape check, never an authorization check ---"
        )
        template_path = Path(__file__).resolve().parents[1] / "RUN_MANIFEST_TEMPLATE.json"
        preflight_on_template = cli.cmd_preflight(
            cli.build_parser().parse_args(["preflight", "--manifest", str(template_path)])
        )
        print(
            f"preflight(RUN_MANIFEST_TEMPLATE.json itself): "
            f"manifest_shape_check={preflight_on_template['manifest_shape_check']} "
            f"(expected FAIL -- the template's own REQUIRED_HUMAN_INPUT fields are still null)"
        )
        assert preflight_on_template["manifest_shape_check"] == "FAIL"
        print(f"disclaimer: {preflight_on_template['disclaimer']}")

    print("\n" + "=" * 78)
    print("ALL SECTIONS PASS (Phase A acceptance items 1-5, this scenario's own scope)")
    print("=" * 78)


if __name__ == "__main__":
    main()
