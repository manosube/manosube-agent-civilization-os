"""Evaluate one development-operation record against the ratified Binding.

The Binding is not a paragraph asking to be respected. It is a predicate over records, and
this module is the predicate. A document that only *describes* the rule is the shape of the
failure it exists to prevent: the delivery protocol already described capability neutrality
correctly, and the description alone did not stop an automated reviewer being placed on the
critical path.

```text
PERMITTED = the ratified Binding allows this exact record
REFUSED   = everything else, including everything unreadable
```

There is no third answer and no default-permit path. **Nothing raises.** An unreadable record
answers ``REFUSED`` with a documented reason code rather than leaking a ``TypeError``, because
a caller that distinguishes verdicts and a caller that catches exceptions are different
callers, and the one that only reads verdicts must not be told "allowed" by silence.
"""

from __future__ import annotations

from typing import Any

from .policy import (
    EXECUTOR_TERMINAL_STATE,
    FINAL_ACCEPTANCE_STATE,
    HUMAN_AUTHORITY,
    MERGE_OPERATION_STATE,
    MERGE_RECOMMENDATION_STATE,
    load_policy,
)

PERMITTED = "PERMITTED"
REFUSED = "REFUSED"

#: Every record type this guard understands. A record naming any other type is refused,
#: never waved through: an unrecognised record is precisely where an unreviewed route hides.
RECORD_TYPES: frozenset[str] = frozenset(
    {
        "HANDOFF_TRANSITION",
        "ACTOR_ACTION",
        "EXTERNAL_FINDING_DISPOSITION",
    }
)

_HANDOFF_KEYS: frozenset[str] = frozenset({"record_type", "actor", "from_state", "to_state"})
_ACTION_KEYS: frozenset[str] = frozenset({"record_type", "actor", "action"})
_FINDING_KEYS: frozenset[str] = frozenset(
    {"record_type", "actor", "finding", "requested_disposition", "adoption"}
)
_FINDING_FIELDS: frozenset[str] = frozenset({"observation_id", "source", "status"})
_ADOPTION_FIELDS: frozenset[str] = frozenset({"authority", "observation_id", "disposition"})


def _verdict(decision: str, *reason_codes: str) -> dict[str, Any]:
    return {"decision": decision, "reason_codes": sorted(set(reason_codes))}


def _closed(record: Any, keys: frozenset[str]) -> str | None:
    """Return a reason code when *record* is not exactly *keys*, else ``None``."""

    if not isinstance(record, dict):
        return "RECORD_UNREADABLE"
    if any(not isinstance(key, str) for key in record):
        return "RECORD_UNREADABLE"
    if set(record) - keys:
        return "RECORD_CARRIES_UNKNOWN_KEYS"
    if keys - set(record):
        return "RECORD_OMITS_REQUIRED_KEYS"
    return None


def _scalars(record: dict[str, Any], *fields: str) -> str | None:
    """Return a reason code unless every named field holds a string.

    JSON permits an array or an object anywhere a string belongs, and those are unhashable:
    ``["CLAUDE_CODE"] in frozenset(...)`` raises ``TypeError`` instead of answering ``False``.
    Every membership test below runs after this, so an ill-typed value is a **verdict** and
    not an exception.
    """

    for field in fields:
        if not isinstance(record.get(field), str):
            return "RECORD_FIELD_IS_NOT_A_SCALAR"
    return None


