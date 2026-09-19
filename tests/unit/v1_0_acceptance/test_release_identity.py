"""V1: release identity/receipt surface (Issue #92, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

`tag_created=False`/`release_published=False` are asserted as `Literal[False]` in the
dataclass itself; these tests exist to prove the tree-entry-count computation is real
(matches `git ls-tree -r -t` on the exact commit) and that a bad commit fails closed.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

from manosube_agent_civilization.v1_0_acceptance.errors import ReleaseIdentityError
from manosube_agent_civilization.v1_0_acceptance.release_identity import (
    compute_release_identity,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_release_identity_matches_independent_git_ls_tree() -> None:
    identity = compute_release_identity(REPO_ROOT, "HEAD", "v1.0-candidate")

    git = shutil.which("git")
    assert git is not None
    result = subprocess.run(  # noqa: S603 -- fixed Git executable resolved via shutil.which above
        [git, "ls-tree", "-r", "-t", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    blob_count = sum(1 for line in lines if line.split("\t", 1)[0].split(" ")[1] == "blob")
    tree_count = sum(1 for line in lines if line.split("\t", 1)[0].split(" ")[1] == "tree")

    assert identity.blob_count == blob_count
    assert identity.directory_count == tree_count
    assert identity.tree_entry_count == blob_count + tree_count


def test_release_identity_never_creates_tag_or_publishes() -> None:
    identity = compute_release_identity(REPO_ROOT, "HEAD", "v1.0-candidate")
    assert identity.tag_created is False
    assert identity.release_published is False


def test_unresolvable_commit_fails_closed() -> None:
    with pytest.raises(ReleaseIdentityError):
        compute_release_identity(REPO_ROOT, "0000000000000000000000000000000000000000", "v1.0")
