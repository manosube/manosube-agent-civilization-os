"""Fixtures that reach Evidence through the public predecessor routes, never around one.

Every Observation these helpers ground is produced by ``observe``; every Change is produced
by ``derive_change`` from a decision ``evaluate_authority`` produced from a Difference
``derive_differences`` produced. Nothing here hand-writes a predecessor record, and the
Evidence engine could not accept one if it did -- it takes the predecessors' *requests*.
"""

from __future__ import annotations

from typing import Any

from tests.authority_helpers import (
    action,
    derived_difference,
    rule,
    scope as authority_scope,
)
from tests.change_helpers import route
from tests.difference_helpers import (
    PREDICATE_ID,
    observation_request,
    observation_scope,
    raw_fact,
    state_fingerprint,
)

from manosube_agent_civilization.difference.identity import (
    closure_policy_id,
    policy_semantic_fingerprint,
)
from manosube_agent_civilization.evidence.sufficiency import evidence_level_scale_digest

__all__ = [
    "AFTER_REVISION",
    "ARTIFACT",
    "BEFORE_REVISION",
    "EVALUATED_AT",
    "RECORDED_AT",
    "after_observation_request",
    "artifact",
    "before_observation_request",
    "change_result_evidence_request",
    "closure_policy",
    "completion_semantics_ref",
    "observation_evidence_request",
    "real_change_request",
    "sufficiency_request",
]

#: The revision the fixture Difference observed, which is therefore the revision every
#: Authority decision built from it evaluates against and every Change expects.
BEFORE_REVISION = 2

#: A second, later revision. Nothing here claims the Change produced it: a re-observation is
#: a second observation, and what it establishes is that an after-state was seen.
AFTER_REVISION = 3

#: Later than the fixture Observation's ``observation_ended_at``. The instant is an input
#: because a timestamp read from the machine that wrote the record is one no reviewer can
#: reproduce.
RECORDED_AT = "2026-08-30T10:00:00Z"

#: An evaluation instant for sufficiency, admitted the same way and for the same reason.
EVALUATED_AT = "2026-08-30T11:00:00Z"


def artifact(
    identity: str = "ARTIFACT-0001",
    digest: str = "a" * 64,
    byte_length: int = 128,
    media_type: str = "application/json",
) -> dict[str, Any]:
    """One artifact reference: integrity, and nothing that could change underneath it."""

    return {
        "kind": "artifact",
        "id": identity,
        "content_sha256": digest,
        "byte_length": byte_length,
        "media_type": media_type,
    }


ARTIFACT = artifact()


def before_observation_request(**kwargs: Any) -> dict[str, Any]:
    """The Observation of the State the fixture Difference and Change were built on."""

    return observation_request(
        observation_scope(),
        [raw_fact(value="NOT-READY")],
        state_fingerprint(),
        BEFORE_REVISION,
        **kwargs,
    )


def after_observation_request(**kwargs: Any) -> dict[str, Any]:
    """A re-observation at a later revision, by the same public Observation Engine."""

    return observation_request(
        observation_scope(),
        [raw_fact(value="READY")],
        state_fingerprint("KNOWN"),
        AFTER_REVISION,
        **kwargs,
    )


