"""Phase 19 (Issue #77) V2: Difference-derived selection matrix.

Proves 1, 2 and N slots, a genuine closed maximum, unsupported/ambiguous capability refusal,
and no caller-selected-count bypass -- :func:`~manosube_agent_civilization.multi_agent.
selection.select_agent_slots` takes no parameter through which a caller preference, a model
recommendation, provider availability, a majority strategy, or a preconfigured organization
could ever reach it.
"""

from __future__ import annotations

import inspect

import pytest
from tests.fixtures.multi_agent_world import difference_for

from manosube_agent_civilization.multi_agent.errors import (
    MultiAgentOverLimitError,
    MultiAgentUnsupportedRequirementError,
)
from manosube_agent_civilization.multi_agent.selection import (
    MAX_AGENT_SLOTS,
    RISK_CLASS_TO_SLOT_COUNT,
    select_agent_slots,
)


def test_the_mapping_is_total_over_the_closed_risk_class_enum() -> None:
    assert set(RISK_CLASS_TO_SLOT_COUNT) == {"LOW", "MODERATE", "HIGH", "CRITICAL"}


def test_the_mapping_produces_a_genuine_1_2_and_n_across_the_four_classes() -> None:
    counts = sorted(set(RISK_CLASS_TO_SLOT_COUNT.values()))
    assert counts == [1, 2, 3]
    assert 1 in RISK_CLASS_TO_SLOT_COUNT.values()
    assert 2 in RISK_CLASS_TO_SLOT_COUNT.values()
    assert max(RISK_CLASS_TO_SLOT_COUNT.values()) >= 3


def test_max_agent_slots_equals_the_mapping_s_own_maximum() -> None:
    assert max(RISK_CLASS_TO_SLOT_COUNT.values()) == MAX_AGENT_SLOTS
    assert MAX_AGENT_SLOTS == 3


@pytest.mark.parametrize(
    ("risk_class", "expected"), [("LOW", 1), ("MODERATE", 1), ("HIGH", 2), ("CRITICAL", 3)]
)
def test_select_agent_slots_matches_the_closed_mapping_for_a_real_difference(
    risk_class: str, expected: int
) -> None:
    difference = difference_for(f"PRJ-SEL-{risk_class}", risk_class=risk_class)
    slots = select_agent_slots(difference)
    assert len(slots) == expected
    assert [slot["slot_index"] for slot in slots] == list(range(expected))
    assert {slot["capability"] for slot in slots} == {"PROPOSE_EVIDENCE_CANDIDATE"}


def test_select_agent_slots_is_deterministic_and_total() -> None:
    difference = difference_for("PRJ-SEL-DET", risk_class="HIGH")
    first = select_agent_slots(difference)
    second = select_agent_slots(difference)
    assert first == second


def test_select_agent_slots_refuses_an_unknown_risk_class() -> None:
    difference = dict(difference_for("PRJ-SEL-UNKNOWN", risk_class="LOW"))
    difference["risk_class"] = "NOT_A_REAL_RISK_CLASS"
    with pytest.raises(MultiAgentUnsupportedRequirementError):
        select_agent_slots(difference)


def test_select_agent_slots_refuses_a_missing_risk_class() -> None:
    difference = dict(difference_for("PRJ-SEL-MISSING", risk_class="LOW"))
    del difference["risk_class"]
    with pytest.raises(MultiAgentUnsupportedRequirementError):
        select_agent_slots(difference)


def test_select_agent_slots_refuses_a_non_string_risk_class() -> None:
    difference = dict(difference_for("PRJ-SEL-NONSTR", risk_class="LOW"))
    difference["risk_class"] = ["HIGH"]
    with pytest.raises(MultiAgentUnsupportedRequirementError):
        select_agent_slots(difference)


def test_select_agent_slots_has_no_caller_selected_count_parameter() -> None:
    """No parameter on this function's own signature could ever let a caller, a model
    recommendation, provider availability, a majority strategy, or a preconfigured
    organization decide the slot count -- the signature itself is the proof."""

    signature = inspect.signature(select_agent_slots)
    assert list(signature.parameters) == ["difference"]


def test_an_over_limit_mapped_count_is_refused_defensively(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unreachable through the shipped mapping alone (every value is within bound), but
    checked anyway -- a decisive, always-on defensive gate rather than an unenforced
    assumption."""

    from manosube_agent_civilization.multi_agent import selection as selection_module

    tampered = dict(RISK_CLASS_TO_SLOT_COUNT)
    tampered["CRITICAL"] = MAX_AGENT_SLOTS + 1
    monkeypatch.setattr(selection_module, "RISK_CLASS_TO_SLOT_COUNT", tampered)
    difference = difference_for("PRJ-SEL-OVERLIMIT", risk_class="CRITICAL")
    with pytest.raises(MultiAgentOverLimitError):
        selection_module.select_agent_slots(difference)


def test_an_ambiguous_capability_vocabulary_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the system-wide capability vocabulary ever gained a second member, this delivery's
    fixed one-capability-per-slot assignment would become ambiguous -- refused, never
    silently resolved by picking one."""

    from manosube_agent_civilization.multi_agent import selection as selection_module

    monkeypatch.setattr(
        selection_module,
        "MULTI_AGENT_CAPABILITIES",
        frozenset({"PROPOSE_EVIDENCE_CANDIDATE", "SOME_FUTURE_CAPABILITY"}),
    )
    difference = difference_for("PRJ-SEL-AMBIGUOUS", risk_class="LOW")
    with pytest.raises(MultiAgentUnsupportedRequirementError):
        selection_module.select_agent_slots(difference)
