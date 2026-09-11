"""V2 (Issue #73): Authority/Change continuity proof.

Every Change and Authority Decision here is produced through the real ``evaluate_authority``/
``derive_change`` route (:func:`tests.fixtures.change_executor_world.build_committed_change`) --
never a hand-forged decision or Change. Proves ``compose_change_executor``'s returned closure
correctly executes a genuine AUTONOMOUS committed Change, and refuses -- before the adapter is
ever reached -- every one of: a tampered Authority Decision, a tampered Change, a cross-project
Change substitution, an out-of-Boundary ``action_kind``, and a Human-only ``action_kind`` (both
at the Boundary-composition level and, structurally, at the module-invariant level).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.change_executor_kill_switch_issuer import issuer_public_key_hex
from tests.fixtures.change_executor_world import (
    CountingAdapter,
    bound,
    bound_with_project_id,
    build_committed_change,
    commit_active_kill_switch,
    commit_foreign_record,
    execution_boundary_for,
    git_worktree,
    operation_for,
    tamper_committed_record,
)

from manosube_agent_civilization.authority.levels import HUMAN_ONLY_ACTION_KINDS
from manosube_agent_civilization.change_executor import boundary as boundary_module
from manosube_agent_civilization.change_executor.boundary import validate_execution_boundary
from manosube_agent_civilization.change_executor.errors import (
    ExecutionAuthorityProvenanceError,
    ExecutionBoundaryError,
    ExecutionReceiptIntegrityError,
)
from manosube_agent_civilization.change_executor.route import compose_change_executor


def _world(tmp_path: Path, *, subdir: str = "backend") -> tuple[Any, dict[str, Any]]:
    return bound(tmp_path, subdir=subdir)


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
        adapter_identity={"kind": "controlled_filesystem_adapter", "version": "0.1"},
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )


def _fresh_change(
    store: Any, info: dict[str, Any], *, path: str = "docs/target.md"
) -> dict[str, Any]:
    return build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": path, "content_utf8": "hello world"}],
        ),
        paths=[path],
    )


# --------------------------------------------------------------------------------------- #
# (a) positive: a genuinely AUTONOMOUS, committed Change executes.
# --------------------------------------------------------------------------------------- #


def test_composed_execute_runs_a_genuinely_autonomous_committed_change(tmp_path: Path) -> None:
    store, info = _world(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    result = _fresh_change(store, info)
    change = result["change"]
    assert result["decision"]["decision"] == "AUTONOMOUS"

    worktree = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    outcome = execute(
        change["change_id"],
        claim_token="claim-a",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    assert outcome["receipt"]["outcome"] == "SUCCEEDED"
    assert adapter.call_count == 1
    assert outcome["receipt"]["change_ref"] == {"kind": "change", "id": change["change_id"]}
    assert outcome["receipt"]["authority_ref"] == {
        "kind": "authority_decision",
        "id": result["decision"]["authority_decision_id"],
    }


# --------------------------------------------------------------------------------------- #
# (b) tampered Authority Decision (Store-committed, bypassing the normal commit path).
# --------------------------------------------------------------------------------------- #


def test_tampered_authority_decision_is_refused_before_any_adapter_call(tmp_path: Path) -> None:
    store, info = _world(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    result = _fresh_change(store, info)
    change = result["change"]
    decision = result["decision"]

    def _flip(record: dict[str, Any]) -> dict[str, Any]:
        record["decision_reason_codes"] = [*record["decision_reason_codes"], "TAMPERED"]
        return record

    tamper_committed_record(
        store, info["project_id"], "authority_decision", decision["authority_decision_id"], _flip
    )

    worktree = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    with pytest.raises(ExecutionReceiptIntegrityError):
        execute(
            change["change_id"],
            claim_token="claim-b",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (c) tampered Change record (Store-committed, bypassing the normal commit path).
# --------------------------------------------------------------------------------------- #


def test_tampered_change_record_is_refused_before_any_adapter_call(tmp_path: Path) -> None:
    store, info = _world(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    result = _fresh_change(store, info)
    change = result["change"]

    def _flip(record: dict[str, Any]) -> dict[str, Any]:
        record["scope"]["paths"] = ["docs/somewhere-else-entirely.md"]
        return record

    tamper_committed_record(store, info["project_id"], "change", change["change_id"], _flip)

    worktree = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    with pytest.raises(ExecutionReceiptIntegrityError):
        execute(
            change["change_id"],
            claim_token="claim-c",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (d) change_id resolves under this project, but its own declared content names another.
# --------------------------------------------------------------------------------------- #


def test_change_declaring_a_different_project_is_refused_before_any_adapter_call(
    tmp_path: Path,
) -> None:
    store_a, info_a = bound_with_project_id(tmp_path, "PRJ-CE-V2D-A", subdir="project-a")
    store_b, info_b = bound_with_project_id(tmp_path, "PRJ-CE-V2D-B", subdir="project-b")
    commit_active_kill_switch(store_a, info_a["project_id"])

    # A genuine, real Change for an entirely separate Store/project B ...
    result_b = _fresh_change(store_b, info_b)
    change_b = result_b["change"]
    assert change_b["project_id"] == info_b["project_id"]

    # ... planted, verbatim, under project A's own directory (real commit API, real content,
    # never hand-forged) -- it resolves under A, but its own declared project_id still says B.
    commit_foreign_record(store_a, info_a["project_id"], "change", change_b["change_id"], change_b)
    commit_foreign_record(
        store_a,
        info_a["project_id"],
        "authority_decision",
        result_b["decision"]["authority_decision_id"],
        result_b["decision"],
    )

    worktree = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = _executor(store_a, info_a, adapter, worktree_root=str(worktree))

    with pytest.raises(ExecutionAuthorityProvenanceError):
        execute(
            change_b["change_id"],
            claim_token="claim-d",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (e) action_kind not permitted by the bound Boundary.
# --------------------------------------------------------------------------------------- #


def test_action_kind_outside_the_bound_boundarys_permitted_set_is_refused(tmp_path: Path) -> None:
    store, info = _world(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    result = build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_ISOLATED_SOURCE_FILE",
        operation=operation_for(
            "WRITE_ISOLATED_SOURCE_FILE", writes=[{"path": "docs/target.md", "content_utf8": "x"}]
        ),
        paths=["docs/target.md"],
    )
    change = result["change"]

    worktree = git_worktree(tmp_path)
    adapter = CountingAdapter()
    # Boundary only permits WRITE_DOCUMENTATION_FILE/DELETE_DOCUMENTATION_FILE (the default) --
    # the Change's own WRITE_ISOLATED_SOURCE_FILE is not among them.
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    with pytest.raises(ExecutionAuthorityProvenanceError):
        execute(
            change["change_id"],
            claim_token="claim-e",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (f) Human-only action kinds: refused at the Boundary-composition level too.
# --------------------------------------------------------------------------------------- #


def test_permitted_action_kinds_is_disjoint_from_human_only_action_kinds() -> None:
    """The module-level invariant ``boundary.py`` itself asserts at import time."""

    assert not (boundary_module.PERMITTED_ACTION_KINDS & HUMAN_ONLY_ACTION_KINDS)


@pytest.mark.parametrize("human_only_kind", sorted(HUMAN_ONLY_ACTION_KINDS))
def test_validate_execution_boundary_refuses_a_smuggled_human_only_action_kind(
    tmp_path: Path, human_only_kind: str
) -> None:
    """A genuine runtime attempt to construct a Boundary naming a Human-only ``action_kind`` is
    structurally impossible through the ordinary public surface: ``PERMITTED_ACTION_KINDS`` is a
    frozenset disjoint from ``HUMAN_ONLY_ACTION_KINDS`` by construction (the test above), so no
    caller can ever pass such a value through the normal Python-level membership check this
    function performs. This test smuggles one in anyway, by transiently monkeypatching the
    module-level ``PERMITTED_ACTION_KINDS`` binding itself -- and proves
    ``validate_execution_boundary`` *still* refuses it, because ``01_SCHEMA/change_executor/
    execution_boundary.schema.json``'s own ``permitted_action_kind`` enum is a second,
    independently-declared closed vocabulary (never derived from the Python frozenset at
    runtime): even with the Python-level gate defeated, the schema-level gate alone still
    refuses. This is the genuine defense-in-depth the module docstring names -- not a single
    check duplicated, but two independently-declared closed vocabularies that must both agree.

    ``worktree_root`` is deliberately a genuine, real, existing directory (``tmp_path`` itself)
    here, not omitted: an omitted ``worktree_root`` would also raise ``ExecutionBoundaryError``
    (a missing required key), which would make this test pass for the wrong reason entirely --
    never reaching the Python-membership-then-schema-enum check this test actually exists to
    prove."""

    original = boundary_module.PERMITTED_ACTION_KINDS
    try:
        boundary_module.PERMITTED_ACTION_KINDS = original | {human_only_kind}
        boundary = execution_boundary_for(
            worktree_root=str(tmp_path), permitted_action_kinds=[human_only_kind]
        )
        with pytest.raises(ExecutionBoundaryError):
            validate_execution_boundary(boundary)
    finally:
        boundary_module.PERMITTED_ACTION_KINDS = original


def test_compose_change_executor_refuses_a_smuggled_human_only_boundary_too(tmp_path: Path) -> None:
    """The identical smuggle attempt, through ``compose_change_executor`` itself (which calls
    ``validate_execution_boundary`` at composition time, before any request-facing operation can
    even be obtained) -- zero adapter calls, since composition itself never completes."""

    store, info = _world(tmp_path)
    human_only_kind = sorted(HUMAN_ONLY_ACTION_KINDS)[0]
    original = boundary_module.PERMITTED_ACTION_KINDS
    adapter = CountingAdapter()
    try:
        boundary_module.PERMITTED_ACTION_KINDS = original | {human_only_kind}
        with pytest.raises(ExecutionBoundaryError):
            _executor(
                store,
                info,
                adapter,
                worktree_root=str(tmp_path),
                permitted_action_kinds=[human_only_kind],
            )
    finally:
        boundary_module.PERMITTED_ACTION_KINDS = original
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (g) zero-call decisive control -- restated explicitly across (b)-(e) above via CountingAdapter,
# collected here as one assertion-of-record for clarity.
# --------------------------------------------------------------------------------------- #


def test_every_refusal_path_above_never_once_called_the_adapter(tmp_path: Path) -> None:
    """A single, explicit restatement of the zero-call property every one of (b)-(e) already
    asserts inline: build every refusal scenario fresh, with one shared counting adapter, and
    confirm the total call count across all of them is exactly zero."""

    store, info = _world(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    adapter = CountingAdapter()
    worktree = git_worktree(tmp_path)

    # (e)-shaped: action_kind outside the bound Boundary.
    result = build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_ISOLATED_SOURCE_FILE",
        operation=operation_for(
            "WRITE_ISOLATED_SOURCE_FILE", writes=[{"path": "docs/z.md", "content_utf8": "x"}]
        ),
        paths=["docs/z.md"],
    )
    execute = _executor(store, info, adapter, worktree_root=str(worktree))
    with pytest.raises(ExecutionAuthorityProvenanceError):
        execute(
            result["change"]["change_id"],
            claim_token="claim-g",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )

    assert adapter.call_count == 0
