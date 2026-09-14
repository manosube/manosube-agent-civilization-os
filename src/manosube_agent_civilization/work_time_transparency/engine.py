"""Pure record builders and the deterministic coordination evaluator for the Human Wait-Time
Transparency vertical (Issue #22): ``work_time_coordination_open``, ``work_time_coordination_
update``, and ``work_time_coordination_terminal``.

Every builder here performs no Store I/O, reads no clock, and trusts every input as already
verified by its own caller (:mod:`~manosube_agent_civilization.work_time_transparency.route`) --
the identical discipline ``change_executor/engine.py``'s own module docstring states. Each
builder computes and embeds its own record's id and semantic fingerprint, and schema-validates
the result before returning it.

The material-reestimate detector (:func:`is_material_reestimate`) restates Issue #22's own
"Estimate Revision" section verbatim:

```text
MATERIAL_ESTIMATE_CHANGE=
remaining range changes by >= 5 minutes
OR
upper bound expands by >= 50 percent
OR
a new blocking dependency appears
```
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as _CANONICAL_SCHEMA_BASE,
    validate_record as _validate_record,
)

from .errors import WorkTimeTransparencyValidationError
from .identity import (
    work_time_coordination_open_id,
    work_time_coordination_open_semantic_fingerprint,
    work_time_coordination_terminal_id,
    work_time_coordination_terminal_semantic_fingerprint,
    work_time_coordination_update_id,
    work_time_coordination_update_semantic_fingerprint,
)
from .types import ADAPTER_KINDS, ESTIMATE_CONFIDENCE_LEVELS, POSITION_KINDS, TERMINAL_OUTCOMES

SCHEMA_VERSION = "0.1"
WORK_TIME_TRANSPARENCY_SCHEMA_BASE = _CANONICAL_SCHEMA_BASE + "work_time_transparency/"


def _validate(record: dict[str, Any], schema_name: str, context: str) -> None:
    try:
        _validate_record(record, schema_name, base=WORK_TIME_TRANSPARENCY_SCHEMA_BASE)
    except DifferenceValidationError as error:
        raise WorkTimeTransparencyValidationError(f"{context}: {error}") from error


def build_work_time_coordination_open(
    *,
    project_id: str,
    project_binding_ref: Mapping[str, str],
    work_unit_ref: Mapping[str, str],
    adapter_kind: str,
    estimated_duration_lower_minutes: int,
    estimated_duration_upper_minutes: int,
    estimate_confidence: str,
    major_steps: list[str],
    next_progress_update_due_minutes: int,
    variability_factors: str,
    opened_at: str,
) -> dict[str, Any]:
    """Build one canonical ``work_time_coordination_open`` record -- Issue #22's own "Required
    Start Notice"."""

    if adapter_kind not in ADAPTER_KINDS:
        raise WorkTimeTransparencyValidationError(f"unrecognized adapter_kind: {adapter_kind!r}")
    if estimate_confidence not in ESTIMATE_CONFIDENCE_LEVELS:
        raise WorkTimeTransparencyValidationError(
            f"unrecognized estimate_confidence: {estimate_confidence!r}"
        )
    if estimated_duration_upper_minutes < estimated_duration_lower_minutes:
        raise WorkTimeTransparencyValidationError(
            "estimated_duration_upper_minutes must be >= estimated_duration_lower_minutes"
        )
    if not major_steps:
        raise WorkTimeTransparencyValidationError("major_steps must name at least one step")
    if estimated_duration_upper_minutes > 10 and next_progress_update_due_minutes > 10:
        raise WorkTimeTransparencyValidationError(
            "next_progress_update_due_minutes must be <= 10 when "
            "estimated_duration_upper_minutes > 10 (Issue #22's own opening-deadline rule, "
            "Structural Review Round 1 P84-R1-F3)"
        )

    open_id = work_time_coordination_open_id(project_id, work_unit_ref)
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "work_time_coordination_open_id": open_id,
        "project_id": project_id,
        "project_binding_ref": dict(project_binding_ref),
        "work_unit_ref": dict(work_unit_ref),
        "adapter_kind": adapter_kind,
        "estimated_duration_lower_minutes": estimated_duration_lower_minutes,
        "estimated_duration_upper_minutes": estimated_duration_upper_minutes,
        "estimate_confidence": estimate_confidence,
        "major_steps": list(major_steps),
        "next_progress_update_due_minutes": next_progress_update_due_minutes,
        "variability_factors": variability_factors,
        "opened_at": opened_at,
        "work_time_coordination_open_semantic_fingerprint": "",
    }
    record["work_time_coordination_open_semantic_fingerprint"] = (
        work_time_coordination_open_semantic_fingerprint(record)
    )
    _validate(
        record, "work_time_coordination_open.schema.json", "generated work_time_coordination_open"
    )
    return record


