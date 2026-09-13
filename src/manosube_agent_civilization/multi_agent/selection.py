"""Difference-derived Agent count and capability selection (Phase 19, Issue #77, P19-C1).

One canonical Difference and its required capabilities determine the execution slots this
delivery ever opens. Caller preference, model recommendation, provider availability, majority
strategy, or a preconfigured organization cannot decide the count -- there is no parameter on
:func:`select_agent_slots` through which any of those could reach it at all; its only input is
an already Store-resolved, schema-valid, identity-verified Difference record.

**The concrete mapping (disclosed design decision).** ``01_SCHEMA/difference/difference.
schema.json`` declares no "required capabilities" field, and this delivery does not add one --
the accepted Difference schema is not reopened. What it does declare, and require on every
Difference, is a closed four-member ``risk_class`` enum (``LOW``/``MODERATE``/``HIGH``/
``CRITICAL``). :data:`RISK_CLASS_TO_SLOT_COUNT` is a fixed, total, caller-immune mapping from
that enum to a slot count, chosen so V2's "1, 2 and N slots" proof is real rather than vacuous:
``LOW``/``MODERATE`` both select one Agent (a Difference this delivery's own closure policy
already treats as ordinary carries no reason to fan work out across several), ``HIGH`` selects
two, and ``CRITICAL`` -- the delivery's own genuine N, N >= 3 -- selects three, which is also
this delivery's own closed maximum (:data:`MAX_AGENT_SLOTS`).

Every produced slot's own capability is the *one* capability that exists system-wide today
(:data:`~manosube_agent_civilization.multi_agent.types.MULTI_AGENT_CAPABILITIES`'s own single
member). This is a disclosed, bounded non-claim, not a shortcut: Phase 19 proves the mechanism
for genuine N-capability fan-out with the one capability that actually exists in this
repository, never a hypothetical multi-capability catalog it would have had to invent to
exercise. A second capability, when one is ever adopted, becomes a second, closed literal this
mapping's own per-slot capability field can carry -- exactly the "extensible later, never an
open string" discipline :data:`~manosube_agent_civilization.model_runtime.types.
MODEL_EXECUTION_CAPABILITIES` already documents for itself.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from .errors import MultiAgentOverLimitError, MultiAgentUnsupportedRequirementError
from .types import MULTI_AGENT_CAPABILITIES

#: The one closed, total, caller-immune mapping P19-C1 requires: every member of the Difference
#: schema's own closed ``risk_class`` enum names exactly one slot count. Never caller-overridable
#: -- there is no parameter on :func:`select_agent_slots` that could reach this mapping's own
#: values, and it is a plain, immutable ``MappingProxyType`` rather than a mutable ``dict`` so an
#: importer cannot silently widen it in place either.
RISK_CLASS_TO_SLOT_COUNT: Mapping[str, int] = MappingProxyType(
    {"LOW": 1, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}
)

#: This delivery's own closed maximum concurrency/count (P19-C1's own "closed maximum"
#: requirement). Equal to ``CRITICAL``'s own mapped count by construction -- no member of
#: :data:`RISK_CLASS_TO_SLOT_COUNT` may ever exceed it, checked decisively below rather than
#: assumed from the mapping's own literal values.
MAX_AGENT_SLOTS = 3


def _the_one_capability() -> str:
    """The one capability every slot this delivery ever selects requires.

    Reads :data:`~manosube_agent_civilization.multi_agent.types.MULTI_AGENT_CAPABILITIES`
    itself rather than hardcoding its one known member: if that frozenset ever gained a second
    member, a mapping that silently picked one arbitrarily would be exactly the "ambiguous
    capability requirement" P19-C1 requires this module to refuse instead. So a second member
    is refused here, loudly, before it could ever reach a fabricated per-slot assignment.
    """

    if len(MULTI_AGENT_CAPABILITIES) != 1:
        raise MultiAgentUnsupportedRequirementError(
            "the system-wide capability vocabulary this delivery selects from no longer has "
            f"exactly one member ({sorted(MULTI_AGENT_CAPABILITIES)!r}) -- this delivery's own "
            "fixed risk_class-to-slot mapping assigns the single existing capability to every "
            "slot and refuses, as ambiguous, rather than silently choose one of several"
        )
    return next(iter(MULTI_AGENT_CAPABILITIES))


def select_agent_slots(difference: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return the bounded, total, deterministic tuple of ``{"slot_index": int, "capability":
    str}`` slots this canonical, already Store-resolved and identity-verified Difference
    requires.

    *difference* must already have been resolved, schema-validated, and identity-recomputed by
    the caller (the identical admission :mod:`~manosube_agent_civilization.multi_agent.route`
    itself performs before this function is ever reached) -- this function performs no Store
    I/O and re-validates nothing about the record's own provenance; it reads exactly one field,
    ``risk_class``.

    Raises :class:`~manosube_agent_civilization.multi_agent.errors.
    MultiAgentUnsupportedRequirementError` for a ``risk_class`` outside
    :data:`RISK_CLASS_TO_SLOT_COUNT`'s own four keys (schema validation upstream should already
    prevent this, but this function never trusts that defensively) or for an ambiguous
    system-wide capability vocabulary, and :class:`~manosube_agent_civilization.multi_agent.
    errors.MultiAgentOverLimitError` for a mapped count exceeding :data:`MAX_AGENT_SLOTS` --
    unreachable through the shipped mapping alone, and checked anyway.
    """

    risk_class = difference.get("risk_class")
    if not isinstance(risk_class, str) or risk_class not in RISK_CLASS_TO_SLOT_COUNT:
        raise MultiAgentUnsupportedRequirementError(
            f"the resolved Difference's own risk_class is not one this delivery's closed "
            f"mapping recognizes: {risk_class!r} not in {sorted(RISK_CLASS_TO_SLOT_COUNT)!r} "
            "-- refusing before any slot is computed"
        )
    count = RISK_CLASS_TO_SLOT_COUNT[risk_class]
    if count < 1 or count > MAX_AGENT_SLOTS:
        raise MultiAgentOverLimitError(
            f"risk_class {risk_class!r} maps to {count} slot(s), which is outside this "
            f"delivery's own closed bound of 1..{MAX_AGENT_SLOTS} -- refusing before any Agent "
            "is constructed"
        )
    capability = _the_one_capability()
    return tuple({"slot_index": index, "capability": capability} for index in range(count))


__all__ = ["MAX_AGENT_SLOTS", "RISK_CLASS_TO_SLOT_COUNT", "select_agent_slots"]
