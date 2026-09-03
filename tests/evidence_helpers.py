"""Fixtures that reach Evidence through the public predecessor routes, never around one.

Every Observation these helpers ground is produced by ``observe``; every Change is produced
by ``derive_change`` from a decision ``evaluate_authority`` produced from a Difference
``derive_differences`` produced. Nothing here hand-writes a predecessor record, and the
Evidence engine could not accept one if it did -- it takes the predecessors' *requests*.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from tests.authority_helpers import (
    action,
    rule,
    scope as authority_scope,
)
from tests.change_helpers import route
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_request,
    observation_scope,
    raw_fact,
    retained_status_predecessor,
    state_fingerprint,
)

from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.identity import (
    closure_policy_id,
    policy_semantic_fingerprint,
)
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.levels import (
    COMPLETION_SEMANTICS_BLOB_SHA,
    COMPLETION_SEMANTICS_PATH,
)
from manosube_agent_civilization.evidence.sufficiency import evidence_level_scale_digest
from manosube_agent_civilization.observation import observe

__all__ = [
    "AFTER_REVISION",
    "AFTER_STATUS_ROUTES",
    "ARTIFACT",
    "BEFORE_REVISION",
    "EVALUATED_AT",
    "RECORDED_AT",
    "STATUS_ROUTES",
    "after_observation_request",
    "after_observation_with_status",
    "artifact",
    "before_observation_request",
    "blocked_after_observation_request",
    "change_result_evidence_request",
    "closure_policy",
    "conflicted_observation_request",
    "difference_request",
    "difference_round_trip_request",
    "evidence_level_scale_ref",
    "evidenced_difference",
    "observation_evidence_request",
    "observation_with_status",
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
    """The Observation of the State the fixture Difference and Change were built on.

    ``evidenced_difference`` derives the Difference from exactly this request, and
    ``real_change_request`` authorizes its Change against that Difference, so the Evidence
    and the Change are about one Difference by construction rather than by coincidence.
    """

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


def difference_request(scope: dict[str, Any] | None = None) -> dict[str, Any]:
    """A one-binding Difference derivation request, ready for its bundle to be substituted.

    The ``observation_bundle`` here is a placeholder: ``derive_evidence`` replaces it with the
    bundle it reproduces, so what the Difference is derived from is the Evidence record's own
    Observation and cannot be anything else.
    """

    where = scope if scope is not None else observation_scope()
    return derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": deepcopy(where),
                "observation_bundle": None,
            }
        ],
        state_fingerprint(),
        BEFORE_REVISION,
    )


def observation_evidence_request(
    *,
    recorded_at: str = RECORDED_AT,
    artifact_references: list[dict[str, Any]] | None = None,
    observation: dict[str, Any] | None = None,
    difference: dict[str, Any] | None = None,
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
        "difference_request": difference if difference is not None else difference_request(),
        "change_request": None,
        "post_change_observation_request": None,
        "artifact_references": list(
            artifact_references if artifact_references is not None else [dict(ARTIFACT)]
        ),
        "predecessor_evidence_refs": list(predecessor_evidence_refs or []),
        "remaining_difference_refs": list(remaining_difference_refs or []),
    }


def evidenced_difference() -> dict[str, Any]:
    """The Difference ``derive_evidence`` derives for the standard fixture, derived the same way.

    A test that authorized a Change for some *other* Difference would exercise the mismatch
    guard rather than the route, so the fixture computes the real one instead of assuming it.
    """

    request = difference_request()
    request["bindings"][0]["observation_bundle"] = observe(before_observation_request())
    derived: dict[str, Any] = derive_differences(request)["differences"][0]
    return derived


def real_change_request() -> dict[str, Any]:
    """One Change request that the canonical Change deriver actually accepts."""

    difference = evidenced_difference()
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
    recorded_at: str = RECORDED_AT,
    change_request: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
    difference: dict[str, Any] | None = None,
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
        "difference_request": difference if difference is not None else difference_request(),
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


def evidence_level_scale_ref(
    scale_digest: str | None = None, blob_sha: str | None = None
) -> dict[str, Any]:
    """The scale source reference G12 requires, carrying only fields the engine verifies.

    Every value here is checked: the path against the canonical one, the blob against the pin
    a repository test holds to ``git hash-object`` of the live document, and the digest
    against the scale actually being applied.
    """

    return {
        "kind": "evidence_level_scale_source",
        "path": COMPLETION_SEMANTICS_PATH,
        "blob_sha": blob_sha if blob_sha is not None else COMPLETION_SEMANTICS_BLOB_SHA,
        "evidence_level_scale_sha256": (
            scale_digest if scale_digest is not None else evidence_level_scale_digest()
        ),
    }


#: Attempt outcome and Negative Observation claim that make the Engine conclude each
#: post-change status. Reachable only here: the post-change Observation never reaches the
#: Difference producer, so it can carry any status while the record still binds the Difference
#: its *before* Observation derived. This is the one way to get several Evidence records of
#: one Difference at several statuses and levels.
AFTER_STATUS_ROUTES: dict[str, tuple[str, str | None]] = {
    "COMPLETE": ("COMPLETE", None),
    "BLOCKED": ("BLOCKED", "BLOCKED"),
    "FAILED": ("FAILED", "FAILED"),
    "INCOMPLETE": ("PARTIAL", "INCOMPLETE"),
    "EMPTY": ("EMPTY", "EMPTY"),
}


def after_observation_with_status(status: str) -> dict[str, Any]:
    """A re-observation the Observation Engine really concludes *status* for."""

    attempt, claim = AFTER_STATUS_ROUTES[status]
    if claim is None:
        return after_observation_request()
    request = observation_request(
        observation_scope(),
        [],
        state_fingerprint("KNOWN"),
        AFTER_REVISION,
        negative_claims=[negative_claim(claim)],
    )
    request["attempts"][0]["result"] = attempt
    request["attempts"][0]["failure_class"] = "SOURCE_ERROR" if attempt == "FAILED" else None
    return request


def blocked_after_observation_request() -> dict[str, Any]:
    """The BLOCKED re-observation, named for the tests that reach for it most."""

    return after_observation_with_status("BLOCKED")


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

    requests = list(
        evidence_requests if evidence_requests is not None else [observation_evidence_request()]
    )
    if difference_id is not None:
        identity = difference_id
    elif requests:
        # The Difference the Evidence actually derives, not an assumption about it. A fixture
        # that guessed would be exercising the exact-binding guard on every ordinary test
        # instead of the semantics under test.
        identity = str(derive_evidence(requests[0])["difference_ref"]["id"])
    else:
        identity = evidenced_difference()["difference_id"]
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
        "evidence_level_scale_ref": scale_ref
        if scale_ref is not None
        else evidence_level_scale_ref(),
        "evidence_requests": list(
            evidence_requests if evidence_requests is not None else [observation_evidence_request()]
        ),
        "evaluation_instant": evaluation_instant,
    }


def conflicted_observation_request() -> dict[str, Any]:
    """An Observation the Engine itself rules CONFLICTED: a positive fact and a NO_RESULT claim.

    Real rather than constructed -- the conflict is detected by the Observation owner, so a
    test using it exercises the same path a real contradiction would.
    """

    return before_observation_request(negative_claims=[negative_claim("NO_RESULT")])


#: Attempt result and Negative Observation claim that make the Observation Engine conclude
#: each status, on the pure-negative route the Difference producer accepts. Facts are absent
#: on purpose: an Observation carrying positive Facts must be COMPLETE or CONFLICTED before
#: Difference will derive from it, so an unfinished observation reaches Evidence as a bounded
#: Negative Observation, which is what a bounded absence *is*.
STATUS_ROUTES: dict[str, tuple[str, str, bool]] = {
    "BLOCKED": ("BLOCKED", "BLOCKED", True),
    "EMPTY": ("EMPTY", "EMPTY", True),
    "INCOMPLETE": ("PARTIAL", "INCOMPLETE", True),
    # An incomplete enumeration is not an observed emptiness: with the collection unproven,
    # the Engine reaches UNKNOWN rather than EMPTY.
    "UNKNOWN": ("EMPTY", "UNKNOWN", False),
}


def observation_with_status(status: str) -> dict[str, Any]:
    """An Observation request the Engine really concludes *status* for.

    Nothing here writes the status: the attempt outcome and the Negative Observation claim
    are the inputs, and the Observation Engine reaches the status from them. A fixture that
    set the status directly would be testing the fixture.
    """

    if status == "COMPLETE":
        return before_observation_request()
    if status == "CONFLICTED":
        return conflicted_observation_request()
    attempt, claim, complete = STATUS_ROUTES[status]
    request = observation_request(
        observation_scope(),
        [],
        state_fingerprint(),
        BEFORE_REVISION,
        negative_claims=[negative_claim(claim)],
        collection_complete=complete,
    )
    request["attempts"][0]["result"] = attempt
    request["attempts"][0]["failure_class"] = None
    return request


def difference_round_trip_request(
    sufficiency_result: dict[str, Any],
) -> dict[str, Any]:
    """A Difference derivation request carrying *sufficiency_result* as a real predecessor.

    ``retained_status_predecessor("REOPENED")`` builds a lineage whose Closure Evaluation
    cites an Evidence Sufficiency Result. The hand-written one is replaced by the record
    Phase 6 actually produced, and the Evaluation is repointed at it, so the bundle that goes
    into ``derive_differences`` contains this Kernel's own output rather than a stand-in.
    """

    _, later = retained_status_predecessor("REOPENED")
    context = later["bindings"][0]["predecessor"]["context"]
    context["evidence_sufficiency_results"] = [deepcopy(sufficiency_result)]
    for evaluation in context["evaluations"]:
        if evaluation.get("evidence_sufficiency_ref") is not None:
            evaluation["evidence_sufficiency_ref"] = {
                "kind": "evidence_sufficiency_result",
                "id": sufficiency_result["evidence_sufficiency_id"],
            }
    return later
