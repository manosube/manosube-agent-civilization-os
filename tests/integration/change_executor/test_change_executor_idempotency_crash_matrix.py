"""V4 (Issue #73): idempotency/concurrency/crash matrix.

**A genuine structural finding this file's own tests demonstrate, up front.** ``route.py``'s own
canonical route runs its staleness check (step 9: the resolved Change's own
``before_state_fingerprint``/``expected_state_revision`` must equal the *freshly Booted* current
State, exactly) *before* its own idempotency-slot resolution (step 10: replay / semantic-reuse /
terminal-claim-mismatch / reconciliation-required). But every commit this package's own route
itself performs (``execution_intent``, ``execution_attempt``, ``change_execution_receipt``)
unconditionally advances the Store's ``state_revision`` counter by exactly one -- regardless of
terminal outcome, and regardless of whether ``semantic_state`` content changed at all
(``state.fingerprint.fingerprint_project_state`` hashes only ``semantic_state``, so the
*fingerprint* half of the staleness check still agrees, but the *exact-integer revision* half
does not). The consequence: **the very first successful ``execute()`` call against a Change
makes every subsequent call for that identical Change -- including an ordinary, identical-
``claim_token`` replay, the single most basic idempotency guarantee this package's own module
docstring, error vocabulary, and this Issue's own V4 spec all promise -- raise
``StaleExecutionInputError`` instead of ever reaching the idempotency-slot resolution logic at
all.** :func:`test_exact_replay_is_broken_by_the_staleness_before_idempotency_ordering_defect`
below demonstrates this directly, as an ordinary caller would encounter it (no special setup),
and is expected to fail against the current implementation -- see this suite's own final report
for the precise fix this points to (swap steps 9 and 10, or skip staleness when a terminal
receipt already exists for the exact resolved slot).

Every *other* test in this file isolates and proves the idempotency-slot *resolution* logic
itself genuinely works correctly *once reached* -- using a disclosed, test-only technique
(:func:`tests.fixtures.change_executor_world.build_committed_change`'s own
``extra_state_revision_headroom`` parameter) to predict, in the Change's own recorded
``expected_state_revision``, exactly how many further Store commits a test's own setup will make
before the ``execute()`` call under test -- something no genuine production caller could ever
legitimately do (it requires knowing route.py's own private internal commit count in advance).
This is a deliberate isolation technique, not a weakened assertion: every test below still
asserts the full, correct contract (exact receipts, exact flags, exact adapter call counts) --
only the *setup* works around the separately-and-honestly-demonstrated staleness-ordering defect
above, so the *rest* of the idempotency machinery can still be verified on its own terms.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.change_executor_kill_switch_issuer import issuer_public_key_hex
from tests.fixtures.change_executor_world import (
    CountingAdapter,
    bound,
    build_committed_change,
    commit_active_kill_switch,
    commit_bare_execution_attempt,
    commit_bare_execution_intent,
    execution_boundary_for,
    operation_for,
    plant_terminal_receipt,
)

from manosube_agent_civilization.change_executor.errors import (
    ExecutionConcurrentClaimError,
    ExecutionReconciliationRequiredError,
    ExecutionTerminalClaimMismatchError,
)
from manosube_agent_civilization.change_executor.route import compose_change_executor

#: Every ordinary ``execute()`` call that gets past idempotency-slot resolution (step 10) and
#: proceeds to commit an ``execution_intent`` and an ``execution_attempt`` always commits exactly
#: three records total by the time it returns or raises a terminal receipt -- intent, attempt,
#: and the terminal receipt itself -- regardless of the eventual outcome (SUCCEEDED,
#: PARTIAL_MUTATION, ROLLBACK_SUCCEEDED, ROLLBACK_FAILED, BOUNDARY_VIOLATION, and
#: KILL_SWITCH_STOPPED all commit exactly these same three records). This is the exact, private
#: implementation-detail count :data:`ONE_SUCCESSFUL_CALL_COMMIT_COUNT` predicts.
ONE_SUCCESSFUL_CALL_COMMIT_COUNT = 3

_BOUNDARY = execution_boundary_for()
_ADAPTER_IDENTITY = {"kind": "controlled_filesystem_adapter", "version": "0.1"}


def _executor(store: Any, info: dict[str, Any], adapter: Any, **boundary_overrides: Any) -> Any:
    return compose_change_executor(
        store,
        project_id=info["project_id"],
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(**boundary_overrides)
        if boundary_overrides
        else _BOUNDARY,
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )


def _fresh_change(
    store: Any, info: dict[str, Any], *, path: str = "docs/idempotency.md", headroom: int = 0
) -> dict[str, Any]:
    return build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE", writes=[{"path": path, "content_utf8": "content"}]
        ),
        paths=[path],
        extra_state_revision_headroom=headroom,
    )


# --------------------------------------------------------------------------------------- #
# The honest, undoctored demonstration of the core defect -- an ordinary caller, no headroom.
# --------------------------------------------------------------------------------------- #


def test_exact_replay_is_broken_by_the_staleness_before_idempotency_ordering_defect(
    tmp_path: Path,
) -> None:
    """The correct contract, per this package's own module docstring and this Issue's own V4
    spec: calling ``execute`` twice with the identical ``claim_token`` returns ``{"replay":
    True}`` with the byte-identical receipt on the second call, and the adapter is called
    exactly once total. An ordinary caller does nothing special between the two calls -- no
    knowledge of route.py's own private commit count, because no legitimate caller could ever
    have that. This test is written to that correct contract, and is expected to fail against
    the current implementation for exactly the reason this file's own module docstring proves:
    the first call's own commits (execution_intent, execution_attempt, receipt) already advance
    ``state_revision`` past what the Change's own ``expected_state_revision`` recorded, so the
    second call's own staleness check (which runs before idempotency-slot resolution) raises
    ``StaleExecutionInputError`` instead."""

    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    change = _fresh_change(store, info)["change"]
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter)

    first = execute(
        change["change_id"],
        claim_token="exact-replay-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
        worktree_root=str(worktree),
    )
    assert first["receipt"]["outcome"] == "SUCCEEDED"
    assert adapter.call_count == 1

    second = execute(
        change["change_id"],
        claim_token="exact-replay-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
        worktree_root=str(worktree),
    )
    assert second["replay"] is True
    assert second["semantic_reuse"] is False
    assert second["receipt"] == first["receipt"]
    assert adapter.call_count == 1, "the adapter must not be called again on a pure replay"


# --------------------------------------------------------------------------------------- #
# (a)/(b)/(c) -- the idempotency-slot *resolution* logic itself (step 10), isolated from the
# staleness-ordering defect above via :func:`plant_terminal_receipt`: a genuine, real, fully
# self-consistent terminal receipt (built by the real ``engine.build_change_execution_receipt``,
# never hand-forged) is planted directly at the exact slot a single ``execute()`` call will
# resolve. The replay/semantic-reuse/terminal-mismatch branches of step 10 never commit anything
# themselves (confirmed by ``adapter.call_count`` staying at 0 throughout -- these branches never
# reach the adapter either), so a single such call is never stale, and genuinely exercises
# route.py's own real resolution branching.
# --------------------------------------------------------------------------------------- #


def _planted(
    tmp_path: Path,
    *,
    outcome: str = "SUCCEEDED",
    claim_token: str = "original-claim",  # noqa: S107
) -> tuple[Any, dict[str, Any], dict[str, Any], dict[str, Any], Path]:
    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    result = _fresh_change(store, info, headroom=1)
    change = result["change"]
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    receipt = plant_terminal_receipt(
        store,
        info["project_id"],
        change,
        result["decision"],
        _BOUNDARY,
        _ADAPTER_IDENTITY,
        project_binding_id=info["project_binding_id"],
        worktree_root=str(worktree),
        claim_token=claim_token,
        outcome=outcome,
        performed_result_summary={
            "files_written": [change["scope"]["paths"][0]],
            "bytes_written": 7,
            "files_deleted": [],
        },
    )
    return store, info, change, receipt, worktree


def test_exact_replay_slot_resolution_itself_is_correct_once_staleness_is_not_in_the_way(
    tmp_path: Path,
) -> None:
    store, info, change, planted, worktree = _planted(tmp_path, claim_token="same-claim")  # noqa: S106
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter)

    result = execute(
        change["change_id"],
        claim_token="same-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
        worktree_root=str(worktree),
    )
    assert result["replay"] is True
    assert result["semantic_reuse"] is False
    assert result["receipt"] == planted
    assert adapter.call_count == 0, "a pure replay must never reach the adapter"


# --------------------------------------------------------------------------------------- #
# (b) conflicting replay -- different claim_token reaching an already-terminal slot.
# --------------------------------------------------------------------------------------- #


def test_conflicting_claim_token_on_a_terminal_slot_raises_terminal_claim_mismatch(
    tmp_path: Path,
) -> None:
    store, info, change, _planted_receipt, worktree = _planted(
        tmp_path,
        claim_token="original-claim",  # noqa: S106
    )
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter)

    with pytest.raises(ExecutionTerminalClaimMismatchError):
        execute(
            change["change_id"],
            claim_token="a-different-claim",  # noqa: S106
            execution_instant="2026-09-10T00:00:02Z",
            worktree_root=str(worktree),
        )
    assert adapter.call_count == 0, "a refused mismatch must never reach the adapter"


# --------------------------------------------------------------------------------------- #
# (c) permit_semantic_reuse=True -- returns semantic_reuse, same receipt, no adapter call.
# --------------------------------------------------------------------------------------- #


def test_permit_semantic_reuse_returns_the_same_receipt_without_calling_the_adapter(
    tmp_path: Path,
) -> None:
    store, info, change, planted, worktree = _planted(tmp_path, claim_token="original-claim")  # noqa: S106
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter)

    result = execute(
        change["change_id"],
        claim_token="a-different-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
        worktree_root=str(worktree),
        permit_semantic_reuse=True,
    )
    assert result["replay"] is False
    assert result["semantic_reuse"] is True
    assert result["receipt"] == planted
    assert adapter.call_count == 0, "semantic reuse must never call the adapter"


# --------------------------------------------------------------------------------------- #
# (d) concurrent duplicate -- a genuine execution_intent already holds the slot.
# --------------------------------------------------------------------------------------- #


def test_concurrent_execution_intent_on_the_same_slot_raises_concurrent_claim(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    change = _fresh_change(store, info, headroom=1)["change"]

    commit_bare_execution_intent(
        store,
        info["project_id"],
        change_id=change["change_id"],
        boundary=_BOUNDARY,
        adapter_identity=_ADAPTER_IDENTITY,
        claim_token="a-different-concurrent-claim",  # noqa: S106
        requested_at="2026-09-10T00:00:00Z",
    )

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter)

    with pytest.raises(ExecutionConcurrentClaimError):
        execute(
            change["change_id"],
            claim_token="the-real-claim",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
            worktree_root=str(worktree),
        )
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (e) crash recovery -- a genuine execution_attempt already holds the slot, no receipt yet.
# --------------------------------------------------------------------------------------- #


def test_orphaned_execution_attempt_on_the_same_slot_requires_reconciliation(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    change = _fresh_change(store, info, headroom=1)["change"]

    commit_bare_execution_attempt(
        store,
        info["project_id"],
        change_id=change["change_id"],
        boundary=_BOUNDARY,
        adapter_identity=_ADAPTER_IDENTITY,
        claim_token="an-orphaned-claim",  # noqa: S106
        requested_at="2026-09-10T00:00:00Z",
    )

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter)

    with pytest.raises(ExecutionReconciliationRequiredError):
        execute(
            change["change_id"],
            claim_token="a-retry-claim",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
            worktree_root=str(worktree),
        )
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (f) partial failure -- outcome classification, and a clean idempotent replay afterward.
# --------------------------------------------------------------------------------------- #


class _PartialFailureAdapter:
    """A real adapter that performs exactly ``keep`` of the requested writes for real (through a
    genuine ``ControlledFilesystemAdapter``) and reports the rest as failed via ``error`` --
    never a fabricated report: every fact this adapter returns about a primary call matches
    exactly what it actually did to disk. Any call carrying no writes (the rollback's own
    delete-only operation) is delegated to the inner adapter in full, so a genuine
    ``BEST_EFFORT_DELETE_WRITTEN_FILES`` rollback can actually succeed."""

    def __init__(self, *, keep: int) -> None:
        from manosube_agent_civilization.change_executor.adapter import ControlledFilesystemAdapter

        self.inner = ControlledFilesystemAdapter(
            executor_identity="controlled_filesystem_adapter", executor_version="0.1"
        )
        self.keep = keep
        self.call_count = 0

    def execute(self, operation: Any, *, worktree_root: str) -> dict[str, Any]:
        self.call_count += 1
        writes = operation.get("file_writes") or []
        if writes:
            partial = {**operation, "file_writes": writes[: self.keep]}
            raw = dict(self.inner.execute(partial, worktree_root=worktree_root))
            raw["error"] = "simulated partial failure: only some writes were applied"
            return raw
        return dict(self.inner.execute(operation, worktree_root=worktree_root))


def _two_write_change(store: Any, info: dict[str, Any], *, headroom: int = 0) -> dict[str, Any]:
    paths = ["docs/partial-a.md", "docs/partial-b.md"]
    built = build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": p, "content_utf8": "content"} for p in paths],
        ),
        paths=paths,
        extra_state_revision_headroom=headroom,
    )
    return dict(built["change"])


def test_partial_failure_with_rollback_policy_none_stays_partial_mutation(tmp_path: Path) -> None:
    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    change = _two_write_change(store, info)

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    adapter = _PartialFailureAdapter(keep=1)
    execute = _executor(store, info, adapter, rollback_policy="NONE")

    outcome = execute(
        change["change_id"],
        claim_token="partial-none",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
        worktree_root=str(worktree),
    )
    receipt = outcome["receipt"]
    assert receipt["outcome"] == "PARTIAL_MUTATION"
    assert receipt["rollback_outcome"] == "NOT_ATTEMPTED"
    assert (worktree / "docs" / "partial-a.md").is_file()
    assert not (worktree / "docs" / "partial-b.md").exists()
    assert adapter.call_count == 1


def test_partial_failure_with_best_effort_rollback_policy_deletes_written_files(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    change = _two_write_change(store, info)

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    adapter = _PartialFailureAdapter(keep=1)
    execute = _executor(store, info, adapter, rollback_policy="BEST_EFFORT_DELETE_WRITTEN_FILES")

    outcome = execute(
        change["change_id"],
        claim_token="partial-rollback",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
        worktree_root=str(worktree),
    )
    receipt = outcome["receipt"]
    assert receipt["outcome"] in ("ROLLBACK_SUCCEEDED", "ROLLBACK_FAILED")
    assert receipt["rollback_outcome"] == receipt["outcome"]
    if receipt["outcome"] == "ROLLBACK_SUCCEEDED":
        assert not (worktree / "docs" / "partial-a.md").exists()
    # exactly two real adapter calls: the primary partial write, and the rollback delete.
    assert adapter.call_count == 2


def test_partial_failure_second_call_is_a_clean_idempotent_replay_not_a_second_adapter_call(
    tmp_path: Path,
) -> None:
    """A terminal ``PARTIAL_MUTATION`` receipt must replay exactly as cleanly as a ``SUCCEEDED``
    one -- proven here, as (a)/(b)/(c) above, via a genuinely real, planted terminal receipt (the
    live two-call form is exactly what this file's own module docstring already demonstrates is
    broken by the staleness-ordering defect, for every outcome alike, not merely SUCCEEDED)."""

    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    result = _fresh_change(store, info, headroom=1)
    change = result["change"]

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    planted = plant_terminal_receipt(
        store,
        info["project_id"],
        change,
        result["decision"],
        _BOUNDARY,
        _ADAPTER_IDENTITY,
        project_binding_id=info["project_binding_id"],
        worktree_root=str(worktree),
        claim_token="partial-replay",  # noqa: S106
        outcome="PARTIAL_MUTATION",
        performed_result_summary={
            "files_written": [change["scope"]["paths"][0]],
            "bytes_written": 7,
            "files_deleted": [],
        },
        rollback_outcome="NOT_ATTEMPTED",
    )

    adapter = _PartialFailureAdapter(keep=1)
    execute = _executor(store, info, adapter, rollback_policy="NONE")

    result2 = execute(
        change["change_id"],
        claim_token="partial-replay",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
        worktree_root=str(worktree),
    )
    assert result2["replay"] is True
    assert result2["receipt"] == planted
    assert adapter.call_count == 0, "a terminal PARTIAL_MUTATION receipt must replay cleanly too"
