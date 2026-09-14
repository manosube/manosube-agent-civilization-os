"""Typed errors for the Human Wait-Time Transparency vertical (Issue #22)."""

from __future__ import annotations


class WorkTimeTransparencyError(Exception):
    """Base class for every error this package raises."""


class WorkTimeTransparencyValidationError(WorkTimeTransparencyError):
    """A caller-supplied value is malformed, out of range, or violates one of this package's
    own closed rules (material-reestimate detection, chain-position invariants, the single-
    terminal-notice rule)."""


class WorkTimeTransparencyLineageError(WorkTimeTransparencyError):
    """A caller-supplied reference (``open_ref``/``predecessor_ref``) does not resolve to a
    real, congruent record in this project's own Store -- a nonexistent open, a cross-project
    or cross-coordination predecessor, a skipped/reordered/forked sequence position, an update
    after a terminal notice already exists, or a terminal notice with no resolvable open.
    Raised only by :mod:`~manosube_agent_civilization.work_time_transparency.verify`'s own
    resolve-and-verify boundary (Structural Review Round 1, P84-R1-F2/F5) -- never by trusting
    a caller-supplied record body."""


class WorkTimeTransparencyClockError(WorkTimeTransparencyError):
    """An observed timestamp is not monotonically consistent with the coordination's own prior
    recorded time (a terminal or update time at or before its own predecessor's time) --
    Structural Review Round 1, P84-R1-F4."""


__all__ = [
    "WorkTimeTransparencyClockError",
    "WorkTimeTransparencyError",
    "WorkTimeTransparencyLineageError",
    "WorkTimeTransparencyValidationError",
]
