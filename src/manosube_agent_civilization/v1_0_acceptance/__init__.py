"""v1.0 Acceptance (Issue #92, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

Public surface: exactly the four entry points below. This package creates no new
canonical owner and persists no Store-committed record -- it mechanically rederives
Gate 22's twelve predicates from already-accepted Phase 0-21 evidence, classifies
every candidate v1.0-blocking Difference against the existing Deferred Differences
register, and computes a release identity/receipt surface bound to an exact commit --
never a git tag, never a GitHub release, never a v1.0 declaration.
"""

from __future__ import annotations

from .blocking_differences import (
    DifferenceDisposition,
    classify_v1_0_blocking_differences,
)
from .engine import build_v1_0_acceptance_bundle
from .gate22 import PredicateRederivation, rederive_all_pytest_owned_predicates
from .release_identity import ReleaseIdentity, compute_release_identity

PUBLIC_V1_0_ACCEPTANCE_ENTRY_POINT_COUNT = 4

__all__ = [
    "PUBLIC_V1_0_ACCEPTANCE_ENTRY_POINT_COUNT",
    "DifferenceDisposition",
    "PredicateRederivation",
    "ReleaseIdentity",
    "build_v1_0_acceptance_bundle",
    "classify_v1_0_blocking_differences",
    "compute_release_identity",
    "rederive_all_pytest_owned_predicates",
]
