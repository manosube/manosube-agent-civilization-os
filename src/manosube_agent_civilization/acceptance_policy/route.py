"""The public Store-touching entry points for Acceptance Policy Lineage (FD-0004, Issue #80).

:mod:`.engine` is pure; this module is the only place in the package that ever resolves a
record from the Store or commits one -- through the one shared, already-atomic
``commit_state_transition`` (Structural Review Round 5-R1's ``SINGLE_COMMITTER_REQUIRED``),
never a direct/internal Store mutation of its own (FD4-C10).
"""

from __future__ import annotations

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
    PolicyProvenanceError,
    UnauthorizedPolicyAdoptionError,
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
    effective_view = resolve_and_verify_effective_policy(store, project_id, baseline_ref)
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
        prior_clause_for_diff: dict[str, Any] | None = None
    else:
        prior_ref = prior_effective["provenance_chain"][-1]
        prior_clause_binding = {
            "source": "TRANSITION" if prior_ref["kind"] == _TRANSITION_KIND else "BASELINE",
            "source_ref": prior_ref,
        }
        if prior_ref["kind"] == _TRANSITION_KIND:
            prior_clause_for_diff = resolve_and_verify_transition(
                store, project_id, prior_ref["id"]
            )["proposed_clause"]
        else:
            prior_clause_for_diff = next(
                c for c in baseline["clauses"] if c["clause_id"] == clause_id
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


def adopt_acceptance_policy_transition(
    store: Any,
    project_id: str,
    *,
    governing_issue: int,
    adopted_ref: dict[str, str],
    decision_owner: str,
    source_reference: dict[str, Any],
    decided_at: str,
    committed_at: str,
) -> dict[str, Any]:
    """FD4-C3: commit the identity-bound SHUKOU decision that activates *adopted_ref* -- the
    one baseline genesis or one proposed transition it names. Refuses (before any commit) any
    ``decision_owner`` other than SHUKOU, or a ``source_reference`` not carrying the OWNER
    association -- the only Human Authority this package ever recognises.

    The referenced target is independently Store-resolved and reproduced *before* the adoption
    itself is built, so an adoption can never be minted for a target that does not genuinely
    exist under the identity it names.
    """

    _require_source_reference(source_reference)
    if adopted_ref["kind"] == _BASELINE_KIND:
        resolve_and_verify_baseline(store, project_id, adopted_ref["id"])
    elif adopted_ref["kind"] == _TRANSITION_KIND:
        resolve_and_verify_transition(store, project_id, adopted_ref["id"])
    else:
        raise AcceptancePolicyValidationError(f"unknown adopted_ref.kind: {adopted_ref['kind']!r}")

    adoption = engine.build_adoption(
        project_id=project_id,
        governing_issue=governing_issue,
        adopted_ref=adopted_ref,
        decision_owner=decision_owner,
        source_reference=source_reference,
        decided_at=decided_at,
    )
    validation.validate_record(adoption, _ADOPTION_SCHEMA)
    _commit_one_record(
        store,
        project_id,
        _ADOPTION_KIND,
        adoption["acceptance_policy_adoption_id"],
        adoption,
        committed_at,
    )
    return adoption


def preview_acceptance_policy_transition(
    store: Any,
    project_id: str,
    baseline_ref: dict[str, str],
    candidate_transition: dict[str, Any],
) -> dict[str, Any]:
    """FD4-C7: the bounded before/after impact preview, computed against the real,
    Store-resolved current effective policy (P82-R1-F1: the canonical, Store-derived adoption
    set, never a caller-supplied list). Makes no Store mutation -- *candidate_transition* need
    not even be committed yet."""

    effective_view = resolve_and_verify_effective_policy(store, project_id, baseline_ref)
    preview = engine.build_impact_preview(effective_view, candidate_transition)
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
