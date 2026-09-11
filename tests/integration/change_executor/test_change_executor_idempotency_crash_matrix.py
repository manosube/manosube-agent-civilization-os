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

from collections.abc import Callable
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
    slot_key_for,
)

from manosube_agent_civilization.change_executor.errors import (
    ExecutionConcurrentClaimError,
    ExecutionReconciliationRequiredError,
    ExecutionTerminalClaimMismatchError,
    StaleExecutionInputError,
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

_ADAPTER_IDENTITY = {"kind": "controlled_filesystem_adapter", "version": "0.1"}


def _boundary_for(worktree_root: str, **overrides: Any) -> dict[str, Any]:
    """``worktree_root`` is now a required field *inside* the closed Boundary itself
    (P18-R1-F3, Structural Review Round 1) -- so, unlike the prior round, no single shared
    module-level ``_BOUNDARY`` constant can be reused across tests that each build their own
    real ``tmp_path``-derived worktree: every boundary a test needs is built fresh, here, from
    that test's own real worktree root."""

    return execution_boundary_for(worktree_root=worktree_root, **overrides)


def _executor(
    store: Any, info: dict[str, Any], adapter: Any, *, worktree_root: str, **boundary_overrides: Any
) -> Any:
    return compose_change_executor(
        store,
        project_id=info["project_id"],
        project_binding_id=info["project_binding_id"],
        execution_boundary=_boundary_for(worktree_root, **boundary_overrides),
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
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    first = execute(
        change["change_id"],
        claim_token="exact-replay-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    assert first["receipt"]["outcome"] == "SUCCEEDED"
    assert adapter.call_count == 1

    second = execute(
        change["change_id"],
        claim_token="exact-replay-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
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
        _boundary_for(str(worktree)),
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
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    result = execute(
        change["change_id"],
        claim_token="same-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
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
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    with pytest.raises(ExecutionTerminalClaimMismatchError):
        execute(
            change["change_id"],
            claim_token="a-different-claim",  # noqa: S106
            execution_instant="2026-09-10T00:00:02Z",
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
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    result = execute(
        change["change_id"],
        claim_token="a-different-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
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

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    commit_bare_execution_intent(
        store,
        info["project_id"],
        change_id=change["change_id"],
        boundary=_boundary_for(str(worktree)),
        adapter_identity=_ADAPTER_IDENTITY,
        claim_token="a-different-concurrent-claim",  # noqa: S106
        requested_at="2026-09-10T00:00:00Z",
    )

    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    with pytest.raises(ExecutionConcurrentClaimError):
        execute(
            change["change_id"],
            claim_token="the-real-claim",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
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

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    commit_bare_execution_attempt(
        store,
        info["project_id"],
        change_id=change["change_id"],
        boundary=_boundary_for(str(worktree)),
        adapter_identity=_ADAPTER_IDENTITY,
        claim_token="an-orphaned-claim",  # noqa: S106
        requested_at="2026-09-10T00:00:00Z",
    )

    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    with pytest.raises(ExecutionReconciliationRequiredError):
        execute(
            change["change_id"],
            claim_token="a-retry-claim",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
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
    execute = _executor(store, info, adapter, worktree_root=str(worktree), rollback_policy="NONE")

    outcome = execute(
        change["change_id"],
        claim_token="partial-none",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
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
    execute = _executor(
        store,
        info,
        adapter,
        worktree_root=str(worktree),
        rollback_policy="BEST_EFFORT_DELETE_WRITTEN_FILES",
    )

    outcome = execute(
        change["change_id"],
        claim_token="partial-rollback",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
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
        _boundary_for(str(worktree)),
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
    execute = _executor(store, info, adapter, worktree_root=str(worktree), rollback_policy="NONE")

    result2 = execute(
        change["change_id"],
        claim_token="partial-replay",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
    )
    assert result2["replay"] is True
    assert result2["receipt"] == planted
    assert adapter.call_count == 0, "a terminal PARTIAL_MUTATION receipt must replay cleanly too"


# --------------------------------------------------------------------------------------- #
# Finding 2 (Codex automated review, PR #74): a crash between the execution_intent commit
# (step 11) and the execution_attempt commit (step 12) must not permanently strand the slot.
# --------------------------------------------------------------------------------------- #


def test_crash_between_intent_commit_and_attempt_commit_is_recoverable_via_resumed_retry(
    tmp_path: Path,
) -> None:
    """A genuine automated-review finding against ``route.py``: every commit this route performs
    -- including the ``execution_intent`` commit alone -- unconditionally advances
    ``state_revision`` by one. A process that crashes after that one commit succeeds but before
    the following ``execution_attempt`` commit ever runs leaves a slot with a durably committed
    intent, no attempt, no receipt. This test plants exactly that intent directly (simulating the
    crash point precisely, the same technique :func:`commit_bare_execution_intent` already
    provides for V4(d)'s concurrent-claim control) with **no** compensating
    ``extra_state_revision_headroom`` -- an ordinary caller retrying with the identical
    ``claim_token``/``execution_instant`` has no way to know, or compensate for, ``route.py``'s
    own private commit count. Before the fix (route.py's own disclosed judgment call 7) this
    retry raised ``StaleExecutionInputError`` permanently, with zero adapter calls ever having
    occurred and no path to reconciliation; after the fix, the identical retry resumes cleanly to
    a genuine terminal ``SUCCEEDED`` receipt, and the adapter is called exactly once total across
    both the interrupted attempt and the successful retry."""

    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    change = _fresh_change(store, info, path="docs/resume-after-intent-crash.md")["change"]

    worktree = tmp_path / "worktree"
    worktree.mkdir()

    claim_token = "resume-after-crash-claim"  # noqa: S105
    execution_instant = "2026-09-10T00:00:01Z"

    # Simulate the crash: an execution_intent is durably committed for this exact slot (this
    # package's own step 11), but the following execution_attempt commit (step 12) never ran --
    # this advances state_revision by one all on its own, with no headroom compensating for it.
    commit_bare_execution_intent(
        store,
        info["project_id"],
        change_id=change["change_id"],
        boundary=_boundary_for(str(worktree)),
        adapter_identity=_ADAPTER_IDENTITY,
        claim_token=claim_token,
        requested_at=execution_instant,
    )

    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    # The identical caller, retrying with the identical claim_token/execution_instant -- no
    # special knowledge of route.py's own private commit count, exactly as a genuine
    # crash-recovery caller would retry.
    outcome = execute(
        change["change_id"],
        claim_token=claim_token,
        execution_instant=execution_instant,
    )
    assert outcome["receipt"]["outcome"] == "SUCCEEDED"
    assert outcome["replay"] is False
    assert outcome["semantic_reuse"] is False
    assert (worktree / "docs" / "resume-after-intent-crash.md").is_file()
    assert adapter.call_count == 1, (
        "the adapter must be called exactly once across both the interrupted attempt and the "
        "successful retry"
    )


# --------------------------------------------------------------------------------------- #
# P18-R1-F2 (Structural Review Round 1): the exact post-intent-successor check, and the final
# pre-effect State barrier. The test immediately above is P18-R1-F2's own positive control --
# resuming from an intent with genuinely no unrelated drift succeeds normally. The two tests
# below are its negative controls.
# --------------------------------------------------------------------------------------- #


def test_resuming_a_crash_interrupted_intent_with_an_unrelated_transition_in_between_is_refused(
    tmp_path: Path,
) -> None:
    """P18-R1-F2(b): plant an intent (simulating the identical crash point the test immediately
    above does), then commit a genuinely *unrelated* transition to this same project's own State
    (any harmless, real commit through the project's own sanctioned committer -- here, a second,
    unrelated Change/Authority-Decision pair, exactly as ``_fresh_change`` already builds
    elsewhere in this file) before retrying the identical, resuming caller. Before P18-R1-F2, a
    blanket staleness skip for any claim_token match would have let this retry proceed as if
    nothing else had happened; the exact successor check now correctly refuses it -- the current
    State's own ``state_revision`` is two past the Change's own ``expected_state_revision``, not
    exactly one, so it can never be genuinely mistaken for "only this call's own intent commit
    happened." Zero adapter calls."""

    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    change = _fresh_change(store, info, path="docs/resume-with-drift.md")["change"]

    worktree = tmp_path / "worktree"
    worktree.mkdir()

    claim_token = "resume-with-drift-claim"  # noqa: S105
    execution_instant = "2026-09-10T00:00:01Z"

    # Simulate the crash: an execution_intent is durably committed for this exact slot.
    commit_bare_execution_intent(
        store,
        info["project_id"],
        change_id=change["change_id"],
        boundary=_boundary_for(str(worktree)),
        adapter_identity=_ADAPTER_IDENTITY,
        claim_token=claim_token,
        requested_at=execution_instant,
    )

    # An unrelated, genuinely real transition lands on this identical project's own State --
    # a second, unrelated Change committed through the real route, never a hand-forged State
    # edit -- before the resuming retry ever runs.
    _fresh_change(store, info, path="docs/unrelated-drift-during-resume.md")

    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    with pytest.raises(StaleExecutionInputError):
        execute(
            change["change_id"],
            claim_token=claim_token,
            execution_instant=execution_instant,
        )
    assert adapter.call_count == 0, (
        "an unrelated transition landing between the crash and the resumed retry must refuse "
        "before the adapter is ever reached"
    )


class _DriftOnThirdLoadCurrent:
    """A thin, real Store proxy -- forwards every call unchanged except the *third* call to
    ``load_current`` for *project_id*, which additionally commits a genuine, unrelated Change
    (through the real, sanctioned committer, never a hand-forged State edit) as a side effect
    before delegating. The three ordinary ``load_current`` calls a genuinely fresh execution
    performs, in order, are: the ``execution_intent`` commit's own retry-loop read (1st), the
    ``execution_attempt`` commit's own retry-loop read (2nd), and P18-R1-F2's own final
    pre-effect State barrier's direct read (3rd) -- so triggering on the third call reproduces
    exactly the race the barrier exists to catch: an unrelated transition landing in the narrow
    window between the attempt commit finishing and the one adapter call."""

    def __init__(self, inner: Any, project_id: str, drift: Callable[[], None]) -> None:
        self._inner = inner
        self._project_id = project_id
        self._drift = drift
        self._count = 0

    def load_current(self, project_id: str) -> dict[str, Any]:
        if project_id == self._project_id:
            self._count += 1
            if self._count == 3:
                self._drift()
        result: dict[str, Any] = self._inner.load_current(project_id)
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def test_unrelated_transition_immediately_before_the_adapter_call_is_refused_by_the_final_barrier(
    tmp_path: Path,
) -> None:
    """P18-R1-F2(c): after the intent and attempt commits both finish, but immediately before the
    one adapter call would run, an unrelated transition lands. The final pre-effect State barrier
    must refuse before ``adapter.execute`` is ever called, zero further mutation."""

    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    change = _fresh_change(store, info, path="docs/resume-with-final-barrier-drift.md")["change"]

    worktree = tmp_path / "worktree"
    worktree.mkdir()

    def _drift() -> None:
        _fresh_change(store, info, path="docs/unrelated-drift-at-the-final-barrier.md")

    proxy = _DriftOnThirdLoadCurrent(store, info["project_id"], _drift)
    adapter = CountingAdapter()
    execute = compose_change_executor(
        proxy,
        project_id=info["project_id"],
        project_binding_id=info["project_binding_id"],
        execution_boundary=_boundary_for(str(worktree)),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )

    with pytest.raises(StaleExecutionInputError):
        execute(
            change["change_id"],
            claim_token="final-barrier-claim",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert adapter.call_count == 0, (
        "an unrelated transition landing immediately before the adapter call must refuse before "
        "the adapter is ever reached"
    )


# --------------------------------------------------------------------------------------- #
# P18-R1-F4 (Structural Review Round 1): every post-attempt outcome -- including an adapter
# raise and a structurally invalid adapter report -- commits exactly one terminal receipt,
# never a bare exception.
# --------------------------------------------------------------------------------------- #


class _RaisingAdapter:
    """A real adapter double that always raises on ``execute`` -- never a mock returning a
    fabricated report, a genuine exception with no facts to report at all."""

    def __init__(self) -> None:
        self.call_count = 0

    def execute(self, operation: Any, *, worktree_root: str) -> dict[str, Any]:
        self.call_count += 1
        raise RuntimeError("simulated adapter failure: disk unavailable")


class _MalformedReportAdapter:
    """A real adapter double that performs no filesystem I/O at all and instead returns a
    structurally invalid report (missing required keys) -- the other path
    ``_validate_adapter_report`` refuses, distinct from a raised exception."""

    def __init__(self) -> None:
        self.call_count = 0

    def execute(self, operation: Any, *, worktree_root: str) -> dict[str, Any]:
        self.call_count += 1
        return {"files_written": ["not-actually-written.md"]}  # missing required keys


def test_adapter_raise_commits_a_terminal_unknown_receipt_not_a_bare_exception(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    change = _fresh_change(store, info, path="docs/adapter-raises.md")["change"]

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    adapter = _RaisingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    outcome = execute(
        change["change_id"],
        claim_token="adapter-raises-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    receipt = outcome["receipt"]
    assert receipt["outcome"] == "UNKNOWN"
    assert receipt["independent_after_state_observation"] == {
        "outcome": "NOT_PERFORMED",
        "checked_files": [],
    }
    assert receipt["reobservation_request"]["kind"] == "change_execution_reobservation_request"
    assert adapter.call_count == 1

    # A second call for the identical slot replays the identical UNKNOWN receipt -- never
    # re-calling the adapter.
    replay = execute(
        change["change_id"],
        claim_token="adapter-raises-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
    )
    assert replay["replay"] is True
    assert replay["receipt"] == receipt
    assert adapter.call_count == 1, "a replay must never re-call a raising adapter either"


def test_structurally_invalid_adapter_report_commits_a_terminal_unknown_receipt(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    change = _fresh_change(store, info, path="docs/malformed-report.md")["change"]

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    adapter = _MalformedReportAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    outcome = execute(
        change["change_id"],
        claim_token="malformed-report-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    receipt = outcome["receipt"]
    assert receipt["outcome"] == "UNKNOWN"
    assert receipt["independent_after_state_observation"] == {
        "outcome": "NOT_PERFORMED",
        "checked_files": [],
    }
    assert adapter.call_count == 1

    replay = execute(
        change["change_id"],
        claim_token="malformed-report-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
    )
    assert replay["replay"] is True
    assert replay["receipt"] == receipt
    assert adapter.call_count == 1, "a replay must never re-call the adapter either"


# --------------------------------------------------------------------------------------- #
# Finding 3 (Codex automated review, PR #74): two genuinely racing callers for the identical
# slot must never both call adapter.execute -- attempt_nonce closes the gap.
# --------------------------------------------------------------------------------------- #


class _RaceSecondCallerIntoTheAttemptCheck:
    """A thin, real Store proxy -- forwards every call unchanged except the *first* call to
    ``resolve_record`` for this exact ``(project_id, "execution_attempt", slot_key)`` triple,
    which additionally drives a second, genuinely independent ``execute()`` call all the way to
    completion -- sharing the identical underlying real Store, Boundary, adapter identity, and
    *adapter instance* -- before returning the pre-race answer (``None``) this caller's own step
    4 actually observed. This reproduces the genuine race Finding 3 identifies: both callers pass
    step 4 before *either* has committed anything, because the second caller's own full run
    happens, in real wall-clock time, entirely inside the first caller's own step-4 check -- yet
    the first caller's own code path only ever sees the answer its own check actually returned,
    exactly as a genuinely concurrent caller would."""

    def __init__(
        self, inner: Any, project_id: str, slot_key: str, second_call: Callable[[], None]
    ) -> None:
        self._inner = inner
        self._project_id = project_id
        self._slot_key = slot_key
        self._second_call = second_call
        self._triggered = False

    def resolve_record(self, project_id: str, kind: str, record_id: str) -> Any:
        result = self._inner.resolve_record(project_id, kind, record_id)
        if (
            not self._triggered
            and project_id == self._project_id
            and kind == "execution_attempt"
            and record_id == self._slot_key
        ):
            self._triggered = True
            self._second_call()
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def test_two_racing_callers_for_the_identical_slot_call_the_adapter_at_most_once(
    tmp_path: Path,
) -> None:
    """Two callers invoking ``execute()`` with the identical ``change_id``/``claim_token``/
    ``execution_instant`` (so, necessarily, through composed executors sharing the identical
    Boundary/adapter identity too), racing so that both pass idempotency-slot resolution before
    either has committed anything, must still call ``adapter.execute`` exactly once combined --
    never twice. ``attempt_nonce`` (a fresh, per-call ``secrets.token_hex(16)``, never
    caller-supplied) makes the two independently-built ``execution_attempt`` records genuinely
    different byte-for-byte, so the Store's own *existing* conflict detection -- not new
    machinery -- correctly refuses the second one as a real ``RecordConflictError`` ->
    ``ExecutionConcurrentClaimError``, rather than silently treating it as an idempotent replay of
    the first."""

    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    change = _fresh_change(store, info, path="docs/race.md")["change"]

    worktree = tmp_path / "worktree"
    worktree.mkdir()

    shared_adapter = CountingAdapter()
    claim_token = "racing-claim"  # noqa: S105
    execution_instant = "2026-09-10T00:00:01Z"
    boundary = _boundary_for(str(worktree))

    slot_key, _boundary_fp, _adapter_fp = slot_key_for(
        change["change_id"], boundary, _ADAPTER_IDENTITY
    )

    execute_second = compose_change_executor(
        store,
        project_id=info["project_id"],
        project_binding_id=info["project_binding_id"],
        execution_boundary=boundary,
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=shared_adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )

    second_outcome: dict[str, Any] = {}
    second_error: Exception | None = None

    def _run_second_caller() -> None:
        nonlocal second_error
        try:
            second_outcome["result"] = execute_second(
                change["change_id"], claim_token=claim_token, execution_instant=execution_instant
            )
        except Exception as error:  # captured for the assertions below, not raised
            second_error = error

    proxy = _RaceSecondCallerIntoTheAttemptCheck(
        store, info["project_id"], slot_key, _run_second_caller
    )
    execute_first = compose_change_executor(
        proxy,
        project_id=info["project_id"],
        project_binding_id=info["project_binding_id"],
        execution_boundary=boundary,
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=shared_adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )

    first_error: Exception | None = None
    first_outcome: dict[str, Any] | None = None
    try:
        first_outcome = execute_first(
            change["change_id"], claim_token=claim_token, execution_instant=execution_instant
        )
    except Exception as error:  # captured for the assertions below, not raised
        first_error = error

    assert second_error is None, (
        f"the racing caller that commits first must succeed: {second_error!r}"
    )
    assert second_outcome["result"]["receipt"]["outcome"] == "SUCCEEDED"

    assert first_outcome is None
    # P18-R1-F2 (Structural Review Round 1) changes exactly *which* typed refusal the loser gets
    # here, without changing the decisive guarantee this test exists to prove (adapter called at
    # most once combined). By the time the first caller's own idempotency-slot resolution reaches
    # its own execution_intent check, the second caller has already raced all the way to a full
    # terminal SUCCEEDED receipt (intent + attempt + receipt, three commits) -- so the intent this
    # first caller resolves (under the identical claim_token, by this test's own design) makes it
    # *believe* it is resuming its own crash-interrupted intent. Before P18-R1-F2, staleness was
    # blanket-skipped for that belief, and the genuine conflict only surfaced one step later, at
    # the attempt-commit itself (RecordConflictError -> ExecutionConcurrentClaimError). P18-R1-F2's
    # own exact-successor staleness check now catches the *same* underlying problem one step
    # earlier and more precisely: state_revision has advanced by three (a full completed
    # execution), not the one commit a genuine crash-interrupted resume would ever produce, so it
    # correctly refuses as StaleExecutionInputError instead -- an equally fail-closed, equally
    # zero-adapter-call refusal, just a more precise diagnosis of the identical race.
    assert isinstance(first_error, ExecutionConcurrentClaimError | StaleExecutionInputError), (
        f"the caller that loses the race must be refused, not {first_error!r}"
    )

    assert shared_adapter.call_count == 1, (
        "adapter.execute must be called exactly once combined across both racing callers"
    )
