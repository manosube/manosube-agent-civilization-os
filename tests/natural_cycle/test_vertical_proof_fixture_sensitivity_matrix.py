"""Phase 8 Vertical Proof -- semantic fixture-input-class sensitivity matrix (P8-R1-F4,
SHUKOU Phase 8 structural-review round 1).

Issue #41's own item E.2 ("changing any semantic fixture field changes the appropriate
downstream identity or verdict") was proven, before this round, against exactly one field:
the before-Observation's own observed value (``test_vertical_proof_negative_routes.py::
test_e2_...``). SHUKOU's own finding: ``ONE_FIELD_SENSITIVITY_PROVES_ALL_FIXTURE_FIELDS=
false`` -- a matrix covering every named semantic input *class* is required instead.

Each test below mutates exactly one bounded fixture input from a real assembled route
(never a second, hand-built substitute) and asserts the real, empirically-observed
downstream effect. One class is a *disclosed, bounded non-claim* rather than "fails closed"
or "changes the verdict" -- reported as such, not silently omitted or misrepresented:

    POST_CHANGE_OBSERVATION's downstream ``status``/``evidence_level`` are unaffected by the
        observed *value* (Observation completeness is measured independently of what was
        found) -- the real, changed effect there is on the Evidence record's own
        content-addressed identity and its ``observed_result``, both asserted directly
        below, not on those two categorical fields.

AUTHORITY_EVALUATION_INSTANT was, before P8-R2-F3 (SHUKOU Phase 8 structural-review round
2), reported here as fully inert -- true only along the one route this matrix originally
exercised (a rule granting ``AUTONOMOUS`` outright, no Approval ever consulted for its
outcome). ``authority/approval.py::binding_mismatches`` reads ``evaluation_time`` against
every Approval's own ``approved_at``/``expires_at`` validity window whenever an Approval
must actually bind a request (``HUMAN_APPROVAL_REQUIRED`` with a real Approval on file) --
so the field is not inert in general. What *is* still true, and is unchanged from the
original finding: the real Authority Decision's own content-addressed ``authority_decision_
id`` never includes ``evaluation_time`` (mirroring State's own Semantic Fingerprint
excluding ``observed_at``/``observer`` -- ``00_KERNEL/KERNEL_INDEX.md`` §2 -- and
Observation's own identity excluding ``observation_evidence_refs`` and the observed value
itself). Its corrected role: ``AUTHORITY_EVALUATION_INSTANT_ROLE=TRANSIENT_ADMISSION_
CONTEXT``, ``AUTHORITY_EVALUATION_INSTANT_IN_DECISION_ID=false``, ``AUTHORITY_EVALUATION_
INSTANT_AFFECTS_TIME_BOUND_ADMISSION=true`` -- see :func:`test_p8r2f3_...` below, which
proves the time-bound-Approval route this matrix's original test never exercised.

Required matrix (Issue #41's own required rows, in order):

    INPUT_CLASS                    MUTATED_FIELD                  ACTUAL EFFECT
    OBJECTIVE_OR_OBJECTIVE_REVISION objective_revision.statement   difference_id / objective_
                                                                    semantic_fingerprint change
    BEFORE_OBSERVATION_VALUE       before Observation raw value    Difference verdict changes
                                                                    (0 vs 1 Difference produced)
    SOURCE_SNAPSHOT_IDENTITY_OR_DIGEST source_snapshot content_digest observation_id changes
    AUTHORITY_RULE                 authority_rule.action_kinds     Authority verdict changes
                                                                    (AUTONOMOUS -> HUMAN_
                                                                    APPROVAL_REQUIRED)
    REQUESTED_ACTION               requested_action.action_kind    Authority verdict changes
    CHANGE_SCOPE                   action_scope.paths              Authority verdict changes
    POST_CHANGE_OBSERVATION        post-change raw value           Evidence identity / observed_
                                                                    result changes (status/level
                                                                    unaffected -- disclosed)
    VERIFICATION_OBSERVATION       verification raw value          Reflow fails closed (non-
                                                                    SATISFIED, refuses CLOSED)
    CLOSURE_POLICY                 minimum_evidence_level           Sufficiency verdict changes
                                                                    (SUFFICIENT -> INSUFFICIENT)
    EVIDENCE_INSTANT               recorded_at                     Evidence derivation fails
                                                                    closed (already proven in
                                                                    test_vertical_proof_negative_
                                                                    routes.py item E3)
    AUTHORITY_EVALUATION_INSTANT   evaluation_time                  transient admission context
                                                                    (P8-R2-F3): inert on the
                                                                    no-Approval AUTONOMOUS-by-
                                                                    rule route, but governs
                                                                    real time-bound Approval
                                                                    admission on the route
                                                                    where an Approval must
                                                                    bind; never part of
                                                                    authority_decision_id
                                                                    either way
    REFLOW_INSTANT                 reflow_instant                   Reflow fails closed (already
                                                                    proven by P8-R1-F5's own
                                                                    provenance check, re-asserted
                                                                    here for this matrix's
                                                                    completeness)
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
from tests.fixtures import vertical_proof as fx
from tests.natural_cycle.proof import (
    assemble_vertical_proof_route,
    build_store,
    check_authority,
    derive_difference,
    derive_the_change_result_evidence,
    evaluate_the_sufficiency,
    initialize_genesis,
    observe_before,
    observe_change_result,
)

from manosube_agent_civilization.authority import evaluate_authority
from manosube_agent_civilization.authority.errors import AuthorityError
from manosube_agent_civilization.authority.identity import (
    action_fingerprint,
    approval_id,
    change_intent_fingerprint,
    rule_id,
)
from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.identity import (
    closure_policy_id,
    policy_semantic_fingerprint,
)
from manosube_agent_civilization.evidence.engine import derive_evidence
from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.observation.source_snapshot import build_source_snapshot
from manosube_agent_civilization.reflow.errors import ReflowError
from manosube_agent_civilization.reflow.route import reflow


def test_p8r1f4_objective_or_objective_revision_changes_the_difference_identity(
    tmp_path: Path,
) -> None:
    """INPUT_CLASS=OBJECTIVE_OR_OBJECTIVE_REVISION, MUTATED_FIELD=objective_revision.
    statement. FAIL_CLOSED_OR_REDERIVED=re-derived: a different Objective Revision content
    re-derives a genuinely different ``difference_id``/``objective_semantic_fingerprint``,
    through the real Difference owner, no hand-built substitute."""

    store = build_store(tmp_path)
    genesis = initialize_genesis(store)
    before = observe_before(genesis)
    real_request = fx.derivation_request(
        observation_bundle=before["bundle"],
        fingerprint=genesis["semantic_fingerprint"],
        state_revision=genesis["state_revision"],
    )
    mutated_request = copy.deepcopy(real_request)
    mutated_request["objective_revision"]["statement"] = "A totally different objective."

    real_result = derive_differences(real_request)
    mutated_result = derive_differences(mutated_request)

    real_diff = real_result["differences"][0]
    mutated_diff = mutated_result["differences"][0]
    assert real_diff["difference_id"] != mutated_diff["difference_id"]
    assert (
        real_diff["objective_semantic_fingerprint"]
        != mutated_diff["objective_semantic_fingerprint"]
    )


def test_p8r1f4_source_snapshot_identity_or_digest_changes_the_observation_identity(
    tmp_path: Path,
) -> None:
    """INPUT_CLASS=SOURCE_SNAPSHOT_IDENTITY_OR_DIGEST, MUTATED_FIELD=source_snapshot.
    content_digest. FAIL_CLOSED_OR_REDERIVED=re-derived: ``observation.identity.
    OBSERVATION_SEMANTIC_FIELDS`` includes ``source_snapshot_refs``, so a differently-keyed
    real Source Snapshot re-derives a genuinely different ``observation_id``, through the
    real Observation owner."""

    store = build_store(tmp_path)
    genesis = initialize_genesis(store)
    before = observe_before(genesis)

    mutated_snapshot = build_source_snapshot(
        source_locator=fx.BEFORE_SOURCE_SNAPSHOT["source_locator"],
        content_digest="sha256:" + "7" * 64,
        captured_at=fx.BEFORE_SNAPSHOT_TIME,
    )
    mutated_ref = {"kind": "source_snapshot", "id": mutated_snapshot["source_snapshot_id"]}
    mutated_request = fx.observation_request(
        value="NOT-READY",
        snapshot_ref=mutated_ref,
        snapshot_locator=fx.BEFORE_SOURCE_SNAPSHOT["source_locator"],
        snapshot_time=fx.BEFORE_SNAPSHOT_TIME,
        fingerprint=genesis["semantic_fingerprint"],
        state_revision=genesis["state_revision"],
        started_at=fx.BEFORE_OBSERVATION_STARTED_AT,
        ended_at=fx.BEFORE_OBSERVATION_ENDED_AT,
        attempt_id="ATTEMPT-VP8-0001",
    )
    mutated_bundle = observe(mutated_request)
    assert (
        mutated_bundle["observations"][-1]["observation_id"]
        != before["bundle"]["observations"][-1]["observation_id"]
    )


def _authority_request(difference: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "project_id": difference["project_id"],
        "difference": difference,
        "requested_action": fx.requested_action(),
        "requested_scope": fx.action_scope(),
        "current_state_revision": difference["observed_state_revision"],
        "current_state_fingerprint": difference["observed_state_fingerprint"],
        "authority_rules": [fx.authority_rule(project_id=difference["project_id"])],
        "prohibitions": [],
        "approvals": [],
        "evaluation_time": fx.AUTHORITY_EVALUATION_TIME,
    }


def test_p8r1f4_authority_rule_changes_the_authority_verdict(tmp_path: Path) -> None:
    """INPUT_CLASS=AUTHORITY_RULE, MUTATED_FIELD=authority_rule.action_kinds.
    FAIL_CLOSED_OR_REDERIVED=fails closed: a rule that no longer covers the requested
    action's own kind denies autonomous authorization, through the real Authority owner."""

    store = build_store(tmp_path)
    genesis = initialize_genesis(store)
    before = observe_before(genesis)
    difference = derive_difference(genesis, before)["difference"]
    base_request = _authority_request(difference)
    assert evaluate_authority(base_request)["decision"] == "AUTONOMOUS"

    mutated_rule = dict(fx.authority_rule(project_id=difference["project_id"]))
    mutated_rule["action_kinds"] = ["DELETE_FILE"]
    mutated_rule["authority_rule_id"] = rule_id(mutated_rule)
    mutated_request = dict(base_request)
    mutated_request["authority_rules"] = [mutated_rule]
    assert evaluate_authority(mutated_request)["decision"] != "AUTONOMOUS"


