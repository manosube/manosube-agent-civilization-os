"""P18-R1-F1 (Structural Review Round 1, ADOPT_P18_R1_STRUCTURAL_CORRECTIONS): independent
after-state re-observation gates ``VERIFIED``.

(a) **Negative control**: a receipt claiming ``outcome == "SUCCEEDED"`` whose own embedded
``independent_after_state_observation`` disagrees (forged/mismatched, or simply not
``"MATCHED"``) must be refused by ``route_change_execution_to_evidence`` -- never silently
derived as ``VERIFIED``.

(b) **Positive control**: a genuine ``execute()`` call through the real route, with a real
``ControlledFilesystemAdapter`` writing the exact requested content to real disk, must produce a
receipt whose own ``independent_after_state_observation["outcome"] == "MATCHED"``, and
``route_change_execution_to_evidence`` must derive ``VERIFIED`` for it.
"""

from __future__ import annotations

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
    operation_for,
    plant_terminal_receipt,
)

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

    worktree = tmp_path / "worktree"
    worktree.mkdir()
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
    with pytest.raises(ChangeExecutorError):
        route_change_execution_to_evidence(store, forged, project_id, evidence_request)


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

    worktree_root = tmp_path / "worktree"
    worktree_root.mkdir()
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
    evidence = route_change_execution_to_evidence(store, receipt, project_id, evidence_request)
    assert evidence["verification_result_provenance"]["status"] == "VERIFIED"
    assert (
        evidence["verification_result_provenance"]["observations"][
            "independent_after_state_observation"
        ]
        == receipt["independent_after_state_observation"]
    )


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

    worktree_root = tmp_path / "worktree"
    worktree_root.mkdir()
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
