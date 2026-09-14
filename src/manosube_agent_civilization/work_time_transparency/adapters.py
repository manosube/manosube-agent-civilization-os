"""The one composition primitive every execution-capable adapter uses to get identical canonical
Work Coordination semantics (Issue #22's own "Kernel Placement": "It must be referenced by the
canonical execution entrypoint and by every adapter that can start work. Adapter-specific UI may
format the notice differently but must preserve the same fields and timing rules.").

**Disclosed judgment call.** This module deliberately does not import CLI/Boot/Temporary Agent/
Model Runtime/Multi-Agent/Change Executor/Independent Verification/Projection and does not wrap
their public entrypoints itself -- doing so would make ``work_time_transparency`` a new upstream
dependency of eight unrelated verticals' own route.py modules (or force this module to duplicate
each one's own complex Authority/Boundary/Grant precondition chain), which is exactly the "second
owner" duplication the adoption's own mandatory pre-design inventory instructs against, and is
unjustified risk to eight already-accepted, already-reviewed verticals for a UX/coordination-only
concern. Instead, :func:`with_work_time_coordination` is the one shared, generic composition
point -- a caller (any adapter's own route.py, or, in this delivery, each adapter's own real
production entrypoint invoked directly from this package's own conformance tests) wraps a call to
its own unmodified real entrypoint through this function and gets identical canonical timing
semantics: a Work Coordination Open before the call, a Work Coordination Terminal Notice after it
(``COMPLETED`` on a normal return, ``FAILED_TERMINAL`` on an unhandled exception -- re-raised
unchanged after the terminal notice is recorded), and, for callers whose own work exceeds the
estimate's own heartbeat deadline, :func:`~manosube_agent_civilization.work_time_transparency.
engine.is_heartbeat_overdue` to detect (never enforce) a missed heartbeat.

``tests/integration/work_time_transparency/test_work_time_transparency_adapter_conformance.py``
proves this composes correctly with the real, unmodified production entrypoint of every
execution-capable adapter present at this delivery's own base.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from .route import (
    open_work_time_coordination,
    record_work_time_terminal_notice,
)


def _elapsed_minutes(opened_at: str, completed_at: str) -> int:
    """Both timestamps are canonical UTC (``01_SCHEMA/common/timestamp.schema.json``, always
    ``Z``-suffixed) -- ``fromisoformat`` needs the offset spelled ``+00:00`` to parse it.
    Rounded to the nearest whole minute: the canonical serializer (``state.canonicalize``)
    prohibits floating-point values repository-wide, so every committed duration field in this
    package is an integer minute count, never a fractional one."""

    started = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
    ended = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    return max(round((ended - started).total_seconds() / 60.0), 0)


def with_work_time_coordination[T](
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    adapter_kind: str,
    work_unit_ref: Mapping[str, str],
    estimated_duration_lower_minutes: int,
    estimated_duration_upper_minutes: int,
    estimate_confidence: str,
    major_steps: list[str],
    next_progress_update_due_minutes: int,
    variability_factors: str,
    opened_at: str,
    completed_at: str,
    perform: Callable[[], T],
) -> tuple[dict[str, Any], dict[str, Any], T]:
    """Open a Work Coordination, call *perform* (a zero-argument callable wrapping one real
    adapter entrypoint call, unmodified), and close the coordination: ``COMPLETED`` if *perform*
    returns, ``FAILED_TERMINAL`` if it raises -- the original exception is always re-raised
    unchanged after the terminal notice is durably committed, never swallowed. Returns
    ``(open_record, terminal_record, perform_result)`` on success.

    Elapsed time is the caller's own *opened_at*/*completed_at* pair, not a clock this function
    reads itself -- the identical "no owner here reads a clock" discipline
    :mod:`~manosube_agent_civilization.work_time_transparency.engine`'s own module docstring
    states, and what makes every one of this module's own tests deterministic."""

    open_record = open_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        work_unit_ref=work_unit_ref,
        adapter_kind=adapter_kind,
        estimated_duration_lower_minutes=estimated_duration_lower_minutes,
        estimated_duration_upper_minutes=estimated_duration_upper_minutes,
        estimate_confidence=estimate_confidence,
        major_steps=major_steps,
        next_progress_update_due_minutes=next_progress_update_due_minutes,
        variability_factors=variability_factors,
        opened_at=opened_at,
    )
    open_ref = {
        "kind": "work_time_coordination_open",
        "id": open_record["work_time_coordination_open_id"],
    }
    elapsed_minutes = _elapsed_minutes(opened_at, completed_at)
    try:
        result = perform()
    except Exception as error:
        record_work_time_terminal_notice(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            open_ref=open_ref,
            predecessor_ref=open_ref,
            terminal_outcome="FAILED_TERMINAL",
            actual_elapsed_minutes=elapsed_minutes,
            explanation=f"{type(error).__name__}: {error}",
            recorded_at=completed_at,
        )
        raise
    terminal_record = record_work_time_terminal_notice(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        open_ref=open_ref,
        predecessor_ref=open_ref,
        terminal_outcome="COMPLETED",
        actual_elapsed_minutes=elapsed_minutes,
        explanation="",
        recorded_at=completed_at,
    )
    return open_record, terminal_record, result


__all__ = ["with_work_time_coordination"]
