"""The single canonical record-type table, and the gates that use it.

Every review round so far found the same shape of defect one layer further out: a record
reached the returned bundle without passing a validator, because the validator that would
have caught it covered a *different* route. ADR-0009 closed that for caller-supplied
predecessor context. The Objective revision escaped anyway, because it arrives on the
current-derivation route, which had no such gate.

This module states the record types once, and both gates read from that one table:

```text
RECORD_TYPES      one canonical schema, key and identity authority per logical type
CARRIED_SECTIONS  predecessor-context section  -> type    (the ADR-0009 boundary)
EMITTED_SECTIONS  returned-bundle section      -> type    (the output gate)
INPUT_KINDS       current-derivation input     -> type    (the input gate)
```

A section absent from the relevant map is rejected rather than silently trusted, and a
contract test compares the Engine's own emitted-section inventory against
``EMITTED_SECTIONS`` in both directions, so a newly emitted section cannot bypass the gate.

Where v0.1 defines no canonical schema for a type, that is recorded rather than papered
over: the type is carried under the identity and reference gates only, and
``ALL_OUTPUT_SCHEMA_VALID`` is qualified by ``UNSCHEMATIZED_SECTIONS``.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from manosube_agent_civilization.observation.identity import (
    binding_identity,
    deterministic_id,
    fact_evaluation_identity,
    fact_identity,
    observation_identity,
)

from .canonical import canonical_bytes, content_address
from .errors import DifferenceError, IdentityCollisionError
from .identity import (
    closure_policy_id,
    difference_id as derive_difference_id,
    lifecycle_event_id,
    policy_semantic_fingerprint,
    supersession_relation_id,
)
from .policy import closure_policy_semantic_errors
from .validation import SCHEMA_BASE, require_schema_version, validate_record

DIFFERENCE_BASE = SCHEMA_BASE + "difference/"
OBSERVATION_BASE = SCHEMA_BASE + "observation/"
OBJECTIVE_BASE = SCHEMA_BASE + "objective/"


def _negative_observation_identity(record: dict[str, Any]) -> str:
    return deterministic_id(
        "NEG",
        {
            "observation_id": record["observation_id"],
            "subject": record["subject"],
            "predicate": record["predicate"],
            "effective_boundary": record["effective_boundary"],
        },
    )


def _negative_evaluation_identity(record: dict[str, Any]) -> str:
    return deterministic_id(
        "NEG-EVAL",
        {
            "negative_observation_id": record["negative_observation_id"],
            "evaluation_revision": record["evaluation_revision"],
        },
    )


def _request_identity(record: dict[str, Any]) -> str:
    return content_address("OBS-REQ-", record, "observation_request_id")


def _method_identity(record: dict[str, Any]) -> str:
    return content_address("OBS-METHOD-", record, "observation_method_id")


def _policy_identity(record: dict[str, Any]) -> str:
    """Recompute the Closure Policy ID from the Policy's *content*, not its stored digest.

    Deriving the ID from ``policy_semantic_fingerprint`` as stored made the identity agree
    with itself and with nothing else: a caller could rewrite a required Claim, keep the
    stored digest, and keep the ID. The digest is recomputed here so an altered Policy
    changes its identity, which is what the identity gate is for.
    """

    subject = record["subject_difference_ref"]
    identity = subject.get("id") if isinstance(subject, dict) else None
    return closure_policy_id(policy_semantic_fingerprint(record), str(identity))


@dataclass(frozen=True)
class RecordType:
    """One canonical record type: its identity field, schema and identity authority."""

    key: str
    #: ``None`` when v0.1 defines no canonical schema for this type.
    schema: str | None
    base: str
    identity: Callable[[dict[str, Any]], str] | None = None
    #: Rules a record must satisfy from its own content, beyond schema and identity. Only
    #: a type that stores a digest of itself needs one; ``None`` states that this type
    #: carries no self-derived semantics to recompute.
    semantics: Callable[[dict[str, Any], str], list[str]] | None = None


#: One canonical schema, identity field and identity authority per logical record type.
RECORD_TYPES: dict[str, RecordType] = {
    "difference": RecordType(
        "difference_id", "difference.schema.json", DIFFERENCE_BASE, derive_difference_id
    ),
    "difference_lifecycle_event": RecordType(
        "difference_event_id", "difference_lifecycle_event.schema.json", DIFFERENCE_BASE,
        lifecycle_event_id,
    ),
    "difference_supersession_relation": RecordType(
        "supersession_relation_id", "difference_supersession_relation.schema.json",
        DIFFERENCE_BASE, supersession_relation_id,
    ),
    "closure_policy": RecordType(
        "closure_policy_id", "closure_policy.schema.json", DIFFERENCE_BASE, _policy_identity,
        closure_policy_semantic_errors,
    ),
    "next_observation_request": RecordType(
        "observation_request_id", "next_observation_request.schema.json", DIFFERENCE_BASE,
        _request_identity,
    ),
    "observation_method": RecordType(
        "observation_method_id", "observation_method.schema.json", DIFFERENCE_BASE,
        _method_identity,
    ),
    "objective_revision": RecordType(
        "objective_revision_id", "objective_revision.schema.json", OBJECTIVE_BASE
    ),
    "observation": RecordType(
        "observation_id", "observation.schema.json", OBSERVATION_BASE, observation_identity
    ),
    "observation_scope": RecordType(
        "scope_id", "observation_scope.schema.json", OBSERVATION_BASE
    ),
    "normalized_fact": RecordType(
        "fact_id", "normalized_fact.schema.json", OBSERVATION_BASE, fact_identity
    ),
    "fact_observation_binding": RecordType(
        "binding_id", "fact_observation_binding.schema.json", OBSERVATION_BASE, binding_identity
    ),
    "fact_evaluation": RecordType(
        "evaluation_id", "fact_evaluation.schema.json", OBSERVATION_BASE, fact_evaluation_identity
    ),
    "negative_observation": RecordType(
        "negative_observation_id", "negative_observation.schema.json", OBSERVATION_BASE,
        _negative_observation_identity,
    ),
    "negative_observation_evaluation": RecordType(
        "evaluation_id", "negative_observation_evaluation.schema.json", OBSERVATION_BASE,
        _negative_evaluation_identity,
    ),
    "closure_evaluation": RecordType(
        "closure_evaluation_id", "closure_evaluation.schema.json", DIFFERENCE_BASE
    ),
    "reopen_condition_evaluation": RecordType(
        "evaluation_id", "reopen_condition_evaluation.schema.json", DIFFERENCE_BASE
    ),
    "candidate_completion_record": RecordType(
        "completion_id", "candidate_completion_record.schema.json", DIFFERENCE_BASE
    ),
    "candidate_claim_evaluation_event": RecordType(
        "event_id", "candidate_claim_evaluation_event.schema.json", DIFFERENCE_BASE
    ),
    "invariant_evaluation": RecordType(
        "evaluation_id", "invariant_evaluation.schema.json", DIFFERENCE_BASE
    ),
    "evidence_sufficiency_result": RecordType(
        "evidence_sufficiency_id", "evidence_sufficiency_result.schema.json", DIFFERENCE_BASE
    ),
    # 01_SCHEMA/change/ and 01_SCHEMA/reflow/ are empty in v0.1: no canonical schema exists
    # for these two, so nothing can validate them. The non-claim is explicit.
    "change": RecordType("change_id", None, ""),
    "reflow_transaction": RecordType("transaction_id", None, ""),
}

#: Predecessor-context section -> canonical record type (the ADR-0009 boundary).
CARRIED_SECTIONS: dict[str, str] = {
    "observations": "observation",
    "normalized_facts": "normalized_fact",
    "fact_observation_bindings": "fact_observation_binding",
    "fact_evaluations": "fact_evaluation",
    "negative_observations": "negative_observation",
    "negative_observation_evaluations": "negative_observation_evaluation",
    "observation_scopes": "observation_scope",
    "objective_revisions": "objective_revision",
    "policies": "closure_policy",
    "next_observation_requests": "next_observation_request",
    "observation_methods": "observation_method",
    "evaluations": "closure_evaluation",
    "reopen_condition_evaluations": "reopen_condition_evaluation",
    "candidate_completion_records": "candidate_completion_record",
    "candidate_claim_evaluation_events": "candidate_claim_evaluation_event",
    "invariant_evaluations": "invariant_evaluation",
    "evidence_sufficiency_results": "evidence_sufficiency_result",
    "changes": "change",
    "reflow_transitions": "reflow_transaction",
}

#: Returned-bundle section -> canonical record type (the output gate).
EMITTED_SECTIONS: dict[str, str] = {
    **CARRIED_SECTIONS,
    "differences": "difference",
    "events": "difference_lifecycle_event",
    "supersession_relations": "difference_supersession_relation",
}

#: Returned-bundle keys that are the bundle's own envelope, not record collections.
ENVELOPE_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "identity_profile",
        "comparison_profile",
        "normalization_profile",
        "current_state_ref",
        "materialized_status",
        "satisfied_target_predicates",
    }
)

#: Current-derivation inputs that arrive as complete canonical records, and the type each
#: is validated as. The Observation Method projection and the Closure Policy requirements
#: arrive as *fragments* the Engine completes, so their conformance is decided on the
#: records it derives from them, which are validated as outputs; the Target Predicate is
#: validated transitively as part of the Objective revision; the Observation bundle is
#: validated by the Observation element's own shared verifier.
INPUT_KINDS: dict[str, str] = {
    "objective_revision": "objective_revision",
    "observation_scope": "observation_scope",
}

#: The canonical fingerprint schema every State fingerprint input must satisfy.
STATE_FINGERPRINT_SCHEMA = "fingerprint.schema.json"
STATE_FINGERPRINT_BASE = SCHEMA_BASE + "common/"

#: Sections v0.1 defines no canonical schema for. ``ALL_OUTPUT_SCHEMA_VALID`` is qualified
#: by this set: those records are gated on identity collision and reference resolution
#: only, and no schema or semantic conformance is claimed for them.
UNSCHEMATIZED_SECTIONS: frozenset[str] = frozenset(
    section
    for section, type_name in EMITTED_SECTIONS.items()
    if RECORD_TYPES[type_name].schema is None
)


def merge_records(
    target: dict[str, dict[str, Any]], records: Any, key: str
) -> None:
    """Merge records into *target* under *key*, failing closed on a contradicted identity.

    This is the one union used by every canonical section, on every route: the current
    derivation, the Observation context closure, predecessor context and final bundle
    assembly. A new identity is inserted, an identical duplicate is idempotent, and a
    same-identity/different-payload pair is rejected *before* the target is mutated -- so
    no plain ``target[identity] = record`` can overwrite a record that is already held.
    Inputs are never mutated: what is stored is a deep copy.
    """

    if not isinstance(records, list):
        raise DifferenceError(f"canonical section is not a list of records: {key}")
    for record in records:
        if not isinstance(record, dict):
            raise DifferenceError(f"canonical record is not an object: {key}")
        identity = record.get(key)
        if not isinstance(identity, str) or not identity:
            raise DifferenceError(f"canonical record has no identity: {key}")
        existing = target.get(identity)
        if existing is not None and canonical_bytes(existing) != canonical_bytes(record):
            raise IdentityCollisionError(f"same-ID different-payload conflict: {identity}")
        target[identity] = deepcopy(record)


def validate_typed_record(record: dict[str, Any], type_name: str, context: str) -> None:
    """Schema-validate one record and recompute its identity, where an authority exists."""

    canonical = RECORD_TYPES[type_name]
    if not isinstance(record, dict):
        raise DifferenceError(f"{context} is not a canonical record object")
    if canonical.schema is not None:
        validate_record(record, canonical.schema, base=canonical.base)
        require_schema_version(record, context)
    identity = record.get(canonical.key)
    if not isinstance(identity, str) or not identity:
        raise DifferenceError(f"{context} has no canonical identity: {canonical.key}")
    # Semantics before identity: where a type stores a digest of itself, the identity is
    # derived from that digest, so "does not recompute" would report the consequence and
    # hide the cause.
    if canonical.semantics is not None:
        errors = canonical.semantics(record, context)
        if errors:
            raise DifferenceError(sorted(errors)[0])
    if canonical.identity is not None and identity != canonical.identity(record):
        raise IdentityCollisionError(f"{context} identity does not recompute: {identity}")


def validate_typed_section(section: str, records: Any, type_name: str) -> None:
    """Validate one section: every record typed, and no same-id/different-payload pair."""

    if not isinstance(records, list):
        raise DifferenceError(f"section is not a list of records: {section}")
    canonical = RECORD_TYPES[type_name]
    seen: dict[str, bytes] = {}
    for record in records:
        validate_typed_record(record, type_name, f"{section}[{record.get(canonical.key)}]"
                              if isinstance(record, dict) else section)
        identity = record[canonical.key]
        payload = canonical_bytes(record)
        existing = seen.get(identity)
        if existing is not None and existing != payload:
            raise IdentityCollisionError(
                f"same-ID different-payload conflict in {section}: {identity}"
            )
        if existing is not None:
            raise IdentityCollisionError(f"duplicate canonical record in {section}: {identity}")
        seen[identity] = payload


def validate_derivation_input(record: Any, input_name: str) -> None:
    """Validate one current-derivation input before any semantic field is read.

    The requested Objective revision, Observation Scope, Observation Method projection and
    Closure Policy arrive on the current-derivation route, which the predecessor boundary
    does not cover. They are validated here against the same canonical schema registry,
    before identity-bearing or semantic fields are consumed.
    """

    validate_typed_record(record, INPUT_KINDS[input_name], f"requested {input_name}")


def validate_state_fingerprint(fingerprint: Any, context: str) -> None:
    """Validate a State fingerprint input against the canonical common schema."""

    if not isinstance(fingerprint, dict):
        raise DifferenceError(f"{context} is not a canonical fingerprint object")
    validate_record(fingerprint, STATE_FINGERPRINT_SCHEMA, base=STATE_FINGERPRINT_BASE)


def validate_emitted_bundle(bundle: dict[str, Any]) -> None:
    """The final output conformance gate: nothing is returned unless the whole bundle passes.

    Every emitted record collection is enumerated, unknown sections are rejected, every
    record is validated against its canonical schema where one exists, every
    content-addressed identity is recomputed, and duplicate or contradicting identities
    fail closed. Cross-record conformance is proven separately by the independent
    validator, which the conformance tests run over these same bundles; this gate is the
    Engine's own guarantee that it never *emits* a record its canonical schema rejects.
    """

    unknown = set(bundle) - set(EMITTED_SECTIONS) - ENVELOPE_KEYS
    if unknown:
        raise DifferenceError(f"returned bundle carries unknown sections: {sorted(unknown)}")
    for section, type_name in EMITTED_SECTIONS.items():
        if section not in bundle:
            continue
        validate_typed_section(section, bundle[section], type_name)
