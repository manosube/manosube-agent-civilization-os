"""Canonical resolve-and-verify boundaries for Work Coordination lineage (Issue #22, Structural
Review Round 1, P84-R1-F2/F5; hardened Structural Review Round 2, P84-R2-F2).

Every public route entrypoint that continues an already-open coordination
(:func:`~manosube_agent_civilization.work_time_transparency.route.record_work_time_progress_
update`, :func:`~manosube_agent_civilization.work_time_transparency.route.record_work_time_
terminal_notice`) resolves the caller-supplied *references* (``open_ref``/``predecessor_ref`` --
bare ``{"kind": ..., "id": ...}`` pairs) from this project's own Store through this module's own
functions -- it never trusts a caller-supplied record *body*. A nonexistent open, a cross-project
Store lookup, a cross-coordination or cross-binding predecessor, a skipped/reordered/forked
sequence position, or a continuation after a terminal notice already exists is refused here, at
one shared boundary, before any record is built or any commit is attempted -- so every refusal
leaves ``state_revision`` unchanged (nothing was ever staged to commit).

**Structural Review Round 2 (P84-R2-F2).** Resolving a record from the Store is not, by itself,
proof that record is genuine: a hand-edited (or otherwise corrupted) Store body resolves exactly
as readily as a genuine one. Every resolver in this module therefore also *verifies* the body it
resolves, before returning it to any caller, through :func:`_verify_open_integrity`,
:func:`_verify_update_integrity`, or :func:`_verify_terminal_integrity`: closed-schema validation
(a malformed body is refused, never silently trusted), recomputing this record kind's own
deterministic id from the body's own content and requiring it to equal the id the record was
resolved *by* (catching a body that does not genuinely hash to the Store slot it occupies),
recomputing this record kind's own semantic fingerprint and requiring it to equal the body's own
embedded fingerprint field (catching any hand-edited semantic field that was not also
re-fingerprinted to match -- the same "post-commit tampering" detection this package's own tests
already exercised, now a genuine resolve-time production guarantee, not only a test-side
recomputation), and congruity of the body's own embedded ``project_id``/``open_ref`` against the
project and coordination this resolve call is actually operating under. No field of a resolved
record is ever consumed by a caller of this module before all of these checks pass.

These functions are deliberately public (not ``route.py``-internal ``_``-prefixed helpers) so a
test can exercise the resolve-and-verify boundary directly, the same way a production caller's
tampered/substituted/replayed reference would actually be refused -- not merely by a test
recomputing a fingerprint itself and asserting inequality.

**Two distinct notions of "the correct predecessor".** A Work Coordination Update's own
predecessor must be whatever record genuinely sits at ``sequence_number - 1`` in this
coordination's own chain (:func:`resolve_predecessor_at_sequence`) -- correct for both a
genuinely new sequence position (where that is necessarily the current live tip) and an exact
replay of an already-committed one (where it is not, since the tip has since moved on, but the
replay's own original predecessor never changes). A Terminal Notice, which never itself extends
the chain, must instead always match the coordination's current live tip
(:func:`resolve_tip`) -- unaffected by this distinction, since nothing after a terminal can ever
move the tip further.
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as _CANONICAL_SCHEMA_BASE,
    validate_record as _validate_record,
)

from .clock import is_monotonic
from .errors import WorkTimeTransparencyLineageError
from .identity import (
    work_time_coordination_open_id,
    work_time_coordination_open_semantic_fingerprint,
    work_time_coordination_terminal_id,
    work_time_coordination_terminal_semantic_fingerprint,
    work_time_coordination_update_id,
    work_time_coordination_update_semantic_fingerprint,
)

_PREDECESSOR_KINDS = ("work_time_coordination_open", "work_time_coordination_update")
_SCHEMA_BASE = _CANONICAL_SCHEMA_BASE + "work_time_transparency/"


def _validate_schema(record: dict[str, Any], schema_name: str, context: str) -> None:
    try:
        _validate_record(record, schema_name, base=_SCHEMA_BASE)
    except DifferenceValidationError as error:
        raise WorkTimeTransparencyLineageError(
            f"resolved {context} is schema-invalid -- refusing to trust it: {error}"
        ) from error


def _verify_open_integrity(record: dict[str, Any], *, project_id: str, expected_id: str) -> None:
    _validate_schema(
        record, "work_time_coordination_open.schema.json", "work_time_coordination_open"
    )
    if record.get("project_id") != project_id:
        raise WorkTimeTransparencyLineageError(
            f"resolved work_time_coordination_open {expected_id!r} carries project_id "
            f"{record.get('project_id')!r}, not the operating project {project_id!r}"
        )
    recomputed_id = work_time_coordination_open_id(record["project_id"], record["work_unit_ref"])
    if recomputed_id != expected_id:
        raise WorkTimeTransparencyLineageError(
            f"resolved work_time_coordination_open body does not recompute to the id it was "
            f"resolved by ({expected_id!r} != {recomputed_id!r}) -- refusing a Store slot whose "
            "own content is not genuinely content-addressed"
        )
    recomputed_fingerprint = work_time_coordination_open_semantic_fingerprint(record)
    if recomputed_fingerprint != record.get("work_time_coordination_open_semantic_fingerprint"):
        raise WorkTimeTransparencyLineageError(
            f"resolved work_time_coordination_open {expected_id!r} no longer matches its own "
            "stored semantic fingerprint -- refusing a tampered body"
        )


def _verify_update_integrity(
    record: dict[str, Any],
    *,
    project_id: str,
    open_id: str,
    expected_id: str,
    expected_sequence_number: int | None = None,
) -> None:
    _validate_schema(
        record, "work_time_coordination_update.schema.json", "work_time_coordination_update"
    )
    if record.get("project_id") != project_id:
        raise WorkTimeTransparencyLineageError(
            f"resolved work_time_coordination_update {expected_id!r} carries project_id "
            f"{record.get('project_id')!r}, not the operating project {project_id!r}"
        )
    open_ref_raw = record.get("open_ref")
    open_ref: dict[str, Any] = open_ref_raw if isinstance(open_ref_raw, dict) else {}
    if open_ref.get("id") != open_id:
        raise WorkTimeTransparencyLineageError(
            f"resolved work_time_coordination_update {expected_id!r} carries open_ref "
            f"{open_ref!r}, not this coordination's own open {open_id!r}"
        )
    sequence_number = record.get("sequence_number")
    if not isinstance(sequence_number, int):
        raise WorkTimeTransparencyLineageError(
            f"resolved work_time_coordination_update {expected_id!r} carries a non-integer "
            f"sequence_number {sequence_number!r}"
        )
    if expected_sequence_number is not None and sequence_number != expected_sequence_number:
        raise WorkTimeTransparencyLineageError(
            f"resolved work_time_coordination_update {expected_id!r} carries sequence_number "
            f"{sequence_number!r}, not the expected {expected_sequence_number!r}"
        )
    recomputed_id = work_time_coordination_update_id(open_id, sequence_number)
    if recomputed_id != expected_id:
        raise WorkTimeTransparencyLineageError(
            f"resolved work_time_coordination_update body does not recompute to the id it was "
            f"resolved by ({expected_id!r} != {recomputed_id!r}) -- refusing a Store slot whose "
            "own content is not genuinely content-addressed"
        )
    recomputed_fingerprint = work_time_coordination_update_semantic_fingerprint(record)
    if recomputed_fingerprint != record.get("work_time_coordination_update_semantic_fingerprint"):
        raise WorkTimeTransparencyLineageError(
            f"resolved work_time_coordination_update {expected_id!r} no longer matches its own "
            "stored semantic fingerprint -- refusing a tampered body"
        )


def _verify_terminal_integrity(
    record: dict[str, Any], *, project_id: str, open_id: str, expected_id: str
) -> None:
    _validate_schema(
        record, "work_time_coordination_terminal.schema.json", "work_time_coordination_terminal"
    )
    if record.get("project_id") != project_id:
        raise WorkTimeTransparencyLineageError(
            f"resolved work_time_coordination_terminal {expected_id!r} carries project_id "
            f"{record.get('project_id')!r}, not the operating project {project_id!r}"
        )
    open_ref_raw = record.get("open_ref")
    open_ref: dict[str, Any] = open_ref_raw if isinstance(open_ref_raw, dict) else {}
    if open_ref.get("id") != open_id:
        raise WorkTimeTransparencyLineageError(
            f"resolved work_time_coordination_terminal {expected_id!r} carries open_ref "
            f"{open_ref!r}, not this coordination's own open {open_id!r}"
        )
    recomputed_id = work_time_coordination_terminal_id(open_id)
    if recomputed_id != expected_id:
        raise WorkTimeTransparencyLineageError(
            f"resolved work_time_coordination_terminal body does not recompute to the id it was "
            f"resolved by ({expected_id!r} != {recomputed_id!r}) -- refusing a Store slot whose "
            "own content is not genuinely content-addressed"
        )
    recomputed_fingerprint = work_time_coordination_terminal_semantic_fingerprint(record)
    if recomputed_fingerprint != record.get("work_time_coordination_terminal_semantic_fingerprint"):
        raise WorkTimeTransparencyLineageError(
            f"resolved work_time_coordination_terminal {expected_id!r} no longer matches its "
            "own stored semantic fingerprint -- refusing a tampered body"
        )


def resolve_open(store: Any, project_id: str, open_ref: Any) -> dict[str, Any]:
    """Resolve *open_ref* to its real, committed, verified ``work_time_coordination_open`` body
    in this project's own Store -- refuses a wrong ``kind``, a nonexistent id, a schema-invalid
    body, an id/fingerprint that does not recompute from the body's own content, and a body
    carrying a foreign ``project_id`` (Structural Review Round 2, P84-R2-F2)."""

    kind = open_ref.get("kind") if hasattr(open_ref, "get") else None
    if kind != "work_time_coordination_open":
        raise WorkTimeTransparencyLineageError(
            f"open_ref must name kind work_time_coordination_open, got {kind!r}"
        )
    record: dict[str, Any] | None = store.resolve_coordination_record(
        project_id, "work_time_coordination_open", open_ref["id"]
    )
    if record is None:
        raise WorkTimeTransparencyLineageError(
            f"no work_time_coordination_open resolves for id {open_ref['id']!r} in project "
            f"{project_id!r} -- terminal-before-open or a fabricated open_ref"
        )
    _verify_open_integrity(record, project_id=project_id, expected_id=open_ref["id"])
    return record


def resolve_terminal_if_exists(store: Any, project_id: str, open_id: str) -> dict[str, Any] | None:
    """The coordination's own terminal record, if one has already been committed -- ``None``
    otherwise, verified exactly as :func:`resolve_open` verifies an open. Used to refuse an
    update-after-terminal before any record is built."""

    terminal_id = work_time_coordination_terminal_id(open_id)
    record: dict[str, Any] | None = store.resolve_coordination_record(
        project_id, "work_time_coordination_terminal", terminal_id
    )
    if record is None:
        return None
    _verify_terminal_integrity(
        record, project_id=project_id, open_id=open_id, expected_id=terminal_id
    )
    return record


def resolve_tip(
    store: Any, project_id: str, open_record: dict[str, Any]
) -> tuple[dict[str, Any], int]:
    """The real, current chain tip for the coordination named by *open_record* (itself already
    resolved and verified by the caller): either the open record itself (sequence ``0``, no
    updates yet) or the update record at the highest contiguous sequence number reachable by
    walking forward from ``1``, each one verified exactly as :func:`resolve_open` verifies an
    open. Used by the Terminal Notice path -- see this module's own docstring for why the Update
    path uses :func:`resolve_predecessor_at_sequence` instead."""

    open_id = open_record["work_time_coordination_open_id"]
    tip_record: dict[str, Any] = open_record
    tip_sequence = 0
    while True:
        candidate_sequence = tip_sequence + 1
        candidate_id = work_time_coordination_update_id(open_id, candidate_sequence)
        candidate: dict[str, Any] | None = store.resolve_coordination_record(
            project_id, "work_time_coordination_update", candidate_id
        )
        if candidate is None:
            return tip_record, tip_sequence
        _verify_update_integrity(
            candidate,
            project_id=project_id,
            open_id=open_id,
            expected_id=candidate_id,
            expected_sequence_number=candidate_sequence,
        )
        tip_record = candidate
        tip_sequence = candidate_sequence


def resolve_predecessor_at_sequence(
    store: Any, project_id: str, open_record: dict[str, Any], sequence_number: int
) -> dict[str, Any]:
    """The one record that must immediately precede *sequence_number* in this coordination's own
    chain: the open record itself (already resolved and verified by the caller) when
    ``sequence_number == 1``, otherwise the update committed at ``sequence_number - 1``, verified
    exactly as :func:`resolve_open` verifies an open. Refuses (skipped sequence) when that prior
    position was never committed. Correct for both a genuinely new sequence position (necessarily
    one past the current live tip) and an exact replay of an already-committed one -- in either
    case, the record genuinely at ``sequence_number - 1`` never changes."""

    if sequence_number == 1:
        return open_record
    open_id = open_record["work_time_coordination_open_id"]
    candidate_id = work_time_coordination_update_id(open_id, sequence_number - 1)
    candidate: dict[str, Any] | None = store.resolve_coordination_record(
        project_id, "work_time_coordination_update", candidate_id
    )
    if candidate is None:
        raise WorkTimeTransparencyLineageError(
            f"sequence_number {sequence_number} has no committed predecessor at sequence "
            f"{sequence_number - 1} -- skipped sequence refused"
        )
    _verify_update_integrity(
        candidate,
        project_id=project_id,
        open_id=open_id,
        expected_id=candidate_id,
        expected_sequence_number=sequence_number - 1,
    )
    return candidate


def _own_ref(record: dict[str, Any]) -> dict[str, str]:
    if "work_time_coordination_open_id" in record:
        return {
            "kind": "work_time_coordination_open",
            "id": record["work_time_coordination_open_id"],
        }
    if "work_time_coordination_update_id" in record:
        return {
            "kind": "work_time_coordination_update",
            "id": record["work_time_coordination_update_id"],
        }
    raise WorkTimeTransparencyLineageError(f"record is neither an open nor an update: {record!r}")


def _own_time(record: dict[str, Any]) -> str:
    value: str = (
        record["opened_at"] if "work_time_coordination_open_id" in record else record["recorded_at"]
    )
    return value


def verify_predecessor_matches(*, predecessor_ref: Any, expected_record: dict[str, Any]) -> None:
    """Refuse a *predecessor_ref* that does not name *expected_record*'s own identity exactly --
    the one check that closes skipped sequence numbers, reordering, forking onto a stale
    predecessor, and a predecessor substituted from a different coordination or project, all at
    once: none of those ever equal the freshly-resolved (and, as of P84-R2-F2, verified) expected
    record's own ``{kind, id}``."""

    kind = predecessor_ref.get("kind") if hasattr(predecessor_ref, "get") else None
    if kind not in _PREDECESSOR_KINDS:
        raise WorkTimeTransparencyLineageError(
            f"predecessor_ref must name work_time_coordination_open or "
            f"work_time_coordination_update, got {kind!r}"
        )
    supplied = {"kind": predecessor_ref["kind"], "id": predecessor_ref["id"]}
    expected = _own_ref(expected_record)
    if supplied != expected:
        raise WorkTimeTransparencyLineageError(
            f"predecessor_ref {supplied!r} does not match the expected predecessor {expected!r} "
            "-- skipped, reordered, forked, or substituted predecessor refused"
        )


