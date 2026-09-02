"""Fixtures that reach Authority through the public Difference route, never around it.

Every Difference these helpers bind is produced by ``derive_differences`` from real
Objective / State / Observation inputs. Hand-writing a Difference record would let the
Authority tests pass over a Difference the producer would never emit, which is exactly the
kind of coverage that proves nothing.
"""

from __future__ import annotations

from typing import Any

from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    state_fingerprint,
)

from manosube_agent_civilization.authority.identity import (
    action_fingerprint,
    approval_id,
    change_intent_fingerprint,
    prohibition_id,
    rule_id,
)
from manosube_agent_civilization.difference import derive_differences

HUMAN = {"kind": "human_authority", "id": "AUTH-0001"}
REPOSITORY = "manosube/example"
BRANCH = "main"


def derived_difference() -> dict[str, Any]:
    """One real Difference, derived through the public producer."""

    fingerprint = state_fingerprint()
    scope = observation_scope()
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope,
                    [raw_fact(value="NOT-READY")],
                    fingerprint,
                    negative_claims=[negative_claim("NO_RESULT")],
                ),
            }
        ],
        fingerprint,
    )
    derived: dict[str, Any] = derive_differences(request)["differences"][0]
    return derived


def action(
    action_kind: str = "WRITE_FILE",
    reversibility: str = "REVERSIBLE",
) -> dict[str, Any]:
    """A requested action carrying its own recomputable fingerprint."""

    record = {
        "action_kind": action_kind,
        "reversibility": reversibility,
        "action_semantic_fingerprint": "",
    }
    record["action_semantic_fingerprint"] = action_fingerprint(record)
    return record


def scope(
    paths: list[str] | None = None,
    subjects: list[str] | None = None,
    repository: str = REPOSITORY,
    branch: str = BRANCH,
) -> dict[str, Any]:
    return {
        "repository": repository,
        "branch": branch,
        "paths": list(paths if paths is not None else ["src/app.py"]),
        "subjects": list(subjects if subjects is not None else []),
    }


def rule(
    project_id: str,
    *,
    action_kinds: list[str] | None = None,
    decision: str = "AUTONOMOUS",
    maximum_reversibility: str = "REVERSIBLE",
    rule_scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "schema_version": "0.1",
        "authority_rule_id": "",
        "project_id": project_id,
        "action_kinds": list(action_kinds if action_kinds is not None else ["WRITE_FILE"]),
        "maximum_reversibility": maximum_reversibility,
        "scope": rule_scope if rule_scope is not None else scope(paths=["src/app.py", "src/lib.py"]),
        "decision": decision,
        "declared_by": dict(HUMAN),
    }
    record["authority_rule_id"] = rule_id(record)
    return record


def prohibition(
    project_id: str,
    *,
    action_kinds: list[str] | None = None,
    prohibition_class: str = "PROJECT",
    reason_code: str = "PROJECT_POLICY",
    prohibited_scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "schema_version": "0.1",
        "prohibition_id": "",
        "project_id": project_id,
        "prohibition_class": prohibition_class,
        "action_kinds": list(action_kinds if action_kinds is not None else ["WRITE_FILE"]),
        "scope": prohibited_scope if prohibited_scope is not None else scope(),
        "reason_code": reason_code,
        "declared_by": dict(HUMAN),
    }
    record["prohibition_id"] = prohibition_id(record)
    return record


def approval(
    difference: dict[str, Any],
    requested_action: dict[str, Any],
    requested_scope: dict[str, Any],
    *,
    project_id: str | None = None,
    approved_scope: dict[str, Any] | None = None,
    state_revision: int | None = None,
    state_fingerprint_override: dict[str, Any] | None = None,
    prohibited_actions: list[str] | None = None,
    status: str = "ACTIVE",
    approved_at: str = "2026-01-01T00:00:00Z",
    expires_at: str = "2026-12-31T23:59:59Z",
    change_intent_override: str | None = None,
) -> dict[str, Any]:
    """An approval bound to exactly this action over exactly this scope, unless overridden."""

    covered = approved_scope if approved_scope is not None else requested_scope
    record = {
        "schema_version": "0.1",
        "approval_id": "",
        "project_id": project_id if project_id is not None else difference["project_id"],
        "difference_ref": {"kind": "difference", "id": difference["difference_id"]},
        "change_intent_fingerprint": (
            change_intent_override
            if change_intent_override is not None
            else change_intent_fingerprint(requested_action, requested_scope)
        ),
        "change_ref": None,
        "approved_state_revision": (
            state_revision
            if state_revision is not None
            else difference["observed_state_revision"]
        ),
        "approved_state_fingerprint": (
            state_fingerprint_override
            if state_fingerprint_override is not None
            else dict(difference["observed_state_fingerprint"])
        ),
        "approved_action_fingerprint": requested_action["action_semantic_fingerprint"],
        "approved_scope": covered,
        "prohibited_actions": list(prohibited_actions or []),
        "approved_by": dict(HUMAN),
        "approved_at": approved_at,
        "expires_at": expires_at,
        "status": status,
    }
    record["approval_id"] = approval_id(record)
    return record


def authority_request(
    difference: dict[str, Any],
    requested_action: dict[str, Any],
    requested_scope: dict[str, Any],
    *,
    rules: list[dict[str, Any]] | None = None,
    prohibitions: list[dict[str, Any]] | None = None,
    approvals: list[dict[str, Any]] | None = None,
    state_revision: int | None = None,
    state_fingerprint_override: dict[str, Any] | None = None,
    evaluation_time: str = "2026-06-01T00:00:00Z",
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "project_id": difference["project_id"],
        "difference": difference,
        "requested_action": requested_action,
        "requested_scope": requested_scope,
        "current_state_revision": (
            state_revision if state_revision is not None else difference["observed_state_revision"]
        ),
        "current_state_fingerprint": (
            state_fingerprint_override
            if state_fingerprint_override is not None
            else dict(difference["observed_state_fingerprint"])
        ),
        "authority_rules": list(rules or []),
        "prohibitions": list(prohibitions or []),
        "approvals": list(approvals or []),
        "evaluation_time": evaluation_time,
    }
