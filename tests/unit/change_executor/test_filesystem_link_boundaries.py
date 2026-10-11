"""Real filesystem negative controls for the execution adapter's write boundary."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from manosube_agent_civilization.change_executor.adapter import ControlledFilesystemAdapter

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX descriptor-relative adapter")


def _write(root: Path, path: str, content: str = "new") -> dict:
    return ControlledFilesystemAdapter(executor_identity="test", executor_version="1").execute(
        {"file_writes": [{"path": path, "content_utf8": content}], "file_deletes": []},
        worktree_root=str(root),
    )


def test_hardlink_write_is_refused_without_changing_either_name(tmp_path: Path) -> None:
    root = tmp_path / "work"
    root.mkdir()
    outside = tmp_path / "protected"
    outside.write_text("original")
    os.link(outside, root / "allowed")
    result = _write(root, "allowed")
    assert result["error"] is not None
    assert result["files_written"] == []
    assert outside.read_text() == (root / "allowed").read_text() == "original"


def test_replacement_does_not_write_through_an_open_existing_inode(tmp_path: Path) -> None:
    target = tmp_path / "allowed"
    target.write_text("old")
    with target.open() as previous:
        assert _write(tmp_path, "allowed")["error"] is None
        assert previous.read() == "old"
    assert target.read_text() == "new"
    assert not list(tmp_path.glob(".manosube-*"))


def test_symlink_parent_cannot_redirect_new_file(tmp_path: Path) -> None:
    root = tmp_path / "work"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "docs").symlink_to(outside, target_is_directory=True)
    assert _write(root, "docs/new.md")["error"] is not None
    assert not (outside / "new.md").exists()
