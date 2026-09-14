"""Typed errors for the Human Wait-Time Transparency vertical (Issue #22)."""

from __future__ import annotations


class WorkTimeTransparencyError(Exception):
    """Base class for every error this package raises."""


class WorkTimeTransparencyValidationError(WorkTimeTransparencyError):
    """A caller-supplied value is malformed, out of range, or violates one of this package's
    own closed rules (material-reestimate detection, chain-position invariants, the single-
    terminal-notice rule)."""


__all__ = ["WorkTimeTransparencyError", "WorkTimeTransparencyValidationError"]
