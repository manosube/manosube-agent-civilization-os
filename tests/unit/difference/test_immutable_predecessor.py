"""A canonical Difference Record is immutable under its own identity.

Covers the independent review finding on `9bfb176`: an equivalent re-observation used to
return a newly constructed record under the preserved Difference ID, silently replacing
the predecessor's observed State revision, State fingerprint, Observation binding and
Evidence binding. Re-observation *appends* provenance; the record itself never changes.
"""

from __future__ import annotations

from copy import deepcopy
from itertools import pairwise
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import reobservation_pair

from manosube_agent_civilization.difference import (
    DifferenceError,
    IdentityCollisionError,
    derive_differences,
)
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes


def _pair() -> tuple[dict[str, Any], dict[str, Any]]:
    baseline_request, later_request = reobservation_pair()
    return derive_differences(baseline_request), later_request


def _with_predecessor(
    baseline: dict[str, Any], later_request: dict[str, Any]
) -> dict[str, Any]:
    request = deepcopy(later_request)
    request["bindings"][0]["predecessor"] = {
        "difference": deepcopy(baseline["differences"][0]),
        "events": deepcopy(baseline["events"]),
        "context": deepcopy(baseline),
    }
    return request


# --------------------------------------------------------------------------- #
# The predecessor payload survives the re-observation byte for byte.
# --------------------------------------------------------------------------- #


def test_the_predecessor_record_is_returned_unchanged() -> None:
    baseline, later_request = _pair()
    predecessor = deepcopy(baseline["differences"][0])
    bundle = derive_differences(_with_predecessor(baseline, later_request))

    assert len(bundle["differences"]) == 1
    assert canonical_json_bytes(bundle["differences"][0]) == canonical_json_bytes(predecessor)


def test_the_caller_predecessor_object_is_never_mutated() -> None:
    baseline, later_request = _pair()
    request = _with_predecessor(baseline, later_request)
    before = canonical_json_bytes(request["bindings"][0]["predecessor"])
    derive_differences(request)
    assert canonical_json_bytes(request["bindings"][0]["predecessor"]) == before


@pytest.mark.parametrize(
    "field",
    [
        "observed_state_revision",
        "observed_state_fingerprint",
        "observation_refs",
        "observation_evidence_refs",
        "normalized_observed_state",
        "objective_revision_ref",
        "genesis_event_ref",
        "closure_policy",
    ],
)
def test_no_immutable_field_is_replaced_by_the_new_binding(field: str) -> None:
    """Every field outside the identity tuple keeps the predecessor's value."""

    baseline, later_request = _pair()
    predecessor = deepcopy(baseline["differences"][0])
    bundle = derive_differences(_with_predecessor(baseline, later_request))
    assert bundle["differences"][0][field] == predecessor[field]


def test_the_new_state_binding_is_genuinely_different() -> None:
    """The assertions above are not vacuous: the re-observation really did move."""

    baseline, later_request = _pair()
    predecessor = baseline["differences"][0]
    bundle = derive_differences(_with_predecessor(baseline, later_request))
    appended = bundle["events"][-1]

    assert appended["event_kind"] == "OBSERVATION_BOUND"
    assert appended["state_revision_evaluated"] != predecessor["observed_state_revision"]
    assert appended["state_fingerprint_evaluated"] != predecessor["observed_state_fingerprint"]
    assert appended["observation_refs"] != predecessor["observation_refs"]
    assert appended["from_status"] == appended["to_status"]


# --------------------------------------------------------------------------- #
# The new binding is represented, and only, by the appended event.
# --------------------------------------------------------------------------- #


def test_the_appended_event_binds_the_new_observation_and_genesis_keeps_its_own() -> None:
    baseline, later_request = _pair()
    bundle = derive_differences(_with_predecessor(baseline, later_request))
    difference = bundle["differences"][0]
    events = {event["difference_event_id"]: event for event in bundle["events"]}
    observations = {item["observation_id"] for item in bundle["observations"]}

    genesis = events[difference["genesis_event_ref"]["id"]]
    assert genesis["event_revision"] == 0
    genesis_refs = {reference["id"] for reference in genesis["observation_refs"]}
    appended_refs = {reference["id"] for reference in bundle["events"][-1]["observation_refs"]}

    assert genesis_refs == {reference["id"] for reference in difference["observation_refs"]}
    assert genesis_refs != appended_refs
    assert genesis_refs | appended_refs == observations
    assert len(observations) == 2

    # Both Observations, and every record either event needs, travel with the lineage.
    for event in bundle["events"]:
        for reference in event["observation_refs"]:
            assert reference["id"] in observations


