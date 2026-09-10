"""The one generic, callable-injecting URL Boot observation engine (Structural Review Round 5,
P17-R5-F2, Issue #69) -- deliberately **not** part of the shipped package.

Every Structural Review through Round 4 narrowed *what a replaceable adapter can do* (first its
own connection, then its own resolution) but left the shipped ``route.py`` itself holding a
generic orchestration function -- the pre-Round-5 ``_observe_url_source_impl`` --
accepting ``classify_resolved_address``/``perform_resolution``/``perform_connection`` as ordinary
function parameters. Round 5 found that this, not any adapter capability, was the real remaining
gap: a caller able to import ``route.py`` directly could call that generic function with the
genuine, shipped trusted-network resolver/connector *and* an ordinary permissive lambda as
``classify_resolved_address`` (``lambda address: None``), reconstructing the exact
loopback-admitting path production's own classifier alone was supposed to close -- using only
shipped code, no isolation break, and no adapter object at all.

The correction is structural, not a narrower check: the shipped package now ships **only** a
fixed, non-parameterized production pipeline
(:func:`~manosube_agent_civilization.url_boot.route._fetch_with_route_owned_redirects_production`,
:func:`~manosube_agent_civilization.url_boot.route._observe_url_source_impl_production`) whose own
classifier/resolver/connector calls are hardcoded, direct calls -- never parameters a caller could
ever override. The *generic*, dependency-injected form of that identical orchestration -- the one
this repository's own internal, fully deterministic route-logic test suite genuinely needs, to
inject a controlled ``FakeUrlSourceAdapter``'s own simulated resolve/connect facts -- moves
entirely into this file, confirmed absent from the distributed wheel by ``pyproject.toml``'s own
``[tool.hatch.build.targets.wheel] packages`` declaration, the identical packaging fact already
established for ``tests/fixtures/url_boot_local_test_authority.py``.

This module also backs the disposable-local-test composition itself
(``tests/fixtures/url_boot_local_test_authority.py``'s own ``compose_disposable_local_test_
observer``): that composition binds this module's own generic engine to the loopback-permitting
classifier and the *same* trusted network resolver/connector production uses (imported from
``route.py``, themselves fixed, non-parameterized functions -- reused, never reimplemented). A
caller who imports only this module gains an engine that still requires *some* classifier/
resolver/connector to be supplied; it is the disposable-local-test composition's own authority
check (Ed25519-verified, genuinely external issuer, see ``url_boot_local_test_authority.py``) and
this repository's own internal test suite's own direct calls that are the only two places this
generic engine is ever actually invoked -- both non-shipped, both outside any caller who has only
``pip install``ed this package.

Reuses ``route.py``'s own shipped, non-generic helper functions (``_hop_result``,
``_classify_terminal_response``, ``_resolve_redirect_target``, ``_require_canonical_identity``,
``_require_within_time_window``, ``_redact``, ``_authority_context``, ``_boot_authority_context``,
``_require_unchanged_authority_context``, ``_commit_envelope``,
``_canonicalize_inert_adapter_identity``) directly -- none of these accept a classifier/resolver/
connector of their own, so reusing them does not reintroduce the shipped generic-engine surface
Round 5 requires removed; only the *orchestration* that threads caller-suppliable primitives
through them is relocated here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from manosube_agent_civilization.url_boot import route as route_module
from manosube_agent_civilization.url_boot.engine import (
    derive_url_source_observation_envelope,
    require_valid_boundary,
    require_valid_source_identity,
    require_valid_timestamp,
)
from manosube_agent_civilization.url_boot.errors import UrlBootAdapterError, UrlBootRequirementError
from manosube_agent_civilization.url_boot.identity import (
    url_boundary_fingerprint,
    url_observed_content_fingerprint,
    url_source_fingerprint,
    url_source_request_identity,
)
from manosube_agent_civilization.url_boot.network import (
    UnsafeResolvedAddressError,
    require_source_within_network_scope,
)
from manosube_agent_civilization.url_boot.types import (
    RECEIPT_STATUSES,
    URL_FETCH_OUTCOMES,
    URL_HOP_CONNECT_OUTCOMES,
    URL_HOP_RESOLVE_OUTCOMES,
    URL_OUTCOME_TO_RECEIPT_STATUS,
    UrlSourceObservationReceipt,
    deep_freeze,
)

_HOP_CONNECT_FAILURE_OUTCOMES: frozenset[str] = frozenset(
    {"CONNECTION_FAILURE", "TLS_FAILURE", "TIMEOUT"}
)


def perform_resolution_via_adapter(
    adapter: Any, current_identity: Mapping[str, Any]
) -> Mapping[str, Any]:
    """Delegates to *adapter*'s own ``resolve_hop`` -- a capability
    :class:`~manosube_agent_civilization.url_boot.adapter.FakeUrlSourceAdapter` still carries
    beyond the shipped ``UrlSourceAdapter`` Protocol itself, purely for controlled, fully
    in-memory, deterministic simulation of a real probe's own bounded per-hop facts. Never reached
    by production or the disposable-local-test composition, both of which bind the genuine
    trusted-network resolver instead."""

    result: Mapping[str, Any] = adapter.resolve_hop(source_identity=deep_freeze(current_identity))
    return result


def perform_connection_via_adapter(
    adapter: Any,
    current_identity: Mapping[str, Any],
    admitted_address: str,
    boundary: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Delegates to *adapter*'s own ``connect_hop`` -- the identical deterministic-simulation
    capability :func:`perform_resolution_via_adapter` documents, for the connect stage."""

    result: Mapping[str, Any] = adapter.connect_hop(
        source_identity=deep_freeze(current_identity),
        boundary=deep_freeze(boundary),
        admitted_address=admitted_address,
    )
    return result


