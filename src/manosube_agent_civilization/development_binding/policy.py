"""The ratified current-repository development policy, loaded and **pinned**.

The artifact at ``03_BINDING/DEVELOPMENT_BINDING_POLICY.json`` is the *published record* of
a Human decision. The ratified values themselves are held here, in code, and the loader
requires the record to match them exactly.

That relationship is the whole point, and the first version of this module got it wrong. It
validated that ``may`` and ``must_not`` were lists of unique strings and never that they were
*the ratified* lists -- so a policy file edited to move ``FINAL_ACCEPTANCE_DECISION`` out of
the Structural Advisor's ``must_not`` and into its ``may`` loaded cleanly, and the evaluator
then answered ``PERMITTED``. Emptying ``human_only_states`` had the same effect on merge.

```text
SHAPE VALIDATED  != CONTENT PINNED
```

That is the same defect as the Phase 5 P1 (`ADR-0027` §3.3): a rule asserted in one place and
enforced nowhere, with a check that resembles it standing in the gap. Here the repair is the
same in kind -- stop describing what the policy should contain and *hold* it.

**This is not a Kernel element.** It selects the four concrete participants building *this*
repository. ``KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md`` §6 defines the observation, acceptance
and execution capabilities without naming a provider, and that neutrality is preserved:
nothing here appears in the kernel loop, in ``RECORD_TYPES``, or in the canonical schema
registry, and conformance tests prove it rather than asserting it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import PolicyIntegrityError

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "03_BINDING" / "DEVELOPMENT_BINDING_POLICY.json"
BINDING_DOCUMENT_PATH = ROOT / "03_BINDING" / "CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md"

POLICY_VERSION = "0.2"
DECISION_ID = "HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0002"
SUPERSEDED_DECISION_ID = "HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0001"

#: The sole Human authority.
HUMAN_AUTHORITY = "SHUKOU"
#: The sole Structural Advisor.
STRUCTURAL_ADVISOR = "CHATGPT"
#: The sole implementation executor.
EXECUTOR = "CLAUDE_CODE"

ROLES: frozenset[str] = frozenset({STRUCTURAL_ADVISOR, EXECUTOR, "GITHUB", HUMAN_AUTHORITY})

#: Every top-level key the policy may carry, and no other.
POLICY_KEYS: frozenset[str] = frozenset(
    {
        "policy_version",
        "decision_id",
        "supersedes",
        "decision_status",
        "decision_authority",
        "repository",
        "scope",
        "kernel_element",
        "roles",
        "structural_review_owner",
        "merge_readiness_recommendation_owner",
        "final_acceptance_owner",
        "merge_operation_owner",
        "external_finding_adoption_authority",
        "external_finding_initial_status",
        "external_finding_sources",
        "external_finding_forbidden_dispositions_without_adoption",
        "non_adoption_signals",
        "handoff_states",
        "handoff_transitions",
        "executor_terminal_state",
        "advisor_only_states",
        "human_only_states",
        "merge_recommendation_state",
        "merge_operation_state",
        "final_acceptance_state",
        "automated_review_trigger_allowed",
        "prohibited_automated_review_triggers",
        "precedence",
        "kernel_provider_neutrality_preserved",
    }
)

ROLE_KEYS: frozenset[str] = frozenset({"capability", "may", "must_not"})
TRANSITION_KEYS: frozenset[str] = frozenset({"from", "to", "actor"})

# --------------------------------------------------------------------------- #
# The ratified values. Held, not described.
# --------------------------------------------------------------------------- #

#: Decision 0002 separates three things Decision 0001 collapsed into one ``MERGE_DECISION``.
#: The Advisor may say a change *looks* ready; only the Human decides that it *is*, and only
#: the Human performs the merge. One word for all three is one word that cannot distinguish
#: a recommendation from an authority.
STRUCTURAL_REVIEW = "STRUCTURAL_REVIEW"
MERGE_READINESS_RECOMMENDATION = "MERGE_READINESS_RECOMMENDATION"
FINAL_ACCEPTANCE_DECISION = "FINAL_ACCEPTANCE_DECISION"
MERGE_OPERATION = "MERGE_OPERATION"

RATIFIED_CAPABILITIES: dict[str, str] = {
    STRUCTURAL_ADVISOR: "STRUCTURAL_ADVISOR",
    EXECUTOR: "IMPLEMENTATION_EXECUTOR",
    "GITHUB": "HUMAN_INTENT_AND_WORK_STATE_SURFACE",
    HUMAN_AUTHORITY: "HUMAN_CONSTITUTIONAL_AUTHORITY",
}

RATIFIED_MAY: dict[str, frozenset[str]] = {
    STRUCTURAL_ADVISOR: frozenset(
        {
            "STRUCTURAL_OBSERVATION",
            "CURRENT_AND_TARGET_STATE",
            "STRUCTURAL_DIFFERENCE",
            "ROADMAP",
            "IMPLEMENTATION_HANDOFF",
            STRUCTURAL_REVIEW,
            MERGE_READINESS_RECOMMENDATION,
        }
    ),
    EXECUTOR: frozenset(
        {"IMPLEMENTATION", "TEST_EXECUTION", "EXECUTOR_SELF_REVIEW", "PR_PREPARATION"}
    ),
    "GITHUB": frozenset(
        {
            "HUMAN_INTENT_RECORD",
            "WORK_STATE_SURFACE",
            "COMMIT_AND_PR_SURFACE",
            "EVIDENCE_RECEIPT_SURFACE",
        }
    ),
    HUMAN_AUTHORITY: frozenset(
        {
            "ADOPT_EXTERNAL_FINDING",
            "REJECT_EXTERNAL_FINDING",
            FINAL_ACCEPTANCE_DECISION,
            MERGE_OPERATION,
        }
    ),
}

RATIFIED_MUST_NOT: dict[str, frozenset[str]] = {
    STRUCTURAL_ADVISOR: frozenset(
        {
            "CODE_AUTHORSHIP",
            FINAL_ACCEPTANCE_DECISION,
            MERGE_OPERATION,
            "ADOPT_EXTERNAL_FINDING",
            "REQUEST_AUTOMATED_EXTERNAL_REVIEW",
        }
    ),
    EXECUTOR: frozenset(
        {
            "STRUCTURAL_AUTHORITY",
            STRUCTURAL_REVIEW,
            MERGE_READINESS_RECOMMENDATION,
            FINAL_ACCEPTANCE_DECISION,
            MERGE_OPERATION,
            "ADOPT_EXTERNAL_FINDING",
            "REQUEST_AUTOMATED_EXTERNAL_REVIEW",
        }
    ),
    "GITHUB": frozenset(
        {
            "CANONICAL_KERNEL_STATE",
            "STRUCTURAL_AUTHORITY",
            STRUCTURAL_REVIEW,
            MERGE_READINESS_RECOMMENDATION,
            FINAL_ACCEPTANCE_DECISION,
            MERGE_OPERATION,
            "COMPLETION_DECLARATION",
            "ADOPT_EXTERNAL_FINDING",
        }
    ),
    HUMAN_AUTHORITY: frozenset(),
}

RATIFIED_STATES: tuple[str, ...] = (
    "IMPLEMENTATION_IN_PROGRESS",
    "CLAUDE_CODE_IMPLEMENTATION_COMPLETE",
    "EXECUTOR_SELF_REVIEW_COMPLETE",
    "GITHUB_PR_READY",
    "READY_FOR_STRUCTURAL_REVIEW",
    "STRUCTURAL_REVIEW_RUNNING",
    "STRUCTURAL_REVIEW_PASS",
    "MERGE_RECOMMENDED",
    "CORRECTION_REQUIRED",
    "MORE_EVIDENCE_REQUIRED",
    "BLOCKED",
    "NOT_REVIEWED",
    "SHUKOU_ACCEPTED",
    "SHUKOU_REJECTED",
    "SHUKOU_MERGED",
)

EXECUTOR_TERMINAL_STATE = "READY_FOR_STRUCTURAL_REVIEW"
MERGE_RECOMMENDATION_STATE = "MERGE_RECOMMENDED"
FINAL_ACCEPTANCE_STATE = "SHUKOU_ACCEPTED"
MERGE_OPERATION_STATE = "SHUKOU_MERGED"

RATIFIED_ADVISOR_ONLY_STATES: frozenset[str] = frozenset(
    {
        "STRUCTURAL_REVIEW_RUNNING",
        "STRUCTURAL_REVIEW_PASS",
        MERGE_RECOMMENDATION_STATE,
        "CORRECTION_REQUIRED",
        "MORE_EVIDENCE_REQUIRED",
        "BLOCKED",
        "NOT_REVIEWED",
    }
)

RATIFIED_HUMAN_ONLY_STATES: frozenset[str] = frozenset(
    {FINAL_ACCEPTANCE_STATE, "SHUKOU_REJECTED", MERGE_OPERATION_STATE}
)

#: The complete declared transition set, as ``(actor, from, to)``. Pinned whole: a transition
#: added to the artifact is refused, and one removed from it is refused too.
RATIFIED_TRANSITIONS: frozenset[tuple[str, str, str]] = frozenset(
    {
        (EXECUTOR, "IMPLEMENTATION_IN_PROGRESS", "CLAUDE_CODE_IMPLEMENTATION_COMPLETE"),
        (EXECUTOR, "CLAUDE_CODE_IMPLEMENTATION_COMPLETE", "EXECUTOR_SELF_REVIEW_COMPLETE"),
        (EXECUTOR, "EXECUTOR_SELF_REVIEW_COMPLETE", "GITHUB_PR_READY"),
        (EXECUTOR, "GITHUB_PR_READY", EXECUTOR_TERMINAL_STATE),
        (STRUCTURAL_ADVISOR, EXECUTOR_TERMINAL_STATE, "STRUCTURAL_REVIEW_RUNNING"),
        (STRUCTURAL_ADVISOR, "STRUCTURAL_REVIEW_RUNNING", "STRUCTURAL_REVIEW_PASS"),
        (STRUCTURAL_ADVISOR, "STRUCTURAL_REVIEW_RUNNING", "CORRECTION_REQUIRED"),
        (STRUCTURAL_ADVISOR, "STRUCTURAL_REVIEW_RUNNING", "MORE_EVIDENCE_REQUIRED"),
        (STRUCTURAL_ADVISOR, "STRUCTURAL_REVIEW_RUNNING", "BLOCKED"),
        (STRUCTURAL_ADVISOR, "STRUCTURAL_REVIEW_RUNNING", "NOT_REVIEWED"),
        (STRUCTURAL_ADVISOR, "STRUCTURAL_REVIEW_PASS", MERGE_RECOMMENDATION_STATE),
        (HUMAN_AUTHORITY, MERGE_RECOMMENDATION_STATE, FINAL_ACCEPTANCE_STATE),
        (HUMAN_AUTHORITY, MERGE_RECOMMENDATION_STATE, "SHUKOU_REJECTED"),
        (HUMAN_AUTHORITY, FINAL_ACCEPTANCE_STATE, MERGE_OPERATION_STATE),
        (EXECUTOR, "CORRECTION_REQUIRED", "IMPLEMENTATION_IN_PROGRESS"),
        (EXECUTOR, "MORE_EVIDENCE_REQUIRED", "IMPLEMENTATION_IN_PROGRESS"),
        (EXECUTOR, "SHUKOU_REJECTED", "IMPLEMENTATION_IN_PROGRESS"),
    }
)

#: Owner field -> the ratified owner. Every one of these is a boundary the incident or the
#: review crossed, so each is pinned rather than read.
RATIFIED_OWNERS: dict[str, str] = {
    "structural_review_owner": STRUCTURAL_ADVISOR,
    "merge_readiness_recommendation_owner": STRUCTURAL_ADVISOR,
    "final_acceptance_owner": HUMAN_AUTHORITY,
    "merge_operation_owner": HUMAN_AUTHORITY,
    "external_finding_adoption_authority": HUMAN_AUTHORITY,
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PolicyIntegrityError(message)


def _string_list(value: Any, context: str) -> list[str]:
    """Return *value* as a list of unique strings, or refuse.

    Type-checked before anything downstream puts an element into a set. A JSON array may hold
    an object, and ``{"a": 1} in frozenset(...)`` raises ``TypeError`` rather than answering.
    """

    _require(isinstance(value, list), f"{context} must be an array")
    _require(
        all(isinstance(item, str) for item in value), f"{context} must contain only strings"
    )
    _require(len(set(value)) == len(value), f"{context} repeats an entry")
    return list(value)


def load_policy(path: Path | None = None) -> dict[str, Any]:
    """Return the ratified policy once the record matches the ratified values exactly.

    Every refusal is a :class:`PolicyIntegrityError`. There is no partial load and no
    defaulting: a policy that cannot be read whole is not a policy that permits anything.
    """

    source = POLICY_PATH if path is None else path
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as error:
        raise PolicyIntegrityError(f"development binding policy is unreadable: {error}") from error
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise PolicyIntegrityError(f"development binding policy is not JSON: {error}") from error

    _require(isinstance(parsed, dict), "development binding policy must be an object")
    policy: dict[str, Any] = parsed

    unknown = set(policy) - POLICY_KEYS
    _require(not unknown, f"development binding policy carries unknown keys: {sorted(unknown)}")
    missing = POLICY_KEYS - set(policy)
    _require(not missing, f"development binding policy omits required keys: {sorted(missing)}")

    _require(
        policy["policy_version"] == POLICY_VERSION,
        f"unsupported development binding policy version: {policy['policy_version']!r}",
    )
    _require(policy["decision_id"] == DECISION_ID, "policy does not record the ratified decision")
    _require(
        policy["supersedes"] == SUPERSEDED_DECISION_ID,
        "policy does not record which decision it supersedes",
    )
    _require(
        policy["decision_status"] == "RATIFIED",
        "development binding policy is not a ratified Human decision",
    )
    _require(
        policy["decision_authority"] == HUMAN_AUTHORITY,
        "development binding policy is not authored by the Human constitutional authority",
    )

    _require(policy["kernel_element"] is None, "the development binding is not a Kernel element")
    _require(
        policy["kernel_provider_neutrality_preserved"] is True,
        "the development binding must preserve Kernel provider neutrality",
    )

    # --- roles, pinned whole ------------------------------------------------- #
    roles = policy["roles"]
    _require(isinstance(roles, dict), "development binding roles must be an object")
    _require(
        set(roles) == ROLES, f"development binding role map is not the closed set: {sorted(roles)}"
    )
    for name in sorted(ROLES):
        role = roles[name]
        _require(isinstance(role, dict), f"role {name} must be an object")
        _require(set(role) == ROLE_KEYS, f"role {name} is not the closed shape: {sorted(role)}")
        _require(
            role["capability"] == RATIFIED_CAPABILITIES[name],
            f"role {name} does not hold its ratified capability",
        )
        may = frozenset(_string_list(role["may"], f"role {name} may"))
        must_not = frozenset(_string_list(role["must_not"], f"role {name} must_not"))
        # The repair. Shape was already checked above; these two lines are what stops a
        # Human-only action being moved into a non-Human `may` list.
        _require(may == RATIFIED_MAY[name], f"role {name} may is not the ratified set")
        _require(
            must_not == RATIFIED_MUST_NOT[name], f"role {name} must_not is not the ratified set"
        )
        _require(not (may & must_not), f"role {name} both permits and forbids an action")

    for field, owner in RATIFIED_OWNERS.items():
        _require(policy[field] == owner, f"{field} must be {owner}, not {policy[field]!r}")

    _require(
        policy["automated_review_trigger_allowed"] is False,
        "automated review triggers are prohibited in this repository",
    )
    _require(
        policy["external_finding_initial_status"] == "UNVERIFIED_EXTERNAL_OBSERVATION",
        "an external finding must begin unverified",
    )

    # --- states and transitions, pinned whole -------------------------------- #
    states = _string_list(policy["handoff_states"], "handoff states")
    _require(tuple(states) == RATIFIED_STATES, "handoff states are not the ratified sequence")
    _require(
        policy["executor_terminal_state"] == EXECUTOR_TERMINAL_STATE,
        f"the executor must stop at {EXECUTOR_TERMINAL_STATE}",
    )
    _require(
        frozenset(_string_list(policy["advisor_only_states"], "advisor-only states"))
        == RATIFIED_ADVISOR_ONLY_STATES,
        "advisor-only states are not the ratified set",
    )
    # Pinned as a set rather than merely checked member-by-member: the previous version
    # accepted an *empty* list, because a loop over nothing raises nothing.
    _require(
        frozenset(_string_list(policy["human_only_states"], "human-only states"))
        == RATIFIED_HUMAN_ONLY_STATES,
        "human-only states are not the ratified set",
    )
    for field, expected in (
        ("merge_recommendation_state", MERGE_RECOMMENDATION_STATE),
        ("final_acceptance_state", FINAL_ACCEPTANCE_STATE),
        ("merge_operation_state", MERGE_OPERATION_STATE),
    ):
        _require(policy[field] == expected, f"{field} must be {expected}")

    _require(isinstance(policy["handoff_transitions"], list), "handoff transitions must be an array")
    declared: set[tuple[str, str, str]] = set()
    for transition in policy["handoff_transitions"]:
        _require(isinstance(transition, dict), "each handoff transition must be an object")
        _require(
            set(transition) == TRANSITION_KEYS,
            f"handoff transition is not the closed shape: {sorted(transition)}",
        )
        for key in sorted(TRANSITION_KEYS):
            _require(
                isinstance(transition[key], str), f"handoff transition {key} must be a string"
            )
        declared.add((transition["actor"], transition["from"], transition["to"]))
    _require(
        len(declared) == len(policy["handoff_transitions"]),
        "handoff transitions repeat an entry",
    )
    _require(
        declared == RATIFIED_TRANSITIONS, "handoff transitions are not the ratified set"
    )

    _string_list(policy["external_finding_sources"], "external finding sources")
    _string_list(
        policy["external_finding_forbidden_dispositions_without_adoption"],
        "forbidden dispositions",
    )
    _string_list(policy["non_adoption_signals"], "non-adoption signals")
    triggers = _string_list(
        policy["prohibited_automated_review_triggers"], "prohibited automated review triggers"
    )
    _require(bool(triggers), "the prohibited automated review trigger list must be non-empty")
    _require(all(trigger for trigger in triggers), "a prohibited trigger must be non-empty")

    precedence = _string_list(policy["precedence"], "precedence")
    _require(
        precedence[0] == "HUMAN_RATIFIED_CURRENT_REPOSITORY_BINDING",
        "the ratified Binding must outrank every other source of instruction",
    )
    return policy
