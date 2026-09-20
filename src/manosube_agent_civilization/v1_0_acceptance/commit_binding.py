"""Exact delivery-commit binding and canonical commit resolution (PR #93 Structural
Review Round 1, `ADOPT_P93_R1_F1_F2_F3_F4_F5`, findings `P93-R1-F1`/`P93-R1-F2`, and
`P93-R1-F5`'s closing ancestry-verification requirement).

Every value this package treats as a commit identity -- `delivery_head`,
`authorized_base_main_sha`, a `release_identity.commit_sha` input -- is resolved
through this module's `resolve_commit_sha` before it is used or persisted, with
commit-object semantics equivalent to `git rev-parse --verify <ref>^{commit}`: a
branch name, tag, `HEAD`, or abbreviated SHA resolves to its target commit's
canonical lowercase 40-hex SHA; a raw tree or blob object, or any unresolvable ref,
fails closed.

Gate 22 predicate rederivation and the Deferred Differences register read both
operate on `repo_root`'s current on-disk worktree state, which has no inherent
relationship to a caller-supplied `delivery_head` label unless
`resolve_and_bind_delivery_head` is called first and its result is the only value
downstream code treats as the delivery commit -- this closes the exact substitution
gap Structural Review found: a historical or unauthorized commit could previously be
recorded as `delivery_head` while the actual rederivation silently ran against a
different (or dirty) worktree.
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess

from .errors import CommitResolutionError, DeliveryHeadBindingError

_CANONICAL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    git = shutil.which("git")
    if git is None:
        raise CommitResolutionError("git executable not found on PATH")
    return subprocess.run(  # noqa: S603 -- fixed Git executable resolved via shutil.which above
        [git, *args], cwd=repo_root, capture_output=True, text=True, check=False
    )


def resolve_commit_sha(repo_root: Path, ref: str) -> str:
    """Canonicalize `ref` to the lowercase 40-hex SHA of the commit object it names,
    via commit-object semantics equivalent to `git rev-parse --verify <ref>^{commit}`.
    A raw tree/blob object, or any ref that cannot be peeled to a commit, fails closed
    with `CommitResolutionError` -- never silently accepted merely because it matches
    the 40-hex schema pattern."""
    result = _git(repo_root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if result.returncode != 0:
        raise CommitResolutionError(
            f"{ref!r} does not resolve to a commit object in {repo_root}: {result.stderr.strip()}"
        )
    sha = result.stdout.strip()
    if not _CANONICAL_SHA_PATTERN.fullmatch(sha):
        raise CommitResolutionError(
            f"resolved value {sha!r} for {ref!r} is not a canonical lowercase 40-hex commit SHA"
        )
    return sha


def verify_repo_root_bound_to_commit(repo_root: Path, resolved_commit_sha: str) -> None:
    """Fail closed unless `repo_root`'s actual current `HEAD` is exactly
    `resolved_commit_sha` and its tracked worktree/index carry no uncommitted change.
    This is the fail-closed alternative to checking out a disposable temporary
    worktree at that commit before rederiving -- Structural Review's own second
    suggested remedy for the same finding (`P93-R1-F1`)."""
    head_result = _git(repo_root, "rev-parse", "HEAD")
    if head_result.returncode != 0:
        raise CommitResolutionError(
            f"could not resolve HEAD in {repo_root}: {head_result.stderr.strip()}"
        )
    actual_head = head_result.stdout.strip()
    if actual_head != resolved_commit_sha:
        raise DeliveryHeadBindingError(
            f"repo_root HEAD {actual_head!r} does not match the requested delivery "
            f"commit {resolved_commit_sha!r} -- rederiving against a historical or "
            "different-commit worktree while recording a different delivery_head is "
            "exactly the substitution this check exists to reject"
        )
    status_result = _git(repo_root, "status", "--porcelain", "--untracked-files=no")
    if status_result.returncode != 0:
        raise CommitResolutionError(
            f"could not read worktree status in {repo_root}: {status_result.stderr.strip()}"
        )
    if status_result.stdout.strip():
        raise DeliveryHeadBindingError(
            f"tracked worktree/index at {resolved_commit_sha!r} is not clean -- "
            "uncommitted evidence must never be silently rederived as accepted:\n"
            f"{status_result.stdout}"
        )


def resolve_and_bind_delivery_head(repo_root: Path, delivery_head: str) -> str:
    """Canonicalize `delivery_head` and verify `repo_root` is exactly, cleanly at
    that commit. Returns the resolved lowercase 40-hex SHA -- the only value any
    downstream rederivation call may treat as the delivery commit."""
    resolved = resolve_commit_sha(repo_root, delivery_head)
    verify_repo_root_bound_to_commit(repo_root, resolved)
    return resolved


def verify_authorized_base_ancestry(repo_root: Path, base_sha: str, delivery_head_sha: str) -> None:
    """Fail closed unless `base_sha` is a real ancestor of (or equal to)
    `delivery_head_sha` in `repo_root`'s own git history -- `authorized_base_main_sha`
    must never be accepted merely because it matches the 40-hex schema pattern
    (`P93-R1-F5`'s own closing requirement)."""
    result = _git(repo_root, "merge-base", "--is-ancestor", base_sha, delivery_head_sha)
    if result.returncode != 0:
        raise DeliveryHeadBindingError(
            f"authorized_base_main_sha {base_sha!r} is not a real ancestor of "
            f"delivery_head {delivery_head_sha!r} in this repository's history "
            "(git merge-base --is-ancestor rejected it)"
        )


def resolve_and_verify_authorized_base(
    repo_root: Path, authorized_base_main_sha: str, resolved_delivery_head: str
) -> str:
    """Canonicalize `authorized_base_main_sha` and verify it is a real ancestor of
    `resolved_delivery_head`. Returns the resolved lowercase 40-hex SHA."""
    resolved_base = resolve_commit_sha(repo_root, authorized_base_main_sha)
    verify_authorized_base_ancestry(repo_root, resolved_base, resolved_delivery_head)
    return resolved_base


__all__ = [
    "resolve_and_bind_delivery_head",
    "resolve_and_verify_authorized_base",
    "resolve_commit_sha",
    "verify_authorized_base_ancestry",
    "verify_repo_root_bound_to_commit",
]
