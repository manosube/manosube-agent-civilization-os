"""V6 (Issue #73): tamper/substitution matrix.

Cross-project and cross-Store Change/receipt substitution, stale Boot/Binding, genuine target
drift, Boundary widening, receipt mutation at the Evidence hand-off, and adapter-identity
substitution across two composed closures for the identical Change -- each proven with real
records and real Store instances, never a hand-forged one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.change_executor_kill_switch_issuer import issuer_public_key_hex
from tests.fixtures.change_executor_world import (
    CountingAdapter,
    adapter_identity_for,
    bound,
    bound_with_project_id,
    build_committed_change,
    commit_active_kill_switch,
    execution_boundary_for,
    git_worktree,
    operation_for,
    plant_terminal_receipt,
)

from manosube_agent_civilization.boot.errors import BootError
from manosube_agent_civilization.change_executor.errors import (
    ChangeExecutorError,
    ExecutionAuthorityProvenanceError,
    StaleExecutionInputError,
)
from manosube_agent_civilization.change_executor.evidence_handoff import (
    route_change_execution_to_evidence,
)
from manosube_agent_civilization.change_executor.route import compose_change_executor

_ADAPTER_IDENTITY = {"kind": "controlled_filesystem_adapter", "version": "0.1"}


def _executor(
    store: Any, info: dict[str, Any], adapter: Any, *, worktree_root: str, **boundary_overrides: Any
) -> Any:
    return compose_change_executor(
        store,
        project_id=info["project_id"],
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(
            worktree_root=worktree_root, **boundary_overrides
        ),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )


def _fresh_change(
    store: Any, info: dict[str, Any], *, path: str = "docs/tamper.md", **kwargs: Any
) -> dict[str, Any]:
    return build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE", writes=[{"path": path, "content_utf8": "content"}]
        ),
        paths=[path],
        **kwargs,
    )


# --------------------------------------------------------------------------------------- #
# (a) cross-project -- a Change committed under project A, execute() called for project B.
# --------------------------------------------------------------------------------------- #


def test_cross_project_change_id_never_resolves_against_a_different_bound_project(
    tmp_path: Path,
) -> None:
    # One real Store, genuinely bound to *two* distinct projects -- Change A is committed only
    # under project A's own directory tree; project B is real and independently bootable, but
    # was never asked to execute anything at all.
    store, info_a = bound_with_project_id(tmp_path, "PRJ-CE-V6A-A", subdir="shared")
    _store_b, info_b = bound_with_project_id(tmp_path, "PRJ-CE-V6A-B", subdir="shared")
    commit_active_kill_switch(store, info_a["project_id"])
    commit_active_kill_switch(store, info_b["project_id"])

    change_a = _fresh_change(store, info_a)["change"]

    worktree = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute_for_b = compose_change_executor(
        store,
        project_id=info_b["project_id"],
        project_binding_id=info_b["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree)),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )

    with pytest.raises(ExecutionAuthorityProvenanceError):
        execute_for_b(
            change_a["change_id"],
            claim_token="cross-project",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (b) cross-Store -- two separate FileStateStore instances, same project_id, different roots.
# --------------------------------------------------------------------------------------- #


def test_cross_store_change_id_never_resolves_against_a_different_store_instance(
    tmp_path: Path,
) -> None:
    store_a, info_a = bound(tmp_path, subdir="store-a")
    store_b, info_b = bound(tmp_path, subdir="store-b")
    assert info_a["project_id"] == info_b["project_id"]  # identical project_id, different Store
    commit_active_kill_switch(store_a, info_a["project_id"])
    commit_active_kill_switch(store_b, info_b["project_id"])

    change_a = _fresh_change(store_a, info_a)["change"]
    assert store_b.resolve_record(info_b["project_id"], "change", change_a["change_id"]) is None

    worktree = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute_via_b = _executor(store_b, info_b, adapter, worktree_root=str(worktree))

    with pytest.raises(ExecutionAuthorityProvenanceError):
        execute_via_b(
            change_a["change_id"],
            claim_token="cross-store",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (c) stale Boot/Binding -- a project_binding_id that does not match the one actually bound.
# --------------------------------------------------------------------------------------- #


def test_stale_project_binding_id_propagates_boots_own_typed_error(tmp_path: Path) -> None:
    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    change = _fresh_change(store, info)["change"]

    real_binding_id = info["project_binding_id"]
    bogus_binding_id = real_binding_id[:-1] + ("A" if real_binding_id[-1] != "A" else "B")
    assert bogus_binding_id != real_binding_id

    worktree = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = compose_change_executor(
        store,
        project_id=info["project_id"],
        project_binding_id=bogus_binding_id,
        execution_boundary=execution_boundary_for(worktree_root=str(worktree)),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )

    with pytest.raises(BootError):
        execute(
            change["change_id"],
            claim_token="stale-binding",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (d) target drift -- a real State transition lands after the Change was derived, before
# execute() is called.
# --------------------------------------------------------------------------------------- #


def test_genuine_target_drift_after_change_derivation_is_refused_as_stale(tmp_path: Path) -> None:
    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    # extra_state_revision_headroom=0 (the default): this Change is fresh only for the *one*
    # revision immediately following its own commit -- exactly the window this test then moves
    # past with a second, unrelated, genuine State transition.
    change = _fresh_change(store, info, path="docs/drift.md")["change"]

    # A second, genuine, unrelated Change, committed after the first -- any real commit through
    # this project's own sanctioned committer advances state_revision, which is exactly what
    # "target drift" means here: the world moved on after this Change observed it.
    _fresh_change(store, info, path="docs/unrelated-drift.md")

    worktree = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    with pytest.raises(StaleExecutionInputError):
        execute(
            change["change_id"],
            claim_token="drifted",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (e) Boundary widening -- two closures, identical Store/project, different Boundaries.
# --------------------------------------------------------------------------------------- #


def test_a_change_admitted_by_a_wider_boundary_cannot_execute_through_a_narrower_one(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    change = _fresh_change(store, info, path="docs/general/report.md")["change"]

    worktree = git_worktree(tmp_path)

    narrow_adapter = CountingAdapter()
    execute_narrow = _executor(
        store,
        info,
        narrow_adapter,
        worktree_root=str(worktree),
        admitted_paths=["docs/general/subset-only"],
    )
    with pytest.raises(ExecutionAuthorityProvenanceError):
        execute_narrow(
            change["change_id"],
            claim_token="narrow",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert narrow_adapter.call_count == 0

    wide_adapter = CountingAdapter()
    execute_wide = _executor(
        store, info, wide_adapter, worktree_root=str(worktree), admitted_paths=["docs"]
    )
    outcome = execute_wide(
        change["change_id"],
        claim_token="wide",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
    )
    assert outcome["receipt"]["outcome"] == "SUCCEEDED"
    assert wide_adapter.call_count == 1


# --------------------------------------------------------------------------------------- #
# (f) operation replacement -- cross-referenced to V4, not duplicated here.
# --------------------------------------------------------------------------------------- #

#: A hand-constructed ``execution_attempt`` whose own ``claim_token`` does not match what a
#: subsequent ``execute()`` call's own request would produce is exactly the concurrent-claim /
#: reconciliation-required scenario ``tests/integration/change_executor/
#: test_change_executor_idempotency_crash_matrix.py``'s own (d)/(e) already cover in full
#: (``test_concurrent_execution_intent_on_the_same_slot_raises_concurrent_claim`` and
#: ``test_orphaned_execution_attempt_on_the_same_slot_requires_reconciliation``) -- not
#: duplicated here.


# --------------------------------------------------------------------------------------- #
# (g) receipt mutation -- fed to route_change_execution_to_evidence as the receipt argument.
# --------------------------------------------------------------------------------------- #


def test_mutated_receipt_copy_is_refused_by_the_evidence_handoff(tmp_path: Path) -> None:
    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)
    change = _fresh_change(store, info, path="docs/mutate.md")["change"]

    worktree = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))
    outcome = execute(
        change["change_id"],
        claim_token="mutate",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    real_receipt = outcome["receipt"]
    assert (
        store.resolve_record(
            project_id, "execution_receipt", real_receipt["change_execution_receipt_id"]
        )
        == real_receipt
    )

    mutated = dict(real_receipt)
    mutated["claim_token"] = "an-entirely-different-claim-token"  # noqa: S105

    from tests.evidence_helpers import change_free_verification_evidence_request

    def _rebind_project(value: Any, old: str, new: str) -> Any:
        if isinstance(value, dict):
            return {key: _rebind_project(item, old, new) for key, item in value.items()}
        if isinstance(value, list):
            return [_rebind_project(item, old, new) for item in value]
        return new if value == old else value

    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    # (P18-R2-F1, Structural Review Round 2) route_change_execution_to_evidence now constructs
    # verification_observation_request itself, from a second, independent, handoff-time-only
    # re-read of the real resulting filesystem state -- it must not be caller-supplied.
    evidence_request["verification_observation_request"] = None
    with pytest.raises(ChangeExecutorError):
        route_change_execution_to_evidence(store, mutated, project_id, evidence_request)

    # The real, unmutated receipt still hands off cleanly.
    evidence = route_change_execution_to_evidence(store, real_receipt, project_id, evidence_request)
    assert evidence["evidence_position"] == "CHANGE_FREE_VERIFICATION_EVIDENCE"


# --------------------------------------------------------------------------------------- #
# (h) adapter identity substitution -- two closures, identical Boundary, different adapters.
# --------------------------------------------------------------------------------------- #


def test_two_adapter_identities_produce_two_distinct_slots_for_the_identical_change(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)
    result = _fresh_change(
        store, info, path="docs/adapter-substitution.md", extra_state_revision_headroom=1
    )
    change = result["change"]

    worktree = git_worktree(tmp_path)
    boundary = execution_boundary_for(worktree_root=str(worktree))
    identity_a = adapter_identity_for(kind="adapter-a")
    identity_b = adapter_identity_for(kind="adapter-b")

    # Plant a real terminal receipt at adapter A's own slot -- this Change's own one valid
    # staleness window is consumed by this single commit (accounted for by
    # extra_state_revision_headroom=1 above).
    planted = plant_terminal_receipt(
        store,
        project_id,
        change,
        result["decision"],
        boundary,
        identity_a,
        project_binding_id=info["project_binding_id"],
        worktree_root=str(worktree),
        claim_token="slot-a-claim",  # noqa: S106
        outcome="SUCCEEDED",
        performed_result_summary={
            "files_written": ["docs/adapter-substitution.md"],
            "bytes_written": 7,
            "files_deleted": [],
        },
    )

    # A single, real, live execute() call through adapter identity B's own closure: a genuinely
    # different mapping slot, so it must proceed as a first-time execution -- never replaying,
    # reusing, or even resolving adapter A's own planted receipt.
    adapter_b = CountingAdapter()
    execute_b = compose_change_executor(
        store,
        project_id=project_id,
        project_binding_id=info["project_binding_id"],
        execution_boundary=boundary,
        adapter_identity=identity_b,
        adapter=adapter_b,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )
    outcome_b = execute_b(
        change["change_id"],
        claim_token="slot-b-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
    )
    assert outcome_b["replay"] is False
    assert outcome_b["semantic_reuse"] is False
    assert outcome_b["receipt"]["outcome"] == "SUCCEEDED"
    assert (
        outcome_b["receipt"]["change_execution_receipt_id"]
        != planted["change_execution_receipt_id"]
    )
    assert adapter_b.call_count == 1, "slot B's own execution must genuinely call its own adapter"


# --------------------------------------------------------------------------------------- #
# (i) P18-R1-F3 (Structural Review Round 1): worktree_root substitution -- a receipt planted
# under one composed executor's own worktree_root cannot be replayed/reused by a different
# composed executor bound to a different worktree_root, for the identical change_id/claim_token.
# --------------------------------------------------------------------------------------- #


def test_two_worktree_roots_produce_two_distinct_slots_for_the_identical_change_and_claim(
    tmp_path: Path,
) -> None:
    """Two composed executors, identical in every respect (Boundary content, adapter identity)
    except ``worktree_root``, must never share a mapping slot: a terminal receipt planted under
    executor A's own worktree_root, for a given ``change_id``/``claim_token``, must not be
    resolved -- as a replay, a semantic reuse, or anything else -- by executor B's own distinct
    worktree_root for the identical ``change_id``/``claim_token``. Each gets its own independent
    slot, verified here directly rather than merely assumed from the Boundary-fingerprint proof
    in ``tests/unit/change_executor/test_change_executor_identity.py``."""

    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)
    result = _fresh_change(
        store, info, path="docs/worktree-substitution.md", extra_state_revision_headroom=1
    )
    change = result["change"]

    worktree_a = git_worktree(tmp_path, subdir="worktree-a")
    worktree_b = git_worktree(tmp_path, subdir="worktree-b")
    boundary_a = execution_boundary_for(worktree_root=str(worktree_a))
    boundary_b = execution_boundary_for(worktree_root=str(worktree_b))

    identical_claim_token = "identical-claim-across-both-worktrees"  # noqa: S105

    # Plant a real terminal receipt at worktree A's own slot -- this Change's own one valid
    # staleness window is consumed by this single commit (extra_state_revision_headroom=1 above).
    planted = plant_terminal_receipt(
        store,
        project_id,
        change,
        result["decision"],
        boundary_a,
        _ADAPTER_IDENTITY,
        project_binding_id=info["project_binding_id"],
        worktree_root=str(worktree_a),
        claim_token=identical_claim_token,
        outcome="SUCCEEDED",
        performed_result_summary={
            "files_written": ["docs/worktree-substitution.md"],
            "bytes_written": 7,
            "files_deleted": [],
        },
    )

    # A single, real, live execute() call through worktree B's own closure, under the identical
    # change_id and the identical claim_token planted for worktree A -- a genuinely different
    # mapping slot (different Boundary fingerprint), so it must proceed as a first-time
    # execution: never replaying, never reusing, never even resolving worktree A's own planted
    # receipt.
    adapter_b = CountingAdapter()
    execute_b = compose_change_executor(
        store,
        project_id=project_id,
        project_binding_id=info["project_binding_id"],
        execution_boundary=boundary_b,
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter_b,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )
    outcome_b = execute_b(
        change["change_id"],
        claim_token=identical_claim_token,
        execution_instant="2026-09-10T00:00:02Z",
    )
    assert outcome_b["replay"] is False
    assert outcome_b["semantic_reuse"] is False
    assert outcome_b["receipt"]["outcome"] == "SUCCEEDED"
    assert (
        outcome_b["receipt"]["change_execution_receipt_id"]
        != planted["change_execution_receipt_id"]
    )
    assert outcome_b["receipt"]["target"]["worktree_root"] == str(worktree_b)
    assert adapter_b.call_count == 1, (
        "worktree B's own execution must genuinely call its own adapter, never resolve worktree "
        "A's own planted receipt"
    )
    assert (worktree_b / "docs" / "worktree-substitution.md").is_file()
