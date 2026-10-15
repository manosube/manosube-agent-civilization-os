"""Contract tests for recorder.py per PROTOCOL.md Sec.8.

Tracks #116 (WU2). Exercises the real canonical Evidence/Store routes end-to-end --
``derive_evidence`` and ``FileStateStore.commit`` -- never a parallel reimplementation,
mirroring ``tests/integration/binding/test_bounded_technical_review_route.py``'s own
"real FileStateStore + bind_project, then call the real route" pattern.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from tests.dots_production_acceptance import recorder as rec
from tests.evidence_helpers import observation_evidence_request
from tests.fixtures.dots_production_acceptance_world import bound
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state


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


def test_commit_evidence_record_goes_through_the_same_store_commit_every_owner_uses(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    project_id = world["project_id"]
    genesis_state = world["genesis_state"]

    evidence = derive_evidence(observation_evidence_request())

    successor = deepcopy(genesis_state)
    successor["state_revision"] = genesis_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = genesis_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": "TX-WU2-RECORDER-0001"}
    successor["semantic_fingerprint"] = fingerprint_project_state(successor, schema_root=SCHEMA_ROOT).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": "TX-WU2-RECORDER-0001",
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": genesis_state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": genesis_state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": "2026-10-15T09:00:00Z",
    }

    committed = rec.commit_evidence_record(
        store,
        project_id=project_id,
        expected_revision=genesis_state["state_revision"],
        expected_fingerprint=genesis_state["semantic_fingerprint"],
        next_state=successor,
        transition=event,
        evidence=evidence,
    )

    assert committed["state_revision"] == genesis_state["state_revision"] + 1

    from manosube_agent_civilization.evidence import EVIDENCE_REFERENCE_KIND

    resolved = store.resolve_record(project_id, EVIDENCE_REFERENCE_KIND, evidence["evidence_id"])
    assert resolved == evidence, "the committed record must be resolvable back, byte-identical"
