"""V4 (Issue #64): failure/tamper/provenance proof matrix.

Each test below proves exactly one required refusal or survival case for the canonical
Runtime Observation route and its Evidence hand-off, over a real ``FileStateStore``.
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Any

import pytest
from tests.evidence_helpers import change_free_verification_evidence_request
from tests.fixtures.runtime_world import bound, boundary_for, commit_records, target_identity_for

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.runtime.adapter import FakeRuntimeAdapter
from manosube_agent_civilization.runtime.errors import (
    RuntimeEnvelopeIntegrityError,
    RuntimeRequirementError,
)
from manosube_agent_civilization.runtime.evidence_handoff import (
    route_runtime_observation_to_evidence,
)
from manosube_agent_civilization.runtime.identity import (
    runtime_observation_boundary_fingerprint,
    runtime_observation_envelope_id,
    runtime_observation_request_identity,
    runtime_target_fingerprint,
)
from manosube_agent_civilization.runtime.route import observe_runtime_target
from manosube_agent_civilization.runtime.types import RuntimeObservationReceipt
from manosube_agent_civilization.store.errors import CorruptStoreError


def _rebind_project(value: Any, old: str, new: str) -> Any:
    if isinstance(value, dict):
        return {key: _rebind_project(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [_rebind_project(item, old, new) for item in value]
    return new if value == old else value


@pytest.fixture
def _world(tmp_path: Path) -> dict[str, Any]:
    store, ctx = bound(tmp_path)
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "human_authority_ref": dict(boot_context.human_authority_ref),
        "target_identity": target_identity_for(ctx["project_binding_id"]),
    }


def _observe(
    world: dict[str, Any], adapter: Any, boundary: dict[str, Any], observed_at: str
) -> dict[str, Any]:
    return observe_runtime_target(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=world["target_identity"],
        boundary=boundary,
        adapter=adapter,
        observed_at=observed_at,
    )


# ---------------------------------------------------------------------------
# Boundary/time-window enforcement
# ---------------------------------------------------------------------------


def test_observation_outside_the_declared_time_window_refuses_before_any_adapter_call(
    _world: dict[str, Any],
) -> None:
    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=_world["target_identity"], fields={"status": "ok"})
    boundary = boundary_for(issued_at="2026-01-01T00:00:00Z", expires_at="2026-01-01T00:10:00Z")
    with pytest.raises(RuntimeRequirementError):
        _observe(_world, adapter, boundary, "2026-01-01T01:00:00Z")  # well past expires_at
    assert adapter.observe_call_count == 0


def test_observation_before_the_declared_issued_at_refuses_before_any_adapter_call(
    _world: dict[str, Any],
) -> None:
    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=_world["target_identity"], fields={"status": "ok"})
    boundary = boundary_for(issued_at="2026-01-01T00:00:00Z", expires_at="2026-01-01T01:00:00Z")
    with pytest.raises(RuntimeRequirementError):
        _observe(_world, adapter, boundary, "2025-12-31T23:59:59Z")
    assert adapter.observe_call_count == 0


# ---------------------------------------------------------------------------
# Substituted Binding/Authority
# ---------------------------------------------------------------------------


def test_target_declaring_a_different_project_binding_refuses_before_any_adapter_call(
    _world: dict[str, Any],
) -> None:
    adapter = FakeRuntimeAdapter()
    foreign_target = dict(_world["target_identity"])
    foreign_target["project_binding_ref"] = {"kind": "project_binding", "id": "PROJBIND-ATTACKER"}
    adapter.seed_target(target_identity=foreign_target, fields={"status": "ok"})
    with pytest.raises(RuntimeRequirementError):
        observe_runtime_target(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=foreign_target,
            boundary=boundary_for(),
            adapter=adapter,
            observed_at="2026-01-01T00:30:00Z",
        )
    assert adapter.observe_call_count == 0


# ---------------------------------------------------------------------------
# Sequential calls and unrelated Store mutation
# ---------------------------------------------------------------------------


def test_sequential_calls_each_survive_their_own_prior_commit(_world: dict[str, Any]) -> None:
    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=_world["target_identity"], fields={"status": "ok"})
    boundary = boundary_for()
    first = _observe(_world, adapter, boundary, "2026-01-01T00:30:00Z")
    second = _observe(_world, adapter, boundary, "2026-01-01T00:31:00Z")
    third = _observe(_world, adapter, boundary, "2026-01-01T00:32:00Z")
    ids = {
        first["envelope"]["runtime_observation_envelope_id"],
        second["envelope"]["runtime_observation_envelope_id"],
        third["envelope"]["runtime_observation_envelope_id"],
    }
    assert len(ids) == 3
    for outcome in (first, second, third):
        resolved = _world["store"].resolve_record(
            _world["project_id"],
            "runtime_observation_envelope",
            outcome["envelope"]["runtime_observation_envelope_id"],
        )
        assert resolved == outcome["envelope"]


def test_an_unrelated_store_mutation_between_calls_does_not_block_a_fresh_observation(
    _world: dict[str, Any],
) -> None:
    """Unlike a bound, reused capability (Phase 14's own ``ProjectionExecutionCapability``),
    each :func:`observe_runtime_target` call independently re-verifies Project/Human
    Authority through Boot fresh -- so a wholly unrelated Store mutation between two calls
    must never block the next, correctly re-verified observation."""

    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=_world["target_identity"], fields={"status": "ok"})
    boundary = boundary_for()
    first = _observe(_world, adapter, boundary, "2026-01-01T00:30:00Z")

    # An unrelated commit: a second, distinct observation of a different target.
    other_target = target_identity_for(
        _world["project_binding_id"], instance_identity="unrelated-instance"
    )
    adapter.seed_target(target_identity=other_target, fields={"status": "ok"})
    _observe({**_world, "target_identity": other_target}, adapter, boundary, "2026-01-01T00:30:30Z")

    second = _observe(_world, adapter, boundary, "2026-01-01T00:31:00Z")
    assert (
        second["envelope"]["runtime_observation_envelope_id"]
        != first["envelope"]["runtime_observation_envelope_id"]
    )
    assert second["receipt"].status == "VERIFIED"


# ---------------------------------------------------------------------------
# Credential leakage / redaction
# ---------------------------------------------------------------------------


def test_redacted_fields_never_appear_unredacted_in_the_committed_envelope(
    _world: dict[str, Any],
) -> None:
    adapter = FakeRuntimeAdapter()
    adapter.seed_target(
        target_identity=_world["target_identity"],
        fields={"status": "ok", "api_token": "SUPER-SECRET-VALUE"},
    )
    boundary = boundary_for(
        permitted_fields=["status", "api_token"], redaction_fields=["api_token"]
    )
    outcome = _observe(_world, adapter, boundary, "2026-01-01T00:30:00Z")

    assert outcome["envelope"]["observed_fields"]["api_token"] == "<REDACTED>"  # noqa: S105
    assert outcome["envelope"]["observed_fields"]["status"] == "ok"

    # Confirm the secret never reaches the Store's own on-disk record at all.
    resolved = _world["store"].resolve_record(
        _world["project_id"],
        "runtime_observation_envelope",
        outcome["envelope"]["runtime_observation_envelope_id"],
    )
    assert "SUPER-SECRET-VALUE" not in json.dumps(resolved)

    # The receipt itself carries only the outcome/fingerprint/timestamp -- never raw fields.
    assert "SUPER-SECRET-VALUE" not in json.dumps(dict(outcome["receipt"].observations))


def test_redaction_changes_the_committed_fingerprint_versus_an_unredacted_field_set(
    _world: dict[str, Any],
) -> None:
    """Redaction is not merely cosmetic -- two targets differing only in their own secret
    field's real value must still commit the identical fingerprint once redacted, proving the
    real secret value never enters the fingerprint computation at all."""

    boundary = boundary_for(
        permitted_fields=["status", "api_token"], redaction_fields=["api_token"]
    )

    adapter_a = FakeRuntimeAdapter()
    target_a = target_identity_for(_world["project_binding_id"], instance_identity="instance-a")
    adapter_a.seed_target(
        target_identity=target_a, fields={"status": "ok", "api_token": "SECRET-A"}
    )
    outcome_a = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=target_a,
        boundary=boundary,
        adapter=adapter_a,
        observed_at="2026-01-01T00:30:00Z",
    )

    adapter_b = FakeRuntimeAdapter()
    target_b = target_identity_for(_world["project_binding_id"], instance_identity="instance-b")
    adapter_b.seed_target(
        target_identity=target_b, fields={"status": "ok", "api_token": "SECRET-B"}
    )
    outcome_b = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=target_b,
        boundary=boundary,
        adapter=adapter_b,
        observed_at="2026-01-01T00:30:00Z",
    )

    assert (
        outcome_a["envelope"]["observed_content_fingerprint"]
        == outcome_b["envelope"]["observed_content_fingerprint"]
    )


# ---------------------------------------------------------------------------
# Store-level and domain-level tamper detection
# ---------------------------------------------------------------------------


def test_a_directly_edited_committed_envelope_is_caught_by_the_stores_own_manifest_check(
    _world: dict[str, Any], tmp_path: Path
) -> None:
    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=_world["target_identity"], fields={"status": "ok"})
    outcome = _observe(_world, adapter, boundary_for(), "2026-01-01T00:30:00Z")
    envelope_id = outcome["envelope"]["runtime_observation_envelope_id"]

    record_path = (
        tmp_path
        / "backend"
        / "projects"
        / _world["project_id"]
        / "records"
        / "runtime_observation_envelope"
        / f"{envelope_id}.json"
    )
    body = json.loads(record_path.read_text())
    body["observed_fields"] = {"status": "TAMPERED"}
    record_path.write_text(json.dumps(body))

    with pytest.raises(CorruptStoreError):
        _world["store"].resolve_record(
            _world["project_id"], "runtime_observation_envelope", envelope_id
        )


def test_a_directly_committed_self_inconsistent_envelope_is_caught_at_domain_level(
    _world: dict[str, Any],
) -> None:
    """Bypassing the route entirely (a hypothetical bug/attacker able to commit records
    directly), a schema-valid but semantically self-inconsistent Envelope -- its own declared
    ``runtime_observation_semantic_fingerprint`` does not equal what its own real content
    recomputes to -- must never be trusted by the Evidence hand-off's own domain-level
    integrity check, independent of whatever the Store's own manifest layer catches."""

    target_identity = _world["target_identity"]
    boundary = boundary_for()
    target_fingerprint = runtime_target_fingerprint(target_identity)
    boundary_fingerprint = runtime_observation_boundary_fingerprint(boundary)
    request_identity = runtime_observation_request_identity(
        target_fingerprint, boundary_fingerprint, boundary["time_window"]["issued_at"]
    )
    envelope = {
        "schema_version": "0.1",
        "project_id": _world["project_id"],
        "target_identity": target_identity,
        "target_fingerprint": target_fingerprint,
        "boundary": boundary,
        "boundary_fingerprint": boundary_fingerprint,
        "observation_request_identity": request_identity,
        "observed_at": "2026-01-01T00:30:00Z",
        "observation_outcome": "OBSERVED",
        "observed_fields": {"status": "ok"},
        "observed_content_fingerprint": "sha256:" + "0" * 64,
        "adapter_identity": {"adapter": "forged", "version": "0.1"},
        "human_authority_ref": _world["human_authority_ref"],
    }
    envelope["runtime_observation_envelope_id"] = runtime_observation_envelope_id(envelope)
    # Forge the declared semantic fingerprint -- deliberately wrong.
    envelope["runtime_observation_semantic_fingerprint"] = "sha256:" + "f" * 64

    current_state = _world["store"].load_current(_world["project_id"])
    commit_records(
        _world["store"],
        _world["project_id"],
        current_state,
        "TX-RUNTIME-FORGED-ENVELOPE",
        [
            (
                "runtime_observation_envelope",
                envelope["runtime_observation_envelope_id"],
                envelope,
            )
        ],
    )

    receipt = RuntimeObservationReceipt(
        status="VERIFIED",
        runtime_observation_envelope_id=envelope["runtime_observation_envelope_id"],
        project_id=_world["project_id"],
        target_identity=target_identity,
        boundary=boundary,
        adapter_identity=envelope["adapter_identity"],
        human_authority_ref=_world["human_authority_ref"],
        input_refs=(dict(target_identity["project_binding_ref"]),),
        observations={
            "observation_outcome": "OBSERVED",
            "observed_content_fingerprint": envelope["observed_content_fingerprint"],
            "observed_at": envelope["observed_at"],
        },
    )
    request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", _world["project_id"]
    )
    with pytest.raises(RuntimeEnvelopeIntegrityError):
        route_runtime_observation_to_evidence(
            _world["store"], receipt, _world["project_id"], request
        )


