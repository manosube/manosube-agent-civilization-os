"""Reconstruct the canonical ``candidate_claim_evaluation_event`` series G21 must trust.

``CLOSURE_POLICY.md``'s G21 section (and its Phase 7 Round 2 structural-review escalation,
R2-F8) requires more than replaying backward from a binding's declared head: "Atomic
Reflow直前に各evaluation_series_idのappend-only event chainをrevision 0から再構築し、
最新head eventを解決する。bindingのevaluation_head_event_refがその最新headとexact一致し
...古いSATISFIED recordを直接参照して最新head解決を省略してはならない。" A caller who can
write a binding can point its declared head at *any* prior event in the series -- including
one a later ``REVOKED`` or ``NOT_SATISFIED`` event has since superseded -- so the only
correct check is: reconstruct the *whole* series, find its one true latest event, and
require the binding to match that event exactly, not merely to name something that once
existed.

Both identities here use the exact domain-separated profile ``CLOSURE_POLICY.md`` gives --
the same kind of Policy-fixed exception :func:`~manosube_agent_civilization.reflow.identity.
after_state_candidate_id` already is, not the repo-wide undecorated
:func:`~manosube_agent_civilization.difference.canonical.content_address` convention.
"""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .errors import ReflowValidationError

_EVENT_DOMAIN_SEPARATOR = b"MANOSUBE:CANDIDATE_CLAIM_EVALUATION_EVENT:0.1:"
_SERIES_DOMAIN_SEPARATOR = b"MANOSUBE:CANDIDATE_CLAIM_EVALUATION_SERIES:0.1:"


def candidate_claim_evaluation_binding_id(binding: dict[str, Any]) -> str:
    """R3-F2: ``CLOSURE_POLICY.md`` line 696 -- "Binding IDと検証規則はG19 bindingと同じ
    canonical profileを使用し、prefixだけを`CAND-CLAIM-EVAL-`とする" -- the *identical*
    ``MANOSUBE-CANDIDATE-EVALUATION-BINDING-SHA256-0.1`` derivation
    :func:`~manosube_agent_civilization.reflow.invariant_registry.
    candidate_invariant_evaluation_binding_id` already implements for G19's own binding,
    with only the id prefix swapped: every field except ``binding_id`` itself, canonical
    JSON UTF-8, SHA-256, uppercase hex, no domain separator (the contract states none for
    this one profile, unlike the event/series ids above -- see that function's own
    docstring for why the absence is read literally, not filled in).
    """

    closed = {key: value for key, value in binding.items() if key != "binding_id"}
    digest = hashlib.sha256(canonical_json_bytes(closed)).hexdigest()
    return "CAND-CLAIM-EVAL-" + digest.upper()


def candidate_claim_evaluation_event_id(event: dict[str, Any]) -> str:
    """Return the content address of a ``candidate_claim_evaluation_event`` record."""

    payload = {key: value for key, value in event.items() if key != "event_id"}
    digest = hashlib.sha256(_EVENT_DOMAIN_SEPARATOR + canonical_json_bytes(payload)).hexdigest()
    return "CAND-CLAIM-EVT-" + digest.upper()


def candidate_claim_evaluation_series_id(
    *,
    difference_id: str,
    policy_ref: dict[str, Any],
    candidate_id: str,
    required_claim_ref: dict[str, Any],
) -> str:
    """Return the one series identity ``difference_id + policy_ref + candidate_id +
    required_claim_ref`` implies -- the same four values, so the same Difference and
    Claim under a different Policy (or the reverse) is a different series by
    construction, and one series' head update can never stale-close another's.
    """

    payload = {
        "difference_id": difference_id,
        "policy_ref": policy_ref,
        "candidate_id": candidate_id,
        "required_claim_ref": required_claim_ref,
    }
    digest = hashlib.sha256(_SERIES_DOMAIN_SEPARATOR + canonical_json_bytes(payload)).hexdigest()
    return "CAND-CLAIM-SERIES-" + digest.upper()


