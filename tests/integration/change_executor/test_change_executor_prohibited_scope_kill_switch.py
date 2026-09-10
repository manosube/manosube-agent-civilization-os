"""V5 (Issue #73): prohibited-scope and kill-switch matrix.

Every Human-only action kind is refused at Boundary construction; every path outside a
Boundary's admitted set is refused (including the sibling-directory-collision case); traversal
is refused both at ``route.py``'s own operation-admission check and, independently, at
``ControlledFilesystemAdapter``'s own defense-in-depth; every one of the six fixed-``False``
permission toggles is refused; and the kill switch is proven a genuine, fail-closed gate at
every checkpoint -- missing, revoked, wrong-key-signed (refused by the committer itself, before
it ever becomes current), pre-start, and a genuine mid-execution revocation racing the one
in-flight call.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.change_executor_kill_switch_issuer import (
    issuer_public_key_hex,
    wrong_kill_switch_signature,
)
from tests.fixtures.change_executor_world import (
    CountingAdapter,
    bound,
    build_committed_change,
    commit_active_kill_switch,
    commit_revoked_successor,
    execution_boundary_for,
    operation_for,
)

from manosube_agent_civilization.authority.levels import HUMAN_ONLY_ACTION_KINDS
from manosube_agent_civilization.change_executor.adapter import ControlledFilesystemAdapter
from manosube_agent_civilization.change_executor.boundary import validate_execution_boundary
from manosube_agent_civilization.change_executor.errors import (
    ExecutionAuthorityProvenanceError,
    ExecutionBoundaryError,
    ExecutionKillSwitchError,
)
from manosube_agent_civilization.change_executor.kill_switch import (
    commit_change_executor_kill_switch,
    kill_switch_id,
    kill_switch_semantic_fingerprint,
    kill_switch_signing_payload,
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
        execution_boundary=execution_boundary_for(**boundary_overrides),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        worktree_root=worktree_root,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )


# --------------------------------------------------------------------------------------- #
# (a) Human-only action kinds can never appear in a valid Execution Boundary.
# --------------------------------------------------------------------------------------- #


@pytest.mark.parametrize("human_only_kind", sorted(HUMAN_ONLY_ACTION_KINDS))
def test_human_only_action_kind_cannot_populate_a_valid_boundary(human_only_kind: str) -> None:
    boundary = execution_boundary_for(permitted_action_kinds=[human_only_kind])
    with pytest.raises(ExecutionBoundaryError):
        validate_execution_boundary(boundary)


@pytest.mark.parametrize("human_only_kind", sorted(HUMAN_ONLY_ACTION_KINDS))
def test_compose_change_executor_refuses_a_boundary_naming_a_human_only_kind(
    tmp_path: Path, human_only_kind: str
) -> None:
    store, info = bound(tmp_path)
    adapter = CountingAdapter()
    with pytest.raises(ExecutionBoundaryError):
        _executor(
            store,
            info,
            adapter,
            worktree_root=str(tmp_path),
            permitted_action_kinds=[human_only_kind],
        )
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (b) a path outside admitted_paths is refused -- including the sibling-directory collision.
# --------------------------------------------------------------------------------------- #


def test_sibling_directory_path_is_not_admitted_by_a_narrower_admitted_prefix(
    tmp_path: Path,
) -> None:
    """``admitted_paths=["docs"]`` must never admit ``"docs-private/x.md"`` -- they share a
    literal string prefix, but ``docs-private`` is not nested under ``docs`` at all."""

    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    result = build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": "docs-private/x.md", "content_utf8": "x"}],
        ),
        paths=["docs-private/x.md"],
    )
    change = result["change"]

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree), admitted_paths=["docs"])

    with pytest.raises(ExecutionAuthorityProvenanceError):
        execute(
            change["change_id"],
            claim_token="sibling",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (c) traversal/symlink escape -- both route.py's own path-admission check, and the adapter's
# own independent defense-in-depth.
# --------------------------------------------------------------------------------------- #


def test_operation_naming_a_traversal_path_is_refused_by_routes_own_admission_check(
    tmp_path: Path,
) -> None:
    """A hand-built ``action.operation`` naming ``"../outside.txt"`` -- a path entirely
    distinct from the Change's own admitted ``scope.paths`` -- is caught by ``route.py``'s own
    operation-level path admission (step 14), never reaching the adapter: ``path_is_admitted``'s
    segment-based comparison never matches ``".."`` against any admitted prefix."""

    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    result = build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE", writes=[{"path": "../outside.txt", "content_utf8": "x"}]
        ),
        paths=["docs/legit.md"],
    )
    change = result["change"]

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    outcome = execute(
        change["change_id"],
        claim_token="traversal",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    assert outcome["receipt"]["outcome"] == "BOUNDARY_VIOLATION"
    assert adapter.call_count == 0, "the adapter must never be reached for a BOUNDARY_VIOLATION"


def test_adapter_itself_refuses_a_real_symlink_planted_inside_the_worktree(tmp_path: Path) -> None:
    """Called directly, bypassing ``route.py`` entirely: a genuine on-disk symlink planted
    inside ``worktree_root``, pointing outside it, is refused by the adapter's own defense-in-
    depth -- never written through, and reported as a structural fact (``error`` set), never
    raised."""

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (worktree / "docs").symlink_to(outside)

    adapter = ControlledFilesystemAdapter(
        executor_identity="controlled_filesystem_adapter", executor_version="0.1"
    )
    report = adapter.execute(
        {
            "operation_kind": "WRITE_DOCUMENTATION_FILE",
            "file_writes": [{"path": "docs/evil.txt", "content_utf8": "escaped"}],
            "file_deletes": [],
        },
        worktree_root=str(worktree),
    )
    assert report["files_written"] == []
    assert report["error"] is not None
    assert not (outside / "evil.txt").exists()


def test_adapter_itself_refuses_writing_through_an_existing_symlink_leaf(tmp_path: Path) -> None:
    """The leaf target itself is a symlink (not a parent component) -- also refused, never
    followed."""

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("original", encoding="utf-8")
    (worktree / "link.txt").symlink_to(outside_file)

    adapter = ControlledFilesystemAdapter(
        executor_identity="controlled_filesystem_adapter", executor_version="0.1"
    )
    report = adapter.execute(
        {
            "operation_kind": "WRITE_DOCUMENTATION_FILE",
            "file_writes": [{"path": "link.txt", "content_utf8": "escaped"}],
            "file_deletes": [],
        },
        worktree_root=str(worktree),
    )
    assert report["files_written"] == []
    assert report["error"] is not None
    assert outside_file.read_text(encoding="utf-8") == "original"


# --------------------------------------------------------------------------------------- #
# (d) every one of the six fixed-False permission toggles is refused if supplied True.
# --------------------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "toggle",
    (
        "permit_symlinks",
        "permit_path_traversal",
        "permit_network",
        "permit_subprocess",
        "permit_environment_mutation",
        "permit_credential_access",
    ),
)
def test_fixed_false_permission_toggle_is_refused_when_supplied_true(toggle: str) -> None:
    boundary = execution_boundary_for(**{toggle: True})
    with pytest.raises(ExecutionBoundaryError):
        validate_execution_boundary(boundary)


# --------------------------------------------------------------------------------------- #
# (e) kill switch: missing, revoked, and wrong-key-signed.
# --------------------------------------------------------------------------------------- #


def test_no_kill_switch_ever_committed_refuses_with_zero_adapter_calls(tmp_path: Path) -> None:
    store, info = bound(tmp_path)
    result = build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE", writes=[{"path": "docs/x.md", "content_utf8": "x"}]
        ),
        paths=["docs/x.md"],
        extra_state_revision_headroom=0,
    )
    change = result["change"]
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    with pytest.raises(ExecutionKillSwitchError):
        execute(
            change["change_id"],
            claim_token="no-switch",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert adapter.call_count == 0


def test_revoked_kill_switch_refuses_with_zero_adapter_calls(tmp_path: Path) -> None:
    store, info = bound(tmp_path)
    active = commit_active_kill_switch(store, info["project_id"])
    commit_revoked_successor(store, info["project_id"], active)

    result = build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE", writes=[{"path": "docs/x.md", "content_utf8": "x"}]
        ),
        paths=["docs/x.md"],
    )
    change = result["change"]
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    with pytest.raises(ExecutionKillSwitchError):
        execute(
            change["change_id"],
            claim_token="revoked",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert adapter.call_count == 0


def test_wrong_key_signed_kill_switch_is_refused_by_the_committer_itself(tmp_path: Path) -> None:
    """The negative control on ``commit_change_executor_kill_switch`` directly: a genuine
    Ed25519 signature, by a genuine second keypair that is *not* the bound trust anchor, never
    becomes current -- refused before it is ever committed, let alone resolved by ``execute``."""

    store, info = bound(tmp_path)
    record: dict[str, Any] = {
        "schema_version": "0.1",
        "change_executor_kill_switch_id": "",
        "project_id": info["project_id"],
        "status": "ACTIVE",
        "generation": 0,
        "predecessor_ref": None,
        "signature": {"algorithm": "ed25519", "key_id": "WRONG-KEY-0001", "value": "0" * 128},
        "change_executor_kill_switch_semantic_fingerprint": "",
    }
    record["change_executor_kill_switch_id"] = kill_switch_id(record)
    record["change_executor_kill_switch_semantic_fingerprint"] = kill_switch_semantic_fingerprint(
        record
    )
    payload = kill_switch_signing_payload(record)
    record["signature"] = wrong_kill_switch_signature(payload)

    with pytest.raises(ExecutionKillSwitchError):
        commit_change_executor_kill_switch(
            store,
            info["project_id"],
            record,
            trust_anchor_public_key_hex=issuer_public_key_hex(),
            committed_at="2026-09-10T00:00:00Z",
        )

    # And, independently: no kill switch became current at all.
    from manosube_agent_civilization.change_executor.kill_switch import resolve_current_kill_switch

    assert resolve_current_kill_switch(store, info["project_id"]) is None


# --------------------------------------------------------------------------------------- #
# (f) pre-start stop -- revoked before execute() is ever called.
# --------------------------------------------------------------------------------------- #


def test_pre_start_kill_switch_revocation_refuses_with_zero_adapter_calls(tmp_path: Path) -> None:
    store, info = bound(tmp_path)
    active = commit_active_kill_switch(store, info["project_id"])

    result = build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE", writes=[{"path": "docs/x.md", "content_utf8": "x"}]
        ),
        paths=["docs/x.md"],
        extra_state_revision_headroom=1,
    )
    change = result["change"]

    commit_revoked_successor(store, info["project_id"], active)

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    adapter = CountingAdapter()
    execute = _executor(store, info, adapter, worktree_root=str(worktree))

    with pytest.raises(ExecutionKillSwitchError):
        execute(
            change["change_id"],
            claim_token="pre-start",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert adapter.call_count == 0


# --------------------------------------------------------------------------------------- #
# (g) safe mid-execution stop -- a genuine revocation racing the one in-flight call.
# --------------------------------------------------------------------------------------- #


class _RevokeOnFirstLoadCurrent:
    """A thin, real Store proxy -- forwards every call unchanged except the *first* call to
    ``load_current`` for *project_id*, which additionally commits a genuine ``REVOKED``
    successor kill switch (through the real, verify-only ``commit_change_executor_kill_switch``,
    never a mock) as a side effect before delegating.

    **Why ``load_current`` is the correct, precise hook, per this file's own reading of
    route.py's own step 13 comment.** Checkpoint #1 (step 3) and checkpoint #2 (step 13) both
    resolve the kill switch through ``read_current_consistent`` (confirmed by this suite's own
    static-conformance proof that ``resolve_current_kill_switch`` never calls ``load_current``),
    so hooking ``read_current_consistent`` would fire on checkpoint #1 itself, before any Change
    is even resolved -- too early to reach checkpoint #2 at all. ``load_current`` is instead
    used *only* by this package's own ``_commit_records`` (the execution_intent/execution_
    attempt/receipt commits, steps 11/12/17) and by ``commit_change_executor_kill_switch``'s own
    retry loop -- never by any kill-switch *read*. Triggering the revocation on the first such
    call (the ``execution_intent`` commit, step 11 -- necessarily *after* checkpoint #1 already
    saw ``ACTIVE``, and necessarily *before* checkpoint #2 runs) reproduces the exact race this
    control needs: ``ACTIVE`` at checkpoint #1, genuinely ``REVOKED`` by checkpoint #2, entirely
    within the one in-flight ``execute()`` call the task's own wording asks to prove -- not
    across two separate calls for two different slots, which checkpoint #1 alone would already
    refuse before ever reaching checkpoint #2 a second time (see this test's own docstring).
    """

    def __init__(self, inner: Any, project_id: str, active_kill_switch: dict[str, Any]) -> None:
        self._inner = inner
        self._project_id = project_id
        self._active = active_kill_switch
        self._triggered = False

    def load_current(self, project_id: str) -> dict[str, Any]:
        if not self._triggered and project_id == self._project_id:
            self._triggered = True
            commit_revoked_successor(self._inner, self._project_id, self._active)
        result: dict[str, Any] = self._inner.load_current(project_id)
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def test_mid_execution_kill_switch_revocation_produces_a_terminal_kill_switch_stopped_receipt(
    tmp_path: Path,
) -> None:
    """A genuine kill-switch revocation, racing the one in-flight ``execute()`` call between
    checkpoint #1 (still ``ACTIVE``) and checkpoint #2 (now ``REVOKED``), produces a terminal
    ``KILL_SWITCH_STOPPED`` receipt -- not a bare exception -- because an ``execution_attempt``
    is already durably committed by the time checkpoint #2 runs, and this package's own
    idempotency contract requires a terminal outcome for any committed attempt."""

    store, info = bound(tmp_path)
    active = commit_active_kill_switch(store, info["project_id"])
    proxy = _RevokeOnFirstLoadCurrent(store, info["project_id"], active)

    result = build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE", writes=[{"path": "docs/mid.md", "content_utf8": "x"}]
        ),
        paths=["docs/mid.md"],
    )
    change = result["change"]

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    adapter = CountingAdapter()
    execute = compose_change_executor(
        proxy,
        project_id=info["project_id"],
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        worktree_root=str(worktree),
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )

    outcome = execute(
        change["change_id"],
        claim_token="mid-execution",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    assert outcome["receipt"]["outcome"] == "KILL_SWITCH_STOPPED"
    assert adapter.call_count == 0, "the adapter must never be reached once checkpoint #2 refuses"

    # And a second call for this exact slot, now genuinely stale (this package's own commits
    # from the first call advanced state_revision -- see V4's own module docstring), is at least
    # never silently retried into a second real mutation.
    from manosube_agent_civilization.change_executor.errors import StaleExecutionInputError

    with pytest.raises((StaleExecutionInputError, ExecutionKillSwitchError)):
        execute(
            change["change_id"],
            claim_token="mid-execution",  # noqa: S106
            execution_instant="2026-09-10T00:00:02Z",
        )