# ---------------------------------------------------------------------------
# Receipt field tampering / cross-project relabeling at hand-off
# ---------------------------------------------------------------------------


@pytest.fixture
def _handed_off_world(_world: dict[str, Any]) -> dict[str, Any]:
    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=_world["target_identity"], fields={"status": "ok"})
    outcome = _observe(_world, adapter, boundary_for(), "2026-01-01T00:30:00Z")
    return {**_world, "outcome": outcome}


def test_receipt_with_a_tampered_target_identity_refuses(_handed_off_world: dict[str, Any]) -> None:
    world = _handed_off_world
    receipt = world["outcome"]["receipt"]
    forged_target = dict(receipt.target_identity)
    forged_target["instance_identity"] = "attacker-instance"
    tampered = replace(receipt, target_identity=forged_target)
    request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", world["project_id"]
    )
    with pytest.raises(RuntimeRequirementError):
        route_runtime_observation_to_evidence(
            world["store"], tampered, world["project_id"], request
        )


def test_receipt_with_a_tampered_boundary_refuses(_handed_off_world: dict[str, Any]) -> None:
    world = _handed_off_world
    receipt = world["outcome"]["receipt"]
    forged_boundary = dict(receipt.boundary)
    forged_boundary["timeout_seconds"] = 60
    tampered = replace(receipt, boundary=forged_boundary)
    request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", world["project_id"]
    )
    with pytest.raises(RuntimeRequirementError):
        route_runtime_observation_to_evidence(
            world["store"], tampered, world["project_id"], request
        )


