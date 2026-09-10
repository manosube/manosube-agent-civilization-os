"""V2 (Issue #69): controlled URL Source Adapter contract proof.

Proves, through a real ``FileStateStore`` and the real
:func:`~manosube_agent_civilization.url_boot.route.observe_url_source`, that:

- every one of the eleven closed :data:`~manosube_agent_civilization.url_boot.types.
  URL_FETCH_OUTCOMES` is reachable end to end and commits a genuine, schema-valid envelope;
- each outcome maps to the correct :data:`~manosube_agent_civilization.url_boot.types.
  RECEIPT_STATUSES` member;
- the route fails closed on a malformed/out-of-vocabulary adapter report, on an adapter
  reporting a field outside the Boundary's own ``permitted_fields``, and on an adapter that
  declares no readable ``adapter_identity``;
- redirect-hop bookkeeping the Boundary's own ``redirect_policy.max_redirects`` disagrees with
  is refused before persistence.
"""

from __future__ import annotations

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
    world: dict[str, Any], adapter: Any, observed_at: str = "2026-09-10T00:00:01Z"
) -> dict[str, Any]:
    return observe_url_source(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        source_identity=world["source_identity"],
        boundary=world["boundary"],
        adapter=adapter,
        observed_at=observed_at,
    )


def test_url_fetch_outcomes_covers_exactly_eleven_members() -> None:
    assert len(URL_FETCH_OUTCOMES) == 11
    assert set(URL_OUTCOME_TO_RECEIPT_STATUS) == URL_FETCH_OUTCOMES
    assert set(URL_OUTCOME_TO_RECEIPT_STATUS.values()) <= RECEIPT_STATUSES


#: The same "no response was ever reached" outcome set
#: :mod:`~manosube_agent_civilization.url_boot.route` itself now enforces -- these must carry a
#: null ``response_status``; every other outcome means a response was genuinely reached and
#: classified, and must carry a real one.
_NO_RESPONSE_OUTCOMES = frozenset(
    {
        "DNS_FAILURE",
        "CONNECTION_FAILURE",
        "TLS_FAILURE",
        "TIMEOUT",
        "BOUNDARY_REFUSED",
        "REDIRECT_REFUSED",
    }
)


@pytest.mark.parametrize("outcome", sorted(URL_FETCH_OUTCOMES))
def test_every_fetch_outcome_is_reachable_end_to_end_and_commits_correctly(
    _world: dict[str, Any], outcome: str
) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.seed_source(
        source_identity=_world["source_identity"],
        fields={"status": "ok"},
        fetch_outcome=outcome,
        response_status=None if outcome in _NO_RESPONSE_OUTCOMES else 200,
    )
    result = _observe(_world, adapter)
    assert result["envelope"]["fetch_outcome"] == outcome
    assert result["receipt"].status == URL_OUTCOME_TO_RECEIPT_STATUS[outcome]
    if outcome == "OBSERVED":
        assert result["envelope"]["observed_fields"] == {"status": "ok"}
        assert result["envelope"]["observed_content_fingerprint"] is not None
    else:
        assert result["envelope"]["observed_fields"] is None
        assert result["envelope"]["observed_content_fingerprint"] is None


def test_a_source_never_seeded_reports_connection_failure_not_a_silent_absence(
    _world: dict[str, Any],
) -> None:
    adapter = FakeUrlSourceAdapter()
    result = _observe(_world, adapter)
    assert result["envelope"]["fetch_outcome"] == "CONNECTION_FAILURE"
    assert result["receipt"].status == "UNAVAILABLE"


def test_the_route_refuses_a_field_the_boundary_never_permitted(_world: dict[str, Any]) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.seed_source(
        source_identity=_world["source_identity"], fields={"status": "ok", "secret": "leak"}
    )
    adapter.force_result(
        {
            "fetch_outcome": "OBSERVED",
            "effective_source_identity": _world["source_identity"],
            "response_status": 200,
            "redirect_hop_count": 0,
            "observed_fields": {"status": "ok", "secret": "leak"},
        }
    )
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_route_refuses_a_malformed_adapter_report(_world: dict[str, Any]) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.force_result({"fetch_outcome": "NOT-A-REAL-OUTCOME"})
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


