"""Fixtures that reach Change through the public Authority route, never around it.

Every Authority decision these helpers bind is produced by ``evaluate_authority`` from a
Difference produced by ``derive_differences``. Hand-writing a decision would let the Change
tests pass over a decision Authority would never emit -- which, until the provenance repair,
was not merely weak coverage but the defect itself.
"""

from __future__ import annotations

from typing import Any

from tests.authority_helpers import authority_request, derived_difference

from manosube_agent_civilization.authority import evaluate_authority

__all__ = ["authority_request", "change_request", "decide", "derived_difference", "route"]


def decide(
    difference: dict[str, Any],
    requested_action: dict[str, Any],
    requested_scope: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """One real Authority decision, produced by the public evaluator."""

    decision: dict[str, Any] = evaluate_authority(
        authority_request(difference, requested_action, requested_scope, **kwargs)
    )
    return decision


def change_request(
    authority_input: dict[str, Any], decision: dict[str, Any]
) -> dict[str, Any]:
    """A Change request: the real Authority inputs, and the decision claimed for them."""

    return {
        "schema_version": "0.1",
        "authority_request": authority_input,
        "authority_decision": decision,
    }


def route(
    difference: dict[str, Any],
    requested_action: dict[str, Any],
    requested_scope: dict[str, Any],
    **kwargs: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """The whole natural route in one call.

    Returns the Authority input, the decision the canonical evaluator produced for it, and
    the Change request pairing them -- so a test never has to assemble a decision itself.
    """

    authority_input = authority_request(difference, requested_action, requested_scope, **kwargs)
    decision: dict[str, Any] = evaluate_authority(authority_input)
    return authority_input, decision, change_request(authority_input, decision)
