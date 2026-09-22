"""V1: v1.0-blocking Difference disposition (Issue #92, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`)."""

from __future__ import annotations

from pathlib import Path

from manosube_agent_civilization.v1_0_acceptance.blocking_differences import (
    classify_v1_0_blocking_differences,
    rederive_all_v1_0_blocking_differences_closed,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_real_register_dc_0001_is_non_blocking() -> None:
    dispositions = classify_v1_0_blocking_differences(REPO_ROOT)
    dc_0001 = next(d for d in dispositions if d.record_id == "DC-0001")
    assert dc_0001.disposition == "NON_BLOCKING"


def test_real_register_fd_0005_is_non_blocking_by_explicit_adoption() -> None:
    dispositions = classify_v1_0_blocking_differences(REPO_ROOT)
    fd_0005 = next(d for d in dispositions if d.record_id == "FD-0005")
    assert fd_0005.disposition == "NON_BLOCKING"
    assert "Issue #92" in fd_0005.rationale


def test_real_register_five_disposed_records_are_non_blocking() -> None:
    """`ADOPT_P92_V1_0_DIFFERENCE_DISPOSITION_R1_AND_FINAL_GATE22_SYNC` (Issue #92 comment
    `5755827293`) closed or cancelled DD-0001/DD-0002/FD-0001/FD-0003; PR #94's own
    delivery head could not yet close FD-0002 (`ADOPT_P94_R1_F1`, comment `5760099935`)
    because its closure condition -- the README correction existing on accepted `main`
    plus post-merge after-state re-observation -- was not yet satisfied. That evidence
    now exists: PR #94 merged (`ddf906eb7cefa43a0c43ce3dc1c208c7c5602439`) and the
    Structural Advisor independently re-observed the resulting `main`
    (`P94_POST_MERGE_AFTER_STATE_R1`, Issue #92 comment `5768458110`). SHUKOU adopted
    FD-0002's closure on that evidence (`ADOPT_P92_FINAL_POST_MERGE_SOURCE_SYNC_R1`,
    comment `5768466436`), so all five records now read `CLOSED_WITH_EVIDENCE`/
    `CANCELLED_BY_HUMAN_DECISION`, both unconditionally non-blocking classifications --
    never inferred, only read from each record's own updated classification field."""
    dispositions = classify_v1_0_blocking_differences(REPO_ROOT)
    for record_id in ("DD-0001", "DD-0002", "FD-0001", "FD-0002", "FD-0003"):
        d = next(x for x in dispositions if x.record_id == record_id)
        assert d.disposition == "NON_BLOCKING", record_id


def test_predicate_12_is_pass_when_every_active_record_is_non_blocking() -> None:
    verdict, dispositions = rederive_all_v1_0_blocking_differences_closed(REPO_ROOT)
    assert verdict == "PASS"
    for disposition in dispositions:
        assert disposition.disposition == "NON_BLOCKING", disposition.record_id


def test_all_non_blocking_yields_pass(tmp_path: Path) -> None:
    register = tmp_path / "register.md"
    register.write_text(
        "# 3. Only\n\n```text\nDIFFERENCE_ID=DD-9000\n"
        "CLASSIFICATION=DEFERRED_DESIGN_CANDIDATE\nCURRENT_STATUS=PROTOTYPE\n```\n",
        encoding="utf-8",
    )
    verdict, dispositions = rederive_all_v1_0_blocking_differences_closed(
        tmp_path, register_relative_path="register.md"
    )
    assert verdict == "PASS"
    assert dispositions[0].disposition == "NON_BLOCKING"


def test_unrecognized_classification_yields_fail_not_silent_pass(tmp_path: Path) -> None:
    register = tmp_path / "register.md"
    register.write_text(
        "# 3. Bad\n\n```text\nDIFFERENCE_ID=DD-9001\n"
        "CLASSIFICATION=NOT_A_REAL_CLASSIFICATION\nCURRENT_STATUS=OPEN\n```\n",
        encoding="utf-8",
    )
    verdict, dispositions = rederive_all_v1_0_blocking_differences_closed(
        tmp_path, register_relative_path="register.md"
    )
    assert verdict == "FAIL"
    assert dispositions[0].disposition == "REGISTER_CONTENT_CONTRADICTION"


def test_none_prefixed_blocking_effect_still_requires_disposition(tmp_path: Path) -> None:
    """A `CURRENT_PHASE_BLOCKING_EFFECT=NONE*` value scoped to an earlier Phase must never
    be silently read as clearance for v1.0/Phase 22 -- it always needs an explicit
    disposition unless the record id is one this package's own record already names
    (see `_EXPLICITLY_ADOPTED_NON_BLOCKING_RECORD_IDS`)."""
    register = tmp_path / "register.md"
    register.write_text(
        "# 3. Only\n\n```text\nDIFFERENCE_ID=DD-9002\n"
        "CLASSIFICATION=FOLLOW_ON_DIFFERENCE\nCURRENT_STATUS=OPEN\n"
        "CURRENT_PHASE_BLOCKING_EFFECT=NONE_FOR_SOME_EARLIER_PHASE\n```\n",
        encoding="utf-8",
    )
    verdict, dispositions = rederive_all_v1_0_blocking_differences_closed(
        tmp_path, register_relative_path="register.md"
    )
    assert verdict == "UNKNOWN"
    assert dispositions[0].disposition == "REQUIRES_HUMAN_AUTHORITY_DISPOSITION"
