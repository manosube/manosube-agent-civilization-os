"""Model handoff attestation guards using canonical facts and a lookup double.

No model is called and no durable commit is asserted. A genuine schema-valid
envelope and the real Evidence/Difference owners establish the positive control.
"""

from copy import deepcopy
from dataclasses import replace

import pytest
from tests.fixtures.model_runtime_world import difference_for, evidence_request_for
from tests.fixtures.product_binding import bind_project_kwargs

from manosube_agent_civilization.model_runtime import evidence_handoff as handoff
from manosube_agent_civilization.model_runtime.engine import (
    canonical_evidence_requirements,
    derive_model_execution_envelope,
)
from manosube_agent_civilization.model_runtime.errors import ModelRuntimeError
from manosube_agent_civilization.model_runtime.identity import (
    model_candidate_fingerprint,
    model_execution_request_identity,
)
from manosube_agent_civilization.model_runtime.types import ModelExecutionReceipt
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state


class Lookup:
    def __init__(self, envelope):
        self.envelope = envelope

    def resolve_record(self, *args):
        return deepcopy(self.envelope)


@pytest.fixture
def world():
    project = "PRJ-0001"
    state = bind_project_kwargs()["genesis_state"]
    fp = fingerprint_project_state(state).as_dict()
    adapter = {"adapter": "unit-candidate", "version": "1"}
    candidate = {"summary": "bounded candidate"}
    envelope = derive_model_execution_envelope(
        project_id=project,
        project_binding_ref={"kind": "project_binding", "id": "PB-UNIT"},
        model_work_unit_ref={"kind": "model_work_unit", "id": "MWU-UNIT"},
        model_execution_request_identity=model_execution_request_identity(
            model_work_unit_id_value="MWU-UNIT",
            state_revision=state["state_revision"],
            semantic_fingerprint=fp,
            adapter_identity=adapter,
        ),
        executed_state_revision=state["state_revision"],
        executed_semantic_fingerprint=fp,
        adapter_identity=adapter,
        executed_at="2026-09-10T00:00:01Z",
        execution_outcome="CANDIDATE_ACCEPTED",
        normalized_candidate_kind="OBSERVATION_CANDIDATE",
        normalized_candidate=candidate,
        normalized_candidate_fingerprint=model_candidate_fingerprint(candidate),
        difference_ref={"kind": "difference", "id": difference_for(project)["difference_id"]},
        required_capability="PROPOSE_EVIDENCE_CANDIDATE",
        authority_ref={"kind": "model_execution_decision", "id": "MED-UNIT"},
        boundary_ref={"kind": "model_execution_boundary", "id": "MEB-UNIT"},
        evidence_requirements=canonical_evidence_requirements(),
        human_authority_ref={"kind": "human_authority", "id": "AUTH-UNIT"},
    )
    fields = {
        key: envelope[key]
        for key in (
            "project_id",
            "model_work_unit_ref",
            "adapter_identity",
            "difference_ref",
            "authority_ref",
            "boundary_ref",
            "required_capability",
            "evidence_requirements",
            "human_authority_ref",
        )
    }
    receipt = ModelExecutionReceipt(
        **fields,
        status="VERIFIED",
        model_execution_envelope_id=envelope["model_execution_envelope_id"],
        input_refs=(envelope["difference_ref"], envelope["model_work_unit_ref"]),
        observations={
            key: envelope[key]
            for key in ("execution_outcome", "normalized_candidate_fingerprint", "executed_at")
        },
    )
    lookup = Lookup(envelope)
    request = evidence_request_for(project, provenance=None)
    assert (
        handoff.route_model_execution_to_evidence(lookup, receipt, project, request)[
            "difference_ref"
        ]
        == envelope["difference_ref"]
    )
    return lookup, receipt, project, request


@pytest.mark.parametrize(
    "field,bad",
    [
        ("model_work_unit_ref", {}),
        ("adapter_identity", {}),
        ("difference_ref", {}),
        ("authority_ref", {}),
        ("boundary_ref", {}),
        ("evidence_requirements", {}),
        ("human_authority_ref", {}),
        ("observations", {}),
        ("input_refs", ()),
        ("status", "UNAVAILABLE"),
        ("project_id", "PRJ-FOREIGN"),
    ],
)
def test_forged_receipt_cannot_attest_to_model_work(world, field, bad):
    lookup, receipt, project, request = world
    with pytest.raises(ModelRuntimeError):
        handoff.route_model_execution_to_evidence(
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
def test_request_cannot_supply_change_or_self_attested_provenance(world, field, bad):
    lookup, receipt, project, request = world
    with pytest.raises(ModelRuntimeError):
        handoff.route_model_execution_to_evidence(lookup, receipt, project, {**request, field: bad})


@pytest.mark.parametrize("bad", [None, [], "not-a-request"])
def test_non_mapping_evidence_request_is_refused(world, bad):
    lookup, receipt, project, _ = world
    with pytest.raises(ModelRuntimeError):
        handoff.route_model_execution_to_evidence(lookup, receipt, project, bad)


@pytest.mark.parametrize("field", ["difference_ref", "verification_result_provenance"])
def test_owner_regression_cannot_silently_return_rebound_evidence(world, monkeypatch, field):
    lookup, receipt, project, request = world
    real = handoff.derive_evidence

    def corrupted(candidate):
        evidence = real(candidate)
        evidence[field] = {}
        return evidence

    monkeypatch.setattr(handoff, "derive_evidence", corrupted)
    with pytest.raises(ModelRuntimeError):
        handoff.route_model_execution_to_evidence(lookup, receipt, project, request)
