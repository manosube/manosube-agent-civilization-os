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

from .errors import ExecutorSelectionError
from .executor_selection import EXECUTOR_SELECTION_ADMITTED, evaluate_executor_selection
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

#: Every reason code :func:`evaluate` can actually emit, declared explicitly rather than
#: inferred from source shape (GAR-R2-F2, Issue #53 comment 5565703135). The sole source of
#: truth the route-drift guard in ``test_active_document_terminal_state.py`` and this
#: module's own reachability tests read from -- ``test_evaluation_reason_code_reachability.py``
#: statically proves this set is neither wider nor narrower than what this module's own
#: source can actually emit.
EMITTED_REASON_CODES: frozenset[str] = frozenset(
    {
        "RECORD_UNREADABLE",
        "RECORD_FIELD_IS_NOT_A_SCALAR",
        "UNKNOWN_RECORD_TYPE",
        "RECORD_CARRIES_UNKNOWN_KEYS",
        "RECORD_OMITS_REQUIRED_KEYS",
        "UNKNOWN_ACTOR",
        "UNKNOWN_FROM_STATE",
        "UNKNOWN_TO_STATE",
        "MERGE_OPERATION_DRIFT",
        "FINAL_ACCEPTANCE_DRIFT",
        "HUMAN_ONLY_STATE_ENTERED_BY_NON_HUMAN",
        "MERGE_READINESS_RECOMMENDATION_DRIFT",
        "STRUCTURAL_REVIEW_DRIFT",
        "ADVISOR_ONLY_STATE_ENTERED_BY_NON_ADVISOR",
        "EXECUTOR_CONTINUED_PAST_TERMINAL_STATE",
        "STRUCTURAL_REVIEW_SKIPPED",
        "MERGE_WITHOUT_FINAL_ACCEPTANCE",
        "TRANSITION_NOT_DECLARED",
        "DECLARED_TRANSITION",
        "AUTOMATED_REVIEW_TRIGGER_PROHIBITED",
        "ROLE_DRIFT",
        "ACTION_WITHIN_ROLE",
        "ACTION_NOT_GRANTED_TO_ROLE",
        "FINDING_UNREADABLE",
        "UNKNOWN_FINDING_SOURCE",
        "FINDING_ASSERTS_ITS_OWN_VERIFICATION",
        "OBSERVATION_PRESENTED_NOT_ADOPTED",
        "UNKNOWN_DISPOSITION",
        "BOT_FINDING_AUTO_ADOPTION",
        "EXPLICIT_HUMAN_ADOPTION_ABSENT",
        "ADOPTION_UNREADABLE",
        "ADOPTION_BY_NON_HUMAN_AUTHORITY",
        "ADOPTION_NOT_BOUND_TO_THIS_OBSERVATION",
        "ADOPTION_NOT_BOUND_TO_THIS_DISPOSITION",
        "HUMAN_ADOPTED_OBSERVATION",
        "EXECUTOR_SELECTION_REQUIRED_AND_ABSENT",
        "EXECUTOR_SELECTION_UNREADABLE",
        "EXECUTOR_SELECTION_PROVIDER_MISMATCH",
        "EXECUTOR_SELECTION_NOT_ADMITTED",
        "ACTION_NOT_PERMITTED_BY_SELECTION",
        "INVOKED_PATHS_REQUIRED_AND_ABSENT",
        "PATH_NOT_PERMITTED_BY_SELECTION",
    }
)

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

#: Optional in both closed shapes above (Decision 0003, Issue #102 Structural Review Round
#: 1, I102-SR1-F1): a non-default eligible executor provider's action or handoff transition
#: must carry one to be admitted at all; the ratified default needs none, so every historical
#: and future Claude Code record keeps its exact three/four-key shape unchanged.
_EXECUTOR_SELECTION_KEY = "executor_selection"

#: Optional in ``ACTOR_ACTION`` only (Structural Review Round 2, I102-SR1 follow-up, PR #104
#: comment 5930926992): the actual invoked path scope of the action, required and checked
#: against the grant's own ``permitted_paths`` for exactly the same non-default-provider
#: records that require ``executor_selection``. Round 1 recorded this as an honest, stated
#: non-claim ("no record shape carries a path"); Round 2 correctly found that recording a
#: limitation does not fulfill an adopted obligation, so this closes it by giving the record
#: shape the field it was missing, rather than by widening what this evaluator claims to
#: prove without the evidence to back it.
_PATHS_KEY = "paths"

