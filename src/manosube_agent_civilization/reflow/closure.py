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
* G19's live Git commit/tree provenance binding -- resolving
  ``APPLICABLE_V0_1_MANDATORY_INVARIANTS`` against the exact
  ``kernel_source_ref_evaluated.commit_sha``/``tree_sha`` a candidate was actually evaluated
  against, by reading an arbitrary commit's tree at evaluation time -- is not implemented
  here, for the same "engine reads no filesystem/live Git" reason named throughout this
  vertical. What *is* claimed in full, via :mod:`.invariant_registry` (R2-G19): the parsed
  v0.1 mandatory Invariant **id** union (every ``ID`` the ``# 16. v0.1 Mandatory Gate``
  fenced block declares, minus the one Policy-excluded post-Reflow id P-003), *and* each
  mandatory id's own per-invariant ``invariant_definition_sha256`` -- recomputed from its
  own ``## <ID> — <NAME>`` definition block in ``KERNEL_INVARIANTS.md`` sections 4-15, by
  the same normalize-then-SHA-256 profile section 16's own digest already uses -- both
  pinned and drift-tested against the live document the same way
  :mod:`manosube_agent_civilization.evidence.levels` pins the Evidence Level scale. G19's
  expected set is this full ``(kind, id, invariant_definition_sha256)`` union, additively
  merged with whatever Policy ``required_invariants`` also declares, so an empty Policy set
  can no longer reach G19 ``PASS`` vacuously, and a fabricated digest on a mandatory-id
  binding no longer passes by mere presence. A Policy that separately (and redundantly)
  names a mandatory id with a *conflicting* digest is a same-ID definition conflict and
  fails G19 closed rather than silently picking a side. The un-implemented Git-provenance
  sub-system named above is the only remaining gap: this module cannot prove a binding's
  digest was computed against the *specific* commit/tree ``kernel_source_ref_evaluated``
  names, only that it equals the one pinned, currently-deployed registry's own digest.
  A binding's own ``binding_id`` is verified against its content-addressed derivation too
  (:func:`.invariant_registry.candidate_invariant_evaluation_binding_id` --
  ``MANOSUBE-CANDIDATE-EVALUATION-BINDING-SHA256-0.1``): a caller cannot reuse or fabricate
  a ``binding_id`` inconsistent with the binding's own closed fields. The registry's own
  identity fields (``registry_digest``/``registry_semantic_fingerprint``/``registry_id``)
  are exposed by :mod:`.invariant_registry` but have no field on
  ``candidate_invariant_evaluation_binding`` to bind against today, so G19 does not check
  a binding against them directly -- what it does check, the exact per-invariant definition
  digest, is the value the registry itself is built from.
* G21's mandatory X-003 completion Claim is claimed in full, as before: its identity is a
  closed-form constant fixed by the Policy text, computed once as
  :data:`MANDATORY_X003_CLAIM_REF`, and is always a member of G21's expected set regardless
  of what the Policy declares. G21 now also reconstructs the ``candidate_claim_evaluation_
  event`` append-only series :mod:`.claims` walks from each binding's declared head back to
  revision 0 -- the binding's own ``evaluation_status`` is never trusted directly; the
  reconstructed head event's status is.
* G18's Atomic-Reflow-commit-time re-check of ``evaluation_expires_at`` (the *second*
  freshness check ``CLOSURE_POLICY.md`` section 8 requires, immediately before commit) is
  not performed here -- this module only evaluates and derives freshness at
  ``evaluated_at``, from the oldest admitted Evidence instant and the Policy's
  ``maximum_evidence_age``. The commit-time re-check is
  :func:`~manosube_agent_civilization.reflow.commit.commit_reflow`'s obligation, not the
  evaluator's, and is implemented there.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from manosube_agent_civilization.difference.admissibility import (
    require_collection,
    require_object,
)
from manosube_agent_civilization.difference.canonical import unordered_set
from manosube_agent_civilization.difference.completion import (
    MANDATORY_X003_CLAIM_DESCRIPTOR as MANDATORY_X003_CLAIM_DESCRIPTOR,
    MANDATORY_X003_CLAIM_ID as MANDATORY_X003_CLAIM_ID,
    MANDATORY_X003_CLAIM_REF as MANDATORY_X003_CLAIM_REF,
    resolve_completion_record,
)
from manosube_agent_civilization.difference.conformance import validate_derivation_input
from manosube_agent_civilization.difference.engine import derive_differences
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.difference.identity import (
    difference_id as recompute_difference_id,
    objective_semantic_fingerprint,
    policy_semantic_fingerprint,
)
from manosube_agent_civilization.difference.invariant_evaluation import resolve_invariant_evaluation
from manosube_agent_civilization.difference.invariant_verifiers import (
    build_invariant_verification_context,
)
from manosube_agent_civilization.difference.lifecycle import is_legal_transition
from manosube_agent_civilization.evidence.engine import (
    derive_evidence,
    resolve_terminal_reason_evidence,
)
from manosube_agent_civilization.evidence.errors import EvidenceError
from manosube_agent_civilization.evidence.sufficiency import evaluate_sufficiency
from manosube_agent_civilization.observation.boundary import instant
from manosube_agent_civilization.observation.errors import ObservationError
from manosube_agent_civilization.observation.identity import observation_identity
from manosube_agent_civilization.observation.source_snapshot import resolve_source_snapshot
from manosube_agent_civilization.state.fingerprint import fingerprint_semantic_state

from .claims import resolve_claim_binding
from .errors import ReflowValidationError
from .git_witness import build_kernel_source_witness_record, verify_kernel_source_witness
from .identity import after_state_candidate_id, closure_evaluation_id
from .invariant_registry import (
    KERNEL_INVARIANTS_BLOB_SHA,
    KERNEL_INVARIANTS_PATH,
    candidate_invariant_evaluation_binding_id,
    expected_g19_invariant_entries,
)

SCHEMA_VERSION = "0.1"

#: Every Mandatory Closure Gate, in the order ``CLOSURE_POLICY.md`` section 3 declares.
GATE_IDS: tuple[str, ...] = tuple(f"G{i}" for i in range(1, 23))

