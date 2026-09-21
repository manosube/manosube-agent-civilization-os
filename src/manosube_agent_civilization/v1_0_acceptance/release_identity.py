"""Release identity/receipt surface (Issue #92, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

A pure data surface only -- this module never invokes `git tag`, never pushes, and
never publishes a GitHub release. The adoption is explicit:
`GITHUB_RELEASE_PUBLICATION_ALLOWED=false`, `RELEASE_TAG_CREATION_ALLOWED=false`.
It computes the same repository-shape fingerprint `04_REPOSITORY_ARCHITECTURE.md`'s
own `AS_BUILT_TREE_ENTRY_COUNT` convention already uses (blob count + tree/directory
count from `git ls-tree -r -t`), bound to an exact commit SHA, so a later Human
release action has a ready, already-verified identity to bind a real tag to -- it
does not itself decide when that release happens.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from typing import Literal

from .commit_binding import resolve_commit_sha
from .errors import ReleaseIdentityError


@dataclass(frozen=True)
class ReleaseIdentity:
    commit_sha: str
    tree_entry_count: int
    blob_count: int
    directory_count: int
    version_label: str
    tag_created: Literal[False]
    release_published: Literal[False]


def compute_release_identity(
    repo_root: Path, commit_sha: str, version_label: str
) -> ReleaseIdentity:
    """Compute the release identity surface for `commit_sha`, without creating or
    publishing anything. `commit_sha` is first canonicalized via
    `commit_binding.resolve_commit_sha` (commit-object semantics equivalent to
    `git rev-parse --verify <commit_sha>^{commit}`) -- `git ls-tree` alone accepts any
    tree-ish (a branch name, `HEAD`, a tag, or even a raw tree object), so without this
    the persisted `commit_sha` could silently change meaning as a branch advances, or
    fail to identify a commit at all (PR #93 Structural Review Round 1, `P93-R1-F2`).
    Only the resolved lowercase 40-hex SHA is ever stored."""
    resolved_commit_sha = resolve_commit_sha(repo_root, commit_sha)

    git = shutil.which("git")
    if git is None:
        raise ReleaseIdentityError("git executable not found on PATH")
    result = subprocess.run(  # noqa: S603 -- fixed Git executable resolved via shutil.which above
        [git, "ls-tree", "-r", "-t", resolved_commit_sha],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseIdentityError(
            f"git ls-tree -r -t {resolved_commit_sha!r} failed (exit {result.returncode}): {result.stderr}"
        )

    blob_count = 0
    tree_count = 0
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        # "<mode> <type> <sha>\t<path>"
        entry_type = line.split("\t", 1)[0].split(" ")[1]
        if entry_type == "blob":
            blob_count += 1
        elif entry_type == "tree":
            tree_count += 1

    return ReleaseIdentity(
        commit_sha=resolved_commit_sha,
        tree_entry_count=blob_count + tree_count,
        blob_count=blob_count,
        directory_count=tree_count,
        version_label=version_label,
        tag_created=False,
        release_published=False,
    )


__all__ = ["ReleaseIdentity", "compute_release_identity"]