def test_p8r1f4_requested_action_changes_the_authority_verdict(tmp_path: Path) -> None:
    """INPUT_CLASS=REQUESTED_ACTION, MUTATED_FIELD=requested_action.action_kind.
    FAIL_CLOSED_OR_REDERIVED=fails closed: an action kind the declared Authority rule does
    not name is denied autonomous authorization."""

    store = build_store(tmp_path)
    genesis = initialize_genesis(store)
    before = observe_before(genesis)
    difference = derive_difference(genesis, before)["difference"]
    base_request = _authority_request(difference)
    assert evaluate_authority(base_request)["decision"] == "AUTONOMOUS"

    mutated_action = dict(fx.requested_action())
    mutated_action["action_kind"] = "DELETE_FILE"
    mutated_action["action_semantic_fingerprint"] = action_fingerprint(mutated_action)
    mutated_request = dict(base_request)
    mutated_request["requested_action"] = mutated_action
    assert evaluate_authority(mutated_request)["decision"] != "AUTONOMOUS"


def test_p8r1f4_change_scope_changes_the_authority_verdict(tmp_path: Path) -> None:
    """INPUT_CLASS=CHANGE_SCOPE, MUTATED_FIELD=action_scope.paths. FAIL_CLOSED_OR_REDERIVED=
    fails closed: a scope the declared Authority rule was never evaluated against is denied
    autonomous authorization."""

    store = build_store(tmp_path)
    genesis = initialize_genesis(store)
    before = observe_before(genesis)
    difference = derive_difference(genesis, before)["difference"]
    base_request = _authority_request(difference)
    assert evaluate_authority(base_request)["decision"] == "AUTONOMOUS"

    mutated_scope = dict(fx.action_scope())
    mutated_scope["paths"] = ["src/an_entirely_different_target.py"]
    mutated_request = dict(base_request)
    mutated_request["requested_scope"] = mutated_scope
    assert evaluate_authority(mutated_request)["decision"] != "AUTONOMOUS"


