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

**This is not a Kernel element.** It selects the concrete participants building *this*
repository. ``KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md`` §6 defines the observation, acceptance
and execution capabilities without naming a provider, and that neutrality is preserved:
nothing here appears in the kernel loop, in ``RECORD_TYPES``, or in the canonical schema
registry, and conformance tests prove it rather than asserting it.

Decision 0003 (Issue #102) evolves this module rather than replacing it: the implementation
executor capability admits a second eligible provider, ``GITHUB_COPILOT``, alongside
``CLAUDE_CODE``. The two hold identical ``may``/``must_not`` sets and identical handoff
transitions -- the capability is unchanged; only the set of names that may fill it grows by
one. Eligibility recorded here is necessary but never sufficient: this module answers "is
``GITHUB_COPILOT`` a role this Binding recognises at all", never "is Copilot the selected
executor for this specific work unit right now". That second, narrower question -- exact
repository, branch, base/head SHA, and a SHUKOU-granted, read-back-verified selection record --
is :mod:`.executor_selection`, a separate gate a caller must pass in addition to, not instead
of, this one. ``ELIGIBLE_PROVIDER_MEMBERSHIP_IS_NOT_EXECUTION_AUTHORITY=true``.

Decision 0004 (Issue #109) evolves this module a second time, admitting a **third** role that
holds no implementation capability at all: ``CODEX``, a ``BOUNDED_TECHNICAL_REVIEWER``. This is
not a third eligible name for the existing ``IMPLEMENTATION_EXECUTOR`` capability -- it is a
distinct capability, held by a distinct role, that may never author code, review structurally,
recommend merge readiness, decide final acceptance, operate a merge, or adopt an external
finding. ``prohibited_automated_review_triggers``/``automated_review_trigger_allowed`` are
unchanged by this decision and continue to prohibit every *unconditional* automated-review
route named there; Decision 0004 opens exactly one additional, narrow, mechanically bounded
route -- the one action ``bounded_technical_review_action`` names, gated the same way
``GITHUB_COPILOT``'s own non-default executor actions already are: role membership makes the
action nameable in principle, and a separate, narrower, offline-checked grant
(:mod:`.review_selection`) must independently admit the specific request before
``evaluation.evaluate`` ever permits it. ``BOUNDED_TECHNICAL_REVIEW_IS_NOT_A_TRIGGER_EXEMPTION=
true``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import PolicyIntegrityError

#: The canonical policy artifact, and the only copy of it kept on disk.
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REPOSITORY_POLICY_PATH = REPOSITORY_ROOT / "03_BINDING" / "DEVELOPMENT_BINDING_POLICY.json"

#: Where that same file lands *inside an installed wheel*, placed there at build time by the
#: `force-include` mapping in `pyproject.toml`. It is not a second maintained copy: nothing
#: writes it, nothing edits it, and a conformance test fails if one ever appears in the
#: source tree.
PACKAGED_POLICY_PATH = Path(__file__).resolve().parent / "DEVELOPMENT_BINDING_POLICY.json"

#: The Binding *document* is prose for people and is read only by conformance tests, so it
#: stays repository-relative. The guard does not read it, and an installed wheel does not
#: need it to answer.
BINDING_DOCUMENT_PATH = REPOSITORY_ROOT / "03_BINDING" / "CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md"


def resolve_policy_path() -> Path:
    """Return the policy artifact, wherever this package is running from.

    Packaged copy first, repository second. In a source checkout the packaged path does not
    exist, so the canonical file is read directly and an edit to it takes effect immediately.
    In an installed wheel the repository path does not exist, and the packaged copy answers.

    A guard that silently stops guarding once installed is worse than no guard. This one
    failed closed rather than open -- it raised instead of permitting -- but it could not run
    at all outside a source checkout, which is its own kind of useless.
    """

    if PACKAGED_POLICY_PATH.is_file():
        return PACKAGED_POLICY_PATH
    return REPOSITORY_POLICY_PATH


#: Backwards-compatible alias for the canonical artifact. Conformance tests that mutate a
#: copy of the ratified record read this; the guard uses :func:`resolve_policy_path`.
POLICY_PATH = REPOSITORY_POLICY_PATH

POLICY_VERSION = "0.4"
DECISION_ID = "HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0004"
SUPERSEDED_DECISION_ID = "HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0003"

#: The sole Human authority.
HUMAN_AUTHORITY = "SHUKOU"
#: The sole Structural Advisor.
STRUCTURAL_ADVISOR = "CHATGPT"
#: The first ratified implementation executor. Decision 0002's name; kept unchanged by
#: Decision 0003 so every historical record and every Claude Code transition continues to
#: read exactly as it did before Copilot was admitted.
EXECUTOR = "CLAUDE_CODE"
#: The second eligible implementation executor (Decision 0003, Issue #102). Same capability,
#: same ``may``/``must_not`` sets, same transitions as :data:`EXECUTOR` -- the Binding does
#: not care which name fills the capability, only that exactly one eligible name does, for a
#: given work unit, through :mod:`.executor_selection`.
COPILOT_EXECUTOR = "GITHUB_COPILOT"

#: Every name this Binding currently recognises as eligible to hold the implementation
#: executor capability. Membership here is eligibility, never authority -- see the module
#: docstring and :mod:`.executor_selection`.
EXECUTOR_PROVIDERS: frozenset[str] = frozenset({EXECUTOR, COPILOT_EXECUTOR})
#: Absent any work-unit-scoped selection record naming Copilot, Claude Code continues to
#: operate exactly as it did under Decision 0002. This is what makes Decision 0003 backward
#: compatible rather than a breaking re-selection.
DEFAULT_EXECUTOR_PROVIDER = EXECUTOR
#: Only the Human authority may select, for one work unit, which eligible provider is the
#: active executor.
EXECUTOR_PROVIDER_SELECTION_AUTHORITY = HUMAN_AUTHORITY

#: Decision 0004 (Issue #109): the one role holding the ``BOUNDED_TECHNICAL_REVIEWER``
#: capability. Never an implementation executor, never eligible for ``EXECUTOR_PROVIDERS``,
#: never the Structural Advisor or the Human authority -- a fourth, disjoint role, not a third
#: name added to an existing one.
BOUNDED_TECHNICAL_REVIEWER = "CODEX"
#: The one action this role's capability may ever perform. Distinct, by name, from
#: ``REQUEST_AUTOMATED_EXTERNAL_REVIEW`` (the unconditional/native trigger every role,
#: ``CODEX`` included, still has in its own ``must_not`` -- see
#: :data:`_BOUNDED_TECHNICAL_REVIEWER_MUST_NOT`): that action names *asking for* an automated
#: review to run at all, outside any grant; this one names the bounded review itself, and is
#: never permitted by role membership alone (``evaluation._requires_review_selection``).
BOUNDED_TECHNICAL_REVIEW_ACTION = "BOUNDED_TECHNICAL_REVIEW"
#: Only the Human authority may grant one bounded review admission -- the identical authority
#: as every other grant this Binding recognises.
BOUNDED_REVIEW_GRANT_AUTHORITY = HUMAN_AUTHORITY
#: Runtime starts disabled, and this value is itself part of the ratified record: a policy
#: edited to flip it is refused by :func:`load_policy` exactly like any other pinned field.
#: Nothing in this delivery ever supplies a path that overrides it to ``true`` --
#: :mod:`.review_control`'s own activation gate reads it and fails closed if it is ever
#: anything else.
BOUNDED_REVIEW_ACTIVATION_DEFAULT = False
#: The ratified numeric ceiling (Issue #109 handoff, comment 6017544351, §4). Held here, as
#: code, for the identical reason every other ratified value in this module is: the JSON
#: artifact is the published record, and the loader requires it to match these constants
#: exactly. A grant (:mod:`.review_selection`) never redeclares its own copy of these numbers;
#: only :mod:`.review_control` reads them, from the loaded policy, when it actually tracks
#: usage against them.
#:
#: ``max_live_state_observation_age_seconds`` (SR5-F1 correction, PR #112 comment
#: 6034603745): the one ratified staleness ceiling a fresh live-review-state observation
#: (:func:`~manosube_agent_civilization.development_binding.review_adapter.
#: fetch_trusted_live_review_state`'s own ``observed_at``) must fall within, checked against
#: a real clock at the exact instant ``scripts/bounded_technical_review.py``'s own
#: ``_recheck_live_authorization`` re-checks it -- an observation older than this (or one
#: that claims to be from the future) is refused as stale, never trusted merely for
#: carrying a matching sha.
BOUNDED_REVIEW_NUMERIC_LIMITS: dict[str, int] = {
    "max_concurrent_reviews_per_repository": 1,
    "max_launches_per_jst_day": 4,
    "max_process_seconds": 1800,
    "max_poll_window_seconds": 28800,
    "poll_interval_seconds": 60,
    "max_input_bytes": 1048576,
    "max_result_bytes": 1048576,
    "automatic_retries_allowed": 0,
    "max_live_state_observation_age_seconds": 300,
}
#: Zero. Not a placeholder, not a default pending confirmation -- the ratified ceiling itself.
BOUNDED_REVIEW_ADDITIONAL_SPENDING_CEILING = 0

ROLES: frozenset[str] = frozenset(
    {
        STRUCTURAL_ADVISOR,
        EXECUTOR,
        COPILOT_EXECUTOR,
        "GITHUB",
        HUMAN_AUTHORITY,
        BOUNDED_TECHNICAL_REVIEWER,
    }
)

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
        "executor_providers",
        "executor_provider_default",
        "executor_provider_selection_authority",
        "bounded_technical_reviewer",
        "bounded_technical_review_action",
        "bounded_review_grant_authority",
        "bounded_review_activation_default",
        "bounded_review_numeric_limits",
        "bounded_review_additional_spending_ceiling",
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

#: The implementation executor's capability and permission sets, shared verbatim by every
#: eligible provider in :data:`EXECUTOR_PROVIDERS`. Declared once and spread into both names
#: below so a future third provider (or a correction to either set) cannot drift the two apart
#: by editing one and forgetting the other.
_EXECUTOR_CAPABILITY = "IMPLEMENTATION_EXECUTOR"
_EXECUTOR_MAY = frozenset(
    {"IMPLEMENTATION", "TEST_EXECUTION", "EXECUTOR_SELF_REVIEW", "PR_PREPARATION"}
)
_EXECUTOR_MUST_NOT = frozenset(
    {
        "STRUCTURAL_AUTHORITY",
        STRUCTURAL_REVIEW,
        MERGE_READINESS_RECOMMENDATION,
        FINAL_ACCEPTANCE_DECISION,
        MERGE_OPERATION,
        "ADOPT_EXTERNAL_FINDING",
        "REQUEST_AUTOMATED_EXTERNAL_REVIEW",
    }
)

#: Decision 0004: held separately from ``_EXECUTOR_MAY``/``_EXECUTOR_MUST_NOT`` on purpose --
#: this is a disjoint capability, not a third name sharing the implementation executor's own
#: permission sets. ``CODEX`` must_not everything the other three non-Human roles must_not,
#: plus the implementation executor's own four actions: a reviewer that could also implement,
#: self-review, or prepare a PR would no longer be a reviewer.
_BOUNDED_REVIEWER_MUST_NOT = frozenset(
    {
        "CODE_AUTHORSHIP",
        "IMPLEMENTATION",
        "TEST_EXECUTION",
        "EXECUTOR_SELF_REVIEW",
        "PR_PREPARATION",
        "STRUCTURAL_AUTHORITY",
        STRUCTURAL_REVIEW,
        MERGE_READINESS_RECOMMENDATION,
        FINAL_ACCEPTANCE_DECISION,
        MERGE_OPERATION,
        "ADOPT_EXTERNAL_FINDING",
        "REQUEST_AUTOMATED_EXTERNAL_REVIEW",
    }
)

RATIFIED_CAPABILITIES: dict[str, str] = {
    STRUCTURAL_ADVISOR: "STRUCTURAL_ADVISOR",
    EXECUTOR: _EXECUTOR_CAPABILITY,
    COPILOT_EXECUTOR: _EXECUTOR_CAPABILITY,
    "GITHUB": "HUMAN_INTENT_AND_WORK_STATE_SURFACE",
    HUMAN_AUTHORITY: "HUMAN_CONSTITUTIONAL_AUTHORITY",
    BOUNDED_TECHNICAL_REVIEWER: "BOUNDED_TECHNICAL_REVIEWER",
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
    EXECUTOR: _EXECUTOR_MAY,
    COPILOT_EXECUTOR: _EXECUTOR_MAY,
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
    BOUNDED_TECHNICAL_REVIEWER: frozenset({BOUNDED_TECHNICAL_REVIEW_ACTION}),
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
    EXECUTOR: _EXECUTOR_MUST_NOT,
    COPILOT_EXECUTOR: _EXECUTOR_MUST_NOT,
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
    BOUNDED_TECHNICAL_REVIEWER: _BOUNDED_REVIEWER_MUST_NOT,
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

#: Every state name a superseded decision used and this one does not. Kept for one purpose:
#: so a conformance test can prove none of them survives in an active document.
#:
#: `READY_FOR_SHUKOU_REVIEW` survived a whole merge inside
#: `HUMAN_AGENT_WORK_COMMUNICATION.md` §7A. The Binding, the policy, both templates and the
#: evaluator were all corrected; the communication protocol restated the value in prose and
#: nothing compared the two.
#:
#: This is a **set**, and the first version of it was a single string -- which was its own
#: instance of the same defect, because Decision 0001 retired two states and the guard knew
#: about one. A renaming decision MUST add every retired name here; that is the one step this
#: guard cannot perform for itself, and it is stated rather than assumed.
SUPERSEDED_STATE_NAMES: frozenset[str] = frozenset(
    {
        "READY_FOR_SHUKOU_REVIEW",
        "SHUKOU_CHECK",
    }
)

#: Kept as a name because the executor terminal state is the one that drifted, and a reader
#: looking for it should find it rather than have to know it is in the set above.
SUPERSEDED_EXECUTOR_TERMINAL_STATE = "READY_FOR_SHUKOU_REVIEW"
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
#:
#: Every executor-actor transition is declared once per entry in :data:`EXECUTOR_PROVIDERS`
#: (built below by substitution) rather than hand-duplicated, so the two providers cannot
#: drift to different transition sets by someone editing one literal block and not the other.
#: The state names themselves are unchanged from Decision 0002 -- they describe a step in the
#: implementation phase, not which eligible provider took it; the actor field is what the
#: Binding actually conditions on.
_EXECUTOR_TRANSITION_TEMPLATE: tuple[tuple[str, str], ...] = (
    ("IMPLEMENTATION_IN_PROGRESS", "CLAUDE_CODE_IMPLEMENTATION_COMPLETE"),
    ("CLAUDE_CODE_IMPLEMENTATION_COMPLETE", "EXECUTOR_SELF_REVIEW_COMPLETE"),
    ("EXECUTOR_SELF_REVIEW_COMPLETE", "GITHUB_PR_READY"),
    ("GITHUB_PR_READY", "READY_FOR_STRUCTURAL_REVIEW"),
    ("CORRECTION_REQUIRED", "IMPLEMENTATION_IN_PROGRESS"),
    ("MORE_EVIDENCE_REQUIRED", "IMPLEMENTATION_IN_PROGRESS"),
    ("SHUKOU_REJECTED", "IMPLEMENTATION_IN_PROGRESS"),
)

RATIFIED_TRANSITIONS: frozenset[tuple[str, str, str]] = frozenset(
    {
        (provider, source, target)
        for provider in EXECUTOR_PROVIDERS
        for source, target in _EXECUTOR_TRANSITION_TEMPLATE
    }
    | {
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
    _require(all(isinstance(item, str) for item in value), f"{context} must contain only strings")
    _require(len(set(value)) == len(value), f"{context} repeats an entry")
    return list(value)


def load_policy(path: Path | None = None) -> dict[str, Any]:
    """Return the ratified policy once the record matches the ratified values exactly.

    Every refusal is a :class:`PolicyIntegrityError`. There is no partial load and no
    defaulting: a policy that cannot be read whole is not a policy that permits anything.
    """

    source = resolve_policy_path() if path is None else path
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

    # --- eligible executor providers, pinned whole (Decision 0003) ---------- #
    _require(
        frozenset(_string_list(policy["executor_providers"], "executor providers"))
        == EXECUTOR_PROVIDERS,
        "executor providers are not the ratified eligible set",
    )
    _require(
        policy["executor_provider_default"] == DEFAULT_EXECUTOR_PROVIDER,
        f"executor_provider_default must be {DEFAULT_EXECUTOR_PROVIDER}",
    )
    _require(
        policy["executor_provider_selection_authority"] == EXECUTOR_PROVIDER_SELECTION_AUTHORITY,
        f"executor_provider_selection_authority must be {EXECUTOR_PROVIDER_SELECTION_AUTHORITY}",
    )

    # --- bounded technical reviewer, pinned whole (Decision 0004) ----------- #
    _require(
        policy["bounded_technical_reviewer"] == BOUNDED_TECHNICAL_REVIEWER,
        f"bounded_technical_reviewer must be {BOUNDED_TECHNICAL_REVIEWER}",
    )
    _require(
        policy["bounded_technical_review_action"] == BOUNDED_TECHNICAL_REVIEW_ACTION,
        f"bounded_technical_review_action must be {BOUNDED_TECHNICAL_REVIEW_ACTION}",
    )
    _require(
        policy["bounded_review_grant_authority"] == BOUNDED_REVIEW_GRANT_AUTHORITY,
        f"bounded_review_grant_authority must be {BOUNDED_REVIEW_GRANT_AUTHORITY}",
    )
    # Pinned as a boolean identity check, not merely "is a bool" -- the exact defect class
    # this module's own docstring names (SHAPE VALIDATED != CONTENT PINNED). A policy edited
    # to flip this to true is refused here, before any caller ever reads it as permission.
    _require(
        policy["bounded_review_activation_default"] is BOUNDED_REVIEW_ACTIVATION_DEFAULT,
        f"bounded_review_activation_default must be {BOUNDED_REVIEW_ACTIVATION_DEFAULT!r}",
    )
    numeric_limits = policy["bounded_review_numeric_limits"]
    _require(isinstance(numeric_limits, dict), "bounded_review_numeric_limits must be an object")
    _require(
        set(numeric_limits) == set(BOUNDED_REVIEW_NUMERIC_LIMITS),
        "bounded_review_numeric_limits does not carry exactly the ratified field set: "
        f"{sorted(numeric_limits)}",
    )
    for field, expected in BOUNDED_REVIEW_NUMERIC_LIMITS.items():
        value = numeric_limits[field]
        _require(
            isinstance(value, int) and not isinstance(value, bool) and value == expected,
            f"bounded_review_numeric_limits[{field!r}] must be the ratified {expected}, "
            f"not {value!r}",
        )
    _require(
        policy["bounded_review_additional_spending_ceiling"]
        == BOUNDED_REVIEW_ADDITIONAL_SPENDING_CEILING,
        "bounded_review_additional_spending_ceiling must be "
        f"{BOUNDED_REVIEW_ADDITIONAL_SPENDING_CEILING}",
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

    _require(
        isinstance(policy["handoff_transitions"], list), "handoff transitions must be an array"
    )
    declared: set[tuple[str, str, str]] = set()
    for transition in policy["handoff_transitions"]:
        _require(isinstance(transition, dict), "each handoff transition must be an object")
        _require(
            set(transition) == TRANSITION_KEYS,
            f"handoff transition is not the closed shape: {sorted(transition)}",
        )
        for key in sorted(TRANSITION_KEYS):
            _require(isinstance(transition[key], str), f"handoff transition {key} must be a string")
        declared.add((transition["actor"], transition["from"], transition["to"]))
    _require(
        len(declared) == len(policy["handoff_transitions"]),
        "handoff transitions repeat an entry",
    )
    _require(declared == RATIFIED_TRANSITIONS, "handoff transitions are not the ratified set")

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
