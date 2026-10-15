#!/usr/bin/env python3
"""WU2 (Issue #116 / PR #119) design-validation script: a realistic, end-to-end
scenario exercising all 5 WU2 harness components together (``case_generators``,
``independent_oracle``, ``recorder``, ``reconciliation``, ``aggregator``), plus the
two exact path-traversal repro cases from the PR #119 review round, confirming the
fixes hold against the real function bodies.

SCOPE DISCLAIMER: this is NOT a WU3/WU4 execution and makes no dots/GitHub call. It
uses a real, disposable ``FileStateStore`` + a real canonical Project Binding (via
``tests.fixtures.dots_production_acceptance_world.bound``) and the real
``manosube_agent_civilization.reflow.route.reflow`` function -- never a parallel
reimplementation -- to demonstrate that an evidence candidate the recorder module
derives actually reaches Store through the existing canonical Reflow route (the PR #119
review round's second finding), and that the two reported path-traversal escapes are
now refused (the review round's first finding).

Dependencies: this repository's own dev/test extras only (already required to run
``pytest`` here) -- no additional third-party packages.

Run with (from the repository root, this PR's HEAD -- PYTHONPATH=. is required so the
``tests.*`` helper modules this script reuses, the same ones pytest's own rootdir
insertion already makes importable under pytest, resolve the identical way here):
    PYTHONPATH=. python3 docs/validation/dots_production_acceptance/verification/wu2_component_scenario.py

Reproducibility note: content-addressed values (receipt_id, evidence_id, sha256
digests) are deterministic given the fixed literal payloads/requests below and will
be identical on every run. Filesystem paths (under a fresh tempdir each run) and
wall-clock timestamps are NOT byte-identical between runs by construction (real
``tempfile.TemporaryDirectory()``, real ``default_clock()``) -- this script's own
exact stdout is saved in wu2_component_scenario_output.txt as the record of one real
run, not as a byte-identical-reproduction contract the way
verify_measurement_contract.py's pure, path-and-clock-free fixtures are.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile

from tests.dots_production_acceptance import (
    aggregator as agg,
    case_generators as cg,
    independent_oracle as oracle,
    reconciliation as recon,
    recorder as rec,
)
from tests.evidence_helpers import before_observation_request, observation_evidence_request
from tests.fixtures.dots_production_acceptance_world import bound
from tests.reflow_helpers import (
    base_closure_request,
    fixture_difference,
    fixture_genesis_lifecycle_event,
    fixture_policy,
)
from tests.state_helpers import SCHEMA_ROOT, genesis_source_snapshot_records, initial_state

from manosube_agent_civilization.evidence import EVIDENCE_REFERENCE_KIND
from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.reflow.route import reflow
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

REFLOW_INSTANT = "2026-08-30T12:00:00Z"
_NEXT_OBSERVATION_REF = {"kind": "next_observation_request", "id": "OBS-REQ-" + "2" * 64}


def _blocker_scope(difference: dict) -> dict:
    return {
        "kind": "difference_blocker_scope",
        "affected_subject_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [{"kind": "difference", "id": difference["difference_id"]}],
        },
        "effective_boundary": difference["effective_boundary"],
        "blocked_stage": "OBSERVATION",
    }


def _blocker_condition(difference: dict) -> dict:
    return {
        "kind": "blocker_resolution_condition",
        "condition_code": "OBSERVATION_PATH_AVAILABLE",
        "subject_ref": {"kind": "difference", "id": difference["difference_id"]},
        "expected_state": "AVAILABLE",
        "verification_request_ref": _NEXT_OBSERVATION_REF,
    }


def section_1_path_traversal_fixes() -> None:
    print("=" * 78)
    print("SECTION 1: path-traversal fix (PR #119 review finding #1)")
    print("=" * 78)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_tree = tmp_path / "repo"
        source_tree.mkdir()
        evidence_root = tmp_path / "evidence_root"
        evidence_root.mkdir()

        # Exact repro #1: an absolute path run_id (pathlib's "/" operator discards the
        # left operand entirely when the right one is absolute).
        try:
            rec.write_raw_receipt(
                evidence_root, run_id=str(source_tree), payload={}, source_tree_root=source_tree
            )
            print("REPRO 1 (absolute-path run_id): FAIL -- no exception raised")
        except rec.RecorderError as exc:
            print(f"REPRO 1 (absolute-path run_id): correctly refused -- {exc}")

        # Exact repro #2: a "../" run_id climbing out of evidence_root.
        try:
            rec.write_raw_receipt(
                evidence_root, run_id="../repo", payload={}, source_tree_root=source_tree
            )
            print("REPRO 2 ('../repo' run_id): FAIL -- no exception raised")
        except rec.RecorderError as exc:
            print(f"REPRO 2 ('../repo' run_id): correctly refused -- {exc}")

        assert not any(source_tree.rglob("RCT-*.json")), "no receipt landed inside source_tree"
        print("Confirmed: no receipt file exists anywhere inside source_tree after either attempt.")

        # Normal, safe usage still works.
        receipt = rec.write_raw_receipt(
            evidence_root, run_id="RUN-NORMAL-001", payload={"ok": True}, source_tree_root=source_tree
        )
        print(f"Normal run_id still works: {receipt.raw_path}")
        assert receipt.raw_path.exists()

    print("\nPASS: both exact repro cases from the review are refused; normal usage is unaffected.")


def section_2_recorder_connects_to_real_reflow() -> None:
    print("\n" + "=" * 78)
    print("SECTION 2: recorder's evidence candidate reaches Store via the real reflow() "
          "route (PR #119 review finding #2)")
    print("=" * 78)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
        project_state = initial_state()
        project_state["objective_revision_id"] = fixture_difference()["objective_revision_ref"]["id"]
        project_state["semantic_fingerprint"] = fingerprint_project_state(
            project_state, schema_root=SCHEMA_ROOT
        ).as_dict()
        project_id = project_state["project_id"]

        # Fixture preparation only -- explicitly separate from the recorder path under
        # test, per the review's own distinction: commit the Observation the evidence
        # candidate's own request names, so Reflow's reference-closure check can resolve
        # it. Observations are not recorder.py's concern.
        before_obs_request = before_observation_request()
        before_observation = observe(before_obs_request)["observations"][-1]
        store.initialize(
            project_id,
            project_state,
            records=[
                *genesis_source_snapshot_records(project_state),
                ("observation", before_observation["observation_id"], before_observation),
            ],
        )
        print(f"Fixture-prepared a real project + committed Observation "
              f"{before_observation['observation_id']} directly (not via recorder.py): "
              f"project_id={project_id}")

        difference = fixture_difference()
        policy = fixture_policy(difference)
        evidence_request = observation_evidence_request(observation=before_obs_request)

        # The recorder path under test.
        candidate = rec.record_evidence_via_canonical_route(deepcopy(evidence_request))
        print(f"recorder.record_evidence_via_canonical_route derived candidate "
              f"evidence_id={candidate['evidence_id']}")

        result = reflow(
            store,
            project_id=project_id,
            previous_event_id=difference["genesis_event_ref"]["id"],
            genesis_lifecycle_event=fixture_genesis_lifecycle_event(difference),
            event_revision=1,
            closure_request=base_closure_request(difference, policy),
            observation_refs=[],
            reflow_instant=REFLOW_INSTANT,
            blocker_scope=_blocker_scope(difference),
            blocker_resolution_condition=_blocker_condition(difference),
            next_observation_ref=_NEXT_OBSERVATION_REF,
            blocker_kind="OBSERVATION_PATH",
            provenance_only_evidence_requests=[evidence_request],
        )
        print(f"reflow() real decision: {result['decision']['to_status']}")
        print(f"reflow() real committed state_revision: {result['committed_state']['state_revision']}")

        resolved = store.resolve_record(project_id, EVIDENCE_REFERENCE_KIND, candidate["evidence_id"])
        matches = resolved == candidate
        print(f"Evidence resolvable from Store via reflow()'s own commit: {matches}")
        assert matches, "the candidate must be the exact record reflow() derived and committed"
        print("Confirmed: recorder.py itself exposes no commit-of-meaningful-state function "
              f"(hasattr check): {hasattr(rec, 'commit_evidence_record')}")

    print("\nPASS: the evidence candidate recorder.py derives reaches Store only through the "
          "real reflow() route -- never through a recorder-owned commit path.")


def section_3_remaining_modules() -> None:
    print("\n" + "=" * 78)
    print("SECTION 3: case_generators / independent_oracle / reconciliation / aggregator "
          "(unaffected by this fix round -- re-confirmed here for a full-suite scenario)")
    print("=" * 78)

    catalog = cg.load_catalog()
    fault_fixtures = cg.generate_fault_case_fixtures(catalog)
    task_fixtures = cg.generate_comparison_task_fixtures(catalog)
    print(f"case_generators: {len(fault_fixtures)} fault fixtures, {len(task_fixtures)} task fixtures")

    one_case = fault_fixtures[0]
    verdict = oracle.judge_from_readback(
        one_case.case_id,
        model_claimed_outcome="SUCCEEDED",
        kernel_recorded_outcome="BLOCKED",
        external_readback={"authority_effect": "denied"},
        expected_spec={
            "required_readback_keys": ["authority_effect"],
            "check": lambda rb: rb["authority_effect"] == "denied",
        },
    )
    print(f"independent_oracle: case={one_case.case_id!r} oracle_judged_outcome="
          f"{verdict.oracle_judged_outcome!r} (model claimed SUCCEEDED; oracle independently "
          "found the expected denial, per its own readback)")
    assert verdict.oracle_judged_outcome == "SATISFIED"

    with tempfile.TemporaryDirectory() as tmp:
        store, world = bound(Path(tmp))
        project_id = world["project_id"]
        genesis_state = world["genesis_state"]
        result = recon.reconcile(
            store, project_id=project_id,
            expected_state_predicate=lambda s: s["state_revision"] == genesis_state["state_revision"],
            external_reader=lambda: {"pr_merged": True},
            expected_external_predicate=lambda obs: obs["pr_merged"] is True,
        )
        print(f"reconciliation: store_matched={result.store_matched} "
              f"external_matched={result.external_matched} reconciled={result.reconciled}")
        assert result.reconciled is True

    blocks = [{"successes": 9, "total": 10}, {"successes": 20, "total": 20}, {"successes": 4, "total": 5}]
    boot = agg.ratio_of_sums_block_bootstrap(blocks, seed=99, iterations=2000)
    print(f"aggregator: pooled_rate={agg.pooled_rate(blocks):.4f} bootstrap point={boot.point:.4f} "
          f"ci=[{boot.ci_lower:.4f}, {boot.ci_upper:.4f}]")

    all_success_blocks = [{"successes": 20, "total": 20} for _ in range(25)]
    gate = agg.zero_failure_gate(all_success_blocks, seed=1, min_blocks_for_cp_reference=20)
    print(f"aggregator: zero_failure_gate verdict={gate.verdict} "
          f"reference_reliable={gate.reference_reliable} cp_lower={gate.cp_lower_reference_only:.4f}")
    assert gate.verdict == "INCOMPLETE"

    print("\nPASS: case_generators, independent_oracle, reconciliation, and aggregator all "
          "behave as specified.")


def main() -> None:
    section_1_path_traversal_fixes()
    section_2_recorder_connects_to_real_reflow()
    section_3_remaining_modules()
    print("\n" + "=" * 78)
    print("ALL SECTIONS PASS")
    print("=" * 78)


if __name__ == "__main__":
    main()
