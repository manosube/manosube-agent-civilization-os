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


__all__ = [
    "DeferredDifferencesRegisterError",
    "GateRederivationError",
    "ReleaseIdentityError",
    "V1_0AcceptanceError",
]