def test_p8r1f4_post_change_observation_value_changes_the_evidence_identity(
    tmp_path: Path,
) -> None:
    """INPUT_CLASS=POST_CHANGE_OBSERVATION, MUTATED_FIELD=post-change Observation's own raw
    value. FAIL_CLOSED_OR_REDERIVED=re-derived: the real Change-result Evidence's own
    content-addressed ``evidence_id`` and ``observed_result`` change with the observed value
    -- disclosed exception: ``status``/``evidence_level`` do not, since those measure the
    Observation's own completeness, never what it found (the identical exclusion already
    established for Observation identity itself)."""

    store = build_store(tmp_path)
    genesis = initialize_genesis(store)
    before = observe_before(genesis)
    difference = derive_difference(genesis, before)["difference"]
    authority = check_authority(difference)
    from tests.natural_cycle.proof import derive_the_change

    change = derive_the_change(authority)
    change_result_obs = observe_change_result(genesis, before, change)
    real_bundle = derive_the_change_result_evidence(genesis, before, change, change_result_obs)
    real_evidence = real_bundle["change_result_evidence"]

    mutated_post_change_request = fx.observation_request(
        value="STILL-NOT-READY",
        snapshot_ref=fx.AFTER_SNAPSHOT_REF,
        snapshot_locator=fx.AFTER_SOURCE_SNAPSHOT["source_locator"],
        snapshot_time=fx.AFTER_SNAPSHOT_TIME,
        fingerprint=genesis["semantic_fingerprint"],
        state_revision=genesis["state_revision"],
        started_at=fx.CHANGE_RESULT_OBSERVATION_STARTED_AT,
        ended_at=fx.CHANGE_RESULT_OBSERVATION_ENDED_AT,
        attempt_id="ATTEMPT-VP8-0002",
    )
    mutated_request = dict(real_bundle["change_result_evidence_request"])
    mutated_request["post_change_observation_request"] = mutated_post_change_request
    mutated_evidence = derive_evidence(mutated_request)

    assert mutated_evidence["evidence_id"] != real_evidence["evidence_id"]
    assert mutated_evidence["observed_result"] != real_evidence["observed_result"]
    # Disclosed, not silently omitted: these two fields are insensitive to the observed
    # value by the identical design Observation's own identity already follows.
    assert mutated_evidence["status"] == real_evidence["status"]
    assert mutated_evidence["evidence_level"] == real_evidence["evidence_level"]


