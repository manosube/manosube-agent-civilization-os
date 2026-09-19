"""V1: identity/semantic-fingerprint determinism for the v1.0 acceptance bundle
(Issue #92, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`)."""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.v1_0_acceptance.identity import (
    compute_acceptance_bundle_id,
    compute_acceptance_bundle_semantic_fingerprint,
)

_BASE_BUNDLE: dict[str, Any] = {
    "authorized_base_main_sha": "b2a5d287113d3a98e77a2212f8b89359d8e09c5d",
    "delivery_head": "abc123",
    "gate_22_predicate_matrix": {"OBJECTIVE_CONTINUITY_PROVEN": {"verification_result": "PASS"}},
    "v1_0_blocking_difference_disposition": [
        {"record_id": "DD-0001", "disposition": "NON_BLOCKING"}
    ],
    "negative_control_results": [],
    "release_identity": {"commit_sha": "abc123", "tree_entry_count": 10},
}


def test_id_excludes_generated_at_same_body_collides() -> None:
    first = {**_BASE_BUNDLE, "schema_version": "0.1", "generated_at": "2026-01-01T00:00:00Z"}
    second = {**_BASE_BUNDLE, "schema_version": "0.1", "generated_at": "2026-06-01T00:00:00Z"}
    assert compute_acceptance_bundle_id(first) == compute_acceptance_bundle_id(second)


def test_semantic_fingerprint_includes_generated_at_diverges() -> None:
    first = {**_BASE_BUNDLE, "schema_version": "0.1", "generated_at": "2026-01-01T00:00:00Z"}
    second = {**_BASE_BUNDLE, "schema_version": "0.1", "generated_at": "2026-06-01T00:00:00Z"}
    assert compute_acceptance_bundle_semantic_fingerprint(
        first
    ) != compute_acceptance_bundle_semantic_fingerprint(second)


def test_id_changes_when_gate_22_matrix_changes() -> None:
    base = {**_BASE_BUNDLE, "schema_version": "0.1", "generated_at": "2026-01-01T00:00:00Z"}
    mutated = {
        **base,
        "gate_22_predicate_matrix": {
            "OBJECTIVE_CONTINUITY_PROVEN": {"verification_result": "FAIL"}
        },
    }
    assert compute_acceptance_bundle_id(base) != compute_acceptance_bundle_id(mutated)


def test_id_is_deterministic_hex_sha256() -> None:
    bundle = {**_BASE_BUNDLE, "schema_version": "0.1", "generated_at": "2026-01-01T00:00:00Z"}
    value = compute_acceptance_bundle_id(bundle)
    assert len(value) == 64
    int(value, 16)  # raises if not valid hex
