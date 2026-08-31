"""The single canonical Fact effective-boundary matching authority.

`NORMALIZED_FACT.md` gives a Normalized Fact three contract-legal effective boundary
forms. Deciding whether one of them was actually observed by a given Observation is a
single rule, owned here by the Observation element and reused by every downstream
consumer, so no second copy can drift.
"""

from __future__ import annotations

from typing import Any

FACT_BOUNDARY_KINDS: frozenset[str] = frozenset(
    {"SOURCE_SNAPSHOT", "TIME_INTERVAL", "STATE_REVISION"}
)


def fact_boundary_observed(boundary: dict[str, Any], observation: dict[str, Any]) -> bool:
    """Return whether *boundary* was observed by *observation*.

    Each legal kind is matched against the exact binding the Observation carries, so a
    mismatched snapshot identity, effective window or State revision is never accepted,
    and an unknown kind is always rejected.
    """

    kind = boundary.get("kind")
    if kind == "SOURCE_SNAPSHOT":
        declared = {reference["id"] for reference in observation["source_snapshot_refs"]}
        return bool(
            boundary["identity"] in declared
            and boundary["start"] is None
            and boundary["end"] is None
        )
    if kind == "TIME_INTERVAL":
        window = observation["time_boundary"]
        return bool(
            boundary["start"] == window["target_effective_start"]
            and boundary["end"] == window["target_effective_end"]
        )
    if kind == "STATE_REVISION":
        revision = observation["state_revision_observed"]
        return bool(boundary["start"] == revision and boundary["end"] == revision)
    return False
