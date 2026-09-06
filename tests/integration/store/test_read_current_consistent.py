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


# --- P10-R3-F1: a durable lineage event whose own recovery journal has been deleted must
#     never be silently excluded -- a Store is quiescent only once every durable lineage
#     event, not merely every still-existing journal, resolves to committed-transaction
#     evidence ------------------------------------------------------------------------------ #


def test_a_committed_later_transactions_deleted_journal_is_rejected_even_with_a_matching_current(
    tmp_path: Path,
) -> None:
    """The exact P10-R3-F1 scenario: crash right after the lineage event is appended (before
    ``COMMITTED``), then delete that transaction's complete recovery journal directory, and
    leave the prior, still-matching ``current.json`` untouched. Pre-fix, ``_transaction_
    committed`` reads the missing journal path identically to "not yet committed", so
    ``_committed_events`` silently stops before this event and ``read_current_consistent``
    returns the stale prior State without ever raising."""

    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    after, event = successor(initial)

    def fault(current: str) -> None:
        if current == "AFTER_LINEAGE_APPEND":
            raise SimulatedCrash("AFTER_LINEAGE_APPEND")

    with pytest.raises(SimulatedCrash):
        s.commit("PRJ-0001", 0, initial["semantic_fingerprint"], after, event, fault=fault)

    journal = (
        tmp_path
        / "backend"
        / "projects"
        / "PRJ-0001"
        / "state"
        / "recovery"
        / event["transaction_id"]
    )
    assert journal.is_dir()
    import shutil

    shutil.rmtree(journal)
    # current.json is untouched -- the crash landed before it was ever replaced, so it still
    # holds `initial`, byte-for-byte consistent with what a naive reconstruction would return.
    assert json.loads(_current_path(tmp_path).read_text(encoding="utf-8")) == initial

    with pytest.raises(CorruptStoreError, match="recovery-journal evidence"):
        s.read_current_consistent("PRJ-0001")


def test_a_deleted_journal_for_a_fully_committed_later_transaction_is_rejected(
    tmp_path: Path,
) -> None:
    """Sharper than the crash-injection case above: the later transaction actually completed
    (its own ``COMMITTED`` marker was genuinely written), and only afterward is its recovery
    journal destroyed -- e.g. external corruption, not an interrupted commit. The lineage
    event is real and fully committed; only the durable evidence proving so is gone. Must
    still be rejected: a Store is quiescent only once every durable lineage event resolves to
    committed-transaction evidence that Boot -- or any other quiescence-checked reader -- can
    itself still verify."""

    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    after, event = successor(initial)
    s.commit("PRJ-0001", 0, initial["semantic_fingerprint"], after, event)

    journal = (
        tmp_path
        / "backend"
        / "projects"
        / "PRJ-0001"
        / "state"
        / "recovery"
        / event["transaction_id"]
    )
    assert (journal / "COMMITTED").is_file()
    import shutil

    shutil.rmtree(journal)

    with pytest.raises(CorruptStoreError, match="recovery-journal evidence"):
        s.read_current_consistent("PRJ-0001")


def test_deleted_journal_and_deleted_current_view_together_are_still_rejected(
    tmp_path: Path,
) -> None:
    """Removing the materialized ``current.json`` view too leaves nothing to contradict
    except the raw lineage itself -- read_current_consistent must still fail closed rather
    than silently reconstruct and return the last revision it can still fully account for."""

    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    after, event = successor(initial)
    s.commit("PRJ-0001", 0, initial["semantic_fingerprint"], after, event)

    journal = (
        tmp_path
        / "backend"
        / "projects"
        / "PRJ-0001"
        / "state"
        / "recovery"
        / event["transaction_id"]
    )
    import shutil

    shutil.rmtree(journal)
    _current_path(tmp_path).unlink()

    with pytest.raises(CorruptStoreError, match="recovery-journal evidence"):
        s.read_current_consistent("PRJ-0001")


def test_bare_genesis_only_store_is_unaffected_by_the_lineage_event_check(tmp_path: Path) -> None:
    """``TX-GENESIS`` is explicitly excluded from the new check -- its own institution is
    settled exclusively by the existing Genesis Receipt, never by a recovery journal, so a
    genesis-only Store (no recovery directory has ever existed) must still boot."""

    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)

    assert s.read_current_consistent("PRJ-0001") == initial


