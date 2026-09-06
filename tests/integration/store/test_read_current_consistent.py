"""``FileStateStore.read_current_consistent`` (Phase 10 Structural Review Round 2,
P10-R2-F1/F2): the one public, read-only, quiescence-checked current-State surface.

Reuses this package's own existing generic Store fixtures (``tests.integration.store.
test_file_store``'s ``prepared_initial``/``successor``/``store``) rather than restating a
second genesis/transition fixture world -- the identical reuse discipline every other Store
test module in this repository already follows.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.integration.store.test_file_store import prepared_initial, store, successor
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.state.errors import SchemaValidationError
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import STAGES
from manosube_agent_civilization.store.errors import CorruptStoreError, SimulatedCrash


def _current_path(tmp_path: Path, project_id: str = "PRJ-0001") -> Path:
    return tmp_path / "backend" / "projects" / project_id / "state" / "current.json"


def _snapshot(tmp_path: Path, project_id: str = "PRJ-0001") -> dict[str, str]:
    import hashlib

    project_dir = tmp_path / "backend" / "projects" / project_id
    if not project_dir.is_dir():
        return {}
    return {
        str(p.relative_to(project_dir)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(project_dir.rglob("*"))
        if p.is_file()
    }


# --- positive routes ------------------------------------------------------------------ #


def test_present_current_matching_lineage_succeeds(tmp_path: Path) -> None:
    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    after, event = successor(initial)
    s.commit("PRJ-0001", 0, initial["semantic_fingerprint"], after, event)

    assert s.read_current_consistent("PRJ-0001") == after


def test_missing_current_succeeds_and_stays_missing(tmp_path: Path) -> None:
    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    _current_path(tmp_path).unlink()

    result = s.read_current_consistent("PRJ-0001")

    assert result == initial
    assert not _current_path(tmp_path).is_file()


def test_missing_current_writes_nothing(tmp_path: Path) -> None:
    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    _current_path(tmp_path).unlink()
    before = _snapshot(tmp_path)

    s.read_current_consistent("PRJ-0001")

    assert _snapshot(tmp_path) == before


def test_present_current_success_writes_nothing(tmp_path: Path) -> None:
    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    before = _snapshot(tmp_path)

    s.read_current_consistent("PRJ-0001")

    assert _snapshot(tmp_path) == before


# --- present-current corruption matrix (P10-R2-F1) ------------------------------------- #


def test_malformed_json_current_is_rejected(tmp_path: Path) -> None:
    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    _current_path(tmp_path).write_text("not-json", encoding="utf-8")

    with pytest.raises(CorruptStoreError):
        s.read_current_consistent("PRJ-0001")


def test_schema_invalid_current_is_rejected(tmp_path: Path) -> None:
    """A missing required field fails at ``_validate_state``'s own schema-shape check --
    :class:`SchemaValidationError`, the identical pre-existing, unchanged behavior
    ``load_current`` already exhibits for this same case -- before ever reaching this
    method's own new checks."""

    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    body = json.loads(_current_path(tmp_path).read_text(encoding="utf-8"))
    del body["schema_version"]
    _current_path(tmp_path).write_text(json.dumps(body), encoding="utf-8")

    with pytest.raises(SchemaValidationError):
        s.read_current_consistent("PRJ-0001")


def test_fingerprint_mismatch_current_is_rejected(tmp_path: Path) -> None:
    """A schema-valid but wrong ``digest`` -- passes the schema-shape check, then fails
    ``_validate_state``'s own recomputed-fingerprint comparison with :class:`CorruptStoreError`."""

    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    body = json.loads(_current_path(tmp_path).read_text(encoding="utf-8"))
    body["semantic_fingerprint"] = {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64}
    _current_path(tmp_path).write_text(json.dumps(body), encoding="utf-8")

    with pytest.raises(CorruptStoreError):
        s.read_current_consistent("PRJ-0001")


def test_project_id_mismatch_current_is_rejected(tmp_path: Path) -> None:
    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    body = json.loads(_current_path(tmp_path).read_text(encoding="utf-8"))
    body["project_id"] = "PRJ-OTHER-0001"
    _current_path(tmp_path).write_text(json.dumps(body), encoding="utf-8")

    with pytest.raises(CorruptStoreError):
        s.read_current_consistent("PRJ-0001")


