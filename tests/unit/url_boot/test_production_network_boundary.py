"""Production decision-loop controls; primitive stubs do not prove real networking."""

from copy import deepcopy

import pytest
from tests.fixtures.url_boot_world import boundary_for

from manosube_agent_civilization.url_boot import route
from manosube_agent_civilization.url_boot.errors import UrlBootRequirementError
from manosube_agent_civilization.url_boot.network import canonical_source_identity


ADDRESS = "8.8.8.8"
SOURCE = canonical_source_identity("http://example.com:80/status")
BOUNDARY = boundary_for(admitted_hosts=["example.com"], admitted_ports=[80])
RESPONSE = {
    "outcome": "RESPONSE",
    "resolved_address": ADDRESS,
    "response_status": 200,
    "content_type": "application/json",
    "body": b'{"status":"ok","secret":"private"}',
}


def install(monkeypatch, resolutions, responses):
    resolutions = iter(resolutions)
    responses = iter(responses)
    calls = {"resolve": [], "connect": []}

    def resolve(identity):
        calls["resolve"].append(dict(identity))
        return next(resolutions)

    def connect(identity, address, boundary):
        calls["connect"].append((dict(identity), address))
        return next(responses)

    monkeypatch.setattr(route, "_perform_resolution_via_trusted_network", resolve)
    monkeypatch.setattr(route, "_perform_connection_via_trusted_network", connect)
    return calls


@pytest.mark.parametrize("resolution", [None, {"outcome": "OBSERVED"}, {"outcome": "TIMEOUT"}])
def test_invalid_resolution_never_connects(monkeypatch, resolution):
    calls = install(monkeypatch, [resolution], [])
    with pytest.raises(UrlBootRequirementError):
        route._fetch_with_route_owned_redirects_production(SOURCE, BOUNDARY)
    assert calls["connect"] == []


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "::1", "169.254.169.254"])
def test_private_address_is_refused_before_connection(monkeypatch, address):
    calls = install(monkeypatch, [{"outcome": "RESOLVED", "resolved_address": address}], [])
    result = route._fetch_with_route_owned_redirects_production(SOURCE, BOUNDARY)
    assert result["fetch_outcome"] == "BOUNDARY_REFUSED"
    assert calls["connect"] == []


@pytest.mark.parametrize(
    "response",
    [
        None,
        {"outcome": "OBSERVED"},
        {"outcome": "DNS_FAILURE"},
        {**RESPONSE, "resolved_address": "1.1.1.1"},
        {**RESPONSE, "response_status": "200"},
        {**RESPONSE, "body": "untrusted-text"},
    ],
)
def test_untrustworthy_connection_facts_are_refused(monkeypatch, response):
    install(monkeypatch, [{"outcome": "RESOLVED", "resolved_address": ADDRESS}], [response])
    with pytest.raises(UrlBootRequirementError):
        route._fetch_with_route_owned_redirects_production(SOURCE, BOUNDARY)


@pytest.mark.parametrize("outcome", ["CONNECTION_FAILURE", "TLS_FAILURE", "TIMEOUT"])
def test_transport_failures_never_claim_observed_fields(monkeypatch, outcome):
    install(
        monkeypatch, [{"outcome": "RESOLVED", "resolved_address": ADDRESS}], [{"outcome": outcome}]
    )
    result = route._fetch_with_route_owned_redirects_production(SOURCE, BOUNDARY)
    assert result["fetch_outcome"] == outcome
    assert result["observed_fields"] is None


def test_dns_failure_never_connects(monkeypatch):
    calls = install(monkeypatch, [{"outcome": "DNS_FAILURE"}], [])
    assert (
        route._fetch_with_route_owned_redirects_production(SOURCE, BOUNDARY)["fetch_outcome"]
        == "DNS_FAILURE"
    )
    assert calls["connect"] == []


