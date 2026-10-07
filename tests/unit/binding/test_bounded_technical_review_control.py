"""Decision 0004 (Issue #109): the operational claim/budget ledger and activation gate
:mod:`manosube_agent_civilization.development_binding.review_control` owns.

Every numeric-limits rule the handoff names (comment 6017544351, §4) is exercised against
the real, file-based, lock-protected ledger this module persists -- never a mock of it: one
launch per identity forever (including a failed or unacknowledged one); one concurrent review
per repository; a JST-day launch ceiling with real rollover; and restart-safety, proven by
discarding the in-process ledger handle entirely and reopening the identical file.
"""

from __future__ import annotations

from pathlib import Path
import threading
from typing import Any

import pytest

from manosube_agent_civilization.development_binding.errors import ReviewControlError
from manosube_agent_civilization.development_binding.policy import BOUNDED_REVIEW_NUMERIC_LIMITS
from manosube_agent_civilization.development_binding.review_control import (
    RESOLUTION_KIND_COLLECTED_RESULT,
    RESOLUTION_KIND_CONFIRMED_CANCELLATION,
    REVIEW_CLAIM_ADMITTED,
    REVIEW_CLAIM_REFUSED,
    STATUS_ACK_UNKNOWN,
    STATUS_CLAIMED,
    STATUS_COMPLETED,
    STATUS_DISPATCHED,
    STATUS_FAILED,
    claim_review_launch,
    compute_identity_key,
    confirm_dispatch_sent,
    jst_date_for,
    read_claim,
    record_dispatch_attempt,
    record_review_outcome,
    release_unsent_claim,
)

_REPO = "manosube/manosube-agent-civilization-os"
_NOW = "2026-10-06T12:00:00Z"


def _identity(**overrides: Any) -> str:
    base: dict[str, Any] = {
        "repository": _REPO,
        "pull_request": "#200",
        "base_sha": "a" * 40,
        "head_sha": "b" * 40,
        "requirement_id": "REQ-CONTROL-UNIT-1",
        "input_digest": "c" * 64,
    }
    base.update(overrides)
    return compute_identity_key(**base)


def _claim(
    ledger_path: Path, identity_key: str, *, now: str = _NOW, work_unit_id: str = "WU-1"
) -> dict[str, Any]:
    return claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id=work_unit_id,
        repository=_REPO,
        now=now,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )


# --------------------------------------------------------------------------- #
# compute_identity_key / jst_date_for -- deterministic, pure helpers
# --------------------------------------------------------------------------- #


def test_identity_key_is_deterministic_and_content_addressed() -> None:
    key_a = _identity()
    key_b = _identity()
    assert key_a == key_b
    assert key_a != _identity(pull_request="#201")
    assert key_a != _identity(requirement_id="REQ-DIFFERENT")


@pytest.mark.parametrize(
    "utc_timestamp,expected_jst_date",
    [
        ("2026-10-06T00:00:00Z", "2026-10-06"),
        ("2026-10-06T14:59:59Z", "2026-10-06"),
        # 15:00 UTC is already 00:00 JST the next calendar day (UTC+9) -- the exact rollover
        # boundary a day-ceiling test must respect.
        ("2026-10-06T15:00:00Z", "2026-10-07"),
        ("2026-10-06T23:59:59Z", "2026-10-07"),
    ],
)
def test_jst_date_rolls_over_at_the_real_utc_plus_nine_boundary(
    utc_timestamp: str, expected_jst_date: str
) -> None:
    assert jst_date_for(utc_timestamp) == expected_jst_date


def test_jst_date_for_an_unparseable_timestamp_raises() -> None:
    with pytest.raises(ReviewControlError):
        jst_date_for("not-a-timestamp")


# --------------------------------------------------------------------------- #
# one launch per identity, forever -- including a failed or unacknowledged one
# --------------------------------------------------------------------------- #