def test_current_behind_committed_lineage_is_rejected(tmp_path: Path) -> None:
    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    after, event = successor(initial)
    s.commit("PRJ-0001", 0, initial["semantic_fingerprint"], after, event)
    # current.json now holds `after` (revision 1) -- roll it back to `initial` (revision 0),
    # which the committed lineage has already moved past.
    _current_path(tmp_path).write_text(json.dumps(initial), encoding="utf-8")

    with pytest.raises(CorruptStoreError):
        s.read_current_consistent("PRJ-0001")


def test_current_unrelated_to_lineage_is_rejected(tmp_path: Path) -> None:
    """A different, but independently valid and self-consistent, project's own State body
    written into this project's own current.json -- schema-valid and internally consistent,
    yet unrelated to this project's own committed lineage."""

    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    other_initial = prepared_initial()
    other_initial["project_id"] = "PRJ-0001"  # keep project_id valid to isolate this case
    other_initial["state_metadata"]["producer"] = "a-different-producer-entirely"
    other_initial["semantic_fingerprint"] = fingerprint_project_state(
        other_initial, schema_root=SCHEMA_ROOT
    ).as_dict()
    _current_path(tmp_path).write_text(json.dumps(other_initial), encoding="utf-8")

    with pytest.raises(CorruptStoreError):
        s.read_current_consistent("PRJ-0001")


# --- full crash-stage quiescence matrix (P10-R2-F2) ------------------------------------ #


@pytest.mark.parametrize("stage", STAGES)
def test_every_crash_stage_of_a_later_transaction_is_rejected(stage: str, tmp_path: Path) -> None:
    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    after, event = successor(initial)

    def fault(current: str, _stage: str = stage) -> None:
        if current == _stage:
            raise SimulatedCrash(_stage)

    before = _snapshot(tmp_path)
    with pytest.raises(SimulatedCrash):
        s.commit("PRJ-0001", 0, initial["semantic_fingerprint"], after, event, fault=fault)
    mid = _snapshot(tmp_path)

    with pytest.raises(CorruptStoreError, match="pending"):
        s.read_current_consistent("PRJ-0001")

    # Rejection itself introduced no further mutation, and never completed the pending
    # transaction via recover() -- the journal is exactly as the crash left it.
    assert _snapshot(tmp_path) == mid
    assert (
        tmp_path
        / "backend"
        / "projects"
        / "PRJ-0001"
        / "state"
        / "recovery"
        / event["transaction_id"]
        / "COMMITTED"
    ).is_file() is False
    # Confirm the crash actually left something behind to reject, i.e. this test is not
    # vacuously passing because nothing happened.
    assert mid != before or stage == STAGES[0]


def test_current_one_revision_ahead_with_pending_transaction_is_rejected(tmp_path: Path) -> None:
    """The exact scenario ``load_current`` explicitly tolerates as a recoverable gap --
    current.json one revision ahead of the committed lineage because a crash landed between
    ``AFTER_CURRENT_REPLACE`` and the transaction's own ``COMMITTED`` marker --
    ``read_current_consistent`` must reject instead: Boot requires a quiescent Store, and
    ``load_current``'s own tolerant semantics for this identical case are left completely
    unchanged for its existing callers."""

    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    after, event = successor(initial)

    def fault(current: str) -> None:
        if current == "AFTER_CURRENT_REPLACE":
            raise SimulatedCrash("AFTER_CURRENT_REPLACE")

    with pytest.raises(SimulatedCrash):
        s.commit("PRJ-0001", 0, initial["semantic_fingerprint"], after, event, fault=fault)

    # load_current's own existing, unchanged semantics: tolerates this gap, returns the
    # still-committed (reconstructed) view, never raises.
    assert s.load_current("PRJ-0001") == initial

    # read_current_consistent: rejects the identical Store state instead.
    with pytest.raises(CorruptStoreError):
        s.read_current_consistent("PRJ-0001")


def test_uninitialized_project_is_rejected(tmp_path: Path) -> None:
    s = store(tmp_path)
    with pytest.raises(CorruptStoreError):
        s.read_current_consistent("PRJ-NEVER-INITIALIZED-0001")
