"""The ratified current-repository development policy, loaded and shape-checked.

This module reads ``03_BINDING/DEVELOPMENT_BINDING_POLICY.json`` and refuses anything that
is not exactly the declared shape. The key sets are **closed** for the reason every closed
key set in this repository is closed: a key nobody validates is a channel, and a channel
into a policy artifact is a way to change what the policy permits without changing what it
appears to say.

**This is not a Kernel element.** It selects the four concrete participants building
*this* repository. ``KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md`` §6 defines the observation,
acceptance and execution capabilities without naming a provider, and that neutrality is
preserved: nothing here appears in the kernel loop, in ``RECORD_TYPES``, or in the canonical
schema registry, and a conformance test proves it rather than asserting it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import PolicyIntegrityError

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "03_BINDING" / "DEVELOPMENT_BINDING_POLICY.json"
BINDING_DOCUMENT_PATH = ROOT / "03_BINDING" / "CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md"

POLICY_VERSION = "0.1"

#: Every top-level key the policy may carry, and no other.
POLICY_KEYS: frozenset[str] = frozenset(
    {
        "policy_version",
        "decision_id",
        "decision_status",
        "decision_authority",
        "repository",
        "scope",
        "kernel_element",
        "roles",
        "acceptance_owner",
        "merge_owner",
        "external_finding_adoption_authority",
        "external_finding_initial_status",
        "external_finding_sources",
        "external_finding_forbidden_dispositions_without_adoption",
        "non_adoption_signals",
        "handoff_states",
        "handoff_transitions",
        "executor_terminal_state",
        "human_only_states",
        "automated_review_trigger_allowed",
        "prohibited_automated_review_triggers",
        "precedence",
        "kernel_provider_neutrality_preserved",
    }
)

#: The four participants this repository's construction is bound to. Closed: a fifth role
#: appearing in the artifact is refused rather than silently gaining whatever it declares.
ROLES: frozenset[str] = frozenset({"CHATGPT", "CLAUDE_CODE", "GITHUB", "SHUKOU"})

ROLE_KEYS: frozenset[str] = frozenset({"capability", "may", "must_not"})

TRANSITION_KEYS: frozenset[str] = frozenset({"from", "to", "actor"})

#: The sole Human authority. Held here as a constant *and* required to equal the artifact's
#: value, so a policy file edited to name a different acceptance owner is refused by the
#: loader rather than obeyed.
HUMAN_AUTHORITY = "SHUKOU"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PolicyIntegrityError(message)


def load_policy(path: Path | None = None) -> dict[str, Any]:
    """Return the ratified policy once it is exactly the declared shape.

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
    _require(
        policy["decision_status"] == "RATIFIED",
        "development binding policy is not a ratified Human decision",
    )
    _require(
        policy["decision_authority"] == HUMAN_AUTHORITY,
        "development binding policy is not authored by the Human constitutional authority",
    )

    # The Binding selects participants for one repository. It is not a Kernel organ, and the
    # artifact says so in a field a test can read.
    _require(policy["kernel_element"] is None, "the development binding is not a Kernel element")
    _require(
        policy["kernel_provider_neutrality_preserved"] is True,
        "the development binding must preserve Kernel provider neutrality",
    )

    roles = policy["roles"]
    _require(isinstance(roles, dict), "development binding roles must be an object")
    _require(
        set(roles) == ROLES,
        f"development binding role map is not the closed set: {sorted(roles)}",
    )
    for name, role in roles.items():
        _require(isinstance(role, dict), f"role {name} must be an object")
        _require(set(role) == ROLE_KEYS, f"role {name} is not the closed shape: {sorted(role)}")
        for field in ("may", "must_not"):
            _require(isinstance(role[field], list), f"role {name} {field} must be an array")
            _require(
                all(isinstance(item, str) for item in role[field]),
                f"role {name} {field} must contain only strings",
            )
            _require(
                len(set(role[field])) == len(role[field]),
                f"role {name} {field} repeats an entry",
            )

    # The two boundaries the incident crossed. Asserted against the constant rather than read
    # from the file alone, because a file that can name its own acceptance owner is a file
    # that can hand acceptance to whoever edits it.
    for field in ("acceptance_owner", "merge_owner", "external_finding_adoption_authority"):
        _require(
            policy[field] == HUMAN_AUTHORITY,
            f"{field} must be {HUMAN_AUTHORITY}, not {policy[field]!r}",
        )

    _require(
        policy["automated_review_trigger_allowed"] is False,
        "automated review triggers are prohibited in this repository",
    )
    _require(
        policy["external_finding_initial_status"] == "UNVERIFIED_EXTERNAL_OBSERVATION",
        "an external finding must begin unverified",
    )

    states = policy["handoff_states"]
    _require(isinstance(states, list) and bool(states), "handoff states must be a non-empty array")
    _require(len(set(states)) == len(states), "handoff states repeat a state")
    _require(
        policy["executor_terminal_state"] in states,
        "the executor terminal state is not a declared handoff state",
    )
    _require(
        policy["executor_terminal_state"] == "READY_FOR_SHUKOU_REVIEW",
        "the executor must stop at READY_FOR_SHUKOU_REVIEW",
    )
    for state in policy["human_only_states"]:
        _require(state in states, f"human-only state {state!r} is not a declared handoff state")

    for transition in policy["handoff_transitions"]:
        _require(isinstance(transition, dict), "each handoff transition must be an object")
        _require(
            set(transition) == TRANSITION_KEYS,
            f"handoff transition is not the closed shape: {sorted(transition)}",
        )
        _require(transition["from"] in states, f"unknown from-state: {transition['from']!r}")
        _require(transition["to"] in states, f"unknown to-state: {transition['to']!r}")
        _require(transition["actor"] in ROLES, f"unknown actor: {transition['actor']!r}")
        # The property the whole state machine exists for: no transition into a Human-only
        # state may be taken by anyone but the Human. Checked at load time, so a policy file
        # edited to grant an executor a merge transition is refused before it is consulted.
        if transition["to"] in policy["human_only_states"]:
            _require(
                transition["actor"] == HUMAN_AUTHORITY,
                f"{transition['to']} may only be entered by {HUMAN_AUTHORITY}",
            )

    triggers = policy["prohibited_automated_review_triggers"]
    _require(
        isinstance(triggers, list) and bool(triggers),
        "the prohibited automated review trigger list must be non-empty",
    )
    _require(
        all(isinstance(item, str) and item for item in triggers),
        "prohibited automated review triggers must be non-empty strings",
    )

    _require(
        policy["precedence"][0] == "HUMAN_RATIFIED_CURRENT_REPOSITORY_BINDING",
        "the ratified Binding must outrank every other source of instruction",
    )
    return policy