#: ``MANDATORY_X003_CLAIM_DESCRIPTOR``/``_ID``/``_REF`` are re-exported here for backward
#: compatibility -- their canonical home is :mod:`manosube_agent_civilization.difference.
#: completion` (R4-F2: Completion-domain content is owned by Difference, not Reflow).

REQUEST_KEYS: frozenset[str] = frozenset(
    {
        "difference",
        "current_status",
        "policy",
        "difference_event_head_ref",
        "current_state",
        "objective_revision_id",
        "kernel_source_ref",
        "base_kernel_source_ref",
        "resolution_mode",
        "change_refs",
        "change_result_evidence_refs",
        "change_result_evidence_requests",
        "change_free_verification_evidence_refs",
        "change_free_verification_evidence_requests",
        "reobservation",
        "evidence_sufficiency_request",
        "after_state_semantic_state",
        "source_snapshot_refs",
        "source_snapshots",
        "producing_change_refs",
        "candidate_invariant_evaluation_bindings",
        "candidate_claim_evaluation_bindings",
        "candidate_claim_evaluation_events",
        "invariant_evaluations",
        "kernel_source_witness",
        "material_contradictions",
        "terminal_reason_evidence_refs",
        "terminal_reason_evidence_requests",
        "proposed_terminal_status",
        "evaluated_at",
    }
)


def _format_instant(value: datetime) -> str:
    """Return *value* as the canonical UTC instant string ``common/timestamp.schema.json``
    admits -- the same ``...isoformat().replace("+00:00", "Z")`` projection
    ``observation/normalization.py`` already uses, applied here because a derived
    ``evaluation_expires_at`` needs the same canonical round-trip a caller-supplied instant
    already gets for free.
    """

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


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


def _evaluate_g3_g4(
    gates: _Gates,
    difference: dict[str, Any],
    *,
    objective_revision_id: str,
    reobservation: dict[str, Any] | None,
    base_kernel_source_ref: dict[str, Any],
    kernel_source_ref: dict[str, Any],
    has_candidate_material: bool,
    kernel_source_witness_verified: bool,
) -> None:
    """R7-F3/R8-F2: G3 binds this Evaluation to the exact Objective the current State itself
    is bound to -- the committed State's own ``objective_revision_id`` (never a caller
    restatement of it) must exactly equal the Difference's own ``objective_revision_ref.id``.
    R8-F2 (SHUKOU Round 8, rejecting Round 7's own disclosed non-claim: "実requestに存在する
    bodyを使用してください") deepens this: the Reflow request's real, complete Objective
    Revision body -- ``reobservation.derivation_request.objective_revision``, the same input
    :func:`~manosube_agent_civilization.difference.engine.derive_differences` itself consumes
    for G8's reproduction -- is independently schema-validated
    (:func:`~manosube_agent_civilization.difference.conformance.validate_derivation_input`)
    and its semantic fingerprint recomputed
    (:func:`~manosube_agent_civilization.difference.identity.objective_semantic_fingerprint`)
    whenever that body is actually present, and bound to *both*
    ``difference["objective_revision_ref"]["id"]`` and
    ``difference["objective_semantic_fingerprint"]`` -- never merely the bare id-equality
    above, which by itself proves only that two strings match, not that either names a real,
    schema-valid Objective. A candidate evaluation with no reobservation at all (the
    ``TERMINAL_POLICY_ONLY``/``BLOCKED`` route, which never derives a candidate in the first
    place) has no such body to validate and is unaffected -- G3's id-equality floor is the
    only proof available or required there, unchanged from R7-F3.

    G4 binds this Evaluation to the exact Kernel source Phase 7 requires unchanged across
    the whole cycle: ``base_kernel_source_ref``/``kernel_source_ref`` must be the identical
    commit/tree (unconditional floor, R7-F3), and -- R8-F2 -- whenever a real Candidate
    exists, that identity must also have actually independently *verified* as a genuine Git
    object (:func:`~manosube_agent_civilization.reflow.git_witness.verify_kernel_source_witness`
    against the pinned ``KERNEL_INVARIANTS_BLOB_SHA``/``KERNEL_INVARIANTS_PATH``, the same
    proof G19 already computes for every binding) -- never bare caller-declared equality
    between two unverified strings alone. *kernel_source_witness_verified* is that real,
    already-computed result (never re-derived a second time here); the caller passes
    ``False`` whenever no witness was supplied or it failed to verify.

    Disclosed, not silently absorbed into a PASS (R8-F1's own SEMANTIC_DECISION_REQUIRED
    discipline, applied here): G4 does not additionally resolve ``base_kernel_source_ref``
    from the canonical base State's own persisted metadata/source snapshot, the deeper half
    SHUKOU's Round 8 adoption also names. No mechanism in this vertical persists "the Kernel
    source a given committed State was itself derived under" as a queryable fact for every
    State -- ``STATE_METADATA.md``/the ``project_state`` schema carry no such field, the
    genesis State never went through a Reflow cycle that could mint one, and even a
    Reflow-produced State's own ``kernel_source_witness`` record (R6-F4b) is minted only
    when that closing cycle happened to carry Invariant bindings, never unconditionally. This
    module (``reflow/closure.py``) is also, by design, a pure function of its own request --
    it holds no Store handle to resolve a historical transaction against even where one might
    exist (``reflow/route.py`` is the only layer with Store access, and does not currently
    resolve or override this field the way F2 already overrides ``current_state``). Closing
    this gap uniquely would mean either minting a new, unconditional Store-visible kernel
    source binding on every future committed State (an additive schema change this round's
    own scope boundary does not authorize inventing unilaterally) or accepting the caller's
    ``base_kernel_source_ref`` claim as the intended floor once its own commit/tree is
    independently witness-verified via the check above (already implemented). That choice is
    SHUKOU's to make, not this vertical's to guess -- named here rather than silently
    resolved.
    """

    if objective_revision_id != difference["objective_revision_ref"]["id"]:
        gates.set(
            "G3",
            "FAIL",
            "current State's objective_revision_id does not match the Difference's own "
            "objective_revision_ref",
        )
    elif reobservation is not None:
        derivation_request = (
            reobservation.get("derivation_request") if isinstance(reobservation, dict) else None
        )
        objective_body = (
            derivation_request.get("objective_revision")
            if isinstance(derivation_request, dict)
            else None
        )
        if not isinstance(objective_body, dict):
            gates.set(
                "G3",
                "FAIL",
                "reobservation.derivation_request carries no real objective_revision body to "
                "independently validate",
            )
        else:
            try:
                validate_derivation_input(objective_body, "objective_revision")
            except DifferenceError as error:
                gates.set("G3", "FAIL", f"objective_revision body is schema-invalid: {error}")
            else:
                if objective_body.get("objective_revision_id") != difference["objective_revision_ref"]["id"]:
                    gates.set(
                        "G3",
                        "FAIL",
                        "objective_revision body's own objective_revision_id does not match the "
                        "Difference's own objective_revision_ref",
                    )
                elif objective_semantic_fingerprint(objective_body) != difference["objective_semantic_fingerprint"]:
                    gates.set(
                        "G3",
                        "FAIL",
                        "objective_revision body's independently recomputed semantic fingerprint "
                        "does not match the Difference's own objective_semantic_fingerprint",
                    )
                else:
                    gates.set("G3", "PASS")
    else:
        gates.set("G3", "PASS")

    if base_kernel_source_ref.get("commit_sha") != kernel_source_ref.get(
        "commit_sha"
    ) or base_kernel_source_ref.get("tree_sha") != kernel_source_ref.get("tree_sha"):
        gates.set(
            "G4",
            "FAIL",
            "base_kernel_source_ref does not exactly match kernel_source_ref: Phase 7 does "
            "not permit a Kernel source change mid-cycle",
        )
    elif has_candidate_material and not kernel_source_witness_verified:
        gates.set(
            "G4",
            "FAIL",
            "kernel_source_witness did not independently verify against kernel_source_ref: a "
            "candidate evaluation cannot rely on bare caller-declared equality alone",
        )
    else:
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


