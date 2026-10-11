"""Execute the shipped observation/commit orchestration with protocol doubles.

Boot, Binding identity, envelope derivation and receipt construction are real
owners. Network primitives and Store persistence are unit doubles, so these
controls claim orchestration behavior, not live networking or crash durability.
"""

from copy import deepcopy

import pytest
from tests.fixtures.product_binding import bind_project_kwargs
from tests.fixtures.url_boot_world import boundary_for

from manosube_agent_civilization.binding.engine import assemble_project_binding
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError
from manosube_agent_civilization.url_boot import route
from manosube_agent_civilization.url_boot.errors import UrlBootError
from manosube_agent_civilization.url_boot.network import canonical_source_identity


class ObservationPlanStore:
    def __init__(self):
        inputs = bind_project_kwargs()
        self.project = inputs["project_id"]
        self.binding = assemble_project_binding(
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
        self.state = inputs["genesis_state"]
        self.state["semantic_fingerprint"] = fingerprint_project_state(self.state).as_dict()
        self.records = {
            ("project_binding", self.binding["project_binding_id"]): self.binding,
            ("objective_revision", inputs["objective_revision"]["objective_revision_id"]): inputs[
                "objective_revision"
            ],
            ("authority_rule", inputs["authority_rule"]["authority_rule_id"]): inputs[
                "authority_rule"
            ],
        }
        self.failures = []
        self.attempts = 0

    def resolve_record(self, project, kind, record_id):
        return deepcopy(self.records.get((kind, record_id)))

    def read_current_consistent(self, project):
        return deepcopy(self.state)

    load_current = read_current_consistent

    def commit(
        self, project, revision, fingerprint, next_state, transition, *, records, fault=None
    ):
        self.attempts += 1
        if self.failures:
            raise self.failures.pop(0)
        assert project == self.project and revision == self.state["state_revision"]
        assert fingerprint == self.state["semantic_fingerprint"]
        assert next_state["state_revision"] == revision + 1
        assert next_state["semantic_state"] == self.state["semantic_state"]
        assert transition["after_state"] == next_state
        assert next_state["semantic_fingerprint"] == fingerprint_project_state(next_state).as_dict()
        self.state = deepcopy(next_state)
        for kind, record_id, body in records:
            assert kind == "url_source_observation_envelope"
            self.records[(kind, record_id)] = deepcopy(body)
        return deepcopy(next_state)


@pytest.fixture
def world(monkeypatch):
    store = ObservationPlanStore()
    calls = []

    def resolve(identity):
        calls.append("resolve")
        return {"outcome": "RESOLVED", "resolved_address": "8.8.8.8"}

    def connect(identity, address, boundary):
        calls.append("connect")
        return {
            "outcome": "RESPONSE",
            "resolved_address": address,
            "response_status": 200,
            "content_type": "application/json",
            "body": b'{"status":"ok","note":"private","extra":"discard"}',
        }

    monkeypatch.setattr(route, "_perform_resolution_via_trusted_network", resolve)
    monkeypatch.setattr(route, "_perform_connection_via_trusted_network", connect)
    observer = route.compose_url_source_observer(
        store,
        project_id=store.project,
        project_binding_id=store.binding["project_binding_id"],
        adapter_identity={"adapter": "unit", "version": "1"},
    )
    return store, calls, observer


def observe(observer, **overrides):
    return observer(
        canonical_source_identity("http://example.com/status"),
        boundary_for(admitted_hosts=["example.com"], **overrides),
        "2026-09-10T00:00:01Z",
    )


def test_the_production_route_commits_only_the_bounded_observation_plan(world):
    store, calls, observer = world
    before = deepcopy(store.state)
    result = observe(observer, permitted_fields=["status", "note"], redaction_fields=["note"])
    assert result["receipt"].status == "VERIFIED"
    assert result["envelope"]["observed_fields"] == {"status": "ok", "note": "<REDACTED>"}
    assert store.attempts == 1 and calls == ["resolve", "connect"]
    assert store.state["state_revision"] == before["state_revision"] + 1
    assert (
        store.records[
            (
                "url_source_observation_envelope",
                result["receipt"].url_source_observation_envelope_id,
            )
        ]
        == result["envelope"]
    )


def test_a_failed_production_fetch_returns_no_envelope_and_makes_no_commit(world, monkeypatch):
    store, calls, observer = world
    before = deepcopy(store.state)
    monkeypatch.setattr(
        route, "_perform_resolution_via_trusted_network", lambda _: {"outcome": "DNS_FAILURE"}
    )
    result = observe(observer)
    assert result["envelope"] is None and result["receipt"].status == "UNAVAILABLE"
    assert result["receipt"].url_source_observation_envelope_id is None
    assert store.state == before and store.attempts == 0 and calls == []


@pytest.mark.parametrize(
    "failures,attempts",
    [
        ([StaleStateError("contention")], 2),
        ([StaleStateError("contention")] * 8, 8),
        ([RecordConflictError("foreign envelope")], 1),
    ],
)
def test_unrelated_contention_is_retried_but_conflicts_cannot_produce_verified_receipts(
    world, failures, attempts
):
    store, calls, observer = world
    before = deepcopy(store.state)
    store.failures = list(failures)
    if attempts == 2:
        assert observe(observer)["receipt"].status == "VERIFIED"
        assert store.state["state_revision"] == before["state_revision"] + 1
    else:
        with pytest.raises(UrlBootError):
            observe(observer)
        assert store.state == before
    assert store.attempts == attempts and calls == ["resolve", "connect"]


def test_corrupt_derived_identity_is_refused_before_any_commit(world, monkeypatch):
    store, calls, observer = world
    real = route.derive_url_source_observation_envelope

    def corrupt(**kwargs):
        envelope = real(**kwargs)
        envelope["url_source_observation_semantic_fingerprint"] = "sha256:" + "f" * 64
        return envelope

    monkeypatch.setattr(route, "derive_url_source_observation_envelope", corrupt)
    with pytest.raises(UrlBootError):
        observe(observer)
    assert store.attempts == 0 and calls == ["resolve", "connect"]


@pytest.mark.parametrize(
    "window",
    [
        {"issued_at": "2026-09-12T00:00:00Z", "expires_at": "2026-09-10T00:00:00Z"},
        {"issued_at": "2026-09-11T00:00:00Z", "expires_at": "2026-09-12T00:00:00Z"},
    ],
)
def test_invalid_or_expired_window_reaches_neither_network_nor_commit(world, window):
    store, calls, observer = world
    with pytest.raises(UrlBootError):
        observer(
            canonical_source_identity("http://example.com/status"),
            {**boundary_for(admitted_hosts=["example.com"]), "time_window": window},
            "2026-09-10T00:00:01Z",
        )
    assert store.attempts == 0 and calls == []


@pytest.mark.parametrize(
    "identity", [None, [], {1: "bad-key"}, {"nested": ()}, {"nested": {1: "bad-key"}}]
)
def test_executable_or_non_plain_identity_data_is_refused_at_composition(identity):
    store = ObservationPlanStore()
    with pytest.raises(UrlBootError):
        route.compose_url_source_observer(
            store,
            project_id=store.project,
            project_binding_id=store.binding["project_binding_id"],
            adapter_identity=identity,
        )
    assert store.attempts == 0


@pytest.mark.parametrize("identity", ["", "../outside", "http://example.com", "with/path"])
def test_a_locator_cannot_replace_the_bound_project_identity(identity):
    store = ObservationPlanStore()
    observer = route.compose_url_source_observer(
        store,
        project_id=identity,
        project_binding_id=store.binding["project_binding_id"],
        adapter_identity={"adapter": "unit"},
    )
    with pytest.raises(UrlBootError):
        observe(observer)
    assert store.attempts == 0