def verify_monotonic_continuation(*, expected_record: dict[str, Any], new_recorded_at: str) -> None:
    """Refuse a continuation whose own time is strictly before *expected_record*'s own time (see
    :func:`~manosube_agent_civilization.work_time_transparency.clock.is_monotonic` for why an
    identical instant is accepted, not just a strictly later one)."""

    expected_time = _own_time(expected_record)
    if not is_monotonic(expected_time, new_recorded_at):
        raise WorkTimeTransparencyLineageError(
            f"recorded_at {new_recorded_at!r} is before the expected predecessor's own time "
            f"{expected_time!r} -- non-monotonic continuation refused"
        )


def verify_binding_congruity(*, open_record: dict[str, Any], project_binding_id: str) -> None:
    """Refuse a continuation whose resolved open record was opened under a project binding
    that no longer matches the caller's own freshly-Booted binding -- a project rebind between
    a coordination's own open and one of its later continuations."""

    open_binding_id = open_record["project_binding_ref"]["id"]
    if open_binding_id != project_binding_id:
        raise WorkTimeTransparencyLineageError(
            f"open was recorded under project_binding {open_binding_id!r}, but this call resolves "
            f"to project_binding {project_binding_id!r} -- cross-binding continuation refused"
        )


__all__ = [
    "resolve_open",
    "resolve_predecessor_at_sequence",
    "resolve_terminal_if_exists",
    "resolve_tip",
    "verify_binding_congruity",
    "verify_monotonic_continuation",
    "verify_predecessor_matches",
]
