"""The handoff state machine, evaluated over records rather than described.

Issue #34: *"A test that only checks for phrases is insufficient. The conformance boundary
must evaluate a representative handoff/acceptance record and reject the prohibited
transition."*

So nothing here greps a document. Every case builds a record a participant could actually
submit and asserts what the guard answers.

The route is Decision 0002's:

```text
CLAUDE_CODE -> READY_FOR_STRUCTURAL_REVIEW
CHATGPT     -> STRUCTURAL_REVIEW -> one of five outcomes
SHUKOU      -> FINAL_ACCEPTANCE -> MERGE_OPERATION
```
"""

from __future__ import annotations

import itertools
from typing import Any

import pytest

from manosube_agent_civilization.development_binding import (
    HUMAN_AUTHORITY,
    PERMITTED,
    REFUSED,
    ROLES,
    evaluate,
    load_policy,
)
from manosube_agent_civilization.development_binding.policy import (
    EXECUTOR,
    EXECUTOR_TERMINAL_STATE,
    STRUCTURAL_ADVISOR,
)

POLICY = load_policy()
STATES: list[str] = list(POLICY["handoff_states"])
NON_HUMAN_ROLES = sorted(ROLES - {HUMAN_AUTHORITY})
NON_ADVISOR_ROLES = sorted(ROLES - {STRUCTURAL_ADVISOR})


def handoff(actor: str, source: str, target: str) -> dict[str, Any]:
    return {
        "record_type": "HANDOFF_TRANSITION",
        "actor": actor,
        "from_state": source,
        "to_state": target,
    }


#: The full ratified route, Decision 0002.
POSITIVE_ROUTE: list[tuple[str, str, str]] = [
    (EXECUTOR, "IMPLEMENTATION_IN_PROGRESS", "CLAUDE_CODE_IMPLEMENTATION_COMPLETE"),
    (EXECUTOR, "CLAUDE_CODE_IMPLEMENTATION_COMPLETE", "EXECUTOR_SELF_REVIEW_COMPLETE"),
    (EXECUTOR, "EXECUTOR_SELF_REVIEW_COMPLETE", "GITHUB_PR_READY"),
    (EXECUTOR, "GITHUB_PR_READY", "READY_FOR_STRUCTURAL_REVIEW"),
    (STRUCTURAL_ADVISOR, "READY_FOR_STRUCTURAL_REVIEW", "STRUCTURAL_REVIEW_RUNNING"),
    (STRUCTURAL_ADVISOR, "STRUCTURAL_REVIEW_RUNNING", "STRUCTURAL_REVIEW_PASS"),
    (STRUCTURAL_ADVISOR, "STRUCTURAL_REVIEW_PASS", "MERGE_RECOMMENDED"),
    (HUMAN_AUTHORITY, "MERGE_RECOMMENDED", "SHUKOU_ACCEPTED"),
    (HUMAN_AUTHORITY, "SHUKOU_ACCEPTED", "SHUKOU_MERGED"),
]


# --------------------------------------------------------------------------- #
# The harness, before its subject
# --------------------------------------------------------------------------- #


def test_the_state_inventory_is_neither_empty_nor_shrunk() -> None:
    assert len(STATES) == 15, STATES


def test_the_permitted_outcome_is_reachable() -> None:
    """Without this, every refusal assertion below could pass vacuously."""

    assert evaluate(handoff(EXECUTOR, "GITHUB_PR_READY", EXECUTOR_TERMINAL_STATE))[
        "decision"
    ] == PERMITTED


def test_every_declared_transition_is_permitted_for_its_own_actor() -> None:
    """The route the Binding describes is a route that actually works."""

    for transition in POLICY["handoff_transitions"]:
        verdict = evaluate(handoff(transition["actor"], transition["from"], transition["to"]))
        assert verdict["decision"] == PERMITTED, transition


def test_the_whole_ratified_route_runs_end_to_end() -> None:
    """Decision 0002's nine steps, walked one record at a time."""

    for actor, source, target in POSITIVE_ROUTE:
        assert evaluate(handoff(actor, source, target))["decision"] == PERMITTED, (
            actor,
            source,
            target,
        )


