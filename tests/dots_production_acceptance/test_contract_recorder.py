"""Contract tests for recorder.py per PROTOCOL.md Sec.8.

Tracks #116 (WU2). Exercises the real canonical Evidence/Reflow/Store routes end-to-end
-- ``derive_evidence`` and (for the connection point a prior revision got wrong)
``reflow()``'s own ``provenance_only_evidence_requests`` parameter -- never a parallel
reimplementation, mirroring ``tests/unit/reflow/test_route_composition.py``'s own "real
composition chain, nothing hand-assembled" pattern.

SR1 correction (this revision): a prior revision's ``test_commit_evidence_record_...``
exercised ``recorder.commit_evidence_record``, a function that hand-built a
``next_state``/``transition`` and committed it directly -- a real Store write, but one
that bypassed Evidence/closure evaluation, i.e. a second, parallel Reflow this module
had no business inventing. That function has been removed from ``recorder.py``; this
file's ``test_a_recorded_evidence_candidate_reaches_store_through_the_real_reflow_route``
replaces it, demonstrating the actual existing connection point instead.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from tests.dots_production_acceptance import recorder as rec
from tests.evidence_helpers import before_observation_request, observation_evidence_request
from tests.reflow_helpers import (
    base_closure_request,
    fixture_difference,
    fixture_genesis_lifecycle_event,
    fixture_policy,
)
from tests.state_helpers import SCHEMA_ROOT, genesis_source_snapshot_records, initial_state

from manosube_agent_civilization.evidence import EVIDENCE_REFERENCE_KIND, derive_evidence
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


def test_write_raw_receipt_lands_outside_source_tree_and_manifest_is_append_only(tmp_path: Path) -> None:
    source_tree = tmp_path / "repo"
    source_tree.mkdir()
    evidence_root = tmp_path / "evidence_root"

    receipt = rec.write_raw_receipt(
        evidence_root, run_id="RUN-1", payload={"k": "v"}, source_tree_root=source_tree
    )

    assert receipt.raw_path.exists()
    assert source_tree not in receipt.raw_path.parents
    assert receipt.receipt_id.startswith("RCT-")
    assert receipt.sha256 in receipt.receipt_id

    manifest_path = tmp_path / "manifest.jsonl"
    entry = rec.ManifestEntry(
        receipt_id=receipt.receipt_id, sha256=receipt.sha256, run_id="RUN-1", recorded_at=receipt.recorded_at
    )
    rec.append_manifest_entry(manifest_path, entry)
    rec.append_manifest_entry(manifest_path, entry)

    entries = rec.read_manifest_entries(manifest_path)
    assert len(entries) == 2, "append_manifest_entry must never overwrite a prior line"
    assert entries[0]["receipt_id"] == receipt.receipt_id


def test_write_raw_receipt_refuses_an_evidence_root_inside_the_source_tree(tmp_path: Path) -> None:
    source_tree = tmp_path / "repo"
    source_tree.mkdir()

    with pytest.raises(rec.RecorderError, match="must be outside source_tree_root"):
        rec.write_raw_receipt(
            source_tree / "evidence", run_id="RUN-1", payload={}, source_tree_root=source_tree
        )

    with pytest.raises(rec.RecorderError, match="must be outside source_tree_root"):
        rec.write_raw_receipt(source_tree, run_id="RUN-1", payload={}, source_tree_root=source_tree)


def test_write_raw_receipt_refuses_an_absolute_path_run_id_escaping_into_the_source_tree(
    tmp_path: Path,
) -> None:
    # Exact repro #1 from the review: an absolute path as run_id. pathlib's own "/"
    # operator silently discards the left operand when the right one is absolute
    # (Path("/a/b") / "/etc/passwd" == Path("/etc/passwd")), so an unvalidated run_id
    # could replace evidence_root entirely and land the receipt inside source_tree.
    source_tree = tmp_path / "repo"
    source_tree.mkdir()
    evidence_root = tmp_path / "evidence_root"
    evidence_root.mkdir()

    with pytest.raises(rec.RecorderError, match="single safe identifier"):
        rec.write_raw_receipt(
            evidence_root, run_id=str(source_tree), payload={}, source_tree_root=source_tree
        )
    assert not any(source_tree.rglob("RCT-*.json")), "no receipt must have landed inside source_tree"


def test_write_raw_receipt_refuses_a_dotdot_run_id_escaping_evidence_root(tmp_path: Path) -> None:
    # Exact repro #2 from the review: run_id="../repo" climbing out of evidence_root.
    source_tree = tmp_path / "repo"
    source_tree.mkdir()
    evidence_root = tmp_path / "evidence_root"
    evidence_root.mkdir()

    with pytest.raises(rec.RecorderError, match="single safe identifier"):
        rec.write_raw_receipt(evidence_root, run_id="../repo", payload={}, source_tree_root=source_tree)
    assert not any(source_tree.rglob("RCT-*.json")), "no receipt must have landed inside source_tree"


def test_read_manifest_entries_on_a_missing_file_is_an_empty_list_not_an_error(tmp_path: Path) -> None:
    assert rec.read_manifest_entries(tmp_path / "does-not-exist.jsonl") == []


def test_record_evidence_via_canonical_route_is_exactly_derive_evidence_no_second_logic() -> None:
    request = observation_evidence_request()

    via_recorder = rec.record_evidence_via_canonical_route(request)
    via_direct_call = derive_evidence(deepcopy(request))

    assert via_recorder == via_direct_call, (
        "record_evidence_via_canonical_route must be a pure pass-through to the one "
        "existing Evidence owner -- any divergence here would mean this module invented "
        "a second derivation path"
    )
    assert via_recorder["evidence_id"]


def test_a_recorded_evidence_candidate_reaches_store_through_the_real_reflow_route(
    tmp_path: Path,
) -> None:
    """The actual connection point for a meaningful State update: the same evidence
    *request* shape ``rec.record_evidence_via_canonical_route`` derives from is passed
    into the real ``reflow()``'s own ``provenance_only_evidence_requests`` parameter,
    which itself calls the real ``derive_evidence`` and persists the result through its
    own real, atomic ``commit_reflow`` transaction -- never through anything recorder.py
    builds. The Observation the evidence candidate's own request names is committed
    directly first, as genuine fixture preparation (clearly separate from, and never
    presented as, the operational recording path under test) -- Observations are not
    this module's concern; Reflow's own reference-closure check simply requires one to
    already resolve before it will admit an Evidence record that refers to it."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = initial_state()
    project_state["objective_revision_id"] = fixture_difference()["objective_revision_ref"]["id"]
    project_state["semantic_fingerprint"] = fingerprint_project_state(
        project_state, schema_root=SCHEMA_ROOT
    ).as_dict()

    # Fixture preparation only (per the review's own distinction): commit the
    # Observation the evidence candidate's request refers to, so its embedded
    # observation_ref resolves. This is not the recorder path under test.
    before_obs_request = before_observation_request()
    before_observation = observe(before_obs_request)["observations"][-1]
    store.initialize(
        project_state["project_id"],
        project_state,
        records=[
            *genesis_source_snapshot_records(project_state),
            ("observation", before_observation["observation_id"], before_observation),
        ],
    )

    # The recorder path under test: build the evidence candidate's own request exactly
    # as rec.record_evidence_via_canonical_route would receive it.
    evidence_request = observation_evidence_request(observation=before_obs_request)
    expected_evidence = rec.record_evidence_via_canonical_route(deepcopy(evidence_request))

    difference = fixture_difference()
    policy = fixture_policy(difference)

    result = reflow(
        store,
        project_id=project_state["project_id"],
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

    # A real Reflow outcome (BLOCKED here -- nothing about this test claims a closure;
    # the point is that the evidence candidate's own commit is real regardless of it).
    assert result["decision"]["to_status"] == "BLOCKED"
    assert store.load_current(project_state["project_id"]) == result["committed_state"]

    resolved = store.resolve_record(
        project_state["project_id"], EVIDENCE_REFERENCE_KIND, expected_evidence["evidence_id"]
    )
    assert resolved == expected_evidence, (
        "the Evidence record recorder.py's own candidate request derives must be the "
        "exact record reflow() independently re-derived and committed -- proving the "
        "candidate genuinely reached Store through the real Reflow route, not a "
        "recorder-owned shortcut"
    )

    # recorder.py itself must own no commit-of-meaningful-state function anymore.
    assert not hasattr(rec, "commit_evidence_record")
