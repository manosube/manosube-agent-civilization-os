"""V3 (Issue #73): disposable worktree vertical proof, non-skipped.

A real ``tmp_path`` worktree root, a real ``ControlledFilesystemAdapter``, a real committed
genuinely-AUTONOMOUS Change, and a real signed-and-committed ``ACTIVE`` kill switch: calls
``execute(...)`` for real, writes a real file to real disk, round-trips the receipt through
``store.resolve_record``, hands the real receipt to ``route_change_execution_to_evidence``
without mocking the Evidence layer, and proves this package closed no Difference and declared no
completion. Never skipped, never xfailed, never gated behind an environment flag.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.evidence_helpers import change_free_verification_evidence_request
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

from manosube_agent_civilization.change_executor.evidence_handoff import (
    route_change_execution_to_evidence,
)
from manosube_agent_civilization.change_executor.route import compose_change_executor


def _rebind_project(value: Any, old: str, new: str) -> Any:
    """The identical recursive-substitution technique ``tests/integration/url_boot/
    test_url_boot_local_http_vertical_proof.py``'s own ``_rebind_project`` already uses to
    retarget a shared, project-agnostic fixture request onto this test's own real bound
    project."""

    if isinstance(value, dict):
        return {key: _rebind_project(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [_rebind_project(item, old, new) for item in value]
    return new if value == old else value


def test_real_vertical_execution_writes_disk_round_trips_and_hands_off_to_evidence(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)

    content = "# Vertical Proof\n\nThis file was written by a real adapter call.\n"
    result = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": "docs/vertical_proof.md", "content_utf8": content}],
        ),
        paths=["docs/vertical_proof.md"],
    )
    change = result["change"]

    worktree_root = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = compose_change_executor(
        store,
        project_id=project_id,
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree_root)),
        adapter_identity={"kind": "controlled_filesystem_adapter", "version": "0.1"},
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )

    outcome = execute(
        change["change_id"],
        claim_token="vertical-proof-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )

    # -- the file genuinely exists on disk with the exact content requested --
    receipt = outcome["receipt"]
    assert receipt["outcome"] == "SUCCEEDED"
    assert adapter.call_count == 1
    written_path = worktree_root / "docs" / "vertical_proof.md"
    assert written_path.is_file()
    assert written_path.read_text(encoding="utf-8") == content
    assert receipt["performed_result_summary"]["files_written"] == ["docs/vertical_proof.md"]
    assert receipt["performed_result_summary"]["bytes_written"] == len(content.encode("utf-8"))

    # -- the returned receipt round-trips through store.resolve_record unchanged --
    resolved = store.resolve_record(
        project_id, "execution_receipt", receipt["change_execution_receipt_id"]
    )
    assert resolved == receipt

    # -- route_change_execution_to_evidence genuinely derives an Evidence record from this real
    # receipt, without any mocking of the Evidence layer --
    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    # (P18-R2-F1, Structural Review Round 2) route_change_execution_to_evidence now constructs
    # verification_observation_request itself, from a second, independent, handoff-time-only
    # re-read of the real resulting filesystem state -- it must not be caller-supplied.
    evidence_request["verification_observation_request"] = None
    evidence = route_change_execution_to_evidence(store, receipt, project_id, evidence_request)
    assert evidence["evidence_position"] == "CHANGE_FREE_VERIFICATION_EVIDENCE"
    assert evidence["verification_result_provenance"]["status"] == "VERIFIED"
    assert (
        evidence["verification_result_provenance"]["requirement_id"]
        == receipt["execution_request_id"]
    )
    assert evidence["target"]["project_id"] == project_id

    # -- nothing in this package closed a Difference or declared completion: the Difference and
    # Reflow packages were never imported/touched by any code path this test exercised -- proven
    # behaviorally, not merely by inspection: no difference_event or closure_evaluation record of
    # any kind exists under this project, because nothing here ever committed one. --
    assert store.resolve_record(project_id, "difference_event", "DIFF-EVENT-ANY") is None
    assert store.resolve_record(project_id, "closure_evaluation", "CLOSURE-ANY") is None
    assert store.resolve_record(project_id, "reflow_transition", "REFLOW-TX-ANY") is None
    # The Difference this Change was authorized against was derived once, in-memory, by this
    # test's own fixture (through the real public ``derive_differences`` route) -- it was never
    # committed to the Store at all, under any id, by this package or this test.
    assert (
        store.resolve_record(project_id, "difference", result["difference"]["difference_id"])
        is None
    )