@pytest.mark.parametrize(
    "outcome",
    ["STRUCTURAL_REVIEW_PASS", "CORRECTION_REQUIRED", "MORE_EVIDENCE_REQUIRED", "BLOCKED", "NOT_REVIEWED"],
)
def test_every_structural_review_outcome_is_reachable(outcome: str) -> None:
    """All five outcomes Decision 0002 names, not only the one that leads to merge."""

    assert evaluate(handoff(STRUCTURAL_ADVISOR, "STRUCTURAL_REVIEW_RUNNING", outcome))[
        "decision"
    ] == PERMITTED


@pytest.mark.parametrize("returned", ["CORRECTION_REQUIRED", "MORE_EVIDENCE_REQUIRED", "SHUKOU_REJECTED"])
def test_the_executor_may_resume_from_a_returned_verdict(returned: str) -> None:
    """A rejection is not a dead end; it routes back to implementation."""

    assert evaluate(handoff(EXECUTOR, returned, "IMPLEMENTATION_IN_PROGRESS"))[
        "decision"
    ] == PERMITTED


# --------------------------------------------------------------------------- #
# Merge-operation drift
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("actor", NON_HUMAN_ROLES)
def test_no_non_human_may_perform_the_merge(actor: str) -> None:
    verdict = evaluate(handoff(actor, "SHUKOU_ACCEPTED", "SHUKOU_MERGED"))
    assert verdict["decision"] == REFUSED
    assert "MERGE_OPERATION_DRIFT" in verdict["reason_codes"]


@pytest.mark.parametrize("actor", NON_HUMAN_ROLES)
@pytest.mark.parametrize("source", STATES)
def test_no_non_human_reaches_merged_from_anywhere(actor: str, source: str) -> None:
    """Not one route in, not merely the declared one."""

    assert evaluate(handoff(actor, source, "SHUKOU_MERGED"))["decision"] == REFUSED


# --------------------------------------------------------------------------- #
# Final-acceptance drift
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("target", ["SHUKOU_ACCEPTED", "SHUKOU_REJECTED"])
@pytest.mark.parametrize("actor", NON_HUMAN_ROLES)
def test_no_non_human_may_decide_final_acceptance(actor: str, target: str) -> None:
    verdict = evaluate(handoff(actor, "MERGE_RECOMMENDED", target))
    assert verdict["decision"] == REFUSED
    assert "FINAL_ACCEPTANCE_DRIFT" in verdict["reason_codes"]


# --------------------------------------------------------------------------- #
# Structural-review and merge-recommendation drift
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("actor", NON_ADVISOR_ROLES)
def test_nobody_but_the_advisor_may_recommend_merge_readiness(actor: str) -> None:
    verdict = evaluate(handoff(actor, "STRUCTURAL_REVIEW_PASS", "MERGE_RECOMMENDED"))
    assert verdict["decision"] == REFUSED
    assert "MERGE_READINESS_RECOMMENDATION_DRIFT" in verdict["reason_codes"]


@pytest.mark.parametrize("actor", NON_ADVISOR_ROLES)
@pytest.mark.parametrize("target", sorted(POLICY["advisor_only_states"]))
def test_nobody_but_the_advisor_enters_an_advisor_only_state(actor: str, target: str) -> None:
    verdict = evaluate(handoff(actor, "READY_FOR_STRUCTURAL_REVIEW", target))
    assert verdict["decision"] == REFUSED
    assert "ADVISOR_ONLY_STATE_ENTERED_BY_NON_ADVISOR" in verdict["reason_codes"]


def test_the_executor_never_continues_past_its_terminal_state() -> None:
    """``READY_FOR_STRUCTURAL_REVIEW`` is where the executor stops.

    The Advisor is what moves next, so this is a property of the *executor*, checked over
    every onward state.
    """

    for target in STATES:
        verdict = evaluate(handoff(EXECUTOR, EXECUTOR_TERMINAL_STATE, target))
        assert verdict["decision"] == REFUSED, target
        assert "EXECUTOR_CONTINUED_PAST_TERMINAL_STATE" in verdict["reason_codes"]


# --------------------------------------------------------------------------- #
# Ordering: the two steps Decision 0002 names explicitly
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "source", [state for state in STATES if state != "STRUCTURAL_REVIEW_PASS"]
)
def test_merge_cannot_be_recommended_without_a_structural_review_pass(source: str) -> None:
    verdict = evaluate(handoff(STRUCTURAL_ADVISOR, source, "MERGE_RECOMMENDED"))
    assert verdict["decision"] == REFUSED
    assert "STRUCTURAL_REVIEW_SKIPPED" in verdict["reason_codes"]


