"""Phase 8 Vertical Proof -- the minimal, pinned, deterministic fixture world.

``00_KERNEL/VERTICAL_PROOF_CONTRACT.md`` names this module the one Fixture Boundary for the
Phase 8 natural-cycle proof (``tests/natural_cycle/proof.py``). Every value here is a bounded
*source-world input* -- an Objective, an initial semantic State's own domain content, a
before/after observation source fact, an Authority rule, a Change action/scope, a Closure
Policy -- never a completed Observation, Difference, Authority Decision, Change, Evidence,
Evidence Sufficiency Result, Closure Evaluation, lifecycle event, or State transition. Those
are all produced, every time, by calling their own real public canonical owner during the
proof run (``NO_MANUAL_INTERMEDIATE_CANONICAL_RECORD_CONSTRUCTION=true``).

This module is deliberately self-contained: it does not import from ``tests/difference_
helpers.py``, ``tests/authority_helpers.py``, ``tests/change_helpers.py`` or ``tests/evidence_
helpers.py`` (the shared, cross-suite test-support fixtures used throughout Phase 3-7's own
component/integration tests) even though several of its literal shapes below deliberately
match theirs field-for-field -- those are the real, frozen request schemas
(``01_SCHEMA/observation/observation_scope.schema.json`` etc.), not an arbitrary shape this
module invented, so matching them is fidelity to the schema, not duplication of test-support
code. Keeping this module's own literal values independent means a future, unrelated change to
those shared test-support fixtures can never silently drift what Phase 8's own pinned fixture
world asserts (``PHASE_8_FIXTURE_BINDING_NE_PHASE_9_BINDING=true`` -- this is proof/test
infrastructure only, never a second canonical Binding, Objective, State, Observation,
Difference, Authority, Change, Evidence or Reflow producer).

The one deliberate exception is the real Kernel-source-witness machinery
(``tests/state_helpers.py``'s ``real_kernel_source_snapshot``/``real_kernel_git_objects``/
``genesis_source_snapshot_records``) -- that is not business/domain fixture data at all, it is
the same real, content-addressed proof of this repository's own actual Git objects every
Phase 7 test already depends on, and re-deriving it here would only risk a second, silently
divergent copy of a proof that must name exactly one real commit/tree/blob chain.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.observation.source_snapshot import build_source_snapshot

#: This vertical proof's own dedicated project/objective/predicate/scope identities --
#: distinct from every other suite's shared ``PRJ-0001``/``TP-0001`` fixtures, so a defect in
#: this proof's own inputs can never be masked or amplified by an unrelated suite's fixture
#: state, and vice versa.
PROJECT_ID = "PRJ-VP8-0001"
OBJECTIVE_ID = "OBJ-VP8-0001"
OBJECTIVE_REVISION_ID = "OBJ-REV-VP8-0001"
PREDICATE_ID = "TP-VP8-0001"
SCOPE_ID = "OBS-SCOPE-VP8-0001"
SUBJECT = "vertical_proof.readiness_marker"
REPOSITORY = "manosube/example-vertical-proof-fixture"
BRANCH = "main"

HUMAN_AUTHORITY: dict[str, Any] = {"kind": "human_authority", "id": "AUTH-VP8-0001"}

#: Explicit instants only -- never a wall-clock read (``UNKNOWN_IS_PASS=false`` extends to
#: "not observed" including a fixture that would make its own re-runs non-deterministic).
OBJECTIVE_RECORDED_AT = "2026-09-05T08:00:00Z"
BEFORE_OBSERVATION_STARTED_AT = "2026-09-05T08:05:00Z"
BEFORE_OBSERVATION_ENDED_AT = "2026-09-05T08:05:30Z"
BEFORE_SNAPSHOT_TIME = "2026-09-05T08:04:00Z"
AUTHORITY_EVALUATION_TIME = "2026-09-05T08:10:00Z"
CHANGE_RESULT_OBSERVATION_STARTED_AT = "2026-09-05T08:20:00Z"
CHANGE_RESULT_OBSERVATION_ENDED_AT = "2026-09-05T08:20:30Z"
VERIFICATION_OBSERVATION_STARTED_AT = "2026-09-05T08:25:00Z"
VERIFICATION_OBSERVATION_ENDED_AT = "2026-09-05T08:25:30Z"
AFTER_SNAPSHOT_TIME = "2026-09-05T08:19:00Z"
EVIDENCE_RECORDED_AT = "2026-09-05T08:30:00Z"
SUFFICIENCY_EVALUATED_AT = "2026-09-05T08:35:00Z"
REFLOW_INSTANT = "2026-09-05T08:40:00Z"

METHOD_REF: dict[str, Any] = {"kind": "observation_method", "id": "OBS-METHOD-VP8-0001"}
OBSERVATION_METHOD: dict[str, Any] = {
    "method_profile": "MANOSUBE-OBSERVATION-METHOD-SHA256-0.1",
    "procedure_kind": "CANONICAL_OBSERVER",
    "procedure_ref": {
        "kind": "observer_procedure",
        "id": "OBS-PROCEDURE-VP8-0001",
        "version": "0.1",
        "semantic_fingerprint": "sha256:" + "e" * 64,
    },
    "normalization_profile": "FIXTURE-0.1",
    "input_contract_ref": {"kind": "schema", "id": "OBS-INPUT-01"},
    "output_contract_refs": {
        "collection_kind": "UNORDERED_SET",
        "members": [{"kind": "schema", "id": "NORMALIZED-FACT-01"}],
    },
    "execution_boundary_ref": {"kind": "execution_boundary", "id": "KERNEL-LOCAL"},
}

#: Two distinct, real, content-addressed Source Snapshots -- the bounded before/after
#: source-world inputs the Issue's own fixture requirement names. No Change Executor exists
#: in this Kernel (``CHANGE_EXECUTOR_IMPLEMENTED=false``), so nothing here claims the
#: fixture's own Change *caused* the before/after difference in these two snapshots' content --
#: only that the Observation owner can observe each side independently, exactly as
#: ``NATURAL_PHASE_8_ROUTE`` requires.
BEFORE_SOURCE_SNAPSHOT: dict[str, Any] = build_source_snapshot(
    source_locator="tests/fixtures/vertical_proof/before_source_world.txt",
    content_digest="sha256:" + "5" * 64,
    captured_at=BEFORE_SNAPSHOT_TIME,
)
BEFORE_SNAPSHOT_REF: dict[str, str] = {
    "kind": "source_snapshot",
    "id": BEFORE_SOURCE_SNAPSHOT["source_snapshot_id"],
}

AFTER_SOURCE_SNAPSHOT: dict[str, Any] = build_source_snapshot(
    source_locator="tests/fixtures/vertical_proof/after_source_world.txt",
    content_digest="sha256:" + "6" * 64,
    captured_at=AFTER_SNAPSHOT_TIME,
)
AFTER_SNAPSHOT_REF: dict[str, str] = {
    "kind": "source_snapshot",
    "id": AFTER_SOURCE_SNAPSHOT["source_snapshot_id"],
}

ARTIFACT: dict[str, Any] = {
    "kind": "artifact",
    "id": "ARTIFACT-VP8-0001",
    "content_sha256": "d" * 64,
    "byte_length": 64,
    "media_type": "application/json",
}

#: An Observation's own ``observation_evidence_refs`` is a bare, declared forward-reference
#: field (the schema requires at least one entry; ``derive_differences`` requires it too) --
#: not a resolved cross-check against a real Evidence record's own content-addressed id, which
#: nothing in the Observation/Difference producers performs. Every existing predecessor
#: fixture in this Kernel's own test suite (``tests/difference_helpers.py``'s own
#: ``EVIDENCE_REF``) uses exactly this same bare-placeholder pattern for the identical reason.
EVIDENCE_REF: dict[str, str] = {"kind": "observation_evidence", "id": "EVID-VP8-0001"}
NEGATIVE_EVIDENCE_REF: dict[str, str] = {"kind": "negative_evidence", "id": "NEG-EVID-VP8-0001"}


def target_predicate() -> dict[str, Any]:
    """This proof's one Target Predicate: the readiness marker reads ``"READY"``."""

    return {
        "predicate_id": PREDICATE_ID,
        "subject": SUBJECT,
        "operator": "equals",
        "expected_value": "READY",
        "observation_scope": "vertical_proof",
        "evidence_requirement": "E1",
        "unknown_policy": "INCOMPLETE",
        "criticality": "mandatory",
    }