# ---------------------------------------------------------------------------
# Outcome/effective-identity/response-status consistency (P1-R1-F3): a review finding on this
# delivery's own PR -- the route must never accept an adapter report whose own fetch_outcome
# contradicts its own effective_source_identity/response_status, even though every field
# individually passes schema/type validation. Each case below is a genuine, individually
# schema-valid report a buggy or malicious replaceable adapter could return.
# ---------------------------------------------------------------------------


def test_the_route_refuses_observed_with_no_effective_source_identity(
    _world: dict[str, Any],
) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.force_result(
        {
            "fetch_outcome": "OBSERVED",
            "effective_source_identity": None,
            "response_status": 200,
            "redirect_hop_count": 0,
            "observed_fields": {"status": "ok"},
        }
    )
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_route_refuses_observed_with_no_response_status(_world: dict[str, Any]) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.force_result(
        {
            "fetch_outcome": "OBSERVED",
            "effective_source_identity": _world["source_identity"],
            "response_status": None,
            "redirect_hop_count": 0,
            "observed_fields": {"status": "ok"},
        }
    )
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_route_refuses_observed_with_a_non_2xx_response_status(
    _world: dict[str, Any],
) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.force_result(
        {
            "fetch_outcome": "OBSERVED",
            "effective_source_identity": _world["source_identity"],
            "response_status": 404,
            "redirect_hop_count": 0,
            "observed_fields": {"status": "ok"},
        }
    )
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_route_refuses_a_no_response_outcome_carrying_a_reached_identity(
    _world: dict[str, Any],
) -> None:
    """A ``DNS_FAILURE`` (or any other never-reached-a-response outcome) claiming a non-null
    ``effective_source_identity`` would let a route consumer believe a source was genuinely
    identified when no response was ever received -- refused before commit."""

    adapter = FakeUrlSourceAdapter()
    adapter.force_result(
        {
            "fetch_outcome": "DNS_FAILURE",
            "effective_source_identity": _world["source_identity"],
            "response_status": None,
            "redirect_hop_count": 0,
            "observed_fields": None,
        }
    )
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_route_refuses_a_response_reached_failure_with_no_effective_source_identity(
    _world: dict[str, Any],
) -> None:
    """``MALFORMED`` (and the other response-reached failure outcomes) means a real response was
    received and classified -- an adapter reporting one of these with no effective identity is
    contradicting its own claim to have reached and classified something."""

    adapter = FakeUrlSourceAdapter()
    adapter.force_result(
        {
            "fetch_outcome": "MALFORMED",
            "effective_source_identity": None,
            "response_status": 500,
            "redirect_hop_count": 0,
            "observed_fields": None,
        }
    )
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_route_refuses_a_response_reached_failure_with_no_response_status(
    _world: dict[str, Any],
) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.force_result(
        {
            "fetch_outcome": "MALFORMED",
            "effective_source_identity": _world["source_identity"],
            "response_status": None,
            "redirect_hop_count": 0,
            "observed_fields": None,
        }
    )
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_route_refuses_a_non_mapping_adapter_report(_world: dict[str, Any]) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.force_result(None)
    adapter.fetch = lambda *, source_identity, boundary: "not-a-mapping"  # type: ignore[method-assign]
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_route_refuses_an_adapter_with_no_readable_identity(_world: dict[str, Any]) -> None:
    class _NoIdentityAdapter:
        def fetch(self, *, source_identity: Any, boundary: Any) -> dict[str, Any]:
            return {
                "fetch_outcome": "OBSERVED",
                "effective_source_identity": source_identity,
                "response_status": 200,
                "redirect_hop_count": 0,
                "observed_fields": {"status": "ok"},
            }

    with pytest.raises(UrlBootAdapterError):
        _observe(_world, _NoIdentityAdapter())


def test_the_route_refuses_a_redirect_hop_count_exceeding_the_boundarys_own_max_redirects(
    _world: dict[str, Any],
) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.seed_source(
        source_identity=_world["source_identity"],
        fields={"status": "ok"},
        redirect_hop_count=_world["boundary"]["redirect_policy"]["max_redirects"] + 1,
    )
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_fake_adapters_own_call_count_is_exactly_one_per_observation(
    _world: dict[str, Any],
) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.seed_source(source_identity=_world["source_identity"], fields={"status": "ok"})
    _observe(_world, adapter)
    assert adapter.fetch_call_count == 1
    _observe(_world, adapter, observed_at="2026-09-10T00:00:02Z")
    assert adapter.fetch_call_count == 2
