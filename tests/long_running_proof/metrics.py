"""Phase 20 -- raw metric dataset and deterministic aggregation (Issue #86 sections 9-10).

Every metric is derived from the raw event list alone (``SUMMARY_DERIVABLE_FROM_RAW_DATA=
true``): :func:`aggregate` takes only ``list[dict]`` raw events and recomputes every number
from them, never from a running counter the orchestrator kept privately. A caller with only the
raw event log (e.g. after editing/removing one event, for the required negative control proving
that changes derived metrics) gets an identical aggregation function to call -- there is no
second, orchestrator-private code path that could silently diverge from this one.

Raw event ``kind`` values used by this proof: ``cycle_committed``, ``cycle_refused`` (a
negative-control cycle that failed to commit, deliberately kept in the dataset --
``FAILURES_NOT_EXCLUDED_FROM_DATASET=true``), ``session_loss_boundary``, ``agent_swap``,
``runtime_observation``. Each event is a plain, JSON-serializable dict -- the actual raw
dataset this Issue's own "raw event and record references" canonical output names.
"""

from __future__ import annotations

from datetime import UTC
from typing import Any


def cycle_committed_event(
    *,
    k: int,
    difference_id: str,
    state_revision: int,
    evidence_item_count: int,
    evidence_required_count: int,
    started_at: str,
    closed_at: str,
) -> dict[str, Any]:
    return {
        "kind": "cycle_committed",
        "cycle": k,
        "difference_id": difference_id,
        "state_revision": state_revision,
        "terminal_status": "CLOSED",
        "evidence_item_count": evidence_item_count,
        "evidence_required_count": evidence_required_count,
        "started_at": started_at,
        "closed_at": closed_at,
    }


def cycle_refused_event(*, k: int, reason: str, started_at: str) -> dict[str, Any]:
    return {"kind": "cycle_refused", "cycle": k, "reason": reason, "started_at": started_at}


def session_loss_boundary_event(
    *, after_cycle: int, pre_restart_revision: int, post_restart_revision: int, recovered: bool
) -> dict[str, Any]:
    return {
        "kind": "session_loss_boundary",
        "after_cycle": after_cycle,
        "pre_restart_revision": pre_restart_revision,
        "post_restart_revision": post_restart_revision,
        "recovered": recovered,
    }


def agent_swap_event(
    *,
    swap_index: int,
    predecessor_identity: dict[str, Any],
    successor_identity: dict[str, Any],
    succeeded: bool,
) -> dict[str, Any]:
    return {
        "kind": "agent_swap",
        "swap_index": swap_index,
        "predecessor_identity": predecessor_identity,
        "successor_identity": successor_identity,
        "succeeded": succeeded,
    }


def runtime_observation_event(*, classification: str, transport_outcome: str) -> dict[str, Any]:
    return {
        "kind": "runtime_observation",
        "classification": classification,
        "transport_outcome": transport_outcome,
    }


def human_intervention_event(*, reason: str) -> dict[str, Any]:
    return {"kind": "human_intervention", "reason": reason}


def human_re_explanation_event(*, reason: str) -> dict[str, Any]:
    return {"kind": "human_re_explanation", "reason": reason}


def rework_event(*, cycle: int, reason: str) -> dict[str, Any]:
    return {"kind": "rework", "cycle": cycle, "reason": reason}


def authority_violation_event(*, blocked: bool, description: str) -> dict[str, Any]:
    return {"kind": "authority_violation", "blocked": blocked, "description": description}


def false_completion_event(*, cycle: int) -> dict[str, Any]:
    return {"kind": "false_completion", "cycle": cycle}


