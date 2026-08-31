"""The executable lifecycle table is the contract's table, and there is only one.

``LEGAL_TRANSITIONS`` lives in ``manosube_agent_civilization.difference.lifecycle`` and is
imported by the independent cross-record validator, so no second table exists. These
proofs pin it to the transition table in ``00_KERNEL/04_DIFFERENCE/DIFFERENCE_LIFECYCLE.md``
so the code cannot drift from the contract.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import scripts.difference_contract_validator as validator

from manosube_agent_civilization.difference.lifecycle import (
    LEGAL_TRANSITIONS,
    NEXT_OBSERVATION_REASON,
    OBSERVATION_BOUND_FORBIDDEN,
    REQUIRES_NEXT_OBSERVATION,
    TERMINAL_STATUSES,
    is_legal_transition,
    legal_supersession_sources,
)

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "00_KERNEL" / "04_DIFFERENCE" / "DIFFERENCE_LIFECYCLE.md"
_ROW = re.compile(r"^\|\s*`(\w+)`\s*\|\s*`(\w+)`\s*\|", re.MULTILINE)


def _contract_transitions() -> set[tuple[str | None, str]]:
    """Parse only the section 3 transition table, not other two-column tables."""

    source = CONTRACT.read_text(encoding="utf-8")
    start = source.index("# 3. Legal Transitions")
    end = source.index("\n# ", start)
    return {
        (None if left == "null" else left, right)
        for left, right in _ROW.findall(source[start:end])
    }


def test_the_executable_table_is_the_contract_table() -> None:
    parsed = _contract_transitions()
    assert parsed, "the lifecycle contract transition table could not be parsed"
    assert set(LEGAL_TRANSITIONS) == parsed


def test_exactly_one_transition_table_exists() -> None:
    """The independent validator imports the table; it does not define its own."""

    # The validator holds the imported object itself, not a copy or a second table.
    assert vars(validator)["LEGAL_TRANSITIONS"] is LEGAL_TRANSITIONS
    assert "LEGAL_TRANSITIONS = {" not in (
        ROOT / "scripts" / "difference_contract_validator.py"
    ).read_text(encoding="utf-8")


def test_terminal_statuses_have_no_outgoing_transition() -> None:
    for status in TERMINAL_STATUSES:
        assert not [target for source, target in LEGAL_TRANSITIONS if source == status]


def test_closed_is_not_terminal() -> None:
    assert "CLOSED" not in TERMINAL_STATUSES
    assert is_legal_transition("CLOSED", "REOPENED")
    assert is_legal_transition("CLOSED", "SUPERSEDED")


def test_observation_bound_forbidden_statuses_are_closed_or_terminal() -> None:
    assert TERMINAL_STATUSES | {"CLOSED"} == OBSERVATION_BOUND_FORBIDDEN


def test_every_status_requiring_a_next_observation_has_a_reason_code() -> None:
    assert set(NEXT_OBSERVATION_REASON) == REQUIRES_NEXT_OBSERVATION
    assert {"BLOCKED", "RETAINED", "REOPENED"} == REQUIRES_NEXT_OBSERVATION


def test_supersession_sources_are_derived_from_the_table() -> None:
    assert legal_supersession_sources() == {
        source for source, target in LEGAL_TRANSITIONS if target == "SUPERSEDED" and source
    }