@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({"oversized": True}, "OVERSIZED_RESPONSE"),
        ({"content_type": "text/plain"}, "UNSUPPORTED_MEDIA_TYPE"),
        ({"body": b"\xff"}, "MALFORMED"),
        ({"body": b"{broken"}, "MALFORMED"),
        ({"body": b"[]"}, "MALFORMED"),
        ({"response_status": 500}, "MALFORMED"),
        ({}, "OBSERVED"),
    ],
)
def test_production_classification_keeps_bounded_facts(monkeypatch, overrides, expected):
    calls = install(
        monkeypatch,
        [{"outcome": "RESOLVED", "resolved_address": ADDRESS}],
        [{**RESPONSE, **overrides}],
    )
    result = route._fetch_with_route_owned_redirects_production(SOURCE, BOUNDARY)
    assert result["fetch_outcome"] == expected
    assert len(calls["connect"]) == 1
    if expected == "OBSERVED":
        assert result["observed_fields"] == {"status": "ok"}
        assert result["resolution_provenance"] == [
            {"host": "example.com", "port": 80, "resolved_address": ADDRESS}
        ]
    else:
        assert result["observed_fields"] is None


def test_expected_identity_mismatch_cannot_be_observed(monkeypatch):
    install(monkeypatch, [{"outcome": "RESOLVED", "resolved_address": ADDRESS}], [RESPONSE])
    boundary = {**BOUNDARY, "expected_field": "identity", "expected_value": "required"}
    result = route._fetch_with_route_owned_redirects_production(SOURCE, boundary)
    assert result["fetch_outcome"] == "IDENTITY_MISMATCH"
    assert result["observed_fields"] is None


@pytest.mark.parametrize(
    "location",
    [
        "http://forbidden.example/status",
        "ftp://example.com/status",
        "http://user:secret@example.com/status",
    ],
)
def test_disallowed_redirect_is_never_reached(monkeypatch, location):
    calls = install(
        monkeypatch,
        [{"outcome": "RESOLVED", "resolved_address": ADDRESS}],
        [{**RESPONSE, "response_status": 302, "redirect_location": location}],
    )
    result = route._fetch_with_route_owned_redirects_production(SOURCE, BOUNDARY)
    assert result["fetch_outcome"] == "REDIRECT_REFUSED"
    assert len(calls["connect"]) == len(calls["resolve"]) == 1


@pytest.mark.parametrize(
    "second_address,expected", [(ADDRESS, "OBSERVED"), ("1.1.1.1", "BOUNDARY_REFUSED")]
)
def test_same_host_redirect_pins_the_first_address(monkeypatch, second_address, expected):
    calls = install(
        monkeypatch,
        [
            {"outcome": "RESOLVED", "resolved_address": ADDRESS},
            {"outcome": "RESOLVED", "resolved_address": second_address},
        ],
        [{**RESPONSE, "response_status": 302, "redirect_location": "/other"}, RESPONSE],
    )
    result = route._fetch_with_route_owned_redirects_production(SOURCE, BOUNDARY)
    assert result["fetch_outcome"] == expected
    assert len(calls["connect"]) == (2 if expected == "OBSERVED" else 1)
    assert len(calls["resolve"]) == 2
    if expected == "OBSERVED":
        assert result["effective_source_identity"]["path"] == "/other"
        assert len(result["resolution_provenance"]) == 1


def test_redirect_budget_is_enforced_before_following(monkeypatch):
    calls = install(
        monkeypatch,
        [{"outcome": "RESOLVED", "resolved_address": ADDRESS}],
        [{**RESPONSE, "response_status": 302, "redirect_location": "/other"}],
    )
    boundary = deepcopy(BOUNDARY)
    boundary["redirect_policy"]["max_redirects"] = 0
    result = route._fetch_with_route_owned_redirects_production(SOURCE, boundary)
    assert result["fetch_outcome"] == "REDIRECT_REFUSED"
    assert result["redirect_hop_count"] == 0
    assert len(calls["connect"]) == len(calls["resolve"]) == 1
