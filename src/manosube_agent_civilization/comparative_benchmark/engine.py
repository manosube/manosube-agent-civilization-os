"""Pure record builders and deterministic aggregation for the Comparative Benchmark
package (Issue #89, `ADOPT_PHASE_21_COMPARATIVE_BENCHMARK`).

Performs no Store I/O and reads no clock -- every input is already assembled and verified by
its own caller, identical to the discipline `long_running_proof_artifact/engine.py` and every
other package's own `engine.py` in this repository already states. This module never imports
from `tests/` -- the actual comparison-group runners (which drive the frozen corpus through
either the real natural route or the disclosed ungated baseline harness) live in
`tests/comparative_benchmark/`, and hand this module only already-computed raw events.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import operator as _operator
import os
from typing import Any, Callable

from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as _CANONICAL_SCHEMA_BASE,
    validate_record as _validate_record,
)

from .errors import (
    ProtocolFreezeValidationError,
    ReproductionReceiptValidationError,
    ResultBundleValidationError,
)
from .identity import (
    protocol_freeze_id,
    protocol_freeze_semantic_fingerprint,
    reproduction_receipt_id,
    reproduction_receipt_semantic_fingerprint,
    result_bundle_id,
    result_bundle_semantic_fingerprint,
)
from .types import COMPARISON_GROUP_ROLES, REPRODUCTION_AGREEMENTS, TASK_OUTCOMES

SCHEMA_VERSION = "0.1"
COMPARATIVE_BENCHMARK_SCHEMA_BASE = _CANONICAL_SCHEMA_BASE + "comparative_benchmark/"

#: The five machine-checkable comparison operators a `numeric_thresholds`/`threshold_evaluations`
#: entry may declare (P90-R1-F7: thresholds carry a real, evaluable operator/value, never an
#: informational-only free-text rule).
_THRESHOLD_OPERATORS: dict[str, Callable[[int, int], bool]] = {
    ">=": _operator.ge,
    "<=": _operator.le,
    ">": _operator.gt,
    "<": _operator.lt,
    "==": _operator.eq,
}


def _detach(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _detach(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_detach(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_detach(item) for item in value)
    return value


def stringify_floats(value: Any) -> Any:
    """Recursively replace every ``float`` in *value* with ``repr(value)`` -- Python's own
    shortest round-tripping decimal representation -- leaving every other JSON-representable
    value untouched.

    Identical to :func:`~manosube_agent_civilization.long_running_proof_artifact.engine.
    stringify_floats`: :mod:`~manosube_agent_civilization.state.canonicalize`'s own
    ``MANOSUBE-CANONICAL-JSON-0.1`` profile prohibits floating-point values outright
    (``UnsupportedValueError``), so a `resource_budget_manifest` timeout/budget expressed in
    fractional seconds can never be embedded in this protocol freeze's content-addressed body
    as-is. This is the one deterministic, lossless (``float(repr(x)) == x`` for every finite
    ``x`` Python can produce) encoding this package uses."""

    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, Mapping):
        return {key: stringify_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [stringify_floats(item) for item in value]
    return value


def _validate(
    record: dict[str, Any], schema_name: str, context: str, error_cls: type[Exception]
) -> None:
    try:
        _validate_record(record, schema_name, base=COMPARATIVE_BENCHMARK_SCHEMA_BASE)
    except DifferenceValidationError as error:
        raise error_cls(f"{context}: {error}") from error


def build_protocol_freeze(
    *,
    project_id: str,
    project_binding_ref: Mapping[str, str],
    corpus_manifest: Mapping[str, Any],
    comparison_groups: Sequence[Mapping[str, Any]],
    authority_boundary_equivalence_manifest: Mapping[str, Any],
    resource_budget_manifest: Mapping[str, Any],
    metric_definitions: Sequence[Mapping[str, Any]],
    numeric_thresholds: Sequence[Mapping[str, Any]],
    unknown_missing_handling: Mapping[str, Any],
    exclusion_policy: Mapping[str, Any],
    claim_vocabulary: Sequence[Mapping[str, Any]],
    reproduction_procedure: Mapping[str, Any],
    comparability_loss_receipts: Sequence[Mapping[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    """Build one canonical `comparative_benchmark_protocol_freeze` record -- Issue #89's own
    required pre-result freeze, immutable and content-addressed before any benchmark result
    may be executed or observed (`PROTOCOL_FROZEN_BEFORE_RESULTS=true`).

    Fail-closed structural check this builder itself performs (never delegated to a caller's
    own honesty): every `comparison_groups` member declares exactly one of
    :data:`COMPARISON_GROUP_ROLES`, and the set of `mechanism_identity` values used by
    `MANOSUBE_PRESENT` groups is disjoint from the set used by `MANOSUBE_ABSENT` groups --
    "same-Agent comparison, MANOSUBE present vs absent" is a structural fact this function
    enforces, never a label a caller could apply to two groups sharing one mechanism."""

    comparison_groups = [_detach(group) for group in comparison_groups]
    if len(comparison_groups) < 2:
        raise ProtocolFreezeValidationError(
            f"comparison_groups must declare at least 2 groups, got {len(comparison_groups)}"
        )
    present_mechanisms: set[tuple[Any, ...]] = set()
    absent_mechanisms: set[tuple[Any, ...]] = set()
    seen_ids: set[str] = set()
    group_ids: set[str] = set()
    for group in comparison_groups:
        role = group.get("comparison_group_role")
        if role not in COMPARISON_GROUP_ROLES:
            raise ProtocolFreezeValidationError(
                f"unrecognized comparison_group_role: {role!r} -- must be one of "
                f"{sorted(COMPARISON_GROUP_ROLES)!r}"
            )
        group_id = group.get("comparison_group_id")
        if not isinstance(group_id, str) or not group_id:
            raise ProtocolFreezeValidationError(
                "every comparison_groups member requires a non-empty comparison_group_id"
            )
        if group_id in seen_ids:
            raise ProtocolFreezeValidationError(f"duplicate comparison_group_id: {group_id!r}")
        seen_ids.add(group_id)
        group_ids.add(group_id)
        mechanism = group.get("mechanism_identity", {})
        mechanism_key = tuple(sorted(mechanism.items()))
        (present_mechanisms if role == "MANOSUBE_PRESENT" else absent_mechanisms).add(mechanism_key)
    if present_mechanisms & absent_mechanisms:
        raise ProtocolFreezeValidationError(
            "MANOSUBE_PRESENT and MANOSUBE_ABSENT groups must never share a mechanism_identity "
            "-- same-Agent comparison requires the presence/absence of MANOSUBE to be a "
            "genuinely distinct mechanism, not a relabeled identical one"
        )
    if not present_mechanisms or not absent_mechanisms:
        raise ProtocolFreezeValidationError(
            "at least one MANOSUBE_PRESENT and one MANOSUBE_ABSENT comparison group is required"
        )

    numeric_thresholds = [_detach(item) for item in numeric_thresholds]
    for entry in numeric_thresholds:
        threshold_group_id = entry.get("comparison_group_id")
        if threshold_group_id not in group_ids:
            raise ProtocolFreezeValidationError(
                f"numeric_thresholds entry references comparison_group_id "
                f"{threshold_group_id!r} that comparison_groups never declares"
            )
        if entry.get("operator") not in _THRESHOLD_OPERATORS:
            raise ProtocolFreezeValidationError(
                f"numeric_thresholds entry declares unrecognized operator {entry.get('operator')!r}"
            )

    claim_vocabulary = [_detach(item) for item in claim_vocabulary]
    for entry in claim_vocabulary:
        for claim_group_id in entry.get("subject_group_ids", []):
            if claim_group_id not in group_ids:
                raise ProtocolFreezeValidationError(
                    f"claim_vocabulary entry {entry.get('claim_id')!r} references "
                    f"comparison_group_id {claim_group_id!r} that comparison_groups never "
                    "declares"
                )

    project_id = str(project_id)
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_freeze_id": "",
        "protocol_freeze_semantic_fingerprint": "",
        "project_id": project_id,
        "project_binding_ref": _detach(project_binding_ref),
        "corpus_manifest": _detach(corpus_manifest),
        "comparison_groups": comparison_groups,
        "authority_boundary_equivalence_manifest": _detach(authority_boundary_equivalence_manifest),
        "resource_budget_manifest": stringify_floats(_detach(resource_budget_manifest)),
        "metric_definitions": [_detach(item) for item in metric_definitions],
        "numeric_thresholds": numeric_thresholds,
        "unknown_missing_handling": _detach(unknown_missing_handling),
        "exclusion_policy": _detach(exclusion_policy),
        "claim_vocabulary": claim_vocabulary,
        "reproduction_procedure": _detach(reproduction_procedure),
        "comparability_loss_receipts": [_detach(item) for item in comparability_loss_receipts],
        "generated_at": generated_at,
    }
    record["protocol_freeze_id"] = protocol_freeze_id(record)
    record["protocol_freeze_semantic_fingerprint"] = protocol_freeze_semantic_fingerprint(record)
    _validate(
        record,
        "comparative_benchmark_protocol_freeze.schema.json",
        "generated comparative_benchmark_protocol_freeze",
        ProtocolFreezeValidationError,
    )
    return record


def aggregate_metrics(
    raw_events: Sequence[Mapping[str, Any]], protocol_freeze: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    """Deterministically recompute, per `comparison_group_id` declared in *protocol_freeze*,
    the count of every :data:`TASK_OUTCOMES` member among *raw_events* plus the total task
    count for that group -- `raw_event_count` doubles as the required denominator
    (`DENOMINATORS_RECORDED=true`). Never excludes a group with zero matching events (its own
    counts are all zero, never absent) and never folds one outcome into another
    (`UNKNOWN_NE_ZERO`/`REFUSAL_NE_SYSTEM_FAILURE`/`RETAINED_NE_CLOSED`)."""

    group_ids = [group["comparison_group_id"] for group in protocol_freeze["comparison_groups"]]
    metrics: dict[str, dict[str, Any]] = {
        group_id: {"raw_event_count": 0, **dict.fromkeys(sorted(TASK_OUTCOMES), 0)}
        for group_id in group_ids
    }
    for event in raw_events:
        group_id = event["comparison_group_id"]
        if group_id not in metrics:
            raise ResultBundleValidationError(
                f"raw event references comparison_group_id {group_id!r} the bound protocol "
                "freeze never declared"
            )
        outcome = event["outcome"]
        if outcome not in TASK_OUTCOMES:
            raise ResultBundleValidationError(f"unrecognized task outcome: {outcome!r}")
        metrics[group_id]["raw_event_count"] += 1
        metrics[group_id][outcome] += 1
    return metrics


def evaluate_numeric_thresholds(
    metrics: Mapping[str, Mapping[str, Any]], protocol_freeze: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Evaluate every `numeric_thresholds` entry *protocol_freeze* predeclares against the
    already-recomputed *metrics*, returning one `threshold_evaluations` entry per declared
    threshold with its own machine-checked `actual_value`/`passed` (P90-R1-F7: a threshold is a
    real, evaluable `(metric_name, comparison_group_id, operator, threshold_value)` tuple this
    function itself checks -- never an informational-only free-text rule a caller could claim
    passed or failed by assertion)."""

    evaluations: list[dict[str, Any]] = []
    for entry in protocol_freeze["numeric_thresholds"]:
        metric_name = entry["metric_name"]
        comparison_group_id = entry["comparison_group_id"]
        operator_symbol = entry["operator"]
        threshold_value = entry["threshold_value"]
        if comparison_group_id not in metrics:
            raise ResultBundleValidationError(
                f"numeric_thresholds entry references comparison_group_id "
                f"{comparison_group_id!r} the bound protocol freeze never declared"
            )
        if operator_symbol not in _THRESHOLD_OPERATORS:
            raise ResultBundleValidationError(
                f"numeric_thresholds entry declares unrecognized operator {operator_symbol!r}"
            )
        actual_value = metrics[comparison_group_id][metric_name]
        passed = _THRESHOLD_OPERATORS[operator_symbol](actual_value, threshold_value)
        evaluations.append(
            {
                "metric_name": metric_name,
                "comparison_group_id": comparison_group_id,
                "operator": operator_symbol,
                "threshold_value": threshold_value,
                "actual_value": actual_value,
                "passed": passed,
            }
        )
    return evaluations


