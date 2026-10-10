"""Unreadable Git identity must refuse the execution boundary before any write.

Baseline metadata is initialized by real Git. Pointer cases exercise metadata
parsing, without claiming membership in an independently verified remote tree.
"""

from pathlib import Path

import pytest
from tests.fixtures.change_executor_world import execution_boundary_for, git_worktree

from manosube_agent_civilization.change_executor.boundary import validate_execution_boundary
from manosube_agent_civilization.change_executor.errors import ExecutionBoundaryError


@pytest.fixture
def checkout(tmp_path):
    root = git_worktree(tmp_path)
    boundary = execution_boundary_for(worktree_root=str(root))
    assert validate_execution_boundary(boundary) == boundary
    return root, boundary


@pytest.mark.parametrize("head", ["", "a" * 40, "ref: refs/tags/main", "ref: refs/heads/"])
def test_unprovable_branch_metadata_is_refused(checkout, head):
    root, boundary = checkout
    (root / ".git" / "HEAD").write_text(head, encoding="utf-8")
    with pytest.raises(ExecutionBoundaryError):
        validate_execution_boundary(boundary)


@pytest.mark.parametrize(
    "config", ["", "not-ini", "[core]\nbare=false\n", '[remote "origin"]\nfetch=anything\n']
)
def test_missing_or_unreadable_origin_is_refused(checkout, config):
    root, boundary = checkout
    (root / ".git" / "config").write_text(config, encoding="utf-8")
    with pytest.raises(ExecutionBoundaryError):
        validate_execution_boundary(boundary)


@pytest.mark.parametrize(
    "remote",
    [
        "https://github.com",
        "git@github.com:",
        "git@elsewhere.example:owner/repo",
        "relative/repo",
        "http://github.com/owner/repo",
        "https://github.com/foreign/repo",
    ],
)
def test_origin_syntax_and_host_cannot_substitute_the_declared_repository(checkout, remote):
    root, boundary = checkout
    (root / ".git" / "config").write_text(f'[remote "origin"]\nurl={remote}\n', encoding="utf-8")
    with pytest.raises(ExecutionBoundaryError):
        validate_execution_boundary(boundary)


@pytest.mark.parametrize("metadata", ["HEAD", "config"])
def test_absent_identity_file_is_refused(checkout, metadata):
    root, boundary = checkout
    (root / ".git" / metadata).unlink()
    with pytest.raises(ExecutionBoundaryError):
        validate_execution_boundary(boundary)


@pytest.mark.parametrize("pointer", ["", "not-a-gitdir", "gitdir: does-not-exist"])
def test_bad_gitdir_pointer_is_refused(checkout, tmp_path, pointer):
    _root, boundary = checkout
    linked = tmp_path / "linked"
    linked.mkdir()
    (linked / ".git").write_text(pointer, encoding="utf-8")
    with pytest.raises(ExecutionBoundaryError):
        validate_execution_boundary({**boundary, "worktree_root": str(linked)})


def test_absent_git_entry_is_refused(checkout, tmp_path):
    _root, boundary = checkout
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ExecutionBoundaryError):
        validate_execution_boundary({**boundary, "worktree_root": str(empty)})


def test_a_gitdir_pointer_to_readable_metadata_uses_its_actual_identity(checkout, tmp_path):
    root, boundary = checkout
    linked = tmp_path / "linked"
    linked.mkdir()
    (linked / ".git").write_text(f"gitdir: {root / '.git'}", encoding="utf-8")
    candidate = {**boundary, "worktree_root": str(linked)}
    assert validate_execution_boundary(candidate) == candidate


def test_common_metadata_pointer_is_resolved_and_an_unreadable_target_is_refused(
    checkout, tmp_path
):
    root, boundary = checkout
    linked = tmp_path / "linked"
    linked.mkdir()
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "HEAD").write_text(
        (root / ".git" / "HEAD").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (metadata / "commondir").write_text(str(root / ".git"), encoding="utf-8")
    (linked / ".git").write_text(f"gitdir: {metadata}", encoding="utf-8")
    candidate = {**boundary, "worktree_root": str(linked)}
    assert validate_execution_boundary(candidate) == candidate
    (metadata / "commondir").write_text("missing", encoding="utf-8")
    with pytest.raises(ExecutionBoundaryError):
        validate_execution_boundary(candidate)


@pytest.mark.parametrize("file", ["HEAD", "commondir", ".git"])
def test_identity_read_failures_cannot_be_silently_accepted(checkout, tmp_path, monkeypatch, file):
    root, boundary = checkout
    if file == ".git":
        linked = tmp_path / "linked"
        linked.mkdir()
        target = linked / ".git"
        target.write_text(f"gitdir: {root / '.git'}", encoding="utf-8")
        boundary = {**boundary, "worktree_root": str(linked)}
    else:
        target = root / ".git" / file
        if file == "commondir":
            target.write_text(str(root / ".git"), encoding="utf-8")
    real = Path.read_text

    def unreadable(path, *args, **kwargs):
        if path == target:
            raise OSError("simulated unreadable metadata")
        return real(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)
    with pytest.raises(ExecutionBoundaryError):
        validate_execution_boundary(boundary)
