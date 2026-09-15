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

**Structural Review Round 4 correction (P84-R4-F1, ``ADOPT_P84_R4_WTT_JOIN_AND_LEDGER_RECOVERY_
CLOSURE``).** :func:`verify_joined_coordination` is the Store-verified boundary a nested-join
composition must pass through -- see that function's own docstring for the full defect this
replaces (Round 3's own ``joined_coordination`` public parameter accepted any object without
verifying it named a real, currently-open, correctly-adapter-kinded, non-terminal coordination
bound to the same Store/project/binding)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .clock import default_clock, is_monotonic
from .errors import WorkTimeTransparencyClockError, WorkTimeTransparencyLineageError
from .route import (
    open_work_time_coordination,
    record_work_time_progress_update,
    record_work_time_terminal_notice,
)
from .verify import resolve_open, resolve_terminal_if_exists, verify_binding_congruity


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

    @property
    def open_ref(self) -> dict[str, str]:
        """This coordination's own root identity (Structural Review Round 3, P84-R3-F4) -- lets
        a nested adapter call join this same, already-open coordination instead of opening a
        second, independent one of its own."""

        return self._open_ref

    @property
    def store(self) -> Any:
        """This coordination's own bound Store instance (Structural Review Round 4, P84-R4-F1)
        -- read, never write, and used only by :func:`verify_joined_coordination` to confirm a
        reporter presented for a nested join is bound to the same Store instance the joining
        call itself is operating on."""

        return self._store

    @property
    def project_id(self) -> str:
        """This coordination's own bound project id (Structural Review Round 4, P84-R4-F1)."""

        return self._project_id

    @property
    def project_binding_id(self) -> str:
        """This coordination's own bound project binding id (Structural Review Round 4,
        P84-R4-F1)."""

        return self._project_binding_id

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


def verify_joined_coordination(
    store: Any,
    reporter: Any,
    *,
    project_id: str,
    project_binding_id: str,
    expected_adapter_kind: str,
) -> dict[str, Any]:
    """Verify that *reporter* genuinely names a currently open, non-terminal Work Coordination
    of *expected_adapter_kind*, bound to this exact *store*/*project_id*/*project_binding_id* --
    the one shared, Store-verified boundary a nested-join composition must pass through before
    it may post through *reporter* instead of opening its own coordination root (Structural
    Review Round 4, P84-R4-F1, ``ADOPT_P84_R4_WTT_JOIN_AND_LEDGER_RECOVERY_CLOSURE``).

    Round 3's own ``joined_coordination`` design (P84-R3-F4) exposed this join as an ordinary
    public parameter on :func:`~manosube_agent_civilization.model_runtime.route.
    open_model_work_unit`, checked only for ``is not None`` -- a caller-forgeable duck-typed
    object with a no-op ``report`` method, a genuine reporter resolved against a different
    project or a different (or already-closed) coordination, or a captured/replayed reporter
    object could all suppress that call's own mandatory Work Coordination. This function is the
    correction: it is never reachable from any public route parameter (the public
    ``open_model_work_unit`` no longer accepts a join capability at all -- see that function's
    own docstring), and is called only by an adapter's own internal nested-join composition
    (today, only :mod:`~manosube_agent_civilization.model_runtime.route`'s own private
    ``_open_model_work_unit_joined``, itself reachable only from
    :mod:`~manosube_agent_civilization.multi_agent.route`'s internal composition) -- but even
    there, the reporter it receives is still fully re-verified here, never merely trusted
    because of who is presumed to have called this:

    - *reporter* must be a genuine :class:`ProgressReporter` instance -- refusing a duck-typed
      substitute, since Python's own ``isinstance`` cannot be satisfied by an object that merely
      happens to expose the same attribute names.
    - *reporter* must be bound to this exact *store* object (by identity, not equality) and to
      this exact *project_id*/*project_binding_id* -- refusing a genuine reporter resolved
      against a different Store, project, or binding.
    - *reporter*'s own ``open_ref`` must resolve, through this package's own canonical
      resolve-and-verify boundary (:func:`~manosube_agent_civilization.work_time_transparency.
      verify.resolve_open`), to a real, schema-valid, content-addressed, binding-congruent
      ``work_time_coordination_open`` record -- refusing a fabricated or substituted reference.
    - that open record's own ``adapter_kind`` must equal *expected_adapter_kind* -- refusing an
      unrelated genuine coordination opened under a different adapter (a standalone
      ``MODEL_RUNTIME`` coordination, say) from ever being joined as if it were the expected
      outer coordination.
    - that coordination must not already have a terminal notice
      (:func:`~manosube_agent_civilization.work_time_transparency.verify.
      resolve_terminal_if_exists`) -- refusing a join onto an already-closed coordination,
      including one closed since the reporter object was first created (a replayed capability).

    Every refusal here is :class:`~manosube_agent_civilization.work_time_transparency.errors.
    WorkTimeTransparencyLineageError`, raised before the nested call ever starts model work.
    Returns the resolved, verified open record on success."""

    if not isinstance(reporter, ProgressReporter):
        raise WorkTimeTransparencyLineageError(
            "joined coordination must be a genuine ProgressReporter instance -- refusing a "
            f"duck-typed substitute ({type(reporter)!r})"
        )
    if reporter.store is not store:
        raise WorkTimeTransparencyLineageError(
            "joined coordination is bound to a different Store instance -- refusing"
        )
    if reporter.project_id != project_id or reporter.project_binding_id != project_binding_id:
        raise WorkTimeTransparencyLineageError(
            f"joined coordination is bound to project {reporter.project_id!r}/"
            f"{reporter.project_binding_id!r}, not the operating project "
            f"{project_id!r}/{project_binding_id!r} -- cross-project/binding join refused"
        )
    open_record = resolve_open(store, project_id, reporter.open_ref)
    verify_binding_congruity(open_record=open_record, project_binding_id=project_binding_id)
    if open_record.get("adapter_kind") != expected_adapter_kind:
        raise WorkTimeTransparencyLineageError(
            "joined coordination's own open was recorded under adapter_kind "
            f"{open_record.get('adapter_kind')!r}, not the expected "
            f"{expected_adapter_kind!r} -- unrelated coordination join refused"
        )
    open_id = open_record["work_time_coordination_open_id"]
    if resolve_terminal_if_exists(store, project_id, open_id) is not None:
        raise WorkTimeTransparencyLineageError(
            f"coordination {open_id!r} already has a terminal notice -- joining a closed "
            "coordination refused"
        )
    return open_record


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
        # Structural Review Round 2 (P84-R2-F5): if persisting the FAILED_TERMINAL notice
        # itself raises, that persistence failure must never replace *error* as the exception
        # this function raises -- the original adapter failure is always the primary fact. The
        # persistence failure is instead attached to *error* as a secondary diagnostic (a note,
        # per Python's own built-in mechanism for exactly this) and set as its __cause__, so it
        # remains fully inspectable without ever becoming the raised exception itself.
        try:
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
        except Exception as persistence_error:
            error.add_note(
                "work_time_transparency: terminal notice persistence also failed -- "
                f"{type(persistence_error).__name__}: {persistence_error}"
            )
            raise error from persistence_error
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


__all__ = ["ProgressReporter", "verify_joined_coordination", "with_work_time_coordination"]
