"""The Model Execution Decision: does a real Human Authority grant *this exact* capability?

Phase 16 (Issue #66, P16-C1): a State-bound Model Work Unit must name "an explicit Authority
reference and decision" -- not a caller-asserted field, and not the mere identity of an
Authority holder. This module is that dedicated, read-only, deterministic public surface for
Model Runtime, added as an extension of the existing ``authority`` owner rather than as a
second owner -- the identical shape :func:`~.projection_authorization.
evaluate_projection_authorization` (Phase 14, P14-R1-F1) and
:func:`~.verifier_selection.evaluate_verifier_selection` (Phase 13, P13-R3-F1) already
established for their own questions.

**Why not :func:`~.engine.evaluate_authority`.** The one Change-permission evaluator answers
"may this *action* occur, against this exact State?" and its closed request shape is built for
exactly that question: a full ``difference`` record, a ``requested_action`` carrying an
``action_kind``/``reversibility``/opaque operation payload and its own recomputed fingerprint,
a ``requested_scope``, ``authority_rules``/``prohibitions``/``approvals``, and a
``current_state_revision``/``current_state_fingerprint`` pair, answering ``AUTONOMOUS`` /
``HUMAN_APPROVAL_REQUIRED`` / ``PROHIBITED``. The question Phase 16 has to ask is a
*capability-grant* question -- "did this Project Binding's Human Authority grant this specific
``required_capability``, for this Difference, inside this Boundary?" -- which has no requested
action, no reversibility, no scope containment and no rule/approval precedence in it at all.
Forcing it through the Change evaluator would mean inventing an ``action_kind`` for it, which
would make an unrecognized-but-well-formed kind fail closed to ``HUMAN_APPROVAL_REQUIRED``
rather than to a capability decision, and would silently reuse Change/Difference/State-bound
machinery for a purpose it was not designed for. That is the identical reasoning P13-R3-F1 and
P14-R1-F1 each recorded for their own extension.

``evaluate_model_execution_authorization`` binds ``project_id``, ``difference_ref``,
``required_capability`` and ``boundary_ref`` to at least one canonical, Human-Authority-granted
:data:`~.conformance.RECORD_TYPES` ``"model_execution_grant"`` record that names exactly those
same values -- never merely a caller-supplied mapping repeating them. A grant that binds on
every field but is not itself ``ACTIVE`` withholds authorization exactly as an excluding
Approval withholds a Change; a request naming no grant at all, or naming only grants that do
not bind, is refused.

**Signed Human declaration anchor.** A core-clean, ``ACTIVE`` ``model_execution_grant`` still
does not bind unless it carries a genuine Ed25519 signature, by the exact
``human_authority_signing_key`` a real Project Binding holds, over exactly the canonical bytes
:func:`~.identity.model_execution_grant_signing_payload` derives from its own adopted semantic
fields. A grant inserted directly into a Store, self-consistent and correctly
``granted_by``-shaped, authorizes zero model executions without that signature. Unlike
``github_projection_grant``, the signature lives on the grant record *itself* rather than on a
separate declaration record: this record kind has exactly one Human-declared body to anchor, so
the shared-derivation convention :func:`~manosube_agent_civilization.runtime.identity.
runtime_deployment_declaration_signing_payload` established -- one canonical projection that is
simultaneously the content address and the signed message -- closes the same gap with one
record instead of two.

Following :mod:`.errors`' own distinction: an unreadable request raises
:class:`~.errors.AuthorityError`. A readable request that does not bind is not an exception --
it is the decision ``MODEL_EXECUTION_REFUSED``.

This module never imports ``manosube_agent_civilization.model_runtime`` -- Model Runtime calls
this surface by its one public function, never the reverse, so no cycle and no Adapter-owned
Authority can exist (the identical prohibition P13-R3-F1 already states for Independent
Verification). It reaches no model, provider, adapter, network, or clock of any kind.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.difference.admissibility import require_object, require_scalar_tag
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.state.errors import CanonicalizationError

from .conformance import AUTHORITY_SCHEMA_BASE, admit_all, validate
from .errors import AuthorityError
from .identity import (
    model_execution_decision_id,
    model_execution_decision_semantic_fingerprint,
    model_execution_grant_signing_payload,
)

SCHEMA_VERSION = "0.1"

AUTHORIZED = "MODEL_EXECUTION_AUTHORIZED"
REFUSED = "MODEL_EXECUTION_REFUSED"
DECISIONS: frozenset[str] = frozenset({AUTHORIZED, REFUSED})

REQUIRED_REQUEST_KEYS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "difference_ref",
    "required_capability",
    "boundary_ref",
    "human_authority_ref",
    "human_authority_signing_key",
    "grants",
)

#: The closed capability vocabulary this evaluator recognizes. Owned by
#: ``01_SCHEMA/model_runtime/model_execution_boundary.schema.json#/$defs/required_capability``;
#: restated here only as the *input-boundary* gate, exactly as
#: :data:`~.projection_authorization._PROJECTION_KINDS` restates its own schema-owned
#: vocabulary, so a malformed capability is a caller-diagnosed refusal at the boundary rather
#: than a generated record failing its own output schema.
_REQUIRED_CAPABILITIES: frozenset[str] = frozenset({"PROPOSE_EVIDENCE_CANDIDATE"})
_PERMITTED_ACTIONS: frozenset[str] = frozenset({"EXECUTE_MODEL_WORK_UNIT"})


def _validate(record: dict[str, Any], schema_name: str) -> None:
    validate(record, schema_name, "model execution decision", base=AUTHORITY_SCHEMA_BASE)


def _require_request_shape(request: Any) -> dict[str, Any]:
    shaped = require_object(request, "model execution request")
    unknown = set(shaped) - set(REQUIRED_REQUEST_KEYS)
    if unknown:
        raise AuthorityError(f"model execution request carries unknown keys: {sorted(unknown)}")
    for key in REQUIRED_REQUEST_KEYS:
        if key not in shaped:
            raise AuthorityError(f"model execution request omits a required key: {key}")
    version = require_scalar_tag(shaped["schema_version"], "model execution request version")
    if version != SCHEMA_VERSION:
        raise AuthorityError(f"unsupported schema_version {version!r} at model execution request")
    return shaped


def _require_typed_reference(value: Any, *, context: str, kind: str) -> dict[str, Any]:
    reference = require_object(value, context)
    if reference.get("kind") != kind:
        raise AuthorityError(f"{context} does not name kind={kind!r}: {reference.get('kind')!r}")
    if not isinstance(reference.get("id"), str) or not reference["id"]:
        raise AuthorityError(f"{context} carries no readable id")
    return reference


def _core_mismatches(
    grant: dict[str, Any],
    *,
    project_id: str,
    difference_ref: dict[str, Any],
    required_capability: str,
    boundary_ref: dict[str, Any],
    human_authority_ref: dict[str, Any],
) -> list[str]:
    """Every way *grant* fails to bind this exact question; empty means it binds.

    Distinctness before activeness -- a grant naming a different Difference, capability or
    Boundary is not *this* question's grant at all, whatever its own status is (the identical
    discipline :func:`~.projection_authorization._core_mismatches` already applies).
    """

    reasons: list[str] = []
    if grant["project_id"] != project_id:
        reasons.append("GRANT_PROJECT_MISMATCH")
    if grant["difference_ref"] != difference_ref:
        reasons.append("GRANT_DIFFERENCE_MISMATCH")
    if grant["required_capability"] != required_capability:
        reasons.append("GRANT_CAPABILITY_MISMATCH")
    if grant["boundary_ref"] != boundary_ref:
        reasons.append("GRANT_BOUNDARY_MISMATCH")
    if grant["permitted_action"] not in _PERMITTED_ACTIONS:
        reasons.append("GRANT_ACTION_MISMATCH")
    if grant["granted_by"] != human_authority_ref:
        reasons.append("GRANT_AUTHORITY_MISMATCH")
    return sorted(reasons)


def _verify_grant_signature(grant: dict[str, Any], *, signing_key: dict[str, Any]) -> bool:
    """Whether *grant*'s own ``signature`` is a genuine Ed25519 signature, by the holder of
    *signing_key*, over exactly :func:`~.identity.model_execution_grant_signing_payload`'s own
    canonical bytes.

    The Ed25519 primitive is **not** reimplemented: Binding's own shared, public, fail-closed-
    as-a-value :func:`~manosube_agent_civilization.binding.signature.verify_ed25519_signature`
    is imported lazily -- deferred to call time, never module import time, for the identical
    circular-import reason :func:`~.conformance._human_grant_declaration_id` already documents
    -- and only the four-line composition around it (algorithm match, ``key_id`` match, then
    the primitive) lives here, exactly as :mod:`~manosube_agent_civilization.runtime.
    deployment_declaration` already composes it for its own signed record kind.

    ``False`` on any mismatch, never an exception; the caller decides what a ``False`` result
    means for the surrounding decision -- which here is always the ``MODEL_EXECUTION_REFUSED``
    decision record, never a raise.
    """

    from manosube_agent_civilization.binding.signature import (
        SUPPORTED_SIGNATURE_ALGORITHM,
        verify_ed25519_signature,
    )

    signature = grant.get("signature")
    if not isinstance(signature, dict):
        return False
    algorithm = signature.get("algorithm")
    if algorithm != SUPPORTED_SIGNATURE_ALGORITHM or signing_key.get("algorithm") != algorithm:
        return False
    if signature.get("key_id") != signing_key.get("key_id"):
        return False
    signature_hex = signature.get("value")
    public_key_hex = signing_key.get("public_key")
    if not isinstance(signature_hex, str) or not isinstance(public_key_hex, str):
        return False
    return verify_ed25519_signature(
        public_key_hex=public_key_hex,
        message=model_execution_grant_signing_payload(grant),
        signature_hex=signature_hex,
    )


def evaluate_model_execution_authorization(request: dict[str, Any]) -> dict[str, Any]:
    """Return one canonical Model Execution Decision for one exact request.

    The returned record is schema-valid and content-addressed: the same question always
    produces the same ``model_execution_decision_id``. *request* is never mutated.

    Every unreadable input leaves here as an :class:`~.errors.AuthorityError`; a readable
    request that does not bind returns a ``MODEL_EXECUTION_REFUSED`` decision rather than
    raising.
    """

    try:
        return _evaluate(request)
    except (DifferenceError, CanonicalizationError) as error:
        raise AuthorityError(str(error)) from error


def _evaluate(request: dict[str, Any]) -> dict[str, Any]:
    request = deepcopy(request)
    shaped = _require_request_shape(request)

    project_id = require_scalar_tag(shaped["project_id"], "model execution request project")
    difference_ref = _require_typed_reference(
        shaped["difference_ref"],
        context="model execution request difference_ref",
        kind="difference",
    )
    required_capability = require_scalar_tag(
        shaped["required_capability"], "model execution request required_capability"
    )
    if required_capability not in _REQUIRED_CAPABILITIES:
        raise AuthorityError(
            "model execution request required_capability is not recognized: "
            f"{required_capability!r}"
        )
    boundary_ref = _require_typed_reference(
        shaped["boundary_ref"],
        context="model execution request boundary_ref",
        kind="model_execution_boundary",
    )
    human_authority_ref = _require_typed_reference(
        shaped["human_authority_ref"],
        context="model execution request human_authority_ref",
        kind="human_authority",
    )
    # The real Project Binding's own public verification key, independently resolved by the
    # caller from its own fresh Boot -- this evaluator never trusts anyone's prior signature
    # check as a substitute for its own independent re-verification, the identical discipline
    # `evaluate_projection_authorization` already establishes.
    human_authority_signing_key = require_object(
        shaped["human_authority_signing_key"],
        "model execution request human_authority_signing_key",
    )

    # Every supplied grant crosses the identical admission gate every other Authority-owned
    # record does: schema, supported version, no unknown property, recomputed content address,
    # and Human Authority provenance (`.conformance.admit`).
    grants = admit_all(shaped["grants"], "model_execution_grant", "grants")

    binding: list[dict[str, Any]] = []
    excluding: list[tuple[dict[str, Any], str]] = []
    failures: list[str] = []
    for candidate in grants:
        mismatches = _core_mismatches(
            candidate,
            project_id=project_id,
            difference_ref=difference_ref,
            required_capability=required_capability,
            boundary_ref=boundary_ref,
            human_authority_ref=human_authority_ref,
        )
        if mismatches:
            failures.extend(mismatches)
            continue
        if candidate["status"] != "ACTIVE":
            excluding.append((candidate, f"GRANT_{candidate['status']}"))
            continue
        if not _verify_grant_signature(candidate, signing_key=human_authority_signing_key):
            excluding.append((candidate, "GRANT_SIGNATURE_INVALID"))
            continue
        binding.append(candidate)

    reason_codes: list[str] = []
    used_grant: dict[str, Any] | None = None
    if not grants:
        reason_codes.append("GRANT_MISSING")
    elif binding:
        # Chosen by identity, not by input position -- the same determinism every other
        # evaluator in this package already guarantees for its own grant selection.
        used_grant = sorted(binding, key=lambda grant: str(grant["model_execution_grant_id"]))[0]
        reason_codes.append("GRANT_EXACT")
    elif excluding:
        _first_grant, first_reason = sorted(
            excluding, key=lambda pair: str(pair[0]["model_execution_grant_id"])
        )[0]
        reason_codes.append(first_reason)
    else:
        reason_codes.extend(sorted(set(failures)))

    decision = AUTHORIZED if used_grant is not None else REFUSED
    return _decision(
        project_id=project_id,
        difference_ref=difference_ref,
        required_capability=required_capability,
        boundary_ref=boundary_ref,
        human_authority_ref=human_authority_ref,
        used_grant=used_grant,
        excluding_grants=[grant for grant, _reason in excluding],
        decision=decision,
        reason_codes=reason_codes,
    )


def _decision(
    *,
    project_id: str,
    difference_ref: dict[str, Any],
    required_capability: str,
    boundary_ref: dict[str, Any],
    human_authority_ref: dict[str, Any],
    used_grant: dict[str, Any] | None,
    excluding_grants: list[dict[str, Any]],
    decision: str,
    reason_codes: list[str],
) -> dict[str, Any]:
    """Assemble, address and validate one Model Execution Decision record."""

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "model_execution_decision_id": "",
        "project_id": project_id,
        "difference_ref": deepcopy(difference_ref),
        "required_capability": required_capability,
        "boundary_ref": deepcopy(boundary_ref),
        "selection_authority_ref": deepcopy(human_authority_ref),
        "grant_ref": (
            None
            if used_grant is None
            else {
                "kind": "model_execution_grant",
                "id": used_grant["model_execution_grant_id"],
            }
        ),
        "excluding_grant_refs": [
            {"kind": "model_execution_grant", "id": grant["model_execution_grant_id"]}
            for grant in excluding_grants
        ],
        "decision": decision,
        "decision_reason_codes": sorted(set(reason_codes)),
        "decision_semantic_fingerprint": "",
    }
    record["decision_semantic_fingerprint"] = model_execution_decision_semantic_fingerprint(record)
    record["model_execution_decision_id"] = model_execution_decision_id(record)
    _validate(record, "model_execution_decision.schema.json")
    return record


__all__ = [
    "AUTHORIZED",
    "DECISIONS",
    "REFUSED",
    "REQUIRED_REQUEST_KEYS",
    "evaluate_model_execution_authorization",
]
