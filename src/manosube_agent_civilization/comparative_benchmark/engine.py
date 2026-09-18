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

from collections.abc import Callable, Mapping, Sequence
import hashlib
import operator as _operator
import os
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as _CANONICAL_SCHEMA_BASE,
    validate_record as _validate_record,
)
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .errors import (
    IndependentReproducerTrustAnchorValidationError,
    IndependentReproductionSubmissionValidationError,
    ProtocolFreezeValidationError,
    ReproductionReceiptValidationError,
    ResultBundleValidationError,
)
from .identity import (
    independent_reproducer_trust_anchor_id,
    independent_reproducer_trust_anchor_semantic_fingerprint,
    independent_reproduction_submission_id,
    independent_reproduction_submission_semantic_fingerprint,
    independent_reproduction_submission_signing_payload,
    protocol_freeze_id,
    protocol_freeze_semantic_fingerprint,
    reproduction_receipt_id,
    reproduction_receipt_semantic_fingerprint,
    result_bundle_id,
    result_bundle_semantic_fingerprint,
)
from .types import COMPARISON_GROUP_ROLES, REPRODUCTION_AGREEMENTS, TASK_OUTCOMES

#: P90-R3-F2: the one signature algorithm an independent reproduction submission may declare.
#: Verification is duplicated here, deliberately, rather than imported from
#: `binding.signature.verify_ed25519_signature` -- importing `binding` at all transitively
#: executes `binding/route.py`'s own `from manosube_agent_civilization.authority.identity
#: import rule_id`, which would make this package a runtime importer of Authority even though
#: no single line inside this package's own five modules names it. This package's own static
#: conformance test (NC-9/NC-11: "never a second owner of / never imports Authority") is a
#: guarantee about substance, not merely about what an AST scan of this package's own literal
#: `import` statements happens to catch -- so this small, generic Ed25519 check (identical in
#: behavior to `binding.signature.verify_ed25519_signature`: fail-closed-as-a-value, never
#: raises on malformed key/signature material) is duplicated locally instead.
SUPPORTED_SIGNATURE_ALGORITHM = "ed25519"

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


def verify_exact_frozen_corpus(
    raw_events: Sequence[Mapping[str, Any]],
    protocol_freeze: Mapping[str, Any],
    *,
    error_cls: type[Exception] = ResultBundleValidationError,
) -> None:
    """P90-R2-F4: refuse *raw_events* unless, for every `comparison_group_id`
    *protocol_freeze* itself declares, that group's own raw events name exactly
    *protocol_freeze*'s own `corpus_manifest.task_ids` list, in that exact order, with no gap
    and no repeat. This is the production builder's own fail-closed corpus-fidelity gate
    (moved here from a test-only orchestrator guard so it can never be bypassed by calling
    `build_result_bundle`/`commit_result_bundle` directly) -- a partial, reordered, omitted,
    duplicated, substituted, or success-only-subset raw event set can never reach a durable
    commit through the public route. *error_cls* lets each caller raise its own record kind's
    own error type (`build_reproduction_receipt` passes `ReproductionReceiptValidationError`) --
    the failure is still the identical corpus-fidelity fact, never a different check."""

    expected_task_ids = tuple(protocol_freeze["corpus_manifest"]["task_ids"])
    declared_group_ids = [
        group["comparison_group_id"] for group in protocol_freeze["comparison_groups"]
    ]
    by_group: dict[str, list[str]] = {group_id: [] for group_id in declared_group_ids}
    for event in raw_events:
        group_id = event["comparison_group_id"]
        if group_id not in by_group:
            raise error_cls(
                f"raw event references comparison_group_id {group_id!r} the bound protocol "
                "freeze never declared"
            )
        by_group[group_id].append(event["task_id"])
    for group_id, task_ids in by_group.items():
        actual = tuple(task_ids)
        if actual != expected_task_ids:
            raise error_cls(
                f"comparison_group_id={group_id!r} attempted task_ids {actual!r}, expected "
                f"exactly the frozen corpus {expected_task_ids!r} in that exact order -- "
                "refusing a reordered, omitted, duplicated, substituted, or partial-scale "
                "corpus attempt before any result bundle is committed"
            )


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
    (P90-R1-F3). Refuses fail-closed, before constructing any record, unless *raw_events*
    covers exactly the frozen corpus for every declared comparison group (P90-R2-F4, see
    :func:`verify_exact_frozen_corpus`) -- no partial, reordered, duplicated, omitted, or
    success-only-subset dataset can ever reach a durable commit through this builder."""

    raw_events = [_detach(event) for event in raw_events]
    verify_exact_frozen_corpus(raw_events, protocol_freeze)
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
    own `is_original_author`/process-identity claim. Also refuses, via the identical
    :func:`verify_exact_frozen_corpus` gate `build_result_bundle` itself uses, any
    *reproduced_raw_events* that does not cover exactly the frozen corpus (P90-R2-F4), and
    persists *reproduced_raw_events* itself in the committed record -- not only their
    aggregated `reproduced_metrics` -- so a third party can rederive `reproduced_metrics`/
    `agreement` from the published raw bytes after reload, never trust a stored aggregate alone
    (P90-R2-F3)."""

    reproduced_raw_events = [_detach(event) for event in reproduced_raw_events]
    verify_exact_frozen_corpus(
        reproduced_raw_events, protocol_freeze, error_cls=ReproductionReceiptValidationError
    )

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
        "reproduced_raw_events": reproduced_raw_events,
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


