"""The seven refusals Decision 0002 requires, and the positive route beside them.

Each of the first five is a **policy artifact edited across a boundary**, and each was
accepted by the first implementation. That version validated that ``may`` and ``must_not``
were lists of unique strings and never that they were *the ratified* lists, so moving a
Human-only action into a non-Human ``may`` loaded cleanly and the evaluator then answered
``PERMITTED``.

```text
SHAPE VALIDATED != CONTENT PINNED
```

The last two are orderings: a recommendation that skipped the review, and a merge that
skipped the acceptance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from manosube_agent_civilization.development_binding import (
    PERMITTED,
    REFUSED,
    PolicyIntegrityError,
    evaluate,
    load_policy,
)
from manosube_agent_civilization.development_binding.policy import (
    EXECUTOR,
    HUMAN_AUTHORITY,
    POLICY_PATH,
    STRUCTURAL_ADVISOR,
)

pytestmark = pytest.mark.integration

POLICY = load_policy()


def _written(tmp_path: Path, mutate: Any) -> Path:
    document = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    mutate(document)
    target = tmp_path / "policy.json"
    target.write_text(json.dumps(document), encoding="utf-8")
    return target


def handoff(actor: str, source: str, target: str) -> dict[str, Any]:
    return {
        "record_type": "HANDOFF_TRANSITION",
        "actor": actor,
        "from_state": source,
        "to_state": target,
    }


# --------------------------------------------------------------------------- #
# 1. ChatGPT granted final acceptance or merge operation
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("granted", ["FINAL_ACCEPTANCE_DECISION", "MERGE_OPERATION"])
def test_the_advisor_cannot_be_granted_a_human_only_action(
    tmp_path: Path, granted: str
) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["roles"][STRUCTURAL_ADVISOR]["must_not"].remove(granted)
        document["roles"][STRUCTURAL_ADVISOR]["may"].append(granted)

    with pytest.raises(PolicyIntegrityError, match="ratified set"):
        load_policy(_written(tmp_path, mutate))


@pytest.mark.parametrize("granted", ["FINAL_ACCEPTANCE_DECISION", "MERGE_OPERATION"])
def test_the_advisor_is_refused_a_human_only_action_at_evaluation(granted: str) -> None:
    """Even against the honest policy, the action itself is refused."""

    verdict = evaluate(
        {"record_type": "ACTOR_ACTION", "actor": STRUCTURAL_ADVISOR, "action": granted}
    )
    assert verdict["decision"] == REFUSED
    assert "ROLE_DRIFT" in verdict["reason_codes"]


# --------------------------------------------------------------------------- #
# 2. Claude Code granted review, recommendation, acceptance or merge
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "granted",
    [
        "STRUCTURAL_REVIEW",
        "MERGE_READINESS_RECOMMENDATION",
        "FINAL_ACCEPTANCE_DECISION",
        "MERGE_OPERATION",
    ],
)
def test_the_executor_cannot_be_granted_a_role_it_does_not_hold(
    tmp_path: Path, granted: str
) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["roles"][EXECUTOR]["must_not"].remove(granted)
        document["roles"][EXECUTOR]["may"].append(granted)

    with pytest.raises(PolicyIntegrityError, match="ratified set"):
        load_policy(_written(tmp_path, mutate))


@pytest.mark.parametrize(
    "granted",
    [
        "STRUCTURAL_REVIEW",
        "MERGE_READINESS_RECOMMENDATION",
        "FINAL_ACCEPTANCE_DECISION",
        "MERGE_OPERATION",
    ],
)
def test_the_executor_is_refused_those_actions_at_evaluation(granted: str) -> None:
    verdict = evaluate({"record_type": "ACTOR_ACTION", "actor": EXECUTOR, "action": granted})
    assert verdict["decision"] == REFUSED
    assert "ROLE_DRIFT" in verdict["reason_codes"]


# --------------------------------------------------------------------------- #
# 3. human_only_states emptied or reduced
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "replacement",
    [[], ["SHUKOU_MERGED"], ["SHUKOU_ACCEPTED"], ["SHUKOU_ACCEPTED", "SHUKOU_REJECTED"]],
    ids=["emptied", "merged-only", "accepted-only", "missing-merged"],
)
def test_the_human_only_state_set_cannot_be_weakened(
    tmp_path: Path, replacement: list[str]
) -> None:
    """An empty list was accepted by the first version: a loop over nothing raises nothing."""

    def mutate(document: dict[str, Any]) -> None:
        document["human_only_states"] = replacement

    with pytest.raises(PolicyIntegrityError, match="human-only states"):
        load_policy(_written(tmp_path, mutate))


def test_the_advisor_only_state_set_cannot_be_weakened(tmp_path: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["advisor_only_states"] = []

    with pytest.raises(PolicyIntegrityError, match="advisor-only states"):
        load_policy(_written(tmp_path, mutate))


# --------------------------------------------------------------------------- #
# 4. a non-Human transition inserted into acceptance or merged
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("actor", [STRUCTURAL_ADVISOR, EXECUTOR, "GITHUB"])
@pytest.mark.parametrize("target", ["SHUKOU_ACCEPTED", "SHUKOU_MERGED"])
def test_a_non_human_transition_into_a_human_state_cannot_be_inserted(
    tmp_path: Path, actor: str, target: str
) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["handoff_transitions"].append(
            {"from": "GITHUB_PR_READY", "to": target, "actor": actor}
        )

    with pytest.raises(PolicyIntegrityError, match="ratified set"):
        load_policy(_written(tmp_path, mutate))


def test_a_declared_transition_cannot_be_removed_either(tmp_path: Path) -> None:
    """Pinned whole. Deleting the Human's merge step is as much a change as adding one."""

    def mutate(document: dict[str, Any]) -> None:
        document["handoff_transitions"] = [
            transition
            for transition in document["handoff_transitions"]
            if transition["to"] != "SHUKOU_MERGED"
        ]

    with pytest.raises(PolicyIntegrityError, match="ratified set"):
        load_policy(_written(tmp_path, mutate))