def test_p8r1f4_verification_observation_value_fails_the_route_closed(tmp_path: Path) -> None:
    """INPUT_CLASS=VERIFICATION_OBSERVATION, MUTATED_FIELD=Reflow's own independent
    re-observation raw value. FAIL_CLOSED_OR_REDERIVED=fails closed: a re-observation
    reporting the Target still unsatisfied makes the Closure Evaluation itself
    non-``SATISFIED``, refusing the ``CLOSED`` proposal -- through the real Difference/
    Reflow owners, not a hand-asserted refusal."""

    assembly = assemble_vertical_proof_route(tmp_path)
    genesis = assembly["genesis_state"]

    mutated_request = fx.observation_request(
        value="STILL-NOT-READY",
        snapshot_ref=fx.AFTER_SNAPSHOT_REF,
        snapshot_locator=fx.AFTER_SOURCE_SNAPSHOT["source_locator"],
        snapshot_time=fx.AFTER_SNAPSHOT_TIME,
        fingerprint=genesis["semantic_fingerprint"],
        state_revision=genesis["state_revision"],
        started_at=fx.VERIFICATION_OBSERVATION_STARTED_AT,
        ended_at=fx.VERIFICATION_OBSERVATION_ENDED_AT,
        attempt_id="ATTEMPT-VP8-0003",
    )
    mutated_bundle = observe(mutated_request)
    mutated_observation_id = mutated_bundle["observations"][-1]["observation_id"]

    kwargs = dict(assembly["reflow_kwargs"])
    closure_request = dict(kwargs["closure_request"])
    closure_request["reobservation"] = {
        "derivation_request": fx.derivation_request(
            observation_bundle=mutated_bundle,
            fingerprint=genesis["semantic_fingerprint"],
            state_revision=genesis["state_revision"],
            snapshot_ref=fx.AFTER_SNAPSHOT_REF,
        ),
        "after_observation_refs": [{"kind": "observation", "id": mutated_observation_id}],
    }
    kwargs["closure_request"] = closure_request
    kwargs["observation_refs"] = [{"kind": "observation", "id": mutated_observation_id}]

    with pytest.raises(ReflowError, match="must propose BLOCKED or RETAINED"):
        reflow(assembly["store"], **kwargs)