def test_a_fresh_identity_is_admitted(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    decision = _claim(ledger, _identity())
    assert decision == {
        "decision": REVIEW_CLAIM_ADMITTED,
        "reason_codes": [],
        "identity_key": _identity(),
    }


def test_the_identical_identity_is_never_admitted_twice(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    key = _identity()
    first = _claim(ledger, key)
    assert first["decision"] == REVIEW_CLAIM_ADMITTED
    second = _claim(ledger, key)
    assert second["decision"] == REVIEW_CLAIM_REFUSED
    assert "DUPLICATE_LAUNCH_FOR_IDENTITY" in second["reason_codes"]


def test_a_failed_outcome_still_blocks_every_future_attempt_at_the_identical_identity(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "ledger.json"
    key = _identity()
    _claim(ledger, key)
    record_dispatch_attempt(ledger, key, repository=_REPO, acknowledged=True)
    record_review_outcome(
        ledger,
        key,
        repository=_REPO,
        status=STATUS_FAILED,
        resolution_kind=RESOLUTION_KIND_COLLECTED_RESULT,
        result_bytes=b"d" * 64,
    )
    retry = _claim(ledger, key)
    assert retry["decision"] == REVIEW_CLAIM_REFUSED
    assert "DUPLICATE_LAUNCH_FOR_IDENTITY" in retry["reason_codes"]


def test_an_unacknowledged_dispatch_blocks_redispatch_even_after_a_simulated_restart(
    tmp_path: Path,
) -> None:
    """ "Unknown post-send acknowledgement retains the claim and blocks redispatch, including
    after controller restart" (handoff §4) -- simulated here by never reusing any in-process
    object across the dispatch and the retry: each step reopens the identical ledger path
    from nothing, exactly as a freshly started controller process would.
    """

    ledger = tmp_path / "ledger.json"
    key = _identity()
    _claim(ledger, key)
    record_dispatch_attempt(ledger, key, repository=_REPO, acknowledged=False)
    snapshot = read_claim(ledger, key, repository=_REPO)
    assert snapshot is not None
    assert snapshot["status"] == STATUS_ACK_UNKNOWN

    # "Restart": a brand-new call sequence, touching only the ledger file on disk.
    retry = _claim(ledger, key)
    assert retry["decision"] == REVIEW_CLAIM_REFUSED
    assert "DUPLICATE_LAUNCH_FOR_IDENTITY" in retry["reason_codes"]


def test_dispatch_attempts_counter_is_one_after_the_one_permitted_dispatch(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "ledger.json"
    key = _identity()
    _claim(ledger, key)
    record_dispatch_attempt(ledger, key, repository=_REPO, acknowledged=True)
    snapshot = read_claim(ledger, key, repository=_REPO)
    assert snapshot is not None
    assert snapshot["dispatch_attempts"] == 1
    assert snapshot["status"] == STATUS_DISPATCHED


def test_a_second_dispatch_attempt_on_an_existing_claim_is_refused(tmp_path: Path) -> None:
    """F5 correction (PR #112 comment 6019024445): CLAIMED -> {DISPATCHED|ACK_UNKNOWN} is a
    one-way transition -- a second dispatch of the identical identity is refused outright,
    including when the first attempt only reached ACK_UNKNOWN."""

    ledger = tmp_path / "ledger.json"
    key = _identity()
    _claim(ledger, key)
    record_dispatch_attempt(ledger, key, repository=_REPO, acknowledged=False)
    with pytest.raises(ReviewControlError):
        record_dispatch_attempt(ledger, key, repository=_REPO, acknowledged=True)
    snapshot = read_claim(ledger, key, repository=_REPO)
    assert snapshot is not None
    assert snapshot["dispatch_attempts"] == 1
    assert snapshot["status"] == STATUS_ACK_UNKNOWN


# --------------------------------------------------------------------------- #
# one concurrent review per repository
# --------------------------------------------------------------------------- #


def test_a_second_identity_is_refused_while_the_first_is_still_active(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    first_key = _identity(pull_request="#201")
    second_key = _identity(pull_request="#202")
    first = _claim(ledger, first_key)
    assert first["decision"] == REVIEW_CLAIM_ADMITTED
    second = _claim(ledger, second_key)
    assert second["decision"] == REVIEW_CLAIM_REFUSED
    assert "CONCURRENT_REVIEW_ACTIVE" in second["reason_codes"]


def test_the_concurrency_slot_is_released_on_outcome_and_a_new_identity_may_then_claim(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "ledger.json"
    first_key = _identity(pull_request="#201")
    second_key = _identity(pull_request="#202")
    _claim(ledger, first_key)
    record_dispatch_attempt(ledger, first_key, repository=_REPO, acknowledged=True)
    record_review_outcome(
        ledger,
        first_key,
        repository=_REPO,
        status=STATUS_COMPLETED,
        resolution_kind=RESOLUTION_KIND_COLLECTED_RESULT,
        result_bytes=b"d" * 64,
    )
    second = _claim(ledger, second_key)
    assert second["decision"] == REVIEW_CLAIM_ADMITTED
    # And the first identity still can never be claimed again.
    retry_first = _claim(ledger, first_key)
    assert retry_first["decision"] == REVIEW_CLAIM_REFUSED


def test_two_threads_racing_the_same_identity_admit_exactly_one(tmp_path: Path) -> None:
    """A real contention proof over the actual file lock, not merely sequential calls: two
    threads attempt to claim the identical identity at (as close as the OS scheduler allows
    to) the same moment, and the lock this module takes must still let exactly one through."""

    ledger = tmp_path / "ledger.json"
    key = _identity()
    results: list[dict[str, Any]] = []
    barrier = threading.Barrier(2)

    def attempt() -> None:
        barrier.wait()
        results.append(_claim(ledger, key))

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    admitted = [result for result in results if result["decision"] == REVIEW_CLAIM_ADMITTED]
    refused = [result for result in results if result["decision"] == REVIEW_CLAIM_REFUSED]
    assert len(admitted) == 1
    assert len(refused) == 1
    assert "DUPLICATE_LAUNCH_FOR_IDENTITY" in refused[0]["reason_codes"]


# --------------------------------------------------------------------------- #
# the JST daily launch ceiling, with a real rollover
# --------------------------------------------------------------------------- #


def test_the_fifth_launch_in_one_jst_day_is_refused(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    for index in range(4):
        key = _identity(pull_request=f"#{300 + index}")
        decision = _claim(ledger, key, now="2026-10-06T12:00:00Z")
        assert decision["decision"] == REVIEW_CLAIM_ADMITTED, (index, decision)
        record_dispatch_attempt(ledger, key, repository=_REPO, acknowledged=True)
        record_review_outcome(
            ledger,
            key,
            repository=_REPO,
            status=STATUS_COMPLETED,
            resolution_kind=RESOLUTION_KIND_COLLECTED_RESULT,
            result_bytes=b"d" * 64,
        )

    fifth_key = _identity(pull_request="#399")
    fifth = _claim(ledger, fifth_key, now="2026-10-06T12:00:00Z")
    assert fifth["decision"] == REVIEW_CLAIM_REFUSED
    assert "DAILY_LAUNCH_CEILING_REACHED" in fifth["reason_codes"]


def test_a_launch_across_the_jst_rollover_gets_a_fresh_daily_budget(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    for index in range(4):
        key = _identity(pull_request=f"#{400 + index}")
        decision = _claim(ledger, key, now="2026-10-06T12:00:00Z")  # 2026-10-06 JST
        assert decision["decision"] == REVIEW_CLAIM_ADMITTED
        record_dispatch_attempt(ledger, key, repository=_REPO, acknowledged=True)
        record_review_outcome(
            ledger,
            key,
            repository=_REPO,
            status=STATUS_COMPLETED,
            resolution_kind=RESOLUTION_KIND_COLLECTED_RESULT,
            result_bytes=b"d" * 64,
        )

    exhausted_key = _identity(pull_request="#499")
    assert (
        _claim(ledger, exhausted_key, now="2026-10-06T12:00:00Z")["decision"]
        == REVIEW_CLAIM_REFUSED
    )

    # 2026-10-06T15:00:00Z is 2026-10-07 JST -- a new calendar day's own fresh budget.
    rolled_over_key = _identity(pull_request="#500")
    rolled_over = _claim(ledger, rolled_over_key, now="2026-10-06T15:00:00Z")
    assert rolled_over["decision"] == REVIEW_CLAIM_ADMITTED


# --------------------------------------------------------------------------- #
# the numeric ceiling itself is never a caller-supplied, un-verified value
# --------------------------------------------------------------------------- #


def test_claim_review_launch_refuses_a_widened_numeric_limits_argument(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    widened = {**BOUNDED_REVIEW_NUMERIC_LIMITS, "max_launches_per_jst_day": 999}
    with pytest.raises(ReviewControlError):
        claim_review_launch(
            ledger,
            identity_key=_identity(),
            work_unit_id="WU-1",
            repository=_REPO,
            now=_NOW,
            numeric_limits=widened,
        )


# --------------------------------------------------------------------------- #
# ledger integrity: corrupt, cross-repository, or unknown-shape ledgers refuse rather than
# silently proceed
# --------------------------------------------------------------------------- #


def test_a_corrupt_ledger_file_raises_rather_than_silently_resetting(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    ledger.write_text("not json at all", encoding="utf-8")
    with pytest.raises(ReviewControlError):
        _claim(ledger, _identity())


def test_a_ledger_for_a_different_repository_raises(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    _claim(ledger, _identity())
    with pytest.raises(ReviewControlError):
        claim_review_launch(
            ledger,
            identity_key=_identity(pull_request="#999"),
            work_unit_id="WU-2",
            repository="someone/else",
            now=_NOW,
            numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
        )


def test_recording_an_outcome_for_an_unclaimed_identity_raises(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    with pytest.raises(ReviewControlError):
        record_review_outcome(
            ledger,
            _identity(),
            repository=_REPO,
            status=STATUS_COMPLETED,
            resolution_kind=RESOLUTION_KIND_COLLECTED_RESULT,
            result_bytes=b"d" * 64,
        )


def test_recording_a_dispatch_for_an_unclaimed_identity_raises(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    with pytest.raises(ReviewControlError):
        record_dispatch_attempt(ledger, _identity(), repository=_REPO, acknowledged=True)


def test_an_unrecognized_outcome_status_raises(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    key = _identity()
    _claim(ledger, key)
    record_dispatch_attempt(ledger, key, repository=_REPO, acknowledged=True)
    with pytest.raises(ReviewControlError):
        record_review_outcome(
            ledger,
            key,
            repository=_REPO,
            status="SOMETHING_ELSE",
            resolution_kind=RESOLUTION_KIND_COLLECTED_RESULT,
            result_bytes=b"d" * 64,
        )


def test_sr2_f4_collected_result_with_no_real_digest_is_refused(tmp_path: Path) -> None:
    """SR2-F4 correction (PR #112 comment 6021757577): the exact reproduction the finding
    names -- an ACK_UNKNOWN claim resolved FAILED/COLLECTED_RESULT with result_bytes=None,
    asserting a result was collected while presenting nothing that was actually collected --
    must be refused outright, never silently accepted as a terminal outcome that releases the
    concurrency slot."""

    ledger = tmp_path / "ledger.json"
    key = _identity()
    _claim(ledger, key)
    record_dispatch_attempt(ledger, key, repository=_REPO, acknowledged=False)
    with pytest.raises(ReviewControlError):
        record_review_outcome(
            ledger,
            key,
            repository=_REPO,
            status=STATUS_FAILED,
            resolution_kind=RESOLUTION_KIND_COLLECTED_RESULT,
            result_bytes=None,
        )
    # The claim must still be exactly as it was -- ACK_UNKNOWN, slot still held -- never
    # silently resolved by the refused call.
    snapshot = read_claim(ledger, key, repository=_REPO)
    assert snapshot is not None
    assert snapshot["status"] == STATUS_ACK_UNKNOWN
    assert snapshot["result_digest"] is None


def test_sr3_f4_the_recorded_digest_is_always_genuinely_computed_from_result_bytes(
    tmp_path: Path,
) -> None:
    """SR3-F4 correction (PR #112 comment 6030487245): before this correction,
    ``record_review_outcome`` accepted a bare caller-asserted ``result_digest: str`` -- any
    well-formed 64-character lowercase hex string satisfied the shape check, including
    ``"0" * 64`` with zero actual collected bytes behind it at all. This function no longer
    accepts a digest parameter -- it accepts the real collected bytes themselves and computes
    the one digest it ever records from them directly, so the recorded digest can never be
    disconnected from any bytes whatsoever."""

    import hashlib

    ledger = tmp_path / "ledger.json"
    key = _identity()
    _claim(ledger, key)
    record_dispatch_attempt(ledger, key, repository=_REPO, acknowledged=True)
    record_review_outcome(
        ledger,
        key,
        repository=_REPO,
        status=STATUS_COMPLETED,
        resolution_kind=RESOLUTION_KIND_COLLECTED_RESULT,
        result_bytes=b"",
    )
    snapshot = read_claim(ledger, key, repository=_REPO)
    assert snapshot is not None
    assert snapshot["result_digest"] == hashlib.sha256(b"").hexdigest()
    assert snapshot["result_digest"] != "0" * 64


def test_sr3_f4_record_review_outcome_no_longer_accepts_a_bare_caller_digest(
    tmp_path: Path,
) -> None:
    """The exact SR3-F4 reproduction: a caller could previously assert an arbitrary
    ``result_digest`` string with no real bytes behind it at all (e.g. ``"0" * 64``) and have
    it admitted as a new, resolved identity. That parameter no longer exists."""

    ledger = tmp_path / "ledger.json"
    key = _identity()
    _claim(ledger, key)
    record_dispatch_attempt(ledger, key, repository=_REPO, acknowledged=True)
    with pytest.raises(TypeError):
        record_review_outcome(  # type: ignore[call-arg]
            ledger,
            key,
            repository=_REPO,
            status=STATUS_FAILED,
            resolution_kind=RESOLUTION_KIND_COLLECTED_RESULT,
            result_digest="0" * 64,
        )


def test_sr2_f4_confirmed_cancellation_with_a_digest_is_refused(tmp_path: Path) -> None:
    """A cancellation never collects a result -- a caller that supplies a result_digest
    alongside CONFIRMED_CANCELLATION is asserting evidence that kind of resolution can never
    actually have."""

    ledger = tmp_path / "ledger.json"
    key = _identity()
    _claim(ledger, key)
    record_dispatch_attempt(ledger, key, repository=_REPO, acknowledged=True)
    with pytest.raises(ReviewControlError):
        record_review_outcome(
            ledger,
            key,
            repository=_REPO,
            status=STATUS_FAILED,
            resolution_kind=RESOLUTION_KIND_CONFIRMED_CANCELLATION,
            result_bytes=b"d" * 64,
        )


def test_sr2_f4_confirm_dispatch_sent_upgrades_an_ack_unknown_claim_with_real_pid(
    tmp_path: Path,
) -> None:
    """SR2-F4 correction: the composed route marks ACK_UNKNOWN *before* the external effect
    begins, then calls :func:`confirm_dispatch_sent` the instant the real process exists --
    attaching its pid/process identity and upgrading the claim to DISPATCHED, so a controller
    restarted after this point (but before collection ever finishes) can still recover
    genuine ownership proof, never mistaking this for an unsent claim."""

    ledger = tmp_path / "ledger.json"
    key = _identity()
    _claim(ledger, key)
    record_dispatch_attempt(ledger, key, repository=_REPO, acknowledged=False)
    confirm_dispatch_sent(ledger, key, repository=_REPO, pid=424242, process_identity="424242:99")
    snapshot = read_claim(ledger, key, repository=_REPO)
    assert snapshot is not None
    assert snapshot["status"] == STATUS_DISPATCHED
    assert snapshot["pid"] == 424242
    assert snapshot["process_identity"] == "424242:99"

    # Once DISPATCHED, release_unsent_claim must refuse -- this claim is no longer "unsent".
    with pytest.raises(ReviewControlError):
        release_unsent_claim(ledger, key, repository=_REPO)

    # And confirm_dispatch_sent itself is a one-way, one-call transition -- a claim already
    # DISPATCHED may never be "confirmed sent" a second time.
    with pytest.raises(ReviewControlError):
        confirm_dispatch_sent(ledger, key, repository=_REPO, pid=1, process_identity="1:1")


def test_read_claim_of_an_unknown_identity_is_none_not_an_error(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    _claim(ledger, _identity())
    assert read_claim(ledger, _identity(pull_request="#never-claimed"), repository=_REPO) is None


def test_the_claim_status_starts_claimed_before_any_dispatch(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    key = _identity()
    _claim(ledger, key)
    snapshot = read_claim(ledger, key, repository=_REPO)
    assert snapshot is not None
    assert snapshot["status"] == STATUS_CLAIMED
    assert snapshot["dispatch_attempts"] == 0
    assert snapshot["result_digest"] is None
