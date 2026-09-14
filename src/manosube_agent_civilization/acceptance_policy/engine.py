"""Pure Acceptance Policy derivation logic (FD-0004, Issue #80).

Every function here is a pure function of its explicit inputs: no Store access, no clock, no
network -- exactly the discipline ``authority.engine``, ``evidence.engine`` and
``reflow.reference_registry`` already hold themselves to. :mod:`.route` is the only module in
this package that ever touches the Store.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.development_binding import (
    ADOPTION_RECORD_ADMITTED,
    AdoptionRecordError,
    evaluate_adoption_record,
)

from . import identity
from .errors import (
    AcceptancePolicyValidationError,
    PolicyLineageConflictError,
    PolicyProvenanceError,
    UnauthorizedPolicyAdoptionError,
    UndeclaredPolicyChangeError,
)
from .types import BLOCKING_EFFECT_FIELDS, POLICY_CLASSES, POLICY_OPERATIONS

SCHEMA_VERSION = "0.1"

#: The three closed clause fields a semantic-diff classification is ever computed over
#: (FD4-C5). ``statement``/``rationale`` are prose provenance; ``existed_in_original_contract``
#: is a lineage fact about the clause *version*, not part of what changed between versions.
_COMPARISON_FIELDS: tuple[str, ...] = ("policy_class", "blocking_effect", "scope")


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AcceptancePolicyValidationError(f"{context} is not an object: {type(value).__name__}")
    return value


def _clause_comparison_projection(clause: dict[str, Any]) -> dict[str, Any]:
    return {field: clause[field] for field in _COMPARISON_FIELDS}


def _true_blocking_fields(blocking_effect: dict[str, bool]) -> frozenset[str]:
    return frozenset(
        field for field in BLOCKING_EFFECT_FIELDS if blocking_effect.get(field) is True
    )


def require_valid_clause(clause: Any) -> dict[str, Any]:
    """Fail-closed structural check for one clause body -- the same shallow shape/enum checks
    a JSON Schema would perform, kept in Python so :mod:`.engine`/:mod:`.route` never need to
    round-trip through the schema validator just to read a field safely."""

    shaped = _require_object(clause, "acceptance policy clause")
    required = {
        "clause_id",
        "policy_class",
        "statement",
        "blocking_effect",
        "scope",
        "rationale",
        "existed_in_original_contract",
    }
    missing = required - set(shaped)
    if missing:
        raise AcceptancePolicyValidationError(f"clause omits required keys: {sorted(missing)}")
    unknown = set(shaped) - required
    if unknown:
        raise AcceptancePolicyValidationError(f"clause carries unknown keys: {sorted(unknown)}")
    if shaped["policy_class"] not in POLICY_CLASSES:
        raise AcceptancePolicyValidationError(f"unknown policy_class: {shaped['policy_class']!r}")
    blocking_effect = _require_object(shaped["blocking_effect"], "clause blocking_effect")
    if set(blocking_effect) != set(BLOCKING_EFFECT_FIELDS):
        raise AcceptancePolicyValidationError(
            f"blocking_effect must declare exactly {sorted(BLOCKING_EFFECT_FIELDS)}"
        )
    for field in BLOCKING_EFFECT_FIELDS:
        if not isinstance(blocking_effect[field], bool):
            raise AcceptancePolicyValidationError(f"blocking_effect.{field} is not a boolean")
    return shaped


def classify_operation(
    prior_clause: dict[str, Any] | None, proposed_clause: dict[str, Any] | None
) -> str:
    """FD4-C5: independently classify which of the six closed operations a prior/proposed
    clause-body pair actually represents. Never trusts a caller's own declared label -- this
    is the function that label is checked *against*.
    """

    if prior_clause is None and proposed_clause is None:
        raise AcceptancePolicyValidationError(
            "cannot classify a transition with neither a prior nor a proposed clause body"
        )
    if prior_clause is None:
        require_valid_clause(proposed_clause)
        return "ADD"
    if proposed_clause is None:
        require_valid_clause(prior_clause)
        return "REMOVE"

    require_valid_clause(prior_clause)
    require_valid_clause(proposed_clause)
    if _clause_comparison_projection(prior_clause) == _clause_comparison_projection(
        proposed_clause
    ):
        raise UndeclaredPolicyChangeError(
            "proposed clause is semantically identical to its own predecessor for "
            f"clause_id {proposed_clause['clause_id']!r} -- not a real policy change"
        )
    if prior_clause["policy_class"] != proposed_clause["policy_class"]:
        return "RECLASSIFY"

    prior_blockers = _true_blocking_fields(prior_clause["blocking_effect"])
    proposed_blockers = _true_blocking_fields(proposed_clause["blocking_effect"])
    added = proposed_blockers - prior_blockers
    removed = prior_blockers - proposed_blockers
    if added and not removed:
        return "BROADEN"
    if removed and not added:
        return "NARROW"
    return "REPLACE"


def assert_transition_operation_matches_diff(
    transition: dict[str, Any], prior_clause: dict[str, Any] | None
) -> None:
    """FD4-C1/FD4-C5: the transition's own declared ``policy_operation`` must equal the
    independently computed classification -- raised before any Store admission.
    """

    computed = classify_operation(prior_clause, transition.get("proposed_clause"))
    declared = transition.get("policy_operation")
    if declared not in POLICY_OPERATIONS:
        raise AcceptancePolicyValidationError(f"unknown policy_operation: {declared!r}")
    if declared != computed:
        raise UndeclaredPolicyChangeError(
            f"transition declares policy_operation={declared!r} for clause_id "
            f"{transition.get('clause_id')!r}, but the independently computed operation is "
            f"{computed!r}"
        )


def _mentions_in_text(text: str, known_clause_ids: frozenset[str]) -> set[str]:
    """A clause_id counts as *mentioned* whether it appears as an exact string value or as a
    substring of a longer key/value (e.g. the real Phase 19 incident's own
    ``GITHUB_PREMERGE_GATE_GREEN_REQUIRED`` flag name, not the bare clause_id alone) -- a
    caller narrowing a gate's own name inside a larger flag/key is exactly the smuggling shape
    FD4-C4 must catch, not only a verbatim standalone match."""

    return {clause_id for clause_id in known_clause_ids if clause_id in text}


def _find_known_clause_id_mentions(node: Any, known_clause_ids: frozenset[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(node, str):
        found |= _mentions_in_text(node, known_clause_ids)
    elif isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str):
                found |= _mentions_in_text(key, known_clause_ids)
            found |= _find_known_clause_id_mentions(value, known_clause_ids)
    elif isinstance(node, list):
        for item in node:
            found |= _find_known_clause_id_mentions(item, known_clause_ids)
    return found


def assert_no_undeclared_policy_change(payload: Any, known_clause_ids: frozenset[str]) -> None:
    """FD4-C4: refuse fail-closed if *payload* -- a code finding, ``REQUIRED_PROOFS`` block,
    implementation handoff, return-Evidence body, or closure-sweep record, anything that is
    *not itself* an ``acceptance_policy_transition`` -- mentions a clause_id this lineage
    already knows about anywhere in its structure, without declaring ``policy_change: True``
    at the payload's own top level.

    This is the mechanical guard against exactly the Phase 19 incident: a gate name appearing
    inside an unrelated ``REQUIRED_PROOFS`` block, or a code-finding adoption, with no
    accompanying policy-change declaration.
    """

    shaped = _require_object(payload, "policy-change-scanned payload")
    mentioned = _find_known_clause_id_mentions(shaped, known_clause_ids)
    if mentioned and shaped.get("policy_change") is not True:
        raise UndeclaredPolicyChangeError(
            f"payload mentions known acceptance-policy clause_id(s) {sorted(mentioned)} "
            "without a top-level policy_change=True declaration (FD4-C4)"
        )


def build_baseline(
    *,
    project_id: str,
    governing_issue: int,
    source_reference: dict[str, Any],
    clauses: list[dict[str, Any]],
) -> dict[str, Any]:
    """FD4-C2: construct the one immutable genesis Baseline for a work unit. Every clause is
    independently shape-checked; duplicate ``clause_id``s within one baseline are refused."""

    if not clauses:
        raise AcceptancePolicyValidationError("a baseline must declare at least one clause")
    seen: set[str] = set()
    validated_clauses: list[dict[str, Any]] = []
    for clause in clauses:
        shaped = require_valid_clause(clause)
        if shaped["clause_id"] in seen:
            raise AcceptancePolicyValidationError(
                f"baseline declares duplicate clause_id {shaped['clause_id']!r}"
            )
        seen.add(shaped["clause_id"])
        if not shaped["existed_in_original_contract"]:
            raise AcceptancePolicyValidationError(
                f"baseline clause {shaped['clause_id']!r} must declare "
                "existed_in_original_contract=true"
            )
        validated_clauses.append(shaped)

    baseline = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "governing_issue": governing_issue,
        "source_reference": deepcopy(source_reference),
        "clauses": validated_clauses,
    }
    baseline["baseline_semantic_fingerprint"] = identity.baseline_semantic_fingerprint(baseline)
    baseline["acceptance_policy_baseline_id"] = identity.baseline_id(baseline)
    return baseline


def build_transition(
    *,
    project_id: str,
    governing_issue: int,
    baseline: dict[str, Any],
    clause_id: str,
    policy_operation: str,
    proposed_by: str,
    prior_clause_binding: dict[str, Any],
    proposed_clause: dict[str, Any] | None,
    prior_clause: dict[str, Any] | None,
    declared_existed_in_original_contract: bool,
    source_reference: dict[str, Any],
    rollback_condition: str,
) -> dict[str, Any]:
    """FD4-C1/FD4-C5: construct one proposed Transition, independently re-verifying that
    *policy_operation* agrees with the actual diff between *prior_clause* and
    *proposed_clause* before the record is even built -- never merely at fold time.
    """

    if proposed_clause is not None:
        proposed_clause = require_valid_clause(proposed_clause)
        if proposed_clause["clause_id"] != clause_id:
            raise AcceptancePolicyValidationError(
                "proposed_clause.clause_id does not match the transition's own clause_id"
            )
        if proposed_clause["existed_in_original_contract"]:
            raise AcceptancePolicyValidationError(
                "a transition's proposed_clause must declare existed_in_original_contract="
                "false -- FD4-C2: a later-added or later-modified clause may never claim it "
                "always existed"
            )
    computed_operation = classify_operation(prior_clause, proposed_clause)
    if policy_operation != computed_operation:
        raise UndeclaredPolicyChangeError(
            f"declared policy_operation={policy_operation!r} does not match the independently "
            f"computed operation {computed_operation!r} for clause_id {clause_id!r}"
        )
    if declared_existed_in_original_contract:
        raise AcceptancePolicyValidationError(
            "declared_existed_in_original_contract must be false for any transition (FD4-C2)"
        )

    transition = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "governing_issue": governing_issue,
        "baseline_ref": {
            "kind": "acceptance_policy_baseline",
            "id": baseline["acceptance_policy_baseline_id"],
        },
        "clause_id": clause_id,
        "policy_operation": policy_operation,
        "proposed_by": proposed_by,
        "prior_clause_binding": deepcopy(prior_clause_binding),
        "proposed_clause": deepcopy(proposed_clause),
        "declared_existed_in_original_contract": declared_existed_in_original_contract,
        "policy_change_declared": True,
        "source_reference": deepcopy(source_reference),
        "rollback_condition": rollback_condition,
    }
    transition["transition_semantic_fingerprint"] = identity.transition_semantic_fingerprint(
        transition
    )
    transition["acceptance_policy_transition_id"] = identity.transition_id(transition)
    return transition


def verify_governance_adoption_record(
    record: Any, *, comment_url: str, governing_issue: int
) -> dict[str, Any]:
    """P82-R2-F1: compose with the repository's existing, non-substitutable Governance
    Adoption Record owner (``development_binding.adoption_record.evaluate_adoption_record``,
    Issue #53) rather than trusting a caller-asserted ``decision_owner``/comment-association
    string pair as sufficient Human-Authority proof on its own.

    *record* must independently evaluate to ``ADOPTION_RECORD_ADMITTED`` -- a malformed shape
    raises (nothing to admit or refuse), and a readable-but-insufficient record (forged
    authority, forged read-back receipt, wrong decision status, unshaped/mismatched SHAs) is
    refused, never silently accepted. Its own declared ``comment_url``/``governing_issue`` must
    also agree with *this exact* acceptance-policy adoption's own source comment and governing
    work unit -- an admitted record for a *different* comment or work unit is not authority for
    *this* one.
    """

    shaped = _require_object(record, "governance_adoption_record")
    try:
        decision = evaluate_adoption_record(shaped)
    except AdoptionRecordError as exc:
        raise UnauthorizedPolicyAdoptionError(
            f"governance_adoption_record is unreadable: {exc}"
        ) from exc
    if decision["decision"] != ADOPTION_RECORD_ADMITTED:
        raise UnauthorizedPolicyAdoptionError(
            "governance_adoption_record was refused by the existing Governance Adoption "
            f"Record owner: {decision['decision_reason_codes']}"
        )
    if shaped["comment_url"] != comment_url:
        raise UnauthorizedPolicyAdoptionError(
            "governance_adoption_record.comment_url does not match this adoption's own "
            f"source_reference.comment_url: {shaped['comment_url']!r} != {comment_url!r}"
        )
    expected_governing_issue = f"#{governing_issue}"
    if shaped["governing_issue"] != expected_governing_issue:
        raise UnauthorizedPolicyAdoptionError(
            "governance_adoption_record.governing_issue does not match this adoption's own "
            f"governing_issue: {shaped['governing_issue']!r} != {expected_governing_issue!r}"
        )
    return shaped


def build_adoption(
    *,
    project_id: str,
    governing_issue: int,
    adopted_ref: dict[str, Any],
    decision_owner: str,
    source_reference: dict[str, Any],
    governance_adoption_record: dict[str, Any],
    decided_at: str,
) -> dict[str, Any]:
    """FD4-C3: construct one Adoption binding. Refuses (rather than silently accepting) any
    ``decision_owner`` other than the sole recognised Human Authority, or a
    ``governance_adoption_record`` that does not independently evaluate to an admitted,
    exactly-bound Governance Adoption Record (P82-R2-F1)."""

    from .types import HUMAN_AUTHORITY

    if decision_owner != HUMAN_AUTHORITY:
        raise AcceptancePolicyValidationError(
            f"decision_owner must be {HUMAN_AUTHORITY!r}, got {decision_owner!r}"
        )
    verified_record = verify_governance_adoption_record(
        governance_adoption_record,
        comment_url=source_reference["comment_url"],
        governing_issue=governing_issue,
    )

    adoption = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "governing_issue": governing_issue,
        "adopted_ref": deepcopy(adopted_ref),
        "decision_owner": decision_owner,
        "source_reference": deepcopy(source_reference),
        "governance_adoption_record": deepcopy(verified_record),
        "decided_at": decided_at,
    }
    adoption["adoption_semantic_fingerprint"] = identity.adoption_semantic_fingerprint(adoption)
    adoption["acceptance_policy_adoption_id"] = identity.adoption_id(adoption)
    return adoption


def derive_effective_policy(
    baseline: dict[str, Any],
    transitions_by_id: dict[str, dict[str, Any]],
    adoptions: list[dict[str, Any]],
) -> dict[str, Any]:
    """FD4-C6: derive the current effective policy from the immutable baseline plus the
    complete ordered set of valid, identity-bound adoptions -- never a caller-authored
    summary.

    *adoptions* must already be in the order they were decided (the Store's own canonical
    commit order for this work unit's adoption records -- see ``route._resolve_canonical_
    adoptions``). Each adoption's target is folded in turn; the moment any one cannot be
    cleanly folded onto the state-so-far, this function refuses rather than silently picking a
    resolution (FD4-C6's own explicit requirement that conflicting/missing/cyclic/stale/
    cross-project/unauthorized transitions "remain explicit and block a clean policy view").

    P82-R1-F2: the baseline's own clauses are not live until an adoption of the baseline
    itself is folded -- ``effective_clauses`` is empty for a proposed-but-not-yet-adopted
    baseline, and a transition-targeting adoption folded before the baseline's own is refused
    as an ordering violation, never silently accepted against an unseeded state.
    """

    project_id = baseline["project_id"]
    governing_issue = baseline["governing_issue"]
    baseline_ref = {
        "kind": "acceptance_policy_baseline",
        "id": baseline["acceptance_policy_baseline_id"],
    }

    live: dict[str, dict[str, Any]] = {}
    provenance: dict[str, list[dict[str, str]]] = {}
    current_version_ref: dict[str, dict[str, str]] = {}
    # P82-R1-F2: the genesis baseline's own clauses are never seeded into the effective view
    # until an explicit, identity-bound Human-Authority adoption of the baseline itself is
    # folded -- a baseline that merely exists (proposed, committed) is not yet in effect.
    baseline_activated = False

    folded_adoption_refs: list[dict[str, str]] = []
    seen_adoption_ids: set[str] = set()

    for adoption in adoptions:
        adoption_record_id = adoption["acceptance_policy_adoption_id"]
        if adoption_record_id in seen_adoption_ids:
            raise PolicyLineageConflictError(
                f"adoption {adoption_record_id!r} folded more than once (replay conflict)"
            )
        seen_adoption_ids.add(adoption_record_id)

        if adoption["project_id"] != project_id or adoption["governing_issue"] != governing_issue:
            raise PolicyLineageConflictError(
                f"adoption {adoption_record_id!r} targets a different project/work unit than "
                "this baseline (cross-project or cross-Issue substitution)"
            )

        adopted_ref = adoption["adopted_ref"]
        adoption_ref = {"kind": "acceptance_policy_adoption", "id": adoption_record_id}

        if adopted_ref["kind"] == "acceptance_policy_baseline":
            if adopted_ref["id"] != baseline["acceptance_policy_baseline_id"]:
                raise PolicyLineageConflictError(
                    f"adoption {adoption_record_id!r} adopts a different baseline than this lineage's own"
                )
            if baseline_activated:
                # P82-R1-F2: a second adoption of the identical, already-activated genesis
                # baseline is a duplicate baseline adoption -- refused rather than silently
                # folded as a no-op, so exactly one Human-Authority act is ever what activates
                # a genesis.
                raise PolicyLineageConflictError(
                    f"adoption {adoption_record_id!r} is a duplicate genesis-baseline adoption -- "
                    f"baseline {baseline['acceptance_policy_baseline_id']!r} is already activated"
                )
            for clause in baseline["clauses"]:
                clause_id = clause["clause_id"]
                if clause_id in live:
                    raise PolicyLineageConflictError(
                        f"baseline declares duplicate clause_id {clause_id!r}"
                    )
                live[clause_id] = clause
                provenance[clause_id] = [baseline_ref]
                current_version_ref[clause_id] = baseline_ref
            baseline_activated = True
            folded_adoption_refs.append(adoption_ref)
            continue

        if not baseline_activated:
            # P82-R1-F2: a transition-targeting adoption folded before the genesis baseline's
            # own adoption is a transition-before-baseline ordering violation -- there is no
            # activated predecessor state for it to extend yet.
            raise PolicyLineageConflictError(
                f"adoption {adoption_record_id!r} adopts transition {adopted_ref['id']!r} "
                f"before this lineage's own genesis baseline "
                f"{baseline['acceptance_policy_baseline_id']!r} has itself been adopted"
            )

        transition_id_value = adopted_ref["id"]
        transition = transitions_by_id.get(transition_id_value)
        if transition is None:
            raise PolicyProvenanceError(
                f"adoption {adoption_record_id!r} references transition "
                f"{transition_id_value!r}, which does not resolve"
            )
        if (
            transition["project_id"] != project_id
            or transition["governing_issue"] != governing_issue
        ):
            raise PolicyLineageConflictError(
                f"transition {transition_id_value!r} targets a different project/work unit "
                "(cross-project or cross-Issue substitution)"
            )
        if transition["baseline_ref"]["id"] != baseline["acceptance_policy_baseline_id"]:
            raise PolicyLineageConflictError(
                f"transition {transition_id_value!r} does not bind to this lineage's own baseline"
            )

        clause_id = transition["clause_id"]
        binding = transition["prior_clause_binding"]
        expected_prior_ref = current_version_ref.get(clause_id)
        actual_prior_ref = binding["source_ref"]
        is_currently_live = clause_id in live

        if expected_prior_ref is None:
            if (
                binding["source"] != "BASELINE"
                or actual_prior_ref["id"] != baseline["acceptance_policy_baseline_id"]
            ):
                raise PolicyLineageConflictError(
                    f"transition {transition_id_value!r} for new clause_id {clause_id!r} must "
                    f"bind prior_clause_binding to this lineage's own baseline (missing "
                    f"predecessor), got {actual_prior_ref!r}"
                )
            if transition["policy_operation"] != "ADD":
                raise PolicyLineageConflictError(
                    f"transition {transition_id_value!r} introduces new clause_id {clause_id!r} "
                    f"but declares policy_operation={transition['policy_operation']!r}, not ADD "
                    "(missing predecessor)"
                )
        else:
            if actual_prior_ref != expected_prior_ref:
                raise PolicyLineageConflictError(
                    f"transition {transition_id_value!r} binds prior_clause_binding to "
                    f"{actual_prior_ref!r}, but the currently-effective predecessor for "
                    f"{clause_id!r} is {expected_prior_ref!r} (fork, reordering, or stale base)"
                )
            if transition["policy_operation"] == "ADD" and is_currently_live:
                raise PolicyLineageConflictError(
                    f"transition {transition_id_value!r} declares ADD for clause_id "
                    f"{clause_id!r}, which already has a live effective clause"
                )
            if transition["policy_operation"] != "ADD" and not is_currently_live:
                raise PolicyLineageConflictError(
                    f"transition {transition_id_value!r} declares "
                    f"{transition['policy_operation']!r} for clause_id {clause_id!r}, which has "
                    "no currently-live clause to operate on"
                )

        prior_clause = live.get(clause_id)
        proposed_clause = transition["proposed_clause"]
        computed_operation = classify_operation(prior_clause, proposed_clause)
        if computed_operation != transition["policy_operation"]:
            raise UndeclaredPolicyChangeError(
                f"transition {transition_id_value!r} declares policy_operation="
                f"{transition['policy_operation']!r} but the independently recomputed "
                f"operation is {computed_operation!r}"
            )

        transition_ref = {"kind": "acceptance_policy_transition", "id": transition_id_value}
        if transition["policy_operation"] == "REMOVE":
            del live[clause_id]
            del provenance[clause_id]
        else:
            live[clause_id] = proposed_clause
            provenance[clause_id] = [*provenance.get(clause_id, [baseline_ref]), transition_ref]
        current_version_ref[clause_id] = transition_ref
        folded_adoption_refs.append(adoption_ref)

    effective_clauses = []
    for clause_id in sorted(live):
        clause = live[clause_id]
        effective_clauses.append(
            {
                "clause_id": clause_id,
                "policy_class": clause["policy_class"],
                "blocking_effect": clause["blocking_effect"],
                "scope": clause["scope"],
                "existed_in_original_contract": clause["existed_in_original_contract"],
                "provenance_chain": provenance[clause_id],
            }
        )

    view = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "governing_issue": governing_issue,
        "baseline_ref": baseline_ref,
        "effective_clauses": effective_clauses,
        "folded_adoption_refs": folded_adoption_refs,
    }
    view["effective_view_semantic_fingerprint"] = identity.effective_view_semantic_fingerprint(view)
    return view


def build_impact_preview(
    before_view: dict[str, Any],
    candidate_transition: dict[str, Any],
) -> dict[str, Any]:
    """FD4-C7: the bounded before/after impact preview SHUKOU must see before adopting.
    Pure -- makes no Store mutation and requires no prior commit of *candidate_transition*.
    """

    project_id = before_view["project_id"]
    governing_issue = before_view["governing_issue"]
    clause_id = candidate_transition["clause_id"]

    before_clauses_by_id = {c["clause_id"]: c for c in before_view["effective_clauses"]}
    prior_effective = before_clauses_by_id.get(clause_id)

    after_clauses_by_id = dict(before_clauses_by_id)
    if candidate_transition["policy_operation"] == "REMOVE":
        # P82-R1-F5: a removed clause has no surviving effective version -- no provenance to
        # extend, because there is nothing left to attribute it to.
        after_clauses_by_id.pop(clause_id, None)
    else:
        proposed = candidate_transition["proposed_clause"]
        # P82-R1-F5: the candidate transition itself must appear in the after-policy clause's
        # own provenance -- an ADD's chain starts with it (there is no prior chain to extend);
        # every modifying operation (REPLACE/NARROW/BROADEN/RECLASSIFY) extends the prior
        # effective clause's own chain with it. Previously this fold silently reused the prior
        # clause's provenance unchanged, so a preview's own after-policy could never be
        # attributed back to the candidate transition that produced it.
        candidate_transition_ref = {
            "kind": "acceptance_policy_transition",
            "id": candidate_transition["acceptance_policy_transition_id"],
        }
        prior_provenance = list(prior_effective["provenance_chain"]) if prior_effective else []
        after_clauses_by_id[clause_id] = {
            "clause_id": clause_id,
            "policy_class": proposed["policy_class"],
            "blocking_effect": proposed["blocking_effect"],
            "scope": proposed["scope"],
            "existed_in_original_contract": proposed["existed_in_original_contract"],
            "provenance_chain": [*prior_provenance, candidate_transition_ref],
        }

    prior_blockers = (
        _true_blocking_fields(prior_effective["blocking_effect"])
        if prior_effective
        else frozenset()
    )
    proposed_body = candidate_transition.get("proposed_clause")
    proposed_blockers = (
        _true_blocking_fields(proposed_body["blocking_effect"]) if proposed_body else frozenset()
    )

    new_blockers = [
        {"clause_id": clause_id, "blocking_effect_field": field}
        for field in sorted(proposed_blockers - prior_blockers)
    ]
    removed_blockers = [
        {"clause_id": clause_id, "blocking_effect_field": field}
        for field in sorted(prior_blockers - proposed_blockers)
    ]

    preview = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "governing_issue": governing_issue,
        "before_policy": before_view["effective_clauses"],
        "proposed_change": {
            "policy_operation": candidate_transition["policy_operation"],
            "clause_id": clause_id,
        },
        "after_policy": [after_clauses_by_id[cid] for cid in sorted(after_clauses_by_id)],
        "new_blockers": new_blockers,
        "removed_blockers": removed_blockers,
        "affected_work_units": [{"project_id": project_id, "governing_issue": governing_issue}],
        "rollback_condition": candidate_transition["rollback_condition"],
    }
    preview["preview_semantic_fingerprint"] = identity.impact_preview_semantic_fingerprint(preview)
    return preview