def _derive_after_observation_ids(request: dict[str, Any]) -> set[str]:
    """R2-F4: the real after-state Observation identities the reobservation derivation
    request actually consumes -- recomputed from the Observation records themselves
    (:func:`~manosube_agent_civilization.observation.identity.observation_identity`), not
    read from any caller-declared list. A caller cannot declare an ``after_observation_refs``
    entry that names an Observation the reproduction did not actually derive from, and
    cannot omit one it did.
    """

    bindings = request.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        return set()
    bundle = bindings[0].get("observation_bundle") if isinstance(bindings[0], dict) else None
    observations = bundle.get("observations") if isinstance(bundle, dict) else None
    if not isinstance(observations, list):
        return set()
    ids: set[str] = set()
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        identity = observation.get("observation_id")
        if isinstance(identity, str) and identity and identity == observation_identity(observation):
            ids.add(identity)
    return ids


def _derive_source_snapshot_ids(request: dict[str, Any]) -> set[str]:
    """R4-F2: the real ``source_snapshot`` reference ids the reproduction's own
    self-consistent Observation(s) actually report -- Observation is these references'
    canonical owner, so a candidate's own declared ``source_snapshot_refs`` is verified by
    cross-reference against Observation's own already-validated set first, then (R6-F1a)
    each id is independently resolved against a real, content-addressed ``source_snapshot``
    body from the caller-supplied pool (see ``_evaluate_reproduction_gates``'s own call to
    :func:`~manosube_agent_civilization.observation.source_snapshot.resolve_source_snapshot`)
    -- ID-only cross-reference alone is no longer sufficient.
    """

    bindings = request.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        return set()
    bundle = bindings[0].get("observation_bundle") if isinstance(bindings[0], dict) else None
    observations = bundle.get("observations") if isinstance(bundle, dict) else None
    if not isinstance(observations, list):
        return set()
    ids: set[str] = set()
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        identity = observation.get("observation_id")
        if not (isinstance(identity, str) and identity and identity == observation_identity(observation)):
            continue
        for ref in observation.get("source_snapshot_refs") or []:
            ref_id = _reference_id(ref)
            if ref_id is not None:
                ids.add(ref_id)
    return ids


