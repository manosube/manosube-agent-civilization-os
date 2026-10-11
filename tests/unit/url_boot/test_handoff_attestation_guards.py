"""Handoff guards against forged receipts and unreadable historical lookup facts.

The lookup double isolates these guards; it does not prove durable Store commits.
Envelope and Binding bodies come from their canonical assembly owners. Real Store
and real-network continuity remain the subjects of the integration suites.
"""

from copy import deepcopy
from dataclasses import replace

import pytest
from tests.evidence_helpers import change_free_verification_evidence_request
from tests.fixtures.product_binding import bind_project_kwargs
from tests.fixtures.url_boot_world import boundary_for

from manosube_agent_civilization.binding.engine import assemble_project_binding
from manosube_agent_civilization.binding.identity import project_binding_id
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.url_boot import evidence_handoff as handoff
from manosube_agent_civilization.url_boot.engine import derive_url_source_observation_envelope
from manosube_agent_civilization.url_boot.errors import UrlBootError
from manosube_agent_civilization.url_boot.identity import (
    url_boundary_fingerprint,
    url_observed_content_fingerprint,
    url_source_fingerprint,
    url_source_observation_envelope_id,
    url_source_observation_envelope_semantic_fingerprint,
    url_source_request_identity,
)
from manosube_agent_civilization.url_boot.network import canonical_source_identity
from manosube_agent_civilization.url_boot.types import UrlSourceObservationReceipt


