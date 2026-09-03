"""Evaluate one development-operation record against the ratified Binding.

The Binding is not a paragraph asking to be respected. It is a predicate over records, and
this module is the predicate. A document that only *describes* the rule is the shape of the
failure it exists to prevent: the protocol already described capability neutrality
correctly, and the description alone did not stop an automated reviewer being placed on the
critical path.

```text
PERMITTED = the ratified Binding allows this exact record
REFUSED   = everything else, including everything unreadable
```

There is no third answer and no default-permit path. An unreadable record is ``REFUSED``
with ``RECORD_UNREADABLE`` rather than skipped, because "we could not tell" and "it is
allowed" are the same outcome to a caller that only checks for a raised exception.
"""

from __future__ import annotations

from typing import Any

from .policy import HUMAN_AUTHORITY, load_policy

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
    if set(record) - keys:
        return "RECORD_CARRIES_UNKNOWN_KEYS"
    if keys - set(record):
        return "RECORD_OMITS_REQUIRED_KEYS"
    return None


def evaluate(record: Any, *, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return ``PERMITTED`` or ``REFUSED`` for one development-operation record."""

    active = load_policy() if policy is None else policy
    if not isinstance(record, dict):
        return _verdict(REFUSED, "RECORD_UNREADABLE")
    record_type = record.get("record_type")
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

    actor, source, target = record["actor"], record["from_state"], record["to_state"]
    reasons: list[str] = []
    if actor not in policy["roles"]:
        reasons.append("UNKNOWN_ACTOR")
    for state, code in ((source, "UNKNOWN_FROM_STATE"), (target, "UNKNOWN_TO_STATE")):
        if state not in policy["handoff_states"]:
            reasons.append(code)
    if reasons:
        return _verdict(REFUSED, *reasons)

    # Named separately from "not a declared transition" because these are the three drifts
    # the Binding exists to stop, and a caller that only sees TRANSITION_NOT_DECLARED cannot
    # tell a boundary crossing from a typo.
    if target in policy["human_only_states"] and actor != HUMAN_AUTHORITY:
        if target == "SHUKOU_MERGED":
            reasons.append("MERGE_AUTHORITY_DRIFT")
        elif target in ("SHUKOU_ACCEPTED", "SHUKOU_REJECTED", "SHUKOU_CHECK"):
            reasons.append("ACCEPTANCE_OWNER_DRIFT")
        reasons.append("HUMAN_ONLY_STATE_ENTERED_BY_NON_HUMAN")

    # The executor's stopping point, stated as a property of the actor rather than of the
    # template it happens to be following. A template can be edited; this cannot.
    if actor != HUMAN_AUTHORITY and source == policy["executor_terminal_state"]:
        reasons.append("EXECUTOR_CONTINUED_PAST_TERMINAL_STATE")

    declared = any(
        transition["from"] == source
        and transition["to"] == target
        and transition["actor"] == actor
        for transition in policy["handoff_transitions"]
    )
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
        if act == "ACCEPTANCE_DECISION":
            reasons.append("ACCEPTANCE_OWNER_DRIFT")
        if act == "MERGE_DECISION":
            reasons.append("MERGE_AUTHORITY_DRIFT")
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

    finding, disposition, adoption = (
        record["finding"],
        record["requested_disposition"],
        record["adoption"],
    )
    finding_unreadable = _closed(finding, _FINDING_FIELDS)
    if finding_unreadable:
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
    adoption_unreadable = _closed(adoption, _ADOPTION_FIELDS)
    if adoption_unreadable:
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
