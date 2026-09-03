"""The ratified FAILED route, end to end, through nothing but the public owners.

```text
observe()            FAILED Observation
derive_differences() UNKNOWN Difference
derive_evidence()    FAILED / E0 Observation Evidence
evaluate_sufficiency()  INSUFFICIENT
derive_differences()    the result carried back, unchanged
```

Structural review of ``370e705`` found no implementation defect and one proof gap, and the
distinction is the reason this file exists. ``test_failed_observation_route.py`` calls
``validate_emitted_bundle`` and ``reference_closure_errors`` on a bundle it assembled itself.
Those are the right gates and they pass -- but running a gate is not the same as running the
**route**, and only the route can show that a real predecessor carrying a real sufficiency
result survives a real re-derivation.

The standard COMPLETE route had that proof (``test_difference_round_trip.py``). The FAILED
route had it demonstrated ad hoc and never committed, which Issue #37 is explicit is not
Repository Evidence. So it is committed here, with the two ratified prohibitions asserted
directly rather than inferred:

```text
CLOSED lifecycle event count = 0
candidate_completion_records = []
materialized status          = OPEN
```
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from tests.difference_helpers import (
    negative_claim,
    observation_request,
    observation_scope,
    state_fingerprint,
)
from tests.evidence_helpers import (
    BEFORE_REVISION,
    difference_request,
    observation_evidence_request,
    sufficiency_request,
)

from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.evidence import derive_evidence, evaluate_sufficiency
from manosube_agent_civilization.observation import observe

#: The failure class the Observation carries. Asserted by identity below, not by shape: a
#: test that only checked "some failure class is present" would pass on a blank one.
FAILURE_CLASS = "SOURCE_ERROR"
ATTEMPT_ID = "ATTEMPT-0001"


def _failed_observation_request() -> dict[str, Any]:
    request = observation_request(
        observation_scope(),
        [],
        state_fingerprint(),
        BEFORE_REVISION,
        negative_claims=[negative_claim("FAILED")],
    )
    request["attempts"][0]["result"] = "FAILED"
    request["attempts"][0]["failure_class"] = FAILURE_CLASS
    return request


def _first_derivation() -> dict[str, Any]:
    """Step 1 and 2, through the public owners and nothing else."""

    request = difference_request()
    request["bindings"][0]["observation_bundle"] = observe(_failed_observation_request())
    return derive_differences(request)


def _sufficiency(first: dict[str, Any]) -> dict[str, Any]:
    """Steps 3 and 4. The policy is the one the Difference producer emitted."""

    evaluation = evaluate_sufficiency(
        sufficiency_request(
            difference_id=first["differences"][0]["difference_id"],
            policy=first["policies"][0],
            evidence_requests=[
                observation_evidence_request(observation=_failed_observation_request())
            ],
        )
    )
    result: dict[str, Any] = evaluation["evidence_sufficiency_result"]
    return result


def _re_derivation(first: dict[str, Any], carried: dict[str, Any]) -> dict[str, Any]:
    """Steps 5 and 6: a real predecessor, back into the public consumer.

    The predecessor is the first derivation's own output -- its Difference, its events, its
    whole bundle as context -- with the produced sufficiency result added to the section that
    carries it. Nothing here is hand-assembled except that one insertion, which is the thing
    under test.
    """

    context = deepcopy(first)
    context["evidence_sufficiency_results"] = [deepcopy(carried)]

    later = difference_request()
    later["bindings"][0]["observation_bundle"] = observe(_failed_observation_request())
    later["bindings"][0]["predecessor"] = {
        "difference": deepcopy(first["differences"][0]),
        "events": deepcopy(first["events"]),
        "context": context,
    }
    return derive_differences(later)


@pytest.fixture(scope="module")
def route() -> dict[str, Any]:
    first = _first_derivation()
    carried = _sufficiency(first)
    return {"first": first, "carried": carried, "second": _re_derivation(first, carried)}


# --------------------------------------------------------------------------- #
# steps 1-4 -- what each public owner concluded
# --------------------------------------------------------------------------- #


def test_the_observation_engine_concludes_failed(route: dict[str, Any]) -> None:
    observation = route["first"]["observations"][-1]
    assert observation["status"] == "FAILED"


def test_the_difference_producer_projects_unknown(route: dict[str, Any]) -> None:
    difference = route["first"]["differences"][0]
    assert difference["normalized_observed_state"]["knowledge_status"] == "UNKNOWN"
    assert difference["structural_difference"]["comparison_result"] == "UNKNOWN"


def test_the_evidence_engine_produces_failed_at_e0(route: dict[str, Any]) -> None:
    record = derive_evidence(
        observation_evidence_request(observation=_failed_observation_request())
    )
    assert record["status"] == "FAILED"
    assert record["evidence_level"] == "E0"
    assert record["difference_ref"]["id"] == route["first"]["differences"][0]["difference_id"]


def test_the_sufficiency_evaluator_returns_insufficient(route: dict[str, Any]) -> None:
    assert route["carried"]["result"] == "INSUFFICIENT"
    assert route["carried"]["evidence_refs"]["members"]


# --------------------------------------------------------------------------- #
# steps 5-7 -- the round trip through the public consumer
# --------------------------------------------------------------------------- #


def test_the_result_survives_re_derivation_as_the_same_record(route: dict[str, Any]) -> None:
    """Step 7. Identity *and* content: a record carried back with a field altered would still
    have the same id, because the id is a digest over the record it was minted from."""

    carried_back = route["second"]["evidence_sufficiency_results"]
    assert carried_back == [route["carried"]]
    assert carried_back[0]["evidence_sufficiency_id"] == route["carried"]["evidence_sufficiency_id"]


def test_the_re_derivation_yields_the_same_difference(route: dict[str, Any]) -> None:
    """The predecessor and the re-derivation are about one Difference, or the round trip is
    carrying a record from somewhere else."""

    assert (
        route["second"]["differences"][0]["difference_id"]
        == route["first"]["differences"][0]["difference_id"]
    )


# --------------------------------------------------------------------------- #
# step 8 -- the failure lineage resolves across all four records
# --------------------------------------------------------------------------- #


def test_the_attempt_resolves_from_the_negative_observation(route: dict[str, Any]) -> None:
    """The link the previous round's tests did not make.

    Round 4 checked ``result``/``failure_class`` on the Observation and ``attempt_outcomes``
    on the Evidence, separately. Neither showed that the Negative Observation is about *this*
    attempt -- so a Negative Observation citing some other attempt would have passed.
    """

    observation = route["second"]["observations"][-1]
    negative = route["second"]["negative_observations"][0]

    assert [
        (item["attempt_id"], item["result"], item["failure_class"])
        for item in observation["attempts"]
    ] == [(ATTEMPT_ID, "FAILED", FAILURE_CLASS)]
    assert negative["attempt_refs"] == [{"kind": "observation_attempt", "id": ATTEMPT_ID}]
    assert negative["observation_id"] == observation["observation_id"]
    assert negative["negative_status"] == "FAILED"


def test_the_evidence_resolves_to_that_observation_and_that_difference(
    route: dict[str, Any],
) -> None:
    record = derive_evidence(
        observation_evidence_request(observation=_failed_observation_request())
    )
    observation = route["first"]["observations"][-1]
    difference = route["first"]["differences"][0]

    assert record["observed_result"]["observation_ref"] == {
        "kind": "observation",
        "id": observation["observation_id"],
    }
    assert {
        "kind": "observation",
        "id": observation["observation_id"],
    } in record["lineage"]["derived_from"]["members"]
    assert {
        "kind": "difference",
        "id": difference["difference_id"],
    } in record["lineage"]["derived_from"]["members"]


def test_the_sufficiency_result_resolves_to_that_evidence(route: dict[str, Any]) -> None:
    record = derive_evidence(
        observation_evidence_request(observation=_failed_observation_request())
    )
    assert [member["id"] for member in route["carried"]["evidence_refs"]["members"]] == [
        record["evidence_id"]
    ]
    assert (
        route["carried"]["difference_ref"]["id"]
        == route["first"]["differences"][0]["difference_id"]
    )


# --------------------------------------------------------------------------- #
# step 9 -- the ratified prohibitions, asserted rather than inferred
# --------------------------------------------------------------------------- #


def test_the_failure_closes_nothing(route: dict[str, Any]) -> None:
    """``FAILED Evidence must not become CLOSED or a completion.``

    Round 4 proved the two upstream facts -- UNKNOWN is not evaluable knowledge, FAILED
    Evidence is never SUFFICIENT -- and left the conclusion to follow from them. It does
    follow, and it is still worth pinning: an inference is not a regression test, and the
    thing a regression would break is the conclusion.
    """

    for bundle in (route["first"], route["second"]):
        assert set(bundle["materialized_status"].values()) == {"OPEN"}
        assert [event for event in bundle["events"] if event.get("to_status") == "CLOSED"] == []
        assert bundle["candidate_completion_records"] == []
        assert bundle["evaluations"] == []


def test_no_lifecycle_event_reaches_a_terminal_status(route: dict[str, Any]) -> None:
    terminal = {"CLOSED", "RETAINED", "SUPERSEDED"}
    reached = {
        event.get("to_status")
        for bundle in (route["first"], route["second"])
        for event in bundle["events"]
    }
    assert reached & terminal == set()
    assert reached == {"DETECTED", "OPEN"}


# --------------------------------------------------------------------------- #
# step 10 -- the negative control, on the same public route
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("kind", ["evidence", "observation", "negative_observation"])
def test_a_wrong_reference_kind_is_refused_by_the_public_consumer(
    kind: str, route: dict[str, Any]
) -> None:
    """The control that makes every assertion above mean something.

    It runs through ``derive_differences`` rather than through ``reference_closure_errors``
    directly, because the claim being controlled is about the *route*. ``evidence`` is first:
    it is the tag round 3 found, and this is the public-route regression for it.
    """

    forged = deepcopy(route["carried"])
    for member in forged["evidence_refs"]["members"]:
        member["kind"] = kind

    with pytest.raises(DifferenceError) as raised:
        _re_derivation(route["first"], forged)
    assert "reference" in str(raised.value)


def test_the_control_and_the_positive_case_differ_only_in_that_tag(
    route: dict[str, Any],
) -> None:
    """Without this, the refusal above could be caused by anything the forgery also changed."""

    forged = deepcopy(route["carried"])
    for member in forged["evidence_refs"]["members"]:
        member["kind"] = "evidence"

    honest = deepcopy(route["carried"])
    assert forged != honest
    for member in forged["evidence_refs"]["members"]:
        member["kind"] = "observation_evidence"
    assert forged == honest
