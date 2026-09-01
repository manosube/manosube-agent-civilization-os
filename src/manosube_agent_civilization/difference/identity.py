"""Deterministic identity and semantic fingerprint authority for Difference records.

Every digest in this module is defined by ``00_KERNEL/04_DIFFERENCE/DIFFERENCE_IDENTITY.md``
and computed over the canonical serializer owned by
:mod:`manosube_agent_civilization.state.canonicalize`.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .canonical import canonical_bytes, canonical_semantic

IDENTITY_PROFILE = "MANOSUBE-DIFFERENCE-SHA256-0.1"
COMPARISON_PROFILE = "MANOSUBE-DIFFERENCE-COMPARISON-0.1"
NORMALIZATION_PROFILE = "MANOSUBE-DIFFERENCE-NORMALIZATION-0.1"
#: ``CLOSURE_POLICY.md`` fixes this profile for the digest a reopen condition declares.
TARGET_PREDICATE_PROFILE = "MANOSUBE-TARGET-PREDICATE-SHA256-0.1"

_SCOPE_DOMAIN = b"MANOSUBE:RESOLVED_OBSERVATION_SCOPE_RECORD:0.1:"
_CLAIM_DOMAIN = b"MANOSUBE:COMPLETION_CLAIM_IDENTITY:0.1:"

#: ``INCLUDED_FIELDS`` of ``MANOSUBE-TARGET-PREDICATE-SHA256-0.1``. ``predicate_id`` and
#: every provenance field are excluded, so the digest states the predicate's *semantics*
#: and a ``PREDICATE_MODIFY`` is what changes it.
_TARGET_PREDICATE_SEMANTIC_FIELDS = (
    "subject",
    "operator",
    "expected_value",
    "observation_scope",
    "evidence_requirement",
    "unknown_policy",
    "criticality",
)

_OBJECTIVE_SEMANTIC_FIELDS = (
    "objective_id",
    "project_id",
    "statement",
    "owner_authority_ref",
    "target_predicates",
    "completion_policy",
    "boundary_ref",
    "constitutional_constraints",
    "status",
)
#: ``UNORDERED_SETS`` of ``MANOSUBE-CLOSURE-POLICY-SHA256-0.1``. The profile also fixes
#: ``DUPLICATE_SET_MEMBER=REJECT``, and a contract test holds this tuple to the profile
#: block in ``CLOSURE_POLICY.md`` in both directions.
POLICY_UNORDERED_SET_FIELDS = (
    "required_claims",
    "required_invariants",
    "allowed_terminal_states",
    "reopen_conditions",
)

_POLICY_SEMANTIC_FIELDS = (
    "target_predicate_ref",
    "required_observation_scope",
    "minimum_evidence_level",
    "required_claims",
    "required_invariants",
    "allowed_terminal_states",
    "independent_verification_required",
    "maximum_evidence_age",
    "contradiction_policy",
    "reopen_conditions",
)


def _sha256_fingerprint(payload: Any, domain: bytes = b"") -> str:
    return "sha256:" + hashlib.sha256(domain + canonical_bytes(payload)).hexdigest()


def objective_semantic_fingerprint(revision: dict[str, Any]) -> str:
    """Return the semantic fingerprint of an Objective revision.

    Editorial revision metadata is excluded, so an ``EDITORIAL`` revision keeps the
    fingerprint and therefore keeps every derived Difference identity.
    """

    return _sha256_fingerprint({key: revision[key] for key in _OBJECTIVE_SEMANTIC_FIELDS})


def resolved_scope_fingerprint(scope: dict[str, Any]) -> str:
    """Return the resolved Observation Scope record digest used by every scope binding."""

    projection = deepcopy(scope)
    for key in ("included_subjects", "excluded_subjects", "source_snapshot_refs", "blind_spots"):
        projection[key] = {
            "collection_kind": "UNORDERED_SET",
            "members": sorted(
                (canonical_semantic(item) for item in projection[key]),
                key=canonical_json_bytes,
            ),
        }
    projection["attempt_policy"]["retry_on"] = {
        "collection_kind": "UNORDERED_SET",
        "members": sorted(projection["attempt_policy"]["retry_on"], key=canonical_json_bytes),
    }
    for item in projection["blind_spots"]["members"]:
        item["affected_subjects"] = {
            "collection_kind": "UNORDERED_SET",
            "members": sorted(item["affected_subjects"], key=canonical_json_bytes),
        }
    return _sha256_fingerprint(projection, _SCOPE_DOMAIN)


def target_predicate_fingerprint(predicate: dict[str, Any]) -> str:
    """Return the semantic fingerprint of one Objective Target Predicate.

    ``CLOSURE_POLICY.md`` fixes this digest and requires a Closure Policy reopen condition
    to resolve exactly against it: the condition's predicate ID, Objective revision and
    fingerprint must all name a predicate that really carries those semantics.
    """

    return _sha256_fingerprint(
        {key: predicate[key] for key in _TARGET_PREDICATE_SEMANTIC_FIELDS}
    )


def completion_claim_fingerprint(descriptor: dict[str, Any]) -> str:
    """Return the semantic fingerprint of a required completion Claim descriptor."""

    return _sha256_fingerprint(
        {key: descriptor[key] for key in ("subject_type", "subject_ref", "claim", "target_state_ref")}
    )


def completion_claim_id(descriptor: dict[str, Any]) -> str:
    """Return the canonical identity of a required completion Claim descriptor."""

    projection = {
        "subject_type": descriptor["subject_type"],
        "subject_ref": descriptor["subject_ref"],
        "claim_semantic_fingerprint": completion_claim_fingerprint(descriptor),
    }
    digest = hashlib.sha256(_CLAIM_DOMAIN + canonical_bytes(projection)).hexdigest()
    return "CLAIM-" + digest.upper()


def policy_semantic_projection(policy: dict[str, Any]) -> dict[str, Any]:
    """Return the exact payload the Closure Policy digest is computed over.

    Extracted from :func:`policy_semantic_fingerprint` so the duplicate-set rule can read
    the *same* projection the digest reads. ``MANOSUBE-CLOSURE-POLICY-SHA256-0.1`` declares
    four unordered sets and ``DUPLICATE_SET_MEMBER=REJECT``, and a duplicate is only
    visible after projection: two ``required_invariants`` differing solely in an excluded
    ``commit_sha``, or two reopen conditions differing solely in an excluded
    ``objective_revision_ref``, are distinct whole objects and identical members. Deriving
    the check from a second, hand-copied projection is how the two would drift.
    """

    projection: dict[str, Any] = {key: policy[key] for key in _POLICY_SEMANTIC_FIELDS}
    projection["required_claims"] = sorted(
        (canonical_semantic(item) for item in projection["required_claims"]),
        key=canonical_json_bytes,
    )
    projection["allowed_terminal_states"] = sorted(
        projection["allowed_terminal_states"], key=canonical_json_bytes
    )
    projection["reopen_conditions"] = sorted(
        (
            {key: item[key] for key in ("kind", "id", "predicate_semantic_fingerprint")}
            for item in projection["reopen_conditions"]
        ),
        key=canonical_json_bytes,
    )
    projection["required_invariants"] = sorted(
        (
            {
                "kind": item["kind"],
                "id": item["id"],
                "contract_source_blob": {
                    "kind": item["contract_source_ref"]["kind"],
                    "repository": item["contract_source_ref"]["repository"],
                    "path": item["contract_source_ref"]["path"],
                    "invariant_definition_sha256": item["contract_source_ref"][
                        "invariant_definition_sha256"
                    ],
                },
            }
            for item in projection["required_invariants"]
        ),
        key=canonical_json_bytes,
    )
    return projection


def policy_semantic_fingerprint(policy: dict[str, Any]) -> str:
    """Return the Closure Policy requirement digest bound into Difference identity.

    ``subject_difference_ref``, ``closure_policy_id`` and ``policy_version`` are excluded,
    so no circular dependency with ``difference_id`` exists and a version-only Policy
    update keeps the Difference identity.
    """

    return _sha256_fingerprint(policy_semantic_projection(policy))


def difference_identity_input(difference: dict[str, Any]) -> dict[str, Any]:
    """Return the closed semantic identity tuple of a materialized Difference record."""

    return {
        "project_id": difference["project_id"],
        "objective_semantic_fingerprint": difference["objective_semantic_fingerprint"],
        "target_predicate_ref": difference["target_predicate_ref"],
        "subject": difference["subject"],
        "observation_scope": difference["observation_scope"],
        "effective_boundary": difference["effective_boundary"],
        "normalized_target_state": difference["normalized_target_state"],
        "normalized_structural_difference": difference["structural_difference"],
        "closure_policy_semantic_fingerprint": difference["closure_policy"]["semantic_fingerprint"],
        "identity_profile": IDENTITY_PROFILE,
    }


def difference_id(difference: dict[str, Any]) -> str:
    """Return the stable ``D-`` identity of a materialized Difference record."""

    digest = hashlib.sha256(canonical_bytes(difference_identity_input(difference))).hexdigest()
    return "D-" + digest.upper()


def closure_policy_id(policy_fingerprint: str, subject_difference_id: str) -> str:
    """Return the deterministic identity of the Difference-bound Closure Policy record."""

    projection = {
        "policy_semantic_fingerprint": policy_fingerprint,
        "subject_difference_id": subject_difference_id,
    }
    return "CP-" + hashlib.sha256(canonical_bytes(projection)).hexdigest().upper()


SUPERSESSION_COMPARISONS: dict[str, tuple[str, ...]] = {
    "PROJECT_CHANGED": ("project_id",),
    "OBJECTIVE_SEMANTICS_CHANGED": ("objective_semantic_fingerprint",),
    "TARGET_PREDICATE_CHANGED": ("target_predicate_ref",),
    "SUBJECT_OR_PREDICATE_CHANGED": ("subject",),
    "BOUNDARY_CHANGED": ("observation_scope", "effective_boundary"),
    "TARGET_STATE_SEMANTICS_CHANGED": ("normalized_target_state",),
    "MISMATCH_SEMANTICS_CHANGED": ("structural_difference",),
}


def supersession_reason_codes(old: dict[str, Any], new: dict[str, Any]) -> set[str]:
    """Return every reason code whose identity input materially changed."""

    codes = {
        code
        for code, fields in SUPERSESSION_COMPARISONS.items()
        if any(canonical_bytes(old[field]) != canonical_bytes(new[field]) for field in fields)
    }
    if old["closure_policy"]["semantic_fingerprint"] != new["closure_policy"]["semantic_fingerprint"]:
        codes.add("CLOSURE_POLICY_SEMANTICS_CHANGED")
    return codes


_EVENT_IDENTITY_FIELDS = (
    "difference_id",
    "event_kind",
    "event_revision",
    "previous_event_id",
    "from_status",
    "to_status",
    "state_revision_evaluated",
    "state_fingerprint_evaluated",
    "reason_code",
    "observation_refs",
    "evidence_refs",
)


def lifecycle_event_id(event: dict[str, Any]) -> str:
    """Return the deterministic identity of a Difference Lifecycle Event.

    The identity input is the event's lineage position and transition semantics. The
    forward-looking ``next_observation_ref`` is excluded because the Next Observation
    Request is derived *from* this event and references it back; including it would make
    both identities circular.
    """

    projection = {key: event[key] for key in _EVENT_IDENTITY_FIELDS}
    return "D-EVT-" + hashlib.sha256(canonical_bytes(projection)).hexdigest().upper()


def supersession_relation_id(relation: dict[str, Any]) -> str:
    """Return the content address of an append-only Supersession Relation."""

    payload = {key: value for key, value in relation.items() if key != "supersession_relation_id"}
    return "D-SUP-" + hashlib.sha256(canonical_bytes(payload)).hexdigest().upper()
