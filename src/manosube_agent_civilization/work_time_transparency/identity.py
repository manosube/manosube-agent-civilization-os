"""Deterministic Work Coordination identities (Issue #22).

Canonical serialization has one owner in this repository -- ``state.canonicalize`` -- read here
exactly as ``change_executor/identity.py`` reads it. Each of the three record kinds this
package owns uses a *narrower* id than a full content address over its own body, for the
identical reason ``change_executor/identity.py``'s own module docstring gives for its mapping-
slot key: the id must be a pure function of exactly the fields that identify *which
coordination, at which chain position* a record is, so a genuinely distinct second record at
the identical position collides at the identical Store ``(kind, id)`` slot and is refused by
the Store's own already-existing same-id-different-body conflict detection -- never a new
mechanism this package has to build itself:

- ``work_time_coordination_open_id`` is a function of ``(project_id, work_unit_ref)`` alone --
  one open record per work unit, ever; a retry with a different estimate for the identical work
  unit collides and is refused, never silently coexists under a second id.
- ``work_time_coordination_update_id`` is a function of ``(open_ref.id, sequence_number)`` --
  one update per sequence position; two callers racing to write sequence number *N* collide at
  the identical slot.
- ``work_time_coordination_terminal_id`` is a function of ``open_ref.id`` alone -- Issue #22's
  own "every work unit ends with exactly one observable outcome" is enforced by construction: a
  second, conflicting terminal notice for the identical coordination is not a new record, it is
  a same-id-different-body write the Store already refuses.

Each kind's own broader content (every other field) is still fully tamper-checked through that
kind's own ``*_semantic_fingerprint`` function below.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

OPEN_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "project_binding_ref",
    "work_unit_ref",
    "adapter_kind",
    "estimated_duration_lower_minutes",
    "estimated_duration_upper_minutes",
    "estimate_confidence",
    "major_steps",
    "next_progress_update_due_minutes",
    "variability_factors",
    "opened_at",
)

UPDATE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "project_binding_ref",
    "open_ref",
    "predecessor_ref",
    "sequence_number",
    "position_kind",
    "current_position",
    "material_result_or_blocker",
    "is_material_reestimate",
    "remaining_duration_unknown",
    "revised_remaining_duration_lower_minutes",
    "revised_remaining_duration_upper_minutes",
    "human_action_required",
    "recorded_at",
)

TERMINAL_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "project_binding_ref",
    "open_ref",
    "predecessor_ref",
    "terminal_outcome",
    "actual_elapsed_minutes",
    "explanation",
    "recorded_at",
)


def _projection(record: Mapping[str, Any], fields: tuple[str, ...], *, kind: str) -> dict[str, Any]:
    missing = [field for field in fields if field not in record]
    if missing:
        raise KeyError(
            f"{kind} carries no readable {', '.join(missing)} -- its own identity cannot be recomputed"
        )
    return {field: record[field] for field in fields}


def work_time_coordination_open_id(project_id: str, work_unit_ref: Mapping[str, str]) -> str:
    """The one deterministic id a Work Coordination Open for *work_unit_ref* ever has -- a pure
    function of *project_id* and *work_unit_ref* alone, deliberately excluding the estimate
    itself, so a genuine retry of the identical open collides at the identical Store slot."""

    payload = {"project_id": project_id, "work_unit_ref": dict(work_unit_ref)}
    return "WTC-OPEN-" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def work_time_coordination_open_semantic_fingerprint(record: Mapping[str, Any]) -> str:
    projection = _projection(record, OPEN_SEMANTIC_FIELDS, kind="work_time_coordination_open")
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def work_time_coordination_update_id(open_id: str, sequence_number: int) -> str:
    """The one deterministic id a Work Coordination Update at *sequence_number* within the
    coordination named by *open_id* ever has."""

    payload = {"open_id": open_id, "sequence_number": sequence_number}
    return "WTC-UPDATE-" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def work_time_coordination_update_semantic_fingerprint(record: Mapping[str, Any]) -> str:
    projection = _projection(record, UPDATE_SEMANTIC_FIELDS, kind="work_time_coordination_update")
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def work_time_coordination_terminal_id(open_id: str) -> str:
    """The one deterministic id the terminal notice for the coordination named by *open_id*
    ever has -- enforcing Issue #22's own "exactly one observable outcome" by construction: a
    second, differently-bodied terminal for the identical *open_id* collides at this identical
    id and is refused by the Store, never silently admitted as a second terminal fact."""

    payload = {"open_id": open_id}
    return "WTC-TERMINAL-" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def work_time_coordination_terminal_semantic_fingerprint(record: Mapping[str, Any]) -> str:
    projection = _projection(
        record, TERMINAL_SEMANTIC_FIELDS, kind="work_time_coordination_terminal"
    )
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


__all__ = [
    "OPEN_SEMANTIC_FIELDS",
    "TERMINAL_SEMANTIC_FIELDS",
    "UPDATE_SEMANTIC_FIELDS",
    "work_time_coordination_open_id",
    "work_time_coordination_open_semantic_fingerprint",
    "work_time_coordination_terminal_id",
    "work_time_coordination_terminal_semantic_fingerprint",
    "work_time_coordination_update_id",
    "work_time_coordination_update_semantic_fingerprint",
]
