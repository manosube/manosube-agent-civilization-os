"""The one production execution adapter: a real, bounded filesystem writer/deleter (Phase 18,
Issue #73).

:class:`ControlledFilesystemAdapter` performs NO network, NO subprocess, NO environment
mutation, and NO credential access -- this module imports none of ``socket``, ``subprocess``,
``urllib``, or ``requests`` anywhere, and never mutates ``os.environ``, so a static-conformance
test can assert this by AST import inspection alone. It holds no ambient authority of its own --
no Store, no Boundary, no Project identity -- only whatever self-identification data its own
constructor is given; it never itself decides whether an operation is in-scope, and it is
confined, on every call, to a caller-supplied ``worktree_root`` it never chooses.

**The traversal/symlink-escape enforcement below is real, not decorative** (V5/V6). For every
target path this adapter is asked to touch, it: (1) rejects an absolute path or any ``.``/``..``
segment outright, before touching the filesystem at all; (2) walks every existing intermediate
ancestor directory from ``worktree_root`` down to the target's own parent and refuses if any of
them is itself a symlink -- a symlink placed at any point along the path could otherwise redirect
the walk outside ``worktree_root`` even if the final resolved path happens to look safe; (3)
refuses outright if the target path itself already exists as a symlink (writing through an
existing symlink would silently write to wherever it points, and this package never permits
following one); and (4) as defense in depth, independently resolves the target with
``Path.resolve()`` and requires the resolved path's own ``parts`` to genuinely begin with
``worktree_root``'s own resolved ``parts``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import ExecutionAdapterError


class ControlledFilesystemAdapter:
    """A real, bounded filesystem writer/deleter, confined to writing UTF-8 text files and
    deleting files strictly beneath a caller-supplied ``worktree_root``.

    Constructor takes no ambient authority -- no Store, no Boundary -- only adapter-identity
    data used purely for self-identification in the facts it reports.
    """

    def __init__(self, *, executor_identity: str, executor_version: str) -> None:
        if not isinstance(executor_identity, str) or not executor_identity:
            raise ExecutionAdapterError("executor_identity must be a non-empty string")
        if not isinstance(executor_version, str) or not executor_version:
            raise ExecutionAdapterError("executor_version must be a non-empty string")
        self.executor_identity = executor_identity
        self.executor_version = executor_version

    def execute(self, operation: Any, *, worktree_root: str) -> dict[str, Any]:
        """Perform exactly the writes/deletes *operation* names, strictly beneath
        *worktree_root*, and return ``{"files_written", "bytes_written", "files_deleted",
        "error"}`` -- raw, structurally bounded facts. Never raises for an ordinary filesystem
        failure (a symlink refusal, a missing file to delete, a permission error): every such
        failure is reported as ``error`` instead, so the caller (this package's own
        ``route.py``, never this adapter) can classify the outcome from the facts alone. Only a
        genuinely malformed *operation*/*worktree_root* argument raises
        :class:`~manosube_agent_civilization.change_executor.errors.ExecutionAdapterError`
        directly."""

        if not isinstance(operation, dict):
            raise ExecutionAdapterError(f"operation must be a mapping, not {type(operation)!r}")
        if not isinstance(worktree_root, str) or not worktree_root:
            raise ExecutionAdapterError("worktree_root must be a non-empty string path")

        root = Path(worktree_root).resolve()
        if not root.is_dir():
            raise ExecutionAdapterError(f"worktree_root does not exist as a directory: {root}")

        files_written: list[str] = []
        bytes_written = 0
        files_deleted: list[str] = []
        error: str | None = None

        writes = operation.get("file_writes") or []
        deletes = operation.get("file_deletes") or []

        try:
            for entry in writes:
                rel_path = entry["path"]
                content = entry["content_utf8"]
                target = self._resolve_within_root(root, rel_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                encoded = content.encode("utf-8")
                target.write_bytes(encoded)
                files_written.append(rel_path)
                bytes_written += len(encoded)
            for entry in deletes:
                rel_path = entry["path"]
                target = self._resolve_within_root(root, rel_path)
                target.unlink()
                files_deleted.append(rel_path)
        except Exception as exc:  # reported as a raw fact, never re-raised
            error = f"{type(exc).__name__}: {exc}"

        return {
            "files_written": files_written,
            "bytes_written": bytes_written,
            "files_deleted": files_deleted,
            "error": error,
        }

    def _resolve_within_root(self, root: Path, rel_path: Any) -> Path:
        """Return the real, resolved path *rel_path* names beneath *root* -- or raise
        :class:`~manosube_agent_civilization.change_executor.errors.ExecutionAdapterError` if
        it is malformed, traverses through a symlink at any component, is itself an existing
        symlink, or resolves outside *root*."""

        if type(rel_path) is not str or not rel_path:
            raise ExecutionAdapterError(f"path must be a non-empty string: {rel_path!r}")
        if rel_path.startswith("/"):
            raise ExecutionAdapterError(f"path must be relative, not absolute: {rel_path!r}")
        segments = rel_path.split("/")
        if any(segment in ("", ".", "..") for segment in segments):
            raise ExecutionAdapterError(
                f"path must contain no empty, '.', or '..' segment: {rel_path!r}"
            )

        current = root
        for segment in segments[:-1]:
            current = current / segment
            if current.exists() and current.is_symlink():
                raise ExecutionAdapterError(
                    f"path component is a symlink -- refusing to traverse it: {current}"
                )

        leaf = root.joinpath(*segments)
        if leaf.exists() and leaf.is_symlink():
            raise ExecutionAdapterError(f"path names an existing symlink -- refusing: {leaf}")

        resolved = leaf.resolve()
        root_parts = root.parts
        if resolved.parts[: len(root_parts)] != root_parts:
            raise ExecutionAdapterError(
                f"resolved path escapes worktree_root: {rel_path!r} -> {resolved}"
            )
        return resolved


__all__ = ["ControlledFilesystemAdapter"]