def test_p8r1f4_closure_policy_minimum_evidence_level_changes_the_sufficiency_verdict(
    tmp_path: Path,
) -> None:
    """INPUT_CLASS=CLOSURE_POLICY, MUTATED_FIELD=minimum_evidence_level. FAIL_CLOSED_OR_
    REDERIVED=re-derived: raising the required level above what this Kernel truthfully
    reaches (E1) changes the real Sufficiency verdict from ``SUFFICIENT`` to
    ``INSUFFICIENT``, through the real Sufficiency owner."""

    store = build_store(tmp_path)
    genesis = initialize_genesis(store)
    before = observe_before(genesis)
    difference = derive_difference(genesis, before)["difference"]
    policy = fx.closure_policy(difference["difference_id"])
    authority = check_authority(difference)
    from tests.natural_cycle.proof import derive_the_change

    change = derive_the_change(authority)
    change_result_obs = observe_change_result(genesis, before, change)
    change_result_evidence_bundle = derive_the_change_result_evidence(
        genesis, before, change, change_result_obs
    )

    real_sufficiency = evaluate_the_sufficiency(
        difference,
        policy,
        observation_evidence_request=before["observation_evidence_request"],
        change_result_evidence_request=change_result_evidence_bundle[
            "change_result_evidence_request"
        ],
    )
    assert real_sufficiency["result"]["result"] == "SUFFICIENT"

    mutated_policy = dict(policy)
    mutated_policy["minimum_evidence_level"] = "E3"
    mutated_policy["policy_semantic_fingerprint"] = policy_semantic_fingerprint(mutated_policy)
    mutated_policy["closure_policy_id"] = closure_policy_id(
        mutated_policy["policy_semantic_fingerprint"], difference["difference_id"]
    )
    mutated_sufficiency = evaluate_the_sufficiency(
        difference,
        mutated_policy,
        observation_evidence_request=before["observation_evidence_request"],
        change_result_evidence_request=change_result_evidence_bundle[
            "change_result_evidence_request"
        ],
    )
    assert mutated_sufficiency["result"]["result"] == "INSUFFICIENT"


