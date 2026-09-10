"""V2 (Issue #69): controlled URL Source Adapter contract proof.

Proves, through a real ``FileStateStore`` and this repository's own internal, fully
deterministic route-logic test entry point (never public ``observe_url_source`` -- see
``test_url_boot_static_conformance.py``/``route.py``'s own module docstring for why: since
Structural Review Round 3, P17-R3-F1, no adapter's own ``connect_hop`` is ever consulted by
either genuinely-networked public entry point at all, so exercising route.py's own
classification/validation logic with a controlled, seeded connect-stage report requires calling
:func:`~manosube_agent_civilization.url_boot.route._observe_url_source_impl` directly, bound to
:func:`~manosube_agent_civilization.url_boot.route._perform_connection_via_adapter`), that:

- every one of the eleven closed :data:`~manosube_agent_civilization.url_boot.types.
  URL_FETCH_OUTCOMES` is reachable end to end, and only ``"OBSERVED"`` ever commits a genuine,
  schema-valid envelope (P17-C7/P17-R1-F1 -- every other outcome returns a bounded, ephemeral,
  non-committed receipt);
- each outcome maps to the correct :data:`~manosube_agent_civilization.url_boot.types.
  RECEIPT_STATUSES` member;
- the route fails closed on a malformed/out-of-vocabulary single-hop adapter report at either
  stage, and on an adapter that declares no readable ``adapter_identity``;
- a response body carrying fields beyond the Boundary's own ``permitted_fields`` never leaks one
  into a committed Envelope's own ``observed_fields`` (the route's own bounded projection, never
  trusted from a replaceable adapter -- P17-R1-F2);
- an adapter cannot assert a route-only classification (``IDENTITY_MISMATCH``/``BOUNDARY_REFUSED``
  and friends) by simply naming it in its own single-hop report: neither
  :data:`~manosube_agent_civilization.url_boot.types.URL_HOP_RESOLVE_OUTCOMES` nor
  :data:`~manosube_agent_civilization.url_boot.types.URL_HOP_CONNECT_OUTCOMES` even contains those
  names (P17-R1-F2/P17-R2-F1);
- a private/loopback/invalid resolved address can never become a successful ``RESPONSE`` --
  the route classifies it itself, independent of anything the adapter reports (P17-R2-F1).

A separate section at the end of this file
(``test_production_observe_url_source_never_reaches_any_adapter_connect_method`` and friends)
proves the P17-R3-F1 production trust boundary itself: through the real, public
``observe_url_source``, a replaceable adapter's own connect-capable method (however named) is
*structurally never invoked at all* -- not "invoked and its report checked", but never reached.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.url_boot_world import bound, boundary_for

from manosube_agent_civilization.url_boot.adapter import FakeUrlSourceAdapter
from manosube_agent_civilization.url_boot.errors import UrlBootAdapterError, UrlBootRequirementError
from manosube_agent_civilization.url_boot.network import canonical_source_identity
from manosube_agent_civilization.url_boot.route import (
    _observe_url_source_impl,
    _perform_connection_via_adapter,
    _require_safe_resolved_address_production,
    observe_url_source,
)
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
    """This repository's own internal deterministic route-logic test entry -- never reachable
    from either genuinely-networked public entry point (P17-R3-F1); see this module's own
    docstring."""

    return _observe_url_source_impl(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        source_identity=world["source_identity"],
        boundary=boundary if boundary is not None else world["boundary"],
        adapter=adapter,
        observed_at=observed_at,
        classify_resolved_address=_require_safe_resolved_address_production,
        perform_connection=_perform_connection_via_adapter,
    )


def test_url_fetch_outcomes_covers_exactly_eleven_members() -> None:
    assert len(URL_FETCH_OUTCOMES) == 11
    assert set(URL_OUTCOME_TO_RECEIPT_STATUS) == URL_FETCH_OUTCOMES
    assert set(URL_OUTCOME_TO_RECEIPT_STATUS.values()) <= RECEIPT_STATUSES


#: The single-hop connect-stage failures that pass straight through to the overall fetch outcome
#: (:mod:`~manosube_agent_civilization.url_boot.route`'s own ``_HOP_CONNECT_FAILURE_OUTCOMES``).
_HOP_CONNECT_FAILURE_OUTCOMES = frozenset({"CONNECTION_FAILURE", "TLS_FAILURE", "TIMEOUT"})

#: A resolved address production ``observe_url_source`` always refuses -- loopback, never
#: admitted regardless of what hostname the Boundary's own ``network_scope`` names.
_UNSAFE_RESOLVED_ADDRESS = "127.0.0.1"
_SAFE_RESOLVED_ADDRESS = "93.184.216.34"


def _seed_for_outcome(
    adapter: FakeUrlSourceAdapter, source_identity: dict[str, Any], outcome: str
) -> dict[str, Any] | None:
    """Seed *adapter*'s own single-hop world so a real trip through the route derives exactly
    *outcome* -- returns a boundary override, or ``None`` to use ``_world["boundary"]`` as is."""

    if outcome == "DNS_FAILURE" or outcome in _HOP_CONNECT_FAILURE_OUTCOMES:
        adapter.seed_hop(source_identity=source_identity, outcome=outcome)
        return None
    if outcome == "BOUNDARY_REFUSED":
        # P17-R2-F1: never seeded as an adapter-asserted outcome (it no longer exists in either
        # adapter-reportable vocabulary) -- reached only via a real, unsafe resolved address the
        # route itself independently classifies.
        adapter.seed_hop(
            source_identity=source_identity,
            outcome="RESPONSE",
            resolved_address=_UNSAFE_RESOLVED_ADDRESS,
        )
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


def test_a_source_never_seeded_reports_dns_failure_not_a_silent_absence(
    _world: dict[str, Any],
) -> None:
    adapter = FakeUrlSourceAdapter()
    result = _observe(_world, adapter)
    assert result["envelope"] is None
    assert result["receipt"].observations["fetch_outcome"] == "DNS_FAILURE"
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


def test_a_private_resolved_address_never_becomes_a_successful_response(
    _world: dict[str, Any],
) -> None:
    """P17-R2-F1's own decisive control: a private (non-loopback) resolved address is refused by
    the route's own independent classification exactly like a loopback one -- never trusted from
    the adapter's own successful-looking ``RESPONSE`` report."""

    adapter = FakeUrlSourceAdapter()
    adapter.seed_hop(
        source_identity=_world["source_identity"],
        outcome="RESPONSE",
        resolved_address="10.0.0.5",
        body=json.dumps({"status": "ok"}).encode(),
    )
    result = _observe(_world, adapter)
    assert result["envelope"] is None
    assert result["receipt"].observations["fetch_outcome"] == "BOUNDARY_REFUSED"


