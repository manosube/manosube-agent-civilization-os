"""P18-R1-F1 (Structural Review Round 1, ADOPT_P18_R1_STRUCTURAL_CORRECTIONS) and P18-R2-F1
(Structural Review Round 2, ADOPT_P18_R2_STRUCTURAL_CORRECTIONS): independent after-state
re-observation gates ``VERIFIED``.

(a) **Negative control (P18-R1-F1)**: a receipt claiming ``outcome == "SUCCEEDED"`` whose own
embedded ``independent_after_state_observation`` disagrees (forged/mismatched, or simply not
``"MATCHED"``) must be refused by ``route_change_execution_to_evidence`` -- never silently
derived as ``VERIFIED``.

(a2) **Negative control (P18-R2-F1)**: R2_F1_NEGATIVE -- a receipt claiming ``outcome ==
"SUCCEEDED"`` whose own embedded ``independent_after_state_observation`` is *forged to agree*
(``"MATCHED"``, passing the P18-R1-F1 check above cleanly), but whose *actual* real on-disk bytes
(written directly by this test, independently of anything the receipt claims) genuinely disagree
with what the receipt's own ``operation`` requested, must still be refused -- proving the fix is
not merely re-trusting the same embedded field a second time under a different name: this is a
real, independent disagreement this hand-off's own SECOND, handoff-time-only re-read discovers.

(b) **Positive control (P18-R1-F1 and R2_F1_POSITIVE)**: a genuine ``execute()`` call through the
real route, with a real ``ControlledFilesystemAdapter`` writing the exact requested content to
real disk, must produce a receipt whose own ``independent_after_state_observation["outcome"] ==
"MATCHED"``, and ``route_change_execution_to_evidence`` must derive ``VERIFIED`` for it -- and the
SECOND, independently-performed, handoff-time re-read this hand-off itself performs must itself
independently confirm the real, freshly-read on-disk content (never merely re-trust the receipt's
own embedded field).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
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
    plant_terminal_receipt,
)

from manosube_agent_civilization.change_executor import evidence_handoff as evidence_handoff_module
from manosube_agent_civilization.change_executor.errors import ChangeExecutorError
from manosube_agent_civilization.change_executor.evidence_handoff import (
    route_change_execution_to_evidence,
)
from manosube_agent_civilization.change_executor.route import compose_change_executor

_ADAPTER_IDENTITY = {"kind": "controlled_filesystem_adapter", "version": "0.1"}


def _rebind_project(value: Any, old: str, new: str) -> Any:
    if isinstance(value, dict):
        return {key: _rebind_project(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [_rebind_project(item, old, new) for item in value]
    return new if value == old else value


# --------------------------------------------------------------------------------------- #
# (a) negative: a forged/disagreeing independent_after_state_observation on a SUCCEEDED
# receipt is refused, never derived as VERIFIED.
# --------------------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "forged_observation",
    (
        {
            "outcome": "MISMATCH",
            "checked_files": [{"path": "docs/x.md", "kind": "write", "status": "MISMATCH"}],
        },
        {"outcome": "NOT_PERFORMED", "checked_files": []},
        {
            "outcome": "MISSING",
            "checked_files": [{"path": "docs/x.md", "kind": "write", "status": "MISSING"}],
        },
    ),
)
def test_forged_succeeded_receipt_with_disagreeing_reobservation_is_refused(
    tmp_path: Path, forged_observation: dict[str, Any]
) -> None:
    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)
    result = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE", writes=[{"path": "docs/x.md", "content_utf8": "hello"}]
        ),
        paths=["docs/x.md"],
    )
    change = result["change"]

    worktree = git_worktree(tmp_path)
    boundary = execution_boundary_for(worktree_root=str(worktree))

    # A genuine, real, schema-valid, self-consistent receipt (built by the real
    # engine.build_change_execution_receipt, never hand-forged) -- claiming SUCCEEDED, but with
    # its own independent_after_state_observation deliberately disagreeing. route.py itself would
    # never construct this combination (F1's own gate at classification time); this receipt is
    # planted directly to prove evidence_handoff's own defensive re-check refuses it regardless.
    forged = plant_terminal_receipt(
        store,
        project_id,
        change,
        result["decision"],
        boundary,
        _ADAPTER_IDENTITY,
        project_binding_id=info["project_binding_id"],
        worktree_root=str(worktree),
        claim_token="forged-claim",  # noqa: S106
        outcome="SUCCEEDED",
        performed_result_summary={
            "files_written": ["docs/x.md"],
            "bytes_written": 5,
            "files_deleted": [],
        },
        independent_after_state_observation=forged_observation,
    )

    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    # (P18-R2-F1, Structural Review Round 2) route_change_execution_to_evidence now constructs
    # verification_observation_request itself, from a second, independent, handoff-time-only
    # re-read of the real resulting filesystem state -- it must not be caller-supplied.
    evidence_request["verification_observation_request"] = None
    with pytest.raises(ChangeExecutorError):
        route_change_execution_to_evidence(store, forged, project_id, evidence_request)


# --------------------------------------------------------------------------------------- #
# (a2) R2_F1_NEGATIVE: a receipt whose own embedded independent_after_state_observation is
# forged to MATCH, but whose real on-disk bytes genuinely disagree, is still refused -- proving
# the fix is a real, independent disagreement (this hand-off's own second, handoff-time-only
# re-read), never a re-check of the same embedded dict route.py itself already computed.
# --------------------------------------------------------------------------------------- #


def test_second_independent_reread_disagreement_refuses_a_receipt_forged_to_match(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)
    requested_content = "the real requested content"
    result = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": "docs/second-reread.md", "content_utf8": requested_content}],
        ),
        paths=["docs/second-reread.md"],
    )
    change = result["change"]

    worktree = git_worktree(tmp_path)
    boundary = execution_boundary_for(worktree_root=str(worktree))

    # Real, DIFFERENT bytes are written directly to disk -- never through the adapter, never
    # matching what the receipt's own operation requests -- simulating a receipt whose own
    # embedded independent_after_state_observation was forged (or is simply stale/wrong) to
    # claim MATCHED regardless of what is actually on disk.
    (worktree / "docs").mkdir(parents=True, exist_ok=True)
    (worktree / "docs" / "second-reread.md").write_text(
        "DIFFERENT bytes than what was ever requested", encoding="utf-8"
    )

    forged_matching = plant_terminal_receipt(
        store,
        project_id,
        change,
        result["decision"],
        boundary,
        _ADAPTER_IDENTITY,
        project_binding_id=info["project_binding_id"],
        worktree_root=str(worktree),
        claim_token="forged-matching-claim",  # noqa: S106
        outcome="SUCCEEDED",
        performed_result_summary={
            "files_written": ["docs/second-reread.md"],
            "bytes_written": len(requested_content.encode("utf-8")),
            "files_deleted": [],
        },
        independent_after_state_observation={
            "outcome": "MATCHED",
            "checked_files": [
                {"path": "docs/second-reread.md", "kind": "write", "status": "MATCHED"}
            ],
        },
    )

    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    evidence_request["verification_observation_request"] = None
    with pytest.raises(ChangeExecutorError):
        route_change_execution_to_evidence(store, forged_matching, project_id, evidence_request)


# --------------------------------------------------------------------------------------- #
# (b) positive: a genuine execute() call's own receipt carries a MATCHED independent
# re-observation, and route_change_execution_to_evidence genuinely derives VERIFIED for it.
# --------------------------------------------------------------------------------------- #


def test_genuine_execution_carries_a_matched_independent_reobservation_and_derives_verified(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)

    content = "# Independent Reobservation Proof\n\nWritten by a real adapter call.\n"
    result = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": "docs/reobservation_proof.md", "content_utf8": content}],
        ),
        paths=["docs/reobservation_proof.md"],
    )
    change = result["change"]

    worktree_root = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = compose_change_executor(
        store,
        project_id=project_id,
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree_root)),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )

    outcome = execute(
        change["change_id"],
        claim_token="genuine-reobservation-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    receipt = outcome["receipt"]
    assert receipt["outcome"] == "SUCCEEDED"
    assert receipt["independent_after_state_observation"] == {
        "outcome": "MATCHED",
        "checked_files": [
            {"path": "docs/reobservation_proof.md", "kind": "write", "status": "MATCHED"}
        ],
    }

    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    # (P18-R2-F1, Structural Review Round 2) route_change_execution_to_evidence now constructs
    # verification_observation_request itself, from a second, independent, handoff-time-only
    # re-read of the real resulting filesystem state -- it must not be caller-supplied.
    evidence_request["verification_observation_request"] = None
    evidence = route_change_execution_to_evidence(store, receipt, project_id, evidence_request)
    assert evidence["verification_result_provenance"]["status"] == "VERIFIED"
    assert (
        evidence["verification_result_provenance"]["observations"][
            "independent_after_state_observation"
        ]
        == receipt["independent_after_state_observation"]
    )

    # R2_F1_POSITIVE: the SECOND, independently-performed, handoff-time-only re-read this
    # hand-off itself performs (never the receipt's own embedded field) genuinely reflects real,
    # freshly-read file content -- proven directly, in white-box fashion, by calling the same
    # internal re-read this hand-off calls and independently confirming its own real snapshot
    # digests equal a real, independently-computed SHA-256 of the actual bytes on disk at test
    # time.
    snapshots, _occurrences, matches = (
        evidence_handoff_module._second_independent_after_state_reread(
            receipt["operation"],
            receipt["target"]["worktree_root"],
            captured_at="2026-08-30T10:00:00Z",
        )
    )
    assert matches is True
    assert len(snapshots) == 1
    real_bytes = (worktree_root / "docs" / "reobservation_proof.md").read_bytes()
    assert snapshots[0]["content_digest"] == "sha256:" + hashlib.sha256(real_bytes).hexdigest()
    assert snapshots[0]["source_locator"] == "docs/reobservation_proof.md"


# --------------------------------------------------------------------------------------- #
# (c) an adapter that writes the wrong content is caught: outcome is reclassified as
# REOBSERVATION_MISMATCH, and the hand-off derives FAILED, never VERIFIED.
# --------------------------------------------------------------------------------------- #


class _LyingAdapter:
    """A real adapter (delegates to a genuine ``ControlledFilesystemAdapter``) that writes
    deliberately *different* content than requested, then falsely reports the requested content
    was written -- the exact scenario independent re-observation exists to catch: the adapter's
    own self-reported facts (``files_written``) claim full success, but the actual on-disk bytes
    disagree with what was requested."""

    def __init__(self) -> None:
        from manosube_agent_civilization.change_executor.adapter import ControlledFilesystemAdapter

        self._inner = ControlledFilesystemAdapter(
            executor_identity="controlled_filesystem_adapter", executor_version="0.1"
        )
        self.call_count = 0

    def execute(self, operation: Any, *, worktree_root: str) -> dict[str, Any]:
        self.call_count += 1
        tampered_operation = {
            **operation,
            "file_writes": [
                {"path": entry["path"], "content_utf8": "TAMPERED-CONTENT-NEVER-REQUESTED"}
                for entry in operation.get("file_writes", [])
            ],
        }
        raw: dict[str, Any] = self._inner.execute(tampered_operation, worktree_root=worktree_root)
        return raw


def test_adapter_writing_wrong_content_is_caught_as_reobservation_mismatch(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)

    result = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": "docs/lied-about.md", "content_utf8": "the real requested content"}],
        ),
        paths=["docs/lied-about.md"],
    )
    change = result["change"]

    worktree_root = git_worktree(tmp_path)
    adapter = _LyingAdapter()
    execute = compose_change_executor(
        store,
        project_id=project_id,
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree_root)),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )

    outcome = execute(
        change["change_id"],
        claim_token="lied-about-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    receipt = outcome["receipt"]
    assert receipt["outcome"] == "REOBSERVATION_MISMATCH"
    assert receipt["independent_after_state_observation"]["outcome"] == "MISMATCH"
    assert adapter.call_count == 1

    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    # (P18-R2-F1, Structural Review Round 2) route_change_execution_to_evidence now constructs
    # verification_observation_request itself, from a second, independent, handoff-time-only
    # re-read of the real resulting filesystem state -- it must not be caller-supplied.
    evidence_request["verification_observation_request"] = None
    evidence = route_change_execution_to_evidence(store, receipt, project_id, evidence_request)
    assert evidence["verification_result_provenance"]["status"] == "FAILED"

    # A second call for the identical slot replays the identical REOBSERVATION_MISMATCH receipt
    # -- never re-calling the adapter, never silently upgrading it.
    replay = execute(
        change["change_id"],
        claim_token="lied-about-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
    )
    assert replay["replay"] is True
    assert replay["receipt"] == receipt
    assert adapter.call_count == 1