def test_p8r1f4_authority_evaluation_instant_is_inert_on_the_no_approval_route(
    tmp_path: Path,
) -> None:
    """INPUT_CLASS=AUTHORITY_EVALUATION_INSTANT, MUTATED_FIELD=evaluation_time, on the one
    route this repository's original vertical proof exercises (a rule granting
    ``AUTONOMOUS`` outright, no Approval ever consulted for the outcome).
    FAIL_CLOSED_OR_REDERIVED=neither, on *this* route -- the real Authority Decision's own
    content-addressed ``authority_decision_id`` and ``decision`` verdict are unaffected by
    this field here, exactly as originally reported. P8-R2-F3 (SHUKOU Phase 8
    structural-review round 2) corrected the *scope* of this claim -- it does not generalize
    to every route, and :func:`test_p8r2f3_authority_evaluation_instant_governs_time_bound_
    approval_admission` below proves the route where the field genuinely matters."""

    store = build_store(tmp_path)
    genesis = initialize_genesis(store)
    before = observe_before(genesis)
    difference = derive_difference(genesis, before)["difference"]
    base_request = _authority_request(difference)
    base_decision = evaluate_authority(base_request)
    assert base_decision["decision"] == "AUTONOMOUS"

    mutated_request = dict(base_request)
    mutated_request["evaluation_time"] = "2020-01-01T00:00:00Z"
    mutated_decision = evaluate_authority(mutated_request)

    assert mutated_decision["decision"] == base_decision["decision"] == "AUTONOMOUS"
    assert mutated_decision["authority_decision_id"] == base_decision["authority_decision_id"]