def evaluate(record: Any, *, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return ``PERMITTED`` or ``REFUSED`` for one development-operation record."""

    active = load_policy() if policy is None else policy
    if not isinstance(record, dict):
        return _verdict(REFUSED, "RECORD_UNREADABLE")
    ill_typed = _scalars(record, "record_type")
    if ill_typed:
        return _verdict(REFUSED, ill_typed)
    record_type = record["record_type"]
    if record_type not in RECORD_TYPES:
        return _verdict(REFUSED, "UNKNOWN_RECORD_TYPE")
    if record_type == "HANDOFF_TRANSITION":
        return _evaluate_handoff(record, active)
    if record_type == "ACTOR_ACTION":
        return _evaluate_action(record, active)
    return _evaluate_finding(record, active)


def _evaluate_handoff(record: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """One step of the handoff state machine, taken by one actor."""

    unreadable = _closed(record, _HANDOFF_KEYS)
    if unreadable:
        return _verdict(REFUSED, unreadable)
    ill_typed = _scalars(record, "actor", "from_state", "to_state")
    if ill_typed:
        return _verdict(REFUSED, ill_typed)

    actor, source, target = record["actor"], record["from_state"], record["to_state"]
    reasons: list[str] = []
    if actor not in policy["roles"]:
        reasons.append("UNKNOWN_ACTOR")
    for state, code in ((source, "UNKNOWN_FROM_STATE"), (target, "UNKNOWN_TO_STATE")):
        if state not in policy["handoff_states"]:
            reasons.append(code)
    if reasons:
        return _verdict(REFUSED, *reasons)

    # Named separately from "not a declared transition" because these are the drifts the
    # Binding exists to stop, and a caller that only sees TRANSITION_NOT_DECLARED cannot tell
    # a boundary crossing from a typo.
    if target in policy["human_only_states"] and actor != HUMAN_AUTHORITY:
        if target == MERGE_OPERATION_STATE:
            reasons.append("MERGE_OPERATION_DRIFT")
        else:
            reasons.append("FINAL_ACCEPTANCE_DRIFT")
        reasons.append("HUMAN_ONLY_STATE_ENTERED_BY_NON_HUMAN")

    if target in policy["advisor_only_states"] and actor != policy["structural_review_owner"]:
        if target == MERGE_RECOMMENDATION_STATE:
            reasons.append("MERGE_READINESS_RECOMMENDATION_DRIFT")
        else:
            reasons.append("STRUCTURAL_REVIEW_DRIFT")
        reasons.append("ADVISOR_ONLY_STATE_ENTERED_BY_NON_ADVISOR")

    # The executor's stopping point, stated as a property of the actor rather than of the
    # template it happens to be following. A template can be edited; this cannot.
    if actor != HUMAN_AUTHORITY and source == EXECUTOR_TERMINAL_STATE and actor != policy[
        "structural_review_owner"
    ]:
        reasons.append("EXECUTOR_CONTINUED_PAST_TERMINAL_STATE")

    # Two orderings Decision 0002 names explicitly. Both are already implied by the declared
    # transition set, and both are called out so the refusal says *which* step was skipped.
    if target == MERGE_RECOMMENDATION_STATE and source != "STRUCTURAL_REVIEW_PASS":
        reasons.append("STRUCTURAL_REVIEW_SKIPPED")
    if target == MERGE_OPERATION_STATE and source != FINAL_ACCEPTANCE_STATE:
        reasons.append("MERGE_WITHOUT_FINAL_ACCEPTANCE")

    declared = (actor, source, target) in {
        (transition["actor"], transition["from"], transition["to"])
        for transition in policy["handoff_transitions"]
    }
    if not declared:
        reasons.append("TRANSITION_NOT_DECLARED")
    if reasons:
        return _verdict(REFUSED, *reasons)
    return _verdict(PERMITTED, "DECLARED_TRANSITION")


def _evaluate_action(record: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """One act by one participant, against what that participant may and may not do."""

    unreadable = _closed(record, _ACTION_KEYS)
    if unreadable:
        return _verdict(REFUSED, unreadable)
    ill_typed = _scalars(record, "actor", "action")
    if ill_typed:
        return _verdict(REFUSED, ill_typed)

    actor, act = record["actor"], record["action"]
    role = policy["roles"].get(actor)
    if role is None:
        return _verdict(REFUSED, "UNKNOWN_ACTOR")

    reasons: list[str] = []
    if act == "REQUEST_AUTOMATED_EXTERNAL_REVIEW" and not policy[
        "automated_review_trigger_allowed"
    ]:
        reasons.append("AUTOMATED_REVIEW_TRIGGER_PROHIBITED")
    if act in role["must_not"]:
        reasons.append("ROLE_DRIFT")
        # Decision 0002 separates the three the previous version collapsed into one word.
        if act == "FINAL_ACCEPTANCE_DECISION":
            reasons.append("FINAL_ACCEPTANCE_DRIFT")
        if act == "MERGE_OPERATION":
            reasons.append("MERGE_OPERATION_DRIFT")
        if act == "MERGE_READINESS_RECOMMENDATION":
            reasons.append("MERGE_READINESS_RECOMMENDATION_DRIFT")
        if act == "STRUCTURAL_REVIEW":
            reasons.append("STRUCTURAL_REVIEW_DRIFT")
    if reasons:
        return _verdict(REFUSED, *reasons)
    if act in role["may"]:
        return _verdict(PERMITTED, "ACTION_WITHIN_ROLE")
    # Neither permitted nor forbidden by name. Silence is not permission -- the same rule
    # Authority applies to a missing rule (`AUTHORITY_CONTRACT.md` §1), for the same reason.
    return _verdict(REFUSED, "ACTION_NOT_GRANTED_TO_ROLE")


def _evaluate_finding(record: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """What an external observation is being turned into, and on whose authority.

    This is the gate the incident crossed. A bot finding is an observation; turning it into
    an instruction, a blocker, an acceptance failure or a work unit is a Human decision, and
    the adoption record must be bound to the exact observation and the exact disposition it
    authorizes.
    """

    unreadable = _closed(record, _FINDING_KEYS)
    if unreadable:
        return _verdict(REFUSED, unreadable)
    ill_typed = _scalars(record, "actor", "requested_disposition")
    if ill_typed:
        return _verdict(REFUSED, ill_typed)

    finding, disposition, adoption = (
        record["finding"],
        record["requested_disposition"],
        record["adoption"],
    )
    if _closed(finding, _FINDING_FIELDS):
        return _verdict(REFUSED, "FINDING_UNREADABLE")
    if _scalars(finding, "observation_id", "source", "status"):
        return _verdict(REFUSED, "FINDING_UNREADABLE")

    if finding["source"] not in policy["external_finding_sources"]:
        return _verdict(REFUSED, "UNKNOWN_FINDING_SOURCE")
    if finding["status"] != policy["external_finding_initial_status"]:
        # A finding that arrives already claiming to be verified is claiming its own
        # adoption. The claim is the thing under review; it cannot also be the evidence.
        return _verdict(REFUSED, "FINDING_ASSERTS_ITS_OWN_VERIFICATION")

    forbidden = policy["external_finding_forbidden_dispositions_without_adoption"]
    if disposition not in forbidden:
        if disposition == "PRESENT_TO_HUMAN":
            return _verdict(PERMITTED, "OBSERVATION_PRESENTED_NOT_ADOPTED")
        return _verdict(REFUSED, "UNKNOWN_DISPOSITION")

    if adoption is None:
        return _verdict(REFUSED, "BOT_FINDING_AUTO_ADOPTION", "EXPLICIT_HUMAN_ADOPTION_ABSENT")
    if _closed(adoption, _ADOPTION_FIELDS):
        return _verdict(REFUSED, "ADOPTION_UNREADABLE")
    if _scalars(adoption, "authority", "observation_id", "disposition"):
        return _verdict(REFUSED, "ADOPTION_UNREADABLE")
    if adoption["authority"] != policy["external_finding_adoption_authority"]:
        return _verdict(REFUSED, "ADOPTION_BY_NON_HUMAN_AUTHORITY")
    # Bound to *this* observation and *this* disposition. An adoption that floats free is an
    # adoption that a later, different finding can be filed under.
    if adoption["observation_id"] != finding["observation_id"]:
        return _verdict(REFUSED, "ADOPTION_NOT_BOUND_TO_THIS_OBSERVATION")
    if adoption["disposition"] != disposition:
        return _verdict(REFUSED, "ADOPTION_NOT_BOUND_TO_THIS_DISPOSITION")
    return _verdict(PERMITTED, "HUMAN_ADOPTED_OBSERVATION")


def prohibited_trigger_in(text: str, *, policy: dict[str, Any] | None = None) -> list[str]:
    """Return every prohibited automated-review trigger appearing in *text*.

    Used to keep the executable handoff and PR-completion templates clean. This is a text
    check and is deliberately the *weakest* guard in this module -- it is why the record
    evaluators above exist, and it is not what the conformance boundary rests on.
    """

    active = load_policy() if policy is None else policy
    lowered = text.lower()
    return [
        trigger
        for trigger in active["prohibited_automated_review_triggers"]
        if trigger.lower() in lowered
    ]
