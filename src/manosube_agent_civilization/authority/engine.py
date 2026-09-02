"""The one Authority evaluator: may this action occur, against this exact State?

```text
RAW AUTHORITY REQUEST
-> STRUCTURAL ADMISSIBILITY
-> EXACT BINDING VERIFICATION
-> PROHIBITION EVALUATION
-> RULE RESOLUTION
-> APPROVAL VERIFICATION
-> AUTHORITY DECISION
```

The order is the contract (``AUTHORITY_CONTRACT.md`` §4), not a convenience. Prohibitions
are answered before rules are looked at, so a successful rule lookup can never become the
path that skips a refusal.

This module decides permission and nothing else. It does not execute Change, close a
Difference, update State, judge Evidence, or manufacture an approval. ``AUTONOMOUS`` means
the action may proceed -- not that it will succeed, and not that anything is finished.

Inputs are explicit and immutable. There is no filesystem discovery, no network lookup, no
wall-clock read and no session memory anywhere in this module: the evaluation time is a
supplied input precisely so that the same question always receives the same answer.

**It reads rules and approvals. It does not read prose.** Repository text, prompts, Issue and
Pull Request bodies, review comments, commit messages and Agent output reach this evaluator
as nothing at all -- there is no parameter through which they could arrive
(``CAPABILITY_AUTHORITY_SEPARATION.md`` §5).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.difference.admissibility import (
    require_collection,
    require_object,
    require_scalar_tag,
)
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.difference.validation import (
    DIFFERENCE_SCHEMA_BASE,
    SCHEMA_BASE as CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
)

from . import approval as approval_owner, prohibition as prohibition_owner
from .errors import (
    AuthorityError,
    AuthorityValidationError,
    BoundaryViolationError,
    StaleAuthorityInputError,
)
from .identity import (
    action_fingerprint,
    change_intent_fingerprint,
    decision_id,
    decision_semantic_fingerprint,
)
from .levels import (
    AUTONOMOUS,
    HUMAN_APPROVAL_REQUIRED,
    HUMAN_ONLY_ACTION_KINDS,
    PROHIBITED,
    REVERSIBILITIES,
    at_least_as_restrictive_as,
    exceeds_reversibility,
)
from .scope import is_contained, require_scope

SCHEMA_VERSION = "0.1"

#: Schema validation has one owner in this repository -- ``difference.validation``, which
#: registers the whole ``01_SCHEMA`` tree. Authority reads that registry rather than building
#: a second one; only the error vocabulary is its own, so a caller can tell which boundary
#: refused without two validators having to agree about what a schema means.
AUTHORITY_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "authority/"


def _validate(record: dict[str, Any], schema_name: str, base: str) -> None:
    try:
        _validate_canonical_record(record, schema_name, base=base)
    except ValueError as error:
        raise AuthorityValidationError(str(error)) from error

#: Every top-level key the evaluation reads before it can validate anything.
REQUIRED_REQUEST_KEYS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "difference",
    "requested_action",
    "requested_scope",
    "current_state_revision",
    "current_state_fingerprint",
    "authority_rules",
    "prohibitions",
    "approvals",
    "evaluation_time",
)

#: Every key a requested action carries. Closed: an action this evaluator cannot fully read
#: is not one it may permit.
_ACTION_KEYS: tuple[str, ...] = ("action_kind", "reversibility", "action_semantic_fingerprint")

_RULE_REQUIRED_KEYS: tuple[str, ...] = (
    "schema_version",
    "authority_rule_id",
    "project_id",
    "action_kinds",
    "maximum_reversibility",
    "scope",
    "decision",
    "declared_by",
)
_RULE_DECISIONS: frozenset[str] = frozenset({AUTONOMOUS, HUMAN_APPROVAL_REQUIRED})


def _require_request_shape(request: Any) -> dict[str, Any]:
    """Reject a request that omits a key the evaluation reads.

    First, before anything else reads it. A gate that runs second is not a gate.
    """

    shaped = require_object(request, "authority request")
    # The key set is **closed**, and that is the security property rather than a tidiness
    # one. An ignored extra key is still a key a caller can believe was considered: attach
    # `pull_request_body` or `agent_conclusion` to a request, watch it be accepted, and the
    # absence of an effect is indistinguishable from a subtle one. Refusing the request says
    # plainly that this evaluator has no input of that kind -- there is no prose channel.
    unknown = set(shaped) - set(REQUIRED_REQUEST_KEYS)
    if unknown:
        raise AuthorityError(f"authority request carries unknown keys: {sorted(unknown)}")
    for key in REQUIRED_REQUEST_KEYS:
        if key not in shaped:
            raise AuthorityError(f"authority request omits a required key: {key}")
    version = require_scalar_tag(shaped["schema_version"], "authority request schema version")
    if version != SCHEMA_VERSION:
        raise AuthorityError(f"unsupported schema_version {version!r} at authority request")
    return shaped


def _require_action(value: Any) -> dict[str, Any]:
    action = require_object(value, "requested action")
    unknown = set(action) - set(_ACTION_KEYS)
    if unknown:
        raise AuthorityError(f"requested action carries unknown keys: {sorted(unknown)}")
    for key in _ACTION_KEYS:
        if key not in action:
            raise AuthorityError(f"requested action omits a required key: {key}")
    require_scalar_tag(action["action_kind"], "requested action kind")
    reversibility = require_scalar_tag(action["reversibility"], "requested action reversibility")
    if reversibility not in REVERSIBILITIES:
        raise AuthorityError(f"unknown reversibility: {reversibility!r}")
    declared = require_scalar_tag(
        action["action_semantic_fingerprint"], "requested action fingerprint"
    )
    # The supplied fingerprint is not trusted as a label. It is recomputed from the action's
    # own content, so a caller cannot bind an approval to one action and present another.
    recomputed = action_fingerprint(action)
    if declared != recomputed:
        raise AuthorityError(
            "requested action fingerprint does not match the action it names: "
            f"{declared!r} != {recomputed!r}"
        )
    return action


def _require_rule(value: Any, position: int) -> dict[str, Any]:
    context = f"authority_rules[{position}]"
    rule = require_object(value, context)
    for key in _RULE_REQUIRED_KEYS:
        if key not in rule:
            raise AuthorityError(f"{context} omits a required key: {key}")
    require_scalar_tag(rule["project_id"], f"{context} project")
    kinds = require_collection(rule["action_kinds"], f"{context} action kinds")
    for index, action_kind in enumerate(kinds):
        require_scalar_tag(action_kind, f"{context} action_kinds[{index}]")
    ceiling = require_scalar_tag(rule["maximum_reversibility"], f"{context} maximum reversibility")
    if ceiling not in REVERSIBILITIES:
        raise AuthorityError(f"{context} declares an unknown reversibility: {ceiling!r}")
    decision = require_scalar_tag(rule["decision"], f"{context} decision")
    if decision not in _RULE_DECISIONS:
        # A rule states what it permits. Refusal is a prohibition record, and keeping the two
        # vocabularies apart is what stops a rule from being written as a soft prohibition
        # that the precedence order would then have to rank.
        raise AuthorityError(f"{context} may not declare {decision!r}; use a prohibition record")
    require_scope(rule["scope"], f"{context} scope")
    return rule


def _resolve_rules(
    rules: list[dict[str, Any]],
    *,
    project_id: str,
    action_kind: str,
    reversibility: str,
    requested_scope: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    """Return the rule that governs this request, and the decision it yields.

    A rule governs only where the request fits **inside** it: same project, the action named,
    reversibility within its ceiling, and scope contained. Where several govern, the most
    restrictive decision wins, so adding a permissive rule can never loosen an existing one.
    """

    governing = [
        rule
        for rule in rules
        if rule["project_id"] == project_id
        and action_kind in rule["action_kinds"]
        and not exceeds_reversibility(reversibility, rule["maximum_reversibility"])
        and is_contained(requested_scope, rule["scope"])
    ]
    if not governing:
        # Silence is not permission. ``AUTHORITY_LEVELS.md`` §2.
        return None, HUMAN_APPROVAL_REQUIRED
    decision = AUTONOMOUS
    for rule in governing:
        decision = at_least_as_restrictive_as(decision, rule["decision"])
    # The cited rule is chosen by identity, not by input position, so the decision record is
    # the same whichever order the rules arrived in.
    chosen = sorted(governing, key=lambda rule: str(rule["authority_rule_id"]))[0]
    return chosen, decision


def evaluate_authority(request: dict[str, Any]) -> dict[str, Any]:
    """Return one canonical Authority Decision for one exact request.

    The returned record is schema-valid and content-addressed: the same question always
    produces the same ``authority_decision_id``. *request* is never mutated.

    Every refusal leaves here as an :class:`AuthorityError`. Readability is decided by the
    owner one layer down (ADR-0025) and that owner speaks in ``DifferenceError``; asking it
    is right, but leaking its vocabulary through this boundary would make a caller of
    *Authority* catch a *Difference* error to learn that its own request was malformed. The
    decision is delegated. The boundary's error vocabulary is not.
    """

    try:
        return _evaluate(request)
    except DifferenceError as error:
        raise AuthorityError(str(error)) from error


def _evaluate(request: dict[str, Any]) -> dict[str, Any]:
    request = deepcopy(request)
    shaped = _require_request_shape(request)

    project_id = require_scalar_tag(shaped["project_id"], "authority request project")
    difference = require_object(shaped["difference"], "bound Difference")
    _validate(difference, "difference.schema.json", DIFFERENCE_SCHEMA_BASE)
    if difference["project_id"] != project_id:
        raise BoundaryViolationError(
            "bound Difference belongs to a different project: "
            f"{difference['project_id']!r} != {project_id!r}"
        )

    action = _require_action(shaped["requested_action"])
    requested_scope = require_scope(shaped["requested_scope"], "requested scope")
    state_revision = shaped["current_state_revision"]
    if not isinstance(state_revision, int) or isinstance(state_revision, bool) or state_revision < 0:
        raise AuthorityError("current State revision must be a non-negative integer")
    state_fingerprint = require_object(
        shaped["current_state_fingerprint"], "current State fingerprint"
    )
    evaluation_time = require_scalar_tag(shaped["evaluation_time"], "evaluation time")

    # The Difference describes a State. If that is not the State being acted on, there is no
    # permission question to answer over it -- re-observe, then ask again.
    if (
        difference["observed_state_revision"] != state_revision
        or difference["observed_state_fingerprint"] != state_fingerprint
    ):
        raise StaleAuthorityInputError(
            "bound Difference is not bound to the current State: "
            f"difference revision {difference['observed_state_revision']} "
            f"vs current {state_revision}"
        )

    rules = [
        _require_rule(rule, position)
        for position, rule in enumerate(
            require_collection(shaped["authority_rules"], "authority rules")
        )
    ]
    prohibitions = [
        prohibition_owner.require_prohibition(record, f"prohibitions[{position}]")
        for position, record in enumerate(
            require_collection(shaped["prohibitions"], "prohibitions")
        )
    ]
    approvals = [
        approval_owner.require_approval(record, f"approvals[{position}]")
        for position, record in enumerate(require_collection(shaped["approvals"], "approvals"))
    ]

    action_kind = action["action_kind"]
    reason_codes: list[str] = []

    # --- prohibition, first ------------------------------------------------- #
    matched = prohibition_owner.matching(
        prohibitions,
        project_id=project_id,
        action_kind=action_kind,
        requested_scope=requested_scope,
    )
    if matched:
        reason_codes.append("PROHIBITION_MATCHED")
        if prohibition_owner.has_constitutional(matched):
            reason_codes.append("CONSTITUTIONAL_PROHIBITION_MATCHED")
        return _decision(
            project_id=project_id,
            difference=difference,
            action=action,
            requested_scope=requested_scope,
            state_revision=state_revision,
            state_fingerprint=state_fingerprint,
            resolved_rule=None,
            matched_prohibitions=matched,
            used_approval=None,
            decision=PROHIBITED,
            reason_codes=reason_codes,
        )

    # --- rules --------------------------------------------------------------- #
    resolved_rule, decision = _resolve_rules(
        rules,
        project_id=project_id,
        action_kind=action_kind,
        reversibility=action["reversibility"],
        requested_scope=requested_scope,
    )
    reason_codes.append("NO_RULE_RESOLVED" if resolved_rule is None else "RULE_RESOLVED")

    # Two floors a rule cannot lower. Both raise the decision and neither can lower it.
    if action_kind in HUMAN_ONLY_ACTION_KINDS:
        decision = at_least_as_restrictive_as(decision, HUMAN_APPROVAL_REQUIRED)
        reason_codes.append("ACTION_IS_HUMAN_ONLY")
    if action["reversibility"] == "IRREVERSIBLE":
        decision = at_least_as_restrictive_as(decision, HUMAN_APPROVAL_REQUIRED)
        reason_codes.append("IRREVERSIBLE_ACTION")

    # --- approval, only where the decision demands one ------------------------ #
    used_approval: dict[str, Any] | None = None
    if decision == HUMAN_APPROVAL_REQUIRED:
        intent = change_intent_fingerprint(action, requested_scope)
        declared_fingerprint = action["action_semantic_fingerprint"]
        if not approvals:
            reason_codes.append("APPROVAL_MISSING")
        else:
            failures: list[str] = []
            for candidate in approvals:
                reasons = approval_owner.unusable_reasons(
                    candidate,
                    project_id=project_id,
                    difference_id=difference["difference_id"],
                    change_intent=intent,
                    action_fingerprint=declared_fingerprint,
                    action_kind=action_kind,
                    requested_scope=requested_scope,
                    state_revision=state_revision,
                    state_fingerprint=state_fingerprint,
                    evaluation_time=evaluation_time,
                )
                if not reasons:
                    used_approval = candidate
                    break
                failures.extend(reasons)
            if used_approval is not None:
                decision = AUTONOMOUS
                reason_codes.append("APPROVAL_EXACT")
            else:
                reason_codes.extend(sorted(set(failures)))

    if decision == AUTONOMOUS and used_approval is None:
        reason_codes.append("RULE_PERMITS_AUTONOMOUS")

    return _decision(
        project_id=project_id,
        difference=difference,
        action=action,
        requested_scope=requested_scope,
        state_revision=state_revision,
        state_fingerprint=state_fingerprint,
        resolved_rule=resolved_rule,
        matched_prohibitions=[],
        used_approval=used_approval,
        decision=decision,
        reason_codes=reason_codes,
    )


def _decision(
    *,
    project_id: str,
    difference: dict[str, Any],
    action: dict[str, Any],
    requested_scope: dict[str, Any],
    state_revision: int,
    state_fingerprint: dict[str, Any],
    resolved_rule: dict[str, Any] | None,
    matched_prohibitions: list[dict[str, Any]],
    used_approval: dict[str, Any] | None,
    decision: str,
    reason_codes: list[str],
) -> dict[str, Any]:
    """Assemble, address and validate one Authority Decision record."""

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "authority_decision_id": "",
        "project_id": project_id,
        "difference_ref": {"kind": "difference", "id": difference["difference_id"]},
        "requested_action": deepcopy(action),
        "requested_scope": deepcopy(requested_scope),
        "evaluated_state_revision": state_revision,
        "evaluated_state_fingerprint": deepcopy(state_fingerprint),
        "resolved_rule_ref": (
            None
            if resolved_rule is None
            else {"kind": "authority_rule", "id": resolved_rule["authority_rule_id"]}
        ),
        "prohibition_refs": [
            {"kind": "prohibition", "id": prohibition["prohibition_id"]}
            for prohibition in matched_prohibitions
        ],
        "approval_ref": (
            None if used_approval is None else {"kind": "approval", "id": used_approval["approval_id"]}
        ),
        "decision": decision,
        "decision_reason_codes": sorted(set(reason_codes)),
        "decision_semantic_fingerprint": "",
    }
    record["decision_semantic_fingerprint"] = decision_semantic_fingerprint(record)
    record["authority_decision_id"] = decision_id(record)
    _validate(record, "authority.schema.json", AUTHORITY_SCHEMA_BASE)
    return record
