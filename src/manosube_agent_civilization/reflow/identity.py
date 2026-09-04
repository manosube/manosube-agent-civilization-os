"""Deterministic Reflow identities.

Canonical serialization has one owner in this repository -- ``state.canonicalize`` -- and
the repo-wide content-address convention has one owner, ``difference.canonical.content_address``.
This module reads both rather than restating them, exactly as ``change/identity.py`` and
``evidence/identity.py`` do. What is defined here is only *which payload* each Reflow-minted
identity is computed over.

Two exceptions use their own scheme rather than the repo convention, because
``CLOSURE_POLICY.md`` §3 gives one explicitly, with its own domain separator and canonical
projection, and a second scheme invented here would disagree with the one an independent
validator is entitled to assume.
"""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.difference.canonical import canonical_bytes, content_address
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

#: ``CLOSURE_POLICY.md`` §3's exact after-state-candidate identity profile.
_CANDIDATE_DOMAIN_SEPARATOR = b"MANOSUBE:AFTER_STATE_CANDIDATE:0.1:"

#: The closed payload fields the candidate identity profile names, in the order the
#: contract lists them. ``kind``, ``candidate_id`` and the profile name are excluded.
_CANDIDATE_PAYLOAD_FIELDS: tuple[str, ...] = (
    "base_state_ref",
    "kernel_source_ref",
    "producing_change_refs",
    "semantic_fingerprint",
    "semantic_state",
    "source_snapshot_refs",
)


def after_state_candidate_id(candidate: dict[str, Any]) -> str:
    """Return the ``STATE-CANDIDATE-`` identity ``CLOSURE_POLICY.md`` §3 defines.

    The payload is the closed six-field projection the contract names; ``producing_change_refs``
    and ``source_snapshot_refs`` are already carried as ``UNORDERED_SET`` wrappers by the
    caller, which is where duplicate rejection and canonical member order belong -- this
    function does not re-derive them, so it cannot silently accept a bare array the contract
    forbids.
    """

    payload = {key: candidate[key] for key in _CANDIDATE_PAYLOAD_FIELDS}
    digest = hashlib.sha256(_CANDIDATE_DOMAIN_SEPARATOR + canonical_json_bytes(payload)).hexdigest()
    return "STATE-CANDIDATE-" + digest.upper()


def closure_evaluation_id(evaluation: dict[str, Any]) -> str:
    """Return the content address of a Closure Evaluation, by the repo-wide convention.

    ``reflow_transition_ref`` is part of the record and is excluded from this projection
    alongside ``closure_evaluation_id`` itself, for the reason ``change/identity.py`` excludes
    ``status`` and ``execution_result``: it is the receipt a later, atomic step stamps onto a
    decision already made, not part of what the decision *is*. Two Evaluations that reached
    the same gate decision from the same inputs are the same Evaluation, whichever one carries
    the receipt.
    """

    return content_address(
        "D-CLOSE-EVAL-",
        {key: value for key, value in evaluation.items() if key != "reflow_transition_ref"},
        "closure_evaluation_id",
    )


def closure_evaluation_decision_fingerprint(evaluation: dict[str, Any]) -> str:
    """Return the digest of a Closure Evaluation's gate decision alone.

    This is the input the Reflow transaction identity is derived from (see
    :func:`transaction_id`), and it is computed *before* ``reflow_transition_ref`` can be
    known -- deriving the transaction from the evaluation's own final ``closure_evaluation_id``
    would be circular, since that id is what names the transaction as its receipt.
    """

    payload = {key: value for key, value in evaluation.items() if key != "reflow_transition_ref"}
    return "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def material_contradiction_id(contradiction: dict[str, Any]) -> str:
    """Return the content address of a Material Contradiction record."""

    return content_address(
        "CONTRA-", contradiction, "material_contradiction_id"
    )


def kernel_source_witness_id(record: dict[str, Any]) -> str:
    """Return the content address of a ``kernel_source_witness`` record (R6-F4).

    The record's own ``commit_sha``/``tree_sha``/``blob_sha``/``path`` and the raw verified
    Git object bytes are all part of the payload -- two witnesses differing in any of them
    (a different path, a re-serialized but byte-different tree) are different records, by the
    same repo-wide convention every other identity here follows, not a scheme of this
    field's own invention.
    """

    return content_address("KERNEL-WITNESS-", record, "kernel_source_witness_id")


def transaction_id(
    *,
    project_id: str,
    difference_id: str,
    closure_decision_fingerprint: str,
    evidence_sufficiency_id: str | None,
    expected_revision: int,
    reflow_instant: str,
) -> str:
    """Return the deterministic identity of the committed ``state_transition`` event.

    Every field here is either an admitted input (``reflow_instant``) or the identity of a
    record a canonical owner already produced. None of it is read from a clock, and none of
    it is the caller's guess at what the next State will be -- the transaction is addressed
    by what was *decided*, not by what it will contain, which is why this function takes
    identities and a fingerprint rather than the derived next State itself.

    Including ``reflow_instant`` is what makes replay exact rather than merely repeatable: the
    Store's own conflict check (``FileStateStore.commit``) compares the *whole* canonical event,
    ``committed_at`` included, so a caller retrying the identical Reflow must supply the
    identical instant to get the identical transaction id and therefore the cached result
    rather than a manufactured conflict.
    """

    payload = {
        "project_id": project_id,
        "difference_id": difference_id,
        "closure_decision_fingerprint": closure_decision_fingerprint,
        "evidence_sufficiency_id": evidence_sufficiency_id,
        "expected_revision": expected_revision,
        "reflow_instant": reflow_instant,
    }
    digest = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    return "TX-" + digest.upper()