def test_receipt_with_a_tampered_status_refuses(_handed_off_world: dict[str, Any]) -> None:
    world = _handed_off_world
    receipt = world["outcome"]["receipt"]
    tampered = replace(receipt, status="FAILED")
    request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", world["project_id"]
    )
    with pytest.raises(RuntimeRequirementError):
        route_runtime_observation_to_evidence(
            world["store"], tampered, world["project_id"], request
        )


def test_receipt_with_a_tampered_observations_refuses(_handed_off_world: dict[str, Any]) -> None:
    world = _handed_off_world
    receipt = world["outcome"]["receipt"]
    forged_observations = dict(receipt.observations)
    forged_observations["observed_content_fingerprint"] = "sha256:" + "9" * 64
    tampered = replace(receipt, observations=forged_observations)
    request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", world["project_id"]
    )
    with pytest.raises(RuntimeRequirementError):
        route_runtime_observation_to_evidence(
            world["store"], tampered, world["project_id"], request
        )


def test_receipt_with_a_tampered_adapter_identity_refuses(
    _handed_off_world: dict[str, Any],
) -> None:
    world = _handed_off_world
    receipt = world["outcome"]["receipt"]
    tampered = replace(receipt, adapter_identity={"adapter": "attacker_adapter", "version": "9.9"})
    request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", world["project_id"]
    )
    with pytest.raises(RuntimeRequirementError):
        route_runtime_observation_to_evidence(
            world["store"], tampered, world["project_id"], request
        )