def fetch_with_injected_primitives(
    source_identity: Mapping[str, Any],
    boundary: Mapping[str, Any],
    *,
    adapter: Any,
    classify_resolved_address: Callable[[str], None],
    perform_resolution: Callable[[Any, Mapping[str, Any]], Mapping[str, Any]],
    perform_connection: Callable[
        [Any, Mapping[str, Any], str, Mapping[str, Any]], Mapping[str, Any]
    ],
) -> dict[str, Any]:
    """The generic, dependency-injected form of the bounded, per-hop-reauthorized redirect loop
    -- see this module's own docstring for why this orchestration itself does not ship. Identical
    decision logic to the pre-Round-5 shipped ``_fetch_with_route_owned_redirects``, reusing
    ``route.py``'s own shipped classification helpers directly."""

    network_scope = boundary["network_scope"]
    max_redirects = boundary["redirect_policy"]["max_redirects"]
    current_identity = dict(source_identity)
    resolution_bindings: dict[tuple[str, int], str] = {}
    resolution_provenance: list[dict[str, Any]] = []

    for hop in range(max_redirects + 1):
        resolve_raw = perform_resolution(adapter, current_identity)
        if not isinstance(resolve_raw, Mapping):
            raise UrlBootRequirementError(
                f"the resolve-stage primitive returned {resolve_raw!r}, not a mapping"
            )
        resolve_outcome = resolve_raw.get("outcome")
        if resolve_outcome not in URL_HOP_RESOLVE_OUTCOMES:
            raise UrlBootRequirementError(
                f"the resolve-stage primitive's own outcome is not recognized: {resolve_outcome!r}"
            )
        if resolve_outcome == "DNS_FAILURE":
            return route_module._hop_result("DNS_FAILURE", redirect_hop_count=hop)

        candidate_address = resolve_raw.get("resolved_address")
        if not isinstance(candidate_address, str) or not candidate_address:
            raise UrlBootRequirementError(
                "the resolve-stage primitive reported RESOLVED with no readable resolved_address"
            )

        try:
            classify_resolved_address(candidate_address)
        except UnsafeResolvedAddressError:
            return route_module._hop_result("BOUNDARY_REFUSED", redirect_hop_count=hop)

        host_port_key = (current_identity["host"], current_identity["port"])
        bound_address = resolution_bindings.get(host_port_key)
        if bound_address is None:
            resolution_bindings[host_port_key] = candidate_address
            resolution_provenance.append(
                {
                    "host": current_identity["host"],
                    "port": current_identity["port"],
                    "resolved_address": candidate_address,
                }
            )
        elif bound_address != candidate_address:
            return route_module._hop_result("BOUNDARY_REFUSED", redirect_hop_count=hop)

        admitted_address = candidate_address
        connect_raw = perform_connection(adapter, current_identity, admitted_address, boundary)
        if not isinstance(connect_raw, Mapping):
            raise UrlBootRequirementError(
                f"the connect-stage primitive returned {connect_raw!r}, not a mapping"
            )
        connect_outcome = connect_raw.get("outcome")
        if connect_outcome not in URL_HOP_CONNECT_OUTCOMES:
            raise UrlBootRequirementError(
                f"the connect-stage primitive's own outcome is not recognized: {connect_outcome!r}"
            )
        if connect_outcome in _HOP_CONNECT_FAILURE_OUTCOMES:
            return route_module._hop_result(connect_outcome, redirect_hop_count=hop)

        if connect_raw.get("resolved_address") != admitted_address:
            raise UrlBootRequirementError(
                "the connect-stage primitive reported a resolved_address that does not equal "
                f"the exact address this route admitted for this hop: "
                f"{connect_raw.get('resolved_address')!r} != {admitted_address!r}"
            )

        raw = connect_raw
        status = raw.get("response_status")
        if not isinstance(status, int):
            raise UrlBootRequirementError(
                "the connect-stage primitive reported RESPONSE with an unreadable "
                f"response_status: {status!r}"
            )
        redirect_location = raw.get("redirect_location")

        if redirect_location is not None and 300 <= status < 400:
            if hop == max_redirects:
                return route_module._hop_result(
                    "REDIRECT_REFUSED", response_status=status, redirect_hop_count=hop
                )
            next_identity = route_module._resolve_redirect_target(
                current_identity, redirect_location
            )
            if next_identity is None:
                return route_module._hop_result(
                    "REDIRECT_REFUSED", response_status=status, redirect_hop_count=hop
                )
            try:
                require_source_within_network_scope(next_identity, network_scope)
            except UrlBootRequirementError:
                return route_module._hop_result(
                    "REDIRECT_REFUSED", response_status=status, redirect_hop_count=hop
                )
            current_identity = next_identity
            continue

        return route_module._classify_terminal_response(
            raw,
            current_identity,
            hop,
            status,
            boundary=boundary,
            resolution_provenance=resolution_provenance,
        )

    return route_module._hop_result("REDIRECT_REFUSED", redirect_hop_count=max_redirects)


