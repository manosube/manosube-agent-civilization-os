"""Evidence reached the way the Kernel loop reaches it, never around it.

```text
OBJECTIVE → STATE → OBSERVATION → DIFFERENCE → AUTHORITY → CHANGE → EVIDENCE
```

Every predecessor here is produced by its canonical owner from real inputs. Nothing in this
file hand-writes an Observation, a Difference, an Authority decision or a Change -- and the
Evidence engine could not accept one if it did, because its request carries the
predecessors' *requests* rather than their records. That is the Phase 5 P1 lesson applied
one phase later: an identity function is public, so a supplied record proves only that its
author could run a hash.
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.authority_helpers import derived_difference
from tests.difference_helpers import PREDICATE_ID
from tests.evidence_helpers import (
    AFTER_REVISION,
    BEFORE_REVISION,
    after_observation_request,
    before_observation_request,
    change_result_evidence_request,
    closure_policy,
    completion_semantics_ref,
    observation_evidence_request,
    real_change_request,
)

from manosube_agent_civilization.authority import evaluate_authority
from manosube_agent_civilization.change import derive_change
from manosube_agent_civilization.evidence import (
    CHANGE_RESULT_EVIDENCE,
    OBSERVATION_EVIDENCE,
    EvidenceError,
    derive_evidence,
    evaluate_sufficiency,
)
from manosube_agent_civilization.observation import observe

# --------------------------------------------------------------------------- #
# route 1 -- Observation → Evidence, with no Change anywhere
# --------------------------------------------------------------------------- #


def test_a_change_free_observation_cycle_produces_formal_evidence() -> None:
    """第27条: Observation Evidence must be recordable where no Change occurs at all."""

    record = derive_evidence(observation_evidence_request())
    assert record["evidence_position"] == OBSERVATION_EVIDENCE
    assert record["change_identity"] is None
    assert record["before_state"]["state_revision"] == BEFORE_REVISION


def test_the_evidence_names_the_observation_the_real_engine_minted() -> None:
    request = before_observation_request()
    minted = observe(request)["observations"][-1]
    record = derive_evidence(observation_evidence_request(observation=request))
    assert record["observed_result"]["observation_ref"]["id"] == minted["observation_id"]
    assert record["observed_result"]["observation_status"] == minted["status"]
    assert record["observed_result"]["attempt_outcomes"]["members"] == [
        attempt["result"] for attempt in minted["attempts"]
    ]


def test_the_state_binding_is_the_state_the_observation_observed() -> None:
    request = before_observation_request()
    minted = observe(request)["observations"][-1]
    record = derive_evidence(observation_evidence_request(observation=request))
    assert record["before_state"] == {
        "state_revision": minted["state_revision_observed"],
        "semantic_fingerprint": minted["state_fingerprint_observed"],
    }


def test_the_engine_takes_a_request_and_not_a_record() -> None:
    """The forgery surface, closed by construction rather than by a check.

    Handing the engine a real Observation *record* is not a supported input at all, so
    there is no path on which a synthesised one could be compared, trusted or refused.
    """

    minted = observe(before_observation_request())["observations"][-1]
    with pytest.raises(EvidenceError):
        derive_evidence(observation_evidence_request(observation=minted))


# --------------------------------------------------------------------------- #
# route 2 -- Difference → Authority → Change → re-observation → Evidence
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def change_route() -> dict[str, Any]:
    request = real_change_request()
    decision = evaluate_authority(request["authority_request"])
    change = derive_change(request)
    return {"request": request, "decision": decision, "change": change}


def test_the_evidence_binds_the_change_the_real_deriver_produced(
    change_route: dict[str, Any],
) -> None:
    record = derive_evidence(change_result_evidence_request(change_request=change_route["request"]))
    assert record["evidence_position"] == CHANGE_RESULT_EVIDENCE
    assert record["change_identity"]["id"] == change_route["change"]["change_id"]
    assert (
        record["change_identity"]["change_semantic_fingerprint"]
        == change_route["change"]["change_semantic_fingerprint"]
    )


def test_the_evidence_binds_the_decision_the_real_evaluator_produced(
    change_route: dict[str, Any],
) -> None:
    record = derive_evidence(change_result_evidence_request(change_request=change_route["request"]))
    assert record["authority_used"]["id"] == change_route["decision"]["authority_decision_id"]
    assert record["authority_used"]["decision"] == "AUTONOMOUS"


def test_a_forged_decision_cannot_reach_evidence(change_route: dict[str, Any]) -> None:
    """Phase 5's provenance repair is inherited rather than restated.

    ``derive_change`` reproduces the decision through ``evaluate_authority``, so a
    synthesised AUTONOMOUS decision is refused one layer down and never becomes an
    ``authority_used`` binding here.
    """

    forged = dict(change_route["request"])
    decision = dict(change_route["decision"])
    decision["decision_reason_codes"] = ["FABRICATED"]
    forged["authority_decision"] = decision
    with pytest.raises(EvidenceError):
        derive_evidence(change_result_evidence_request(change_request=forged))


def test_the_after_state_is_the_re_observation_and_not_the_change_s_claim(
    change_route: dict[str, Any],
) -> None:
    after = after_observation_request()
    minted = observe(after)["observations"][-1]
    record = derive_evidence(
        change_result_evidence_request(
            change_request=change_route["request"], post_change_observation=after
        )
    )
    assert record["after_state"]["state_revision"] == AFTER_REVISION
    assert record["after_state"]["semantic_fingerprint"] == minted["state_fingerprint_observed"]
    assert record["observed_result"]["observation_ref"]["id"] == minted["observation_id"]


def test_the_status_comes_from_the_re_observation_not_the_before_picture(
    change_route: dict[str, Any],
) -> None:
    """A complete observation of the old state must not stand in for a missing one of the new."""

    after = after_observation_request()
    after["attempts"][0]["result"] = "BLOCKED"
    record = derive_evidence(
        change_result_evidence_request(
            change_request=change_route["request"], post_change_observation=after
        )
    )
    assert record["status"] == "BLOCKED"
    assert observe(before_observation_request())["observations"][-1]["status"] == "COMPLETE"


def test_the_lineage_names_every_record_the_evidence_was_derived_from(
    change_route: dict[str, Any],
) -> None:
    record = derive_evidence(change_result_evidence_request(change_request=change_route["request"]))
    kinds = [member["kind"] for member in record["lineage"]["derived_from"]["members"]]
    assert sorted(kinds) == ["authority_decision", "change", "observation", "observation"]


# --------------------------------------------------------------------------- #
# route 3 -- Evidence → Sufficiency, against the Difference's own Policy
# --------------------------------------------------------------------------- #


def test_sufficiency_runs_against_the_policy_the_real_difference_bound() -> None:
    """The Policy the fixture builds is the very one ``derive_differences`` addressed.

    If it were not, this whole route would be evaluating a policy no Difference ever
    carried -- coverage that proves nothing, which is the failure mode the helper's
    computed identity exists to prevent.
    """

    difference = derived_difference()
    policy = closure_policy(difference["difference_id"])
    assert policy["closure_policy_id"] == difference["closure_policy"]["id"]
    assert (
        policy["policy_semantic_fingerprint"]
        == difference["closure_policy"]["semantic_fingerprint"]
    )
    assert policy["target_predicate_ref"]["id"] == PREDICATE_ID

    evaluation = evaluate_sufficiency(
        {
            "schema_version": "0.1",
            "difference_ref": {"kind": "difference", "id": difference["difference_id"]},
            "closure_policy": policy,
            "completion_semantics_ref": completion_semantics_ref(),
            "evidence_requests": [observation_evidence_request()],
            "evaluation_instant": "2026-08-30T11:00:00Z",
        }
    )
    result = evaluation["evidence_sufficiency_result"]
    assert result["result"] == "SUFFICIENT"
    assert result["difference_ref"]["id"] == difference["difference_id"]
    assert result["policy_ref"]["id"] == difference["closure_policy"]["id"]


def test_change_result_evidence_feeds_sufficiency_on_the_same_route(
    change_route: dict[str, Any],
) -> None:
    difference = derived_difference()
    evaluation = evaluate_sufficiency(
        {
            "schema_version": "0.1",
            "difference_ref": {"kind": "difference", "id": difference["difference_id"]},
            "closure_policy": closure_policy(
                difference["difference_id"], minimum_evidence_level="E3"
            ),
            "completion_semantics_ref": completion_semantics_ref(),
            "evidence_requests": [
                change_result_evidence_request(change_request=change_route["request"])
            ],
            "evaluation_instant": "2026-08-30T11:00:00Z",
        }
    )
    assert evaluation["evidence_sufficiency_result"]["result"] == "SUFFICIENT"
    assert evaluation["evidence_sufficiency_result"]["evidence_level"] == "E3"


def test_the_produced_result_is_shaped_for_the_section_difference_carries_it_in() -> None:
    """``difference/engine.py`` carries ``evidence_sufficiency_results`` keyed by
    ``evidence_sufficiency_id``. A result that could not be keyed there would be a record
    with no consumer."""

    from manosube_agent_civilization.difference.engine import _CARRIED_SECTIONS

    assert _CARRIED_SECTIONS["evidence_sufficiency_results"] == "evidence_sufficiency_id"
    result = evaluate_sufficiency(
        {
            "schema_version": "0.1",
            "difference_ref": {"kind": "difference", "id": derived_difference()["difference_id"]},
            "closure_policy": closure_policy(derived_difference()["difference_id"]),
            "completion_semantics_ref": completion_semantics_ref(),
            "evidence_requests": [observation_evidence_request()],
            "evaluation_instant": "2026-08-30T11:00:00Z",
        }
    )["evidence_sufficiency_result"]
    assert result["evidence_sufficiency_id"].startswith("EVID-SUFF-")
