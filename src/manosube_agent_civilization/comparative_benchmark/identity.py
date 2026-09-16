"""Deterministic identity and content-addressing for the Comparative Benchmark package
(Issue #89, `ADOPT_PHASE_21_COMPARATIVE_BENCHMARK`).

Follows the identical narrow-id/broad-fingerprint split every other package's own
`identity.py` in this repository already establishes (see
`long_running_proof_artifact/identity.py`'s own module docstring): the *id* is a pure
function of *which record this is* -- deliberately excluding `generated_at` and every other
genuinely nondeterministic field -- so a same-body re-commit collides at the identical Store
slot (idempotent replay), while the *semantic fingerprint* is a full content address over
every field, the record's own tamper-detection value.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

#: A protocol freeze's own identity: the complete pre-result protocol content -- every
#: predeclared field except `schema_version` and `generated_at` -- so a change to *any*
#: policy content (metrics, thresholds, exclusion policy, claim vocabulary, resource/
#: authority manifests, reproduction procedure) mints a genuinely new protocol identity,
#: never a same-id collision (P90-R1-F4: "subsequent protocol change creates a new protocol
#: identity ... never retroactively applied to prior results"). Only `generated_at` is
#: excluded, since it is the one genuinely nondeterministic field a byte-identical re-freeze
#: of the identical policy should still collide on (idempotent replay).
PROTOCOL_FREEZE_ID_FIELDS: tuple[str, ...] = (
    "project_id",
    "project_binding_ref",
    "corpus_manifest",
    "comparison_groups",
    "authority_boundary_equivalence_manifest",
    "resource_budget_manifest",
    "metric_definitions",
    "numeric_thresholds",
    "unknown_missing_handling",
    "exclusion_policy",
    "claim_vocabulary",
    "reproduction_procedure",
    "comparability_loss_receipts",
)

PROTOCOL_FREEZE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_ref",
    "corpus_manifest",
    "comparison_groups",
    "authority_boundary_equivalence_manifest",
    "resource_budget_manifest",
    "metric_definitions",
    "numeric_thresholds",
    "unknown_missing_handling",
    "exclusion_policy",
    "claim_vocabulary",
    "reproduction_procedure",
    "comparability_loss_receipts",
    "generated_at",
)

#: A result bundle's own identity: which protocol freeze it ran, and its own raw events --
#: two runs of the identical protocol against the identical raw events collide at the
#: identical slot (idempotent replay); two runs with genuinely different raw events (a real
#: divergent trial) never collide.
RESULT_BUNDLE_ID_FIELDS: tuple[str, ...] = ("project_id", "protocol_freeze_ref", "raw_events")

#: P90-R2-F5: every field the result bundle schema itself requires (except the id/fingerprint
#: fields the record carries its own identity in) must be covered by this projection -- a
#: `threshold_evaluations` or `generation_process_id` tamper must change the semantic
#: fingerprint exactly like a `metrics`/`claims` tamper already does. This tuple is asserted,
#: by a dedicated static test, to equal the schema's own `required` field set minus
#: `result_bundle_id`/`result_bundle_semantic_fingerprint`.
RESULT_BUNDLE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_ref",
    "protocol_freeze_ref",
    "raw_events",
    "metrics",
    "claims",
    "threshold_evaluations",
    "environment_manifest",
    "generation_process_id",
    "generated_at",
)

#: A reproduction receipt's own identity: which original result bundle, by which declared
#: reproducer -- excludes the reproducer's own recomputed metrics/agreement outcome, so a
#: caller can resolve "did this reproducer already attempt this bundle" before knowing what
#: they found.
REPRODUCTION_RECEIPT_ID_FIELDS: tuple[str, ...] = (
    "project_id",
    "original_result_bundle_ref",
    "reproducer_identity",
)

#: P90-R2-F3: `reproduced_raw_events` -- the reproducer's own raw per-task outcomes, not just
#: their aggregated `reproduced_metrics` -- is now part of this record's own required schema
#: shape and must therefore be part of its semantic fingerprint too, for the identical
#: tamper-detection reason `RESULT_BUNDLE_SEMANTIC_FIELDS` above states.
REPRODUCTION_RECEIPT_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_ref",
    "protocol_freeze_ref",
    "original_result_bundle_ref",
    "reproducer_identity",
    "reproduced_raw_events",
    "reproduced_metrics",
    "agreement",
    "generated_at",
)


#: P90-R3-F2: an independent reproduction submission's own identity: which original result
#: bundle, by which declared reproducer actor/authority -- the identical narrow-id shape
#: `REPRODUCTION_RECEIPT_ID_FIELDS` already establishes for "did this reproducer already
#: submit against this bundle."
INDEPENDENT_REPRODUCTION_SUBMISSION_ID_FIELDS: tuple[str, ...] = (
    "project_id",
    "original_result_bundle_ref",
    "reproducer_actor_or_authority_id",
)

#: Every other field this record's own schema requires except its own id/semantic-fingerprint/
#: signature -- literally everything a genuine reproducer actor/authority must have committed
#: to before submitting, so this projection doubles as the exact bytes
#: :func:`independent_reproduction_submission_signing_payload` signs: the content address and
#: the signed message are never allowed to drift apart (the identical discipline
#: `binding.identity.human_grant_declaration_signing_payload` already establishes).
INDEPENDENT_REPRODUCTION_SUBMISSION_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_ref",
    "reproducer_actor_or_authority_id",
    "provenance_mechanism",
    "original_result_bundle_ref",
    "protocol_freeze_ref",
    "reproduced_raw_events",
    "reproduced_raw_events_content_address",
    "agent_runtime_model_configuration_identity",
    "execution_environment_manifest",
    "reproduced_metrics",
    "agreement",
    "submission_time",
)


def _projection(record: Mapping[str, Any], fields: tuple[str, ...], *, kind: str) -> dict[str, Any]:
    missing = [field for field in fields if field not in record]
    if missing:
        raise KeyError(
            f"{kind} carries no readable {', '.join(missing)} -- its own identity cannot be recomputed"
        )
    return {field: record[field] for field in fields}


def protocol_freeze_id(record: Mapping[str, Any]) -> str:
    payload = _projection(
        record, PROTOCOL_FREEZE_ID_FIELDS, kind="comparative_benchmark_protocol_freeze"
    )
    return "CBPF-" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def protocol_freeze_semantic_fingerprint(record: Mapping[str, Any]) -> str:
    projection = _projection(
        record, PROTOCOL_FREEZE_SEMANTIC_FIELDS, kind="comparative_benchmark_protocol_freeze"
    )
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def result_bundle_id(record: Mapping[str, Any]) -> str:
    payload = _projection(
        record, RESULT_BUNDLE_ID_FIELDS, kind="comparative_benchmark_result_bundle"
    )
    return "CBRB-" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def result_bundle_semantic_fingerprint(record: Mapping[str, Any]) -> str:
    projection = _projection(
        record, RESULT_BUNDLE_SEMANTIC_FIELDS, kind="comparative_benchmark_result_bundle"
    )
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def reproduction_receipt_id(record: Mapping[str, Any]) -> str:
    payload = _projection(
        record, REPRODUCTION_RECEIPT_ID_FIELDS, kind="comparative_benchmark_reproduction_receipt"
    )
    return "CBRR-" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def reproduction_receipt_semantic_fingerprint(record: Mapping[str, Any]) -> str:
    projection = _projection(
        record,
        REPRODUCTION_RECEIPT_SEMANTIC_FIELDS,
        kind="comparative_benchmark_reproduction_receipt",
    )
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def independent_reproduction_submission_signing_payload(record: Mapping[str, Any]) -> bytes:
    """Return the exact canonical bytes a genuine reproducer signature over *record* must
    cover -- :data:`INDEPENDENT_REPRODUCTION_SUBMISSION_SEMANTIC_FIELDS`'s own projection.
    Excludes `independent_reproduction_submission_id`/`..._semantic_fingerprint` (an identity
    cannot be computed over itself) and `signature` (a signature cannot cover its own value)."""

    projection = _projection(
        record,
        INDEPENDENT_REPRODUCTION_SUBMISSION_SEMANTIC_FIELDS,
        kind="comparative_benchmark_independent_reproduction_submission",
    )
    return canonical_json_bytes(projection)


def independent_reproduction_submission_id(record: Mapping[str, Any]) -> str:
    payload = _projection(
        record,
        INDEPENDENT_REPRODUCTION_SUBMISSION_ID_FIELDS,
        kind="comparative_benchmark_independent_reproduction_submission",
    )
    return "CBIRS-" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def independent_reproduction_submission_semantic_fingerprint(record: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(independent_reproduction_submission_signing_payload(record)).hexdigest()
    return "sha256:" + digest


__all__ = [
    "INDEPENDENT_REPRODUCTION_SUBMISSION_ID_FIELDS",
    "INDEPENDENT_REPRODUCTION_SUBMISSION_SEMANTIC_FIELDS",
    "PROTOCOL_FREEZE_ID_FIELDS",
    "PROTOCOL_FREEZE_SEMANTIC_FIELDS",
    "REPRODUCTION_RECEIPT_ID_FIELDS",
    "REPRODUCTION_RECEIPT_SEMANTIC_FIELDS",
    "RESULT_BUNDLE_ID_FIELDS",
    "RESULT_BUNDLE_SEMANTIC_FIELDS",
    "independent_reproduction_submission_id",
    "independent_reproduction_submission_semantic_fingerprint",
    "independent_reproduction_submission_signing_payload",
    "protocol_freeze_id",
    "protocol_freeze_semantic_fingerprint",
    "reproduction_receipt_id",
    "reproduction_receipt_semantic_fingerprint",
    "result_bundle_id",
    "result_bundle_semantic_fingerprint",
]