def objective_revision() -> dict[str, Any]:
    """The one, real (Human-Authority-declared) Objective Revision this proof's Difference
    is derived against -- Objective/Objective Revision has no producing owner of its own
    (``difference/objective.py``'s own docstring: "An Objective revision is Human Authority
    input this phase consumes and re-emits"), so a literal, schema-valid dict is the correct,
    not a compromise, way to supply it."""

    return {
        "schema_version": "0.1",
        "objective_id": OBJECTIVE_ID,
        "objective_revision_id": OBJECTIVE_REVISION_ID,
        "project_id": PROJECT_ID,
        "statement": "The vertical proof's readiness marker reaches READY.",
        "owner_authority_ref": dict(HUMAN_AUTHORITY),
        "target_predicates": [target_predicate()],
        "completion_policy": {"mode": "ALL", "contradiction_policy": "BLOCK"},
        "boundary_ref": {"kind": "objective_boundary", "id": "BOUND-VP8-0001"},
        "constitutional_constraints": [],
        "status": "ACTIVE",
        "revision": 0,
        "previous_objective_ref": None,
        "change_reason": "initial vertical-proof objective",
        "base_semantic_fingerprint": None,
        "semantic_change_summary": "initial vertical-proof objective revision",
        "human_authority_ref": dict(HUMAN_AUTHORITY),
        "recorded_at": OBJECTIVE_RECORDED_AT,
    }


