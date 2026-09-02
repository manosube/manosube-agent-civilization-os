"""The three Authority levels, their precedence, and what is Human-only.

``AUTHORITY_LEVELS.md`` fixes the vocabulary; this module is the executable copy of it, and
a contract test holds the two to each other in both directions so neither can drift.
"""

from __future__ import annotations

AUTONOMOUS = "AUTONOMOUS"
HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
PROHIBITED = "PROHIBITED"

#: The only decisions that exist. A fourth value is not a softer answer; it is a lie about
#: which of these three the evaluator actually reached.
DECISIONS: tuple[str, ...] = (AUTONOMOUS, HUMAN_APPROVAL_REQUIRED, PROHIBITED)

#: Ascending restrictiveness. ``max`` over this order is how conflicting rules resolve, and
#: it is why a permissive rule can never lift a restrictive one.
_ORDER: dict[str, int] = {AUTONOMOUS: 0, HUMAN_APPROVAL_REQUIRED: 1, PROHIBITED: 2}

REVERSIBILITIES: tuple[str, ...] = ("REVERSIBLE", "RECOVERABLE", "IRREVERSIBLE")
_REVERSIBILITY_ORDER: dict[str, int] = {name: index for index, name in enumerate(REVERSIBILITIES)}

#: Actions Human Authority keeps, from ``SECURITY.md`` §3 and ``AUTHORITY_LEVELS.md`` §4. A
#: rule may not lower any of these below ``HUMAN_APPROVAL_REQUIRED``; only the Kernel
#: constitution can, and changing it is itself a Human-only operation.
HUMAN_ONLY_ACTION_KINDS: frozenset[str] = frozenset(
    {
        "CHANGE_OBJECTIVE",
        "WIDEN_BOUNDARY",
        "CHANGE_AUTHORITY",
        "CHANGE_ORIGIN",
        "CHANGE_KERNEL_CONSTITUTION",
        "CHANGE_SECURITY_POLICY",
        "DEPLOY_PRODUCTION",
        "CHANGE_CREDENTIAL",
        "CHANGE_BILLING",
        "IRREVERSIBLE_OPERATION",
        "DESTRUCTIVE_RECOVERY",
        "MERGE",
        "RELEASE",
    }
)


def most_restrictive(*decisions: str) -> str:
    """Return the most restrictive of *decisions*.

    Conflicting rules do not average and do not race. The strictest one is the answer, which
    is the only resolution that cannot be exploited by adding a permissive rule.
    """

    return max(decisions, key=lambda decision: _ORDER[decision])


def at_least_as_restrictive_as(decision: str, floor: str) -> str:
    """Raise *decision* to *floor* when it is more permissive; never lower it."""

    return most_restrictive(decision, floor)


def exceeds_reversibility(actual: str, ceiling: str) -> bool:
    """Whether *actual* is less reversible than a rule's declared ceiling."""

    return _REVERSIBILITY_ORDER[actual] > _REVERSIBILITY_ORDER[ceiling]