def test_the_route_refuses_an_out_of_vocabulary_resolve_outcome(_world: dict[str, Any]) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.force_resolve_result({"outcome": "NOT-A-REAL-OUTCOME"})
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_route_refuses_an_out_of_vocabulary_connect_outcome(_world: dict[str, Any]) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.seed_hop(source_identity=_world["source_identity"], outcome="RESPONSE")
    adapter.force_connect_result({"outcome": "NOT-A-REAL-OUTCOME"})
    with pytest.raises(UrlBootRequirementError):
        _observe(_world, adapter)


@pytest.mark.parametrize("stage_outcome", ["BOUNDARY_REFUSED", "IDENTITY_MISMATCH", "MALFORMED"])
def test_the_route_refuses_an_adapter_asserting_a_route_only_classification_at_resolve_stage(
    _world: dict[str, Any], stage_outcome: str
) -> None:
    """Neither ``BOUNDARY_REFUSED`` nor any overall :data:`~manosube_agent_civilization.url_boot.
    types.URL_FETCH_OUTCOMES` member that also is not a genuine resolve-stage outcome is even a
    readable ``resolve_hop`` report any more -- an adapter naming one directly is a malformed
    report, refused before any classification of its own is ever attempted (P17-R1-F2/P17-R2-F1)."""

    adapter = FakeUrlSourceAdapter()
    adapter.force_resolve_result({"outcome": stage_outcome, "resolved_address": "93.184.216.34"})
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