def observation_scope(*, snapshot_ref: dict[str, str]) -> dict[str, Any]:
    """A schema-valid ``observation_scope``, bounded to exactly one Source Snapshot."""

    return {
        "schema_version": "0.1",
        "scope_id": SCOPE_ID,
        "project_id": PROJECT_ID,
        "target_identity": PREDICATE_ID,
        "included_subjects": [SUBJECT],
        "excluded_subjects": ["vertical_proof.secret"],
        "boundary_root": "/vertical_proof",
        "path_policy": {
            "relative_locators_only": True,
            "symlink_escape": "BLOCK",
            "submodule_traversal": "DECLARED_ONLY",
            "mount_escape": "BLOCK",
            "credential_paths": "EXCLUDE",
        },
        "observation_window": {"start": "2026-09-05T08:00:00Z", "end": "2026-09-05T09:00:00Z"},
        "target_effective_window": {
            "start": "2026-09-05T07:00:00Z",
            "end": "2026-09-05T09:00:00Z",
        },
        "freshness_limit_seconds": 3600,
        "cutoff": "2026-09-05T09:00:00Z",
        "source_snapshot_refs": [dict(snapshot_ref)],
        "enumeration_rule": {"kind": "enumeration_rule", "id": "ENUM-VP8-0001"},
        "completion_predicate": {"kind": "completion_predicate", "id": "COMPLETE-VP8-0001"},
        "method_ref": dict(METHOD_REF),
        "attempt_policy": {"max_attempts": 1, "timeout_seconds": 60, "retry_on": []},
        "blind_spots": [],
        "scope_status": "COMPLETE",
    }


def raw_fact(*, value: str, snapshot_id: str) -> dict[str, Any]:
    return {
        "subject": SUBJECT,
        "predicate": "equals@v1",
        "value": value,
        "value_type": "STRING",
        "unit": None,
        "effective_boundary": {
            "kind": "SOURCE_SNAPSHOT",
            "identity": snapshot_id,
            "start": None,
            "end": None,
        },
    }


def observation_request(
    *,
    value: str,
    snapshot_ref: dict[str, str],
    snapshot_locator: str,
    snapshot_time: str,
    fingerprint: dict[str, Any],
    state_revision: int,
    started_at: str,
    ended_at: str,
    attempt_id: str,
) -> dict[str, Any]:
    """One schema-valid Observation request over this proof's own bounded source world."""

    scope = observation_scope(snapshot_ref=snapshot_ref)
    return {
        "project_id": PROJECT_ID,
        "state_revision_observed": state_revision,
        "state_fingerprint_observed": deepcopy(fingerprint),
        "target_identity": PREDICATE_ID,
        "target_kind": "FIXTURE",
        "scope": scope,
        "method_ref": dict(METHOD_REF),
        "time_boundary": {
            "observation_started_at": started_at,
            "observation_ended_at": ended_at,
            "target_effective_start": "2026-09-05T07:00:00Z",
            "target_effective_end": "2026-09-05T09:00:00Z",
            "source_snapshot_time": snapshot_time,
        },
        "source_snapshot_refs": [dict(snapshot_ref)],
        "normalization_profile": "FIXTURE-0.1",
        "source_occurrences": [
            {
                "source_ref": dict(snapshot_ref),
                "source_locator": snapshot_locator,
                "facts": [raw_fact(value=value, snapshot_id=snapshot_ref["id"])],
            }
        ],
        "attempts": [
            {
                "attempt_id": attempt_id,
                "method_ref": dict(METHOD_REF),
                "started_at": started_at,
                "ended_at": ended_at,
                "result": "COMPLETE",
                "failure_class": None,
            }
        ],
        "blind_spots": [],
        "observation_evidence_refs": [dict(EVIDENCE_REF)],
        "negative_evidence_refs": [dict(NEGATIVE_EVIDENCE_REF)],
        "negative_claims": [],
        "collection_complete": True,
    }


