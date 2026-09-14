"""V1 (Issue #22): deterministic Work Coordination identity + engine + schema round-trip proof.

Pure-function proof of :mod:`manosube_agent_civilization.work_time_transparency.identity` and
:mod:`manosube_agent_civilization.work_time_transparency.engine` -- no Store, no Boot, no
adapter. Proves every id function is a pure function of exactly its declared narrow key (never
the estimate/body itself), every semantic-fingerprint function is sensitive to each of its own
declared fields individually, the material-reestimate rule matches Issue #22's own "Estimate
Revision" section exactly, and every record the builders produce validates cleanly against its
own canonical JSON Schema.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from manosube_agent_civilization.work_time_transparency.engine import (
    build_work_time_coordination_open,
    build_work_time_coordination_terminal,
    build_work_time_coordination_update,
    is_heartbeat_overdue,
    is_material_reestimate,
)
from manosube_agent_civilization.work_time_transparency.errors import (
    WorkTimeTransparencyValidationError,
)
from manosube_agent_civilization.work_time_transparency.identity import (
    OPEN_SEMANTIC_FIELDS,
    TERMINAL_SEMANTIC_FIELDS,
    UPDATE_SEMANTIC_FIELDS,
    work_time_coordination_open_id,
    work_time_coordination_open_semantic_fingerprint,
    work_time_coordination_terminal_id,
    work_time_coordination_terminal_semantic_fingerprint,
    work_time_coordination_update_id,
    work_time_coordination_update_semantic_fingerprint,
)

PROJECT_ID = "PROJECT-WTC-UNIT"
PROJECT_BINDING_REF = {"kind": "project_binding", "id": "PROJECT-BINDING-WTC-UNIT"}
WORK_UNIT_REF = {"kind": "change_executor_execution", "id": "WORK-UNIT-WTC-1"}


def _open_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "project_id": PROJECT_ID,
        "project_binding_ref": PROJECT_BINDING_REF,
        "work_unit_ref": WORK_UNIT_REF,
        "adapter_kind": "CHANGE_EXECUTOR",
        "estimated_duration_lower_minutes": 5,
        "estimated_duration_upper_minutes": 15,
        "estimate_confidence": "MEDIUM",
        "major_steps": ["resolve boundary", "execute", "commit receipt"],
        "next_progress_update_due_minutes": 10,
        "variability_factors": "external filesystem latency",
        "opened_at": "2026-09-14T06:00:00Z",
    }
    kwargs.update(overrides)
    return kwargs


def test_work_time_coordination_open_id_is_a_pure_function_of_project_id_and_work_unit_ref() -> (
    None
):
    first = work_time_coordination_open_id(PROJECT_ID, WORK_UNIT_REF)
    second = work_time_coordination_open_id(PROJECT_ID, dict(WORK_UNIT_REF))
    assert first == second
    assert first.startswith("WTC-OPEN-")
    assert (
        work_time_coordination_open_id(
            PROJECT_ID, {"kind": "change_executor_execution", "id": "DIFFERENT"}
        )
        != first
    )
    assert work_time_coordination_open_id("DIFFERENT-PROJECT", WORK_UNIT_REF) != first


def test_build_work_time_coordination_open_is_schema_valid_and_id_does_not_depend_on_the_estimate() -> (
    None
):
    record = build_work_time_coordination_open(**_open_kwargs())
    assert record["work_time_coordination_open_id"] == work_time_coordination_open_id(
        PROJECT_ID, WORK_UNIT_REF
    )
    other_estimate = build_work_time_coordination_open(
        **_open_kwargs(estimated_duration_upper_minutes=999)
    )
    assert (
        other_estimate["work_time_coordination_open_id"] == record["work_time_coordination_open_id"]
    )
    assert (
        other_estimate["work_time_coordination_open_semantic_fingerprint"]
        != (record["work_time_coordination_open_semantic_fingerprint"])
    )


@pytest.mark.parametrize("field", OPEN_SEMANTIC_FIELDS)
def test_open_semantic_fingerprint_is_sensitive_to_each_declared_field(field: str) -> None:
    record = build_work_time_coordination_open(**_open_kwargs())
    mutated = deepcopy(record)
    if isinstance(mutated[field], str):
        mutated[field] = mutated[field] + "-X"
    elif isinstance(mutated[field], bool):
        mutated[field] = not mutated[field]
    elif isinstance(mutated[field], int | float):
        mutated[field] = mutated[field] + 1
    elif isinstance(mutated[field], list):
        mutated[field] = [*mutated[field], "extra-step"]
    elif isinstance(mutated[field], dict):
        mutated[field] = {**mutated[field], "id": mutated[field]["id"] + "-X"}
    else:  # pragma: no cover - every OPEN_SEMANTIC_FIELDS member is one of the above
        raise AssertionError(f"unhandled field type for {field!r}")
    assert work_time_coordination_open_semantic_fingerprint(mutated) != (
        work_time_coordination_open_semantic_fingerprint(record)
    )


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"adapter_kind": "NOT-A-REAL-ADAPTER"}, "adapter_kind"),
        ({"estimate_confidence": "VERY_HIGH"}, "estimate_confidence"),
        (
            {"estimated_duration_lower_minutes": 20, "estimated_duration_upper_minutes": 5},
            "upper_minutes",
        ),
        ({"major_steps": []}, "major_steps"),
    ],
)
def test_build_work_time_coordination_open_refuses_invalid_input(
    kwargs: dict[str, Any], match: str
) -> None:
    with pytest.raises(WorkTimeTransparencyValidationError, match=match):
        build_work_time_coordination_open(**_open_kwargs(**kwargs))


@pytest.mark.parametrize(
    (
        "previous_lower",
        "previous_upper",
        "new_lower",
        "new_upper",
        "new_blocker",
        "expected",
    ),
    [
        (10, 20, 10, 20, False, False),
        (10, 20, 10, 21, False, False),
        (10, 20, 5, 20, False, True),
        (10, 20, 10, 25, False, True),
        (10, 20, 10, 30, False, True),
        (10, 20, 10, 20, True, True),
        (None, None, None, None, False, False),
        (None, None, 10, 20, False, True),
        (10, 20, None, None, False, True),
    ],
)
def test_is_material_reestimate_matches_issue_22s_own_rule(
    previous_lower: int | None,
    previous_upper: int | None,
    new_lower: int | None,
    new_upper: int | None,
    new_blocker: bool,
    expected: bool,
) -> None:
    assert (
        is_material_reestimate(
            previous_remaining_lower_minutes=previous_lower,
            previous_remaining_upper_minutes=previous_upper,
            new_remaining_lower_minutes=new_lower,
            new_remaining_upper_minutes=new_upper,
            new_blocking_dependency=new_blocker,
        )
        is expected
    )


def _open_ref() -> dict[str, str]:
    return {
        "kind": "work_time_coordination_open",
        "id": work_time_coordination_open_id(PROJECT_ID, WORK_UNIT_REF),
    }


def _update_kwargs(**overrides: Any) -> dict[str, Any]:
    open_ref = _open_ref()
    kwargs: dict[str, Any] = {
        "project_id": PROJECT_ID,
        "project_binding_ref": PROJECT_BINDING_REF,
        "open_ref": open_ref,
        "predecessor_ref": open_ref,
        "sequence_number": 1,
        "position_kind": "WORK_RUNNING",
        "current_position": "resolving execution boundary",
        "material_result_or_blocker": "",
        "is_material_reestimate": False,
        "remaining_duration_unknown": False,
        "revised_remaining_duration_lower_minutes": 5,
        "revised_remaining_duration_upper_minutes": 10,
        "human_action_required": False,
        "recorded_at": "2026-09-14T06:10:00Z",
    }
    kwargs.update(overrides)
    return kwargs


def test_work_time_coordination_update_id_is_a_pure_function_of_open_id_and_sequence_number() -> (
    None
):
    open_id = work_time_coordination_open_id(PROJECT_ID, WORK_UNIT_REF)
    first = work_time_coordination_update_id(open_id, 1)
    assert first == work_time_coordination_update_id(open_id, 1)
    assert first != work_time_coordination_update_id(open_id, 2)
    assert first != work_time_coordination_update_id("WTC-OPEN-" + "0" * 64, 1)


def test_build_work_time_coordination_update_is_schema_valid() -> None:
    record = build_work_time_coordination_update(**_update_kwargs())
    assert record["work_time_coordination_update_id"] == work_time_coordination_update_id(
        _open_ref()["id"], 1
    )


@pytest.mark.parametrize("field", UPDATE_SEMANTIC_FIELDS)
def test_update_semantic_fingerprint_is_sensitive_to_each_declared_field(field: str) -> None:
    record = build_work_time_coordination_update(**_update_kwargs())
    mutated = deepcopy(record)
    if mutated[field] is None:
        mutated[field] = 999
    elif isinstance(mutated[field], str):
        mutated[field] = mutated[field] + "-X"
    elif isinstance(mutated[field], bool):
        mutated[field] = not mutated[field]
    elif isinstance(mutated[field], int | float):
        mutated[field] = mutated[field] + 1
    elif isinstance(mutated[field], dict):
        mutated[field] = {**mutated[field], "id": mutated[field]["id"] + "-X"}
    else:  # pragma: no cover
        raise AssertionError(f"unhandled field type for {field!r}")
    assert work_time_coordination_update_semantic_fingerprint(mutated) != (
        work_time_coordination_update_semantic_fingerprint(record)
    )


def test_build_work_time_coordination_update_refuses_unrecognized_position_kind() -> None:
    with pytest.raises(WorkTimeTransparencyValidationError, match="position_kind"):
        build_work_time_coordination_update(**_update_kwargs(position_kind="ON_FIRE"))


def test_build_work_time_coordination_update_refuses_unknown_flag_with_present_bounds() -> None:
    with pytest.raises(WorkTimeTransparencyValidationError, match="remaining_duration_unknown"):
        build_work_time_coordination_update(**_update_kwargs(remaining_duration_unknown=True))


def test_build_work_time_coordination_update_refuses_known_flag_with_missing_bounds() -> None:
    with pytest.raises(WorkTimeTransparencyValidationError, match="remaining_duration_unknown"):
        build_work_time_coordination_update(
            **_update_kwargs(
                remaining_duration_unknown=False,
                revised_remaining_duration_lower_minutes=None,
                revised_remaining_duration_upper_minutes=None,
            )
        )


def test_build_work_time_coordination_update_accepts_unknown_remaining_duration() -> None:
    record = build_work_time_coordination_update(
        **_update_kwargs(
            remaining_duration_unknown=True,
            revised_remaining_duration_lower_minutes=None,
            revised_remaining_duration_upper_minutes=None,
            is_material_reestimate=True,
            position_kind="EXTERNAL_REVIEW_WAIT",
            human_action_required=True,
        )
    )
    assert record["remaining_duration_unknown"] is True
    assert record["revised_remaining_duration_lower_minutes"] is None


def _terminal_kwargs(**overrides: Any) -> dict[str, Any]:
    open_ref = _open_ref()
    kwargs: dict[str, Any] = {
        "project_id": PROJECT_ID,
        "project_binding_ref": PROJECT_BINDING_REF,
        "open_ref": open_ref,
        "predecessor_ref": open_ref,
        "terminal_outcome": "COMPLETED",
        "actual_elapsed_minutes": 12,
        "explanation": "",
        "recorded_at": "2026-09-14T06:12:00Z",
    }
    kwargs.update(overrides)
    return kwargs


def test_work_time_coordination_terminal_id_is_a_pure_function_of_open_id_alone() -> None:
    open_id = work_time_coordination_open_id(PROJECT_ID, WORK_UNIT_REF)
    first = work_time_coordination_terminal_id(open_id)
    assert first == work_time_coordination_terminal_id(open_id)
    assert first != work_time_coordination_terminal_id("WTC-OPEN-" + "0" * 64)


def test_build_work_time_coordination_terminal_is_schema_valid() -> None:
    record = build_work_time_coordination_terminal(**_terminal_kwargs())
    assert record["work_time_coordination_terminal_id"] == work_time_coordination_terminal_id(
        _open_ref()["id"]
    )


@pytest.mark.parametrize("field", TERMINAL_SEMANTIC_FIELDS)
def test_terminal_semantic_fingerprint_is_sensitive_to_each_declared_field(field: str) -> None:
    record = build_work_time_coordination_terminal(**_terminal_kwargs())
    mutated = deepcopy(record)
    if isinstance(mutated[field], str):
        mutated[field] = mutated[field] + "-X"
    elif isinstance(mutated[field], int | float):
        mutated[field] = mutated[field] + 1
    elif isinstance(mutated[field], dict):
        mutated[field] = {**mutated[field], "id": mutated[field]["id"] + "-X"}
    else:  # pragma: no cover
        raise AssertionError(f"unhandled field type for {field!r}")
    assert work_time_coordination_terminal_semantic_fingerprint(mutated) != (
        work_time_coordination_terminal_semantic_fingerprint(record)
    )


def test_build_work_time_coordination_terminal_refuses_unrecognized_outcome() -> None:
    with pytest.raises(WorkTimeTransparencyValidationError, match="terminal_outcome"):
        build_work_time_coordination_terminal(**_terminal_kwargs(terminal_outcome="VIBES_GOOD"))


@pytest.mark.parametrize(
    "outcome",
    [
        "COMPLETED",
        "BLOCKED_HUMAN_ACTION_REQUIRED",
        "FAILED_RETRYABLE",
        "FAILED_TERMINAL",
        "PAUSED_BY_HUMAN",
    ],
)
def test_every_required_terminal_outcome_is_schema_valid(outcome: str) -> None:
    record = build_work_time_coordination_terminal(**_terminal_kwargs(terminal_outcome=outcome))
    assert record["terminal_outcome"] == outcome


def test_is_heartbeat_overdue_detects_but_does_not_raise() -> None:
    assert is_heartbeat_overdue(
        opened_at_minutes=0, next_progress_update_due_minutes=10, now_minutes=15, has_update=False
    )
    assert not is_heartbeat_overdue(
        opened_at_minutes=0, next_progress_update_due_minutes=10, now_minutes=5, has_update=False
    )
    assert not is_heartbeat_overdue(
        opened_at_minutes=0, next_progress_update_due_minutes=10, now_minutes=15, has_update=True
    )
