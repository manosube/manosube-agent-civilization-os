"""V1: `06_DEFERRED_DIFFERENCES.md` register parsing (Issue #92,
`ADOPT_PHASE_22_V1_0_ACCEPTANCE`)."""

from __future__ import annotations

from pathlib import Path

import pytest

from manosube_agent_civilization.v1_0_acceptance.deferred_differences_register import (
    DEFAULT_REGISTER_RELATIVE_PATH,
    parse_deferred_differences_register,
)
from manosube_agent_civilization.v1_0_acceptance.errors import (
    DeferredDifferencesRegisterError,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_real_register_parses_every_currently_active_record() -> None:
    records = parse_deferred_differences_register(REPO_ROOT / DEFAULT_REGISTER_RELATIVE_PATH)
    record_ids = {r.record_id for r in records}
    # The exact active-record set as of this Phase 22 round -- a change to this set is a
    # real register change this test must be updated to see, never silently absorbed.
    assert record_ids == {
        "DD-0001",
        "DD-0002",
        "DC-0001",
        "FD-0001",
        "FD-0002",
        "FD-0003",
        "FD-0005",
    }


def test_real_register_every_record_has_classification_and_status() -> None:
    records = parse_deferred_differences_register(REPO_ROOT / DEFAULT_REGISTER_RELATIVE_PATH)
    for record in records:
        assert record.classification
        assert record.current_status


def test_fd_0005_blocking_effect_scoped_to_phase_21() -> None:
    records = parse_deferred_differences_register(REPO_ROOT / DEFAULT_REGISTER_RELATIVE_PATH)
    fd_0005 = next(r for r in records if r.record_id == "FD-0005")
    assert fd_0005.current_phase_blocking_effect == "NONE_FOR_PHASE_21_ACCEPTANCE"


def test_missing_file_raises_register_error(tmp_path: Path) -> None:
    with pytest.raises(DeferredDifferencesRegisterError):
        parse_deferred_differences_register(tmp_path / "does_not_exist.md")


def test_record_missing_classification_raises(tmp_path: Path) -> None:
    register = tmp_path / "register.md"
    register.write_text(
        "# 3. Active Deferred Difference DD-9999\n\n```text\nDIFFERENCE_ID=DD-9999\n"
        "CURRENT_STATUS=OPEN\n```\n",
        encoding="utf-8",
    )
    with pytest.raises(DeferredDifferencesRegisterError):
        parse_deferred_differences_register(register)


def test_record_missing_current_status_raises(tmp_path: Path) -> None:
    register = tmp_path / "register.md"
    register.write_text(
        "# 3. Active Deferred Difference DD-9999\n\n```text\nDIFFERENCE_ID=DD-9999\n"
        "CLASSIFICATION=FOLLOW_ON_DIFFERENCE\n```\n",
        encoding="utf-8",
    )
    with pytest.raises(DeferredDifferencesRegisterError):
        parse_deferred_differences_register(register)


def test_two_records_in_same_document_both_parsed(tmp_path: Path) -> None:
    register = tmp_path / "register.md"
    register.write_text(
        "# 3. First\n\n```text\nDIFFERENCE_ID=DD-0100\nCLASSIFICATION=FOLLOW_ON_DIFFERENCE\n"
        "CURRENT_STATUS=OPEN\nCURRENT_PHASE_BLOCKING_EFFECT=NONE\n```\n\n"
        "# 4. Second\n\n```text\nCANDIDATE_ID=DC-0100\nCLASSIFICATION=DEFERRED_DESIGN_CANDIDATE\n"
        "CURRENT_STATUS=PROTOTYPE\n```\n",
        encoding="utf-8",
    )
    records = parse_deferred_differences_register(register)
    assert [r.record_id for r in records] == ["DD-0100", "DC-0100"]
    assert records[0].current_phase_blocking_effect == "NONE"
    assert records[1].current_phase_blocking_effect is None
