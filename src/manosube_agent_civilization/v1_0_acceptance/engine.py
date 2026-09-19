"""v1.0 acceptance bundle assembly (Issue #92, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

`build_v1_0_acceptance_bundle` is the single point that combines Gate 22's mechanical
predicate rederivation (`gate22.py`), the v1.0-blocking Difference disposition
(`blocking_differences.py`) and the release identity surface (`release_identity.py`)
into one content-addressed record. It never itself decides Gate 22 PASS/FAIL/UNKNOWN
for a caller -- `gate_22_all_pass` is a plain, inspectable fold over the assembled
matrix, always re-derivable by a reader from the same `gate_22_predicate_matrix` field.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .blocking_differences import rederive_all_v1_0_blocking_differences_closed
from .gate22 import rederive_all_pytest_owned_predicates
from .identity import (
    compute_acceptance_bundle_id,
    compute_acceptance_bundle_semantic_fingerprint,
)
from .release_identity import compute_release_identity
from .types import GATE_22_PREDICATES

SCHEMA_VERSION = "0.1"


def build_v1_0_acceptance_bundle(
    repo_root: Path,
    authorized_base_main_sha: str,
    delivery_head: str,
    release_version_label: str,
    negative_control_results: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    pytest_owned = rederive_all_pytest_owned_predicates(repo_root)
    blocking_verdict, dispositions = rederive_all_v1_0_blocking_differences_closed(repo_root)
    release_identity = compute_release_identity(repo_root, delivery_head, release_version_label)

    gate_22_predicate_matrix: dict[str, dict[str, Any]] = {}
    for predicate in GATE_22_PREDICATES:
        if predicate == "ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED":
            gate_22_predicate_matrix[predicate] = {
                "owner_source": "deferred_differences_register",
                "evidence_identifier": "docs/project_sources/06_DEFERRED_DIFFERENCES.md",
                "verification_result": blocking_verdict,
                "disposition_count": len(dispositions),
            }
        else:
            rederivation = pytest_owned[predicate]
            gate_22_predicate_matrix[predicate] = {
                "owner_source": "test_module",
                "evidence_identifier": ",".join(rederivation.owner_test_paths),
                "verification_result": rederivation.verification_result,
                "exit_code": rederivation.exit_code,
            }

    gate_22_all_pass = all(
        row["verification_result"] == "PASS" for row in gate_22_predicate_matrix.values()
    )

    bundle: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "authorized_base_main_sha": authorized_base_main_sha,
        "delivery_head": delivery_head,
        "gate_22_predicate_matrix": gate_22_predicate_matrix,
        "gate_22_all_pass": gate_22_all_pass,
        "v1_0_blocking_difference_disposition": [
            {
                "record_id": d.record_id,
                "classification": d.classification,
                "current_status": d.current_status,
                "current_phase_blocking_effect": d.current_phase_blocking_effect,
                "disposition": d.disposition,
                "rationale": d.rationale,
            }
            for d in dispositions
        ],
        "negative_control_results": list(negative_control_results),
        "release_identity": {
            "commit_sha": release_identity.commit_sha,
            "tree_entry_count": release_identity.tree_entry_count,
            "blob_count": release_identity.blob_count,
            "directory_count": release_identity.directory_count,
            "version_label": release_identity.version_label,
            "tag_created": release_identity.tag_created,
            "release_published": release_identity.release_published,
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }
    bundle["acceptance_bundle_id"] = compute_acceptance_bundle_id(bundle)
    bundle["acceptance_bundle_semantic_fingerprint"] = (
        compute_acceptance_bundle_semantic_fingerprint(bundle)
    )
    return bundle


__all__ = ["SCHEMA_VERSION", "build_v1_0_acceptance_bundle"]
