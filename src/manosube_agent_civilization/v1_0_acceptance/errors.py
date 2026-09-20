"""Typed exception hierarchy for the v1.0 Acceptance package (Issue #92,
`ADOPT_PHASE_22_V1_0_ACCEPTANCE`)."""

from __future__ import annotations


class V1_0AcceptanceError(Exception):
    """Base for every error this package raises."""


class GateRederivationError(V1_0AcceptanceError):
    """A Gate 22 predicate could not be mechanically rederived from its owning
    evidence -- e.g. its owning test module is missing, or subprocess execution of
    the owning test suite itself failed to start (never conflated with the owning
    suite's own PASS/FAIL verdict, which is a valid, expected outcome)."""


class DeferredDifferencesRegisterError(V1_0AcceptanceError):
    """`06_DEFERRED_DIFFERENCES.md` could not be read, or a record inside it does
    not carry the required shape (`DIFFERENCE_ID`/`CANDIDATE_ID`, `CLASSIFICATION`,
    `CURRENT_STATUS`, `CURRENT_PHASE_BLOCKING_EFFECT`) this package depends on."""


class ReleaseIdentityError(V1_0AcceptanceError):
    """A release identity/receipt surface value failed schema validation or one of
    this package's own fail-closed structural checks."""


class CommitResolutionError(V1_0AcceptanceError):
    """A caller-supplied ref (`delivery_head`, `authorized_base_main_sha`, or a
    `release_identity` commit input) does not resolve to a real commit object in the
    target repository -- e.g. it is a raw tree/blob object, an unresolvable ref, or
    simply does not exist there. Never silently accepted merely because it matches a
    40-hex schema pattern (PR #93 Structural Review Round 1, `P93-R1-F2`)."""


class DeliveryHeadBindingError(V1_0AcceptanceError):
    """The repository at `repo_root` is not exactly, cleanly at the resolved delivery
    commit -- its actual checked-out `HEAD` differs from the requested commit, its
    tracked worktree/index carries uncommitted changes, or a supplied
    `authorized_base_main_sha` is not a real ancestor of the delivery commit. Rederiving
    Gate 22 predicates or the Deferred Differences register against such a repository
    would silently attach current-worktree (or unauthorized) evidence to a different
    commit than the one being accepted (PR #93 Structural Review Round 1, `P93-R1-F1`/
    `P93-R1-F5`)."""


class RepositoryProjectBindingError(V1_0AcceptanceError):
    """`repo_root`'s resolved GitHub `owner/repo` project identity (from its `origin`
    remote URL) does not equal the authorized project. Commit-object identity and
    ancestry (`CommitResolutionError`/`DeliveryHeadBindingError`) prove nothing about
    *which* repository a caller-supplied `repo_root` actually is -- a clone or fork
    carrying the exact same git objects is not a substitute for the authorized
    repository/project identity (PR #93 Structural Review Round 2, `P93-R2-F1`)."""


__all__ = [
    "CommitResolutionError",
    "DeferredDifferencesRegisterError",
    "DeliveryHeadBindingError",
    "GateRederivationError",
    "ReleaseIdentityError",
    "RepositoryProjectBindingError",
    "V1_0AcceptanceError",
]