def test_p8r2f3_authority_evaluation_instant_governs_time_bound_approval_admission(
    tmp_path: Path,
) -> None:
    """P8-R2-F3 (SHUKOU Phase 8 structural-review round 2): on the route the original
    AUTONOMOUS-by-rule test above never exercises -- a rule that itself requires
    ``HUMAN_APPROVAL_REQUIRED``, with a real, time-bound Approval on file -- ``evaluation_
    time`` genuinely decides whether that Approval binds
    (``authority/approval.py::binding_mismatches``' own validity-window check), and so
    genuinely decides the Decision's own ``decision``/``approval_ref``.
    ``AUTHORITY_EVALUATION_INSTANT_ROLE=TRANSIENT_ADMISSION_CONTEXT``,
    ``AUTHORITY_EVALUATION_INSTANT_AFFECTS_TIME_BOUND_ADMISSION=true``.

    ``AUTHORITY_EVALUATION_INSTANT_IN_DECISION_ID=false`` is proven in the same breath, not
    contradicted by the above: two evaluation times that land the Approval in the identical
    outcome (both inside the window, or both outside it) reproduce byte-identical Decision
    content and therefore one identical ``authority_decision_id`` -- only a time that
    actually changes the outcome changes the id, and it changes because the *outcome*
    changed, never because the raw timestamp was folded into the identity itself."""

    store = build_store(tmp_path)
    genesis = initialize_genesis(store)
    before = observe_before(genesis)
    difference = derive_difference(genesis, before)["difference"]

    approval_required_rule = dict(fx.authority_rule(project_id=difference["project_id"]))
    approval_required_rule["decision"] = "HUMAN_APPROVAL_REQUIRED"
    approval_required_rule["authority_rule_id"] = rule_id(approval_required_rule)

    requested_action = fx.requested_action()
    requested_scope = fx.action_scope()
    valid_from = "2026-09-05T08:00:00Z"
    valid_until = "2026-09-05T09:00:00Z"

    approval_record: dict[str, Any] = {
        "schema_version": "0.1",
        "approval_id": "",
        "project_id": difference["project_id"],
        "difference_ref": {"kind": "difference", "id": difference["difference_id"]},
        "change_intent_fingerprint": change_intent_fingerprint(requested_action, requested_scope),
        "change_ref": None,
        "approved_state_revision": difference["observed_state_revision"],
        "approved_state_fingerprint": dict(difference["observed_state_fingerprint"]),
        "approved_action_fingerprint": requested_action["action_semantic_fingerprint"],
        "approved_scope": dict(requested_scope),
        "prohibited_actions": [],
        "approved_by": dict(fx.HUMAN_AUTHORITY),
        "approved_at": valid_from,
        "expires_at": valid_until,
        "status": "ACTIVE",
    }
    approval_record["approval_id"] = approval_id(approval_record)

    def _request(evaluation_time: str) -> dict[str, Any]:
        return {
            "schema_version": "0.1",
            "project_id": difference["project_id"],
            "difference": difference,
            "requested_action": requested_action,
            "requested_scope": requested_scope,
            "current_state_revision": difference["observed_state_revision"],
            "current_state_fingerprint": difference["observed_state_fingerprint"],
            "authority_rules": [approval_required_rule],
            "prohibitions": [],
            "approvals": [approval_record],
            "evaluation_time": evaluation_time,
        }

    # INVALID_EVALUATION_TIME_REJECTED=true: admission belongs to the whole request, not
    # only the branch that happens to read it -- already proven repository-wide (``tests/
    # contract/authority/``); re-asserted once here for this matrix's own completeness.
    with pytest.raises(AuthorityError):
        evaluate_authority(_request("not-a-timestamp"))

    before_window = evaluate_authority(_request("2026-09-05T07:59:59Z"))
    within_window_a = evaluate_authority(_request(valid_from))
    within_window_b = evaluate_authority(_request("2026-09-05T08:30:00Z"))
    after_window = evaluate_authority(_request("2026-09-05T09:00:01Z"))

    # BEFORE_APPROVAL_VALID_FROM / AFTER_APPROVAL_EXPIRY: the Approval does not bind, so
    # authorization is not granted -- APPROVAL_NOT_USED_OR_AUTHORIZATION_NOT_GRANTED.
    for outside in (before_window, after_window):
        assert outside["decision"] == "HUMAN_APPROVAL_REQUIRED"
        assert outside["approval_ref"] is None
        assert "APPROVAL_OUTSIDE_VALIDITY_WINDOW" in outside["decision_reason_codes"]

    # WITHIN_APPROVAL_VALIDITY_WINDOW: the Approval binds and is used, as the contract
    # requires -- APPROVAL_USED_AS_CONTRACT_REQUIRES.
    for inside in (within_window_a, within_window_b):
        assert inside["decision"] == "AUTONOMOUS"
        assert inside["approval_ref"] == {
            "kind": "approval",
            "id": approval_record["approval_id"],
        }

    # AUTHORITY_EVALUATION_INSTANT_IN_DECISION_ID=false: two different valid times that land
    # in the identical real outcome share one Decision id...
    assert within_window_a["authority_decision_id"] == within_window_b["authority_decision_id"]
    assert before_window["authority_decision_id"] == after_window["authority_decision_id"]
    # ...while a time that genuinely changes the outcome changes the id too --
    # AUTHORITY_EVALUATION_INSTANT_AFFECTS_TIME_BOUND_ADMISSION=true, not
    # AUTHORITY_EVALUATION_INSTANT_IS_INERT.
    assert before_window["authority_decision_id"] != within_window_a["authority_decision_id"]
    assert after_window["authority_decision_id"] != within_window_a["authority_decision_id"]


def test_p8r1f4_reflow_instant_fails_the_route_closed(tmp_path: Path) -> None:
    """INPUT_CLASS=REFLOW_INSTANT, MUTATED_FIELD=reflow_instant. FAIL_CLOSED_OR_REDERIVED=
    fails closed -- by P8-R1-F5's own new provenance check (``reflow_instant`` may never
    precede the Closure Evaluation's own ``evaluated_at``), re-asserted here for this
    matrix's own completeness rather than only in the F5-specific test file."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs["reflow_instant"] = "2020-01-01T00:00:00Z"
    with pytest.raises(ReflowError, match="precedes"):
        reflow(assembly["store"], **kwargs)
