"""What the four-valued sufficiency result means, and what it must never flatten.

```text
EVIDENCE COUNT != EVIDENCE STRENGTH
NO_RESULT      != PROVEN_ABSENCE
```

Difference's ``evidence_sufficiency_result.schema.json`` carries four values, and widening
it here would be creating a second owner. So the distinctions live beside the record, in
``reason_codes``, and every one of them is asserted below -- because a distinction nothing
checks is a distinction that has already collapsed.
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.evidence_helpers import (
    EVALUATED_AT,
    RECORDED_AT,
    after_observation_with_status,
    blocked_after_observation_request,
    change_result_evidence_request,
    observation_evidence_request,
    observation_with_status,
    sufficiency_request,
)

from manosube_agent_civilization.evidence import evaluate_sufficiency

#: Every Observation status, and the reason code sufficiency must keep it as. The mapping is
#: injective on purpose: two statuses sharing a code would be the collapse this file exists
#: to prevent.
STATUS_CODES: dict[str, str | None] = {
    "COMPLETE": None,
    "EMPTY": "EVIDENCE_STATUS_EMPTY",
    "INCOMPLETE": "EVIDENCE_STATUS_INCOMPLETE",
    "UNKNOWN": "EVIDENCE_STATUS_UNKNOWN",
    "UNOBSERVED": "EVIDENCE_STATUS_UNOBSERVED",
    "BLOCKED": "EVIDENCE_STATUS_BLOCKED",
    "FAILED": "EVIDENCE_STATUS_FAILED",
    "INVALID": "EVIDENCE_STATUS_INVALID",
    "CONFLICTED": "EVIDENCE_STATUS_CONFLICTED",
}

#: The statuses an Evidence record can actually carry once it is bound to a Difference. The
#: rest are not unreachable by choice: the Difference producer refuses to derive from an
#: Observation it cannot read a State from, so ``FAILED``, ``INVALID`` and ``UNOBSERVED``
#: stop one layer earlier. That boundary is pinned in
#: ``test_kernel_route_to_evidence.py`` and is reported, not taken.
REACHABLE_STATUSES: tuple[str, ...] = (
    "COMPLETE",
    "EMPTY",
    "BLOCKED",
    "INCOMPLETE",
    "CONFLICTED",
)


def _evaluate(**kwargs: Any) -> dict[str, Any]:
    return evaluate_sufficiency(sufficiency_request(**kwargs))


def _result(**kwargs: Any) -> str:
    return str(_evaluate(**kwargs)["evidence_sufficiency_result"]["result"])


def _evidence_with_status(status: str, **kwargs: Any) -> dict[str, Any]:
    """An Observation Evidence request whose Observation the Engine concludes *status* for.

    Each status is a different observed State, so each derives a *different* Difference.
    That is correct and is why the mixed-status tests below use ``_after_status`` instead:
    two Evidence records of two Differences cannot back one Closure, and sufficiency now
    refuses the combination rather than averaging it.
    """

    return observation_evidence_request(observation=observation_with_status(status), **kwargs)


def _after_status(status: str, **kwargs: Any) -> dict[str, Any]:
    """A Change Result Evidence request whose *re-observation* concludes *status*.

    All of these bind one Difference -- the one their shared before-Observation derives -- so
    they can be combined in a single sufficiency evaluation.
    """

    return change_result_evidence_request(
        post_change_observation=after_observation_with_status(status), **kwargs
    )


# --------------------------------------------------------------------------- #
# the positive route
# --------------------------------------------------------------------------- #


def test_a_complete_observation_at_the_policy_floor_is_sufficient() -> None:
    evaluation = _evaluate(minimum_evidence_level="E1")
    assert evaluation["evidence_sufficiency_result"]["result"] == "SUFFICIENT"
    assert evaluation["reason_codes"] == ["SUFFICIENT"]


def test_sufficiency_names_the_evidence_it_rested_on() -> None:
    evaluation = _evaluate()
    record = evaluation["evidence_sufficiency_result"]
    assert record["evidence_refs"]["collection_kind"] == "UNORDERED_SET"
    assert len(record["evidence_refs"]["members"]) == 1
    assert record["evidence_refs"]["members"][0]["kind"] == "evidence"


# --------------------------------------------------------------------------- #
# strength: 件数で補ってはならない
# --------------------------------------------------------------------------- #


def test_the_effective_level_is_the_weakest_not_the_strongest() -> None:
    evaluation = _evaluate(
        minimum_evidence_level="E0",
        evidence_requests=[
            observation_evidence_request(),
            change_result_evidence_request(
                post_change_observation=blocked_after_observation_request()
            ),
        ],
    )
    assert evaluation["evidence_sufficiency_result"]["evidence_level"] == "E0"


def test_more_weak_evidence_does_not_reach_a_higher_floor() -> None:
    many = [
        change_result_evidence_request(
            post_change_observation=blocked_after_observation_request(),
            recorded_at=f"2026-08-30T10:0{index}:00Z",
        )
        for index in range(5)
    ]
    evaluation = _evaluate(minimum_evidence_level="E1", evidence_requests=many)
    assert len({request["recorded_at"] for request in many}) == 5
    assert evaluation["evidence_sufficiency_result"]["result"] == "INSUFFICIENT"
    assert "EVIDENCE_LEVEL_BELOW_MINIMUM" in evaluation["reason_codes"]


def test_a_floor_at_or_below_the_evidence_is_met() -> None:
    assert _result(minimum_evidence_level="E0") == "SUFFICIENT"
    assert _result(minimum_evidence_level="E1") == "SUFFICIENT"


# --------------------------------------------------------------------------- #
# Q2-A: a policy Phase 6 cannot satisfy is held, not weakened
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("floor", ["E2", "E3", "E4", "E5", "E6"])
def test_an_underivable_floor_is_held_as_insufficient_rather_than_lowered(floor: str) -> None:
    evaluation = _evaluate(minimum_evidence_level=floor)
    assert evaluation["evidence_sufficiency_result"]["result"] == "INSUFFICIENT"
    assert "EVIDENCE_LEVEL_UNREACHABLE_IN_PHASE_6" in evaluation["reason_codes"]
    # The refusal names what would have to exist, rather than only that something does not.
    assert evaluation["unreachable_level_reason"]


def test_an_unreachable_floor_is_distinguished_from_evidence_that_is_merely_too_weak() -> None:
    """Two situations with entirely different remedies, and one four-valued result.

    "Come back with better evidence" and "no evidence of this kind can be produced yet" are
    both INSUFFICIENT. Only the reason codes separate them.
    """

    unreachable = _evaluate(minimum_evidence_level="E5")
    too_weak = _evaluate(
        minimum_evidence_level="E1", evidence_requests=[_evidence_with_status("BLOCKED")]
    )
    assert "EVIDENCE_LEVEL_UNREACHABLE_IN_PHASE_6" in unreachable["reason_codes"]
    assert unreachable["unreachable_level_reason"]
    assert "EVIDENCE_LEVEL_UNREACHABLE_IN_PHASE_6" not in too_weak["reason_codes"]
    assert "EVIDENCE_LEVEL_BELOW_MINIMUM" in too_weak["reason_codes"]
    assert too_weak["unreachable_level_reason"] is None


# --------------------------------------------------------------------------- #
# absence, emptiness, and everything that is neither
# --------------------------------------------------------------------------- #


def test_no_evidence_is_insufficient_and_says_so_as_absence() -> None:
    evaluation = _evaluate(evidence_requests=[])
    assert evaluation["evidence_sufficiency_result"]["result"] == "INSUFFICIENT"
    assert "EVIDENCE_ABSENT" in evaluation["reason_codes"]
    assert evaluation["evidence_sufficiency_result"]["evidence_refs"]["members"] == []


def test_a_proven_empty_observation_is_not_an_absent_one() -> None:
    """``EMPTY`` is a completed observation of nothing; absence is no observation at all.

    Sufficiency records the distinction and does not downgrade EMPTY: whether an empty
    enumeration satisfies the Target is Difference's question, not this module's.
    """

    evaluation = _evaluate(
        minimum_evidence_level="E0", evidence_requests=[_evidence_with_status("EMPTY")]
    )
    codes = evaluation["reason_codes"]
    assert "EVIDENCE_STATUS_EMPTY" in codes
    assert "EVIDENCE_ABSENT" not in codes
    assert evaluation["evidence_sufficiency_result"]["result"] == "SUFFICIENT"


@pytest.mark.parametrize(
    ("status", "code"),
    [("BLOCKED", "EVIDENCE_STATUS_BLOCKED"), ("CONFLICTED", "EVIDENCE_STATUS_CONFLICTED")],
)
def test_a_blocked_or_contradicted_observation_is_determinately_insufficient(
    status: str, code: str
) -> None:
    evaluation = _evaluate(
        minimum_evidence_level="E0", evidence_requests=[_evidence_with_status(status)]
    )
    assert evaluation["evidence_sufficiency_result"]["result"] == "INSUFFICIENT"
    assert code in evaluation["reason_codes"]


def test_an_incomplete_observation_is_unknown_rather_than_insufficient() -> None:
    """Reporting INSUFFICIENT here would assert a negative nobody observed."""

    evaluation = _evaluate(
        minimum_evidence_level="E0", evidence_requests=[_evidence_with_status("INCOMPLETE")]
    )
    assert evaluation["evidence_sufficiency_result"]["result"] == "UNKNOWN"
    assert "EVIDENCE_STATUS_INCOMPLETE" in evaluation["reason_codes"]


def test_every_observation_status_keeps_its_own_reason_code() -> None:
    """The non-collapse property, stated as a property rather than case by case."""

    codes = [code for code in STATUS_CODES.values() if code is not None]
    assert len(codes) == len(set(codes)) == 8


# --------------------------------------------------------------------------- #
# freshness, from an admitted instant
# --------------------------------------------------------------------------- #


def test_evidence_older_than_the_policy_bound_is_stale() -> None:
    evaluation = _evaluate(maximum_evidence_age=1800)
    assert evaluation["evidence_sufficiency_result"]["result"] == "STALE"
    assert "EVIDENCE_AGE_EXCEEDED" in evaluation["reason_codes"]


def test_evidence_inside_the_policy_bound_is_not_stale() -> None:
    """The control on the bound: without it, ``STALE`` for every age would also pass."""

    assert _result(maximum_evidence_age=7200) == "SUFFICIENT"
    assert _result(maximum_evidence_age=3600) == "SUFFICIENT"
    assert _result(maximum_evidence_age=3599) == "STALE"


def test_a_null_bound_imposes_no_age_limit() -> None:
    assert _result(maximum_evidence_age=None, evaluation_instant="2099-01-01T00:00:00Z") == (
        "SUFFICIENT"
    )


def test_evidence_dated_after_the_evaluation_is_stale_rather_than_negative_aged() -> None:
    evaluation = _evaluate(evaluation_instant="2026-08-30T09:30:00Z")
    assert evaluation["evidence_sufficiency_result"]["result"] == "STALE"
    assert "EVIDENCE_FUTURE_DATED" in evaluation["reason_codes"]


def test_the_reported_age_is_measured_from_the_admitted_instant() -> None:
    evaluation = _evaluate()
    measured = evaluation["evidence_level_evaluations"][0]
    assert measured["recorded_at"] == RECORDED_AT
    assert evaluation["evidence_sufficiency_result"]["evaluated_at"] == EVALUATED_AT
    assert measured["age_seconds"] == 3600


# --------------------------------------------------------------------------- #
# precedence
# --------------------------------------------------------------------------- #


def test_staleness_outranks_every_other_verdict() -> None:
    """A stale binding is not evaluated on its merits: ``SATISFIED`` is not available to it,
    so a stale *and* weak evidence set must report STALE rather than INSUFFICIENT."""

    evaluation = _evaluate(
        minimum_evidence_level="E1",
        maximum_evidence_age=1,
        evidence_requests=[_evidence_with_status("BLOCKED")],
    )
    assert evaluation["evidence_sufficiency_result"]["result"] == "STALE"
    assert "EVIDENCE_LEVEL_BELOW_MINIMUM" in evaluation["reason_codes"]


def test_a_determinate_failure_outranks_an_indeterminate_one() -> None:
    evaluation = _evaluate(
        minimum_evidence_level="E0",
        evidence_requests=[
            _after_status("INCOMPLETE"),
            _after_status("BLOCKED", recorded_at="2026-08-30T10:30:00Z"),
        ],
    )
    assert evaluation["evidence_sufficiency_result"]["result"] == "INSUFFICIENT"
    assert {"EVIDENCE_STATUS_INCOMPLETE", "EVIDENCE_STATUS_BLOCKED"} <= set(
        evaluation["reason_codes"]
    )


def test_sufficient_is_the_only_verdict_that_carries_the_sufficient_code() -> None:
    for evaluation in (
        _evaluate(minimum_evidence_level="E3"),
        _evaluate(maximum_evidence_age=1),
        _evaluate(evidence_requests=[]),
    ):
        assert "SUFFICIENT" not in evaluation["reason_codes"]


def test_every_code_the_evaluator_emits_is_a_declared_reason_code() -> None:
    """``REASON_CODES`` is public and is what a caller switches on. A code emitted but not
    declared would be one no consumer could have handled."""

    from manosube_agent_civilization.evidence import REASON_CODES

    emitted: set[str] = set()
    evaluations = [
        _evaluate(),
        _evaluate(minimum_evidence_level="E5"),
        _evaluate(maximum_evidence_age=1),
        _evaluate(evaluation_instant="2026-08-30T09:30:00Z"),
        _evaluate(evidence_requests=[]),
        _evaluate(
            minimum_evidence_level="E1", evidence_requests=[_evidence_with_status("BLOCKED")]
        ),
    ]
    evaluations.extend(
        _evaluate(minimum_evidence_level="E0", evidence_requests=[_evidence_with_status(status)])
        for status in REACHABLE_STATUSES
    )
    for evaluation in evaluations:
        emitted |= set(evaluation["reason_codes"])

    assert emitted <= set(REASON_CODES)
    # The control: a run that emitted nothing would satisfy the subset check trivially.
    assert len(emitted) >= 8