def test_receipt_with_a_tampered_human_authority_ref_refuses(
    _handed_off_world: dict[str, Any],
) -> None:
    world = _handed_off_world
    receipt = world["outcome"]["receipt"]
    tampered = replace(
        receipt, human_authority_ref={"kind": "human_authority", "id": "AUTH-ATTACKER"}
    )
    request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", world["project_id"]
    )
    with pytest.raises(RuntimeRequirementError):
        route_runtime_observation_to_evidence(
            world["store"], tampered, world["project_id"], request
        )


def test_receipt_with_tampered_input_refs_refuses(_handed_off_world: dict[str, Any]) -> None:
    world = _handed_off_world
    receipt = world["outcome"]["receipt"]
    tampered = replace(
        receipt, input_refs=({"kind": "project_binding", "id": "PROJBIND-ATTACKER"},)
    )
    request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", world["project_id"]
    )
    with pytest.raises(RuntimeRequirementError):
        route_runtime_observation_to_evidence(
            world["store"], tampered, world["project_id"], request
        )


def test_cross_project_receipt_relabeling_refuses(_handed_off_world: dict[str, Any]) -> None:
    """A real Runtime Observation Receipt, genuinely produced for one project, must never be
    usable as Evidence for a different project."""

    world = _handed_off_world
    request = change_free_verification_evidence_request(provenance=None)
    with pytest.raises(RuntimeRequirementError):
        route_runtime_observation_to_evidence(
            world["store"], world["outcome"]["receipt"], "PRJ-SOME-OTHER-PROJECT", request
        )