def is_material_reestimate(
    *,
    previous_remaining_lower_minutes: int | None,
    previous_remaining_upper_minutes: int | None,
    new_remaining_lower_minutes: int | None,
    new_remaining_upper_minutes: int | None,
    new_blocking_dependency: bool,
) -> bool:
    """Issue #22's own "Estimate Revision" rule, verbatim: a remaining-range change of >= 5
    minutes (either bound), OR the upper bound expanding by >= 50 percent, OR a new blocking
    dependency appearing. ``None`` bounds mean "unknown remaining duration"; a transition into
    or out of "unknown" is always material (a caller genuinely losing or regaining the ability
    to bound the remaining work is exactly the kind of change this rule exists to surface)."""

    if new_blocking_dependency:
        return True
    unknown_before = (
        previous_remaining_lower_minutes is None or previous_remaining_upper_minutes is None
    )
    unknown_after = new_remaining_lower_minutes is None or new_remaining_upper_minutes is None
    if unknown_before != unknown_after:
        return True
    if unknown_before and unknown_after:
        return False
    if previous_remaining_lower_minutes is None or previous_remaining_upper_minutes is None:
        raise WorkTimeTransparencyValidationError(
            "unreachable: unknown_before already excluded this case"
        )
    if new_remaining_lower_minutes is None or new_remaining_upper_minutes is None:
        raise WorkTimeTransparencyValidationError(
            "unreachable: unknown_after already excluded this case"
        )
    if abs(new_remaining_lower_minutes - previous_remaining_lower_minutes) >= 5:
        return True
    if abs(new_remaining_upper_minutes - previous_remaining_upper_minutes) >= 5:
        return True
    return (
        previous_remaining_upper_minutes > 0
        and new_remaining_upper_minutes >= previous_remaining_upper_minutes * 1.5
    )


def build_work_time_coordination_update(
    *,
    project_id: str,
    project_binding_ref: Mapping[str, str],
    open_ref: Mapping[str, str],
    predecessor_ref: Mapping[str, str],
    sequence_number: int,
    position_kind: str,
    current_position: str,
    material_result_or_blocker: str,
    is_material_reestimate: bool,
    remaining_duration_unknown: bool,
    revised_remaining_duration_lower_minutes: int | None,
    revised_remaining_duration_upper_minutes: int | None,
    human_action_required: bool,
    next_progress_update_due_minutes: int,
    heartbeat_deadline_breached: bool,
    recorded_at: str,
) -> dict[str, Any]:
    """Build one canonical ``work_time_coordination_update`` record -- Issue #22's own "Progress
    Heartbeat" / "Estimate Revision" / "External Wait" sections, unified into one record kind
    discriminated by *position_kind*.

    *is_material_reestimate* and *heartbeat_deadline_breached* are never taken from a raw
    caller-supplied boolean -- :mod:`~manosube_agent_civilization.work_time_transparency.route`
    derives both from the resolved canonical predecessor and the coordination's own declared
    deadlines (:func:`is_material_reestimate`, :func:`~manosube_agent_civilization.
    work_time_transparency.clock.is_monotonic`) before calling this builder (Structural Review
    Round 1, P84-R1-F3). This builder itself stays a pure, Store-free function; it only embeds
    values its caller already derived."""

    if position_kind not in POSITION_KINDS:
        raise WorkTimeTransparencyValidationError(f"unrecognized position_kind: {position_kind!r}")
    if remaining_duration_unknown:
        if (
            revised_remaining_duration_lower_minutes is not None
            or revised_remaining_duration_upper_minutes is not None
        ):
            raise WorkTimeTransparencyValidationError(
                "remaining_duration_unknown=true requires both revised_remaining_duration_*_minutes to be null"
            )
    else:
        if (
            revised_remaining_duration_lower_minutes is None
            or revised_remaining_duration_upper_minutes is None
        ):
            raise WorkTimeTransparencyValidationError(
                "remaining_duration_unknown=false requires both revised_remaining_duration_*_minutes"
            )
        if revised_remaining_duration_upper_minutes < revised_remaining_duration_lower_minutes:
            raise WorkTimeTransparencyValidationError(
                "revised_remaining_duration_upper_minutes must be >= revised_remaining_duration_lower_minutes"
            )

    update_id = work_time_coordination_update_id(open_ref["id"], sequence_number)
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "work_time_coordination_update_id": update_id,
        "project_id": project_id,
        "project_binding_ref": dict(project_binding_ref),
        "open_ref": dict(open_ref),
        "predecessor_ref": dict(predecessor_ref),
        "sequence_number": sequence_number,
        "position_kind": position_kind,
        "current_position": current_position,
        "material_result_or_blocker": material_result_or_blocker,
        "is_material_reestimate": is_material_reestimate,
        "remaining_duration_unknown": remaining_duration_unknown,
        "revised_remaining_duration_lower_minutes": revised_remaining_duration_lower_minutes,
        "revised_remaining_duration_upper_minutes": revised_remaining_duration_upper_minutes,
        "human_action_required": human_action_required,
        "next_progress_update_due_minutes": next_progress_update_due_minutes,
        "heartbeat_deadline_breached": heartbeat_deadline_breached,
        "recorded_at": recorded_at,
        "work_time_coordination_update_semantic_fingerprint": "",
    }
    record["work_time_coordination_update_semantic_fingerprint"] = (
        work_time_coordination_update_semantic_fingerprint(record)
    )
    _validate(
        record,
        "work_time_coordination_update.schema.json",
        "generated work_time_coordination_update",
    )
    return record


