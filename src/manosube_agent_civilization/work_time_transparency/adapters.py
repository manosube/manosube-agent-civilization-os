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
semantics.

``tests/integration/work_time_transparency/test_work_time_transparency_adapter_conformance.py``
proves this composes correctly with the real, unmodified production entrypoint of every
execution-capable adapter present at this delivery's own base -- all 8 of 8, per Structural
Review Round 1's own P84-R1-F1 requirement.

**Structural Review Round 1 corrections (P84-R1-F4).** This primitive no longer accepts
``opened_at``/``completed_at`` as caller-supplied timestamps: it reads exactly one injected
*clock* (a zero-argument callable returning a canonical UTC timestamp, defaulting to
:func:`~manosube_agent_civilization.work_time_transparency.clock.default_clock`, the one real
wall-clock reading in this entire package) once before opening and once after *perform* returns
or raises, and refuses a non-monotonic observation rather than silently clamping a negative
duration to zero. *perform* now receives one argument -- a :class:`ProgressReporter` bound to
the open coordination -- so a real, possibly long-running adapter call can post genuine
in-flight heartbeats/external-wait notices through the identical, fully-verified
:func:`~manosube_agent_civilization.work_time_transparency.route.record_work_time_progress_
update` boundary, rather than the coordination being limited to only an open and a terminal
notice around one opaque, silent call.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .clock import default_clock, is_monotonic
from .errors import WorkTimeTransparencyClockError
from .route import (
    open_work_time_coordination,
    record_work_time_progress_update,
    record_work_time_terminal_notice,
)


class ProgressReporter:
    """Bound to one open coordination; a real adapter call receives one of these (as
    :func:`with_work_time_coordination`'s own *perform* argument) and may call :meth:`report`
    zero or more times while it is still running, to post a genuine in-flight heartbeat,
    estimate revision, or external-wait notice. Each call durably commits one
    ``work_time_coordination_update`` record, chained to whichever record -- the open, or this
    reporter's own previous update -- is currently this coordination's live tip; the tip is
    tracked here so a caller never has to compute its own sequence number or predecessor_ref."""

    def __init__(
        self,
        store: Any,
        *,
        project_id: str,
        project_binding_id: str,
        open_ref: dict[str, str],
        clock: Callable[[], str],
    ) -> None:
        self._store = store
        self._project_id = project_id
        self._project_binding_id = project_binding_id
        self._open_ref = open_ref
        self._clock = clock
        self._tip_ref = open_ref
        self._sequence_number = 0

    @property
    def tip_ref(self) -> dict[str, str]:
        """This coordination's current live tip -- the ``predecessor_ref`` the eventual terminal
        notice must chain to."""

        return self._tip_ref

    def report(
        self,
        *,
        position_kind: str,
        current_position: str,
        next_progress_update_due_minutes: int,
        material_result_or_blocker: str = "",
        remaining_duration_unknown: bool = False,
        revised_remaining_duration_lower_minutes: int | None = None,
        revised_remaining_duration_upper_minutes: int | None = None,
        human_action_required: bool = False,
    ) -> dict[str, Any]:
        """Post one real, immediately-committed progress update -- the in-flight channel P84-R1-
        F4 requires: a long-running or externally-waiting real adapter call can report genuine
        progress *while it is still running*, not only through a terminal notice observed after
        it ends."""

        self._sequence_number += 1
        recorded_at = self._clock()
        record = record_work_time_progress_update(
            self._store,
            project_id=self._project_id,
            project_binding_id=self._project_binding_id,
            open_ref=self._open_ref,
            predecessor_ref=self._tip_ref,
            sequence_number=self._sequence_number,
            position_kind=position_kind,
            current_position=current_position,
            material_result_or_blocker=material_result_or_blocker,
            remaining_duration_unknown=remaining_duration_unknown,
            revised_remaining_duration_lower_minutes=revised_remaining_duration_lower_minutes,
            revised_remaining_duration_upper_minutes=revised_remaining_duration_upper_minutes,
            human_action_required=human_action_required,
            next_progress_update_due_minutes=next_progress_update_due_minutes,
            recorded_at=recorded_at,
        )
        self._tip_ref = {
            "kind": "work_time_coordination_update",
            "id": record["work_time_coordination_update_id"],
        }
        return record


def with_work_time_coordination[T](
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    adapter_kind: str,
    work_unit_ref: dict[str, str],
    estimated_duration_lower_minutes: int,
    estimated_duration_upper_minutes: int,
    estimate_confidence: str,
    major_steps: list[str],
    next_progress_update_due_minutes: int,
    variability_factors: str,
    perform: Callable[[ProgressReporter], T],
    clock: Callable[[], str] = default_clock,
) -> tuple[dict[str, Any], dict[str, Any], T]:
    """Open a Work Coordination, call *perform* (one real adapter entrypoint call, unmodified,
    receiving a bound :class:`ProgressReporter`), and close the coordination: ``COMPLETED`` if
    *perform* returns, ``FAILED_TERMINAL`` if it raises -- the original exception is always
    re-raised unchanged after the terminal notice is durably committed, never swallowed. Returns
    ``(open_record, terminal_record, perform_result)`` on success.

    *clock* is read exactly twice by this function itself: once to open (``opened_at``), and
    once immediately after *perform* returns or raises (the terminal's own ``recorded_at``).
    Every other observed time -- each :meth:`ProgressReporter.report` call's own ``recorded_at``
    -- is also a fresh *clock* read, made by the reporter itself while *perform* is still
    running. A terminal observation that is not at or after ``opened_at`` raises
    :class:`~manosube_agent_civilization.work_time_transparency.errors.
    WorkTimeTransparencyClockError` -- Structural Review Round 1's own P84-R1-F4 requirement to
    reject non-monotonic time, never silently clamp a negative duration to zero."""

    opened_at = clock()
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
    reporter = ProgressReporter(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        open_ref=open_ref,
        clock=clock,
    )

    try:
        result = perform(reporter)
    except Exception as error:
        terminal_time = clock()
        if not is_monotonic(opened_at, terminal_time):
            raise WorkTimeTransparencyClockError(
                f"observed terminal time {terminal_time!r} is before opened_at {opened_at!r}"
            ) from error
        record_work_time_terminal_notice(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            open_ref=open_ref,
            predecessor_ref=reporter.tip_ref,
            terminal_outcome="FAILED_TERMINAL",
            explanation=f"{type(error).__name__}: {error}",
            recorded_at=terminal_time,
        )
        raise

    terminal_time = clock()
    if not is_monotonic(opened_at, terminal_time):
        raise WorkTimeTransparencyClockError(
            f"observed terminal time {terminal_time!r} is before opened_at {opened_at!r}"
        )
    terminal_record = record_work_time_terminal_notice(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        open_ref=open_ref,
        predecessor_ref=reporter.tip_ref,
        terminal_outcome="COMPLETED",
        explanation="",
        recorded_at=terminal_time,
    )
    return open_record, terminal_record, result


__all__ = ["ProgressReporter", "with_work_time_coordination"]