#: One representative action per handoff target state a non-default eligible provider can
#: reach (Structural Review Round 2, I102-SR1 follow-up): ``permitted_actions`` bounds what a
#: grant authorizes, and a transition is itself the claim that the bounded work was done, so
#: each target is mapped to the capability it represents and checked the same way an
#: ``ACTOR_ACTION`` naming that capability would be. Built from the ratified transition
#: template (`policy._EXECUTOR_TRANSITION_TEMPLATE`) rather than listed by hand a second time,
#: so a future transition added there is covered here without anyone remembering this map.
_TRANSITION_ACTION: dict[str, str] = {
    "CLAUDE_CODE_IMPLEMENTATION_COMPLETE": "IMPLEMENTATION",
    "EXECUTOR_SELF_REVIEW_COMPLETE": "EXECUTOR_SELF_REVIEW",
    "GITHUB_PR_READY": "PR_PREPARATION",
    EXECUTOR_TERMINAL_STATE: "PR_PREPARATION",
    # Returning to IMPLEMENTATION_IN_PROGRESS from a correction, an evidence request, or a
    # Human rejection is the executor taking on implementation work again, not a no-op.
    "IMPLEMENTATION_IN_PROGRESS": "IMPLEMENTATION",
}


def _verdict(decision: str, *reason_codes: str) -> dict[str, Any]:
    return {"decision": decision, "reason_codes": sorted(set(reason_codes))}


def _closed(
    record: Any, keys: frozenset[str], *, optional: frozenset[str] = frozenset()
) -> str | None:
    """Return a reason code when *record* is not exactly *keys*, plus zero or more of
    *optional*, else ``None``.

    *optional* exists for exactly one key (``executor_selection``) and exactly one reason
    (Decision 0003): a non-default eligible executor provider's record must carry it, but
    the ratified default must not be required to, so every historical and future Claude Code
    record keeps the exact required shape it always had.
    """

    if not isinstance(record, dict):
        return "RECORD_UNREADABLE"
    if any(not isinstance(key, str) for key in record):
        return "RECORD_UNREADABLE"
    if set(record) - keys - optional:
        return "RECORD_CARRIES_UNKNOWN_KEYS"
    if keys - set(record):
        return "RECORD_OMITS_REQUIRED_KEYS"
    return None


def _requires_executor_selection(actor: str, policy: dict[str, Any]) -> bool:
    """Whether *actor* must carry an admitted :mod:`.executor_selection` record to act.

    True for exactly the eligible executor providers other than the ratified default
    (Decision 0003, Issue #102 Structural Review Round 1, I102-SR1-F1). The default itself
    needs no selection record -- that is what keeps it backward compatible -- but every other
    eligible name must prove, through this record, that it is the one actually selected for
    this exact work unit before the role-membership check below can ever be reached.
    """

    providers = policy.get("executor_providers")
    default = policy.get("executor_provider_default")
    return isinstance(providers, list) and actor in providers and actor != default


