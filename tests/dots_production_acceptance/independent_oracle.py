"""WU2: independent judgment per
``docs/validation/dots_production_acceptance/PROTOCOL.md`` Sec.7.

The oracle never uses Kernel closure as its own ground truth -- it judges from
independently-supplied readback/probe data only. Pure function module: no Kernel/Store
call of its own (callers pass in whatever Store/external reads they already performed
through the real canonical routes; this module adds no second read path of its own).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from manosube_agent_civilization.work_time_transparency.clock import default_clock

EVALUATION_AXES = (
    "false_completion",
    "long_term_state_retention",
    "runtime_reachability",
    "human_re_explanation",
    "rework",
    "agent_swap",
    "authority_violation",
    "evidence_completeness",
)

AxisEvaluator = Callable[[str, dict[str, Any], dict[str, Any]], bool | None]


class IndependentOracleError(Exception):
    """Raised for a judgment request this oracle cannot honestly answer -- e.g. a
    missing case_id or rationale -- refuses rather than fabricating a verdict."""


@dataclass(frozen=True)
class FeasibilityJudgment:
    case_id: str
    feasible: bool
    rationale: str
    judged_at: str


def pre_register_feasibility(
    case_id: str,
    *,
    feasible: bool,
    rationale: str,
    clock: Callable[[], str] = default_clock,
) -> FeasibilityJudgment:
    """PROTOCOL.md Sec.7: feasibility is judged BEFORE the case runs, from the task spec
    alone -- never decided after seeing the outcome. Call this once per case/task,
    before dispatch; ``MEASUREMENT_CONTRACT.md``'s denominator formula treats this
    value as fixed alongside ``case_classification``."""

    if not case_id or not rationale:
        raise IndependentOracleError("pre_register_feasibility requires case_id and rationale")
    return FeasibilityJudgment(case_id=case_id, feasible=feasible, rationale=rationale, judged_at=clock())


def _unknown_axis_evaluator(_axis: str, _readback: dict[str, Any], _spec: dict[str, Any]) -> bool | None:
    """The default axis evaluator: UNKNOWN for every axis. An oracle that was not given
    a real per-axis evaluator must say it doesn't know, never guess False/0."""

    return None


def _judge_outcome(external_readback: dict[str, Any], expected_spec: dict[str, Any]) -> str:
    """The oracle's own outcome judgment, from readback vs. spec alone. Returns
    ``"SATISFIED"`` / ``"NOT_SATISFIED"`` / ``"UNKNOWN"`` -- UNKNOWN whenever the
    readback itself doesn't contain what's needed to judge, or the spec's own check
    cannot be evaluated; never defaulted to NOT_SATISFIED (that would silently convert
    missing information into a specific negative claim)."""

    required_keys = expected_spec.get("required_readback_keys", ())
    if any(key not in external_readback for key in required_keys):
        return "UNKNOWN"
    check = expected_spec.get("check")
    if check is None:
        return "UNKNOWN"
    try:
        satisfied = check(external_readback)
    except Exception:
        return "UNKNOWN"
    return "SATISFIED" if satisfied else "NOT_SATISFIED"


DiscrepancyEvaluator = Callable[[str, str, str], bool]


@dataclass(frozen=True)
class OracleVerdict:
    case_id: str
    axis_judgments: dict[str, bool | None]  # keyed by EVALUATION_AXES; None == UNKNOWN
    model_claimed_outcome: str
    kernel_recorded_outcome: str
    oracle_judged_outcome: str
    discrepancy: bool | None  # None == not evaluated (no discrepancy_evaluator given)
    judged_at: str


def judge_from_readback(
    case_id: str,
    *,
    model_claimed_outcome: str,
    kernel_recorded_outcome: str,
    external_readback: dict[str, Any],
    expected_spec: dict[str, Any],
    axis_evaluator: AxisEvaluator | None = None,
    discrepancy_evaluator: DiscrepancyEvaluator | None = None,
    clock: Callable[[], str] = default_clock,
) -> OracleVerdict:
    """PROTOCOL.md Sec.7: judges purely from *external_readback* (an independent read
    the caller already performed, e.g. via the real
    ``FileStateStore.read_current_consistent`` or an actual external-system probe --
    never re-derived here) against *expected_spec*.

    *model_claimed_outcome* and *kernel_recorded_outcome* are recorded for comparison
    and discrepancy reporting only -- neither is ever substituted for the oracle's own
    independent judgment, per this document's own rule that the model's completion
    claim, the Kernel's own decision, human acceptance, and the actual outcome are each
    saved in separate fields, never merged into one.

    This oracle's own outcome vocabulary (``SATISFIED``/``NOT_SATISFIED``/``UNKNOWN``)
    is not the same vocabulary a model or the Kernel reports its own outcome in (e.g.
    ``SUCCEEDED``/``FAILED``/``TIMEOUT``, or Reflow's own
    ``CLOSED``/``NOT_SATISFIED``/``BLOCKED``/``STALE``/``CONTRADICTED``/``REVOKED``), so
    a bare string-equality check between them is meaningless and would report a
    "discrepancy" on nearly every genuinely-agreeing case. *discrepancy_evaluator*, if
    given, is called as
    ``discrepancy_evaluator(oracle_judged_outcome, model_claimed_outcome, kernel_recorded_outcome) -> bool``
    with the caller's own real cross-vocabulary mapping; without one, ``discrepancy`` is
    left ``None`` (not evaluated) rather than guessed from a comparison that doesn't
    actually mean what it would look like it means.

    *axis_evaluator*, if given, is called once per axis in :data:`EVALUATION_AXES` as
    ``axis_evaluator(axis_name, external_readback, expected_spec) -> True/False/None``;
    the default evaluator reports every axis ``None`` (UNKNOWN) -- an oracle that cannot
    evaluate an axis must say so, not guess."""

    if not case_id:
        raise IndependentOracleError("judge_from_readback requires case_id")

    evaluator = axis_evaluator or _unknown_axis_evaluator
    axis_judgments = {axis: evaluator(axis, external_readback, expected_spec) for axis in EVALUATION_AXES}

    oracle_judged_outcome = _judge_outcome(external_readback, expected_spec)
    discrepancy = (
        discrepancy_evaluator(oracle_judged_outcome, model_claimed_outcome, kernel_recorded_outcome)
        if discrepancy_evaluator is not None
        else None
    )

    return OracleVerdict(
        case_id=case_id,
        axis_judgments=axis_judgments,
        model_claimed_outcome=model_claimed_outcome,
        kernel_recorded_outcome=kernel_recorded_outcome,
        oracle_judged_outcome=oracle_judged_outcome,
        discrepancy=discrepancy,
        judged_at=clock(),
    )
