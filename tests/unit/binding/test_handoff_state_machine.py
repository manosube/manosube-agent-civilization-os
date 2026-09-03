"""The handoff state machine, evaluated over records rather than described.

Issue #34: *"A test that only checks for phrases is insufficient. The conformance boundary
must evaluate a representative handoff/acceptance record and reject the prohibited
transition."*

So nothing here greps a document. Every case builds a record a participant could actually
submit and asserts what the guard answers.
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

POLICY = load_policy()
STATES: list[str] = list(POLICY["handoff_states"])
NON_HUMAN_ROLES = sorted(ROLES - {HUMAN_AUTHORITY})


def handoff(actor: str, source: str, target: str) -> dict[str, Any]:
    return {
        "record_type": "HANDOFF_TRANSITION",
        "actor": actor,
        "from_state": source,
        "to_state": target,
    }


# --------------------------------------------------------------------------- #
# The harness, before its subject
# --------------------------------------------------------------------------- #


def test_the_state_inventory_is_neither_empty_nor_shrunk() -> None:
    assert len(STATES) >= 9, STATES


def test_the_permitted_outcome_is_reachable() -> None:
    """Without this, every refusal assertion below could pass vacuously."""

    verdict = evaluate(handoff("CLAUDE_CODE", "GITHUB_PR_READY", "READY_FOR_SHUKOU_REVIEW"))
    assert verdict["decision"] == PERMITTED


def test_every_declared_transition_is_permitted_for_its_own_actor() -> None:
    """The route the Binding describes is a route that actually works."""

    for transition in POLICY["handoff_transitions"]:
        verdict = evaluate(
            handoff(transition["actor"], transition["from"], transition["to"])
        )
        assert verdict["decision"] == PERMITTED, transition


def test_the_whole_lifecycle_runs_end_to_end() -> None:
    """The lifecycle Issue #34 requires, walked one record at a time."""

    lifecycle = [
        ("CLAUDE_CODE", "IMPLEMENTATION_IN_PROGRESS", "CLAUDE_CODE_IMPLEMENTATION_COMPLETE"),
        ("CLAUDE_CODE", "CLAUDE_CODE_IMPLEMENTATION_COMPLETE", "EXECUTOR_SELF_REVIEW_COMPLETE"),
        ("CLAUDE_CODE", "EXECUTOR_SELF_REVIEW_COMPLETE", "GITHUB_PR_READY"),
        ("CLAUDE_CODE", "GITHUB_PR_READY", "READY_FOR_SHUKOU_REVIEW"),
        ("SHUKOU", "READY_FOR_SHUKOU_REVIEW", "SHUKOU_CHECK"),
        ("SHUKOU", "SHUKOU_CHECK", "SHUKOU_ACCEPTED"),
        ("SHUKOU", "SHUKOU_ACCEPTED", "SHUKOU_MERGED"),
    ]
    for actor, source, target in lifecycle:
        assert evaluate(handoff(actor, source, target))["decision"] == PERMITTED


# --------------------------------------------------------------------------- #
# Merge-authority drift
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("actor", NON_HUMAN_ROLES)
def test_no_non_human_may_merge(actor: str) -> None:
    verdict = evaluate(handoff(actor, "SHUKOU_ACCEPTED", "SHUKOU_MERGED"))
    assert verdict["decision"] == REFUSED
    assert "MERGE_AUTHORITY_DRIFT" in verdict["reason_codes"]


@pytest.mark.parametrize("actor", NON_HUMAN_ROLES)
@pytest.mark.parametrize("source", STATES)
def test_no_non_human_reaches_merged_from_anywhere(actor: str, source: str) -> None:
    """Not one route in, not merely the declared one."""

    assert evaluate(handoff(actor, source, "SHUKOU_MERGED"))["decision"] == REFUSED


# --------------------------------------------------------------------------- #
# Acceptance-owner drift
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("target", ["SHUKOU_CHECK", "SHUKOU_ACCEPTED", "SHUKOU_REJECTED"])
@pytest.mark.parametrize("actor", NON_HUMAN_ROLES)
def test_no_non_human_may_accept_or_reject(actor: str, target: str) -> None:
    verdict = evaluate(handoff(actor, "READY_FOR_SHUKOU_REVIEW", target))
    assert verdict["decision"] == REFUSED
    assert "ACCEPTANCE_OWNER_DRIFT" in verdict["reason_codes"]


@pytest.mark.parametrize("actor", NON_HUMAN_ROLES)
@pytest.mark.parametrize("target", STATES)
def test_the_executor_never_continues_past_its_terminal_state(actor: str, target: str) -> None:
    """``READY_FOR_SHUKOU_REVIEW`` is where the executor stops. Every onward step refused."""

    verdict = evaluate(handoff(actor, "READY_FOR_SHUKOU_REVIEW", target))
    assert verdict["decision"] == REFUSED, target
    assert "EXECUTOR_CONTINUED_PAST_TERMINAL_STATE" in verdict["reason_codes"]


# --------------------------------------------------------------------------- #
# Totality: no undeclared transition is ever permitted, by any actor
# --------------------------------------------------------------------------- #


DECLARED = {
    (transition["actor"], transition["from"], transition["to"])
    for transition in POLICY["handoff_transitions"]
}
ALL_TRIPLES = list(itertools.product(sorted(ROLES), STATES, STATES))
UNDECLARED = [triple for triple in ALL_TRIPLES if triple not in DECLARED]


def test_the_undeclared_inventory_is_large_enough_to_mean_something() -> None:
    assert len(UNDECLARED) >= 300, len(UNDECLARED)
    assert len(DECLARED) == len(POLICY["handoff_transitions"])


@pytest.mark.parametrize(
    "triple", UNDECLARED, ids=lambda triple: ":".join(str(part) for part in triple)
)
def test_no_undeclared_transition_is_permitted(triple: tuple[str, str, str]) -> None:
    actor, source, target = triple
    assert evaluate(handoff(actor, source, target))["decision"] == REFUSED


# --------------------------------------------------------------------------- #
# Fail closed on anything unreadable
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "record",
    [
        None,
        7,
        "READY_FOR_SHUKOU_REVIEW",
        [],
        {},
        {"record_type": "HANDOFF_TRANSITION"},
        {"record_type": "SOMETHING_ELSE", "actor": "SHUKOU"},
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": "CLAUDE_CODE",
            "from_state": "GITHUB_PR_READY",
            "to_state": "READY_FOR_SHUKOU_REVIEW",
            "note": "the bot said this was fine",
        },
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": "CODEX",
            "from_state": "GITHUB_PR_READY",
            "to_state": "READY_FOR_SHUKOU_REVIEW",
        },
    ],
)
def test_an_unreadable_record_is_refused_rather_than_skipped(record: Any) -> None:
    """"We could not tell" and "it is allowed" are the same outcome to a caller.

    An unknown actor is in this list on purpose: an external reviewer is not a participant,
    and a record naming one is not a transition it may take.
    """

    assert evaluate(record)["decision"] == REFUSED
