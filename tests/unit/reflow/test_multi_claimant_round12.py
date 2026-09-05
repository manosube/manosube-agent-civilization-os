"""R12-F1 (Phase 7 Final Closure Round): exhaustive multi-claimant Record visibility.

Reproduces, directly against the real on-disk journal/manifest layout
``FileStateStore`` itself writes, exactly the scenario SHUKOU's own adoption named: more
than one transaction's recovery journal can legitimately (or, for an abandoned journal,
illegitimately) claim the same ``(kind, record_id)`` key in its own ``manifest.json``.
``_record_committed_by_any_transaction`` must examine *every* such claimant, never settle
for the first one a directory listing happens to produce, and must fail closed -- never
silently pick a convenient body -- on any real divergence.

Items 10-12 of SHUKOU's own required-test list (recovery-before/after convergence,
identical-replay idempotence, manifest-membership-conflict preservation) are already
covered, unchanged and still passing, by ``test_r10f1_genesis_with_records_is_invisible_
before_recovery_and_converges_after`` (``test_structural_review_correction.py``),
``test_replaying_the_same_transaction_is_idempotent`` (``test_atomic_commit.py``), and
``test_identical_record_replayed_across_transactions_is_not_a_conflict``/
``test_r2f3b_replaying_a_transaction_with_a_divergent_manifest_conflicts``
(``test_record_manifest.py``) -- none of those needed to change for this fix, so they are
not duplicated here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.state_helpers import SCHEMA_ROOT, real_kernel_source_snapshot

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.store.errors import CorruptStoreError

PROJECT_ID = "PRJ-0001"
KIND = "source_snapshot"


def _claim(
    recovery: Path,
    name: str,
    *,
    record_id: str,
    committed: bool,
    staged_body: dict | None = None,
) -> None:
    """Write one real manifest-claimant journal directly, the same shape ``commit()``/
    ``initialize()`` themselves produce -- never through a second, parallel construction
    path."""

    journal = recovery / name
    journal.mkdir(parents=True)
    (journal / "manifest.json").write_bytes(canonical_json_bytes([[KIND, record_id]]))
    if staged_body is not None:
        records_dir = journal / "records"
        records_dir.mkdir()
        (records_dir / f"{KIND}__{record_id}.json").write_bytes(canonical_json_bytes(staged_body))
    if committed:
        (journal / "COMMITTED").write_bytes(b"1")


def _store(tmp_path: Path) -> tuple[FileStateStore, Path]:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    recovery = tmp_path / "backend" / "projects" / PROJECT_ID / "state" / "recovery"
    recovery.mkdir(parents=True)
    return store, recovery


def _write_permanent(tmp_path: Path, record_id: str, body: dict) -> None:
    record_dir = tmp_path / "backend" / "projects" / PROJECT_ID / "records" / KIND
    record_dir.mkdir(parents=True, exist_ok=True)
    (record_dir / f"{record_id}.json").write_bytes(canonical_json_bytes(body))


# --- 1/2/3: claimant order (and its permutation) must never change the result -------------- #


@pytest.mark.parametrize(
    "uncommitted_name,committed_name",
    [("AAA-uncommitted", "ZZZ-committed"), ("ZZZ-uncommitted", "AAA-committed")],
)
def test_r12f1_visible_regardless_of_which_claimant_sorts_first(
    uncommitted_name: str, committed_name: str, tmp_path: Path
) -> None:
    """1/2/3: an uncommitted claimant and a real COMMITTED claimant for the same key --
    whichever one a directory listing would produce first, the record is visible, because
    a real committed claimant exists. ``CLAIMANT_ORDER_PERMUTATION_INVARIANT=true``."""

    store, recovery = _store(tmp_path)
    snapshot = real_kernel_source_snapshot()
    record_id = snapshot["source_snapshot_id"]
    _write_permanent(tmp_path, record_id, snapshot)
    _claim(recovery, uncommitted_name, record_id=record_id, committed=False)
    _claim(recovery, committed_name, record_id=record_id, committed=True)

    resolved = store.resolve_record(PROJECT_ID, KIND, record_id)
    assert resolved == snapshot


# --- 4: every claimant uncommitted -> invisible --------------------------------------------- #


def test_r12f1_all_claimants_uncommitted_is_invisible(tmp_path: Path) -> None:
    store, recovery = _store(tmp_path)
    snapshot = real_kernel_source_snapshot()
    record_id = snapshot["source_snapshot_id"]
    _write_permanent(tmp_path, record_id, snapshot)
    _claim(recovery, "AAA", record_id=record_id, committed=False)
    _claim(recovery, "BBB", record_id=record_id, committed=False)

    assert store.resolve_record(PROJECT_ID, KIND, record_id) is None


# --- 5: zero claimants -> invisible, even with a permanent file on disk --------------------- #


def test_r12f1_zero_claimants_is_invisible_even_with_a_permanent_file_present(tmp_path: Path) -> None:
    store, _recovery = _store(tmp_path)
    snapshot = real_kernel_source_snapshot()
    record_id = snapshot["source_snapshot_id"]
    _write_permanent(tmp_path, record_id, snapshot)

    assert store.resolve_record(PROJECT_ID, KIND, record_id) is None


# --- 6: multiple COMMITTED claimants, identical body -> visible ---------------------------- #


def test_r12f1_multiple_committed_claimants_with_the_identical_body_are_visible(tmp_path: Path) -> None:
    store, recovery = _store(tmp_path)
    snapshot = real_kernel_source_snapshot()
    record_id = snapshot["source_snapshot_id"]
    _write_permanent(tmp_path, record_id, snapshot)
    _claim(recovery, "AAA", record_id=record_id, committed=True, staged_body=snapshot)
    _claim(recovery, "BBB", record_id=record_id, committed=True)

    assert store.resolve_record(PROJECT_ID, KIND, record_id) == snapshot


# --- 7: an uncommitted claimant's own staged body differs from the committed body ----------- #


def test_r12f1_an_uncommitted_claimants_staged_body_diverging_from_committed_fails_closed(
    tmp_path: Path,
) -> None:
    store, recovery = _store(tmp_path)
    snapshot = real_kernel_source_snapshot()
    record_id = snapshot["source_snapshot_id"]
    tampered = dict(snapshot, captured_at="2099-01-01T00:00:00Z")
    _write_permanent(tmp_path, record_id, snapshot)
    _claim(recovery, "AAA-uncommitted-tampered", record_id=record_id, committed=False, staged_body=tampered)
    _claim(recovery, "ZZZ-committed-real", record_id=record_id, committed=True)

    with pytest.raises(CorruptStoreError, match="diverges across manifest claimants"):
        store.resolve_record(PROJECT_ID, KIND, record_id)


# --- 8: two COMMITTED claimants, same id, different body ----------------------------------- #


def test_r12f1_two_committed_claimants_with_different_bodies_fail_closed(tmp_path: Path) -> None:
    store, recovery = _store(tmp_path)
    snapshot = real_kernel_source_snapshot()
    record_id = snapshot["source_snapshot_id"]
    tampered = dict(snapshot, captured_at="2099-01-01T00:00:00Z")
    _write_permanent(tmp_path, record_id, snapshot)
    _claim(recovery, "AAA-committed-tampered", record_id=record_id, committed=True, staged_body=tampered)
    _claim(recovery, "ZZZ-committed-real", record_id=record_id, committed=True, staged_body=snapshot)

    with pytest.raises(CorruptStoreError, match="diverges across manifest claimants"):
        store.resolve_record(PROJECT_ID, KIND, record_id)


# --- 9: the permanent record body itself differs from a committed claimant's own body ------- #


def test_r12f1_permanent_body_diverging_from_a_committed_claimants_body_fails_closed(
    tmp_path: Path,
) -> None:
    store, recovery = _store(tmp_path)
    snapshot = real_kernel_source_snapshot()
    record_id = snapshot["source_snapshot_id"]
    tampered = dict(snapshot, captured_at="2099-01-01T00:00:00Z")
    _write_permanent(tmp_path, record_id, snapshot)
    _claim(recovery, "AAA-committed-tampered", record_id=record_id, committed=True, staged_body=tampered)

    with pytest.raises(CorruptStoreError, match="diverges across manifest claimants"):
        store.resolve_record(PROJECT_ID, KIND, record_id)


# --- positive control: none of the above narrows a real, single-claimant genesis ----------- #


def test_r12f1_a_real_single_claimant_genesis_record_still_resolves(tmp_path: Path) -> None:
    from tests.difference_helpers import objective_revision as _objective_revision
    from tests.state_helpers import genesis_source_snapshot_records, initial_state

    from manosube_agent_civilization.state.fingerprint import fingerprint_project_state

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = initial_state()
    project_state["objective_revision_id"] = _objective_revision()["objective_revision_id"]
    project_state["semantic_fingerprint"] = fingerprint_project_state(
        project_state, schema_root=SCHEMA_ROOT
    ).as_dict()
    records = genesis_source_snapshot_records(project_state)
    assert records
    store.initialize(project_state["project_id"], project_state, records=records)

    kind, record_id, body = records[0]
    assert store.resolve_record(project_state["project_id"], kind, record_id) == body
