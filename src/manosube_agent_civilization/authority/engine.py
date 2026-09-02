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
    require_object,
    require_scalar_tag,
)
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.difference.validation import (
    validate_record as _validate_canonical_record,
)
from manosube_agent_civilization.state.errors import CanonicalizationError

from . import approval as approval_owner, prohibition as prohibition_owner
from .conformance import (
    AUTHORITY_SCHEMA_BASE,
    admit_all,
    admit_difference,
    transient_instant,
)
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
_ACTION_KEYS: tuple[str, ...] = (
    "action_kind",
    "reversibility",
    "operation",
    "action_semantic_fingerprint",
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
    # The opaque payload must at least be *canonically serializable*, or no fingerprint over
    # it exists and there is nothing to bind an approval to. Opaque means Authority does not
    # interpret the payload; it does not mean the payload may be unrepresentable. The precise
    # diagnosis is produced here rather than left to the boundary translation, so a caller is
    # told which field it was.
    try:
        recomputed = action_fingerprint(action)
    except CanonicalizationError as error:
        raise AuthorityError(
            f"requested action operation payload is not canonical: {error}"
        ) from error
    if declared != recomputed:
        raise AuthorityError(
            "requested action fingerprint does not match the action it names: "
            f"{declared!r} != {recomputed!r}"
        )
    return action


def _refine_rule(rule: dict[str, Any], context: str) -> None:
    """What a rule must satisfy beyond admission.

    Admission is the shared gate. The hand-written key check that once stood here validated
    neither the schema version, nor the declaring authority, nor unknown properties, nor the
    rule's own content address -- so a rule could keep a well-formed identity, be edited to
    ``AUTONOMOUS``, name an Agent as its author, and still govern the request.

    What stays local is the one thing better said as a sentence: a rule states what it
    *permits*. Refusal is a prohibition record, and keeping the two vocabularies apart is
    what stops a rule from becoming a soft prohibition that precedence would have to rank.
    """

    if rule["decision"] not in _RULE_DECISIONS:
        raise AuthorityError(f"{context} may not declare {rule['decision']!r}; use a prohibition")
    require_scope(rule["scope"], f"{context} scope")


def _refine_prohibition(record: dict[str, Any], context: str) -> None:
    """A prohibition's scope is enumerated for the same reason a rule's is."""

    require_scope(record["scope"], f"{context} scope")


def _resolve_rules(
    rules: list[dict[str, Any]],
    *,
    project_id: str,
    action_kind: str,
    reversibility: str,
    requested_scope: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    """Return every rule that governs this request, and the decision they yield.

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
        return [], HUMAN_APPROVAL_REQUIRED
    decision = AUTONOMOUS
    for rule in governing:
        decision = at_least_as_restrictive_as(decision, rule["decision"])
    return governing, decision


def _cite_rule(governing: list[dict[str, Any]], decision: str) -> dict[str, Any] | None:
    """Return the rule that accounts for *decision*, or ``None`` when no rule does.

    A citation is a claim about *why* the answer is what it is, and the reference
    participates in the decision's content address, so it must name a rule that declares the
    resolved decision -- not merely a rule that was present.

    Which rules can say that is only knowable once every floor and every approval narrowing
    has been applied, which is why this is asked at the end rather than at rule resolution.
    Resolving it early cited a rule declaring ``AUTONOMOUS`` on a decision the human-only
    floor had already raised to ``HUMAN_APPROVAL_REQUIRED``: a record whose provenance argued
    against its own answer. Where a floor alone created the restriction no rule declares it,
    and the honest citation is none at all.
    """

    supporting = [rule for rule in governing if rule["decision"] == decision]
    if not supporting:
        return None
    # Chosen by identity, not by input position, so the record is the same whichever order
    # the rules arrived in.
    return sorted(supporting, key=lambda rule: str(rule["authority_rule_id"]))[0]


def evaluate_authority(request: dict[str, Any]) -> dict[str, Any]:
    """Return one canonical Authority Decision for one exact request.

    The returned record is schema-valid and content-addressed: the same question always
    produces the same ``authority_decision_id``. *request* is never mutated.

    Every refusal leaves here as an :class:`AuthorityError`. Two owners one layer down speak
    their own vocabularies -- readability answers in ``DifferenceError`` (ADR-0025) and
    canonical serialization in ``CanonicalizationError`` -- and asking both is right. Letting
    either escape would make a caller of *Authority* catch a *Difference* or a *State* error
    to learn that its own request was malformed. The decisions are delegated. The boundary's
    error vocabulary is not.
    """

    try:
        return _evaluate(request)
    except (DifferenceError, CanonicalizationError) as error:
        raise AuthorityError(str(error)) from error


def _evaluate(request: dict[str, Any]) -> dict[str, Any]:
    request = deepcopy(request)
    shaped = _require_request_shape(request)

    project_id = require_scalar_tag(shaped["project_id"], "authority request project")
    difference = admit_difference(shaped["difference"], "bound Difference")
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
    # Time conformance belongs to the admission stage, not to the one branch that happens to
    # read a clock value. Parsed only inside the approval check, ``not-a-time`` produced a
    # decision on every early route -- a rule granting autonomy, a prohibition returning
    # first, an empty approval list -- because none of them reached the parser.
    transient_instant(evaluation_time, "evaluation time")

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

    # Every supplied record crosses one admission path before it can affect anything:
    # schema, supported version, no unknown property, recomputed content address, and Human
    # Authority provenance. A record failing any of those does not govern, is not consulted,
    # and does not quietly become an absence -- it refuses the request.
    rules = admit_all(
        shaped["authority_rules"], "authority_rule", "authority rules", refine=_refine_rule
    )
    prohibitions = admit_all(
        shaped["prohibitions"], "prohibition", "prohibitions", refine=_refine_prohibition
    )
    approvals = admit_all(
        shaped["approvals"], "approval", "approvals", refine=approval_owner.refine_approval
    )

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
            excluding_approvals=[],
            decision=PROHIBITED,
            reason_codes=reason_codes,
        )

    # --- rules --------------------------------------------------------------- #
    governing, decision = _resolve_rules(
        rules,
        project_id=project_id,
        action_kind=action_kind,
        reversibility=action["reversibility"],
        requested_scope=requested_scope,
    )
    if not governing:
        reason_codes.append("NO_RULE_RESOLVED")

    # Two floors a rule cannot lower. Both raise the decision and neither can lower it.
    if action_kind in HUMAN_ONLY_ACTION_KINDS:
        decision = at_least_as_restrictive_as(decision, HUMAN_APPROVAL_REQUIRED)
        reason_codes.append("ACTION_IS_HUMAN_ONLY")
    if action["reversibility"] == "IRREVERSIBLE":
        decision = at_least_as_restrictive_as(decision, HUMAN_APPROVAL_REQUIRED)
        reason_codes.append("IRREVERSIBLE_ACTION")

    # --- approvals: which bind, which withhold -------------------------------- #
    #
    # Binding is settled **independently of what the rules decided**. An approval may narrow
    # authority even where a rule permits (``APPROVAL_CONTRACT.md`` §6), and an exclusion
    # examined only when a rule already required approval is not a narrowing -- it is a
    # coincidence of which branch ran.
    intent = change_intent_fingerprint(action, requested_scope)
    declared_fingerprint = action["action_semantic_fingerprint"]
    failures: list[str] = []
    binding: list[dict[str, Any]] = []
    for candidate in approvals:
        mismatches = approval_owner.binding_mismatches(
            candidate,
            project_id=project_id,
            difference_id=difference["difference_id"],
            change_intent=intent,
            action_fingerprint=declared_fingerprint,
            requested_scope=requested_scope,
            state_revision=state_revision,
            state_fingerprint=state_fingerprint,
            evaluation_time=evaluation_time,
        )
        if mismatches:
            failures.extend(mismatches)
        else:
            binding.append(candidate)

    excluding = sorted(
        (record for record in binding if approval_owner.excludes_action(record, action_kind)),
        key=lambda record: str(record["approval_id"]),
    )
    if excluding:
        # An approval may add a refusal; it may never lift one. This raises the decision and
        # can never lower it, whatever the rules said.
        decision = at_least_as_restrictive_as(decision, HUMAN_APPROVAL_REQUIRED)
        reason_codes.append("APPROVAL_EXCLUDES_ACTION")

    # An approval that withheld the action does not then authorize it.
    usable = [record for record in binding if record not in excluding]

    used_approval: dict[str, Any] | None = None
    if decision == HUMAN_APPROVAL_REQUIRED:
        if excluding:
            # ``ANY_APPLICABLE_EXCLUSION -> NEVER_AUTONOMOUS``. A second approval that binds
            # and permits does not overrule the first one's refusal: an approval may narrow
            # and may never widen (``APPROVAL_CONTRACT.md`` §6), and "one of them said yes"
            # is exactly the widening that rule forbids. The exclusion is already recorded;
            # nothing below may lower it.
            pass
        elif not approvals:
            reason_codes.append("APPROVAL_MISSING")
        elif usable:
            # Every binding approval is examined, then one is chosen **by identity**. Taking
            # the first supplied made the returned record depend on input order, which for an
            # evaluator promising a canonical answer is a second answer to the same question.
            used_approval = sorted(usable, key=lambda record: str(record["approval_id"]))[0]
            decision = AUTONOMOUS
            reason_codes.append("APPROVAL_EXACT")
        else:
            reason_codes.extend(sorted(set(failures)))

    if decision == AUTONOMOUS and used_approval is None:
        reason_codes.append("RULE_PERMITS_AUTONOMOUS")

    # Provenance last, because until here the decision could still be raised by a floor or by
    # an exclusion, or lowered by an approval. ``RULE_NOT_DECISIVE`` is what a governing rule
    # that does not account for the answer leaves behind: the rule is recorded as having
    # governed, and no rule is cited, so the reason codes and the citation cannot disagree.
    resolved_rule = _cite_rule(governing, decision)
    if governing:
        reason_codes.append("RULE_RESOLVED" if resolved_rule is not None else "RULE_NOT_DECISIVE")

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
        excluding_approvals=excluding,
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
    excluding_approvals: list[dict[str, Any]],
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
        # An approval that *withheld* the action is provenance too: without it, two different
        # approvals narrowing the same request to the same level with the same reason code
        # would share one decision identity.
        "excluding_approval_refs": [
            {"kind": "approval", "id": record["approval_id"]} for record in excluding_approvals
        ],
        "decision": decision,
        "decision_reason_codes": sorted(set(reason_codes)),
        "decision_semantic_fingerprint": "",
    }
    record["decision_semantic_fingerprint"] = decision_semantic_fingerprint(record)
    record["authority_decision_id"] = decision_id(record)
    _validate(record, "authority.schema.json", AUTHORITY_SCHEMA_BASE)
    return record
