"""Invalid comparison declarations cannot become favorable benchmark claims.

Pure controls only: no claim of a measured external model or third-party run.
"""

from copy import deepcopy

import pytest
from tests.fixtures.comparative_benchmark import PROJECT_ID, protocol_freeze_kwargs

from manosube_agent_civilization.comparative_benchmark import engine
from manosube_agent_civilization.comparative_benchmark.errors import (
    ProtocolFreezeValidationError,
    ResultBundleValidationError,
)


@pytest.fixture
def freeze():
    kwargs = protocol_freeze_kwargs(generated_at="2026-09-20T00:00:00Z")
    kwargs["project_id"] = PROJECT_ID
    assert engine.build_protocol_freeze(**kwargs)["protocol_freeze_id"]
    return kwargs


@pytest.mark.parametrize(
    "defect",
    [
        "role",
        "empty_id",
        "duplicate",
        "unknown_threshold_group",
        "unknown_operator",
        "unknown_claim_group",
        "all_present",
        "all_absent",
    ],
)
def test_invalid_pre_result_declaration_is_refused(freeze, defect):
    groups = freeze["comparison_groups"]
    if defect == "role":
        groups[0]["comparison_group_role"] = "FAVORABLE_BY_ASSERTION"
    elif defect == "empty_id":
        groups[0]["comparison_group_id"] = ""
    elif defect == "duplicate":
        groups[1]["comparison_group_id"] = groups[0]["comparison_group_id"]
    elif defect == "unknown_threshold_group":
        freeze["numeric_thresholds"][0]["comparison_group_id"] = "undeclared"
    elif defect == "unknown_operator":
        freeze["numeric_thresholds"][0]["operator"] = "trust-me"
    elif defect == "unknown_claim_group":
        freeze["claim_vocabulary"][0]["subject_group_ids"] = ["undeclared"]
    else:
        for group in groups:
            group["comparison_group_role"] = (
                "MANOSUBE_PRESENT" if defect == "all_present" else "MANOSUBE_ABSENT"
            )
    with pytest.raises(ProtocolFreezeValidationError):
        engine.build_protocol_freeze(**freeze)


@pytest.mark.parametrize(
    "defect",
    [
        "event_group",
        "outcome",
        "threshold_group",
        "threshold_operator",
        "claim_group",
        "claim_placeholder",
        "corpus_group",
    ],
)
def test_undeclared_metrics_and_claims_cannot_be_substituted_after_freeze(freeze, defect):
    protocol = engine.build_protocol_freeze(**freeze)
    group = protocol["comparison_groups"][0]["comparison_group_id"]
    metrics = engine.aggregate_metrics([], protocol)
    with pytest.raises(ResultBundleValidationError):
        if defect == "event_group":
            engine.aggregate_metrics(
                [{"comparison_group_id": "undeclared", "outcome": "CLOSED"}], protocol
            )
        elif defect == "outcome":
            engine.aggregate_metrics(
                [{"comparison_group_id": group, "outcome": "SELF_ACCEPTED"}], protocol
            )
        elif defect.startswith("threshold_"):
            threshold = protocol["numeric_thresholds"][0]
            threshold["comparison_group_id" if defect == "threshold_group" else "operator"] = (
                "undeclared"
            )
            engine.evaluate_numeric_thresholds(metrics, protocol)
        elif defect.startswith("claim_"):
            claim = protocol["claim_vocabulary"][0]
            if defect == "claim_group":
                claim["subject_group_ids"] = ["undeclared"]
            else:
                claim["claim_statement_template"] = "{not_a_declared_subject}"
            engine.derive_bounded_claims(metrics, protocol)
        else:
            engine.verify_exact_frozen_corpus(
                [{"comparison_group_id": "undeclared", "task_id": "unknown"}], protocol
            )


@pytest.mark.parametrize("key,signature", [("not-hex", "00"), ("00", "not-hex"), ("00", "00")])
def test_malformed_reproducer_key_or_signature_is_not_verified(key, signature):
    assert (
        engine.verify_ed25519_signature(
            public_key_hex=key, message=b"unit evidence", signature_hex=signature
        )
        is False
    )


def test_fractional_resource_budget_round_trips_without_changing_boolean_meaning():
    value = {"enabled": True, "seconds": 0.125, "nested": [False, 1.5, "unchanged"]}
    original = deepcopy(value)
    result = engine.stringify_floats(value)
    assert result == {"enabled": True, "seconds": "0.125", "nested": [False, "1.5", "unchanged"]}
    assert float(result["seconds"]) == value["seconds"]
    assert value == original
