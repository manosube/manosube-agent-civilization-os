"""Receipt/request guards, with canonical envelopes and a read-only lookup double.

These controls test the handoff, not transport or durable commit. The positive
control reaches the real Evidence owner before any forged field is introduced.
"""

from copy import deepcopy
from dataclasses import replace

import pytest
from tests.evidence_helpers import change_free_verification_evidence_request
from tests.fixtures.runtime_world import boundary_for, target_identity_for

from manosube_agent_civilization.runtime import evidence_handoff as handoff
from manosube_agent_civilization.runtime.engine import derive_runtime_observation_envelope
from manosube_agent_civilization.runtime.errors import RuntimeObservationError as RuntimeDomainError
from manosube_agent_civilization.runtime.identity import (
    runtime_observation_boundary_fingerprint,
    runtime_observation_request_identity,
    runtime_observed_content_fingerprint,
    runtime_target_fingerprint,
)
from manosube_agent_civilization.runtime.types import RuntimeObservationReceipt


class Lookup:
    def __init__(self, envelope):
        self.envelope = envelope

    def resolve_record(self, *args):
        return deepcopy(self.envelope)


@pytest.fixture
def world():
    target = target_identity_for(
        "PB-UNIT",
        deployment_declaration_ref={"kind": "runtime_deployment_declaration", "id": "RDD-UNIT"},
    )
    boundary = boundary_for()
    target_fp = runtime_target_fingerprint(target)
    boundary_fp = runtime_observation_boundary_fingerprint(boundary)
    envelope = derive_runtime_observation_envelope(
        project_id="PRJ-0001",
        target_identity=target,
        target_fingerprint=target_fp,
        boundary=boundary,
        boundary_fingerprint=boundary_fp,
        observation_request_identity=runtime_observation_request_identity(
            target_fp, boundary_fp, boundary["time_window"]["issued_at"]
        ),
        observed_at="2026-01-01T00:00:01Z",
        observation_outcome="OBSERVED",
        observed_fields={"status": "ok"},
        observed_content_fingerprint=runtime_observed_content_fingerprint({"status": "ok"}),
        adapter_identity={"adapter": "unit-lookup", "version": "1"},
        human_authority_ref={"kind": "human_authority", "id": "AUTH-UNIT"},
    )
    receipt = RuntimeObservationReceipt(
        status="VERIFIED",
        runtime_observation_envelope_id=envelope["runtime_observation_envelope_id"],
        project_id="PRJ-0001",
        target_identity=target,
        boundary=boundary,
        adapter_identity=envelope["adapter_identity"],
        human_authority_ref=envelope["human_authority_ref"],
        input_refs=(target["project_binding_ref"],),
        observations={
            key: envelope[key]
            for key in ("observation_outcome", "observed_content_fingerprint", "observed_at")
        },
    )
    lookup = Lookup(envelope)
    request = change_free_verification_evidence_request(provenance=None)
    assert (
        handoff.route_runtime_observation_to_evidence(lookup, receipt, "PRJ-0001", request)[
            "target"
        ]["project_id"]
        == "PRJ-0001"
    )
    return lookup, receipt, request


@pytest.mark.parametrize(
    "field,bad",
    [
        ("target_identity", {}),
        ("boundary", {}),
        ("adapter_identity", {}),
        ("human_authority_ref", {}),
        ("observations", {}),
        ("input_refs", ()),
        ("status", "UNAVAILABLE"),
        ("project_id", "PRJ-FOREIGN"),
    ],
)
def test_each_forged_receipt_field_is_refused(world, field, bad):
    lookup, receipt, request = world
    with pytest.raises(RuntimeDomainError):
        handoff.route_runtime_observation_to_evidence(
            lookup, replace(receipt, **{field: bad}), "PRJ-0001", request
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
def test_request_cannot_supply_change_or_its_own_provenance(world, field, bad):
    lookup, receipt, request = world
    with pytest.raises(RuntimeDomainError):
        handoff.route_runtime_observation_to_evidence(
            lookup, receipt, "PRJ-0001", {**request, field: bad}
        )


def test_missing_resolved_envelope_is_refused(world):
    lookup, receipt, request = world
    lookup.envelope = None
    with pytest.raises(RuntimeDomainError):
        handoff.route_runtime_observation_to_evidence(lookup, receipt, "PRJ-0001", request)


@pytest.mark.parametrize("field", ["target", "verification_result_provenance"])
def test_owner_regression_cannot_return_unconfirmed_evidence(world, monkeypatch, field):
    lookup, receipt, request = world
    real = handoff.derive_evidence

    def corrupted(candidate):
        evidence = real(candidate)
        if field == "target":
            evidence[field]["project_id"] = "PRJ-FOREIGN"
        else:
            evidence[field] = {}
        return evidence

    monkeypatch.setattr(handoff, "derive_evidence", corrupted)
    with pytest.raises(RuntimeDomainError):
        handoff.route_runtime_observation_to_evidence(lookup, receipt, "PRJ-0001", request)