def verify_ed25519_signature(*, public_key_hex: str, message: bytes, signature_hex: str) -> bool:
    """Whether *signature_hex* (a raw 64-byte Ed25519 signature, hex-encoded) is a genuine
    signature over *message* by the holder of the private key matching *public_key_hex* (a raw
    32-byte Ed25519 public key, hex-encoded). Never raises on a bad signature or malformed key/
    signature material -- returns ``False``, identical to
    `binding.signature.verify_ed25519_signature`'s own convention (see this module's own
    :data:`SUPPORTED_SIGNATURE_ALGORITHM` docstring for why this is a local duplicate rather
    than an import)."""

    try:
        public_key_bytes = bytes.fromhex(public_key_hex)
        signature_bytes = bytes.fromhex(signature_hex)
    except ValueError:
        return False
    try:
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature_bytes, message)
    except (InvalidSignature, ValueError):
        return False
    return True


def _reproduced_raw_events_content_address(
    reproduced_raw_events: Sequence[Mapping[str, Any]],
) -> str:
    digest = hashlib.sha256(canonical_json_bytes(list(reproduced_raw_events))).hexdigest()
    return "sha256:" + digest


def build_independent_reproducer_trust_anchor(
    *,
    project_id: str,
    project_binding_ref: Mapping[str, str],
    reproducer_actor_or_authority_id: str,
    ed25519_public_key: str,
    key_id: str,
    adoption_ref: Mapping[str, str],
    authorized_protocol_or_corpus_ref: Mapping[str, str],
    valid_from: str,
    valid_until: str | None,
    revocation_status: str,
    generated_at: str,
) -> dict[str, Any]:
    """Build one canonical `comparative_benchmark_independent_reproducer_trust_anchor` record
    (P90-R4-F2) -- the pre-registered admission of a distinct reproducer actor/authority's own
    Ed25519 public key, committed *before* that actor ever submits a reproduction, so
    `verify_independent_reproduction_submission` can resolve trust from this Store-committed
    record rather than the submission's own self-declared key
    (`DO_NOT_TRUST_A_PUBLIC_KEY_SUPPLIED_ONLY_BY_THE_SUBMISSION_BEING_VERIFIED`).

    `role` is always `"INDEPENDENT_PHASE_21_REPRODUCER"` and `admitted_by` is always
    `"HUMAN_AUTHORITY"` -- neither is a caller-supplied parameter, so this production builder can
    never admit a trust anchor under any other label
    (`ORIGINAL_OPERATOR_IDENTITY_REFUSED`/`CLAUDE_CODE_SESSION_IDENTITY_REFUSED`-equivalent at
    the builder itself); it also never generates the key pair this record names -- this module
    imports only `Ed25519PublicKey`, never the private-key counterpart (see the package's own
    static-conformance proof)."""

    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(ed25519_public_key))
    except ValueError as error:
        raise IndependentReproducerTrustAnchorValidationError(
            f"ed25519_public_key {ed25519_public_key!r} is not a structurally valid Ed25519 "
            f"public key: {error}"
        ) from error

    if valid_until is not None and valid_until <= valid_from:
        raise IndependentReproducerTrustAnchorValidationError(
            f"valid_until {valid_until!r} must be strictly after valid_from {valid_from!r}"
        )

    project_id = str(project_id)
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "trust_anchor_id": "",
        "trust_anchor_semantic_fingerprint": "",
        "project_id": project_id,
        "project_binding_ref": _detach(project_binding_ref),
        "reproducer_actor_or_authority_id": reproducer_actor_or_authority_id,
        "role": "INDEPENDENT_PHASE_21_REPRODUCER",
        "ed25519_public_key": ed25519_public_key,
        "key_id": key_id,
        "admitted_by": "HUMAN_AUTHORITY",
        "adoption_ref": _detach(adoption_ref),
        "authorized_protocol_or_corpus_ref": _detach(authorized_protocol_or_corpus_ref),
        "valid_from": valid_from,
        "valid_until": valid_until,
        "revocation_status": revocation_status,
        "generated_at": generated_at,
    }
    record["trust_anchor_id"] = independent_reproducer_trust_anchor_id(record)
    record["trust_anchor_semantic_fingerprint"] = (
        independent_reproducer_trust_anchor_semantic_fingerprint(record)
    )
    _validate(
        record,
        "comparative_benchmark_independent_reproducer_trust_anchor.schema.json",
        "generated comparative_benchmark_independent_reproducer_trust_anchor",
        IndependentReproducerTrustAnchorValidationError,
    )
    return record