def test_the_appended_event_carries_the_new_evidence_binding() -> None:
    baseline, later_request = _pair()
    bundle = derive_differences(_with_predecessor(baseline, later_request))
    observations = {item["observation_id"]: item for item in bundle["observations"]}
    appended = bundle["events"][-1]

    bound = [observations[reference["id"]] for reference in appended["observation_refs"]]
    expected = {
        canonical_json_bytes(reference)
        for observation in bound
        for reference in observation["observation_evidence_refs"]
    }
    assert expected == {
        canonical_json_bytes(reference) for reference in appended["evidence_refs"]
    }


def test_the_returned_lineage_is_append_only_and_contiguous() -> None:
    baseline, later_request = _pair()
    bundle = derive_differences(_with_predecessor(baseline, later_request))
    chain = sorted(bundle["events"], key=lambda event: event["event_revision"])

    assert [event["event_revision"] for event in chain] == list(range(len(chain)))
    assert chain[0]["previous_event_id"] is None
    for previous, event in pairwise(chain):
        assert event["previous_event_id"] == previous["difference_event_id"]
        assert event["from_status"] == previous["to_status"]
    # Every predecessor event is retained verbatim.
    for original, retained in zip(baseline["events"], chain, strict=False):
        assert canonical_json_bytes(original) == canonical_json_bytes(retained)


def test_the_returned_bundle_is_cross_record_valid() -> None:
    baseline, later_request = _pair()
    bundle = derive_differences(_with_predecessor(baseline, later_request))
    assert validate_bundle(bundle) == []
    assert bundle["supersession_relations"] == []


def test_the_route_is_deterministic() -> None:
    baseline, later_request = _pair()
    request = _with_predecessor(baseline, later_request)
    assert canonical_json_bytes(derive_differences(deepcopy(request))) == canonical_json_bytes(
        derive_differences(deepcopy(request))
    )


# --------------------------------------------------------------------------- #
# Any attempt to replace the record under the preserved identity fails closed.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subject", "service.other"),
        ("project_id", "PRJ-9999"),
        ("objective_semantic_fingerprint", "sha256:" + "0" * 64),
        ("observation_scope", "OTHER_SCOPE"),
    ],
)
def test_a_predecessor_with_a_forged_identity_field_is_rejected(
    field: str, value: Any
) -> None:
    """A same-ID/different-payload predecessor still fails closed."""

    baseline, later_request = _pair()
    request = _with_predecessor(baseline, later_request)
    request["bindings"][0]["predecessor"]["difference"][field] = value
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_a_predecessor_with_a_forged_closure_policy_identity_is_rejected() -> None:
    baseline, later_request = _pair()
    request = _with_predecessor(baseline, later_request)
    request["bindings"][0]["predecessor"]["difference"]["closure_policy"]["id"] = (
        "CLOSURE-POLICY-FORGED"
    )
    with pytest.raises(IdentityCollisionError, match="Closure Policy identity"):
        derive_differences(request)


def test_a_predecessor_whose_genesis_reference_was_redirected_is_rejected() -> None:
    baseline, later_request = _pair()
    request = _with_predecessor(baseline, later_request)
    chain = request["bindings"][0]["predecessor"]["events"]
    request["bindings"][0]["predecessor"]["difference"]["genesis_event_ref"] = {
        "kind": "difference_event",
        "id": chain[-1]["difference_event_id"],
    }
    with pytest.raises(DifferenceError, match="genesis reference"):
        derive_differences(request)


def test_a_predecessor_naming_an_observation_it_never_carries_is_rejected() -> None:
    """The retained record's own Observation binding must resolve in the returned bundle."""

    baseline, later_request = _pair()
    request = _with_predecessor(baseline, later_request)
    request["bindings"][0]["predecessor"]["context"]["observations"] = []
    with pytest.raises(DifferenceError, match="does not resolve"):
        derive_differences(request)