def aggregate(raw_events: list[dict[str, Any]]) -> dict[str, Any]:
    """The one deterministic aggregator -- every metric below is recomputed from *raw_events*
    alone, with its own denominator recorded alongside it
    (``METRIC_DENOMINATORS_RECORDED=true``). ``UNKNOWN`` runtime observations are counted, not
    treated as zero (``UNKNOWN_NE_ZERO=true``)."""

    committed = [e for e in raw_events if e["kind"] == "cycle_committed"]
    refused = [e for e in raw_events if e["kind"] == "cycle_refused"]
    false_completions = [e for e in raw_events if e["kind"] == "false_completion"]
    session_losses = [e for e in raw_events if e["kind"] == "session_loss_boundary"]
    swaps = [e for e in raw_events if e["kind"] == "agent_swap"]
    runtime_observations = [e for e in raw_events if e["kind"] == "runtime_observation"]
    human_interventions = [e for e in raw_events if e["kind"] == "human_intervention"]
    human_re_explanations = [e for e in raw_events if e["kind"] == "human_re_explanation"]
    reworks = [e for e in raw_events if e["kind"] == "rework"]
    authority_violations = [e for e in raw_events if e["kind"] == "authority_violation"]

    terminal_completions = len(committed)
    false_completion_numerator = len(false_completions)

    runtime_counts = {"REACHABLE": 0, "UNREACHABLE": 0, "UNKNOWN": 0}
    for e in runtime_observations:
        runtime_counts[e["classification"]] = runtime_counts.get(e["classification"], 0) + 1
    runtime_total = len(runtime_observations)

    session_loss_recovered = sum(1 for e in session_losses if e["recovered"])
    swap_succeeded = sum(1 for e in swaps if e["succeeded"])

    evidence_item_total = sum(e["evidence_item_count"] for e in committed)
    evidence_required_total = sum(e["evidence_required_count"] for e in committed)

    closure_durations_seconds = [
        _elapsed_seconds(e["started_at"], e["closed_at"]) for e in committed
    ]

    return {
        "false_completion_rate": {
            "numerator": false_completion_numerator,
            "denominator": terminal_completions,
            "rate": _safe_rate(false_completion_numerator, terminal_completions),
        },
        "human_intervention_count": len(human_interventions),
        "human_re_explanation_count": len(human_re_explanations),
        "rework_count": len(reworks),
        "runtime_reachability": {
            "reachable": runtime_counts["REACHABLE"],
            "unreachable": runtime_counts["UNREACHABLE"],
            "unknown": runtime_counts["UNKNOWN"],
            "total": runtime_total,
            "rate": _safe_rate(runtime_counts["REACHABLE"], runtime_total),
        },
        "state_reconstruction_success": {
            "numerator": session_loss_recovered,
            "denominator": len(session_losses),
            "rate": _safe_rate(session_loss_recovered, len(session_losses)),
        },
        "session_loss_recovery_success": {
            "numerator": session_loss_recovered,
            "denominator": len(session_losses),
            "rate": _safe_rate(session_loss_recovered, len(session_losses)),
        },
        "agent_swap_success": {
            "numerator": swap_succeeded,
            "denominator": len(swaps),
            "rate": _safe_rate(swap_succeeded, len(swaps)),
        },
        "authority_violation_count": {
            "blocked": sum(1 for e in authority_violations if e["blocked"]),
            "passed_through": sum(1 for e in authority_violations if not e["blocked"]),
        },
        "evidence_completeness": {
            "numerator": evidence_item_total,
            "denominator": evidence_required_total,
            "rate": _safe_rate(evidence_item_total, evidence_required_total),
        },
        "time_to_structural_closure_seconds": {
            "count": len(closure_durations_seconds),
            "total": sum(closure_durations_seconds),
            "mean": (
                sum(closure_durations_seconds) / len(closure_durations_seconds)
                if closure_durations_seconds
                else None
            ),
        },
        "raw_event_count": len(raw_events),
        "committed_cycle_count": len(committed),
        "refused_cycle_count": len(refused),
    }


def _safe_rate(numerator: int, denominator: int) -> float | None:
    """``ZERO_DENOMINATOR_HANDLING_DECLARED=true``: an empty denominator yields ``None``
    (undefined), never a silently substituted ``0.0`` or ``1.0``."""

    if denominator == 0:
        return None
    return numerator / denominator


def _elapsed_seconds(started_at: str, ended_at: str) -> float:
    """Real elapsed wall-clock seconds between two :func:`~tests.long_running_proof.
    orchestrator._observed_now` reads (P87-R1-F9) -- microsecond-precision
    ``%Y-%m-%dT%H:%M:%S.%fZ``, genuinely variable across cycles (including any real
    session-loss restart/retry time a boundary injected), never the fixed-second corpus clock
    a deterministic identity timestamp would produce."""

    from datetime import datetime

    fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
    start = datetime.strptime(started_at, fmt).replace(tzinfo=UTC)
    end = datetime.strptime(ended_at, fmt).replace(tzinfo=UTC)
    return (end - start).total_seconds()
