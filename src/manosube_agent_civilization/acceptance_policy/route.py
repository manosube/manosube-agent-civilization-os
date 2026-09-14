"""The public Store-touching entry points for Acceptance Policy Lineage (FD-0004, Issue #80).

:mod:`.engine` is pure; this module is the only place in the package that ever resolves a
record from the Store or commits one -- through the one shared, already-atomic
``commit_state_transition`` (Structural Review Round 5-R1's ``SINGLE_COMMITTER_REQUIRED``),
never a direct/internal Store mutation of its own (FD4-C10).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import (
    RecordConflictError,
    StaleStateError,
    TransactionConflictError,
)

from . import engine, identity, validation
from .errors import (
    AcceptancePolicyValidationError,
    ConflictingPolicyReplayError,
    PolicyLineageConflictError,
    PolicyProvenanceError,
    UnauthorizedPolicyAdoptionError,
    UndeclaredPolicyChangeError,
)
from .types import HUMAN_AUTHORITY, REQUIRED_COMMENT_AUTHOR_ASSOCIATION

_BASELINE_SCHEMA = "acceptance_policy_baseline.schema.json"
_TRANSITION_SCHEMA = "acceptance_policy_transition.schema.json"
_ADOPTION_SCHEMA = "acceptance_policy_adoption.schema.json"
_EFFECTIVE_VIEW_SCHEMA = "acceptance_policy_effective_view.schema.json"
_IMPACT_PREVIEW_SCHEMA = "acceptance_policy_impact_preview.schema.json"

_BASELINE_KIND = "acceptance_policy_baseline"
_TRANSITION_KIND = "acceptance_policy_transition"
_ADOPTION_KIND = "acceptance_policy_adoption"

#: The identical bounded Compare-And-Swap retry ``change_executor/route.py``'s own
#: ``_commit_records`` and ``url_boot/route.py``'s own ``_commit_envelope`` use -- bounded
#: protection against genuine, unrelated contention only.
_MAX_COMMIT_RETRIES = 8


def _require_source_reference(source_reference: Any) -> dict[str, Any]:
    if not isinstance(source_reference, dict):
        raise AcceptancePolicyValidationError("source_reference is not an object")
    required = {
        "comment_url",
        "comment_id",
        "comment_author",
        "comment_author_association",
        "source_kind",
    }
    missing = required - set(source_reference)
    if missing:
        raise AcceptancePolicyValidationError(
            f"source_reference omits required keys: {sorted(missing)}"
        )
    if source_reference["comment_author_association"] != REQUIRED_COMMENT_AUTHOR_ASSOCIATION:
        raise UnauthorizedPolicyAdoptionError(
            "source_reference.comment_author_association must be "
            f"{REQUIRED_COMMENT_AUTHOR_ASSOCIATION!r}, got "
            f"{source_reference['comment_author_association']!r}"
        )
    return source_reference


def _commit_one_record(
    store: Any,
    project_id: str,
    kind: str,
    record_id: str,
    body: dict[str, Any],
    committed_at: str,
) -> dict[str, Any]:
    """Commit exactly one immutable Acceptance Policy record, under a transaction id derived
    from the record's own content-addressed identity -- so an exact replay (the identical
    record, submitted twice) is naturally idempotent (the identical transaction id, which the
    Store's own Compare-And-Swap commit already treats as a no-op replay), while an attempted
    *conflicting* replay -- the same identity claimed for a materially different body -- always
    fails the Store's own manifest-identity check, translated here into
    :class:`ConflictingPolicyReplayError` rather than an opaque Store exception leaking through
    this package's own boundary.
    """

    already_committed: dict[str, Any] | None = store.resolve_record(project_id, kind, record_id)
    if already_committed is not None:
        if canonical_json_bytes(already_committed) == canonical_json_bytes(body):
            # FD4-C9: an exact replay -- the identical record, submitted again -- is a no-op,
            # never a re-commit. Content-addressed identity already proves the two calls agree
            # on every semantic field; nothing more needs to happen.
            current_state: dict[str, Any] = store.load_current(project_id)
            return current_state
        raise ConflictingPolicyReplayError(
            f"a different {kind} record already exists under identity {record_id!r} -- "
            "this is a conflicting replay, not an exact one"
        )

    transaction_id = record_id
    for _ in range(_MAX_COMMIT_RETRIES):
        current_state = store.load_current(project_id)
        next_state = dict(current_state)
        next_state["state_revision"] = current_state["state_revision"] + 1
        next_state["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
        next_state["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
        next_state["semantic_fingerprint"] = fingerprint_project_state(next_state).as_dict()
        transition = {
            "schema_version": "0.1",
            "transaction_id": transaction_id,
            "event_type": "TRANSITION",
            "project_id": project_id,
            "from_revision": current_state["state_revision"],
            "to_revision": next_state["state_revision"],
            "before_fingerprint": current_state["semantic_fingerprint"],
            "after_fingerprint": next_state["semantic_fingerprint"],
            "after_state": next_state,
            "evidence_refs": [],
            "committed_at": committed_at,
        }
        try:
            return commit_state_transition(
                store,
                project_id,
                current_state["state_revision"],
                current_state["semantic_fingerprint"],
                next_state,
                transition,
                records=[(kind, record_id, body)],
            )
        except (RecordConflictError, TransactionConflictError) as exc:
            raise ConflictingPolicyReplayError(
                f"a different {kind} record already exists under identity {record_id!r} -- "
                "this is a conflicting replay, not an exact one"
            ) from exc
        except StaleStateError:
            continue
    raise AcceptancePolicyValidationError(
        f"could not durably commit {kind} {record_id!r} after {_MAX_COMMIT_RETRIES} "
        "Compare-And-Swap retries -- sustained unrelated contention on this project's own State"
    )


def open_acceptance_policy_baseline(
    store: Any,
    project_id: str,
    *,
    governing_issue: int,
    source_reference: dict[str, Any],
    clauses: list[dict[str, Any]],
    committed_at: str,
) -> dict[str, Any]:
    """FD4-C2: commit the one immutable genesis Baseline for a work unit."""

    _require_source_reference(source_reference)
    if source_reference["source_kind"] != "ORIGINAL_ISSUE":
        raise AcceptancePolicyValidationError(
            "a baseline's own source_reference.source_kind must be ORIGINAL_ISSUE"
        )
    baseline = engine.build_baseline(
        project_id=project_id,
        governing_issue=governing_issue,
        source_reference=source_reference,
        clauses=clauses,
    )
    validation.validate_record(baseline, _BASELINE_SCHEMA)
    _commit_one_record(
        store,
        project_id,
        _BASELINE_KIND,
        baseline["acceptance_policy_baseline_id"],
        baseline,
        committed_at,
    )
    return baseline


def resolve_and_verify_baseline(
    store: Any, project_id: str, baseline_id_value: str
) -> dict[str, Any]:
    """Resolve a committed Baseline and independently reproduce its own declared identity and
    semantic fingerprint before ever trusting its content (FD4-C9's tamper boundary)."""

    resolved: dict[str, Any] | None = store.resolve_record(
        project_id, _BASELINE_KIND, baseline_id_value
    )
    if resolved is None:
        raise PolicyProvenanceError(
            f"acceptance_policy_baseline {baseline_id_value!r} does not resolve"
        )
    validation.validate_record(resolved, _BASELINE_SCHEMA)
    if resolved["project_id"] != project_id:
        raise PolicyProvenanceError(
            f"acceptance_policy_baseline {baseline_id_value!r} is bound to a different project "
            f"({resolved['project_id']!r}) than requested ({project_id!r})"
        )
    if (
        identity.baseline_semantic_fingerprint(resolved)
        != resolved["baseline_semantic_fingerprint"]
    ):
        raise PolicyProvenanceError(
            f"acceptance_policy_baseline {baseline_id_value!r} fingerprint does not reproduce"
        )
    if identity.baseline_id(resolved) != baseline_id_value:
        raise PolicyProvenanceError(
            f"acceptance_policy_baseline {baseline_id_value!r} id does not reproduce from its own content"
        )
    return resolved


def resolve_and_verify_transition(
    store: Any, project_id: str, transition_id_value: str
) -> dict[str, Any]:
    """Resolve a committed Transition and independently reproduce its own declared identity
    and semantic fingerprint."""

    resolved: dict[str, Any] | None = store.resolve_record(
        project_id, _TRANSITION_KIND, transition_id_value
    )
    if resolved is None:
        raise PolicyProvenanceError(
            f"acceptance_policy_transition {transition_id_value!r} does not resolve"
        )
    validation.validate_record(resolved, _TRANSITION_SCHEMA)
    if resolved["project_id"] != project_id:
        raise PolicyProvenanceError(
            f"acceptance_policy_transition {transition_id_value!r} is bound to a different "
            f"project ({resolved['project_id']!r}) than requested ({project_id!r})"
        )
    if (
        identity.transition_semantic_fingerprint(resolved)
        != resolved["transition_semantic_fingerprint"]
    ):
        raise PolicyProvenanceError(
            f"acceptance_policy_transition {transition_id_value!r} fingerprint does not reproduce"
        )
    if identity.transition_id(resolved) != transition_id_value:
        raise PolicyProvenanceError(
            f"acceptance_policy_transition {transition_id_value!r} id does not reproduce from its own content"
        )
    return resolved


def resolve_and_verify_adoption(
    store: Any, project_id: str, adoption_id_value: str
) -> dict[str, Any]:
    """Resolve a committed Adoption and independently reproduce its own declared identity and
    semantic fingerprint -- and re-verify its Human Authority binding every time it is read,
    never only at commit time (the same discipline ``change_executor``'s kill-switch resolver
    holds itself to)."""

    resolved: dict[str, Any] | None = store.resolve_record(
        project_id, _ADOPTION_KIND, adoption_id_value
    )
    if resolved is None:
        raise PolicyProvenanceError(
            f"acceptance_policy_adoption {adoption_id_value!r} does not resolve"
        )
    validation.validate_record(resolved, _ADOPTION_SCHEMA)
    if resolved["project_id"] != project_id:
        raise PolicyProvenanceError(
            f"acceptance_policy_adoption {adoption_id_value!r} is bound to a different project "
            f"({resolved['project_id']!r}) than requested ({project_id!r})"
        )
    if (
        identity.adoption_semantic_fingerprint(resolved)
        != resolved["adoption_semantic_fingerprint"]
    ):
        raise PolicyProvenanceError(
            f"acceptance_policy_adoption {adoption_id_value!r} fingerprint does not reproduce"
        )
    if identity.adoption_id(resolved) != adoption_id_value:
        raise PolicyProvenanceError(
            f"acceptance_policy_adoption {adoption_id_value!r} id does not reproduce from its own content"
        )
    if resolved["decision_owner"] != HUMAN_AUTHORITY:
        raise UnauthorizedPolicyAdoptionError(
            f"acceptance_policy_adoption {adoption_id_value!r} decision_owner is "
            f"{resolved['decision_owner']!r}, not {HUMAN_AUTHORITY!r}"
        )
    _require_source_reference(resolved["source_reference"])
    # P82-R2-F1: re-evaluate the Governance Adoption Record binding every time this adoption
    # is read, never only at commit time -- the same discipline the decision_owner/source_
    # reference checks above already hold themselves to.
    engine.verify_governance_adoption_record(
        resolved["governance_adoption_record"],
        comment_url=resolved["source_reference"]["comment_url"],
        governing_issue=resolved["governing_issue"],
    )
    return resolved


def _resolve_canonical_adoptions(
    store: Any, project_id: str, baseline: dict[str, Any]
) -> list[dict[str, Any]]:
    """P82-R1-F1: derive the complete, canonically-ordered adoption set for this baseline's own
    work unit directly from Store-owned state -- never from a caller-supplied list. A caller
    can no longer omit, subset, reorder, fork, or substitute an unrelated adoption into this
    lineage's own effective-policy resolution, because it no longer supplies the set at all.

    Canonical order is genuine commit order, not directory/sort order: ``_commit_one_record``
    sets a record's own content-addressed id as its committing transaction's ``transaction_id``
    (see :mod:`.route` module docstring), so :meth:`store.resolve_transaction` keyed by each
    adoption id returns that adoption's own committed ``to_revision`` -- the one canonical,
    monotonic ordering this project's Store ever assigns.
    """

    governing_issue = baseline["governing_issue"]
    candidate_ids = store.list_committed_record_ids(project_id, _ADOPTION_KIND)
    ordered: list[tuple[int, dict[str, Any]]] = []
    for adoption_id_value in candidate_ids:
        adoption = resolve_and_verify_adoption(store, project_id, adoption_id_value)
        if adoption["governing_issue"] != governing_issue:
            continue
        transaction = store.resolve_transaction(project_id, adoption_id_value)
        if transaction is None:
            raise PolicyProvenanceError(
                f"acceptance_policy_adoption {adoption_id_value!r} has no resolvable "
                "committing transaction -- cannot establish canonical lineage order"
            )
        ordered.append((transaction["to_revision"], adoption))
    ordered.sort(key=lambda pair: pair[0])
    return [adoption for _, adoption in ordered]


def resolve_and_verify_effective_policy(
    store: Any,
    project_id: str,
    baseline_ref: dict[str, str],
) -> dict[str, Any]:
    """FD4-C6: derive the current effective policy from the Store-resolved, independently
    reproduced baseline plus the complete, canonically-ordered adoption set this same lineage's
    own Store state defines (P82-R1-F1 -- never a caller-supplied ``adoption_refs`` list).
    Every referenced transition is likewise Store-resolved and reproduced before being folded --
    nothing here trusts an unresolved reference.
    """

    baseline = resolve_and_verify_baseline(store, project_id, baseline_ref["id"])
    adoptions = _resolve_canonical_adoptions(store, project_id, baseline)

    transitions_by_id: dict[str, dict[str, Any]] = {}
    for adoption in adoptions:
        adopted_ref = adoption["adopted_ref"]
        if adopted_ref["kind"] == _TRANSITION_KIND and adopted_ref["id"] not in transitions_by_id:
            transitions_by_id[adopted_ref["id"]] = resolve_and_verify_transition(
                store, project_id, adopted_ref["id"]
            )

    effective_view = engine.derive_effective_policy(baseline, transitions_by_id, adoptions)
    validation.validate_record(effective_view, _EFFECTIVE_VIEW_SCHEMA)
    return effective_view


def _resolve_expected_prior_clause_binding(
    store: Any,
    project_id: str,
    baseline: dict[str, Any],
    effective_view: dict[str, Any],
    clause_id: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """The one place ``prior_clause_binding``/the prior clause body used for the semantic-diff
    recomputation is derived from the real, current effective view -- shared by
    :func:`propose_acceptance_policy_transition` (to construct a new transition) and
    :func:`_verify_candidate_transition_for_preview` (P82-R2-F3, to verify a caller-supplied
    candidate's own claimed binding against this exact same derivation), so the two can never
    silently diverge on what "the real current predecessor" means.
    """

    effective_by_id = {c["clause_id"]: c for c in effective_view["effective_clauses"]}
    prior_effective = effective_by_id.get(clause_id)

    if prior_effective is None:
        prior_clause_binding = {
            "source": "BASELINE",
            "source_ref": {
                "kind": "acceptance_policy_baseline",
                "id": baseline["acceptance_policy_baseline_id"],
            },
        }
        return prior_clause_binding, None

    prior_ref = prior_effective["provenance_chain"][-1]
    prior_clause_binding = {
        "source": "TRANSITION" if prior_ref["kind"] == _TRANSITION_KIND else "BASELINE",
        "source_ref": prior_ref,
    }
    if prior_ref["kind"] == _TRANSITION_KIND:
        prior_clause_for_diff = resolve_and_verify_transition(store, project_id, prior_ref["id"])[
            "proposed_clause"
        ]
    else:
        prior_clause_for_diff = next(c for c in baseline["clauses"] if c["clause_id"] == clause_id)
    return prior_clause_binding, prior_clause_for_diff


def propose_acceptance_policy_transition(
    store: Any,
    project_id: str,
    *,
    governing_issue: int,
    baseline_ref: dict[str, str],
    clause_id: str,
    policy_operation: str,
    proposed_by: str,
    proposed_clause: dict[str, Any] | None,
    source_reference: dict[str, Any],
    rollback_condition: str,
    committed_at: str,
) -> dict[str, Any]:
    """FD4-C1/FD4-C5: propose one Transition against the *actual*, freshly Store-resolved
    effective policy -- refuses fail-closed, before any commit, if *policy_operation* does not
    match the independently computed diff against the real current predecessor clause.

    Proposing is not adopting (FD4-C3): this commits the Transition as a durable, addressable
    proposal, never as an effective policy change. Only :func:`adopt_acceptance_policy_transition`
    can make one effective.
    """

    _require_source_reference(source_reference)
    baseline = resolve_and_verify_baseline(store, project_id, baseline_ref["id"])
    if baseline["governing_issue"] != governing_issue:
        # P82-R2-F2: a proposal declaring a different governing_issue than its own resolved
        # baseline is refused before any commit -- never silently accepted under the caller's
        # own label.
        raise PolicyLineageConflictError(
            f"baseline {baseline_ref['id']!r} is bound to governing_issue "
            f"{baseline['governing_issue']!r}, not this proposal's own {governing_issue!r}"
        )
    effective_view = resolve_and_verify_effective_policy(store, project_id, baseline_ref)
    prior_clause_binding, prior_clause_for_diff = _resolve_expected_prior_clause_binding(
        store, project_id, baseline, effective_view, clause_id
    )

    transition = engine.build_transition(
        project_id=project_id,
        governing_issue=governing_issue,
        baseline=baseline,
        clause_id=clause_id,
        policy_operation=policy_operation,
        proposed_by=proposed_by,
        prior_clause_binding=prior_clause_binding,
        proposed_clause=proposed_clause,
        prior_clause=prior_clause_for_diff,
        declared_existed_in_original_contract=False,
        source_reference=source_reference,
        rollback_condition=rollback_condition,
    )
    validation.validate_record(transition, _TRANSITION_SCHEMA)
    _commit_one_record(
        store,
        project_id,
        _TRANSITION_KIND,
        transition["acceptance_policy_transition_id"],
        transition,
        committed_at,
    )
    return transition


def _assert_adoption_does_not_poison_the_canonical_lineage(
    store: Any,
    project_id: str,
    baseline: dict[str, Any],
    candidate_adoption: dict[str, Any],
) -> None:
    """P82-R2-F2: simulate folding *candidate_adoption* onto the current canonical adoption
    lineage -- using the exact same fold :func:`engine.derive_effective_policy` already
    performs -- before it is durably committed. A cross-Issue/cross-baseline target, a stale or
    forked predecessor binding, or a duplicate genesis-baseline adoption is refused here, before
    any write, rather than discovered only the next time someone resolves the effective policy
    against an already-immutable, already-poisoned adoption set.
    """

    canonical_adoptions = _resolve_canonical_adoptions(store, project_id, baseline)
    candidate_id = candidate_adoption["acceptance_policy_adoption_id"]
    if any(a["acceptance_policy_adoption_id"] == candidate_id for a in canonical_adoptions):
        # An exact replay of an adoption already part of the canonical lineage was already
        # proven non-poisoning at its own original commit; _commit_one_record's own
        # idempotency check handles the no-op replay from here.
        return

    prospective_adoptions = [*canonical_adoptions, candidate_adoption]
    transitions_by_id: dict[str, dict[str, Any]] = {}
    for adoption in prospective_adoptions:
        adopted_ref = adoption["adopted_ref"]
        if adopted_ref["kind"] == _TRANSITION_KIND and adopted_ref["id"] not in transitions_by_id:
            transitions_by_id[adopted_ref["id"]] = resolve_and_verify_transition(
                store, project_id, adopted_ref["id"]
            )
    engine.derive_effective_policy(baseline, transitions_by_id, prospective_adoptions)


def adopt_acceptance_policy_transition(
    store: Any,
    project_id: str,
    *,
    governing_issue: int,
    adopted_ref: dict[str, str],
    decision_owner: str,
    source_reference: dict[str, Any],
    governance_adoption_record: dict[str, Any],
    decided_at: str,
    committed_at: str,
) -> dict[str, Any]:
    """FD4-C3: commit the identity-bound SHUKOU decision that activates *adopted_ref* -- the
    one baseline genesis or one proposed transition it names. Refuses (before any commit) any
    ``decision_owner`` other than SHUKOU, a ``source_reference`` not carrying the OWNER
    association, or a ``governance_adoption_record`` that does not independently evaluate to an
    admitted, exactly-bound Governance Adoption Record (P82-R2-F1) -- the only Human Authority
    this package ever recognises.

    The referenced target is independently Store-resolved and reproduced *before* the adoption
    itself is built, so an adoption can never be minted for a target that does not genuinely
    exist under the identity it names, and is required to agree with this call's own
    project/governing_issue (P82-R2-F2) -- never merely under the caller's own label. The
    candidate adoption is also simulated against the current canonical lineage before commit,
    so a stale, forked, or duplicate-baseline adoption is refused before it can ever poison the
    immutable canonical set.
    """

    _require_source_reference(source_reference)
    if adopted_ref["kind"] == _BASELINE_KIND:
        target = resolve_and_verify_baseline(store, project_id, adopted_ref["id"])
        baseline_for_simulation = target
    elif adopted_ref["kind"] == _TRANSITION_KIND:
        target = resolve_and_verify_transition(store, project_id, adopted_ref["id"])
        baseline_for_simulation = resolve_and_verify_baseline(
            store, project_id, target["baseline_ref"]["id"]
        )
    else:
        raise AcceptancePolicyValidationError(f"unknown adopted_ref.kind: {adopted_ref['kind']!r}")

    if target["governing_issue"] != governing_issue or target["project_id"] != project_id:
        # P82-R2-F2: cross-work-unit adoption is refused before any commit -- the resolved
        # target's own (project_id, governing_issue) must agree with this adoption's own,
        # never merely with the caller's own separately-declared label.
        raise PolicyLineageConflictError(
            f"adopted_ref {adopted_ref!r} resolves to a record bound to "
            f"(project_id={target['project_id']!r}, governing_issue={target['governing_issue']!r}), "
            f"not this adoption's own (project_id={project_id!r}, governing_issue={governing_issue!r})"
        )

    adoption = engine.build_adoption(
        project_id=project_id,
        governing_issue=governing_issue,
        adopted_ref=adopted_ref,
        decision_owner=decision_owner,
        source_reference=source_reference,
        governance_adoption_record=governance_adoption_record,
        decided_at=decided_at,
    )
    validation.validate_record(adoption, _ADOPTION_SCHEMA)
    _assert_adoption_does_not_poison_the_canonical_lineage(
        store, project_id, baseline_for_simulation, adoption
    )
    _commit_one_record(
        store,
        project_id,
        _ADOPTION_KIND,
        adoption["acceptance_policy_adoption_id"],
        adoption,
        committed_at,
    )
    return adoption


def _verify_candidate_transition_for_preview(
    store: Any,
    project_id: str,
    baseline: dict[str, Any],
    effective_view: dict[str, Any],
    candidate_transition: dict[str, Any],
) -> dict[str, Any]:
    """P82-R2-F3: detach *candidate_transition* from the caller's own mutable object and
    independently verify it before it is ever used to build a preview -- schema, identity,
    fingerprint, project/governing_issue/baseline binding, the prior-clause binding against the
    real current effective view, and the declared operation against the independently
    recomputed semantic diff. Only this retained, fully-verified copy is ever passed to
    :func:`engine.build_impact_preview` -- the caller's own original object, and any further
    mutation of it, has no effect on the preview actually built.
    """

    candidate = deepcopy(candidate_transition)
    validation.validate_record(candidate, _TRANSITION_SCHEMA)

    if (
        identity.transition_semantic_fingerprint(candidate)
        != candidate["transition_semantic_fingerprint"]
    ):
        raise PolicyProvenanceError(
            "candidate_transition fingerprint does not reproduce from its own content"
        )
    if identity.transition_id(candidate) != candidate["acceptance_policy_transition_id"]:
        raise PolicyProvenanceError(
            "candidate_transition id does not reproduce from its own content"
        )

    if candidate["project_id"] != project_id:
        raise PolicyLineageConflictError(
            f"candidate_transition is bound to project_id {candidate['project_id']!r}, not "
            f"this preview's own {project_id!r}"
        )
    if candidate["governing_issue"] != baseline["governing_issue"]:
        raise PolicyLineageConflictError(
            f"candidate_transition is bound to governing_issue {candidate['governing_issue']!r}, "
            f"not this lineage's own {baseline['governing_issue']!r}"
        )
    if candidate["baseline_ref"]["id"] != baseline["acceptance_policy_baseline_id"]:
        raise PolicyLineageConflictError(
            "candidate_transition does not bind to this lineage's own baseline"
        )

    clause_id = candidate["clause_id"]
    expected_prior_clause_binding, prior_clause_for_diff = _resolve_expected_prior_clause_binding(
        store, project_id, baseline, effective_view, clause_id
    )
    if candidate["prior_clause_binding"] != expected_prior_clause_binding:
        raise PolicyLineageConflictError(
            f"candidate_transition binds prior_clause_binding to "
            f"{candidate['prior_clause_binding']!r}, but the currently-effective predecessor "
            f"for {clause_id!r} is {expected_prior_clause_binding!r} (stale, forked, or wrong "
            "predecessor)"
        )

    computed_operation = engine.classify_operation(
        prior_clause_for_diff, candidate.get("proposed_clause")
    )
    if computed_operation != candidate["policy_operation"]:
        raise UndeclaredPolicyChangeError(
            f"candidate_transition declares policy_operation={candidate['policy_operation']!r} "
            f"but the independently recomputed operation is {computed_operation!r}"
        )

    return candidate


def preview_acceptance_policy_transition(
    store: Any,
    project_id: str,
    baseline_ref: dict[str, str],
    candidate_transition: dict[str, Any],
) -> dict[str, Any]:
    """FD4-C7: the bounded before/after impact preview, computed against the real,
    Store-resolved current effective policy (P82-R1-F1: the canonical, Store-derived adoption
    set, never a caller-supplied list). Makes no Store mutation -- *candidate_transition* need
    not even be committed yet, but is independently detached and verified (P82-R2-F3) before
    it is ever used to build the preview."""

    baseline = resolve_and_verify_baseline(store, project_id, baseline_ref["id"])
    effective_view = resolve_and_verify_effective_policy(store, project_id, baseline_ref)
    verified_candidate = _verify_candidate_transition_for_preview(
        store, project_id, baseline, effective_view, candidate_transition
    )
    preview = engine.build_impact_preview(effective_view, verified_candidate)
    validation.validate_record(preview, _IMPACT_PREVIEW_SCHEMA)
    return preview


def assert_no_undeclared_policy_change_in_payload(
    store: Any,
    project_id: str,
    baseline_ref: dict[str, str],
    payload: dict[str, Any],
) -> None:
    """FD4-C4: refuse fail-closed if *payload* -- a code finding, review round, implementation
    handoff, return-Evidence body, or closure sweep -- mentions any clause_id already known to
    this lineage's own Store-resolved effective policy, without declaring
    ``policy_change: True``."""

    effective_view = resolve_and_verify_effective_policy(store, project_id, baseline_ref)
    known_clause_ids = frozenset(c["clause_id"] for c in effective_view["effective_clauses"])
    engine.assert_no_undeclared_policy_change(payload, known_clause_ids)


__all__ = [
    "adopt_acceptance_policy_transition",
    "assert_no_undeclared_policy_change_in_payload",
    "open_acceptance_policy_baseline",
    "preview_acceptance_policy_transition",
    "propose_acceptance_policy_transition",
    "resolve_and_verify_adoption",
    "resolve_and_verify_baseline",
    "resolve_and_verify_effective_policy",
    "resolve_and_verify_transition",
]
