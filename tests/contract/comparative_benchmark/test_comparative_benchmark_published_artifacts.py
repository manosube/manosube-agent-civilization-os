"""Phase 21 Comparative Benchmark -- Structural Review Round 1 (Issue #89, P90-R1-F2):
``MATERIALIZE_VERSIONED_PUBLIC_PROTOCOL_RESULT_AND_REPRODUCTION_ARTIFACTS``,
``INCLUDE_RAW_FAILURES_AND_ENVIRONMENT_MANIFEST``,
``PROVE_RELOAD_AND_REDERIVATION_FROM_THE_PUBLISHED_BYTES``.

Loads the three checked-in ``examples/comparative_benchmark/*.json`` files directly off disk
(``json.loads(Path(...).read_text())`` alone -- no Store, no fixture module, no orchestrator
call) and proves they are self-consistent and rederivable byte-for-byte from their own published
bytes alone: each validates against its own canonical schema; each record's own declared id and
semantic fingerprint fields are recomputed from the loaded body and match exactly
(``PUBLISHED_BYTES_RELOADABLE=true``); the result bundle's own ``metrics``/``claims``/
``threshold_evaluations`` are recomputed from its own loaded ``raw_events`` and the loaded
protocol freeze alone, and match the stored values exactly
(``REPRODUCED_RAW_EVENTS_DURABLY_REDERIVABLE=true``); the loaded raw events include at least one
real non-``COMPLETED_VERIFIED`` outcome (``FAILURES_PRESENT_IN_PUBLISHED_RAW_DATA=true``); and
the reproduction receipt's own ``agreement`` verdict is recomputed, from its own loaded
``reproduced_metrics`` compared against the loaded result bundle's own ``metrics``, using the
identical MATCH/DIVERGENT/INCOMPARABLE rule ``engine.build_reproduction_receipt`` itself applies,
and matches the stored value exactly.

Regenerate the three files with ``python scripts/generate_comparative_benchmark_artifacts.py``
(see ``examples/comparative_benchmark/README.md``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manosube_agent_civilization.comparative_benchmark.engine import (
    COMPARATIVE_BENCHMARK_SCHEMA_BASE,
    aggregate_metrics,
    derive_bounded_claims,
    evaluate_numeric_thresholds,
)
from manosube_agent_civilization.comparative_benchmark.identity import (
    protocol_freeze_id,
    protocol_freeze_semantic_fingerprint,
    reproduction_receipt_id,
    reproduction_receipt_semantic_fingerprint,
    result_bundle_id,
    result_bundle_semantic_fingerprint,
)
from manosube_agent_civilization.comparative_benchmark.types import REPRODUCTION_AGREEMENTS
from manosube_agent_civilization.difference.validation import validate_record

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARTIFACT_DIR = _REPO_ROOT / "examples" / "comparative_benchmark"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_ARTIFACT_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _protocol_freeze() -> dict[str, Any]:
    return _load("protocol_freeze")


def _result_bundle() -> dict[str, Any]:
    return _load("result_bundle")


def _reproduction_receipt() -> dict[str, Any]:
    return _load("reproduction_receipt")


# --- schema validity (loaded straight off disk, no in-process builder involved) --------------- #


def test_published_protocol_freeze_is_schema_valid() -> None:
    validate_record(
        _protocol_freeze(),
        "comparative_benchmark_protocol_freeze.schema.json",
        base=COMPARATIVE_BENCHMARK_SCHEMA_BASE,
    )


def test_published_result_bundle_is_schema_valid() -> None:
    validate_record(
        _result_bundle(),
        "comparative_benchmark_result_bundle.schema.json",
        base=COMPARATIVE_BENCHMARK_SCHEMA_BASE,
    )


def test_published_reproduction_receipt_is_schema_valid() -> None:
    validate_record(
        _reproduction_receipt(),
        "comparative_benchmark_reproduction_receipt.schema.json",
        base=COMPARATIVE_BENCHMARK_SCHEMA_BASE,
    )


# --- PUBLISHED_BYTES_RELOADABLE: id/fingerprint recomputation from the loaded body alone ------- #


def test_published_protocol_freeze_id_and_fingerprint_are_reloadable() -> None:
    protocol_freeze = _protocol_freeze()
    assert protocol_freeze["protocol_freeze_id"] == protocol_freeze_id(protocol_freeze)
    assert protocol_freeze[
        "protocol_freeze_semantic_fingerprint"
    ] == protocol_freeze_semantic_fingerprint(protocol_freeze)


def test_published_result_bundle_id_and_fingerprint_are_reloadable() -> None:
    result_bundle = _result_bundle()
    assert result_bundle["result_bundle_id"] == result_bundle_id(result_bundle)
    assert result_bundle[
        "result_bundle_semantic_fingerprint"
    ] == result_bundle_semantic_fingerprint(result_bundle)


def test_published_reproduction_receipt_id_and_fingerprint_are_reloadable() -> None:
    receipt = _reproduction_receipt()
    assert receipt["reproduction_receipt_id"] == reproduction_receipt_id(receipt)
    assert receipt[
        "reproduction_receipt_semantic_fingerprint"
    ] == reproduction_receipt_semantic_fingerprint(receipt)


def test_published_result_bundle_names_the_published_protocol_freeze() -> None:
    protocol_freeze = _protocol_freeze()
    result_bundle = _result_bundle()
    assert (
        result_bundle["protocol_freeze_ref"]["protocol_freeze_id"]
        == protocol_freeze["protocol_freeze_id"]
    )
    assert (
        result_bundle["protocol_freeze_ref"]["protocol_freeze_semantic_fingerprint"]
        == protocol_freeze["protocol_freeze_semantic_fingerprint"]
    )


def test_published_reproduction_receipt_names_the_published_protocol_freeze_and_result_bundle() -> (
    None
):
    protocol_freeze = _protocol_freeze()
    result_bundle = _result_bundle()
    receipt = _reproduction_receipt()
    assert (
        receipt["protocol_freeze_ref"]["protocol_freeze_id"]
        == protocol_freeze["protocol_freeze_id"]
    )
    assert (
        receipt["original_result_bundle_ref"]["result_bundle_id"]
        == result_bundle["result_bundle_id"]
    )
    assert (
        receipt["original_result_bundle_ref"]["result_bundle_semantic_fingerprint"]
        == result_bundle["result_bundle_semantic_fingerprint"]
    )


# --- REPRODUCED_RAW_EVENTS_DURABLY_REDERIVABLE: raw -> metric -> claim -> threshold rederivation #
#     from the published bytes alone, never from an ephemeral Store ---------------------------- #


def test_published_result_bundle_metrics_claims_and_thresholds_rederive_byte_for_byte() -> None:
    protocol_freeze = _protocol_freeze()
    result_bundle = _result_bundle()

    rederived_metrics = aggregate_metrics(result_bundle["raw_events"], protocol_freeze)
    assert rederived_metrics == result_bundle["metrics"]

    rederived_claims = derive_bounded_claims(rederived_metrics, protocol_freeze)
    assert rederived_claims == result_bundle["claims"]

    rederived_thresholds = evaluate_numeric_thresholds(rederived_metrics, protocol_freeze)
    assert rederived_thresholds == result_bundle["threshold_evaluations"]


# --- FAILURES_PRESENT_IN_PUBLISHED_RAW_DATA: real non-success outcomes survive into the -------- #
#     published bytes, never a success-only subset ---------------------------------------------- #


def test_published_raw_events_include_at_least_one_real_non_success_outcome() -> None:
    result_bundle = _result_bundle()
    outcomes = {event["outcome"] for event in result_bundle["raw_events"]}
    non_success = outcomes - {"COMPLETED_VERIFIED"}
    assert non_success, "expected at least one real non-COMPLETED_VERIFIED outcome published"


def test_published_raw_events_cover_every_declared_comparison_group_and_the_full_frozen_corpus() -> (
    None
):
    protocol_freeze = _protocol_freeze()
    result_bundle = _result_bundle()
    expected_task_ids = tuple(protocol_freeze["corpus_manifest"]["task_ids"])
    for group in protocol_freeze["comparison_groups"]:
        group_id = group["comparison_group_id"]
        actual_task_ids = tuple(
            event["task_id"]
            for event in result_bundle["raw_events"]
            if event["comparison_group_id"] == group_id
        )
        assert actual_task_ids == expected_task_ids


# --- PROVE_RELOAD_AND_REDERIVATION_FROM_THE_PUBLISHED_BYTES for the reproduction receipt ------- #


def test_published_reproduction_receipt_agreement_rederives_from_published_bytes() -> None:
    result_bundle = _result_bundle()
    receipt = _reproduction_receipt()

    reproduced_metrics = receipt["reproduced_metrics"]
    original_metrics = result_bundle["metrics"]
    if set(reproduced_metrics) != set(original_metrics):
        expected_agreement = "INCOMPARABLE"
    elif reproduced_metrics == original_metrics:
        expected_agreement = "MATCH"
    else:
        expected_agreement = "DIVERGENT"

    assert expected_agreement in REPRODUCTION_AGREEMENTS
    assert receipt["agreement"] == expected_agreement


def test_published_reproduction_receipt_metrics_rederive_from_published_reproduced_raw_events() -> (
    None
):
    """P90-R2-F3: `reproduced_raw_events` is itself part of the published bytes -- a third party
    can rederive `reproduced_metrics` from those raw bytes alone, never merely trust the stored
    aggregate on its own."""

    protocol_freeze = _protocol_freeze()
    receipt = _reproduction_receipt()
    rederived = aggregate_metrics(receipt["reproduced_raw_events"], protocol_freeze)
    assert rederived == receipt["reproduced_metrics"]


def test_published_reproduced_raw_events_cover_every_declared_group_and_the_full_frozen_corpus() -> (
    None
):
    protocol_freeze = _protocol_freeze()
    receipt = _reproduction_receipt()
    expected_task_ids = tuple(protocol_freeze["corpus_manifest"]["task_ids"])
    for group in protocol_freeze["comparison_groups"]:
        group_id = group["comparison_group_id"]
        actual_task_ids = tuple(
            event["task_id"]
            for event in receipt["reproduced_raw_events"]
            if event["comparison_group_id"] == group_id
        )
        assert actual_task_ids == expected_task_ids


def test_published_reproduction_receipt_is_a_genuinely_separate_process_reproduction() -> None:
    """P90-R1-F3: the published receipt's own reproducer identity records a real, separate
    reproduction process id -- distinct from the published result bundle's own
    ``generation_process_id`` -- and a real environment manifest, never a self-asserted
    ``is_original_author`` boolean standing in for genuine independence."""

    result_bundle = _result_bundle()
    receipt = _reproduction_receipt()
    identity = receipt["reproducer_identity"]

    assert identity["is_original_author"] is False
    assert isinstance(identity["reproduction_process_id"], int)
    assert identity["reproduction_process_id"] != result_bundle["generation_process_id"]
    assert set(identity["reproduction_environment_manifest"]) == {
        "python_implementation",
        "python_version",
        "platform",
    }