def test_receipt_naming_an_uncommitted_envelope_id_refuses(
    _handed_off_world: dict[str, Any],
) -> None:
    world = _handed_off_world
    receipt = world["outcome"]["receipt"]
    tampered = replace(
        receipt,
        runtime_observation_envelope_id="RUNTIME-OBSERVATION-" + "0" * 64,
    )
    request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", world["project_id"]
    )
    with pytest.raises(RuntimeRequirementError):
        route_runtime_observation_to_evidence(
            world["store"], tampered, world["project_id"], request
        )


# ---------------------------------------------------------------------------
# Caller-built alternate Store/Boot world
# ---------------------------------------------------------------------------


def test_a_receipt_genuinely_produced_under_one_store_cannot_be_handed_off_through_another(
    tmp_path: Path,
) -> None:
    """A caller cannot substitute an entirely different (attacker-built or merely distinct)
    Store for the one a receipt's own envelope was genuinely committed to -- the hand-off
    resolves the envelope from *the store it is given*, and an unrelated store simply never
    has that record."""

    store_a, ctx_a = bound(tmp_path / "world-a")
    store_b, ctx_b = bound(tmp_path / "world-b")

    boot_a = boot_project(
        store_a, project_id=ctx_a["project_id"], project_binding_id=ctx_a["project_binding_id"]
    )
    target_identity = target_identity_for(ctx_a["project_binding_id"])
    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=target_identity, fields={"status": "ok"})
    outcome = observe_runtime_target(
        store_a,
        project_id=ctx_a["project_id"],
        project_binding_id=ctx_a["project_binding_id"],
        target_identity=target_identity,
        boundary=boundary_for(),
        adapter=adapter,
        observed_at="2026-01-01T00:30:00Z",
    )
    assert boot_a.project_id == ctx_a["project_id"]

    request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", ctx_b["project_id"]
    )
    with pytest.raises(RuntimeRequirementError):
        route_runtime_observation_to_evidence(
            store_b, outcome["receipt"], ctx_b["project_id"], request
        )