def observation_evidence_request(
    *,
    method_class: str = "STATIC_INSPECTION",
    recorded_at: str = RECORDED_AT,
    artifact_references: list[dict[str, Any]] | None = None,
    observation: dict[str, Any] | None = None,
    predecessor_evidence_refs: list[dict[str, Any]] | None = None,
    remaining_difference_refs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """An Evidence request in 第27条's first position: no Change, no after-state."""

    return {
        "schema_version": "0.1",
        "recorded_at": recorded_at,
        "observation_request": observation
        if observation is not None
        else before_observation_request(),
        "observation_method_class": method_class,
        "change_request": None,
        "post_change_observation_request": None,
        "artifact_references": list(
            artifact_references if artifact_references is not None else [dict(ARTIFACT)]
        ),
        "predecessor_evidence_refs": list(predecessor_evidence_refs or []),
        "remaining_difference_refs": list(remaining_difference_refs or []),
    }


def real_change_request() -> dict[str, Any]:
    """One Change request that the canonical Change deriver actually accepts."""

    difference = derived_difference()
    where = authority_scope()
    _, _, request = route(
        difference,
        action(),
        where,
        rules=[rule(difference["project_id"], rule_scope=where)],
    )
    return request


def change_result_evidence_request(
    *,
    method_class: str = "INTEGRATION_TEST",
    recorded_at: str = RECORDED_AT,
    change_request: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
    post_change_observation: dict[str, Any] | None = None,
    artifact_references: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """An Evidence request in 第27条's second position, grounded in a re-observation."""

    return {
        "schema_version": "0.1",
        "recorded_at": recorded_at,
        "observation_request": observation
        if observation is not None
        else before_observation_request(),
        "observation_method_class": method_class,
        "change_request": change_request if change_request is not None else real_change_request(),
        "post_change_observation_request": post_change_observation
        if post_change_observation is not None
        else after_observation_request(),
        "artifact_references": list(
            artifact_references if artifact_references is not None else [dict(ARTIFACT)]
        ),
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }


def closure_policy(
    difference_id: str,
    *,
    minimum_evidence_level: str = "E1",
    maximum_evidence_age: int | None = None,
) -> dict[str, Any]:
    """One Closure Policy, addressed by Difference's own identity functions.

    The identity and the fingerprint are computed rather than written, so a fixture that
    changes a requirement cannot keep an address that says it did not.
    """

    policy: dict[str, Any] = {
        "schema_version": "0.1",
        "closure_policy_id": "",
        "policy_version": "0.1",
        "policy_semantic_fingerprint": "",
        "subject_difference_ref": {"kind": "difference", "id": difference_id},
        "target_predicate_ref": {"kind": "target_predicate", "id": PREDICATE_ID},
        "required_observation_scope": None,
        "minimum_evidence_level": minimum_evidence_level,
        "required_claims": [],
        "required_invariants": [],
        "allowed_terminal_states": ["CLOSED", "BLOCKED", "RETAINED"],
        "independent_verification_required": False,
        "maximum_evidence_age": maximum_evidence_age,
        "contradiction_policy": "FAIL_CLOSED",
        "reopen_conditions": [],
    }
    policy["policy_semantic_fingerprint"] = policy_semantic_fingerprint(policy)
    policy["closure_policy_id"] = closure_policy_id(
        policy["policy_semantic_fingerprint"], difference_id
    )
    return policy


def completion_semantics_ref(scale_digest: str | None = None) -> dict[str, Any]:
    """The content-addressed blob reference G12 requires, addressing the applied scale."""

    return {
        "kind": "git_blob",
        "repository": "manosube/manosube-agent-civilization-os",
        "commit_sha": "0" * 40,
        "path": "00_KERNEL/COMPLETION_SEMANTICS.md",
        "blob_sha": "1" * 40,
        "evidence_level_scale_sha256": (
            scale_digest if scale_digest is not None else evidence_level_scale_digest()
        ),
    }


def sufficiency_request(
    *,
    difference_id: str | None = None,
    evidence_requests: list[dict[str, Any]] | None = None,
    minimum_evidence_level: str = "E1",
    maximum_evidence_age: int | None = None,
    evaluation_instant: str = EVALUATED_AT,
    policy: dict[str, Any] | None = None,
    scale_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A sufficiency request over Evidence requests, never over Evidence records."""

    identity = difference_id if difference_id is not None else derived_difference()["difference_id"]
    return {
        "schema_version": "0.1",
        "difference_ref": {"kind": "difference", "id": identity},
        "closure_policy": policy
        if policy is not None
        else closure_policy(
            identity,
            minimum_evidence_level=minimum_evidence_level,
            maximum_evidence_age=maximum_evidence_age,
        ),
        "completion_semantics_ref": scale_ref
        if scale_ref is not None
        else completion_semantics_ref(),
        "evidence_requests": list(
            evidence_requests if evidence_requests is not None else [observation_evidence_request()]
        ),
        "evaluation_instant": evaluation_instant,
    }