def before_observation_request(
    *, fingerprint: dict[str, Any], state_revision: int
) -> dict[str, Any]:
    """The genesis-world Observation: the readiness marker reads ``"NOT-READY"``."""

    return observation_request(
        value="NOT-READY",
        snapshot_ref=BEFORE_SNAPSHOT_REF,
        snapshot_locator=BEFORE_SOURCE_SNAPSHOT["source_locator"],
        snapshot_time=BEFORE_SNAPSHOT_TIME,
        fingerprint=fingerprint,
        state_revision=state_revision,
        started_at=BEFORE_OBSERVATION_STARTED_AT,
        ended_at=BEFORE_OBSERVATION_ENDED_AT,
        attempt_id="ATTEMPT-VP8-0001",
    )


def change_result_observation_request(
    *, fingerprint: dict[str, Any], state_revision: int
) -> dict[str, Any]:
    """The Change's own post-change-world Observation: the readiness marker now reads
    ``"READY"``. Bound into ``change_result_evidence``'s own ``after_state`` -- never used as
    Reflow's own independent ``reobservation`` (see :func:`verification_observation_request`
    for that role; reusing this exact Observation for both would collide with the Kernel's own
    ``G8`` anti-self-closing check, since a Change's own claimed result cannot also stand in as
    the independent re-observation that verifies it)."""

    return observation_request(
        value="READY",
        snapshot_ref=AFTER_SNAPSHOT_REF,
        snapshot_locator=AFTER_SOURCE_SNAPSHOT["source_locator"],
        snapshot_time=AFTER_SNAPSHOT_TIME,
        fingerprint=fingerprint,
        state_revision=state_revision,
        started_at=CHANGE_RESULT_OBSERVATION_STARTED_AT,
        ended_at=CHANGE_RESULT_OBSERVATION_ENDED_AT,
        attempt_id="ATTEMPT-VP8-0002",
    )


def verification_observation_request(
    *, fingerprint: dict[str, Any], state_revision: int
) -> dict[str, Any]:
    """Reflow's own independent re-observation of the identical real post-change world --
    a second, genuinely separate Observation Engine invocation (a later observation window,
    its own ``attempt_id``), not a restatement of :func:`change_result_observation_request`.
    This is the one Observation whose identity becomes ``reobservation.after_observation_
    refs`` in the Reflow closure request."""

    return observation_request(
        value="READY",
        snapshot_ref=AFTER_SNAPSHOT_REF,
        snapshot_locator=AFTER_SOURCE_SNAPSHOT["source_locator"],
        snapshot_time=AFTER_SNAPSHOT_TIME,
        fingerprint=fingerprint,
        state_revision=state_revision,
        started_at=VERIFICATION_OBSERVATION_STARTED_AT,
        ended_at=VERIFICATION_OBSERVATION_ENDED_AT,
        attempt_id="ATTEMPT-VP8-0003",
    )


