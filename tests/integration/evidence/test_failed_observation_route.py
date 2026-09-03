"""A failed observation reflows as Evidence, without becoming a success on the way.

第31条 requires failure, EMPTY, BLOCKED, STALE and non-arrival to reflow as formal Evidence.
Binding Evidence to a Difference (ADR-0029 §1A) made that impossible for an *initial* FAILED
Observation, because the Difference producer refused the status outright:

```text
FAILED Observation -> Difference producer refuses -> no Observation Evidence anywhere
```

That was a constitutional contradiction, not a missing feature, and Phase 6 held it rather
than resolving it on its own authority. The Human Authority ratified the amendment recorded
in ADR-0030: admit ``FAILED``, project it as ``UNKNOWN``, keep refusing ``INVALID``, and let
Evidence reach it only through the Difference.

Everything below is the ratified decision, asserted as behaviour.
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
from manosube_agent_civilization.difference.conformance import validate_emitted_bundle
from manosube_agent_civilization.difference.engine import _ACCEPTED_OBSERVATION_STATUS
from manosube_agent_civilization.difference.graph import reference_closure_errors
from manosube_agent_civilization.difference.projection import (
    _NEGATIVE_STATUS_MAP,
    EVALUABLE_KNOWLEDGE,
    PROVEN_ABSENCE,
    UNRESOLVED_KNOWLEDGE,
)
from manosube_agent_civilization.evidence import (
    CHANGE_RESULT_EVIDENCE,
    OBSERVATION_EVIDENCE,
    EvidenceError,
    derive_evidence,
    evaluate_sufficiency,
)
from manosube_agent_civilization.observation import observe


def _failed_observation_request(claim: str = "FAILED") -> dict[str, Any]:
    """An Observation the Engine itself rules FAILED, with its failure class intact."""

    request = observation_request(
        observation_scope(),
        [],
        state_fingerprint(),
        BEFORE_REVISION,
        negative_claims=[negative_claim(claim)],
    )
    request["attempts"][0]["result"] = "FAILED"
    request["attempts"][0]["failure_class"] = "SOURCE_ERROR"
    return request


@pytest.fixture(scope="module")
def failed_evidence() -> dict[str, Any]:
    record: dict[str, Any] = derive_evidence(
        observation_evidence_request(observation=_failed_observation_request())
    )
    return record


# --------------------------------------------------------------------------- #
# the amendment is exactly one status
# --------------------------------------------------------------------------- #


def test_the_amendment_admits_failed_and_nothing_else() -> None:
    """One status, named. An amendment that quietly widened further would be a different
    decision than the one ratified."""

    assert (
        frozenset(
            {
                "COMPLETE",
                "EMPTY",
                "UNKNOWN",
                "UNOBSERVED",
                "BLOCKED",
                "INCOMPLETE",
                "CONFLICTED",
                "FAILED",
            }
        )
        == _ACCEPTED_OBSERVATION_STATUS
    )
    assert "INVALID" not in _ACCEPTED_OBSERVATION_STATUS


def test_the_projection_it_reaches_was_already_canonical() -> None:
    """The amendment invents no semantics: it lets the gate reach a map that already existed.

    ``_NEGATIVE_STATUS_MAP`` declared ``FAILED -> UNKNOWN`` and
    ``INVALID -> REJECT_OR_QUARANTINE`` before this work unit. The gate refused before either
    was ever consulted.
    """

    assert _NEGATIVE_STATUS_MAP["FAILED"] == "UNKNOWN"
    assert _NEGATIVE_STATUS_MAP["INVALID"] == "REJECT_OR_QUARANTINE"


def test_unknown_cannot_become_satisfaction_absence_or_completion() -> None:
    """Why UNKNOWN is a safe projection, as set membership rather than as a promise."""

    assert "UNKNOWN" in UNRESOLVED_KNOWLEDGE
    assert "UNKNOWN" not in EVALUABLE_KNOWLEDGE
    assert "UNKNOWN" not in PROVEN_ABSENCE


# --------------------------------------------------------------------------- #
# the route
# --------------------------------------------------------------------------- #


def test_a_failed_observation_now_reaches_evidence_as_failed_at_e0(
    failed_evidence: dict[str, Any],
) -> None:
    assert failed_evidence["evidence_position"] == OBSERVATION_EVIDENCE
    assert failed_evidence["status"] == "FAILED"
    assert failed_evidence["evidence_level"] == "E0"


def test_the_difference_projects_the_failure_as_unknown() -> None:
    request = difference_request()
    request["bindings"][0]["observation_bundle"] = observe(_failed_observation_request())
    derived = derive_differences(request)["differences"][0]
    assert derived["normalized_observed_state"]["knowledge_status"] == "UNKNOWN"
    assert derived["structural_difference"]["comparison_result"] == "UNKNOWN"


def test_the_failure_itself_is_preserved_and_not_replaced_by_the_projection() -> None:
    """The projection is UNKNOWN; the record still says FAILED, and says why.

    A projection that overwrote the attempt outcome or the failure class would be the
    collapse ``NO_RESULT != PROVEN_ABSENCE`` forbids, arriving from the other direction: not
    a failure promoted to a result, but a failure erased into a shrug.
    """

    request = difference_request()
    request["bindings"][0]["observation_bundle"] = observe(_failed_observation_request())
    bundle = derive_differences(request)

    carried = bundle["observations"][-1]
    assert carried["status"] == "FAILED"
    assert [(item["result"], item["failure_class"]) for item in carried["attempts"]] == [
        ("FAILED", "SOURCE_ERROR")
    ]
    assert [item["negative_status"] for item in bundle["negative_observations"]] == ["FAILED"]


def test_the_evidence_carries_the_failure_forward(failed_evidence: dict[str, Any]) -> None:
    assert failed_evidence["observed_result"]["observation_status"] == "FAILED"
    assert failed_evidence["observed_result"]["attempt_outcomes"]["members"] == ["FAILED"]


def test_the_evidence_did_not_bypass_the_difference(failed_evidence: dict[str, Any]) -> None:
    """``EVIDENCE_MUST_NOT_BYPASS_DIFFERENCE=true``. The record names a Difference that was
    derived, by its own producer, from this failed Observation."""

    request = difference_request()
    request["bindings"][0]["observation_bundle"] = observe(_failed_observation_request())
    derived = derive_differences(request)["differences"][0]
    assert failed_evidence["difference_ref"] == {
        "kind": "difference",
        "id": derived["difference_id"],
    }


def test_no_third_evidence_position_was_created(failed_evidence: dict[str, Any]) -> None:
    """``THIRD_EVIDENCE_POSITION_CREATED=false``. 第27条 still has exactly two positions, and
    a failure is recorded in the first of them."""

    from manosube_agent_civilization.evidence.engine import (
        CHANGE_RESULT_EVIDENCE as change_position,
        OBSERVATION_EVIDENCE as observation_position,
    )

    assert {observation_position, change_position} == {
        OBSERVATION_EVIDENCE,
        CHANGE_RESULT_EVIDENCE,
    }
    assert failed_evidence["evidence_position"] == OBSERVATION_EVIDENCE


# --------------------------------------------------------------------------- #
# failure does not become sufficiency
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("floor", ["E0", "E1", "E2", "E3", "E4", "E5", "E6"])
def test_failed_evidence_is_never_sufficient_at_any_floor(floor: str) -> None:
    evaluation = evaluate_sufficiency(
        sufficiency_request(
            minimum_evidence_level=floor,
            evidence_requests=[
                observation_evidence_request(observation=_failed_observation_request())
            ],
        )
    )
    assert evaluation["evidence_sufficiency_result"]["result"] == "INSUFFICIENT"
    assert "EVIDENCE_STATUS_FAILED" in evaluation["reason_codes"]
    assert "SUFFICIENT" not in evaluation["reason_codes"]


def test_the_control_that_the_same_route_can_reach_sufficient() -> None:
    """Without this, "never SUFFICIENT" would also hold for a route that never works."""

    evaluation = evaluate_sufficiency(sufficiency_request(minimum_evidence_level="E1"))
    assert evaluation["evidence_sufficiency_result"]["result"] == "SUFFICIENT"


# --------------------------------------------------------------------------- #
# INVALID, refused twice over
# --------------------------------------------------------------------------- #


def test_an_invalid_negative_observation_is_still_refused() -> None:
    with pytest.raises(EvidenceError) as raised:
        derive_evidence(
            observation_evidence_request(observation=_failed_observation_request("INVALID"))
        )
    assert "INVALID Negative Observation cannot produce a Difference" in str(raised.value)


def test_an_invalid_observation_status_is_still_refused_by_the_gate() -> None:
    """The second refusal, at the gate rather than the projection.

    Both exist and neither is redundant: the gate reads the Observation's own status, the
    projection reads the Negative Observation's evaluation. An INVALID record is untrustworthy
    at both.
    """

    assert "INVALID" not in _ACCEPTED_OBSERVATION_STATUS


# --------------------------------------------------------------------------- #
# and it round-trips
# --------------------------------------------------------------------------- #


def test_failed_evidence_passes_the_difference_owner_s_own_bundle_gates() -> None:
    """The whole point of admitting FAILED: the record has to be *usable*, not merely creatable.

    The gates are the Difference owner's own functions, run over a real bundle: the one
    ``derive_differences`` emitted for the failed Observation, carrying the sufficiency result
    Phase 6 produced from Evidence about that same Observation.

    It is done this way rather than through ``difference_round_trip_request`` for a reason
    worth stating. That helper's retained lineage is built by ``reobservation_pair``, which
    constructs its bundle internally and exposes no way to make an attempt FAIL -- so its
    predecessor Difference can never be the failed one, and a sufficiency result naming the
    failed Difference cannot resolve inside it. Reshaping a Phase 3 helper to force it would
    change a retained surface for a Phase 6 test. Running the same two gates over the bundle
    that does contain the failed Difference proves the same property against the same code.

    ``test_difference_round_trip.py`` proves the full ``derive_differences`` transport on the
    standard route; nothing in that transport reads a status.
    """

    request = difference_request()
    request["bindings"][0]["observation_bundle"] = observe(_failed_observation_request())
    bundle = derive_differences(request)
    assert bundle["differences"][0]["normalized_observed_state"]["knowledge_status"] == "UNKNOWN"

    # The Difference's own Closure Policy, as its producer emitted it -- not a policy the
    # test wrote. A fixture policy would differ in its requirements, and therefore in its
    # CP- address, and the reference would fail to resolve for a reason that has nothing to
    # do with what is being proven here.
    policy = bundle["policies"][0]
    evaluation = evaluate_sufficiency(
        sufficiency_request(
            difference_id=bundle["differences"][0]["difference_id"],
            policy=policy,
            evidence_requests=[
                observation_evidence_request(observation=_failed_observation_request())
            ],
        )
    )
    produced = evaluation["evidence_sufficiency_result"]
    assert produced["result"] == "INSUFFICIENT"
    assert produced["evidence_refs"]["members"]
    assert produced["difference_ref"]["id"] == bundle["differences"][0]["difference_id"]
    assert produced["policy_ref"]["id"] == policy["closure_policy_id"]

    bundle["evidence_sufficiency_results"] = [deepcopy(produced)]
    validate_emitted_bundle(bundle)
    assert reference_closure_errors(bundle) == []


def test_that_bundle_gate_is_not_vacuous() -> None:
    """The control. A gate reporting nothing must be shown capable of reporting.

    The wrong reference kind is the one that mattered -- it is what round 3 found -- so it is
    the one injected here, into the same bundle the positive case above passes.
    """

    request = difference_request()
    request["bindings"][0]["observation_bundle"] = observe(_failed_observation_request())
    bundle = derive_differences(request)

    produced = evaluate_sufficiency(
        sufficiency_request(
            difference_id=bundle["differences"][0]["difference_id"],
            policy=bundle["policies"][0],
            evidence_requests=[
                observation_evidence_request(observation=_failed_observation_request())
            ],
        )
    )["evidence_sufficiency_result"]

    forged = deepcopy(produced)
    for member in forged["evidence_refs"]["members"]:
        member["kind"] = "evidence"
    bundle["evidence_sufficiency_results"] = [forged]
    assert reference_closure_errors(bundle) != []
