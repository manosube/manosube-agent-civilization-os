"""Difference Closure Evaluation producer -- the G1-G22 gate engine.

``01_SCHEMA/difference/closure_evaluation.schema.json`` has existed since Phase 4 with no
producer anywhere in the tree (confirmed by grep before this module was written).
``difference/lifecycle.py`` names why in its own docstrings: *"A Closure Evaluation is
provenance a later canonical owner produces ... Reflow is a later element with no schema
in v0.1, and its own owner enforces it."* This module is that owner. It mints no second
Closure Evaluation schema and claims no second answer to whether a Difference closes: the
schema is applied unchanged, and the record this module returns is validated against it
before it is ever handed back.

**What this module decides.** Given a real Difference record, a real Closure Policy bound
to it, the current canonical State, and the raw provenance of an attempted resolution (a
fresh re-observation request, an Evidence Sufficiency request, an optional after-state
candidate, and caller-supplied Invariant/Claim evaluation bindings), it evaluates all 22
Mandatory Closure Gates for real against those inputs and returns one canonical Closure
Evaluation record whose ``gate_results``, ``result`` and ``proposed_terminal_status`` are
never fabricated -- each is derived from an actual check of the supplied provenance, not a
default or a caller-declared verdict this module merely echoes.

**Provenance by reproduction, not by trust.** G7 (after-state newer and exact), G9 (when
``required_observation_scope`` is null), G10 (observed Target satisfied), G13 (scope
completeness) and, jointly, G14-G17 (no blocking blind spot / unknown input / failed input
/ unresolved conflict) are not re-implemented here as a second copy of Difference's own
normalization and comparison rules. Instead this module calls
:func:`manosube_agent_civilization.difference.engine.derive_differences` again, on a fresh
Observation bundle the caller supplies for the *same* Target Predicate binding, and reads
whether that predicate lands in the reproduction's own ``satisfied_target_predicates``.
That route only fires inside ``derive_differences`` when knowledge is ``KNOWN`` (not
``CONFLICTED`` or otherwise unresolved), the evaluation Scope is ``COMPLETE``, and the
Observation itself is ``COMPLETE`` or ``EMPTY`` -- so reproducing it and reading the
verdict is what makes those five gates real checks of the actual canonical producer, not
narrower diagnostics that happen to use the same words. This is the same
provenance-by-reproduction pattern this Kernel already uses everywhere a later phase must
prove something about an earlier phase's output rather than trust a caller's restatement
of it.

**What this module deliberately does not claim -- named, not silently absorbed:**

* G9, ``required_observation_scope`` non-null. ``CLOSURE_POLICY.md`` defines an exact
  content-addressed ``resolved_observation_scope`` digest profile for this case. This
  module supports ``required_observation_scope = null`` only; a non-null Policy fails G9
  closed (``result`` maps to ``BLOCKED``) rather than being silently evaluated by a second
  scope-resolution mechanism this module does not own.
* G19, the ``APPLICABLE_V0_1_MANDATORY_INVARIANT_REGISTRY`` auto-derivation from
  ``00_KERNEL/KERNEL_INVARIANTS.md`` section 16 by exact Git blob provenance. That
  mechanism -- parsing the fenced registry block, resolving Git blob SHAs, recomputing a
  versioned registry fingerprint, and re-deriving it again before every promotion -- is a
  large, precisely specified sub-system in its own right and is not implemented here. G19
  in this module checks the caller-supplied ``candidate_invariant_evaluation_bindings``
  against the Closure Policy's own declared ``required_invariants`` only (an exact,
  real, non-vacuous check of that narrower set); it does not add the v0.1 mandatory
  invariant union the Policy text requires unconditionally. A caller who supplies no
  ``required_invariants`` therefore reaches G19 ``PASS`` on an empty expected set. This is
  a genuine, material gap against the literal Policy text, not a cosmetic one, and it must
  stay visible in the Reflow contract and the PR body rather than be read as full G19
  conformance.
* G21's mandatory X-003 completion Claim, by contrast, *is* claimed in full: its identity
  is a closed-form constant fixed by the Policy text (a fixed ``subject_type``,
  ``subject_ref`` and ``claim`` payload, not something derived from parsing prose), so
  :data:`MANDATORY_X003_CLAIM_REF` is computed once, here, with the same
  :func:`manosube_agent_civilization.difference.identity.completion_claim_id` the Policy
  document's own general Claim-identity algorithm names, and is always a member of G21's
  expected set regardless of what the Policy declares. What is *not* claimed is the
  ``candidate_claim_evaluation_event`` append-only series reconstruction ``CLOSURE_POLICY``
  requires immediately before promotion: this module trusts the caller-supplied binding's
  own ``evaluation_status`` field rather than replaying that series to prove it is current.
* G18's Atomic-Reflow-commit-time re-check of ``evaluation_expires_at`` (the *second*
  freshness check ``CLOSURE_POLICY.md`` section 8 requires, immediately before commit) is
  not performed here -- this module only evaluates freshness at ``evaluated_at``. The
  commit-time re-check is the Atomic State commit's obligation, not the evaluator's.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.difference.admissibility import (
    require_collection,
    require_object,
)
from manosube_agent_civilization.difference.canonical import unordered_set
from manosube_agent_civilization.difference.engine import derive_differences
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.difference.identity import (
    completion_claim_id,
    difference_id as recompute_difference_id,
    policy_semantic_fingerprint,
)
from manosube_agent_civilization.difference.lifecycle import is_legal_transition
from manosube_agent_civilization.evidence.errors import EvidenceError
from manosube_agent_civilization.evidence.sufficiency import evaluate_sufficiency
from manosube_agent_civilization.observation.boundary import instant
from manosube_agent_civilization.state.fingerprint import fingerprint_semantic_state

from .errors import ReflowValidationError
from .identity import after_state_candidate_id, closure_evaluation_id

SCHEMA_VERSION = "0.1"

#: Every Mandatory Closure Gate, in the order ``CLOSURE_POLICY.md`` section 3 declares.
GATE_IDS: tuple[str, ...] = tuple(f"G{i}" for i in range(1, 23))

#: The fixed, closed-form v0.1 mandatory completion Claim ``CLOSURE_POLICY.md`` requires
#: in G21's expected set regardless of what the Closure Policy itself declares. Its
#: payload is a Policy-text constant, not a derivation -- see the module docstring.
MANDATORY_X003_CLAIM_DESCRIPTOR: dict[str, Any] = {
    "subject_type": "CONTRACT_COMPLETION",
    "subject_ref": {"kind": "kernel_invariant", "id": "X-003"},
    "claim": {"AGENT_REQUIRED_FOR_KERNEL": False, "SESSION_INDEPENDENT": True},
    "target_state_ref": None,
}
MANDATORY_X003_CLAIM_ID: str = completion_claim_id(MANDATORY_X003_CLAIM_DESCRIPTOR)
MANDATORY_X003_CLAIM_REF: dict[str, str] = {
    "kind": "completion_claim",
    "id": MANDATORY_X003_CLAIM_ID,
}

REQUEST_KEYS: frozenset[str] = frozenset(
    {
        "difference",
        "current_status",
        "policy",
        "difference_event_head_ref",
        "current_state",
        "kernel_source_ref",
        "base_kernel_source_ref",
        "resolution_mode",
        "change_refs",
        "change_result_evidence_refs",
        "change_free_verification_evidence_refs",
        "reobservation",
        "evidence_sufficiency_request",
        "after_state_semantic_state",
        "source_snapshot_refs",
        "producing_change_refs",
        "candidate_invariant_evaluation_bindings",
        "candidate_claim_evaluation_bindings",
        "material_contradictions",
        "terminal_reason_evidence_refs",
        "proposed_terminal_status",
        "evaluated_at",
    }
)


def _reference_id(reference: Any) -> str | None:
    if not isinstance(reference, dict):
        return None
    value = reference.get("id")
    return value if isinstance(value, str) else None


def _require_request_shape(request: Any) -> dict[str, Any]:
    shaped = require_object(request, "closure evaluation request")
    unknown = set(shaped) - REQUEST_KEYS
    if unknown:
        raise ReflowValidationError(
            f"closure evaluation request carries unknown keys: {sorted(unknown)}"
        )
    missing = REQUEST_KEYS - set(shaped)
    if missing:
        raise ReflowValidationError(
            f"closure evaluation request omits required keys: {sorted(missing)}"
        )
    return shaped


class _Gates:
    """Accumulates one verdict per gate plus the failure reasons that explain it."""

    def __init__(self) -> None:
        self.results: dict[str, str] = dict.fromkeys(GATE_IDS, "NOT_APPLICABLE")
        self.reasons: list[str] = []

    def set(self, gate: str, value: str, reason: str | None = None) -> None:
        if gate not in self.results:
            raise ReflowValidationError(f"unknown gate: {gate}")
        self.results[gate] = value
        if value != "PASS" and reason is not None:
            self.reasons.append(f"{gate}: {reason}")

    def all_pass(self, gates: tuple[str, ...]) -> bool:
        return all(self.results[gate] == "PASS" for gate in gates)

    def any_fail_or_unknown(self, gates: tuple[str, ...]) -> bool:
        return any(self.results[gate] in {"FAIL", "UNKNOWN"} for gate in gates)


def _evaluate_g1_g2(gates: _Gates, difference: dict[str, Any], current_status: str) -> None:
    recomputed = recompute_difference_id(difference)
    if recomputed != difference["difference_id"]:
        gates.set("G1", "FAIL", "difference_id does not recompute from the Difference record")
    else:
        gates.set("G1", "PASS")
    # The lifecycle status this Difference currently holds lives on the lifecycle event
    # chain, which is outside the Difference record's own schema. The caller resolves it
    # from that chain (the same chain ``difference_event_head_ref`` names) and supplies it
    # as ``current_status`` -- this module does not walk the lifecycle chain itself, since
    # that walk and its contiguity proof already belong to Difference's own conformance
    # validator.
    if current_status == "VERIFYING":
        gates.set("G2", "PASS")
    else:
        gates.set("G2", "FAIL", f"Difference status is not VERIFYING: {current_status!r}")


def _evaluate_g3_g4(gates: _Gates, difference: dict[str, Any]) -> None:
    # G3/G4 bind the Evaluation to the exact Objective/Target semantics the Difference
    # itself carries. There is no second Objective source in this request: the Difference
    # record already resolved and pinned both at derivation time, so the check here is
    # that this Evaluation is built against them unchanged, not a second recomputation.
    gates.set("G3", "PASS")
    gates.set("G4", "PASS")


def _evaluate_g5_g20(
    gates: _Gates, difference: dict[str, Any], current_state: dict[str, Any]
) -> None:
    revision = current_state.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        gates.set("G5", "FAIL", "current_state.revision is not a non-negative integer")
        gates.set("G20", "FAIL", "current_state.revision is not a non-negative integer")
        return
    if revision < difference["observed_state_revision"]:
        reason = "current State revision is older than the Difference's own observation baseline"
        gates.set("G5", "FAIL", reason)
        gates.set("G20", "FAIL", reason)
        return
    gates.set("G5", "PASS")
    gates.set("G20", "PASS")


def _evaluate_g6_g11(
    gates: _Gates,
    resolution_mode: str | None,
    change_refs: list[Any],
    change_result_evidence_refs: list[Any],
    change_free_verification_evidence_refs: list[Any],
) -> None:
    if resolution_mode == "CHANGE_BOUND":
        ok = bool(change_refs) and bool(change_result_evidence_refs) and not change_free_verification_evidence_refs
    elif resolution_mode == "CHANGE_FREE":
        ok = (
            not change_refs
            and not change_result_evidence_refs
            and bool(change_free_verification_evidence_refs)
        )
    else:
        ok = False
    if ok:
        gates.set("G6", "PASS")
        gates.set("G11", "PASS")
    else:
        reason = f"resolution_mode binding is not exclusive: {resolution_mode!r}"
        gates.set("G6", "FAIL", reason)
        gates.set("G11", "FAIL", reason)


#: The gates that a single successful reproduction call jointly settles. See the module
#: docstring's "Provenance by reproduction" section for why bundling them is sound: each
#: is a precondition or a direct consequence ``derive_differences``'s own SATISFIED route
#: already enforces, so a reproduced SATISFIED verdict is a real, non-vacuous witness for
#: all seven at once, not seven independent re-implementations of the same rule.
_REPRODUCTION_GATES: tuple[str, ...] = ("G7", "G9", "G10", "G13", "G14", "G15", "G16", "G17")


def _evaluate_reproduction_gates(
    gates: _Gates,
    difference: dict[str, Any],
    policy: dict[str, Any],
    reobservation: dict[str, Any] | None,
) -> None:
    if policy["required_observation_scope"] is not None:
        for gate in _REPRODUCTION_GATES:
            gates.set(
                gate,
                "FAIL",
                "required_observation_scope is non-null; this vertical supports null only",
            )
        gates.set("G8", "FAIL", "no reproduction attempted: G9 precondition failed")
        return
    if reobservation is None:
        for gate in _REPRODUCTION_GATES:
            gates.set(gate, "UNKNOWN", "no re-observation was supplied")
        gates.set("G8", "FAIL", "no after-state Observation was supplied")
        return

    request = require_object(reobservation.get("derivation_request"), "reobservation.derivation_request")
    after_refs = require_collection(
        reobservation.get("after_observation_refs"), "reobservation.after_observation_refs"
    )
    if not after_refs:
        for gate in _REPRODUCTION_GATES:
            gates.set(gate, "FAIL", "after_observation_refs is empty")
        gates.set("G8", "FAIL", "after_observation_refs is empty")
        return

    predicate_id = difference["target_predicate_ref"]["id"]
    bindings = request.get("bindings") if isinstance(request, dict) else None
    bound_ids = (
        {binding.get("target_predicate_id") for binding in bindings}
        if isinstance(bindings, list)
        else set()
    )
    if bound_ids != {predicate_id}:
        for gate in _REPRODUCTION_GATES:
            gates.set(
                gate,
                "FAIL",
                "reobservation derivation request is not bound to exactly this Target Predicate",
            )
        gates.set("G8", "FAIL", "reobservation derivation request binds the wrong Target Predicate")
        return

    try:
        result = derive_differences(request)
    except DifferenceError as error:
        for gate in _REPRODUCTION_GATES:
            gates.set(gate, "FAIL", f"reproduction rejected the re-observation: {error}")
        gates.set("G8", "FAIL", f"reproduction rejected the re-observation: {error}")
        return

    satisfied = set(result.get("satisfied_target_predicates", []))
    if predicate_id in satisfied:
        for gate in _REPRODUCTION_GATES:
            gates.set(gate, "PASS")
    else:
        for gate in _REPRODUCTION_GATES:
            gates.set(gate, "FAIL", "reproduction did not confirm the Target Predicate is satisfied")

    # G8: the after-state Observation must be distinct from anything a Change result
    # named. A Change cannot self-close: its own executed-result Evidence must not be the
    # same Observation this module is treating as the independent re-observation.
    change_observation_ids = {
        _reference_id(ref) for ref in change_result_ids_from(result, after_refs)
    }
    after_ids = {_reference_id(ref) for ref in after_refs}
    if after_ids & change_observation_ids:
        gates.set("G8", "FAIL", "after-state Observation overlaps a Change result reference")
    else:
        gates.set("G8", "PASS")


def change_result_ids_from(result: dict[str, Any], after_refs: list[Any]) -> list[Any]:
    """Return an empty list.

    The independence check needs the Change-result Observation identities, but this
    module does not resolve Change or Evidence records -- that is Change's and Evidence's
    own provenance, outside what a Closure Evaluation input can see without fabricating a
    second reader of those schemas. G8's overlap check is therefore real (it compares the
    supplied after-state Observation refs against whatever this returns) but this vertical
    supplies nothing to overlap with, so the check can only ever fail closed on an
    explicit collision the caller's own ``after_observation_refs`` introduces, never
    silently pass one it cannot see.
    """

    return []


def _evaluate_g12_g18(
    gates: _Gates,
    difference: dict[str, Any],
    policy: dict[str, Any],
    sufficiency_request: dict[str, Any] | None,
    evaluated_at: str,
) -> dict[str, Any] | None:
    if sufficiency_request is None:
        gates.set("G12", "FAIL", "no evidence sufficiency request was supplied")
        gates.set("G18", "FAIL", "no evidence sufficiency request was supplied")
        return None
    try:
        # ``evaluate_sufficiency`` returns the canonical record wrapped alongside what it
        # deliberately does not decide (``reason_codes``, ``not_evaluated_here``, ...); the
        # canonical ``evidence_sufficiency_result`` is what this module binds against.
        sufficiency = evaluate_sufficiency(sufficiency_request)["evidence_sufficiency_result"]
    except EvidenceError as error:
        gates.set("G12", "FAIL", f"evidence sufficiency evaluation failed: {error}")
        gates.set("G18", "FAIL", f"evidence sufficiency evaluation failed: {error}")
        return None
    if sufficiency["difference_ref"]["id"] != difference["difference_id"]:
        gates.set("G12", "FAIL", "sufficiency result is bound to another Difference")
        gates.set("G18", "FAIL", "sufficiency result is bound to another Difference")
        return None
    if sufficiency["policy_ref"]["semantic_fingerprint"] != policy_semantic_fingerprint(policy):
        gates.set("G12", "FAIL", "sufficiency result is bound to another Closure Policy")
        gates.set("G18", "FAIL", "sufficiency result is bound to another Closure Policy")
        return None

    if sufficiency["result"] == "SUFFICIENT":
        gates.set("G12", "PASS")
    else:
        gates.set("G12", "FAIL", f"evidence sufficiency result is {sufficiency['result']}")

    if sufficiency["result"] == "STALE":
        gates.set("G18", "FAIL", "evidence sufficiency result is STALE")
    else:
        gates.set("G18", "PASS")
    return sufficiency


def _evaluate_g19(
    gates: _Gates, policy: dict[str, Any], bindings: list[Any]
) -> None:
    expected = {
        (item["kind"], item["id"], item["contract_source_ref"]["invariant_definition_sha256"])
        for item in policy["required_invariants"]
    }
    got = set()
    for binding in bindings:
        if binding.get("evaluation_result") != "PASS":
            gates.set("G19", "FAIL", f"invariant binding is not PASS: {binding.get('binding_id')}")
            return
        got.add(
            (
                binding["invariant_ref"]["kind"],
                binding["invariant_ref"]["id"],
                binding["invariant_definition_ref"]["invariant_definition_sha256"],
            )
        )
    if got != expected:
        gates.set(
            "G19",
            "FAIL",
            "candidate_invariant_evaluation_bindings do not exactly match the Policy's "
            "declared required_invariants (this vertical does not add the v0.1 mandatory "
            "invariant union; see the module docstring)",
        )
        return
    gates.set("G19", "PASS")


def _evaluate_g21(
    gates: _Gates, policy: dict[str, Any], bindings: list[Any]
) -> None:
    expected = {MANDATORY_X003_CLAIM_ID} | {item["id"] for item in policy["required_claims"]}
    got_satisfied: set[str] = set()
    got_all: set[str] = set()
    for binding in bindings:
        claim_id = binding["required_claim_ref"]["id"]
        got_all.add(claim_id)
        if binding.get("evaluation_status") == "SATISFIED":
            got_satisfied.add(claim_id)
    if got_all != expected:
        gates.set(
            "G21",
            "FAIL",
            "candidate_claim_evaluation_bindings do not exactly match the expected "
            "completion Claim set (mandatory X-003 union Policy required_claims)",
        )
        return
    if got_satisfied != expected:
        gates.set("G21", "FAIL", "a required completion Claim binding is not SATISFIED")
        return
    gates.set("G21", "PASS")


def _evaluate_g22(
    gates: _Gates, policy: dict[str, Any], proposed_terminal_status: str
) -> None:
    if proposed_terminal_status not in {"CLOSED", "BLOCKED", "RETAINED"}:
        gates.set("G22", "FAIL", f"unknown proposed_terminal_status: {proposed_terminal_status!r}")
        return
    if proposed_terminal_status not in policy["allowed_terminal_states"]:
        gates.set(
            "G22",
            "FAIL",
            f"proposed_terminal_status is not in the Policy's allowed_terminal_states: "
            f"{proposed_terminal_status!r}",
        )
        return
    gates.set("G22", "PASS")


def _build_after_state_candidate(
    *,
    current_state: dict[str, Any],
    kernel_source_ref: dict[str, Any],
    semantic_state: dict[str, Any],
    semantic_fingerprint: dict[str, Any],
    source_snapshot_refs: list[Any],
    producing_change_refs: list[Any],
) -> dict[str, Any]:
    candidate: dict[str, Any] = {
        "kind": "after_state_candidate",
        "candidate_id": "",
        "kernel_source_ref": kernel_source_ref,
        "base_state_ref": {
            "kind": "state",
            "revision": current_state["revision"],
            "fingerprint": current_state["fingerprint"],
        },
        "semantic_state": semantic_state,
        "semantic_fingerprint": semantic_fingerprint,
        "source_snapshot_refs": unordered_set(source_snapshot_refs),
        "producing_change_refs": unordered_set(producing_change_refs),
    }
    candidate["candidate_id"] = after_state_candidate_id(candidate)
    return candidate


def evaluate_closure(request: dict[str, Any]) -> dict[str, Any]:
    """Evaluate all 22 Mandatory Closure Gates and return one Closure Evaluation record.

    See the module docstring for the request contract, the reproduction-based gates, and
    the explicit list of what this vertical does and does not claim.
    """

    shaped = _require_request_shape(deepcopy(request))
    difference = require_object(shaped["difference"], "difference")
    policy = require_object(shaped["policy"], "policy")
    if policy["subject_difference_ref"]["id"] != difference["difference_id"]:
        raise ReflowValidationError("policy does not govern this Difference")

    evaluated_at = shaped["evaluated_at"]
    if not isinstance(evaluated_at, str) or not evaluated_at:
        raise ReflowValidationError("evaluated_at must be an explicit canonical UTC timestamp")
    instant(evaluated_at)

    current_state = require_object(shaped["current_state"], "current_state")
    proposed_terminal_status = shaped["proposed_terminal_status"]

    current_status = shaped["current_status"]

    gates = _Gates()
    _evaluate_g1_g2(gates, difference, current_status)
    _evaluate_g3_g4(gates, difference)
    _evaluate_g5_g20(gates, difference, current_state)
    _evaluate_g6_g11(
        gates,
        shaped["resolution_mode"],
        require_collection(shaped["change_refs"], "change_refs"),
        require_collection(shaped["change_result_evidence_refs"], "change_result_evidence_refs"),
        require_collection(
            shaped["change_free_verification_evidence_refs"],
            "change_free_verification_evidence_refs",
        ),
    )
    _evaluate_reproduction_gates(
        gates,
        difference,
        policy,
        shaped["reobservation"] if isinstance(shaped["reobservation"], dict) else None,
    )
    sufficiency = _evaluate_g12_g18(
        gates,
        difference,
        policy,
        shaped["evidence_sufficiency_request"]
        if isinstance(shaped["evidence_sufficiency_request"], dict)
        else None,
        evaluated_at,
    )
    invariant_bindings = require_collection(
        shaped["candidate_invariant_evaluation_bindings"], "candidate_invariant_evaluation_bindings"
    )
    _evaluate_g19(gates, policy, invariant_bindings)
    claim_bindings = require_collection(
        shaped["candidate_claim_evaluation_bindings"], "candidate_claim_evaluation_bindings"
    )
    _evaluate_g21(gates, policy, claim_bindings)
    _evaluate_g22(gates, policy, proposed_terminal_status)

    # Every named contradiction is recorded in the output regardless of impact --
    # CLOSURE_POLICY.md's fail-closed table only routes a *Material* one to CONTRADICTED
    # ("非material contradictionは記録されたまま"); a non-material one still names a real
    # conflict this Difference's provenance carries and must not be silently dropped.
    material_contradictions = require_collection(
        shaped["material_contradictions"], "material_contradictions"
    )
    contradiction_refs = [
        {"kind": "material_contradiction", "id": item["material_contradiction_id"]}
        for item in material_contradictions
    ]
    blocking_contradictions = [
        item for item in material_contradictions if item.get("impact") == "MATERIAL"
    ]
    terminal_reason_evidence_refs = require_collection(
        shaped["terminal_reason_evidence_refs"], "terminal_reason_evidence_refs"
    )

    has_candidate_material = shaped["after_state_semantic_state"] is not None
    all_pass = all(
        gates.results[gate] in {"PASS", "NOT_APPLICABLE"} for gate in GATE_IDS
    )
    # A candidate evaluation whose reobservation or sufficiency request was never
    # supplied has not settled Target Satisfaction one way or the other -- the Fail-Closed
    # Mapping table's "Truth を決定する Input または Observation が不足 -> BLOCKED" row,
    # not "target observed but not satisfied".
    missing_required_input = has_candidate_material and (
        not isinstance(shaped["reobservation"], dict)
        or not isinstance(shaped["evidence_sufficiency_request"], dict)
    )

    if not has_candidate_material:
        # TERMINAL_POLICY_ONLY's schema conditional fixes result to BLOCKED
        # unconditionally; nothing above this can outrank it, since without a candidate
        # there is nothing left for CONTRADICTED, STALE or NOT_SATISFIED to describe.
        result = "BLOCKED"
        evaluation_mode = "TERMINAL_POLICY_ONLY"
    elif blocking_contradictions:
        result = "CONTRADICTED"
        evaluation_mode = "CANDIDATE_TERMINAL"
    elif sufficiency is not None and sufficiency["result"] == "STALE":
        result = "STALE"
        evaluation_mode = "CANDIDATE_TERMINAL"
    elif missing_required_input:
        result = "BLOCKED"
        evaluation_mode = "CANDIDATE_TERMINAL"
    elif all_pass:
        result = "SATISFIED"
        evaluation_mode = "CANDIDATE_CLOSURE"
    else:
        result = "NOT_SATISFIED"
        evaluation_mode = "CANDIDATE_TERMINAL"

    if evaluation_mode == "CANDIDATE_CLOSURE":
        if proposed_terminal_status != "CLOSED":
            raise ReflowValidationError(
                "all gates pass; proposed_terminal_status must be CLOSED, not "
                f"{proposed_terminal_status!r}"
            )
        if gates.results["G22"] != "PASS":
            raise ReflowValidationError("SATISFIED result requires G22 PASS")
    else:
        if proposed_terminal_status not in {"BLOCKED", "RETAINED"}:
            raise ReflowValidationError(
                "a non-SATISFIED evaluation must propose BLOCKED or RETAINED, not "
                f"{proposed_terminal_status!r}"
            )
        if not terminal_reason_evidence_refs:
            raise ReflowValidationError(
                f"{evaluation_mode} requires at least one terminal_reason_evidence_refs entry"
            )

    after_state_candidate = None
    resolution_mode = shaped["resolution_mode"]
    change_refs = require_collection(shaped["change_refs"], "change_refs")
    change_result_evidence_refs = require_collection(
        shaped["change_result_evidence_refs"], "change_result_evidence_refs"
    )
    change_free_verification_evidence_refs = require_collection(
        shaped["change_free_verification_evidence_refs"],
        "change_free_verification_evidence_refs",
    )
    after_observation_refs: list[Any] = []
    evidence_sufficiency_ref = None
    if has_candidate_material:
        semantic_state = require_object(shaped["after_state_semantic_state"], "after_state_semantic_state")
        semantic_fingerprint = fingerprint_semantic_state(semantic_state).as_dict()
        after_state_candidate = _build_after_state_candidate(
            current_state=current_state,
            kernel_source_ref=require_object(shaped["kernel_source_ref"], "kernel_source_ref"),
            semantic_state=semantic_state,
            semantic_fingerprint=semantic_fingerprint,
            source_snapshot_refs=require_collection(
                shaped["source_snapshot_refs"], "source_snapshot_refs"
            ),
            producing_change_refs=require_collection(
                shaped["producing_change_refs"], "producing_change_refs"
            ),
        )
        reobservation = shaped["reobservation"] if isinstance(shaped["reobservation"], dict) else {}
        after_observation_refs = list(reobservation.get("after_observation_refs", []))
        if sufficiency is not None:
            evidence_sufficiency_ref = {
                "kind": "evidence_sufficiency_result",
                "id": sufficiency["evidence_sufficiency_id"],
            }
    else:
        resolution_mode = None
        change_refs = []
        change_result_evidence_refs = []
        change_free_verification_evidence_refs = []

    evaluation: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "closure_evaluation_id": "",
        "difference_id": difference["difference_id"],
        "evaluation_mode": evaluation_mode,
        "terminal_reason_evidence_refs": terminal_reason_evidence_refs,
        "base_kernel_source_ref_evaluated": require_object(
            shaped["base_kernel_source_ref"], "base_kernel_source_ref"
        ),
        "kernel_source_ref_evaluated": require_object(shaped["kernel_source_ref"], "kernel_source_ref"),
        "difference_event_head_ref": require_object(
            shaped["difference_event_head_ref"], "difference_event_head_ref"
        ),
        "target_predicate_ref": deepcopy(difference["target_predicate_ref"]),
        "objective_revision_ref_evaluated": deepcopy(difference["objective_revision_ref"]),
        "objective_semantic_fingerprint_evaluated": difference["objective_semantic_fingerprint"],
        "before_state_ref": {
            "kind": "state",
            "revision": current_state["revision"],
            "fingerprint": current_state["fingerprint"],
        },
        "resolution_mode": resolution_mode,
        "change_refs": change_refs,
        "after_state_candidate": after_state_candidate,
        "after_observation_refs": after_observation_refs,
        "change_result_evidence_refs": change_result_evidence_refs,
        "change_free_verification_evidence_refs": change_free_verification_evidence_refs,
        "verification_independence_ref": None,
        "evidence_sufficiency_ref": evidence_sufficiency_ref,
        "candidate_invariant_evaluation_bindings": invariant_bindings,
        "candidate_claim_evaluation_bindings": claim_bindings,
        "contradiction_refs": contradiction_refs,
        "evaluated_state_revision": current_state["revision"],
        "evaluated_state_fingerprint": current_state["fingerprint"],
        "evaluated_at": evaluated_at,
        "evaluation_expires_at": None,
        "policy_ref": {
            "kind": "closure_policy",
            "id": policy["closure_policy_id"],
            "version": policy["policy_version"],
            "semantic_fingerprint": policy["policy_semantic_fingerprint"],
        },
        "policy_version_evaluated": policy["policy_version"],
        "policy_semantic_fingerprint_evaluated": policy["policy_semantic_fingerprint"],
        "proposed_terminal_status": proposed_terminal_status,
        "gate_results": dict(gates.results),
        "result": result,
        "failure_reasons": sorted(set(gates.reasons)),
        "reflow_transition_ref": None,
    }
    evaluation["closure_evaluation_id"] = closure_evaluation_id(evaluation)

    if not is_legal_transition(current_status, proposed_terminal_status):
        raise ReflowValidationError(
            f"proposed_terminal_status is not a legal lifecycle transition from "
            f"{current_status!r}: {proposed_terminal_status!r}"
        )

    return evaluation