@pytest.mark.parametrize("owner_field", sorted(
    {
        "structural_review_owner",
        "merge_readiness_recommendation_owner",
        "final_acceptance_owner",
        "merge_operation_owner",
        "external_finding_adoption_authority",
    }
))
def test_no_owner_field_can_be_reassigned(tmp_path: Path, owner_field: str) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document[owner_field] = "CODEX"

    with pytest.raises(PolicyIntegrityError):
        load_policy(_written(tmp_path, mutate))


# --------------------------------------------------------------------------- #
# 5. record fields arriving as arrays or objects
# --------------------------------------------------------------------------- #


_ILL_TYPED: tuple[Any, ...] = ([], ["SHUKOU"], {}, {"actor": "SHUKOU"}, 7, True, None)


@pytest.mark.parametrize("value", _ILL_TYPED, ids=lambda value: repr(value))
@pytest.mark.parametrize("field", ["record_type", "actor", "from_state", "to_state"])
def test_an_ill_typed_handoff_field_is_a_verdict_not_an_exception(
    field: str, value: Any
) -> None:
    record = handoff(EXECUTOR, "GITHUB_PR_READY", "READY_FOR_STRUCTURAL_REVIEW")
    record[field] = value
    verdict = evaluate(record)
    assert verdict["decision"] == REFUSED
    assert "RECORD_FIELD_IS_NOT_A_SCALAR" in verdict["reason_codes"]


@pytest.mark.parametrize("value", _ILL_TYPED, ids=lambda value: repr(value))
def test_an_ill_typed_finding_is_a_verdict_not_an_exception(value: Any) -> None:
    verdict = evaluate(
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": EXECUTOR,
            "finding": {"observation_id": value, "source": "CODEX", "status": "UNVERIFIED_EXTERNAL_OBSERVATION"},
            "requested_disposition": "IMPLEMENTATION_INSTRUCTION",
            "adoption": None,
        }
    )
    assert verdict["decision"] == REFUSED


@pytest.mark.parametrize("value", _ILL_TYPED, ids=lambda value: repr(value))
def test_an_ill_typed_adoption_is_a_verdict_not_an_exception(value: Any) -> None:
    verdict = evaluate(
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": EXECUTOR,
            "finding": {
                "observation_id": "OBS-1",
                "source": "CODEX",
                "status": "UNVERIFIED_EXTERNAL_OBSERVATION",
            },
            "requested_disposition": "IMPLEMENTATION_INSTRUCTION",
            "adoption": {"authority": value, "observation_id": "OBS-1", "disposition": "IMPLEMENTATION_INSTRUCTION"},
        }
    )
    assert verdict["decision"] == REFUSED