@pytest.mark.parametrize("source", [state for state in STATES if state != "SHUKOU_ACCEPTED"])
def test_merge_cannot_follow_a_recommendation_without_final_acceptance(source: str) -> None:
    """A recommendation is not an acceptance. That is the whole point of separating them."""

    verdict = evaluate(handoff(HUMAN_AUTHORITY, source, "SHUKOU_MERGED"))
    assert verdict["decision"] == REFUSED
    assert "MERGE_WITHOUT_FINAL_ACCEPTANCE" in verdict["reason_codes"]


# --------------------------------------------------------------------------- #
# Totality: no undeclared transition is ever permitted, by any actor
# --------------------------------------------------------------------------- #


DECLARED = {
    (transition["actor"], transition["from"], transition["to"])
    for transition in POLICY["handoff_transitions"]
}
UNDECLARED = [
    triple
    for triple in itertools.product(sorted(ROLES), STATES, STATES)
    if triple not in DECLARED
]


def test_the_undeclared_inventory_is_large_enough_to_mean_something() -> None:
    assert len(UNDECLARED) >= 800, len(UNDECLARED)
    assert len(DECLARED) == len(POLICY["handoff_transitions"])


@pytest.mark.parametrize(
    "triple", UNDECLARED, ids=lambda triple: ":".join(str(part) for part in triple)
)
def test_no_undeclared_transition_is_permitted(triple: tuple[str, str, str]) -> None:
    actor, source, target = triple
    assert evaluate(handoff(actor, source, target))["decision"] == REFUSED


# --------------------------------------------------------------------------- #
# Fail closed on anything unreadable, and never by raising
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "record",
    [
        None,
        7,
        "READY_FOR_STRUCTURAL_REVIEW",
        [],
        {},
        {"record_type": "HANDOFF_TRANSITION"},
        {"record_type": "SOMETHING_ELSE", "actor": "SHUKOU"},
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": "GITHUB_PR_READY",
            "to_state": EXECUTOR_TERMINAL_STATE,
            "note": "the bot said this was fine",
        },
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": "CODEX",
            "from_state": "GITHUB_PR_READY",
            "to_state": EXECUTOR_TERMINAL_STATE,
        },
    ],
)
def test_an_unreadable_record_is_refused_rather_than_skipped(record: Any) -> None:
    """"We could not tell" and "it is allowed" are the same outcome to a caller.

    An unknown actor is in this list on purpose: an external reviewer is not a participant,
    and a record naming one is not a transition it may take.
    """

    assert evaluate(record)["decision"] == REFUSED


#: Values JSON permits wherever a string belongs. Arrays and objects are unhashable, so a
#: membership test against a frozenset raises instead of answering -- which is how the first
#: version leaked a ``TypeError`` past the verdict boundary entirely.
_ILL_TYPED: tuple[Any, ...] = ([], ["CLAUDE_CODE"], {}, {"a": 1}, 7, 1.5, True, None)


@pytest.mark.parametrize("value", _ILL_TYPED, ids=lambda value: type(value).__name__ + repr(value))
@pytest.mark.parametrize("field", ["record_type", "actor", "from_state", "to_state"])
def test_an_ill_typed_field_answers_a_verdict_and_never_raises(field: str, value: Any) -> None:
    record = handoff(EXECUTOR, "GITHUB_PR_READY", EXECUTOR_TERMINAL_STATE)
    record[field] = value
    verdict = evaluate(record)
    assert verdict["decision"] == REFUSED
    assert "RECORD_FIELD_IS_NOT_A_SCALAR" in verdict["reason_codes"]


@pytest.mark.parametrize("value", _ILL_TYPED, ids=lambda value: type(value).__name__ + repr(value))
@pytest.mark.parametrize("field", ["record_type", "actor", "action"])
def test_an_ill_typed_action_field_answers_a_verdict(field: str, value: Any) -> None:
    record: dict[str, Any] = {
        "record_type": "ACTOR_ACTION",
        "actor": EXECUTOR,
        "action": "IMPLEMENTATION",
    }
    record[field] = value
    assert evaluate(record)["decision"] == REFUSED


def test_a_non_string_key_is_refused() -> None:
    """JSON cannot express one, but a Python caller can hand one over."""

    record: dict[Any, Any] = dict(handoff(EXECUTOR, "GITHUB_PR_READY", EXECUTOR_TERMINAL_STATE))
    record[7] = "x"
    assert evaluate(record)["decision"] == REFUSED