def derivation_request(
    *,
    observation_bundle: dict[str, Any] | None,
    fingerprint: dict[str, Any],
    state_revision: int,
    snapshot_ref: dict[str, str] = BEFORE_SNAPSHOT_REF,
) -> dict[str, Any]:
    """A one-binding Difference derivation request over this proof's own Objective/Target.

    *snapshot_ref* must name the same Source Snapshot the real *observation_bundle* being
    bound here was itself observed against (``BEFORE_SNAPSHOT_REF`` for the before-world
    Observation, ``AFTER_SNAPSHOT_REF`` for the verification re-observation) -- the bound
    ``observation_scope``'s own declared snapshot set is independently cross-checked against
    what the Observation actually reports, so a caller cannot bind a real re-observation of
    one snapshot to a declared Scope naming a different one.
    """

    return {
        "schema_version": "0.1",
        "identity_profile": "MANOSUBE-DIFFERENCE-SHA256-0.1",
        "comparison_profile": "MANOSUBE-DIFFERENCE-COMPARISON-0.1",
        "normalization_profile": "MANOSUBE-DIFFERENCE-NORMALIZATION-0.1",
        "project_id": PROJECT_ID,
        "objective_revision": objective_revision(),
        "state_revision": state_revision,
        "state_fingerprint": deepcopy(fingerprint),
        "closure_policy_requirements": {"minimum_evidence_level": "E1"},
        "observation_method": deepcopy(OBSERVATION_METHOD),
        "bindings": [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": observation_scope(snapshot_ref=snapshot_ref),
                "observation_bundle": observation_bundle,
            }
        ],
    }


#: The requested Change action/scope: one bounded, reversible write, matching exactly what
#: :func:`authority_rule` below authorizes -- the Authority owner's own ``AUTONOMOUS``
#: decision is real only because the requested action/scope and the rule's own declared
#: ``action_kinds``/``scope`` genuinely agree, not because this fixture asserts they do.
def action_scope() -> dict[str, Any]:
    return {
        "repository": REPOSITORY,
        "branch": BRANCH,
        "paths": ["src/vertical_proof_target.py"],
        "subjects": [],
    }


def authority_rule(*, project_id: str) -> dict[str, Any]:
    """A real Authority Rule permitting exactly this proof's requested action/scope --
    identity computed by the real ``authority.identity.rule_id`` function, not asserted."""

    from manosube_agent_civilization.authority.identity import rule_id

    record = {
        "schema_version": "0.1",
        "authority_rule_id": "",
        "project_id": project_id,
        "action_kinds": ["WRITE_FILE"],
        "maximum_reversibility": "REVERSIBLE",
        "scope": action_scope(),
        "decision": "AUTONOMOUS",
        "declared_by": dict(HUMAN_AUTHORITY),
    }
    record["authority_rule_id"] = rule_id(record)
    return record


def requested_action() -> dict[str, Any]:
    """The one requested Change action -- identity computed by the real
    ``authority.identity.action_fingerprint`` function."""

    from manosube_agent_civilization.authority.identity import action_fingerprint

    record = {
        "action_kind": "WRITE_FILE",
        "reversibility": "REVERSIBLE",
        "operation": {"body": "mark the vertical-proof readiness fixture READY"},
        "action_semantic_fingerprint": "",
    }
    record["action_semantic_fingerprint"] = action_fingerprint(record)
    return record


def closure_policy(difference_id: str) -> dict[str, Any]:
    """The one Closure Policy this proof's Difference is evaluated under -- satisfiable by
    the evidence level this Kernel truthfully derives (E1) and the Static+Natural-Cycle
    Invariant classes it truthfully implements
    (``FULL_EXTERNAL_RUNTIME_CHANGE_EXECUTION=NOT_CLAIMED``,
    ``G9_NON_NULL_REQUIRED_OBSERVATION_SCOPE=NOT_CLAIMED_FAIL_CLOSED`` -- explicit ``null``,
    used honestly, not to widen a false claim of broader scope support)."""

    from manosube_agent_civilization.difference.identity import (
        closure_policy_id,
        policy_semantic_fingerprint,
    )

    policy: dict[str, Any] = {
        "schema_version": "0.1",
        "closure_policy_id": "",
        "policy_version": "0.1",
        "policy_semantic_fingerprint": "",
        "subject_difference_ref": {"kind": "difference", "id": difference_id},
        "target_predicate_ref": {"kind": "target_predicate", "id": PREDICATE_ID},
        "required_observation_scope": None,
        "minimum_evidence_level": "E1",
        "required_claims": [],
        "required_invariants": [],
        "allowed_terminal_states": ["CLOSED", "BLOCKED", "RETAINED"],
        "independent_verification_required": False,
        "maximum_evidence_age": None,
        "contradiction_policy": "FAIL_CLOSED",
        "reopen_conditions": [],
    }
    policy["policy_semantic_fingerprint"] = policy_semantic_fingerprint(policy)
    policy["closure_policy_id"] = closure_policy_id(
        policy["policy_semantic_fingerprint"], difference_id
    )
    return policy
