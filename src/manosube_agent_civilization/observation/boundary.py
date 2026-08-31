"""The single canonical Fact effective-boundary matching authority.

`NORMALIZED_FACT.md` gives a Normalized Fact three contract-legal effective boundary
forms. Deciding whether one of them was actually observed by a given Observation is a
single rule, owned here by the Observation element and reused by every downstream
consumer, so no second copy can drift.
"""

from __future__ import annotations

from datetime import datetime
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


def instant(value: str) -> datetime:
    """Parse a canonical UTC instant."""

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def time_boundary_within_scope(observation: dict[str, Any], scope: dict[str, Any]) -> bool:
    """Return whether *observation*'s time boundary falls inside the resolved Scope.

    The observation window, the Target effective window, the source snapshot instant and
    the Scope cutoff are one containment rule, owned here so the Observation Engine that
    reports completeness and any consumer that verifies the binding cannot disagree.
    """

    boundary = observation["time_boundary"]
    try:
        observed_start = instant(boundary["observation_started_at"])
        observed_end = instant(boundary["observation_ended_at"])
        effective_start = instant(boundary["target_effective_start"])
        effective_end = instant(boundary["target_effective_end"])
        snapshot = instant(boundary["source_snapshot_time"])
        scope_observed_start = instant(scope["observation_window"]["start"])
        scope_observed_end = instant(scope["observation_window"]["end"])
        scope_effective_start = instant(scope["target_effective_window"]["start"])
        scope_effective_end = instant(scope["target_effective_window"]["end"])
        cutoff = instant(scope["cutoff"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        observed_start <= observed_end
        and effective_start <= effective_end
        and scope_observed_start <= observed_start <= observed_end <= scope_observed_end
        and scope_effective_start <= effective_start <= effective_end <= scope_effective_end
        and effective_start <= snapshot <= observed_end
        and snapshot <= cutoff
    )