def test_no_evaluation_input_raises_at_all() -> None:
    """The property the reason codes above depend on, asserted directly.

    A caller that reads verdicts and a caller that catches exceptions are different callers,
    and the first must never be told "allowed" by silence.
    """

    hostile: list[Any] = [
        None, 7, "x", [], {}, {"record_type": []}, {"record_type": {}},
        {"record_type": "HANDOFF_TRANSITION", "actor": [], "from_state": {}, "to_state": 7},
        {"record_type": "ACTOR_ACTION", "actor": {}, "action": []},
        {"record_type": "EXTERNAL_FINDING_DISPOSITION", "actor": [], "finding": [],
         "requested_disposition": {}, "adoption": 7},
    ]
    for record in hostile:
        verdict = evaluate(record)
        assert verdict["decision"] == REFUSED, record


# --------------------------------------------------------------------------- #
# 6. structural review skipped before MERGE_RECOMMENDED
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "source",
    [state for state in POLICY["handoff_states"] if state != "STRUCTURAL_REVIEW_PASS"],
)
def test_merge_cannot_be_recommended_without_a_review_pass(source: str) -> None:
    verdict = evaluate(handoff(STRUCTURAL_ADVISOR, source, "MERGE_RECOMMENDED"))
    assert verdict["decision"] == REFUSED
    assert "STRUCTURAL_REVIEW_SKIPPED" in verdict["reason_codes"]


def test_the_review_running_state_cannot_be_jumped(tmp_path: Path) -> None:
    """Going straight from the executor's terminal state to a pass skips the review itself."""

    verdict = evaluate(
        handoff(STRUCTURAL_ADVISOR, "READY_FOR_STRUCTURAL_REVIEW", "STRUCTURAL_REVIEW_PASS")
    )
    assert verdict["decision"] == REFUSED
    assert "TRANSITION_NOT_DECLARED" in verdict["reason_codes"]


# --------------------------------------------------------------------------- #
# 7. merge attempted from MERGE_RECOMMENDED without Shukou acceptance
# --------------------------------------------------------------------------- #


def test_merge_cannot_follow_a_recommendation_directly() -> None:
    """The separation Decision 0002 exists for: a recommendation is not an acceptance."""

    verdict = evaluate(handoff(HUMAN_AUTHORITY, "MERGE_RECOMMENDED", "SHUKOU_MERGED"))
    assert verdict["decision"] == REFUSED
    assert "MERGE_WITHOUT_FINAL_ACCEPTANCE" in verdict["reason_codes"]


@pytest.mark.parametrize(
    "source", [state for state in POLICY["handoff_states"] if state != "SHUKOU_ACCEPTED"]
)
def test_merge_follows_final_acceptance_and_nothing_else(source: str) -> None:
    verdict = evaluate(handoff(HUMAN_AUTHORITY, source, "SHUKOU_MERGED"))
    assert verdict["decision"] == REFUSED
    assert "MERGE_WITHOUT_FINAL_ACCEPTANCE" in verdict["reason_codes"]


# --------------------------------------------------------------------------- #
# The positive route, so none of the above passes vacuously
# --------------------------------------------------------------------------- #


def test_the_ratified_route_runs_end_to_end() -> None:
    route = [
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
    for actor, source, target in route:
        assert evaluate(handoff(actor, source, target))["decision"] == PERMITTED, (
            actor,
            source,
            target,
        )


def test_each_owner_may_do_its_own_owned_action() -> None:
    """The three actions Decision 0002 separated, each permitted to exactly its owner."""

    for owner, action in (
        (STRUCTURAL_ADVISOR, "STRUCTURAL_REVIEW"),
        (STRUCTURAL_ADVISOR, "MERGE_READINESS_RECOMMENDATION"),
        (HUMAN_AUTHORITY, "FINAL_ACCEPTANCE_DECISION"),
        (HUMAN_AUTHORITY, "MERGE_OPERATION"),
    ):
        verdict = evaluate(
            {"record_type": "ACTOR_ACTION", "actor": owner, "action": action}
        )
        assert verdict["decision"] == PERMITTED, (owner, action)


def test_the_unpinned_policy_is_the_one_that_actually_loads() -> None:
    """A control on every `load_policy` refusal above: the shipped artifact still loads."""

    assert load_policy()["decision_id"].endswith("0002")
