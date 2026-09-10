"""V2 (Issue #69): controlled URL Source Adapter contract proof.

Proves, through a real ``FileStateStore`` and the real
:func:`~manosube_agent_civilization.url_boot.route.observe_url_source`, that:

- every one of the eleven closed :data:`~manosube_agent_civilization.url_boot.types.
  URL_FETCH_OUTCOMES` is reachable end to end, and only ``"OBSERVED"`` ever commits a genuine,
  schema-valid envelope (P17-C7/P17-R1-F1 -- every other outcome returns a bounded, ephemeral,
  non-committed receipt);
- each outcome maps to the correct :data:`~manosube_agent_civilization.url_boot.types.
  RECEIPT_STATUSES` member;
- the route fails closed on a malformed/out-of-vocabulary single-hop adapter report, and on an
  adapter that declares no readable ``adapter_identity``;
- a response body carrying fields beyond the Boundary's own ``permitted_fields`` never leaks one
  into a committed Envelope's own ``observed_fields`` (the route's own bounded projection, never
  trusted from a replaceable adapter -- P17-R1-F2);
- an adapter cannot assert a route-only classification (``IDENTITY_MISMATCH`` and friends) by
  simply naming it in its own single-hop report: only the six
  :data:`~manosube_agent_civilization.url_boot.types.URL_HOP_TRANSPORT_OUTCOMES` are even
  readable from an adapter at all (P17-R1-F2).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.url_boot_world import bound, boundary_for

from manosube_agent_civilization.url_boot.adapter import FakeUrlSourceAdapter
from manosube_agent_civilization.url_boot.errors import UrlBootAdapterError
from manosube_agent_civilization.url_boot.network import canonical_source_identity
from manosube_agent_civilization.url_boot.route import observe_url_source
from manosube_agent_civilization.url_boot.types import (
    RECEIPT_STATUSES,
    URL_FETCH_OUTCOMES,
    URL_OUTCOME_TO_RECEIPT_STATUS,
)

_SOURCE_URL = "http://127.0.0.1:1/status"


@pytest.fixture
def _world(tmp_path: Path) -> dict[str, Any]:
    store, ctx = bound(tmp_path)
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "source_identity": canonical_source_identity(_SOURCE_URL),
        "boundary": boundary_for(admitted_hosts=["127.0.0.1"], admitted_ports=[1]),
    }


def _observe(
    world: dict[str, Any],
    adapter: Any,
    *,
    boundary: dict[str, Any] | None = None,
    observed_at: str = "2026-09-10T00:00:01Z",
) -> dict[str, Any]:
    return observe_url_source(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        source_identity=world["source_identity"],
        boundary=boundary if boundary is not None else world["boundary"],
        adapter=adapter,
        observed_at=observed_at,
    )


def test_url_fetch_outcomes_covers_exactly_eleven_members() -> None:
    assert len(URL_FETCH_OUTCOMES) == 11
    assert set(URL_OUTCOME_TO_RECEIPT_STATUS) == URL_FETCH_OUTCOMES
    assert set(URL_OUTCOME_TO_RECEIPT_STATUS.values()) <= RECEIPT_STATUSES


#: The single-hop transport failures that pass straight through to the overall fetch outcome
#: (:mod:`~manosube_agent_civilization.url_boot.route`'s own ``_HOP_FAILURE_OUTCOMES``).
_HOP_FAILURE_OUTCOMES = frozenset(
    {"DNS_FAILURE", "CONNECTION_FAILURE", "TLS_FAILURE", "TIMEOUT", "BOUNDARY_REFUSED"}
)


def _seed_for_outcome(
    adapter: FakeUrlSourceAdapter, source_identity: dict[str, Any], outcome: str
) -> dict[str, Any] | None:
    """Seed *adapter*'s own single-hop world so a real trip through the route derives exactly
    *outcome* -- returns a boundary override, or ``None`` to use ``_world["boundary"]`` as is."""

    if outcome in _HOP_FAILURE_OUTCOMES:
        adapter.seed_hop(source_identity=source_identity, outcome=outcome)
        return None
    if outcome == "REDIRECT_REFUSED":
        adapter.seed_hop(
            source_identity=source_identity,
            outcome="RESPONSE",
            response_status=302,
            redirect_location="http://out-of-scope.example/status",
        )
        return None
    if outcome == "OVERSIZED_RESPONSE":
        adapter.seed_hop(source_identity=source_identity, outcome="RESPONSE", oversized=True)
        return None
    if outcome == "UNSUPPORTED_MEDIA_TYPE":
        adapter.seed_hop(
            source_identity=source_identity, outcome="RESPONSE", content_type="text/plain"
        )
        return None
    if outcome == "MALFORMED":
        adapter.seed_hop(source_identity=source_identity, outcome="RESPONSE", response_status=500)
        return None
    if outcome == "IDENTITY_MISMATCH":
        adapter.seed_hop(
            source_identity=source_identity,
            outcome="RESPONSE",
            body=json.dumps({"status": "unexpected"}).encode("utf-8"),
        )
        return boundary_for(
            admitted_hosts=["127.0.0.1"],
            admitted_ports=[1],
            expected_field="status",
            expected_value="ok",
        )
    assert outcome == "OBSERVED"
    adapter.seed_hop(
        source_identity=source_identity,
        outcome="RESPONSE",
        body=json.dumps({"status": "ok"}).encode(),
    )
    return None


@pytest.mark.parametrize("outcome", sorted(URL_FETCH_OUTCOMES))
def test_every_fetch_outcome_is_reachable_end_to_end_and_only_observed_commits(
    _world: dict[str, Any], outcome: str
) -> None:
    adapter = FakeUrlSourceAdapter()
    boundary_override = _seed_for_outcome(adapter, _world["source_identity"], outcome)
    result = _observe(_world, adapter, boundary=boundary_override)
    assert result["receipt"].observations["fetch_outcome"] == outcome
    assert result["receipt"].status == URL_OUTCOME_TO_RECEIPT_STATUS[outcome]
    if outcome == "OBSERVED":
        assert result["envelope"] is not None
        assert result["envelope"]["fetch_outcome"] == "OBSERVED"
        assert result["envelope"]["observed_fields"] == {"status": "ok"}
        assert result["envelope"]["observed_content_fingerprint"] is not None
        assert (
            result["receipt"].url_source_observation_envelope_id
            == (result["envelope"]["url_source_observation_envelope_id"])
        )
    else:
        # P17-C7/P17-R1-F1: zero canonical State mutation, zero committed record.
        assert result["envelope"] is None
        assert result["receipt"].url_source_observation_envelope_id is None
        assert result["receipt"].observations["observed_content_fingerprint"] is None


def test_a_source_never_seeded_reports_connection_failure_not_a_silent_absence(
    _world: dict[str, Any],
) -> None:
    adapter = FakeUrlSourceAdapter()
    result = _observe(_world, adapter)
    assert result["envelope"] is None
    assert result["receipt"].observations["fetch_outcome"] == "CONNECTION_FAILURE"
    assert result["receipt"].status == "UNAVAILABLE"


def test_a_field_outside_permitted_fields_never_reaches_a_committed_envelope(
    _world: dict[str, Any],
) -> None:
    """The route's own bounded projection (P17-R1-F2) -- built directly from the raw response
    body it parsed itself, never from an adapter's own field selection -- excludes anything
    ``boundary.permitted_fields`` never named, by construction. This is a positive proof, not an
    exception: there is no longer an adapter-reported field selection to distrust at all."""

    adapter = FakeUrlSourceAdapter()
    adapter.seed_hop(
        source_identity=_world["source_identity"],
        outcome="RESPONSE",
        body=json.dumps({"status": "ok", "secret": "leak"}).encode("utf-8"),
    )
    result = _observe(_world, adapter)
    assert result["envelope"]["observed_fields"] == {"status": "ok"}
    assert "secret" not in result["envelope"]["observed_fields"]


def test_the_route_refuses_an_out_of_vocabulary_single_hop_outcome(_world: dict[str, Any]) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.force_result({"outcome": "NOT-A-REAL-OUTCOME"})
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_route_refuses_an_adapter_asserting_a_route_only_classification_directly(
    _world: dict[str, Any],
) -> None:
    """P17-R1-F2's own decisive control: ``IDENTITY_MISMATCH`` (and every other overall
    :data:`~manosube_agent_civilization.url_boot.types.URL_FETCH_OUTCOMES` member that is not
    also a :data:`~manosube_agent_civilization.url_boot.types.URL_HOP_TRANSPORT_OUTCOMES` member)
    is not even a readable single-hop outcome any more -- an adapter naming it directly is a
    malformed report, refused before any classification of its own content is ever attempted."""

    adapter = FakeUrlSourceAdapter()
    adapter.force_result(
        {
            "outcome": "IDENTITY_MISMATCH",
            "resolved_address": "203.0.113.10",
            "response_status": 200,
            "content_type": "application/json",
            "redirect_location": None,
            "body": b"{}",
            "oversized": False,
        }
    )
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_route_refuses_a_non_mapping_adapter_report(_world: dict[str, Any]) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.fetch_one_hop = lambda *, source_identity, boundary: "not-a-mapping"  # type: ignore[method-assign]
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_route_refuses_an_adapter_with_no_readable_identity(_world: dict[str, Any]) -> None:
    class _NoIdentityAdapter:
        def fetch_one_hop(self, *, source_identity: Any, boundary: Any) -> dict[str, Any]:
            return {
                "outcome": "RESPONSE",
                "resolved_address": "203.0.113.10",
                "response_status": 200,
                "content_type": "application/json",
                "redirect_location": None,
                "body": json.dumps({"status": "ok"}).encode("utf-8"),
                "oversized": False,
            }

    with pytest.raises(UrlBootAdapterError):
        _observe(_world, _NoIdentityAdapter())


def test_a_response_missing_a_readable_resolved_address_is_refused(_world: dict[str, Any]) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.force_result(
        {
            "outcome": "RESPONSE",
            "resolved_address": None,
            "response_status": 200,
            "content_type": "application/json",
            "redirect_location": None,
            "body": b"{}",
            "oversized": False,
        }
    )
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_fake_adapters_own_call_count_is_exactly_one_hop_per_direct_observation(
    _world: dict[str, Any],
) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.seed_hop(
        source_identity=_world["source_identity"],
        outcome="RESPONSE",
        body=json.dumps({"status": "ok"}).encode(),
    )
    _observe(_world, adapter)
    assert adapter.fetch_call_count == 1
    _observe(_world, adapter, observed_at="2026-09-10T00:00:02Z")
    assert adapter.fetch_call_count == 2