def reconstruct_claim_series(
    events: list[dict[str, Any]],
    *,
    difference_id: str,
    policy_ref: dict[str, Any],
    candidate_id: str,
    required_claim_ref: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return the complete, contiguous, fork-free event chain for one series, from its
    unique latest event back to revision 0 -- head first.

    *events* is the whole pool a caller supplies; only events whose own declared
    ``evaluation_series_id`` equals the identity this series' own fields recompute are
    admitted (a foreign event is silently excluded from the pool, not merged into it). Of
    the admitted events: each must recompute its own content address (an edited body is
    refused); each must belong to this exact Difference/Policy/candidate/Claim (a event
    from a same-series-id-but-different-body claim never validates -- see
    :func:`candidate_claim_evaluation_series_id`); revision numbers must run 0..N with no
    gap and no duplicate (two different bodies at one revision is a fork, refused); and
    each non-zero revision's ``predecessor_event_ref`` must name exactly the previous
    revision's own recomputed identity (refusing both a broken chain and an "unconsumed"
    later event dangling off a revision nothing in the walked chain reaches).
    """

    expected_series_id = candidate_claim_evaluation_series_id(
        difference_id=difference_id,
        policy_ref=policy_ref,
        candidate_id=candidate_id,
        required_claim_ref=required_claim_ref,
    )
    by_revision: dict[int, dict[str, Any]] = {}
    for event in events:
        if event.get("evaluation_series_id") != expected_series_id:
            continue
        identity = candidate_claim_evaluation_event_id(event)
        if event.get("event_id") != identity:
            raise ReflowValidationError(
                "candidate_claim_evaluation_event fails its own content address: "
                f"{event.get('event_id')!r}"
            )
        if event["difference_id"] != difference_id:
            raise ReflowValidationError(
                "claim evaluation series belongs to a different Difference"
            )
        if event["policy_ref"] != policy_ref:
            raise ReflowValidationError("claim evaluation series belongs to a different Policy")
        if event["candidate_id"] != candidate_id:
            raise ReflowValidationError(
                "claim evaluation series belongs to a different candidate"
            )
        if event["required_claim_ref"] != required_claim_ref:
            raise ReflowValidationError(
                "claim evaluation series belongs to a different required Claim"
            )
        revision = event["event_revision"]
        if revision in by_revision and by_revision[revision] != event:
            raise ReflowValidationError(
                f"claim evaluation series forks at revision {revision}: two different "
                "events declare the same revision"
            )
        by_revision[revision] = event

    if not by_revision:
        raise ReflowValidationError(
            f"claim evaluation series {expected_series_id} has no admitted events"
        )
    max_revision = max(by_revision)
    if sorted(by_revision) != list(range(max_revision + 1)):
        raise ReflowValidationError(
            f"claim evaluation series {expected_series_id} is not contiguous from revision 0"
        )

    chain: list[dict[str, Any]] = []
    for revision in range(max_revision, -1, -1):
        event = by_revision[revision]
        predecessor_ref = event["predecessor_event_ref"]
        if revision == 0:
            if predecessor_ref is not None:
                raise ReflowValidationError(
                    "claim evaluation event_revision 0 must carry a null predecessor_event_ref"
                )
        else:
            if predecessor_ref is None:
                raise ReflowValidationError(
                    f"claim evaluation event_revision {revision} carries a null "
                    "predecessor_event_ref"
                )
            expected_predecessor_id = candidate_claim_evaluation_event_id(by_revision[revision - 1])
            if predecessor_ref.get("id") != expected_predecessor_id:
                raise ReflowValidationError(
                    f"claim evaluation series is non-contiguous at revision {revision}: "
                    "predecessor_event_ref does not name the true revision "
                    f"{revision - 1} event"
                )
        chain.append(event)
    return chain


def verify_claim_binding_matches_latest(
    binding: dict[str, Any], head_event: dict[str, Any]
) -> None:
    """Fail closed unless *binding* matches *head_event* exactly on every field both
    carry -- head reference, Completion Record reference and fingerprint, status,
    candidate, Policy, and time. A binding still naming an event that was once the true
    latest, before a later event superseded it, fails here exactly as one naming a
    fabricated head would: *head_event* is only ever the series' one current tip.
    """

    if binding["evaluation_head_event_ref"].get("id") != head_event["event_id"]:
        raise ReflowValidationError(
            "binding's evaluation_head_event_ref does not name this series' true latest event"
        )
    if binding["completion_record_ref"] != head_event["completion_record_ref"]:
        raise ReflowValidationError(
            "binding's completion_record_ref does not match the latest event"
        )
    if binding["evaluation_record_fingerprint"] != head_event["completion_record_fingerprint"]:
        raise ReflowValidationError(
            "binding's evaluation_record_fingerprint does not match the latest event's "
            "completion_record_fingerprint"
        )
    if binding["evaluation_status"] != head_event["evaluation_status"]:
        raise ReflowValidationError(
            "binding's evaluation_status does not match the latest event's evaluation_status"
        )
    if binding["candidate_id"] != head_event["candidate_id"]:
        raise ReflowValidationError("binding's candidate_id does not match the latest event")
    if binding.get("policy_ref") != head_event["policy_ref"]:
        raise ReflowValidationError("binding's policy_ref does not match the latest event")
    if binding["evaluated_at"] != head_event["recorded_at"]:
        raise ReflowValidationError(
            "binding's evaluated_at does not match the latest event's recorded_at"
        )


def resolve_claim_binding(
    events: list[dict[str, Any]],
    binding: dict[str, Any],
    *,
    difference_id: str,
) -> list[dict[str, Any]]:
    """Reconstruct *binding*'s series, verify the binding matches its true latest event,
    and return the complete validated chain (head first) -- the set a caller must persist
    for every field this binding is now trusted on to stay reference-resolvable.

    R3-F2: two checks a Round 2 caller could still forge without detection, closed here --
    a fabricated ``binding_id`` (:func:`candidate_claim_evaluation_binding_id`) and a
    fabricated ``evaluation_series_id`` naming a *different* series than the one the
    binding's own ``difference_id``/``policy_ref``/``candidate_id``/``required_claim_ref``
    recompute (:func:`candidate_claim_evaluation_series_id`) -- both were previously
    accepted at face value because ``reconstruct_claim_series`` only ever *used* the
    recomputed series id to filter the event pool, never compared it back against the
    binding's own declared field.
    """

    if binding.get("difference_id") != difference_id:
        raise ReflowValidationError("binding's difference_id does not match this Reflow's Difference")
    if binding.get("binding_id") != candidate_claim_evaluation_binding_id(binding):
        raise ReflowValidationError(
            "binding's binding_id does not match its own content-addressed derivation"
        )
    policy_ref = binding.get("policy_ref")
    if not isinstance(policy_ref, dict):
        raise ReflowValidationError("binding's policy_ref must be an object")
    expected_series_id = candidate_claim_evaluation_series_id(
        difference_id=difference_id,
        policy_ref=policy_ref,
        candidate_id=binding["candidate_id"],
        required_claim_ref=binding["required_claim_ref"],
    )
    if binding.get("evaluation_series_id") != expected_series_id:
        raise ReflowValidationError(
            "binding's evaluation_series_id does not match the series its own "
            "difference_id/policy_ref/candidate_id/required_claim_ref recompute"
        )
    chain = reconstruct_claim_series(
        events,
        difference_id=difference_id,
        policy_ref=policy_ref,
        candidate_id=binding["candidate_id"],
        required_claim_ref=binding["required_claim_ref"],
    )
    verify_claim_binding_matches_latest(binding, chain[0])
    return chain