def verify_independent_reproduction_submission(
    record: Mapping[str, Any],
    *,
    protocol_freeze: Mapping[str, Any],
    original_result_bundle: Mapping[str, Any],
    trust_anchor: Mapping[str, Any],
) -> None:
    """P90-R3-F2/P90-R4-F2: refuse *record* fail-closed
    (`IndependentReproductionSubmissionValidationError`) unless every one of the following
    independently holds -- this function only ever verifies an externally-supplied submission,
    it never builds or signs one itself (`CLAUDE_CODE_MAY_SELF_ISSUE_INDEPENDENT_RECEIPT=false`):

    * *record* validates against its own schema;
    * `independent_reproduction_submission_id`/`..._semantic_fingerprint` genuinely rederive
      from *record*'s own remaining fields (self-consistent identity, not a caller-asserted
      label);
    * `protocol_freeze_ref`/`original_result_bundle_ref` name exactly the already-resolved,
      Store-authoritative *protocol_freeze*/*original_result_bundle* this route itself resolved
      -- never a caller-supplied look-alike (the identical P90-R1-F6 discipline
      `commit_reproduction_receipt` already applies);
    * `reproduced_raw_events` covers exactly the frozen corpus (`verify_exact_frozen_corpus`);
    * `reproduced_raw_events_content_address` genuinely rederives from `reproduced_raw_events`;
    * `reproduced_metrics` genuinely rederives from `reproduced_raw_events` via
      `aggregate_metrics` -- a submitter's own claimed aggregate can never substitute for this
      function's own independent recomputation;
    * `agreement` genuinely rederives by the identical MATCH/DIVERGENT/INCOMPARABLE rule
      `build_reproduction_receipt` itself already uses, comparing against
      *original_result_bundle*'s own `metrics`;
    * *trust_anchor* -- a Store-resolved `comparative_benchmark_independent_reproducer_trust_
      anchor`, never the submission's own declared key alone
      (`DO_NOT_TRUST_A_PUBLIC_KEY_SUPPLIED_ONLY_BY_THE_SUBMISSION_BEING_VERIFIED`) -- is
      `revocation_status="ACTIVE"`, its own `reproducer_actor_or_authority_id` matches
      *record*'s declared one, its own `authorized_protocol_or_corpus_ref` matches *record*'s
      own `protocol_freeze_ref` (refusing cross-protocol/corpus replay of a trust anchor
      admitted for a different frozen protocol), and *record*'s own `submission_time` falls
      inside `[valid_from, valid_until)` (an unbounded `valid_until=None` never expires);
    * *record*'s own `signature.public_key` equals *trust_anchor*'s own registered
      `ed25519_public_key` exactly (`SUBMISSION_KEY_EQUALS_PRETRUSTED_KEY=true`,
      `SELF_DECLARED_KEY_ALONE_INSUFFICIENT=true` -- a self-declared key that merely matches
      itself is never sufficient);
    * `signature` is a genuine Ed25519 signature, by the holder of the private key matching
      *trust_anchor*'s own pre-registered `ed25519_public_key` -- never *record*'s own declared
      key, even though the two are also checked equal above -- over exactly
      `independent_reproduction_submission_signing_payload(record)`."""

    _validate(
        dict(record),
        "comparative_benchmark_independent_reproduction_submission.schema.json",
        "independent reproduction submission",
        IndependentReproductionSubmissionValidationError,
    )

    if record["independent_reproduction_submission_id"] != independent_reproduction_submission_id(
        record
    ):
        raise IndependentReproductionSubmissionValidationError(
            "independent_reproduction_submission_id does not rederive from this submission's "
            "own remaining fields"
        )
    if record[
        "independent_reproduction_submission_semantic_fingerprint"
    ] != independent_reproduction_submission_semantic_fingerprint(record):
        raise IndependentReproductionSubmissionValidationError(
            "independent_reproduction_submission_semantic_fingerprint does not rederive from "
            "this submission's own remaining fields"
        )

    declared_freeze_ref = record["protocol_freeze_ref"]
    if declared_freeze_ref != {
        "protocol_freeze_id": protocol_freeze["protocol_freeze_id"],
        "protocol_freeze_semantic_fingerprint": protocol_freeze[
            "protocol_freeze_semantic_fingerprint"
        ],
    }:
        raise IndependentReproductionSubmissionValidationError(
            "protocol_freeze_ref diverges from the Store's own resolved protocol freeze -- an "
            "independent reproduction submission must bind to the ledger's own authoritative "
            "freeze body, never a caller-supplied look-alike"
        )
    declared_bundle_ref = record["original_result_bundle_ref"]
    if declared_bundle_ref != {
        "result_bundle_id": original_result_bundle["result_bundle_id"],
        "result_bundle_semantic_fingerprint": original_result_bundle[
            "result_bundle_semantic_fingerprint"
        ],
    }:
        raise IndependentReproductionSubmissionValidationError(
            "original_result_bundle_ref diverges from the Store's own resolved result bundle "
            "-- an independent reproduction submission must bind to the ledger's own "
            "authoritative bundle body, never a caller-supplied look-alike"
        )

    reproduced_raw_events = record["reproduced_raw_events"]
    verify_exact_frozen_corpus(
        reproduced_raw_events,
        protocol_freeze,
        error_cls=IndependentReproductionSubmissionValidationError,
    )

    if record["reproduced_raw_events_content_address"] != _reproduced_raw_events_content_address(
        reproduced_raw_events
    ):
        raise IndependentReproductionSubmissionValidationError(
            "reproduced_raw_events_content_address does not rederive from reproduced_raw_events"
        )

    recomputed_metrics = aggregate_metrics(reproduced_raw_events, protocol_freeze)
    if record["reproduced_metrics"] != recomputed_metrics:
        raise IndependentReproductionSubmissionValidationError(
            "reproduced_metrics does not rederive from reproduced_raw_events -- a submitter's "
            "own claimed aggregate can never substitute for independent recomputation"
        )

    original_metrics = original_result_bundle["metrics"]
    if set(recomputed_metrics) != set(original_metrics):
        recomputed_agreement = "INCOMPARABLE"
    elif recomputed_metrics == original_metrics:
        recomputed_agreement = "MATCH"
    else:
        recomputed_agreement = "DIVERGENT"
    if record["agreement"] != recomputed_agreement:
        raise IndependentReproductionSubmissionValidationError(
            f"declared agreement {record['agreement']!r} does not match the recomputed "
            f"agreement {recomputed_agreement!r} between reproduced_metrics and the original "
            "result bundle's own metrics"
        )

    if trust_anchor.get("revocation_status") != "ACTIVE":
        raise IndependentReproductionSubmissionValidationError(
            "the resolved independent reproducer trust anchor is not ACTIVE -- a revoked trust "
            "anchor can never admit a submission, however genuine its signature"
        )
    if (
        trust_anchor.get("reproducer_actor_or_authority_id")
        != record["reproducer_actor_or_authority_id"]
    ):
        raise IndependentReproductionSubmissionValidationError(
            "the resolved independent reproducer trust anchor's own "
            "reproducer_actor_or_authority_id diverges from this submission's declared one"
        )
    if trust_anchor.get("authorized_protocol_or_corpus_ref") != declared_freeze_ref:
        raise IndependentReproductionSubmissionValidationError(
            "the resolved independent reproducer trust anchor was admitted for a different "
            "protocol_freeze_ref -- refusing cross-protocol/corpus replay of a trust anchor "
            "admitted for a different frozen protocol"
        )
    submission_time = record["submission_time"]
    valid_from = trust_anchor.get("valid_from")
    valid_until = trust_anchor.get("valid_until")
    if not (isinstance(valid_from, str) and submission_time >= valid_from):
        raise IndependentReproductionSubmissionValidationError(
            "this submission's own submission_time is before the resolved independent "
            "reproducer trust anchor's own valid_from -- refusing a submission the trust "
            "anchor was not yet in force for"
        )
    if valid_until is not None and submission_time >= valid_until:
        raise IndependentReproductionSubmissionValidationError(
            "this submission's own submission_time is at or after the resolved independent "
            "reproducer trust anchor's own valid_until -- refusing a submission made under a "
            "revoked or expired trust anchor"
        )

    signature = record["signature"]
    trust_anchor_public_key = trust_anchor.get("ed25519_public_key")
    if signature.get("public_key") != trust_anchor_public_key:
        raise IndependentReproductionSubmissionValidationError(
            "this submission's own declared signature.public_key diverges from the resolved "
            "independent reproducer trust anchor's own registered ed25519_public_key -- a "
            "self-declared key that merely matches itself is never sufficient "
            "(SELF_DECLARED_KEY_ALONE_INSUFFICIENT=true); only the pre-registered trust-anchor "
            "key is ever trusted"
        )
    if not verify_ed25519_signature(
        public_key_hex=trust_anchor_public_key,
        message=independent_reproduction_submission_signing_payload(record),
        signature_hex=signature["value"],
    ):
        raise IndependentReproductionSubmissionValidationError(
            "signature does not verify against the resolved independent reproducer trust "
            "anchor's own pre-registered public key over this submission's own signing payload "
            "-- refusing a submission whose own signature cannot structurally establish it came "
            "from the pre-trusted distinct actor"
        )


__all__ = [
    "COMPARATIVE_BENCHMARK_SCHEMA_BASE",
    "SCHEMA_VERSION",
    "SUPPORTED_SIGNATURE_ALGORITHM",
    "aggregate_metrics",
    "build_independent_reproducer_trust_anchor",
    "build_protocol_freeze",
    "build_reproduction_receipt",
    "build_result_bundle",
    "derive_bounded_claims",
    "evaluate_numeric_thresholds",
    "stringify_floats",
    "verify_ed25519_signature",
    "verify_exact_frozen_corpus",
    "verify_independent_reproduction_submission",
]
