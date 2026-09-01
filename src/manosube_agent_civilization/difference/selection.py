"""Which canonical inputs a Difference derivation is actually built from.

Two review findings were the same mistake in different places: the Engine treated a
*container* as the source set. An Observation over a multi-subject Scope legitimately
carries Facts for subjects other than the Target's, and an Objective revision can carry two
Target Predicates under one ``predicate_id`` whose payloads differ. In both cases the
Engine read the container -- every referenced Fact, the last predicate to win a dict
comprehension -- rather than selecting the exact record the Difference contract binds.

Selection is stated once here so the Engine and the independent contract validator cannot
disagree about which records a Difference is derived from. Selection is not validation:
these functions decide *which* records bind, and every selected record still crosses the
schema, identity, boundary and cross-record gates it always did.
"""

from __future__ import annotations

from typing import Any

from .canonical import canonical_bytes
from .errors import DifferenceError, IdentityCollisionError


def contributing_facts(
    observation: dict[str, Any],
    facts_by_id: dict[str, dict[str, Any]],
    subject: str,
    project_id: str,
) -> list[dict[str, Any]]:
    """Return the Facts of *observation* that bind this exact project and Target subject.

    A canonical Observation is scoped to a Scope, not to a single subject: a Scope that
    includes ``kernel.state`` and ``kernel.other`` yields one Observation referencing both
    subjects' Facts. Those other Facts are legitimate provenance and travel with the
    returned bundle; they simply do not contribute to *this* Target's observed state.
    Rejecting the Observation because it carries them, as the Engine did, made a valid
    multi-subject Scope underivable.

    The project check is the other half of the same rule and the more dangerous one: a
    Fact minted for another project recomputes its own identity perfectly, so nothing
    downstream would have questioned it, and its value entered a foreign project's
    observed-state candidates.

    Order follows the Observation's own ``normalized_fact_refs``, so selection is
    deterministic and independent of bundle ordering.
    """

    selected: list[dict[str, Any]] = []
    for reference in observation["normalized_fact_refs"]:
        if reference.get("kind") != "normalized_fact":
            continue
        fact = facts_by_id.get(str(reference.get("id")))
        if fact is None:
            continue
        if fact["project_id"] == project_id and fact["subject"] == subject:
            selected.append(fact)
    return selected


def unique_target_predicates(objective: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the Objective's Target Predicates by identity, rejecting an ambiguous id.

    ``objective_revision.schema.json`` declares ``target_predicates`` with ``uniqueItems``,
    which compares *whole payloads*: two predicates sharing a ``predicate_id`` while
    differing anywhere else satisfy it. A dict comprehension over that list silently keeps
    the last one, and the independent validator resolves the first match -- so ambiguous
    Human Objective input produced a bundle that fails cross-record validation.

    A Target Predicate identity names one predicate. Two payloads under one identity is
    not a preference to resolve; it is input the Difference route cannot interpret, and it
    fails closed here before any index is built. An exactly identical duplicate is
    idempotent, which the schema's ``uniqueItems`` already forbids independently.
    """

    predicates: dict[str, dict[str, Any]] = {}
    payloads: dict[str, bytes] = {}
    for predicate in objective["target_predicates"]:
        identity = predicate.get("predicate_id")
        if not isinstance(identity, str) or not identity:
            raise DifferenceError("Target Predicate has no identity")
        payload = canonical_bytes(predicate)
        existing = payloads.get(identity)
        if existing is not None and existing != payload:
            raise IdentityCollisionError(
                f"Objective declares two different Target Predicates under one identity: "
                f"{identity}"
            )
        payloads[identity] = payload
        predicates[identity] = predicate
    return predicates
