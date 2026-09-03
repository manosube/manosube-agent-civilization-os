"""Fixtures that reach Change through the public Authority route, never around it.

Every Authority decision these helpers bind is produced by ``evaluate_authority`` from a
Difference produced by ``derive_differences``. Hand-writing a decision would let the Change
tests pass over a decision Authority would never emit, which is exactly the kind of coverage
that proves nothing.
"""

from __future__ import annotations

from typing import Any

from tests.authority_helpers import authority_request, derived_difference

from manosube_agent_civilization.authority import evaluate_authority

__all__ = ["change_request", "decide", "derived_difference"]


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
    difference: dict[str, Any],
    decision: dict[str, Any],
    requested_action: dict[str, Any],
    requested_scope: dict[str, Any],
    *,
    project_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "project_id": project_id if project_id is not None else difference["project_id"],
        "difference": difference,
        "authority_decision": decision,
        "requested_action": requested_action,
        "requested_scope": requested_scope,
    }
