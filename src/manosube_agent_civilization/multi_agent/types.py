"""Closed Multi-Agent Dynamic Execution vocabularies (Phase 19, Issue #77).

Every closed vocabulary this package needs that already exists elsewhere is *imported*, never
restated: :data:`~manosube_agent_civilization.model_runtime.types.MODEL_EXECUTION_CAPABILITIES`
(the one capability that exists system-wide today) and
:data:`~manosube_agent_civilization.model_runtime.types.MODEL_EXECUTION_OUTCOMES` (the seven
typed outcomes a bounded model execution may ever settle at) are reused verbatim as this
package's own capability and slot-outcome vocabularies -- P19-C5 and the proposal's own research
note both require this: "reuse model_runtime's own closed MODEL_EXECUTION_OUTCOMES vocabulary
directly -- do not invent a second one."

Every vocabulary declared *here* is new to this delivery and closed to exactly the members this
delivery's own contract names -- ``execution_order``, ``release_policy`` and ``conflict_policy``
each have exactly one member today because this delivery proves the mechanism once, not a
catalog of interchangeable policies (a second member is a future, disclosed extension, never an
open string).

``deep_freeze`` is a private, package-local copy of the identical ~15-line implementation every
other adapter-layer package in this repository already keeps for itself
(:func:`~manosube_agent_civilization.model_runtime.types.deep_freeze`,
:func:`~manosube_agent_civilization.runtime.types.deep_freeze`) -- deliberately duplicated
rather than imported, the same decoupling convention those two modules' own docstrings already
state for one another.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from manosube_agent_civilization.model_runtime.types import (
    MODEL_EXECUTION_CAPABILITIES,
    MODEL_EXECUTION_OUTCOMES,
)

#: Reused verbatim (see this module's own docstring). This delivery selects every slot's own
#: capability requirement from this exact frozenset -- never a second, package-local capability
#: vocabulary.
MULTI_AGENT_CAPABILITIES: frozenset[str] = MODEL_EXECUTION_CAPABILITIES

#: Reused verbatim. A slot's own attempt settles at exactly one of these seven outcomes --
#: the identical closed vocabulary :mod:`~manosube_agent_civilization.model_runtime.route`
#: itself computes, never re-derived or widened here.
MULTI_AGENT_SLOT_OUTCOMES: frozenset[str] = MODEL_EXECUTION_OUTCOMES

#: The one outcome, among :data:`MULTI_AGENT_SLOT_OUTCOMES`, that admits a non-null
#: ``result_fingerprint`` and a non-null ``model_execution_envelope_ref``.
ACCEPTED_SLOT_OUTCOME = "CANDIDATE_ACCEPTED"

#: P19-C2's own "execution ordering or concurrency groups" field, closed to one declared value
#: in this delivery. "Concurrent" here is a disclosed, honest, narrower claim than real
#: OS-level parallelism: it means this package's own orchestration loop declares, and enforces
#: by construction, no execution-order *dependency* between any two slots of one plan -- slot
#: N's own outcome is never read, branched on, or required by slot N-1's own execution. It does
#: not mean this delivery threads or schedules slots across real OS threads/async tasks, which
#: it does not build (see ``14_MULTI_AGENT/MULTI_AGENT_CONTRACT.md``'s own disclosed judgment
#: calls section).
EXECUTION_ORDERS: frozenset[str] = frozenset({"CONCURRENT"})
EXECUTION_ORDER = "CONCURRENT"

#: P19-C8's own release policy, closed to one declared value: every constructed Agent is
#: released as soon as its own slot reaches a terminal outcome (success, refusal, failure,
#: timeout, cancellation, or an uncaught error propagating past this package's own per-slot
#: ``try/finally``) -- never held open across slots, never batched.
RELEASE_POLICIES: frozenset[str] = frozenset({"RELEASE_ON_TERMINAL_OUTCOME"})
RELEASE_POLICY = "RELEASE_ON_TERMINAL_OUTCOME"

#: P19-C6's own conflict/aggregation policy, closed to one declared value: exact
#: ``result_fingerprint`` equality across every ``CANDIDATE_ACCEPTED`` attempt for the same
#: ``(plan, capability)`` group is "agreeing"; two or more distinct non-null fingerprints in
#: that group is "contradicting", with full membership preserved; there is no majority vote,
#: confidence average, or last-writer-wins anywhere in this policy's own computation.
CONFLICT_POLICIES: frozenset[str] = frozenset(
    {"EXACT_FINGERPRINT_EQUALITY_OR_EXPLICIT_DISAGREEMENT"}
)
CONFLICT_POLICY = "EXACT_FINGERPRINT_EQUALITY_OR_EXPLICIT_DISAGREEMENT"

#: P19-C2's own declared cancellation policy. Disclosed as a genesis-time declaration this
#: delivery does not runtime-enforce: no module in this package reads a clock, schedules a
#: timeout, or cancels a running Agent -- an adapter that hangs simply has not returned yet.
#: A slot's own ``TIMEOUT``/``CANCELLED`` outcome is honestly representable in
#: :data:`MULTI_AGENT_SLOT_OUTCOMES` (Model Runtime's own adapter may report it), but nothing
#: in this package *produces* one by watching a deadline.
CANCELLATION_POLICIES: frozenset[str] = frozenset({"COOPERATIVE_PER_SLOT_TIMEOUT"})
CANCELLATION_POLICY = "COOPERATIVE_PER_SLOT_TIMEOUT"

#: Structural Review Round 3, P19-R3-F4: the real, wall-clock-bounded per-slot adapter-call
#: budget this delivery's default plans open with -- runtime-enforced (``route.py``'s own
#: bounded call around ``execute_model_work_unit``, not merely a declared, unread policy name).
#: A caller of :func:`~manosube_agent_civilization.multi_agent.route.open_dynamic_execution_plan`
#: may supply its own bound (a real test proving enforcement needs a much shorter one than this
#: production default), but every plan's own ``execution_bounds.per_slot_timeout_seconds`` is
#: always a real, positive, bounded whole number of seconds -- never absent, never read as a
#: no-op, and never a fraction: Canonical State's own v0.1 encoding prohibits floating-point
#: values entirely (:mod:`~manosube_agent_civilization.state.canonicalize`), so this bound is an
#: ``int``, the same convention every other ``timeout_seconds`` field in this repository already
#: keeps.
DEFAULT_PER_SLOT_TIMEOUT_SECONDS = 30

#: P19-C8's own release-receipt vocabulary. ``RELEASE_FAILED`` is carried honestly even though
#: :mod:`~manosube_agent_civilization.agent_runtime`'s own ``release()`` is documented
#: "local, idempotent, and zero-write" and cannot currently fail -- the record still states the
#: field rather than assuming success (see the proposal's own P19-C8 text).
RELEASE_STATUSES: frozenset[str] = frozenset({"RELEASED", "RELEASE_FAILED"})

#: P19-C6's own conflict-set member-kind vocabulary. ``AGREEING``/``CONTRADICTING`` classify a
#: capability's own group of accepted attempts; ``ABSENT`` names one slot whose own attempt did
#: not reach ``CANDIDATE_ACCEPTED`` at all -- first-class, never dropped from the set.
CONFLICT_MEMBER_KINDS: frozenset[str] = frozenset({"AGREEING", "CONTRADICTING", "ABSENT"})

#: The six non-accepting outcomes an ``ABSENT`` conflict-set member may ever carry -- exactly
#: :data:`MULTI_AGENT_SLOT_OUTCOMES` minus the one accepting outcome, reused rather than
#: restated as a fourth copy of the same six names.
ABSENT_MEMBER_OUTCOMES: frozenset[str] = MULTI_AGENT_SLOT_OUTCOMES - {ACCEPTED_SLOT_OUTCOME}

#: The terminal orchestration outcome vocabulary. ``ABORTED_RELEASE_INCOMPLETE`` names the
#: state P19-C8 requires to exist -- "blocks the orchestration attempt from claiming clean
#: terminal completion" -- but is, disclosed and by construction, unreachable through this
#: package's own public route in this delivery: :func:`~manosube_agent_civilization.
#: multi_agent.route.execute_dynamic_execution_plan` refuses (raises
#: :class:`~manosube_agent_civilization.multi_agent.errors.MultiAgentReleaseIncompleteError`)
#: before it would ever construct an aggregation input naming this outcome, because Phase 12's
#: own ``release()`` cannot currently fail. The vocabulary member -- and the engine-level
#: refusal a caller *could* reach by supplying a tampered, already-``RELEASE_FAILED`` receipt
#: directly to the engine's own builder -- exist so the schema is honest about the shape of a
#: real failure rather than only about the happy path.
ORCHESTRATION_OUTCOMES: frozenset[str] = frozenset(
    {
        "COMPLETED_ALL_RELEASED",
        "COMPLETED_WITH_UNRESOLVED_CAPABILITY",
        "ABORTED_RELEASE_INCOMPLETE",
    }
)


def deep_freeze(value: Any) -> Any:
    """Recursively rebuild *value* into an immutable, alias-free equivalent.

    Deliberately duplicated rather than imported from
    :mod:`~manosube_agent_civilization.model_runtime.types` or any other package's own copy --
    the identical decoupling convention this repository already keeps between every pair of
    adapter-layer packages that each need one.
    """

    if isinstance(value, Mapping):
        return {key: deep_freeze(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(deep_freeze(item) for item in value)
    return value


__all__ = [
    "ABSENT_MEMBER_OUTCOMES",
    "ACCEPTED_SLOT_OUTCOME",
    "CANCELLATION_POLICIES",
    "CANCELLATION_POLICY",
    "CONFLICT_MEMBER_KINDS",
    "CONFLICT_POLICIES",
    "CONFLICT_POLICY",
    "DEFAULT_PER_SLOT_TIMEOUT_SECONDS",
    "EXECUTION_ORDER",
    "EXECUTION_ORDERS",
    "MULTI_AGENT_CAPABILITIES",
    "MULTI_AGENT_SLOT_OUTCOMES",
    "ORCHESTRATION_OUTCOMES",
    "RELEASE_POLICIES",
    "RELEASE_POLICY",
    "RELEASE_STATUSES",
    "deep_freeze",
]
