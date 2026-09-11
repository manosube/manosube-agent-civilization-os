"""P18-R2-F2 (Structural Review Round 2, ADOPT_P18_R2_STRUCTURAL_CORRECTIONS): composition-time
``worktree_root`` identity verification against the bound Boundary's own ``repository``/
``branch``.

Structural Review Round 1 (P18-R1-F3) made ``worktree_root`` a required, schema-validated field
*inside* the closed Execution Boundary itself, folding it into the Boundary fingerprint -- but
explicitly disclaimed proving the directory it names is genuinely a checkout of that same
Boundary's own declared ``repository``/``branch`` at all. This file proves the required-proof
matrix R2_F2_NEGATIVE/R2_F2_POSITIVE:

(a) R2_F2_NEGATIVE -- a real, valid directory that IS a git checkout, but of a genuinely
    different branch, or a different remote ``repository``, than the Boundary claims, is refused
    by ``validate_execution_boundary``/``compose_change_executor``.
(c) a directory that is not a git checkout at all (no ``.git`` whatsoever) is refused too, for
    the *right* reason (a readable, git-identity-specific message, not merely "not a directory").
(b) R2_F2_POSITIVE -- a real git checkout whose branch/remote genuinely match the Boundary's own
    declared ``repository``/``branch`` passes composition, and a real ``execute()`` call
    succeeds through it end to end.

Every real git repository this file builds is built via the real ``git`` binary itself (test-only
-- this package's own non-network/non-subprocess-call constraint is about the *shipped* package's
own modules, never about what a test's own setup does)."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest
from tests.fixtures.change_executor_kill_switch_issuer import issuer_public_key_hex
from tests.fixtures.change_executor_world import (
    BRANCH,
    REPOSITORY,
    CountingAdapter,
    bound,
    build_committed_change,
    commit_active_kill_switch,
    execution_boundary_for,
    git_worktree,
    operation_for,
)

from manosube_agent_civilization.change_executor.boundary import validate_execution_boundary
from manosube_agent_civilization.change_executor.errors import ExecutionBoundaryError
from manosube_agent_civilization.change_executor.route import compose_change_executor


def _run_git(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    """The one, real ``git`` invocation this file shares -- test-only (this package's own
    non-subprocess-call constraint is about the *shipped* package's own modules, never about
    what a test's own setup does). Kept to one call site so the security-linter suppression
    lives in exactly one place."""

    command = ["git", *args] if cwd is None else ["git", "-C", cwd, *args]
    return subprocess.run(command, check=True, capture_output=True, text=True)  # noqa: S603


def _configure_local_git_identity(cwd: str) -> None:
    """Set a repo-local commit identity -- never relying on the ambient environment's own
    global git config being present, which a genuinely portable CI environment need not have."""

    _run_git("config", "user.email", "change-executor-fixture@example.invalid", cwd=cwd)
    _run_git("config", "user.name", "Change Executor Fixture", cwd=cwd)


# --------------------------------------------------------------------------------------- #
# (a) R2_F2_NEGATIVE -- a real git checkout of a mismatched branch, or a mismatched remote
# repository, is refused.
# --------------------------------------------------------------------------------------- #


def test_worktree_root_checked_out_to_a_different_branch_is_refused(tmp_path: Path) -> None:
    worktree = git_worktree(tmp_path, repository=REPOSITORY, branch="an-unrelated-branch")
    boundary = execution_boundary_for(worktree_root=str(worktree))
    with pytest.raises(ExecutionBoundaryError, match="branch"):
        validate_execution_boundary(boundary)


def test_worktree_root_with_a_different_origin_remote_is_refused(tmp_path: Path) -> None:
    worktree = git_worktree(tmp_path, repository="org/an-unrelated-repo", branch=BRANCH)
    boundary = execution_boundary_for(worktree_root=str(worktree))
    with pytest.raises(ExecutionBoundaryError, match="repository"):
        validate_execution_boundary(boundary)


def test_worktree_root_mismatch_is_refused_at_composition_too(tmp_path: Path) -> None:
    """Not merely a unit-level ``validate_execution_boundary`` proof -- the identical refusal
    reaches all the way up through ``compose_change_executor`` itself, before any request-facing
    operation can even be obtained."""

    store, info = bound(tmp_path)
    worktree = git_worktree(tmp_path, repository=REPOSITORY, branch="a-different-branch-again")
    with pytest.raises(ExecutionBoundaryError):
        compose_change_executor(
            store,
            project_id=info["project_id"],
            project_binding_id=info["project_binding_id"],
            execution_boundary=execution_boundary_for(worktree_root=str(worktree)),
            adapter_identity={"kind": "controlled_filesystem_adapter", "version": "0.1"},
            adapter=CountingAdapter(),
            kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
        )


def test_worktree_root_detached_head_is_refused(tmp_path: Path) -> None:
    """A detached HEAD cannot prove a branch identity at all -- refused closed, never treated as
    an ambiguous "maybe matches"."""

    worktree = git_worktree(tmp_path, repository=REPOSITORY, branch=BRANCH)
    _configure_local_git_identity(str(worktree))
    _run_git("commit", "--allow-empty", "-m", "genesis", cwd=str(worktree))
    head_sha = _run_git("rev-parse", "HEAD", cwd=str(worktree)).stdout.strip()
    _run_git("checkout", head_sha, cwd=str(worktree))

    boundary = execution_boundary_for(worktree_root=str(worktree))
    with pytest.raises(ExecutionBoundaryError, match="detached"):
        validate_execution_boundary(boundary)


# --------------------------------------------------------------------------------------- #
# (c) a directory that is not a git checkout at all is refused too, for the right reason.
# --------------------------------------------------------------------------------------- #


def test_worktree_root_with_no_git_directory_at_all_is_refused_for_the_right_reason(
    tmp_path: Path,
) -> None:
    plain = tmp_path / "plain-directory"
    plain.mkdir()
    boundary = execution_boundary_for(worktree_root=str(plain))
    with pytest.raises(ExecutionBoundaryError, match="\\.git"):
        validate_execution_boundary(boundary)


# --------------------------------------------------------------------------------------- #
# (b) R2_F2_POSITIVE -- a real, matching git checkout passes composition, and a real execute()
# call succeeds through it end to end.
# --------------------------------------------------------------------------------------- #


def test_matching_worktree_root_passes_composition_and_a_real_execution_succeeds(
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
            writes=[{"path": "docs/worktree-identity.md", "content_utf8": "real content"}],
        ),
        paths=["docs/worktree-identity.md"],
    )
    change = result["change"]

    worktree = git_worktree(tmp_path)
    boundary = validate_execution_boundary(execution_boundary_for(worktree_root=str(worktree)))
    assert boundary["worktree_root"] == str(worktree)

    adapter = CountingAdapter()
    execute = compose_change_executor(
        store,
        project_id=project_id,
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree)),
        adapter_identity={"kind": "controlled_filesystem_adapter", "version": "0.1"},
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )
    outcome = execute(
        change["change_id"],
        claim_token="matching-worktree-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    assert outcome["receipt"]["outcome"] == "SUCCEEDED"
    assert adapter.call_count == 1
    assert (worktree / "docs" / "worktree-identity.md").read_text(encoding="utf-8") == (
        "real content"
    )


def test_matching_worktree_root_via_https_remote_url_form_also_passes(tmp_path: Path) -> None:
    """``_normalize_repository_slug`` must handle the ``https://github.com/owner/repo.git`` form
    exactly as it handles the bare ``owner/repo`` slug ``REPOSITORY`` already uses."""

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    _run_git("init", "--quiet", str(worktree))
    _run_git("symbolic-ref", "HEAD", f"refs/heads/{BRANCH}", cwd=str(worktree))
    _run_git("remote", "add", "origin", f"https://github.com/{REPOSITORY}.git", cwd=str(worktree))
    boundary = validate_execution_boundary(execution_boundary_for(worktree_root=str(worktree)))
    assert boundary["repository"] == REPOSITORY


def test_matching_worktree_root_via_scp_like_remote_url_form_also_passes(tmp_path: Path) -> None:
    """The ``git@github.com:owner/repo.git`` scp-like form is handled identically."""

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    _run_git("init", "--quiet", str(worktree))
    _run_git("symbolic-ref", "HEAD", f"refs/heads/{BRANCH}", cwd=str(worktree))
    _run_git("remote", "add", "origin", f"git@github.com:{REPOSITORY}.git", cwd=str(worktree))
    boundary = validate_execution_boundary(execution_boundary_for(worktree_root=str(worktree)))
    assert boundary["repository"] == REPOSITORY


def test_linked_git_worktree_resolves_via_its_own_commondir(tmp_path: Path) -> None:
    """A genuine ``git worktree add`` linked worktree -- its own ``.git`` is a *file* naming the
    real gitdir, and that gitdir's own ``commondir`` names the main repository's own git
    directory, which alone carries the populated ``config`` this check reads. Requires one real
    commit (an empty tree is not eligible for a second worktree checkout of the same branch, so
    this creates a genuinely separate branch for the linked worktree, still under the identical
    declared ``repository``)."""

    main = git_worktree(tmp_path, repository=REPOSITORY, branch=BRANCH, subdir="main")
    _configure_local_git_identity(str(main))
    _run_git("commit", "--allow-empty", "-m", "genesis", cwd=str(main))
    linked = tmp_path / "linked"
    _run_git("worktree", "add", "-b", "linked-branch", str(linked), cwd=str(main))
    boundary = execution_boundary_for(
        worktree_root=str(linked), repository=REPOSITORY, branch="linked-branch"
    )
    validated = validate_execution_boundary(boundary)
    assert validated["worktree_root"] == str(linked)