@pytest.mark.parametrize("stage_outcome", ["BOUNDARY_REFUSED", "IDENTITY_MISMATCH", "DNS_FAILURE"])
def test_the_route_refuses_an_adapter_asserting_a_route_only_classification_at_connect_stage(
    _world: dict[str, Any], stage_outcome: str
) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.seed_hop(source_identity=_world["source_identity"], outcome="RESPONSE")
    adapter.force_connect_result(
        {
            "outcome": stage_outcome,
            "resolved_address": _SAFE_RESOLVED_ADDRESS,
            "response_status": 200,
            "content_type": "application/json",
            "redirect_location": None,
            "body": b"{}",
            "oversized": False,
        }
    )
    with pytest.raises(UrlBootRequirementError):
        _observe(_world, adapter)


def test_the_route_refuses_a_non_mapping_resolve_report(_world: dict[str, Any]) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.resolve_hop = lambda *, source_identity: "not-a-mapping"  # type: ignore[method-assign]
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_the_route_refuses_a_non_mapping_connect_report(_world: dict[str, Any]) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.seed_hop(source_identity=_world["source_identity"], outcome="RESPONSE")
    adapter.connect_hop = (  # type: ignore[method-assign]
        lambda *, source_identity, boundary, admitted_address: "not-a-mapping"
    )
    with pytest.raises(UrlBootRequirementError):
        _observe(_world, adapter)


def test_the_route_refuses_an_adapter_with_no_readable_identity(_world: dict[str, Any]) -> None:
    class _NoIdentityAdapter:
        def resolve_hop(self, *, source_identity: Any) -> dict[str, Any]:
            return {"outcome": "RESOLVED", "resolved_address": _SAFE_RESOLVED_ADDRESS}

        def connect_hop(
            self, *, source_identity: Any, boundary: Any, admitted_address: str
        ) -> dict[str, Any]:
            return {
                "outcome": "RESPONSE",
                "resolved_address": admitted_address,
                "response_status": 200,
                "content_type": "application/json",
                "redirect_location": None,
                "body": json.dumps({"status": "ok"}).encode("utf-8"),
                "oversized": False,
            }

    with pytest.raises(UrlBootAdapterError):
        _observe(_world, _NoIdentityAdapter())


def test_a_resolved_report_missing_a_readable_resolved_address_is_refused(
    _world: dict[str, Any],
) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.force_resolve_result({"outcome": "RESOLVED", "resolved_address": None})
    with pytest.raises(UrlBootAdapterError):
        _observe(_world, adapter)


def test_an_adapter_cannot_connect_to_an_address_different_from_the_route_admitted_one(
    _world: dict[str, Any],
) -> None:
    """P17-R2-F1's own decisive control, retained as defense-in-depth on the internal
    deterministic connector (P17-R3-F1): the route hands the adapter one exact admitted address
    to connect to; an adapter reporting having connected anywhere else is refused, never trusted
    as a successful ``RESPONSE`` for the address the route itself admitted. Production
    ``observe_url_source`` closes this far more strongly -- see
    ``test_production_never_reaches_any_adapter_connect_method`` below: no adapter method is ever
    called there at all, so there is no report to disagree with in the first place."""

    adapter = FakeUrlSourceAdapter()
    adapter.seed_hop(
        source_identity=_world["source_identity"],
        outcome="RESPONSE",
        resolved_address=_SAFE_RESOLVED_ADDRESS,
    )
    adapter.force_connect_result(
        {
            "outcome": "RESPONSE",
            "resolved_address": "198.51.100.7",
            "response_status": 200,
            "content_type": "application/json",
            "redirect_location": None,
            "body": json.dumps({"status": "ok"}).encode("utf-8"),
            "oversized": False,
        }
    )
    with pytest.raises(UrlBootRequirementError):
        _observe(_world, adapter)


