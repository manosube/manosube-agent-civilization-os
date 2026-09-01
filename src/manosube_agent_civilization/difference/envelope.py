"""Invariants of the returned bundle's own envelope.

A returned bundle carries records *and* envelope fields that summarise them --
``satisfied_target_predicates`` is the one this module exists for. Records are decided by
schema, identity and the relational gate; an envelope field is decided by nothing unless
something reconciles it against the records it summarises.

The rule here was first written directly inside :func:`difference.graph.relational_errors`,
which the Engine calls and the independent validator does not: that validator composes its
own relational pass out of shared owners. So the producer rejected the contradiction and the
auditor stayed silent on the same bundle -- an Engine-only rule, the exact mirror of the
auditor-only rule ADR-0015 removed, and it falsified the claim that the contradiction was
unemittable by any route. Stated here, both read it.
"""

from __future__ import annotations

from typing import Any


def satisfaction_reconciliation_errors(bundle: dict[str, Any]) -> list[str]:
    """Return every Target reported satisfied while an open Difference names it.

    A Target is satisfied or it is open; it cannot be both. The two answers are produced on
    routes that never meet -- the satisfied route returns before emitting any record, and
    every other whole-bundle rule reads records -- so nothing compared them.

    Total over an untrusted bundle: a non-list envelope, or a Difference without a readable
    Target reference, is passed over rather than raised on.
    """

    satisfied = bundle.get("satisfied_target_predicates")
    if not isinstance(satisfied, list):
        return []
    open_targets = {
        record["target_predicate_ref"]["id"]
        for record in bundle.get("differences", []) or []
        if isinstance(record, dict)
        and isinstance(record.get("target_predicate_ref"), dict)
        and isinstance(record["target_predicate_ref"].get("id"), str)
    }
    # Each member is filtered to a hashable identity *before* the set operation. Both gates
    # call this on an untrusted envelope, so an array or object member would otherwise raise
    # `unhashable type` from `intersection` -- a membership test needs the guard a subscript
    # needs, which is the rule this module's own predecessor round missed twice.
    declared = {member for member in satisfied if isinstance(member, str)}
    return [
        f"Target Predicate is reported satisfied and open at once: {identity}"
        for identity in sorted(open_targets.intersection(declared))
    ]