def test_with_records_genesis_is_unaffected_by_the_lineage_event_check(tmp_path: Path) -> None:
    """A ``WITH_RECORDS`` genesis's own recovery journal persists forever by the same
    contract every other committed transaction's journal does -- unaffected either way, since
    ``TX-GENESIS`` is excluded from this check regardless of its journal's presence."""

    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize(
        "PRJ-0001",
        initial,
        records=[("closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64, {"result": "SATISFIED"})],
    )

    assert s.read_current_consistent("PRJ-0001") == initial


def test_quiescent_store_with_a_real_committed_later_transition_still_boots(
    tmp_path: Path,
) -> None:
    """The positive control this whole matrix exists to keep true: an honestly-operating,
    fully quiescent Store with a real committed later transition -- journal intact, COMMITTED
    marker intact -- must still succeed."""

    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    after, event = successor(initial)
    s.commit("PRJ-0001", 0, initial["semantic_fingerprint"], after, event)

    assert s.read_current_consistent("PRJ-0001") == after


# --- P10-R4-F1: a plain filesystem entry substituted for a deleted recovery journal
#     directory must not be mistaken for journal evidence -- checking mere path *existence*
#     is not enough; the path must be a real directory -------------------------------------- #


def test_a_crash_appended_transactions_journal_directory_replaced_by_a_file_is_rejected(
    tmp_path: Path,
) -> None:
    """The exact P10-R4-F1 scenario: crash right after the lineage event is appended (before
    ``COMMITTED``), delete that transaction's complete recovery journal directory, then write
    a plain regular file at the identical path -- leaving the prior, still-matching
    ``current.json`` untouched. Pre-fix, ``_has_unexplained_lineage_event`` only checked
    ``journal.exists()``, so this file-at-the-same-path read as "explained" and the stale
    prior State was returned without ever raising."""

    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    after, event = successor(initial)

    def fault(current: str) -> None:
        if current == "AFTER_LINEAGE_APPEND":
            raise SimulatedCrash("AFTER_LINEAGE_APPEND")

    with pytest.raises(SimulatedCrash):
        s.commit("PRJ-0001", 0, initial["semantic_fingerprint"], after, event, fault=fault)

    journal = (
        tmp_path
        / "backend"
        / "projects"
        / "PRJ-0001"
        / "state"
        / "recovery"
        / event["transaction_id"]
    )
    assert journal.is_dir()
    import shutil

    shutil.rmtree(journal)
    journal.write_text("not-a-journal-directory", encoding="utf-8")
    assert journal.exists() and not journal.is_dir()
    assert json.loads(_current_path(tmp_path).read_text(encoding="utf-8")) == initial

    with pytest.raises(CorruptStoreError, match="recovery-journal evidence"):
        s.read_current_consistent("PRJ-0001")


def test_a_committed_later_transactions_journal_replaced_by_a_file_and_current_removed_is_rejected(
    tmp_path: Path,
) -> None:
    """A fully committed later transaction whose recovery journal directory is destroyed and
    replaced by a plain file, with the materialized ``current.json`` view also removed --
    nothing is left to contradict except the raw lineage itself, and the substituted file must
    still not be mistaken for journal evidence."""

    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    after, event = successor(initial)
    s.commit("PRJ-0001", 0, initial["semantic_fingerprint"], after, event)

    journal = (
        tmp_path
        / "backend"
        / "projects"
        / "PRJ-0001"
        / "state"
        / "recovery"
        / event["transaction_id"]
    )
    assert (journal / "COMMITTED").is_file()
    import shutil

    shutil.rmtree(journal)
    journal.write_text("not-a-journal-directory", encoding="utf-8")
    _current_path(tmp_path).unlink()

    with pytest.raises(CorruptStoreError, match="recovery-journal evidence"):
        s.read_current_consistent("PRJ-0001")


def test_rejection_from_a_journal_file_substitution_introduces_zero_store_mutation(
    tmp_path: Path,
) -> None:
    """The rejection itself must never write, delete, or replace anything further."""

    s = store(tmp_path)
    initial = prepared_initial()
    s.initialize("PRJ-0001", initial)
    after, event = successor(initial)

    def fault(current: str) -> None:
        if current == "AFTER_LINEAGE_APPEND":
            raise SimulatedCrash("AFTER_LINEAGE_APPEND")

    with pytest.raises(SimulatedCrash):
        s.commit("PRJ-0001", 0, initial["semantic_fingerprint"], after, event, fault=fault)

    journal = (
        tmp_path
        / "backend"
        / "projects"
        / "PRJ-0001"
        / "state"
        / "recovery"
        / event["transaction_id"]
    )
    import shutil

    shutil.rmtree(journal)
    journal.write_text("not-a-journal-directory", encoding="utf-8")
    before = _snapshot(tmp_path)

    with pytest.raises(CorruptStoreError):
        s.read_current_consistent("PRJ-0001")

    assert _snapshot(tmp_path) == before
