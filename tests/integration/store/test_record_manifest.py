"""FileStateStore's atomic immutable-record manifest (Phase 7 correction, F3).

``FileStateStore`` stays the sole persistence owner: this is not a second registry, it is
an extension of the one existing staged-commit sequence to also stage, conflict-check,
promote and recover a set of immutable records (Closure Evaluation, Difference lifecycle
event, admitted Evidence, ...) atomically alongside the ``state_transition`` that
references them. A record is never resolvable unless its transaction actually committed;
a same-ID/different-body record is rejected the same way a same-transaction-id/
different-payload commit already was.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from tests.state_helpers import SCHEMA_ROOT, initial_state

from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import STAGES, FileStateStore
from manosube_agent_civilization.store.errors import (
    CorruptStoreError,
    RecordConflictError,
    SimulatedCrash,
    TransactionConflictError,
)

PROJECT_ID = "PRJ-0001"


def _prepared_initial() -> dict:
    state = initial_state()
    state["semantic_fingerprint"] = fingerprint_project_state(state, schema_root=SCHEMA_ROOT).as_dict()
    return state


def _successor(before: dict, tx: str = "TX-0001") -> tuple[dict, dict]:
    state = deepcopy(before)
    state["state_revision"] = before["state_revision"] + 1
    state["previous_state_fingerprint"] = before["semantic_fingerprint"]
    state["lineage_head_ref"] = {"kind": "state_transition", "id": tx}
    state["semantic_state"]["code"]["status"] = "KNOWN"
    state["semantic_fingerprint"] = fingerprint_project_state(state, schema_root=SCHEMA_ROOT).as_dict()
    event = {
        "schema_version": "0.1", "transaction_id": tx, "event_type": "TRANSITION",
        "project_id": state["project_id"], "from_revision": before["state_revision"],
        "to_revision": state["state_revision"], "before_fingerprint": before["semantic_fingerprint"],
        "after_fingerprint": state["semantic_fingerprint"], "after_state": state,
        "evidence_refs": [], "committed_at": "2026-08-30T10:00:00Z",
    }
    return state, event


def _store(tmp_path: Path) -> FileStateStore:
    return FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)


def test_committed_records_resolve_and_uncommitted_ones_do_not(tmp_path: Path) -> None:
    store = _store(tmp_path)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)
    after, event = _successor(initial)

    record = {"closure_evaluation_id": "D-CLOSE-EVAL-" + "A" * 64, "result": "SATISFIED"}
    store.commit(
        PROJECT_ID, 0, initial["semantic_fingerprint"], after, event,
        records=[("closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64, record)],
    )

    assert store.resolve_record(PROJECT_ID, "closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64) == record
    assert store.resolve_record(PROJECT_ID, "closure_evaluation", "D-CLOSE-EVAL-" + "B" * 64) is None


def test_same_id_different_body_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)
    after, event = _successor(initial)
    store.commit(
        PROJECT_ID, 0, initial["semantic_fingerprint"], after, event,
        records=[("closure_evaluation", "D-CLOSE-EVAL-X", {"result": "SATISFIED"})],
    )

    after2, event2 = _successor(after, "TX-0002")
    with pytest.raises(RecordConflictError):
        store.commit(
            PROJECT_ID, 1, after["semantic_fingerprint"], after2, event2,
            records=[("closure_evaluation", "D-CLOSE-EVAL-X", {"result": "DIFFERENT"})],
        )
    # The rejected commit must not have advanced State or promoted the conflicting body.
    assert store.load_current(PROJECT_ID)["state_revision"] == 1
    assert store.resolve_record(PROJECT_ID, "closure_evaluation", "D-CLOSE-EVAL-X") == {"result": "SATISFIED"}


def test_duplicate_identity_within_one_manifest_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)
    after, event = _successor(initial)

    with pytest.raises(RecordConflictError):
        store.commit(
            PROJECT_ID, 0, initial["semantic_fingerprint"], after, event,
            records=[
                ("difference_lifecycle_event", "D-EVT-1", {"a": 1}),
                ("difference_lifecycle_event", "D-EVT-1", {"a": 2}),
            ],
        )
    assert store.load_current(PROJECT_ID)["state_revision"] == 0


def test_identical_record_replayed_across_transactions_is_not_a_conflict(tmp_path: Path) -> None:
    store = _store(tmp_path)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)
    after, event = _successor(initial)
    shared = {"evidence_id": "EVIDENCE-SHARED", "status": "COMPLETE"}
    store.commit(
        PROJECT_ID, 0, initial["semantic_fingerprint"], after, event,
        records=[("observation_evidence", "EVIDENCE-SHARED", shared)],
    )

    after2, event2 = _successor(after, "TX-0002")
    committed = store.commit(
        PROJECT_ID, 1, after["semantic_fingerprint"], after2, event2,
        records=[("observation_evidence", "EVIDENCE-SHARED", shared)],
    )
    assert committed["state_revision"] == 2
    assert store.resolve_record(PROJECT_ID, "observation_evidence", "EVIDENCE-SHARED") == shared


def test_r2f3b_replaying_a_transaction_with_a_divergent_manifest_conflicts(tmp_path: Path) -> None:
    """R2-F3B: idempotent replay must compare the record manifest, not only the event.

    Before this fix, ``commit()``'s ``prior`` branch compared only the canonical
    ``state_transition`` bytes -- an identical ``transaction_id``/event pair replayed with
    a *different* ``records=`` manifest (a substituted, added, or dropped record) was
    silently accepted as the same idempotent replay, never raising anything.
    """

    store = _store(tmp_path)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)
    after, event = _successor(initial)
    original = {"closure_evaluation_id": "D-CLOSE-EVAL-" + "A" * 64, "result": "SATISFIED"}
    store.commit(
        PROJECT_ID, 0, initial["semantic_fingerprint"], after, event,
        records=[("closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64, original)],
    )

    # Same transaction_id, same event -- but a substituted record body under a *different*
    # identity than the one this transaction actually committed.
    substituted = {"closure_evaluation_id": "D-CLOSE-EVAL-" + "B" * 64, "result": "SATISFIED"}
    with pytest.raises(TransactionConflictError):
        store.commit(
            PROJECT_ID, 0, initial["semantic_fingerprint"], after, event,
            records=[("closure_evaluation", "D-CLOSE-EVAL-" + "B" * 64, substituted)],
        )

    # Same transaction_id, same event -- but the manifest now carries an *additional*
    # record the original transaction never claimed.
    extra = {"evidence_id": "EVIDENCE-EXTRA"}
    with pytest.raises(TransactionConflictError):
        store.commit(
            PROJECT_ID, 0, initial["semantic_fingerprint"], after, event,
            records=[
                ("closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64, original),
                ("observation_evidence", "EVIDENCE-EXTRA", extra),
            ],
        )

    # Same transaction_id, same event -- but the manifest now omits the record the
    # original transaction committed.
    with pytest.raises(TransactionConflictError):
        store.commit(PROJECT_ID, 0, initial["semantic_fingerprint"], after, event, records=[])

    # The exact, unmodified replay is still the one thing that succeeds idempotently.
    replayed = store.commit(
        PROJECT_ID, 0, initial["semantic_fingerprint"], after, event,
        records=[("closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64, original)],
    )
    assert replayed["state_revision"] == 1
    assert store.resolve_record(PROJECT_ID, "closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64) == original


@pytest.mark.parametrize("stage", STAGES)
def test_manifest_crash_recovery_never_leaves_a_dangling_reference(stage: str, tmp_path: Path) -> None:
    store = _store(tmp_path)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)
    after, event = _successor(initial)
    record_kind, record_id = "difference_lifecycle_event", "D-EVT-CRASH"
    record = {"to_status": "CLOSED"}

    def fault(current: str) -> None:
        if current == stage:
            raise SimulatedCrash(stage)

    with pytest.raises(SimulatedCrash):
        store.commit(
            PROJECT_ID, 0, initial["semantic_fingerprint"], after, event,
            records=[(record_kind, record_id, record)], fault=fault,
        )

    recovered = store.recover(PROJECT_ID)
    pre_commit_intent = STAGES[: STAGES.index("AFTER_COMMIT_INTENT")]
    resolved = store.resolve_record(PROJECT_ID, record_kind, record_id)

    if stage in pre_commit_intent:
        # Old-complete: the transaction never committed, so the record it would have
        # named is not canonical -- there is nothing for lineage.identity_refs to
        # dangle toward, because nothing yet references it.
        assert recovered["state_revision"] == 0
        assert resolved is None
    else:
        # New-complete: State advanced and the record it references resolves.
        assert recovered["state_revision"] == 1
        assert resolved == record


@pytest.mark.parametrize("stage", STAGES)
def test_r8f4_a_record_promoted_before_committed_is_invisible_until_recovery(
    stage: str, tmp_path: Path
) -> None:
    """R8-F4: ``resolve_record`` must not return a transaction's records while that
    transaction is not durably ``COMMITTED`` -- even once its file already physically
    exists on disk. ``commit``'s own sequence writes a staged record's permanent file
    (``AFTER_RECORDS_PROMOTED``) *before* it replaces ``current.json``
    (``AFTER_CURRENT_REPLACE``) and writes the transaction's own ``COMMITTED`` marker
    (after ``BEFORE_COMMITTED_MARKER``) -- so a crash anywhere in that window once left the
    record's file already resolvable through ``resolve_record`` while ``resolve_transaction``
    (R7-F5) still correctly reported no such transaction: a real split between the two
    methods' own visibility, not simulated. This checks the record is invisible at exactly
    that crash point, immediately -- before :meth:`recover` ever runs -- and only becomes
    visible, alongside its transaction, once :meth:`recover` actually completes it."""

    store = _store(tmp_path)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)
    after, event = _successor(initial)
    record_kind, record_id = "closure_evaluation", "D-CLOSE-EVAL-" + "C" * 64
    record = {"closure_evaluation_id": record_id, "result": "BLOCKED"}

    def fault(current: str) -> None:
        if current == stage:
            raise SimulatedCrash(stage)

    with pytest.raises(SimulatedCrash):
        store.commit(
            PROJECT_ID, 0, initial["semantic_fingerprint"], after, event,
            records=[(record_kind, record_id, record)], fault=fault,
        )

    # Immediately after the crash, before recover() ever runs: every fault point this
    # module's own STAGES names fires strictly before the transaction's COMMITTED marker
    # is ever written, so the state_transition and the record it references must both stay
    # invisible -- regardless of whether the record's own file already physically exists
    # on disk (AFTER_RECORDS_PROMOTED onward).
    resolved_before_recovery = store.resolve_record(PROJECT_ID, record_kind, record_id)
    transaction_before_recovery = store.resolve_transaction(PROJECT_ID, event["transaction_id"])
    assert resolved_before_recovery is None
    assert transaction_before_recovery is None

    recovered = store.recover(PROJECT_ID)
    resolved_after_recovery = store.resolve_record(PROJECT_ID, record_kind, record_id)
    transaction_after_recovery = store.resolve_transaction(PROJECT_ID, event["transaction_id"])
    pre_commit_intent = STAGES[: STAGES.index("AFTER_COMMIT_INTENT")]
    if stage in pre_commit_intent:
        assert recovered["state_revision"] == 0
        assert resolved_after_recovery is None
        assert transaction_after_recovery is None
    else:
        assert recovered["state_revision"] == 1
        assert resolved_after_recovery == record
        assert transaction_after_recovery is not None
        assert transaction_after_recovery["transaction_id"] == event["transaction_id"]


@pytest.mark.parametrize("stage", STAGES)
def test_r9f4_all_four_public_read_surfaces_converge_atomically(stage: str, tmp_path: Path) -> None:
    """R9-F4: ``load_current``, ``reconstruct``, ``resolve_transaction`` and
    ``resolve_record`` must agree at every point -- not only the two R7-F5/R8-F4 already
    gated. Before this fix, ``reconstruct`` (and therefore ``load_current``) read the raw,
    unfiltered lineage log directly: a crash at ``AFTER_LINEAGE_APPEND`` or later left the
    advanced revision *already visible* through ``load_current``/``reconstruct`` while
    ``resolve_transaction``/``resolve_record`` still correctly reported nothing for that
    same transaction -- a real split across the four surfaces, not simulated. A crash
    between ``AFTER_CURRENT_REPLACE`` and the transaction's own ``COMMITTED`` marker also
    once made ``load_current`` raise ``CorruptStoreError`` outright (``current.json``
    already advanced, the lineage view still not), rather than gracefully reporting the
    old, complete view a recoverable incomplete transaction must never corrupt.

    Verified for all 9 crash stages, with a non-empty record manifest: immediately after
    the crash (before :meth:`recover` ever runs) all four surfaces agree on the *old*,
    complete view, with no exception raised; after :meth:`recover` completes, all four
    converge together either to the *new* view (stage at or after
    ``AFTER_COMMIT_INTENT``) or stay together at the *old* view (an earlier stage, where
    the transaction never truly began committing)."""

    store = _store(tmp_path)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)
    after, event = _successor(initial)
    record_kind, record_id = "closure_evaluation", "D-CLOSE-EVAL-" + "D" * 64
    record = {"closure_evaluation_id": record_id, "result": "BLOCKED"}

    def fault(current: str) -> None:
        if current == stage:
            raise SimulatedCrash(stage)

    with pytest.raises(SimulatedCrash):
        store.commit(
            PROJECT_ID, 0, initial["semantic_fingerprint"], after, event,
            records=[(record_kind, record_id, record)], fault=fault,
        )

    # Before recover(): every surface must agree on the old, complete view -- and none
    # may raise, even though current.json may already have been advanced on disk.
    current_before = store.load_current(PROJECT_ID)
    reconstructed_before = store.reconstruct(PROJECT_ID)
    transaction_before = store.resolve_transaction(PROJECT_ID, event["transaction_id"])
    resolved_before = store.resolve_record(PROJECT_ID, record_kind, record_id)
    assert current_before["state_revision"] == 0
    assert reconstructed_before["state_revision"] == 0
    assert current_before == reconstructed_before
    assert transaction_before is None
    assert resolved_before is None

    recovered = store.recover(PROJECT_ID)
    current_after = store.load_current(PROJECT_ID)
    reconstructed_after = store.reconstruct(PROJECT_ID)
    transaction_after = store.resolve_transaction(PROJECT_ID, event["transaction_id"])
    resolved_after = store.resolve_record(PROJECT_ID, record_kind, record_id)

    pre_commit_intent = STAGES[: STAGES.index("AFTER_COMMIT_INTENT")]
    if stage in pre_commit_intent:
        assert recovered["state_revision"] == 0
        assert current_after["state_revision"] == 0
        assert reconstructed_after["state_revision"] == 0
        assert transaction_after is None
        assert resolved_after is None
    else:
        assert recovered["state_revision"] == 1
        assert current_after["state_revision"] == 1
        assert reconstructed_after["state_revision"] == 1
        assert current_after == reconstructed_after
        assert transaction_after is not None
        assert transaction_after["transaction_id"] == event["transaction_id"]
        assert resolved_after == record


# --- P9-R3-F2: TX-GENESIS transaction_id string is not, by itself, commit evidence ---------- #


def test_never_initialized_project_reports_unresolvable_not_committed_bare_genesis(
    tmp_path: Path,
) -> None:
    """A project for which ``initialize`` was never called at all has no recovery journal --
    the identical absent-journal shape a genuinely committed bare genesis has. Before P9-R3-F2
    the transaction_id string ``TX-GENESIS`` alone was taken as commit evidence, so this
    never-initialized project was indistinguishable from one whose bare genesis legitimately
    committed with zero records. Both public read surfaces must now agree it is unresolvable."""

    store = _store(tmp_path)
    assert store.resolve_transaction(PROJECT_ID, "TX-GENESIS") is None
    assert store.resolve_transaction_manifest(PROJECT_ID, "TX-GENESIS") is None


def test_bare_project_directory_with_no_lineage_reports_unresolvable(tmp_path: Path) -> None:
    """A project directory that exists (e.g. created by an unrelated failed attempt) but
    carries no lineage log and no recovery journal is still never-initialized -- the mere
    existence of the directory is not commit evidence either."""

    store = _store(tmp_path)
    (store.root / "projects" / PROJECT_ID).mkdir(parents=True)
    assert store.resolve_transaction(PROJECT_ID, "TX-GENESIS") is None
    assert store.resolve_transaction_manifest(PROJECT_ID, "TX-GENESIS") is None


def test_bare_genesis_manifest_is_empty_list_not_none(tmp_path: Path) -> None:
    """A real, committed bare genesis (``initialize`` called with no ``records``) has real
    evidence in the lineage log -- ``resolve_transaction`` resolves the real event and
    ``resolve_transaction_manifest`` reports ``[]`` (committed, adopted nothing), never
    ``None`` (unresolvable) -- the positive control distinguishing it from the never-
    initialized case above."""

    store = _store(tmp_path)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)

    transaction = store.resolve_transaction(PROJECT_ID, "TX-GENESIS")
    assert transaction is not None
    assert transaction["transaction_id"] == "TX-GENESIS"
    assert store.resolve_transaction_manifest(PROJECT_ID, "TX-GENESIS") == []

    # Fresh Store instance / fresh process (same on-disk backend) agrees.
    fresh = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    assert fresh.resolve_transaction(PROJECT_ID, "TX-GENESIS") is not None
    assert fresh.resolve_transaction_manifest(PROJECT_ID, "TX-GENESIS") == []


def test_genesis_with_records_manifest_is_the_exact_member_list(tmp_path: Path) -> None:
    """A real, committed genesis-with-records adoption reports the exact ``(kind, id)``
    membership both public read surfaces agree on."""

    store = _store(tmp_path)
    initial = _prepared_initial()
    record = {"closure_evaluation_id": "D-CLOSE-EVAL-" + "A" * 64, "result": "SATISFIED"}
    store.initialize(
        PROJECT_ID, initial, records=[("closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64, record)]
    )

    assert store.resolve_transaction(PROJECT_ID, "TX-GENESIS") is not None
    assert store.resolve_transaction_manifest(PROJECT_ID, "TX-GENESIS") == [
        ("closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64)
    ]

    fresh = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    assert fresh.resolve_transaction_manifest(PROJECT_ID, "TX-GENESIS") == [
        ("closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64)
    ]


@pytest.mark.parametrize("stage", STAGES)
def test_genesis_with_records_crash_stages_joint_visibility(stage: str, tmp_path: Path) -> None:
    """``resolve_transaction`` and ``resolve_transaction_manifest`` must agree at every crash
    stage of a genesis-with-records adoption -- both report the real transaction/manifest
    once ``COMMITTED`` is durable, and neither reports one before that, matching the existing
    ``AFTER_COMMIT_INTENT`` recovery-outcome boundary this vertical already establishes."""

    store = _store(tmp_path)
    initial = _prepared_initial()
    record_kind, record_id, record = "closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64, {
        "closure_evaluation_id": "D-CLOSE-EVAL-" + "A" * 64,
        "result": "SATISFIED",
    }

    def fault(hit_stage: str) -> None:
        if hit_stage == stage:
            raise SimulatedCrash(stage)

    with pytest.raises(SimulatedCrash):
        store.initialize(PROJECT_ID, initial, records=[(record_kind, record_id, record)], fault=fault)

    transaction_before = store.resolve_transaction(PROJECT_ID, "TX-GENESIS")
    manifest_before = store.resolve_transaction_manifest(PROJECT_ID, "TX-GENESIS")
    assert (transaction_before is None) == (manifest_before is None)

    pre_commit_intent = STAGES[: STAGES.index("AFTER_COMMIT_INTENT")]
    if stage in pre_commit_intent:
        # A crash on genesis itself, before its own COMMIT_INTENT was durably written,
        # leaves no completed transaction at all for this project -- recover() correctly
        # refuses to recover something that never started committing (StateNotFoundError,
        # the same "nothing has ever committed" boundary this method already documents).
        from manosube_agent_civilization.store.errors import StateNotFoundError

        with pytest.raises(StateNotFoundError):
            store.recover(PROJECT_ID)
        transaction_after = store.resolve_transaction(PROJECT_ID, "TX-GENESIS")
        manifest_after = store.resolve_transaction_manifest(PROJECT_ID, "TX-GENESIS")
        assert transaction_after is None
        assert manifest_after is None
    else:
        store.recover(PROJECT_ID)
        transaction_after = store.resolve_transaction(PROJECT_ID, "TX-GENESIS")
        manifest_after = store.resolve_transaction_manifest(PROJECT_ID, "TX-GENESIS")
        assert transaction_after is not None
        assert manifest_after == [(record_kind, record_id)]


def test_committed_genesis_manifest_with_a_tampered_duplicate_member_fails_closed(
    tmp_path: Path,
) -> None:
    """A committed genesis-with-records manifest.json tampered to name the same (kind, id)
    twice is corruption, not a legitimate duplicate -- P9-R3-F1's third boundary (the
    committed-manifest read itself, not merely the pre-commit candidate)."""

    store = _store(tmp_path)
    initial = _prepared_initial()
    record = {"closure_evaluation_id": "D-CLOSE-EVAL-" + "A" * 64, "result": "SATISFIED"}
    store.initialize(
        PROJECT_ID, initial, records=[("closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64, record)]
    )

    manifest_path = store.root / "projects" / PROJECT_ID / "state" / "recovery" / "TX-GENESIS" / "manifest.json"
    entry = ["closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64]
    manifest_path.write_text(json.dumps([entry, entry]), encoding="utf-8")

    with pytest.raises(CorruptStoreError, match="more than once"):
        store.resolve_transaction_manifest(PROJECT_ID, "TX-GENESIS")


def test_committed_genesis_manifest_missing_file_reports_empty_not_none(tmp_path: Path) -> None:
    """A committed genesis-with-records transaction whose ``manifest.json`` file is itself
    absent (e.g. removed after commit) is treated identically to a committed transaction that
    adopted no records -- the existing, unchanged convention for a missing (as opposed to
    malformed) manifest file, distinct from the never-initialized case above which has no
    recovery journal *directory* at all."""

    store = _store(tmp_path)
    initial = _prepared_initial()
    record = {"closure_evaluation_id": "D-CLOSE-EVAL-" + "A" * 64, "result": "SATISFIED"}
    store.initialize(
        PROJECT_ID, initial, records=[("closure_evaluation", "D-CLOSE-EVAL-" + "A" * 64, record)]
    )

    manifest_path = store.root / "projects" / PROJECT_ID / "state" / "recovery" / "TX-GENESIS" / "manifest.json"
    manifest_path.unlink()

    assert store.resolve_transaction(PROJECT_ID, "TX-GENESIS") is not None
    assert store.resolve_transaction_manifest(PROJECT_ID, "TX-GENESIS") == []