def rebind(value, old, new):
    if isinstance(value, dict):
        return {key: rebind(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [rebind(item, old, new) for item in value]
    return new if value == old else value


class LookupFacts:
    def __init__(self, envelope, binding, transition):
        self.envelope = deepcopy(envelope)
        self.binding = deepcopy(binding)
        self.transition = deepcopy(transition)

    def resolve_record(self, project_id, kind, record_id):
        return deepcopy(
            self.envelope if kind == "url_source_observation_envelope" else self.binding
        )

    def resolve_transaction(self, project_id, transaction_id):
        return deepcopy(self.transition)

    def commit(self, *args, **kwargs):
        raise AssertionError("handoff may not commit State")


@pytest.fixture
def world():
    inputs = bind_project_kwargs()
    project = inputs["project_id"]
    binding = assemble_project_binding(
        **{
            key: inputs[key]
            for key in (
                "project_id",
                "boundary",
                "authority_policy_ref",
                "source_registrations",
                "command_policy",
                "secret_exclusion_policy",
                "human_authority_ref",
                "human_authority_signing_key",
                "bound_at",
            )
        },
        objective_revision_ref={
            "kind": "objective_revision",
            "id": inputs["objective_revision"]["objective_revision_id"],
        },
    )
    state = inputs["genesis_state"]
    fingerprint = fingerprint_project_state(state).as_dict()
    source = canonical_source_identity("http://example.com/status")
    boundary = boundary_for(admitted_hosts=["example.com"])
    adapter = {"adapter": "unit-lookup", "version": "1"}
    authority = inputs["human_authority_ref"]
    source_fp = url_source_fingerprint(source)
    boundary_fp = url_boundary_fingerprint(boundary)
    envelope = derive_url_source_observation_envelope(
        project_id=project,
        project_binding_ref={"kind": "project_binding", "id": binding["project_binding_id"]},
        boot_state_fingerprint=fingerprint,
        boot_state_transition_ref={"kind": "state_transition", "id": "TX-UNIT-LOOKUP"},
        requested_source_identity=source,
        requested_source_fingerprint=source_fp,
        effective_source_identity=source,
        effective_source_fingerprint=source_fp,
        boundary=boundary,
        boundary_fingerprint=boundary_fp,
        source_request_identity=url_source_request_identity(
            source_fp, boundary_fp, boundary["time_window"]["issued_at"]
        ),
        retrieved_at="2026-09-10T00:00:01Z",
        fetch_outcome="OBSERVED",
        response_status=200,
        redirect_hop_count=0,
        resolution_provenance=[{"host": "example.com", "port": 80, "resolved_address": "8.8.8.8"}],
        observed_fields={"status": "ok"},
        observed_content_fingerprint=url_observed_content_fingerprint({"status": "ok"}),
        adapter_identity=adapter,
        human_authority_ref=authority,
    )
    receipt = UrlSourceObservationReceipt(
        status="VERIFIED",
        url_source_observation_envelope_id=envelope["url_source_observation_envelope_id"],
        project_id=project,
        requested_source_identity=source,
        boundary=boundary,
        adapter_identity=adapter,
        human_authority_ref=authority,
        input_refs=(authority,),
        observations={
            key: envelope[key]
            for key in ("fetch_outcome", "observed_content_fingerprint", "retrieved_at")
        },
    )
    lookup = LookupFacts(
        envelope,
        binding,
        {"project_id": project, "after_state": state, "after_fingerprint": fingerprint},
    )
    request = rebind(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project
    )
    positive = handoff.route_url_observation_to_evidence(lookup, receipt, project, request)
    assert positive["target"]["project_id"] == project
    return lookup, receipt, project, request


@pytest.mark.parametrize(
    "field,bad",
    [
        ("requested_source_identity", {}),
        ("boundary", {}),
        ("adapter_identity", {"adapter": "forged"}),
        ("human_authority_ref", {"kind": "human_authority", "id": "AUTH-FOREIGN"}),
        ("observations", {}),
        ("input_refs", ()),
    ],
)
def test_each_forged_attestation_field_is_refused(world, field, bad):
    lookup, receipt, project, request = world
    with pytest.raises(UrlBootError):
        handoff.route_url_observation_to_evidence(
            lookup, replace(receipt, **{field: bad}), project, request
        )


@pytest.mark.parametrize(
    "field,bad",
    [
        ("change_request", {}),
        ("post_change_observation_request", {}),
        ("verification_observation_request", None),
        ("verification_result_provenance", {}),
    ],
)
def test_handoff_cannot_be_repurposed_as_a_change_or_supplied_provenance(world, field, bad):
    lookup, receipt, project, request = world
    with pytest.raises(UrlBootError):
        handoff.route_url_observation_to_evidence(lookup, receipt, project, {**request, field: bad})


@pytest.mark.parametrize("bad", [None, [], "not-a-request"])
def test_non_mapping_request_is_refused(world, bad):
    lookup, receipt, project, _ = world
    with pytest.raises(UrlBootError):
        handoff.route_url_observation_to_evidence(lookup, receipt, project, bad)


@pytest.mark.parametrize(
    "target,bad",
    [
        ("envelope", None),
        ("envelope", []),
        ("binding", None),
        ("binding", []),
        ("transition", None),
        ("transition", []),
    ],
)
def test_missing_or_unreadable_lookup_fact_is_refused(world, target, bad):
    lookup, receipt, project, request = world
    setattr(lookup, target, bad)
    with pytest.raises(UrlBootError):
        handoff.route_url_observation_to_evidence(lookup, receipt, project, request)


@pytest.mark.parametrize(
    "target,field,bad",
    [
        ("envelope", "project_id", "PRJ-FOREIGN"),
        ("binding", "project_binding_id", "PB-FOREIGN"),
        ("binding", "project_id", "PRJ-FOREIGN"),
        ("binding", "human_authority_ref", {"kind": "human_authority", "id": "AUTH-FOREIGN"}),
        ("transition", "project_id", "PRJ-FOREIGN"),
        ("transition", "after_state", None),
        ("transition", "after_fingerprint", {}),
    ],
)
def test_lookup_identity_and_historical_state_mismatches_are_refused(world, target, field, bad):
    lookup, receipt, project, request = world
    getattr(lookup, target)[field] = bad
    if target == "binding":
        if field == "project_binding_id":
            lookup.binding["boundary"]["root_paths"] = ["other"]
        lookup.binding["project_binding_id"] = project_binding_id(lookup.binding)
        if field != "project_binding_id":
            lookup.envelope["project_binding_ref"]["id"] = lookup.binding["project_binding_id"]
            lookup.envelope["url_source_observation_envelope_id"] = (
                url_source_observation_envelope_id(lookup.envelope)
            )
            lookup.envelope["url_source_observation_semantic_fingerprint"] = (
                url_source_observation_envelope_semantic_fingerprint(lookup.envelope)
            )
            receipt = replace(
                receipt,
                url_source_observation_envelope_id=lookup.envelope[
                    "url_source_observation_envelope_id"
                ],
            )
    with pytest.raises(UrlBootError):
        handoff.route_url_observation_to_evidence(lookup, receipt, project, request)


@pytest.mark.parametrize("field", ["verification_result_provenance", "target"])
def test_an_owner_regression_cannot_silently_return_unconfirmed_evidence(world, monkeypatch, field):
    lookup, receipt, project, request = world
    real = handoff.derive_evidence

    def corrupted(candidate):
        evidence = real(candidate)
        if field == "target":
            evidence[field]["project_id"] = "PRJ-FOREIGN"
        else:
            evidence[field] = {}
        return evidence

    monkeypatch.setattr(handoff, "derive_evidence", corrupted)
    with pytest.raises(UrlBootError):
        handoff.route_url_observation_to_evidence(lookup, receipt, project, request)