def _evaluate_reproduction_gates(
    gates: _Gates,
    difference: dict[str, Any],
    policy: dict[str, Any],
    reobservation: dict[str, Any] | None,
    resolution_mode: str | None,
    change_result_evidence_refs: list[Any],
    change_result_evidence_requests: list[Any],
    change_free_verification_evidence_refs: list[Any],
    change_free_verification_evidence_requests: list[Any],
    source_snapshot_refs: list[Any],
    source_snapshots: list[Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(change_result_evidence, change_free_evidence)`` -- the real Evidence
    records this call's own G8 branch reproduced through :func:`derive_evidence` (empty
    when the branch never reached a reproduction, or reproduced none). R7-F1: this is the
    same real, already-verified Evidence :func:`build_after_state_candidate`'s own
    invariant-verification context binds to, rather than a second, independent
    re-derivation of it.
    """

    if policy["required_observation_scope"] is not None:
        for gate in _REPRODUCTION_GATES:
            gates.set(
                gate,
                "FAIL",
                "required_observation_scope is non-null; this vertical supports null only",
            )
        gates.set("G8", "FAIL", "no reproduction attempted: G9 precondition failed")
        return [], []
    if reobservation is None:
        for gate in _REPRODUCTION_GATES:
            gates.set(gate, "UNKNOWN", "no re-observation was supplied")
        gates.set("G8", "FAIL", "no after-state Observation was supplied")
        return [], []

    request = require_object(reobservation.get("derivation_request"), "reobservation.derivation_request")
    after_refs = require_collection(
        reobservation.get("after_observation_refs"), "reobservation.after_observation_refs"
    )
    if not after_refs:
        for gate in _REPRODUCTION_GATES:
            gates.set(gate, "FAIL", "after_observation_refs is empty")
        gates.set("G8", "FAIL", "after_observation_refs is empty")
        return [], []

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
        return [], []

    # R2-F4: declared after_observation_refs must name exactly the Observation(s) the
    # reproduction request actually carries -- never a caller-chosen id substituted in
    # its place. A forged after_observation_refs entry can no longer sidestep G8's
    # overlap check by pointing somewhere the real bundle never derived from.
    derived_after_ids = _derive_after_observation_ids(request)
    declared_after_ids = {_reference_id(ref) for ref in after_refs}
    if declared_after_ids != derived_after_ids:
        for gate in _REPRODUCTION_GATES:
            gates.set(
                gate,
                "FAIL",
                "after_observation_refs does not exactly match the Observation(s) the "
                "reobservation derivation request actually consumed",
            )
        gates.set(
            "G8",
            "FAIL",
            "after_observation_refs does not exactly match the Observation(s) the "
            "reobservation derivation request actually consumed",
        )
        return [], []

    # R4-F2: a candidate's own source_snapshot_refs must exactly match the real,
    # self-consistent Observation's own reported set -- Observation is this reference
    # kind's canonical owner, so cross-referencing its already-validated data is this
    # vertical's actual resolution of it (see :func:`_derive_source_snapshot_ids`).
    derived_snapshot_ids = _derive_source_snapshot_ids(request)
    declared_snapshot_ids = {_reference_id(ref) for ref in source_snapshot_refs}
    if declared_snapshot_ids != derived_snapshot_ids:
        for gate in _REPRODUCTION_GATES:
            gates.set(
                gate,
                "FAIL",
                "source_snapshot_refs does not exactly match the real Observation's own "
                "reported source snapshots",
            )
        gates.set(
            "G8",
            "FAIL",
            "source_snapshot_refs does not exactly match the real Observation's own "
            "reported source snapshots",
        )
        return [], []

    # R6-F1a: ID-only cross-reference is no longer sufficient -- every declared
    # source_snapshot_refs entry must also resolve to a real, schema-valid, content-addressed
    # source_snapshot record (Observation's own producer, :mod:`observation.source_snapshot`)
    # in the caller-supplied pool, whose own identity independently recomputes. A caller who
    # names an id no real record backs, or supplies a record whose content does not actually
    # produce that id, fails closed here rather than being accepted on the bare string match.
    for ref in source_snapshot_refs:
        try:
            resolve_source_snapshot(ref, source_snapshots)
        except ObservationError as error:
            for gate in _REPRODUCTION_GATES:
                gates.set(gate, "FAIL", f"source_snapshot did not resolve: {error}")
            gates.set("G8", "FAIL", f"source_snapshot did not resolve: {error}")
            return [], []

    try:
        result = derive_differences(request)
    except DifferenceError as error:
        for gate in _REPRODUCTION_GATES:
            gates.set(gate, "FAIL", f"reproduction rejected the re-observation: {error}")
        gates.set("G8", "FAIL", f"reproduction rejected the re-observation: {error}")
        return [], []

    satisfied = set(result.get("satisfied_target_predicates", []))
    if predicate_id in satisfied:
        for gate in _REPRODUCTION_GATES:
            gates.set(gate, "PASS")
    else:
        for gate in _REPRODUCTION_GATES:
            gates.set(gate, "FAIL", "reproduction did not confirm the Target Predicate is satisfied")

    # G8: the after-state Observation must be distinct from anything a Change result
    # named. A Change cannot self-close: its own executed-result Evidence must not be the
    # same Observation this module is treating as the independent re-observation. F4:
    # the Change-result Evidence and its Observation identities are reproduced through
    # Evidence's own canonical owner (`derive_evidence`) from the raw requests the caller
    # supplies -- never trusted from the bare `change_result_evidence_refs` ids alone,
    # which a caller could otherwise point at anything, or at nothing.
    after_ids = {_reference_id(ref) for ref in after_refs}
    if resolution_mode == "CHANGE_BOUND":
        if not change_result_evidence_requests:
            gates.set(
                "G8",
                "FAIL",
                "CHANGE_BOUND resolution supplied no change_result_evidence_requests to "
                "reproduce the Change result Evidence from",
            )
            return [], []
        try:
            reproduced = [derive_evidence(item) for item in change_result_evidence_requests]
        except EvidenceError as error:
            gates.set("G8", "FAIL", f"change-result Evidence reproduction failed: {error}")
            return [], []
        reproduced_ids = {record["evidence_id"] for record in reproduced}
        declared_ids = {_reference_id(ref) for ref in change_result_evidence_refs}
        if reproduced_ids != declared_ids:
            gates.set(
                "G8",
                "FAIL",
                "change_result_evidence_refs does not exactly match the reproduced "
                "change-result Evidence (substitution, omission or duplication)",
            )
            return [], []
        change_observation_ids = {
            member["id"]
            for record in reproduced
            for member in record["lineage"]["derived_from"]["members"]
            if member["kind"] == "observation"
        }
        if after_ids & change_observation_ids:
            gates.set("G8", "FAIL", "after-state Observation overlaps a Change result reference")
        else:
            gates.set("G8", "PASS")
        return reproduced, []
    if resolution_mode == "CHANGE_FREE":
        if change_result_evidence_refs or change_result_evidence_requests:
            gates.set(
                "G8", "FAIL", "CHANGE_FREE resolution must not carry Change-result Evidence"
            )
            return [], []
        if not change_free_verification_evidence_requests:
            # R6-F1b: a bare change_free_verification_evidence_refs id, with no real
            # request to reproduce it from, is exactly the "実体のない参照" (a reference
            # without substance) SHUKOU's Round 6 adoption prohibits.
            gates.set(
                "G8",
                "FAIL",
                "CHANGE_FREE resolution supplied no change_free_verification_evidence_requests "
                "to reproduce the change-free verification Evidence from",
            )
            return [], []
        try:
            reproduced = [
                derive_evidence(item) for item in change_free_verification_evidence_requests
            ]
        except EvidenceError as error:
            gates.set(
                "G8", "FAIL", f"change-free verification Evidence reproduction failed: {error}"
            )
            return [], []
        reproduced_ids = {record["evidence_id"] for record in reproduced}
        declared_ids = {_reference_id(ref) for ref in change_free_verification_evidence_refs}
        if reproduced_ids != declared_ids:
            gates.set(
                "G8",
                "FAIL",
                "change_free_verification_evidence_refs does not exactly match the "
                "reproduced change-free verification Evidence (substitution, omission "
                "or duplication)",
            )
            return [], reproduced
        if any(
            record["evidence_position"] != "CHANGE_FREE_VERIFICATION_EVIDENCE"
            for record in reproduced
        ):
            gates.set(
                "G8",
                "FAIL",
                "a change_free_verification_evidence_requests entry did not reproduce "
                "as CHANGE_FREE_VERIFICATION_EVIDENCE",
            )
            return [], reproduced
        gates.set("G8", "PASS")
        return [], reproduced
    gates.set("G8", "FAIL", f"G8 requires a bound resolution_mode: {resolution_mode!r}")
    return [], []


def _evaluate_g12_g18(
    gates: _Gates,
    difference: dict[str, Any],
    policy: dict[str, Any],
    sufficiency_request: dict[str, Any] | None,
    evaluated_at: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return ``(sufficiency_result, oldest_evidence_recorded_at)``.

    The second value is the earliest ``recorded_at`` among the Evidence records
    ``evaluate_sufficiency`` itself reproduced -- F5's real source for G18's
    ``evaluation_expires_at`` derivation, rather than a second, independent read of the
    same Evidence.
    """

    if sufficiency_request is None:
        gates.set("G12", "FAIL", "no evidence sufficiency request was supplied")
        gates.set("G18", "FAIL", "no evidence sufficiency request was supplied")
        return None, None
    try:
        # ``evaluate_sufficiency`` returns the canonical record wrapped alongside what it
        # deliberately does not decide (``reason_codes``, ``not_evaluated_here``, ...); the
        # canonical ``evidence_sufficiency_result`` is what this module binds against.
        wrapper = evaluate_sufficiency(sufficiency_request)
        sufficiency = wrapper["evidence_sufficiency_result"]
    except EvidenceError as error:
        gates.set("G12", "FAIL", f"evidence sufficiency evaluation failed: {error}")
        gates.set("G18", "FAIL", f"evidence sufficiency evaluation failed: {error}")
        return None, None
    if sufficiency["difference_ref"]["id"] != difference["difference_id"]:
        gates.set("G12", "FAIL", "sufficiency result is bound to another Difference")
        gates.set("G18", "FAIL", "sufficiency result is bound to another Difference")
        return None, None
    if sufficiency["policy_ref"]["semantic_fingerprint"] != policy_semantic_fingerprint(policy):
        gates.set("G12", "FAIL", "sufficiency result is bound to another Closure Policy")
        gates.set("G18", "FAIL", "sufficiency result is bound to another Closure Policy")
        return None, None

    if sufficiency["result"] == "SUFFICIENT":
        gates.set("G12", "PASS")
    else:
        gates.set("G12", "FAIL", f"evidence sufficiency result is {sufficiency['result']}")

    if sufficiency["result"] == "STALE":
        gates.set("G18", "FAIL", "evidence sufficiency result is STALE")
    else:
        gates.set("G18", "PASS")

    evaluations = wrapper["evidence_level_evaluations"]
    oldest = min((item["recorded_at"] for item in evaluations), key=instant) if evaluations else None
    return sufficiency, oldest


def _evaluate_g19(
    gates: _Gates,
    policy: dict[str, Any],
    bindings: list[Any],
    *,
    kernel_source_ref: dict[str, Any] | None,
    kernel_source_witness: dict[str, Any] | None,
    invariant_evaluations: list[Any],
    after_state_candidate: dict[str, Any] | None,
    verification_context: dict[str, Any],
) -> None:
    # R2-G19: the v0.1 mandatory Invariant union is additive over whatever the Policy
    # itself declares -- an empty `required_invariants` cannot reach G19 PASS vacuously.
    # Each mandatory id's own pinned `invariant_definition_sha256` (:mod:`.invariant_registry`)
    # is now the exact expected digest, not merely a presence check: a fabricated digest on
    # a mandatory-id binding no longer passes. A Policy that separately (and redundantly)
    # names a mandatory id in its own `required_invariants` with a *different* digest is a
    # same-ID definition conflict -- ``repository``/``path`` are already schema-fixed
    # constants, so the digest is the only field that can disagree -- and fails G19 closed
    # rather than silently picking one side.
    policy_by_id: dict[str, tuple[str, str]] = {}
    for item in policy["required_invariants"]:
        invariant_id = item["id"]
        digest = item["contract_source_ref"]["invariant_definition_sha256"]
        if invariant_id in policy_by_id and policy_by_id[invariant_id][1] != digest:
            gates.set(
                "G19",
                "FAIL",
                f"Policy required_invariants declares {invariant_id} more than once with "
                "conflicting invariant_definition_sha256",
            )
            return
        policy_by_id[invariant_id] = (item["kind"], digest)

    expected: dict[str, tuple[str, str]] = {}
    for _, invariant_id, mandatory_digest in expected_g19_invariant_entries():
        policy_entry = policy_by_id.get(invariant_id)
        if policy_entry is not None and policy_entry[1] != mandatory_digest:
            gates.set(
                "G19",
                "FAIL",
                f"required_invariants declares {invariant_id} with an invariant_definition_"
                "sha256 that conflicts with the v0.1 mandatory registry's own pinned digest",
            )
            return
        expected[invariant_id] = ("kernel_invariant", mandatory_digest)
    for invariant_id, entry in policy_by_id.items():
        expected.setdefault(invariant_id, entry)

    # R4-F3: live Git commit/tree provenance, via a pure immutable Git object witness --
    # only required (and only meaningful) when a real candidate Invariant set exists.
    # OPTIONAL_OR_DEGRADING_PROVENANCE_ALLOWED=false: a candidate with bindings but no
    # witness fails closed, never silently skips the check.
    if bindings:
        if kernel_source_ref is None or kernel_source_witness is None:
            gates.set(
                "G19",
                "FAIL",
                "a candidate invariant evaluation set requires both kernel_source_ref and "
                "kernel_source_witness",
            )
            return
        commit_sha = kernel_source_ref.get("commit_sha")
        tree_sha = kernel_source_ref.get("tree_sha")
        if not isinstance(commit_sha, str) or not isinstance(tree_sha, str):
            gates.set("G19", "FAIL", "kernel_source_ref is missing commit_sha/tree_sha")
            return
        try:
            verify_kernel_source_witness(
                witness=kernel_source_witness,
                expected_commit_sha=commit_sha,
                expected_tree_sha=tree_sha,
                expected_blob_sha=KERNEL_INVARIANTS_BLOB_SHA,
                path=KERNEL_INVARIANTS_PATH,
            )
        except ReflowValidationError as error:
            gates.set("G19", "FAIL", f"kernel_source_witness did not verify: {error}")
            return
        # R5-F1: a candidate invariant evaluation set requires the real, content-addressed
        # after_state_candidate -- a bare witness proves the *registry*'s own provenance,
        # never that any binding actually names the Candidate this Evaluation is for.
        if after_state_candidate is None:
            gates.set(
                "G19",
                "FAIL",
                "a candidate invariant evaluation set requires a real after_state_candidate",
            )
            return

    got: dict[str, tuple[str, str]] = {}
    for binding in bindings:
        if binding.get("binding_id") != candidate_invariant_evaluation_binding_id(binding):
            gates.set(
                "G19",
                "FAIL",
                f"candidate_invariant_evaluation_binding binding_id does not match its own "
                f"content-addressed derivation: {binding.get('binding_id')}",
            )
            return
        if binding.get("evaluation_result") != "PASS":
            gates.set("G19", "FAIL", f"invariant binding is not PASS: {binding.get('binding_id')}")
            return
        # R5-F1: CANDIDATE_BINDING_REQUIRED/CANDIDATE_ID_AND_FINGERPRINT_EXACT_MATCH_REQUIRED
        # -- the binding's own candidate_id/candidate_semantic_fingerprint must exactly match
        # the real after_state_candidate this Evaluation is actually for, not merely be
        # schema-shaped and self-consistent with the binding's own hash. ``after_state_candidate``
        # is never ``None`` here (checked above whenever bindings is non-empty); the explicit
        # ``is None`` clause fails closed defensively rather than asserting it away.
        if (
            after_state_candidate is None
            or binding.get("candidate_id") != after_state_candidate["candidate_id"]
            or binding.get("candidate_semantic_fingerprint") != after_state_candidate["semantic_fingerprint"]
        ):
            gates.set(
                "G19",
                "FAIL",
                f"candidate_invariant_evaluation_binding's candidate_id/candidate_semantic_"
                f"fingerprint does not match the real after_state_candidate: "
                f"{binding.get('binding_id')}",
            )
            return
        invariant_id = binding["invariant_ref"]["id"]
        if invariant_id in got:
            gates.set(
                "G19",
                "FAIL",
                f"more than one candidate_invariant_evaluation_binding for {invariant_id}",
            )
            return
        # R4-F2: the binding's own invariant_evaluation_ref must resolve to a real,
        # schema-valid Invariant Evaluation record whose recomputed fingerprint and every
        # field the binding asserts actually match -- not merely be present.
        try:
            resolve_invariant_evaluation(
                binding,
                invariant_evaluations,
                base_state_ref=binding["base_state_ref"],
                after_state_candidate=after_state_candidate,
                verification_context=verification_context,
            )
        except DifferenceError as error:
            gates.set(
                "G19",
                "FAIL",
                f"invariant_evaluation_ref for {invariant_id} did not resolve: {error}",
            )
            return
        got[invariant_id] = (
            binding["invariant_ref"]["kind"],
            binding["invariant_definition_ref"]["invariant_definition_sha256"],
        )

    if got != expected:
        gates.set(
            "G19",
            "FAIL",
            "candidate_invariant_evaluation_bindings do not exactly match the expected "
            "invariant set (Policy required_invariants union the v0.1 mandatory registry, "
            "each by exact (kind, id, invariant_definition_sha256))",
        )
        return
    gates.set("G19", "PASS")


def _evaluate_g21(
    gates: _Gates,
    policy: dict[str, Any],
    difference_id: str,
    current_state: dict[str, Any],
    bindings: list[Any],
    claim_events: list[Any],
    *,
    invariant_evaluation_refs: list[Any],
    material_contradiction_refs: list[Any],
    after_state_candidate: dict[str, Any] | None,
) -> None:
    expected = {MANDATORY_X003_CLAIM_ID} | {item["id"] for item in policy["required_claims"]}
    got_satisfied: set[str] = set()
    got_all: set[str] = set()
    observed_state_ref = {
        "kind": "state",
        "revision": current_state["revision"],
        "fingerprint": current_state["fingerprint"],
    }
    # R5-F1: a completion Claim binding requires the real, content-addressed
    # after_state_candidate -- see the identical G19 requirement's own comment.
    if bindings and after_state_candidate is None:
        gates.set(
            "G21",
            "FAIL",
            "a candidate_claim_evaluation_binding requires a real after_state_candidate",
        )
        return
    for binding in bindings:
        claim_id = binding["required_claim_ref"]["id"]
        got_all.add(claim_id)
        # R2-F8: "evaluated State" -- the binding's own base_state_ref must be the exact
        # State this Evaluation is itself bound to, never a stale or foreign one a caller
        # could otherwise reuse from an earlier candidate.
        base_state_ref = binding.get("base_state_ref") or {}
        if (
            base_state_ref.get("revision") != current_state["revision"]
            or base_state_ref.get("fingerprint") != current_state["fingerprint"]
        ):
            gates.set(
                "G21",
                "FAIL",
                f"claim binding for {claim_id} is not bound to the evaluated State",
            )
            return
        # R5-F1/R6-F2: CANDIDATE_BINDING_REQUIRED/CANDIDATE_ID_AND_FINGERPRINT_EXACT_MATCH_
        # REQUIRED is now enforced *inside* :func:`resolve_claim_binding` itself (see its own
        # docstring) rather than inline here -- the exact same check the atomic preflight
        # calls, so the two can never again silently diverge on it, the way the equivalent
        # check on Invariant Evaluation bindings once did (R6-F3).
        #
        # F8/R2-F8: the binding's own `evaluation_status` (and every other field it
        # asserts) is never trusted directly -- the append-only
        # `candidate_claim_evaluation_event` series is fully reconstructed and its one
        # true latest event resolved, and the binding must match that latest event
        # exactly. A later REVOKED/STALE/non-SATISFIED event supersedes an older
        # SATISFIED one even if the binding still points at it: that binding no longer
        # matches the true latest event and fails here, not silently passes.
        if after_state_candidate is None:
            # Unreachable: checked above whenever bindings is non-empty. The explicit
            # narrowing lets the shared resolver's own required parameter stay non-optional
            # rather than accepting `None` only to reject it internally.
            gates.set("G21", "FAIL", "a candidate_claim_evaluation_binding requires a real after_state_candidate")
            return
        try:
            chain = resolve_claim_binding(
                claim_events,
                binding,
                difference_id=difference_id,
                after_state_candidate=after_state_candidate,
            )
        except ReflowValidationError as error:
            gates.set(
                "G21",
                "FAIL",
                f"claim evaluation series for {claim_id} did not reconstruct: {error}",
            )
            return
        # R4-F2/R3-F2: the binding's completion_record_ref must resolve to the one
        # Completion Record its own Claim descriptor and this Evaluation's inputs imply --
        # not merely echo the head event's own restated ref/fingerprint.
        try:
            resolve_completion_record(
                binding,
                policy=policy,
                observed_state_ref=observed_state_ref,
                evaluated_state_revision=current_state["revision"],
                evaluated_state_fingerprint=current_state["fingerprint"],
                invariant_evaluation_refs=invariant_evaluation_refs,
                material_contradiction_refs=material_contradiction_refs,
            )
        except DifferenceError as error:
            gates.set(
                "G21",
                "FAIL",
                f"completion_record_ref for {claim_id} did not resolve: {error}",
            )
            return
        if chain[0]["evaluation_status"] == "SATISFIED":
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


def build_after_state_candidate(
    *,
    current_state: dict[str, Any],
    kernel_source_ref: dict[str, Any],
    semantic_state: dict[str, Any],
    semantic_fingerprint: dict[str, Any],
    source_snapshot_refs: list[Any],
    producing_change_refs: list[Any],
) -> dict[str, Any]:
    """Build the one real, content-addressed ``after_state_candidate`` a request's own
    inputs imply.

    Public (R5-F1): every ``candidate_invariant_evaluation_binding``/
    ``candidate_claim_evaluation_binding``'s own ``candidate_id``/``candidate_semantic_
    fingerprint`` must exactly match this same candidate's own ``candidate_id``/
    ``semantic_fingerprint`` -- a caller building a real, resolvable binding needs this
    function too, not only :func:`evaluate_closure`'s own internal call.
    """

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

    # R5-F1: the real, content-addressed after_state_candidate this request's own inputs
    # imply -- built here, before G19/G21 run, so both gates can verify every binding's own
    # candidate_id/candidate_semantic_fingerprint against it rather than accept a caller's
    # bare restatement of either.
    has_candidate_material = shaped["after_state_semantic_state"] is not None
    after_state_candidate = None
    if has_candidate_material:
        semantic_state = require_object(shaped["after_state_semantic_state"], "after_state_semantic_state")
        semantic_fingerprint = fingerprint_semantic_state(semantic_state).as_dict()
        after_state_candidate = build_after_state_candidate(
            current_state=current_state,
            kernel_source_ref=require_object(shaped["kernel_source_ref"], "kernel_source_ref"),
            semantic_state=semantic_state,
            semantic_fingerprint=semantic_fingerprint,
            source_snapshot_refs=require_collection(shaped["source_snapshot_refs"], "source_snapshot_refs"),
            producing_change_refs=require_collection(
                shaped["producing_change_refs"], "producing_change_refs"
            ),
        )

    # R6-F4: an independent, top-level verification of the caller-supplied
    # kernel_source_witness against kernel_source_ref -- separate from G19's own
    # per-binding verification -- so the Closure Evaluation can carry a reference to the
    # verified witness bytes even when no invariant binding happens to need it. Identity is
    # the commit's own native commit_sha (already independently re-derived by
    # verify_kernel_source_witness), not a new domain-separated hash.
    kernel_source_witness_ref = None
    if has_candidate_material:
        kernel_source_ref_in = (
            shaped["kernel_source_ref"] if isinstance(shaped["kernel_source_ref"], dict) else None
        )
        kernel_source_witness_in = (
            shaped["kernel_source_witness"] if isinstance(shaped["kernel_source_witness"], dict) else None
        )
        if kernel_source_ref_in is not None and kernel_source_witness_in is not None:
            commit_sha = kernel_source_ref_in.get("commit_sha")
            tree_sha = kernel_source_ref_in.get("tree_sha")
            if isinstance(commit_sha, str) and isinstance(tree_sha, str):
                try:
                    verify_kernel_source_witness(
                        witness=kernel_source_witness_in,
                        expected_commit_sha=commit_sha,
                        expected_tree_sha=tree_sha,
                        expected_blob_sha=KERNEL_INVARIANTS_BLOB_SHA,
                        path=KERNEL_INVARIANTS_PATH,
                    )
                    witness_record = build_kernel_source_witness_record(
                        commit_sha=commit_sha,
                        tree_sha=tree_sha,
                        blob_sha=KERNEL_INVARIANTS_BLOB_SHA,
                        path=KERNEL_INVARIANTS_PATH,
                        witness=kernel_source_witness_in,
                    )
                    kernel_source_witness_ref = {
                        "kind": "kernel_source_witness",
                        "id": witness_record["kernel_source_witness_id"],
                    }
                except ReflowValidationError:
                    pass

    gates = _Gates()
    _evaluate_g1_g2(gates, difference, current_status)
    objective_revision_id = shaped["objective_revision_id"]
    if not isinstance(objective_revision_id, str) or not objective_revision_id:
        raise ReflowValidationError("objective_revision_id must be a non-empty string")
    base_kernel_source_ref = require_object(shaped["base_kernel_source_ref"], "base_kernel_source_ref")
    kernel_source_ref_for_g4 = require_object(shaped["kernel_source_ref"], "kernel_source_ref")
    _evaluate_g3_g4(
        gates,
        difference,
        objective_revision_id=objective_revision_id,
        reobservation=shaped["reobservation"] if isinstance(shaped["reobservation"], dict) else None,
        base_kernel_source_ref=base_kernel_source_ref,
        kernel_source_ref=kernel_source_ref_for_g4,
        has_candidate_material=has_candidate_material,
        kernel_source_witness_verified=kernel_source_witness_ref is not None,
    )
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
    change_result_evidence_refs_in = require_collection(
        shaped["change_result_evidence_refs"], "change_result_evidence_refs"
    )
    change_result_evidence_requests_in = require_collection(
        shaped["change_result_evidence_requests"], "change_result_evidence_requests"
    )
    change_result_evidence_for_context, change_free_evidence_for_context = _evaluate_reproduction_gates(
        gates,
        difference,
        policy,
        shaped["reobservation"] if isinstance(shaped["reobservation"], dict) else None,
        shaped["resolution_mode"],
        change_result_evidence_refs_in,
        change_result_evidence_requests_in,
        require_collection(
            shaped["change_free_verification_evidence_refs"],
            "change_free_verification_evidence_refs",
        ),
        require_collection(
            shaped["change_free_verification_evidence_requests"],
            "change_free_verification_evidence_requests",
        ),
        require_collection(shaped["source_snapshot_refs"], "source_snapshot_refs"),
        require_collection(shaped["source_snapshots"], "source_snapshots"),
    )
    sufficiency, oldest_evidence_recorded_at = _evaluate_g12_g18(
        gates,
        difference,
        policy,
        shaped["evidence_sufficiency_request"]
        if isinstance(shaped["evidence_sufficiency_request"], dict)
        else None,
        evaluated_at,
    )
    # Every named contradiction is recorded in the output regardless of impact --
    # CLOSURE_POLICY.md's fail-closed table only routes a *Material* one to CONTRADICTED
    # ("非material contradictionは記録されたまま"); a non-material one still names a real
    # conflict this Difference's provenance carries and must not be silently dropped.
    # Computed here (moved up from after G19/G21) because R4-F2's Completion Record
    # resolution needs `contradiction_refs` as its own `material_contradiction_refs`.
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

    invariant_bindings = require_collection(
        shaped["candidate_invariant_evaluation_bindings"], "candidate_invariant_evaluation_bindings"
    )
    invariant_evaluations = require_collection(shaped["invariant_evaluations"], "invariant_evaluations")
    reobservation_for_context = (
        shaped["reobservation"] if isinstance(shaped["reobservation"], dict) else None
    )
    after_observation_ids_for_context: set[str] = set()
    if reobservation_for_context is not None:
        for ref in reobservation_for_context.get("after_observation_refs") or []:
            ref_id = _reference_id(ref)
            if ref_id is not None:
                after_observation_ids_for_context.add(ref_id)
    verification_context = build_invariant_verification_context(
        policy=policy,
        difference=difference,
        current_state=current_state,
        after_state_candidate=after_state_candidate,
        resolution_mode=shaped["resolution_mode"],
        change_result_evidence=change_result_evidence_for_context,
        change_free_evidence=change_free_evidence_for_context,
        after_observation_ids=after_observation_ids_for_context,
        source_snapshot_refs=require_collection(shaped["source_snapshot_refs"], "source_snapshot_refs"),
        source_snapshots=require_collection(shaped["source_snapshots"], "source_snapshots"),
        sufficiency=sufficiency,
        material_contradictions=material_contradictions,
        blocking_contradictions=blocking_contradictions,
        proposed_terminal_status=proposed_terminal_status,
    )
    _evaluate_g19(
        gates,
        policy,
        invariant_bindings,
        kernel_source_ref=shaped["kernel_source_ref"] if isinstance(shaped["kernel_source_ref"], dict) else None,
        kernel_source_witness=shaped["kernel_source_witness"]
        if isinstance(shaped["kernel_source_witness"], dict)
        else None,
        invariant_evaluations=invariant_evaluations,
        after_state_candidate=after_state_candidate,
        verification_context=verification_context,
    )
    claim_bindings = require_collection(
        shaped["candidate_claim_evaluation_bindings"], "candidate_claim_evaluation_bindings"
    )
    claim_events = require_collection(
        shaped["candidate_claim_evaluation_events"], "candidate_claim_evaluation_events"
    )
    invariant_evaluation_refs_for_completion = [
        binding["invariant_evaluation_ref"] for binding in invariant_bindings
    ]
    _evaluate_g21(
        gates,
        policy,
        difference["difference_id"],
        current_state,
        claim_bindings,
        claim_events,
        invariant_evaluation_refs=invariant_evaluation_refs_for_completion,
        material_contradiction_refs=contradiction_refs,
        after_state_candidate=after_state_candidate,
    )
    _evaluate_g22(gates, policy, proposed_terminal_status)

    # F5/G18: the *evaluator's* freshness deadline, derived from the oldest admitted
    # Evidence instant plus the Policy's `maximum_evidence_age` -- never the wall clock.
    # A `null` (unbounded) age or no admitted Evidence at all leaves no deadline to derive.
    maximum_evidence_age = policy["maximum_evidence_age"]
    if (
        sufficiency is not None
        and maximum_evidence_age is not None
        and oldest_evidence_recorded_at is not None
    ):
        evaluation_expires_at = _format_instant(
            instant(oldest_evidence_recorded_at) + timedelta(seconds=maximum_evidence_age)
        )
    else:
        evaluation_expires_at = None
    terminal_reason_evidence_refs = require_collection(
        shaped["terminal_reason_evidence_refs"], "terminal_reason_evidence_refs"
    )

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
        # R7-F4/R8-F3: a bare terminal_reason_evidence_refs id, with no real Evidence request
        # to reproduce it from, is exactly the same "reference without substance" R6-F1b
        # already refused for change_free_verification_evidence_refs -- Evidence remains the
        # sole producer, reproduced and bound to this real Difference through the one shared
        # resolver (:func:`~manosube_agent_civilization.evidence.engine.
        # resolve_terminal_reason_evidence`) the atomic preflight and admitted-record
        # persistence also call, never assembled or re-verified independently by Reflow.
        terminal_reason_evidence_requests = require_collection(
            shaped["terminal_reason_evidence_requests"], "terminal_reason_evidence_requests"
        )
        if not terminal_reason_evidence_requests:
            raise ReflowValidationError(
                f"{evaluation_mode} supplied no terminal_reason_evidence_requests to "
                "reproduce the terminal reason Evidence from"
            )
        try:
            resolve_terminal_reason_evidence(
                terminal_reason_evidence_refs,
                terminal_reason_evidence_requests,
                difference=difference,
            )
        except EvidenceError as error:
            raise ReflowValidationError(
                f"terminal_reason_evidence_refs did not resolve: {error}"
            ) from error

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
        "kernel_source_witness_ref": kernel_source_witness_ref,
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
        "evaluation_expires_at": evaluation_expires_at,
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