def observe_url_source_for_internal_testing(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    source_identity: Mapping[str, Any],
    boundary: Mapping[str, Any],
    adapter_identity: Mapping[str, Any],
    observed_at: str,
    classify_resolved_address: Callable[[str], None],
    perform_resolution: Callable[[Any, Mapping[str, Any]], Mapping[str, Any]],
    perform_connection: Callable[
        [Any, Mapping[str, Any], str, Mapping[str, Any]], Mapping[str, Any]
    ],
    adapter: Any = None,
) -> dict[str, Any]:
    """The generic, dependency-injected observation implementation -- the non-shipped counterpart
    to ``route.py``'s own fixed ``_observe_url_source_impl_production``, reached only by:

    - this repository's own internal deterministic route-logic test suite, calling this function
      directly with the production classifier and the adapter-delegating resolver/connector;
    - ``tests/fixtures/url_boot_local_test_authority.py``'s own ``compose_disposable_local_test_
      observer``, binding the loopback-permitting classifier and the genuine trusted-network
      resolver/connector (imported from ``route.py``).

    Never exported to, or reachable from, any production caller. *adapter_identity* is, exactly
    like production's own :func:`~manosube_agent_civilization.url_boot.
    route._observe_url_source_impl_production`, already-realized plain data the caller supplies
    directly (Structural Review Round 5, P17-R5-F1) -- this function performs no attribute access
    on *adapter* to obtain it; *adapter* itself is consulted only by *perform_resolution*/
    *perform_connection* when those are the adapter-delegating primitives."""

    route_module._require_canonical_identity("project_id", project_id)
    route_module._require_canonical_identity("project_binding_id", project_binding_id)
    require_valid_timestamp(observed_at, "observed_at")

    checked_source_identity = require_valid_source_identity(source_identity)
    checked_boundary = require_valid_boundary(boundary)
    require_source_within_network_scope(checked_source_identity, checked_boundary["network_scope"])
    route_module._require_within_time_window(checked_boundary, observed_at)

    canonical_adapter_identity = deep_freeze(
        route_module._canonicalize_inert_adapter_identity(adapter_identity)
    )

    boot_context = route_module._boot_authority_context(store, project_id, project_binding_id)
    real_human_authority_ref = dict(boot_context.human_authority_ref)
    authority_context = route_module._authority_context(boot_context)
    real_project_binding_ref = {"kind": "project_binding", "id": project_binding_id}
    real_boot_state_fingerprint = dict(boot_context.current_state["semantic_fingerprint"])
    real_boot_lineage_head_ref = boot_context.current_state.get("lineage_head_ref")
    real_boot_state_transition_ref = (
        dict(real_boot_lineage_head_ref)
        if real_boot_lineage_head_ref is not None
        else {"kind": "state_transition", "id": route_module._GENESIS_TRANSACTION_ID}
    )

    requested_source_fingerprint = url_source_fingerprint(checked_source_identity)
    boundary_fingerprint = url_boundary_fingerprint(checked_boundary)
    source_request_identity = url_source_request_identity(
        requested_source_fingerprint,
        boundary_fingerprint,
        checked_boundary["time_window"]["issued_at"],
    )

    route_module._require_unchanged_authority_context(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        expected=authority_context,
        stage="before the adapter is reached",
    )

    fetch_result = fetch_with_injected_primitives(
        checked_source_identity,
        checked_boundary,
        adapter=adapter,
        classify_resolved_address=classify_resolved_address,
        perform_resolution=perform_resolution,
        perform_connection=perform_connection,
    )
    fetch_outcome = fetch_result["fetch_outcome"]
    if fetch_outcome not in URL_FETCH_OUTCOMES:
        raise UrlBootAdapterError(f"unrecognized derived fetch_outcome: {fetch_outcome!r}")
    status = URL_OUTCOME_TO_RECEIPT_STATUS[fetch_outcome]
    if status not in RECEIPT_STATUSES:
        raise UrlBootAdapterError(f"unrecognized receipt status derived from outcome: {status!r}")

    if fetch_outcome != "OBSERVED":
        receipt = UrlSourceObservationReceipt(
            status=status,
            url_source_observation_envelope_id=None,
            project_id=project_id,
            requested_source_identity=checked_source_identity,
            boundary=checked_boundary,
            adapter_identity=dict(canonical_adapter_identity),
            human_authority_ref=real_human_authority_ref,
            input_refs=(dict(real_human_authority_ref),),
            observations={
                "fetch_outcome": fetch_outcome,
                "observed_content_fingerprint": None,
                "retrieved_at": observed_at,
            },
        )
        return {"envelope": None, "receipt": receipt}

    effective_source_identity = fetch_result["effective_source_identity"]
    effective_source_fingerprint = url_source_fingerprint(effective_source_identity)
    observed_fields = route_module._redact(
        fetch_result["observed_fields"], list(checked_boundary.get("redaction_fields", []))
    )
    observed_content_fingerprint = url_observed_content_fingerprint(observed_fields)

    envelope = derive_url_source_observation_envelope(
        project_id=project_id,
        project_binding_ref=real_project_binding_ref,
        boot_state_fingerprint=real_boot_state_fingerprint,
        boot_state_transition_ref=real_boot_state_transition_ref,
        requested_source_identity=checked_source_identity,
        requested_source_fingerprint=requested_source_fingerprint,
        effective_source_identity=effective_source_identity,
        effective_source_fingerprint=effective_source_fingerprint,
        boundary=checked_boundary,
        boundary_fingerprint=boundary_fingerprint,
        source_request_identity=source_request_identity,
        retrieved_at=observed_at,
        fetch_outcome=fetch_outcome,
        response_status=fetch_result["response_status"],
        redirect_hop_count=fetch_result["redirect_hop_count"],
        resolution_provenance=fetch_result["resolution_provenance"],
        observed_fields=observed_fields,
        observed_content_fingerprint=observed_content_fingerprint,
        adapter_identity=dict(canonical_adapter_identity),
        human_authority_ref=real_human_authority_ref,
    )

    route_module._commit_envelope(
        store,
        project_id,
        envelope,
        observed_at,
        project_binding_id=project_binding_id,
        authority_context=authority_context,
    )

    receipt = UrlSourceObservationReceipt(
        status="VERIFIED",
        url_source_observation_envelope_id=envelope["url_source_observation_envelope_id"],
        project_id=project_id,
        requested_source_identity=checked_source_identity,
        boundary=checked_boundary,
        adapter_identity=dict(canonical_adapter_identity),
        human_authority_ref=real_human_authority_ref,
        input_refs=(dict(real_human_authority_ref),),
        observations={
            "fetch_outcome": "OBSERVED",
            "observed_content_fingerprint": observed_content_fingerprint,
            "retrieved_at": observed_at,
        },
    )
    return {"envelope": envelope, "receipt": receipt}


__all__ = [
    "fetch_with_injected_primitives",
    "observe_url_source_for_internal_testing",
    "perform_connection_via_adapter",
    "perform_resolution_via_adapter",
]