def _check_executor_selection(
    selection: Any, actor: str, *, action: str | None = None
) -> str | None:
    """Return a reason code unless *selection* is an admitted grant naming *actor*.

    Eligible provider membership is not execution authority (``policy`` module docstring,
    `03_BINDING/CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md` §10.1): this is the connection
    between that stated boundary and the actual admission route, which previously existed
    only as a module nothing called.

    *action* is passed for both record types (Structural Review Round 2 completed what Round
    1's follow-up handoff, comment 5927538575, started): an admitted selection grants a
    *bounded* set of actions, not every action the role's own ``may`` list permits in
    general, so the requested action or represented transition capability is checked against
    the grant's own ``permitted_actions`` in addition to the role check that follows.
    ``_evaluate_action`` passes the record's own ``action``; ``_evaluate_handoff`` passes the
    target state's represented capability via ``_TRANSITION_ACTION``.

    ``permitted_paths`` is **not** checked in this helper -- ``_evaluate_action`` checks it
    directly, against the record's own ``paths`` field, because that check needs the
    caller-supplied invoked paths this helper is never given, not anything this helper could
    answer from *selection* and *actor* alone. Round 1 recorded the absence of a path
    carrier as an honest non-claim; Round 2 correctly found that recording a limitation does
    not fulfill an adopted obligation, and the fix is the field, not a wider claim here.
    """

    if selection is None:
        return "EXECUTOR_SELECTION_REQUIRED_AND_ABSENT"
    try:
        decision = evaluate_executor_selection(selection)
    except ExecutorSelectionError:
        return "EXECUTOR_SELECTION_UNREADABLE"
    if decision["selected_executor_provider"] != actor:
        return "EXECUTOR_SELECTION_PROVIDER_MISMATCH"
    if decision["decision"] != EXECUTOR_SELECTION_ADMITTED:
        return "EXECUTOR_SELECTION_NOT_ADMITTED"
    if action is not None and action not in selection.get("permitted_actions", ()):
        return "ACTION_NOT_PERMITTED_BY_SELECTION"
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

    unreadable = _closed(record, _HANDOFF_KEYS, optional=frozenset({_EXECUTOR_SELECTION_KEY}))
    if unreadable:
        return _verdict(REFUSED, unreadable)
    ill_typed = _scalars(record, "actor", "from_state", "to_state")
    if ill_typed:
        return _verdict(REFUSED, ill_typed)

    actor, source, target = record["actor"], record["from_state"], record["to_state"]
    reasons: list[str] = []
    if actor not in policy["roles"]:
        reasons.append("UNKNOWN_ACTOR")
    # Written as two direct checks rather than a loop over (state, code) pairs so each
    # reason code reaches its caller as a literal argument to .append() -- the one AST shape
    # GAR-R2-F2's declared-surface proof (EMITTED_REASON_CODES, below) can recognize without
    # tracing a code through a loop variable.
    if source not in policy["handoff_states"]:
        reasons.append("UNKNOWN_FROM_STATE")
    if target not in policy["handoff_states"]:
        reasons.append("UNKNOWN_TO_STATE")
    if reasons:
        return _verdict(REFUSED, *reasons)

    # Checked after the shape/identity gate above (actor is now known to be a real role) but
    # *before* the early return below, so a missing or refused selection accumulates alongside
    # whatever drift-specific codes the same record also triggers (I102-SR1, PR #104 Round 1
    # correction) -- a non-default provider's self-merge attempt without a selection is still
    # reported with MERGE_OPERATION_DRIFT, not only EXECUTOR_SELECTION_REQUIRED_AND_ABSENT.
    #
    # The target state's own represented action is checked against the grant's
    # permitted_actions (Structural Review Round 2, I102-SR1 follow-up): Round 1 wired this
    # for ACTOR_ACTION only, so a grant naming only TEST_EXECUTION still permitted every
    # HANDOFF_TRANSITION, including into CLAUDE_CODE_IMPLEMENTATION_COMPLETE.
    if _requires_executor_selection(actor, policy):
        selection_reason = _check_executor_selection(
            record.get(_EXECUTOR_SELECTION_KEY), actor, action=_TRANSITION_ACTION.get(target)
        )
        if selection_reason:
            reasons.append(selection_reason)

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

    unreadable = _closed(
        record, _ACTION_KEYS, optional=frozenset({_EXECUTOR_SELECTION_KEY, _PATHS_KEY})
    )
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
    if _requires_executor_selection(actor, policy):
        selection = record.get(_EXECUTOR_SELECTION_KEY)
        selection_reason = _check_executor_selection(selection, actor, action=act)
        if selection_reason:
            reasons.append(selection_reason)
        # The invoked path scope, required and checked against the grant's own
        # permitted_paths (Structural Review Round 2, I102-SR1 follow-up): an admitted
        # selection bounds which paths it covers, and an action naming none is refused
        # rather than silently exempted from that bound.
        paths = record.get(_PATHS_KEY)
        if not isinstance(paths, list) or not paths or not all(
            isinstance(path, str) and path for path in paths
        ):
            reasons.append("INVOKED_PATHS_REQUIRED_AND_ABSENT")
        elif selection_reason is None:
            permitted_paths = selection.get("permitted_paths", []) if isinstance(
                selection, dict
            ) else []
            if not all(path in permitted_paths for path in paths):
                reasons.append("PATH_NOT_PERMITTED_BY_SELECTION")
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