def build_work_time_coordination_terminal(
    *,
    project_id: str,
    project_binding_ref: Mapping[str, str],
    open_ref: Mapping[str, str],
    predecessor_ref: Mapping[str, str],
    terminal_outcome: str,
    actual_elapsed_minutes: int,
    heartbeat_deadline_breached: bool,
    explanation: str,
    recorded_at: str,
) -> dict[str, Any]:
    """Build one canonical ``work_time_coordination_terminal`` record -- Issue #22's own
    "Terminal Notice": "Every work unit ends with exactly one observable outcome."

    *heartbeat_deadline_breached* is never a raw caller-supplied boolean -- see
    :func:`build_work_time_coordination_update`'s own docstring for why (Structural Review
    Round 1, P84-R1-F3)."""

    if terminal_outcome not in TERMINAL_OUTCOMES:
        raise WorkTimeTransparencyValidationError(
            f"unrecognized terminal_outcome: {terminal_outcome!r}"
        )

    terminal_id = work_time_coordination_terminal_id(open_ref["id"])
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "work_time_coordination_terminal_id": terminal_id,
        "project_id": project_id,
        "project_binding_ref": dict(project_binding_ref),
        "open_ref": dict(open_ref),
        "predecessor_ref": dict(predecessor_ref),
        "terminal_outcome": terminal_outcome,
        "actual_elapsed_minutes": actual_elapsed_minutes,
        "heartbeat_deadline_breached": heartbeat_deadline_breached,
        "explanation": explanation,
        "recorded_at": recorded_at,
        "work_time_coordination_terminal_semantic_fingerprint": "",
    }
    record["work_time_coordination_terminal_semantic_fingerprint"] = (
        work_time_coordination_terminal_semantic_fingerprint(record)
    )
    _validate(
        record,
        "work_time_coordination_terminal.schema.json",
        "generated work_time_coordination_terminal",
    )
    return record


def is_heartbeat_overdue(
    *,
    opened_at_minutes: int,
    next_progress_update_due_minutes: int,
    now_minutes: int,
    has_update: bool,
) -> bool:
    """A read-side, non-blocking observation: has the coordination's own ``next_progress_update_
    due_minutes`` deadline (measured from ``opened_at``) passed with no update yet recorded?
    Detectable, never enforced -- Issue #22's own doctrine is that silence must never be trusted
    as a health signal, not that silence must block anything this package owns. A caller (the
    natural-route proof, an adapter wrapper) may use this to decide whether to surface a warning;
    :mod:`~manosube_agent_civilization.work_time_transparency.route` itself never refuses a late
    update or a terminal notice on account of it."""

    if has_update:
        return False
    return now_minutes - opened_at_minutes > next_progress_update_due_minutes


__all__ = [
    "SCHEMA_VERSION",
    "WORK_TIME_TRANSPARENCY_SCHEMA_BASE",
    "build_work_time_coordination_open",
    "build_work_time_coordination_terminal",
    "build_work_time_coordination_update",
    "is_heartbeat_overdue",
    "is_material_reestimate",
]