def derive_bounded_claims(
    metrics: Mapping[str, Mapping[str, Any]], protocol_freeze: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Derive claims strictly from *metrics* and *protocol_freeze*'s own predeclared
    `claim_vocabulary` -- never a claim outside that closed, pre-registered vocabulary
    (`POST_HOC_METRIC_SUBSTITUTION_FORBIDDEN`-equivalent for claims). Each derived claim's own
    `statement` is produced by formatting the frozen `claim_statement_template` against the
    actual recomputed `computed_values` for its declared `subject_metric_name`/
    `subject_group_ids` (P90-R1-F5: a claim's rendered text is bound to the metrics that
    produced it, never independent boilerplate that happens to sit beside a metric)."""

    claims: list[dict[str, Any]] = []
    for entry in protocol_freeze["claim_vocabulary"]:
        subject_metric_name = entry["subject_metric_name"]
        subject_group_ids = list(entry["subject_group_ids"])
        computed_values: dict[str, int] = {}
        for group_id in subject_group_ids:
            if group_id not in metrics:
                raise ResultBundleValidationError(
                    f"claim_vocabulary entry {entry['claim_id']!r} references "
                    f"comparison_group_id {group_id!r} the bound protocol freeze never declared"
                )
            computed_values[group_id] = metrics[group_id][subject_metric_name]
        try:
            statement = entry["claim_statement_template"].format(**computed_values)
        except (KeyError, IndexError) as error:
            raise ResultBundleValidationError(
                f"claim_vocabulary entry {entry['claim_id']!r} claim_statement_template "
                f"references a placeholder outside its own declared subject_group_ids: {error}"
            ) from error
        claims.append(
            {
                "claim_id": entry["claim_id"],
                "statement": statement,
                "bound": entry["bound"],
                "subject_metric_name": subject_metric_name,
                "subject_group_ids": subject_group_ids,
                "computed_values": computed_values,
            }
        )
    return claims


def build_result_bundle(
    *,
    project_id: str,
    project_binding_ref: Mapping[str, str],
    protocol_freeze: Mapping[str, Any],
    raw_events: Sequence[Mapping[str, Any]],
    environment_manifest: Mapping[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """Build one canonical `comparative_benchmark_result_bundle` record. `metrics`, `claims`,
    and `threshold_evaluations` are always recomputed here from *raw_events* and
    *protocol_freeze* alone (`SUMMARY_DERIVABLE_FROM_RAW_DATA=true`) -- this function accepts
    no caller-supplied metrics/claims/threshold-evaluation shortcut. `protocol_freeze_ref`
    carries both the bound protocol freeze's own id and its full semantic fingerprint
    (P90-R1-F4/F6: a child record names which exact frozen policy content it ran against, not
    merely which id -- a same-id, different-content freeze can never be silently substituted).
    `generation_process_id` records the real OS process id this bundle was built in, so a later
    reproduction receipt can machine-verify it ran in a genuinely separate process
    (P90-R1-F3)."""

    raw_events = [_detach(event) for event in raw_events]
    metrics = aggregate_metrics(raw_events, protocol_freeze)
    claims = derive_bounded_claims(metrics, protocol_freeze)
    threshold_evaluations = evaluate_numeric_thresholds(metrics, protocol_freeze)

    project_id = str(project_id)
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result_bundle_id": "",
        "result_bundle_semantic_fingerprint": "",
        "project_id": project_id,
        "project_binding_ref": _detach(project_binding_ref),
        "protocol_freeze_ref": {
            "protocol_freeze_id": protocol_freeze["protocol_freeze_id"],
            "protocol_freeze_semantic_fingerprint": protocol_freeze[
                "protocol_freeze_semantic_fingerprint"
            ],
        },
        "raw_events": raw_events,
        "metrics": metrics,
        "claims": claims,
        "threshold_evaluations": threshold_evaluations,
        "environment_manifest": _detach(environment_manifest),
        "generation_process_id": os.getpid(),
        "generated_at": generated_at,
    }
    record["result_bundle_id"] = result_bundle_id(record)
    record["result_bundle_semantic_fingerprint"] = result_bundle_semantic_fingerprint(record)
    _validate(
        record,
        "comparative_benchmark_result_bundle.schema.json",
        "generated comparative_benchmark_result_bundle",
        ResultBundleValidationError,
    )
    return record


def build_reproduction_receipt(
    *,
    project_id: str,
    project_binding_ref: Mapping[str, str],
    protocol_freeze: Mapping[str, Any],
    original_result_bundle: Mapping[str, Any],
    reproducer_identity: Mapping[str, Any],
    reproduced_raw_events: Sequence[Mapping[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    """Build one canonical `comparative_benchmark_reproduction_receipt`. `reproduced_metrics`
    is always recomputed here from *reproduced_raw_events* alone, and `agreement` is always
    derived by this function (never accepted from a caller) by comparing the recomputation
    against the *original* bundle's own `metrics` -- a reproducer's own claimed agreement can
    never substitute for this function's own independent recomputation
    (`SELF_RUN_REPRODUCTION_CANNOT_IMPERSONATE_INDEPENDENT_RECEIPT`-equivalent: this function
    performs the comparison itself, no matter what *reproducer_identity* claims).

    Refuses fail-closed (`ReproductionReceiptValidationError`) whenever
    `reproducer_identity["reproduction_process_id"]` equals the *original* bundle's own
    `generation_process_id` -- a reproduction that shares its OS process with the run it claims
    to independently reproduce is a self-assertion, not a genuinely separate execution
    (P90-R1-F3), and this function itself enforces that boundary rather than trusting a caller's
    own `is_original_author`/process-identity claim."""

    reproduction_process_id = reproducer_identity.get("reproduction_process_id")
    if not isinstance(reproduction_process_id, int) or isinstance(reproduction_process_id, bool):
        raise ReproductionReceiptValidationError(
            "reproducer_identity requires an integer reproduction_process_id"
        )
    original_process_id = original_result_bundle.get("generation_process_id")
    if reproduction_process_id == original_process_id:
        raise ReproductionReceiptValidationError(
            f"reproduction_process_id {reproduction_process_id!r} is identical to the original "
            f"result bundle's own generation_process_id {original_process_id!r} -- a "
            "reproduction must run in a genuinely separate OS process; a reproducer cannot "
            "assert independence from within the same process that produced the original result"
        )
    reproduction_environment_manifest = reproducer_identity.get("reproduction_environment_manifest")
    if not isinstance(reproduction_environment_manifest, Mapping):
        raise ReproductionReceiptValidationError(
            "reproducer_identity requires a reproduction_environment_manifest object"
        )

    is_original_author = bool(reproducer_identity.get("is_original_author", False))
    reproduced_metrics = aggregate_metrics(reproduced_raw_events, protocol_freeze)
    original_metrics = original_result_bundle["metrics"]
    if set(reproduced_metrics) != set(original_metrics):
        agreement = "INCOMPARABLE"
    elif reproduced_metrics == original_metrics:
        agreement = "MATCH"
    else:
        agreement = "DIVERGENT"
    if agreement not in REPRODUCTION_AGREEMENTS:
        raise ReproductionReceiptValidationError(f"unrecognized agreement outcome: {agreement!r}")

    project_id = str(project_id)
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "reproduction_receipt_id": "",
        "reproduction_receipt_semantic_fingerprint": "",
        "project_id": project_id,
        "project_binding_ref": _detach(project_binding_ref),
        "protocol_freeze_ref": {
            "protocol_freeze_id": protocol_freeze["protocol_freeze_id"],
            "protocol_freeze_semantic_fingerprint": protocol_freeze[
                "protocol_freeze_semantic_fingerprint"
            ],
        },
        "original_result_bundle_ref": {
            "result_bundle_id": original_result_bundle["result_bundle_id"],
            "result_bundle_semantic_fingerprint": original_result_bundle[
                "result_bundle_semantic_fingerprint"
            ],
        },
        "reproducer_identity": {
            **_detach(reproducer_identity),
            "is_original_author": is_original_author,
        },
        "reproduced_metrics": reproduced_metrics,
        "agreement": agreement,
        "generated_at": generated_at,
    }
    record["reproduction_receipt_id"] = reproduction_receipt_id(record)
    record["reproduction_receipt_semantic_fingerprint"] = reproduction_receipt_semantic_fingerprint(
        record
    )
    _validate(
        record,
        "comparative_benchmark_reproduction_receipt.schema.json",
        "generated comparative_benchmark_reproduction_receipt",
        ReproductionReceiptValidationError,
    )
    return record


__all__ = [
    "COMPARATIVE_BENCHMARK_SCHEMA_BASE",
    "SCHEMA_VERSION",
    "aggregate_metrics",
    "build_protocol_freeze",
    "build_reproduction_receipt",
    "build_result_bundle",
    "derive_bounded_claims",
    "evaluate_numeric_thresholds",
    "stringify_floats",
]