def test_the_fake_adapters_own_call_counts_are_exactly_one_hop_per_direct_observation(
    _world: dict[str, Any],
) -> None:
    adapter = FakeUrlSourceAdapter()
    adapter.seed_hop(
        source_identity=_world["source_identity"],
        outcome="RESPONSE",
        body=json.dumps({"status": "ok"}).encode(),
    )
    _observe(_world, adapter)
    assert adapter.resolve_call_count == 1
    assert adapter.connect_call_count == 1
    _observe(_world, adapter, observed_at="2026-09-10T00:00:02Z")
    assert adapter.resolve_call_count == 2
    assert adapter.connect_call_count == 2


# ---------------------------------------------------------------------------------------------
# Structural Review Round 3 (P17-R3-F1): the production trust boundary itself -- a replaceable
# adapter's own connect-capable method, however named, is never invoked by the real, public
# ``observe_url_source`` at all, regardless of what a malicious implementation would do if it
# ever were. These proofs use the real, public entry point, never the internal deterministic one
# ``_observe`` above delegates to.
# ---------------------------------------------------------------------------------------------


def test_production_observe_url_source_never_reaches_any_adapter_connect_method(
    _world: dict[str, Any],
) -> None:
    """The decisive P17-R3-F1 control: a malicious adapter's own ``connect_hop`` -- which, if it
    were ever invoked, would fabricate a completely different, successful ``RESPONSE`` -- is
    never called at all through the real, public ``observe_url_source``. Not "invoked and its
    report checked and refused": never reached, proved by the call count staying zero. The real
    target (``127.0.0.1:1``, an unreachable port in this test environment) genuinely fails at the
    trusted network layer -- proving the derived outcome came from real I/O, never from the
    malicious adapter's own fabricated response."""

    connect_call_count = {"count": 0}

    class _MaliciousAdapter:
        def __init__(self) -> None:
            self.adapter_identity: Mapping[str, Any] = {"adapter": "malicious", "version": "0.1"}

        def resolve_hop(self, *, source_identity: Any) -> dict[str, Any]:
            return {"outcome": "RESOLVED", "resolved_address": _SAFE_RESOLVED_ADDRESS}

        def connect_hop(
            self, *, source_identity: Any, boundary: Any, admitted_address: str
        ) -> dict[str, Any]:
            connect_call_count["count"] += 1
            return {
                "outcome": "RESPONSE",
                "resolved_address": admitted_address,
                "response_status": 200,
                "content_type": "application/json",
                "redirect_location": None,
                "body": json.dumps({"status": "fabricated-by-malicious-adapter"}).encode("utf-8"),
                "oversized": False,
            }

    result = observe_url_source(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        source_identity=_world["source_identity"],
        boundary=_world["boundary"],
        adapter=_MaliciousAdapter(),
        observed_at="2026-09-10T00:00:01Z",
    )

    assert connect_call_count["count"] == 0
    assert result["envelope"] is None
    assert result["receipt"].observations["fetch_outcome"] in ("CONNECTION_FAILURE", "TIMEOUT")
    assert "fabricated-by-malicious-adapter" not in str(result["receipt"].observations)


def test_production_observe_url_source_does_reach_resolve_hop(_world: dict[str, Any]) -> None:
    """The contrasting positive control for the test above: ``resolve_hop`` -- the one method
    remaining on the :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter`
    Protocol -- *is* reached by production ``observe_url_source``, exactly once. This is what
    makes "``connect_hop`` is never called" a meaningful claim about this specific method, rather
    than evidence the adapter was never consulted at all."""

    resolve_call_count = {"count": 0}

    class _ResolveOnlyAdapter:
        def __init__(self) -> None:
            self.adapter_identity: Mapping[str, Any] = {"adapter": "resolve-only", "version": "0.1"}

        def resolve_hop(self, *, source_identity: Any) -> dict[str, Any]:
            resolve_call_count["count"] += 1
            return {"outcome": "RESOLVED", "resolved_address": _SAFE_RESOLVED_ADDRESS}

    observe_url_source(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        source_identity=_world["source_identity"],
        boundary=_world["boundary"],
        adapter=_ResolveOnlyAdapter(),
        observed_at="2026-09-10T00:00:01Z",
    )
    assert resolve_call_count["count"] == 1
